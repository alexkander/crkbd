# Repository architecture

The Corne is a split keyboard with 3x6 column-staggered keys plus 3 thumb keys per half, derived from Helix. "Mini" refers to the 3x5 layout.

## Layout

| Path | Contents |
| --- | --- |
| `pcbs/corne-cherry/hotswap/` | Current (v4.x) KiCad project for Cherry MX compatible switches. |
| `pcbs/corne-chocolate/hotswap/` | Current (v4.x) KiCad project for Kailh Choc v1/v2 switches. |
| `pcbs/*/hotswap/jlcpcb/` | JLCPCB order data: `production_files/` (BOM, CPL, zipped Gerbers) and `project.db`. |
| `pcbs/common/kbd/` | Shared KiCad symbol, footprint, and 3D model libraries (git subtree, see `kicad.md`). |
| `plates/3x6/`, `plates/3x5/` | Top and bottom plates, as KiCad PCB designs (`pcb/`, with their own `jlcpcb/production_files/`) and as SVG outlines (`svg/`). Top plates come in `cherrymx`/`alps` variants, with `-ex` versions. |
| `cases/3x6/`, `cases/3x5/` | Left/right case models in STEP format. |
| `docs/` | End-user build guides and firmware flashing guides (see `build-guides.md`). |

## Versions

Only v4 hardware sources are in the tree. Older boards (corne-classic v1, cherry v2/v3, chocolate v2, corne-light v1/v2) survive only as build guides in `docs/`; their PCB sources were removed from `pcbs/` and exist only in git history.

The PCB revision is stored in the KiCad title block (`rev` in the `.kicad_pcb`, e.g. `4.1.0`). v4.0.0 and v4.1.0 need different firmware builds (`docs/firmware/rev4/`), so revision bumps must be reflected there.

A single PCB project serves both the 3x6 and 3x5 (mini) layouts; plates and cases are split by layout instead.

## Generated artifacts

Gerbers, BOM, and CPL files under `jlcpcb/production_files/` are exported from the KiCad projects and committed. After changing a `.kicad_pcb`, they must be regenerated to stay in sync. `gerber/` and `order/` directories are git-ignored scratch output.

## Licensing

`LICENSE_MIT` and `LICENSE_CC` (CC BY 4.0) are both present at the root.
