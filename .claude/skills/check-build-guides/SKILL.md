---
name: check-build-guides
description: Check the EN/JP build and firmware guides in docs/ for missing counterparts, structural drift between languages, broken links, and versions missing from the index pages or README.md. Use after editing anything in docs/ or README.md, when reviewing a docs change or pull request, or when adding a new board version.
---

# Check build guides

Run the checker from the repository root instead of reading the guides to compare them by hand:

```sh
python .claude/skills/check-build-guides/scripts/check_guides.py
python .claude/skills/check-build-guides/scripts/check_guides.py --changed main   # also flag one-sided edits since main
```

It prints one `ERROR` or `WARN` line per finding and a summary; it exits with 1 only when there are errors.

| Finding | Meaning | Severity |
| --- | --- | --- |
| `pairs` | A `*_en.md` or `*_jp.md` has no counterpart. | error |
| `links` broken | A relative link, or a `github.com/foostan/crkbd/...` link, points to a path that does not exist. | error |
| `links` master | A link uses the old `master` branch; GitHub redirects it, but `main` is correct. | warning |
| `structure` | Heading, image, or code block counts differ between languages (shown as en/jp). | warning |
| `index` | A versioned guide is not linked from its section index page or from `README.md`. | warning |
| `changed` | With `--changed REF`: one side of a pair changed since REF and the other did not. | warning |

## Working with the results

- Report the findings grouped by file. Treat the checker output as the source of truth; do not re-derive it.
- For a `structure` warning, read only the differing parts: list headings with `grep -n '^#' <en> <jp>` and compare, instead of reading both files in full.
- A `changed` warning is expected for typo fixes that only apply to one language. For content changes, propose the matching edit in the other language and say that Japanese text written by Claude should be reviewed by a native speaker.
- Pre-existing warnings unrelated to the current change are known debt; mention them briefly but do not fix them unless asked.
- Section index pages are `docs/<section>/*_<lang>.md`; versioned guides are `docs/<section>/<version>/*_<lang>.md`. `docs/firmware/` guides are not linked from `README.md`, so they are not checked against it.
