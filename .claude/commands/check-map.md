---
model: sonnet
description: Full validation + live server probe for a map folder, with a status-ladder report
argument-hint: <maps\dir>
---
Map folder: $ARGUMENTS

Read-only: change nothing in the repo.

1. Find the `.vxl` and `.txt` in the folder and the mode (from the `.txt` extensions, the spec doc,
   or `server_test/*/config.toml`).
2. Parser checks: our reader (0 issues), re-encode, pyspades `VXLData.generate()`; if not byte-identical,
   compare 20,000 sampled voxels (solid + colour).
3. Run `python -m aosmap.kit.babel_checks <dir> --out <scratch>/validation.json` (Babel maps). Write the
   report to a scratch directory, never over the folder's own `validation.json`.
4. `.txt` checks: it loads, only real keys, author `shywolf91 + AI`, no spawn hooks, fog channels ~150+.
5. Live probe: `python -m aosmap.kit.probe <dir> --mode babel` (piqueserver 1.4.2 in a temp config).
6. Print one pass/fail table, the differences against the folder's `validation.json`, and the highest
   status-ladder rung actually reached. If something needs fixing, list it and ask.
