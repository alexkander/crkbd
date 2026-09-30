# KiCad projects and libraries

## Projects

Each board variant is a KiCad project (`.kicad_pro`, `.kicad_sch`, `.kicad_pcb`), saved in the KiCad 7 file format (`version 20221018`). Edit them with KiCad; avoid hand-editing the S-expression files except for small, well-understood changes.

## Footprint library resolution

Footprints come from two nicknames:

- `kbd` — the globally installed kbd footprint library (e.g. `kbd:keyswitch_cherrymx_hotswap_1u`).
- `kbd_local` — declared in each project's `fp-lib-table` as `${KBD_DIR}/kicad-footprints/kbd.pretty` (OLED, TRRS jack, USB-C, SK6812MINI-E LEDs, reset switch, breakaway tabs, logo, etc.).

`KBD_DIR` is not defined in the project (`text_variables` is empty). It must be set as a KiCad path variable (Preferences → Configure Paths) pointing at `pcbs/common/kbd`, otherwise `kbd_local` footprints fail to resolve.

## The `kbd` subtree

`pcbs/common/kbd/` is a squashed git subtree of https://github.com/foostan/kbd:

- `kicad-symbols/kbd.kicad_sym` — schematic symbols.
- `kicad-footprints/kbd.pretty/*.kicad_mod` plus `fp-lib-table`.
- `kicad-packages3D/kbd.3dshapes/` — STEP models.

Pull upstream changes from the repository root:

```sh
make pull-kbd-module
```

## Library checks

The subtree has its own `Makefile` and GitHub workflows (Python 3.6, run on pull requests upstream) that use KiCad's `kicad-library-utils`. Run them from `pcbs/common/kbd/`:

```sh
make tools                              # clone kicad-library-utils
make kicad-footprints-check-lib-table
make kicad-footprints-check-all         # check_kicad_mod.py on every footprint
make kicad-symbols-check-lib-table
make kicad-symbols-comparelibs
```

The symbol targets still reference the legacy `*.lib` format and a `sym-lib-table`, while the library is now a single `.kicad_sym` file, so they are likely to fail as written.

## Inspecting projects

Use the `kicad-inspect` skill (`.claude/skills/kicad-inspect/`) instead of reading `.kicad_pcb` or `.kicad_sch` files: it wraps `kicad-cli` to report summaries, the BOM, net connections, DRC/ERC counts, and semantic diffs between git revisions. It needs `kicad-cli` (KiCad 10 was used to write it).

The files are in the KiCad 7 format. Opening and saving them in a newer KiCad upgrades the format, producing a huge diff and making them unreadable for older KiCad versions; do not save or run `kicad-cli pcb upgrade` unless that migration is intended.
