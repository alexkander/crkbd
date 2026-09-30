# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

This is the hardware repository of the Corne (crkbd) split keyboard: KiCad PCB sources, JLCPCB production files, plate and case models, and build guides. There is no application code, build step, or test suite; firmware lives in https://github.com/foostan/kbd_firmware.

Detailed agent documentation lives in `docs-agents/`:

- `docs-agents/architecture.md` — repository layout, how board variants, plates, cases, and docs relate.
- `docs-agents/kicad.md` — KiCad projects, the `kbd` library subtree, library path setup, and the library check commands.
- `docs-agents/build-guides.md` — conventions for the user-facing build guides in `docs/`.

Key facts:

- `pcbs/common/kbd/` is a git subtree of https://github.com/foostan/kbd. Update it with `make pull-kbd-module`; do not edit it in place unless the change is meant to be upstreamed.
- Every build guide exists as an English/Japanese pair (`*_en.md` / `*_jp.md`); change both together.
- `docs/` is the user-facing documentation and is unrelated to `docs-agents/`.
- `.claude/settings.json` denies reading 3D models, zips, `.db` files, and `production_files/` to save tokens. Get information about them from their source (KiCad projects, file names, git history) instead of working around the rule with shell commands.
