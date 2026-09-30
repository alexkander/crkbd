#!/usr/bin/env python3
"""Query the KiCad projects in this repository through kicad-cli.

Prints compact summaries instead of the raw KiCad files. All kicad-cli output
goes to a temporary directory; the repository is never written to.

PROJECT is a name (cherry, chocolate), a project directory, or a
.kicad_pcb / .kicad_sch / .kicad_pro file (plates only have a .kicad_pcb).

  summary PROJECT                 title block, board size, component and pad counts
  bom PROJECT                     grouped bill of materials from the schematic
  net PROJECT QUERY               pins of the nets matching QUERY, or the nets of a
                                  reference (e.g. U1) or pin (e.g. U1.12)
  drc PROJECT [--type T]          DRC and schematic parity, counted by type
  erc PROJECT [--type T]          ERC, counted by type
  diff PROJECT REV [REV2]         component, footprint, net, and board statistics changes between two git
                                  revisions (REV2 defaults to the working tree)
"""

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

ALIASES = {
    "cherry": "pcbs/corne-cherry/hotswap/corne-cherry",
    "chocolate": "pcbs/corne-chocolate/hotswap/corne-chocolate",
}
# Violations caused by the local KiCad library configuration, not by the design.
ENVIRONMENT_TYPES = {"lib_footprint_issues", "lib_symbol_issues", "footprint_link_issues"}
DETAIL_LIMIT = 20


def run(*args, cwd=None):
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"command failed: {' '.join(map(str, args))}\n{result.stderr.strip() or result.stdout.strip()}")
    return result.stdout


def repo_root():
    return Path(run("git", "rev-parse", "--show-toplevel").strip())


def project_base(root, name):
    """Return the project path without extension, relative to root."""
    if name in ALIASES:
        return Path(ALIASES[name])
    path = Path(name).resolve()
    if path.is_dir():
        found = sorted(path.glob("*.kicad_pcb"))
        if len(found) != 1:
            sys.exit(f"expected one .kicad_pcb in {name}, found {len(found)}")
        path = found[0]
    if path.suffix not in (".kicad_pcb", ".kicad_sch", ".kicad_pro"):
        sys.exit(f"not a KiCad project file: {name}")
    return path.with_suffix("").relative_to(root)


def need(path):
    if not path.exists():
        sys.exit(f"missing {path.name}; this command needs it")
    return path


def title_block(pcb):
    head = pcb.read_text(encoding="utf-8")[:4000]
    fields = dict(re.findall(r'\((title|date|rev|company) "([^"]*)"\)', head))
    version = re.search(r"\(version (\d+)\)", head)
    fields["file format"] = version.group(1) if version else "?"
    return fields


def compress_refs(refs):
    """Turn R1,R2,R3,R5 into R1-R3,R5, keeping prefixes such as 'r' apart."""
    groups = defaultdict(list)
    for ref in refs:
        match = re.fullmatch(r"(.*?)(\d+)", ref)
        if match:
            groups[match.group(1)].append(int(match.group(2)))
        else:
            groups[ref].append(None)
    parts = []
    for prefix in sorted(groups):
        numbers = sorted(n for n in groups[prefix] if n is not None)
        if not numbers:
            parts.append(prefix)
            continue
        start = prev = numbers[0]
        for n in numbers[1:] + [None]:
            if n is not None and n == prev + 1:
                prev = n
                continue
            parts.append(f"{prefix}{start}" if start == prev else f"{prefix}{start}-{prefix}{prev}")
            if n is not None:
                start = prev = n
    return ",".join(parts)


def export_components(sch, tmp):
    out = tmp / "components.csv"
    run("kicad-cli", "sch", "export", "bom", "-o", out, "--fields", "Reference,Value,Footprint,DNP",
        "--labels", "ref,value,footprint,dnp", "--ref-range-delimiter", "", sch)
    with out.open(encoding="utf-8") as f:
        return {row["ref"]: row for row in csv.DictReader(f)}


def export_nets(sch, tmp):
    out = tmp / "netlist.xml"
    run("kicad-cli", "sch", "export", "netlist", "--format", "kicadxml", "-o", out, sch)
    nets = {}
    for net in ET.parse(out).getroot().find("nets"):
        nets[net.get("name")] = sorted(
            (node.get("ref"), node.get("pin"), node.get("pinfunction") or "") for node in net
        )
    return nets


def export_stats(pcb, tmp):
    out = tmp / "stats.json"
    run("kicad-cli", "pcb", "export", "stats", "--format", "json", "-o", out, pcb)
    return json.loads(out.read_text(encoding="utf-8"))


def flat_stats(stats):
    """Flatten the comparable board statistics into {name: value}."""
    flat = {f"board {k}": v for k, v in stats["board"].items() if "density" not in k}
    flat.update({f"pads {k}": v for k, v in stats["pads"].items()})
    flat.update({f"vias {k}": v for k, v in stats["vias"].items()})
    flat.update({f"components {k}": c["total"] for k, c in stats["components"].items()})
    return flat


