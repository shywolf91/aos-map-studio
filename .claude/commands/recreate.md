---
description: "[recreate] an existing .vxl: analyse it, then redesign it with new life"
argument-hint: <file.vxl>
---
Map to recreate: $ARGUMENTS

Same pipeline as /new-map (sync, branch `map/<new-slug>`, questions, concepts, graybox, art pass, export,
validate, probe, spec, PR), with the `[recreate]` flow from `docs/remus_recreate_report.md` in front:

1. Sync and branch as in /new-map step 1.
2. Analyse the original read-only. Keep it in `refs/` and never commit another author's map.
   Measure: SHA-256 and size; the `.txt` if supplied (author, fog, extensions); map DNA (levels, share of
   walkable street, reachable roofs, water depth and traps, mirror match, route parity); Babel fitness
   (platform volume, ground under both ends, build gap, roof or water spawn spots, anchor equality);
   spawn exposure with `aosmap.sightline`; art stats (hue families, bright share, floating pieces,
   sealed pockets).
3. Write the element ledger: every element marked Keep / Reimagine / Replace / Remove / Add.
4. Ask the recreate questions (how far to move from the original, modes, era or theme, extras, name).
   **Stop until I answer**, then offer three concepts unless I gave one.
5. Continue with /new-map steps 4–9. The report goes in `docs/<new-slug>_recreate_report.md` and credits
   the original map and its author.
