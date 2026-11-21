---
description: "[recreate] an existing .vxl: analyse it, then redesign it with new life"
argument-hint: <file.vxl>
---
Map to recreate: $ARGUMENTS

Use this command for every `[recreate]`, not a generic recreate skill (Floebreaker lesson, 2026-11-20). Same pipeline as /new-map (sync, branch `map/<new-slug>`, questions, concepts, graybox, art pass, export,
validate, probe, spec, PR), with the `[recreate]` flow from `docs/remus_recreate_report.md` in front:

1. Sync and branch as in /new-map step 1.
2. Analyse the original read-only. Keep it in `refs/` (git-ignored) and never commit another author's map.
   Its `.txt` is never executed or imported, only parsed for literal values.
   Run `python tools/recreate_analysis.py refs/<file>.vxl` (add `--txt` if the `.txt` has another name).
   It writes `out/recreate/<stem>/analysis.md` + `analysis.json` + numpy previews and measures:
   SHA-256, size and encoding; the `.txt` (author, fog, extensions, hooks); map DNA (levels, share of walkable
   ground, water depth, mirror match, floating pieces, sealed pockets, route parity); Babel fitness (platform
   volume, ground under both ends, build gap, roof or water spawn spots, anchor equality); spawn exposure;
   the 2026-11-13 zone targets (front, under-platform strip, centre footprint, cover placement); art stats
   (hue families, bright share, team hues, too white / too black); island-style metrics when it is an island.
   Read the previews and the analysis yourself as well: the tool finds numbers, not the map's identity.
   Caveats: an original has no authored terrain heights, so zone verdicts use an estimated ground (cliffs and
   shores can count as objects, mostly on islands); floating pieces may be the author's sky decor; build gap is
   the kit definition, one less than the figure quoted for remus; reachable roofs are not measured.
3. Write the element ledger: start from the tool's ledger skeleton, name every element and mark it
   Keep / Reimagine / Replace / Remove / Add.
4. Ask the recreate questions (how far to move from the original, modes, era or theme, island style if it is
   an island, extras, name). **Stop until I answer**, then offer three concepts unless I gave one.
5. Continue with /new-map steps 4–9. After the export, run
   `python tools/recreate_analysis.py refs/<file>.vxl --compare maps/<new-slug>_v1/<new-slug>.vxl` for the
   fidelity and problem-ledger sections. The report goes in `docs/<new-slug>_recreate_report.md` and credits
   the original map and its author.

**Model split (owner, 2026-11-15; agent roles 2026-11-20, `docs/agent_pipeline.md`).** This session acts as
`aos-guru`: it reads the analysis with you, owns the element ledger and the questions to me, and reviews every
stage (concepts, SPEC, graybox, art pass, release) against AGENTS.md §4 and the evidence before it is committed.
`map-runner` (Sonnet) runs the analysis tool, the checks, the probe, the previews and the report draft.
`map-designer` (Sonnet) turns the analysis + ledger + my answers into three concepts. `map-builder` (Opus) asks
its design questions, writes the SPEC numbers and implements them. A recreate is always tier L in /new-map step 0.
In a session that cannot spawn subagents, do the roles in order and say so in the hand-off.
