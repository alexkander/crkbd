# Build guide conventions

`docs/` holds the end-user documentation, organized by product line and version:

```
docs/<product>/<version>/buildguide_{en,jp}.md
docs/firmware/<rev>/firmware_{en,jp}.md
```

- Products: `corne-cherry`, `corne-chocolate`, `corne-classic`, `corne-light`.
- Every guide is an English/Japanese pair. Keep both in sync when changing content; most contributions are typo fixes or translation corrections to one side of a pair.
- The unversioned `docs/<product>/buildguide_{en,jp}.md` files are index pages that link to each versioned guide. Adding a new version means updating these index pages and the "Latest versions" / "Old versions" lists in the root `README.md`.
- Firmware guides are per board revision (`rev1`, `rev4`); `docs/firmware/firmware_{en,jp}.md` is the index. rev4 guides link to prebuilt `.uf2` files in the `foostan/kbd_firmware` repository, split by PCB revision (v4.0.0 / v4.1.0) and layout (standard 3x6 / mini 3x5).
- Newer guides embed images as GitHub asset URLs; some older ones (e.g. `corne-cherry/v3`, `corne-light/v2`) keep images in a sibling `assets/` directory.

## Checking consistency

The `check-build-guides` skill (`.claude/skills/check-build-guides/`) runs a script that reports missing EN/JP counterparts, structural drift between languages, broken links, and guides missing from the index pages or `README.md`. Run it after any change to `docs/` or `README.md`.
