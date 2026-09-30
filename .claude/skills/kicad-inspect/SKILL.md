---
name: kicad-inspect
description: Answer questions about the KiCad boards and plates in this repository (parts, footprints, nets and pin connections, board size and revision, DRC/ERC results, what changed between commits) through kicad-cli, without reading the huge .kicad_pcb and .kicad_sch files. Use for any question about the PCB or schematic design, or when reviewing a commit or pull request that touches pcbs/ or plates/.
---

# Inspect KiCad projects

Never read `.kicad_pcb` or `.kicad_sch` files directly or `git diff` them; they are tens of thousands of lines. Run the script from the repository root instead:

```sh
S=.claude/skills/kicad-inspect/scripts/kicad_inspect.py
python $S summary cherry                     # title block (rev, date), size, component/pad/via counts
python $S bom chocolate                      # grouped BOM: qty, value, footprint, references
python $S net cherry U1                      # every pin of U1 and its net
python $S net cherry U1.12                   # one pin
python $S net cherry VBUS                    # pins of every net whose name contains VBUS
python $S drc cherry [--type TYPE]           # DRC + schematic parity counts; --type lists entries
python $S erc cherry [--type TYPE]           # ERC counts per sheet
python $S diff cherry REV [REV2]             # changes between git revisions (REV2 = working tree)
```

`PROJECT` is `cherry`, `chocolate`, a project directory, or a KiCad file path. Plates (`plates/*/pcb/*.kicad_pcb`) have no schematic, so only `summary`, `drc`, and the board statistics part of `diff` apply to them.

## Interpreting the output

- Both halves are on one board: right-half references start with `r` (`rU1`) and right-half power nets end in `R` (`GNDR`). The `left`/`right` sheets live in `pcbs/common/` and are shared by the cherry and chocolate projects, so `diff` on either project shows changes to them.
- DRC/ERC lines marked "library configuration of this machine" come from KiCad library tables not being set up locally (`kbd`, `kbd_local`, standard libraries). They are not design problems; ignore them unless the question is about library setup.
- The design was made with KiCad 7 and the script runs a newer `kicad-cli`, so some DRC/ERC findings (for example `footprint_symbol_field_mismatch` parity warnings) may come from newer checks. Say so when reporting them, and do not present long-standing findings as regressions without checking the previous revision with `diff` or by running the check at that revision.
- `diff` compares components, footprints, values, DNP, nets, title block, and board statistics (areas, pad, via, and component counts). Placement and routing changes only show up as changed statistics; say that the comparison is indirect when that is all that changed.

## Rules

- The script only writes to temporary directories. Do not run `kicad-cli` commands that write into the repository, and never `kicad-cli pcb upgrade` or `--save-board`: they would convert the KiCad 7 files to a newer format.
- If `kicad-cli` is missing, tell the user to install KiCad (Arch: `sudo pacman -S kicad`) instead of falling back to reading the files.
