#!/usr/bin/env python3
"""Check the EN/JP build and firmware guides under docs/ for consistency.

Checks:
  pairs      every *_en.md has a *_jp.md counterpart and vice versa
  structure  paired files have the same number of headings, images, and code blocks
  links      relative links and links to this repository on GitHub point to existing files
  index      every versioned guide is linked from its index page and from README.md
  changed    (with --changed REF) files changed since REF whose counterpart was not

Exits with status 1 when any error is found; warnings alone exit with 0.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

LANGS = ("en", "jp")
LINK_RE = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
HTML_SRC_RE = re.compile(r"<(?:img|a)\b[^>]*?(?:src|href)=\"([^\"]+)\"", re.IGNORECASE)
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(|<img\b", re.IGNORECASE)
REPO_URL_RE = re.compile(
    r"^https?://github\.com/foostan/crkbd/(?:blob|tree|raw)/(main|master)/([^?#]+)"
)


def repo_root():
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True
    )
    return Path(out.stdout.strip())


def counterpart(path):
    stem = path.stem
    for lang, other in (("_en", "_jp"), ("_jp", "_en")):
        if stem.endswith(lang):
            return path.with_name(stem[: -len(lang)] + other + path.suffix)
    return None


def strip_code(text):
    """Return lines outside fenced code blocks and the number of fenced blocks."""
    lines, blocks, fenced = [], 0, False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            blocks += 0 if fenced else 1
            continue
        if not fenced:
            lines.append(line)
    return lines, blocks


def structure(path):
    lines, blocks = strip_code(path.read_text(encoding="utf-8"))
    headings = sum(1 for line in lines if re.match(r"#{1,6}\s", line))
    images = sum(len(IMAGE_RE.findall(line)) for line in lines)
    return {"headings": headings, "images": images, "code blocks": blocks}


def links(path):
    lines, _ = strip_code(path.read_text(encoding="utf-8"))
    for number, line in enumerate(lines, 1):
        for regex in (LINK_RE, HTML_SRC_RE):
            for match in regex.finditer(line):
                yield number, match.group(1)


def resolve(root, source, target):
    """Map a link target to a repository path, or None when it is external."""
    match = REPO_URL_RE.match(target)
    if match:
        return root / match.group(2).rstrip("/")
    if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.IGNORECASE) or target.startswith("#"):
        return None
    target = target.split("#", 1)[0].split("?", 1)[0]
    if not target:
        return None
    if target.startswith("/"):
        return root / target.lstrip("/")
    return (source.parent / target).resolve()


def changed_files(root, ref):
    out = subprocess.run(
        ["git", "diff", "--name-only", ref, "--", "docs"],
        cwd=root, capture_output=True, text=True, check=True,
    ).stdout.split()
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "--", "docs"],
        cwd=root, capture_output=True, text=True, check=True,
    ).stdout.split()
    return {root / name for name in out + untracked}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--changed", metavar="REF", help="also report files changed since REF without their counterpart")
    args = parser.parse_args()

    root = repo_root()
    docs = root / "docs"
    readme = root / "README.md"
    guides = sorted(p for p in docs.rglob("*.md") if counterpart(p))
    errors, warnings = [], []

    def rel(path):
        return path.relative_to(root).as_posix()

    # pairs and structure
    for path in guides:
        other = counterpart(path)
        if not other.exists():
            errors.append(f"pairs: {rel(path)} has no counterpart {rel(other)}")
        elif path.stem.endswith("_en"):
            a, b = structure(path), structure(other)
            diffs = [f"{key} {a[key]}/{b[key]}" for key in a if a[key] != b[key]]
            if diffs:
                warnings.append(f"structure: {rel(path)} vs _jp: " + ", ".join(diffs) + " (en/jp)")

    # links, collecting every internal target for the index check
    linked_from = {}
    for source in guides + [readme]:
        for line, target in links(source):
            match = REPO_URL_RE.match(target)
            if match and match.group(1) == "master":
                warnings.append(f"links: {rel(source)}:{line} uses the old 'master' branch: {target}")
            resolved = resolve(root, source, target)
            if resolved is None:
                continue
            linked_from.setdefault(resolved, set()).add(source)
            if not resolved.exists():
                errors.append(f"links: {rel(source)}:{line} broken link: {target}")

    # index coverage: docs/<section>/<version>/<file> must be linked from
    # docs/<section>/<index>_<lang>.md and, for build guides, from README.md
    for path in guides:
        parts = path.relative_to(docs).parts
        if len(parts) != 3:
            continue
        section, lang = parts[0], path.stem.rsplit("_", 1)[1]
        indexes = sorted((docs / section).glob(f"*_{lang}.md"))
        sources = linked_from.get(path, set())
        if indexes and not sources.intersection(indexes):
            warnings.append(f"index: {rel(path)} is not linked from {', '.join(rel(i) for i in indexes)}")
        if section != "firmware" and readme not in sources:
            warnings.append(f"index: {rel(path)} is not linked from README.md")

    if args.changed:
        changed = changed_files(root, args.changed)
        for path in sorted(changed):
            other = counterpart(path)
            if other and path.suffix == ".md" and other not in changed:
                warnings.append(f"changed: {rel(path)} changed since {args.changed} but {rel(other)} did not")

    for kind, items in (("ERROR", errors), ("WARN", warnings)):
        for item in items:
            print(f"{kind} {item}")
    print(f"{len(guides)} guides checked: {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