def board_limit(value):
    # kicad-cli reports INT_MAX nanometers (2147.4836 mm) when a board has no tracks or drills
    return "n/a" if value.startswith("2147.48") else value


def cmd_summary(root, base, args):
    pcb = need(root / base.with_suffix(".kicad_pcb"))
    with tempfile.TemporaryDirectory() as tmp:
        stats = export_stats(pcb, Path(tmp))
    print(base.as_posix())
    for key, value in title_block(pcb).items():
        print(f"  {key}: {value}")
    board = stats["board"]
    print(f"  size: {board['width']} x {board['height']}, thickness {board['board_thickness']}")
    print(f"  min track width {board_limit(board['min_track_width'])}, "
          f"min clearance {board_limit(board['min_track_clearance'])}, "
          f"min drill {board_limit(board['min_drill_diameter'])}")
    comps = {kind: c for kind, c in stats["components"].items() if kind != "total" and c["total"]}
    print("  components: " + (", ".join(
        f"{kind} {c['total']} (front {c['front']}, back {c['back']})" for kind, c in comps.items()) or "none"))
    print("  pads: " + (", ".join(f"{k} {v}" for k, v in stats["pads"].items() if v) or "none"))
    print("  vias: " + (", ".join(f"{k} {v}" for k, v in stats["vias"].items() if v) or "none"))


def cmd_bom(root, base, args):
    sch = need(root / base.with_suffix(".kicad_sch"))
    with tempfile.TemporaryDirectory() as tmp:
        components = export_components(sch, Path(tmp))
    groups = defaultdict(list)
    for ref, row in components.items():
        groups[(row["value"], row["footprint"], row["dnp"])].append(ref)
    print("qty\tvalue\tfootprint\trefs")
    for (value, footprint, dnp), refs in sorted(groups.items(), key=lambda g: g[1][0].lstrip("r")):
        print(f"{len(refs)}\t{value}\t{footprint}{' [DNP]' if dnp else ''}\t{compress_refs(refs)}")
    print(f"{len(components)} components in {len(groups)} groups")


def cmd_net(root, base, args):
    sch = need(root / base.with_suffix(".kicad_sch"))
    with tempfile.TemporaryDirectory() as tmp:
        nets = export_nets(sch, Path(tmp))
    ref, _, pin = args.query.partition(".")
    by_ref = [(name, node) for name, nodes in nets.items() for node in nodes
              if node[0] == ref and (not pin or node[1] == pin)]
    if by_ref:
        for name, (r, p, function) in sorted(by_ref, key=lambda x: (x[1][1].zfill(4), x[0])):
            print(f"{r}.{p}\t{function}\t{name}")
        return
    matches = {name: nodes for name, nodes in nets.items() if args.query.lower() in name.lower()}
    if not matches:
        sys.exit(f"no net or reference matches {args.query!r}")
    for name, nodes in sorted(matches.items()):
        pins = " ".join(f"{r}.{p}" + (f"({f})" if f else "") for r, p, f in nodes)
        print(f"{name} [{len(nodes)}]: {pins}")


def report_violations(groups, type_filter):
    for label, items in groups:
        counts = Counter((v["severity"], v["type"]) for v in items)
        design = [(k, n) for k, n in counts.most_common() if k[1] not in ENVIRONMENT_TYPES]
        environment = sum(n for k, n in counts.items() if k[1] in ENVIRONMENT_TYPES)
        print(f"{label}: {len(items)}")
        for (severity, kind), n in design:
            print(f"  {n}\t{severity}\t{kind}")
        if environment:
            print(f"  {environment}\t(library configuration of this machine, not the design)")
        if type_filter:
            selected = [v for v in items if v["type"] == type_filter]
            for v in selected[:DETAIL_LIMIT]:
                where = "; ".join(i["description"] for i in v.get("items", []))
                print(f"    - {v['description']} | {where}")
            if len(selected) > DETAIL_LIMIT:
                print(f"    ... {len(selected) - DETAIL_LIMIT} more")


def cmd_drc(root, base, args):
    pcb = need(root / base.with_suffix(".kicad_pcb"))
    parity = base.with_suffix(".kicad_sch")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "drc.json"
        extra = ["--schematic-parity"] if (root / parity).exists() else []
        run("kicad-cli", "pcb", "drc", "--format", "json", "--severity-error", "--severity-warning", *extra,
            "-D", f"KBD_DIR={root / 'pcbs/common/kbd'}", "-o", out, pcb)
        report = json.loads(out.read_text(encoding="utf-8"))
    report_violations([
        ("violations", report.get("violations", [])),
        ("unconnected items", report.get("unconnected_items", [])),
        ("schematic parity", report.get("schematic_parity", [])),
    ], args.type)


def cmd_erc(root, base, args):
    sch = need(root / base.with_suffix(".kicad_sch"))
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "erc.json"
        run("kicad-cli", "sch", "erc", "--format", "json", "--severity-error", "--severity-warning", "-o", out, sch)
        report = json.loads(out.read_text(encoding="utf-8"))
    groups = [(f"sheet {s['path']}", s["violations"]) for s in report["sheets"]]
    report_violations(groups, args.type)


def snapshot(root, base, rev, dest):
    """Extract pcbs/ at rev (or the working tree when rev is None) into dest."""
    if rev is None:
        shutil.copytree(root / "pcbs", dest / "pcbs", ignore=shutil.ignore_patterns("kicad-packages3D", "jlcpcb"))
    else:
        archive = subprocess.run(["git", "archive", rev, "pcbs"], cwd=root, capture_output=True)
        if archive.returncode != 0:
            sys.exit(archive.stderr.decode().strip())
        subprocess.run(["tar", "-x", "-C", dest], input=archive.stdout, check=True)
    sch, pcb = dest / base.with_suffix(".kicad_sch"), dest / base.with_suffix(".kicad_pcb")
    return {
        "title": title_block(pcb) if pcb.exists() else {},
        "stats": flat_stats(export_stats(pcb, dest)) if pcb.exists() else {},
        "components": export_components(sch, dest) if sch.exists() else {},
        "nets": export_nets(sch, dest) if sch.exists() else {},
    }


def cmd_diff(root, base, args):
    with tempfile.TemporaryDirectory() as tmp_a, tempfile.TemporaryDirectory() as tmp_b:
        a = snapshot(root, base, args.rev, Path(tmp_a))
        b = snapshot(root, base, args.rev2, Path(tmp_b))
    label = f"{args.rev}..{args.rev2 or 'working tree'}"
    print(f"{base.as_posix()} {label}")
    for key in sorted(set(a["title"]) | set(b["title"])):
        if a["title"].get(key) != b["title"].get(key):
            print(f"  title block {key}: {a['title'].get(key)} -> {b['title'].get(key)}")
    for key in sorted(set(a["stats"]) | set(b["stats"])):
        if a["stats"].get(key) != b["stats"].get(key):
            print(f"  pcb {key}: {a['stats'].get(key)} -> {b['stats'].get(key)}")

    ca, cb = a["components"], b["components"]
    for name, refs in (("added", sorted(set(cb) - set(ca))), ("removed", sorted(set(ca) - set(cb)))):
        if refs:
            print(f"  components {name}: {compress_refs(refs)}")
    changes = defaultdict(list)
    for ref in set(ca) & set(cb):
        for field in ("value", "footprint", "dnp"):
            if ca[ref][field] != cb[ref][field]:
                changes[(field, ca[ref][field], cb[ref][field])].append(ref)
    for (field, old, new), refs in sorted(changes.items()):
        print(f"  {field} {old!r} -> {new!r}: {compress_refs(refs)}")

    na, nb = a["nets"], b["nets"]
    for name, nets in (("added", sorted(set(nb) - set(na))), ("removed", sorted(set(na) - set(nb)))):
        if nets:
            print(f"  nets {name} ({len(nets)}): {', '.join(nets[:DETAIL_LIMIT])}"
                  + (" ..." if len(nets) > DETAIL_LIMIT else ""))
    changed = [n for n in sorted(set(na) & set(nb)) if na[n] != nb[n]]
    for name in changed[:DETAIL_LIMIT]:
        pa = {f"{r}.{p}" for r, p, _ in na[name]}
        pb = {f"{r}.{p}" for r, p, _ in nb[name]}
        print(f"  net {name}: +[{' '.join(sorted(pb - pa))}] -[{' '.join(sorted(pa - pb))}]")
    if len(changed) > DETAIL_LIMIT:
        print(f"  ... {len(changed) - DETAIL_LIMIT} more changed nets")
    print("  note: PCB placement, routing, and zones are compared only through the statistics above")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("summary", "bom", "net", "drc", "erc", "diff"):
        p = sub.add_parser(name)
        p.add_argument("project")
        if name == "net":
            p.add_argument("query")
        if name in ("drc", "erc"):
            p.add_argument("--type", help="list the violations of this type")
        if name == "diff":
            p.add_argument("rev")
            p.add_argument("rev2", nargs="?")
    args = parser.parse_args()
    if not shutil.which("kicad-cli"):
        sys.exit("kicad-cli not found; install KiCad (on Arch: sudo pacman -S kicad)")
    root = repo_root()
    base = project_base(root, args.project)
    globals()[f"cmd_{args.command}"](root, base, args)


if __name__ == "__main__":
    main()
