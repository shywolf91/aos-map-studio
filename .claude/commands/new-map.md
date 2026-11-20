---
description: Design and build a new AoS map from a brief, through the full pipeline
argument-hint: <brief>
---
Brief: $ARGUMENTS

Follow AGENTS.md (§3–§5, §11 git workflow) and the knowledge base.

**Step 0 — classify the scope and route models** (owner, 2026-11-18; saves usage without lowering quality).
Say the tier in one line before step 1, and re-classify if my answers change the scope.

| tier | brief looks like | planning (this session) | implementation | mechanical |
|---|---|---|---|---|
| **S** | edit/recolour/glow/fog/`.txt` change of an existing map, version bump, small fix | short, no concepts unless asked | `map-runner` (Sonnet) | `map-runner` |
| **M** | a normal new map in a style we have built before | full questions + concepts | `map-builder` (Opus) per stage | `map-runner` |
| **L** | `[recreate]`, assist structures, new mode, new island style, many unique structures, or anything we have not built before | full, careful SPEC; review every stage | `map-builder` (Opus) per stage | `map-runner` |

Rules for every tier: questions, concepts, SPEC numbers, reviewing check output and every commit stay in this
session. Hand subagents a self-contained brief (SPEC path, files to touch, what done looks like). If the session
cannot spawn subagents, do the work here and say so in the hand-off.

Steps:

1. Sync and branch. In the main checkout: `git checkout main && git pull`, then `git checkout -b map/<slug>`.
   In a worktree (main is held by the main checkout): `git fetch origin && git checkout -b map/<slug> origin/main`.
2. Read AGENTS.md §4, `docs/knowledge/project_memory.md` (newest entries win) and knowledge base §14.
   Ask my standard questions (mode/script, Babel type, full map or island, water, extras: underground,
   sky decor, glow, heavens_color, fog, corner tag, must-have objects). **Stop until I answer.**
3. Offer three distinct concepts (identity, Babel style, spawn floor z, target build gaps, art and play risk)
   and recommend one, unless I already gave a concept. **Stop for my pick.**
4. Log my answers and pick in `docs/knowledge/project_memory.md` (`- [stated] … (date)`).
5. Put every number in a SPEC dict in `scenes/<slug>/`. Build the graybox with `aosmap.kit`
   (`canvas`, `structures`, `symmetry`). Run `python -m aosmap.kit.babel_checks` and fix failures.
   Commit "graybox" and push.
6. Art pass in its own module (`aosmap.kit.color`, `veg`, `tag`, `sky`). The art pass must not change
   gameplay geometry. Re-run every check. Commit "art pass" and push.
7. Export `.vxl` + `.txt` and `build.json` (`aosmap.kit.build`). Cross-check with our reader and pyspades.
   Run the live server probe (`python -m aosmap.kit.probe`) in the target mode. Render previews and label
   them numpy previews.
8. Write `docs/<slug>_spec.md` (status ladder, owner answers, layout table, validation table, limits,
   regenerate commands). Put the map, renders, `build.json` and `validation.json` in `maps/<slug>_v1/`.
   Update the catalogue in `docs/agents_reference.md` §9 and `docs/knowledge/map_sources.md`.
9. Release commit, push, open a PR into main. Never merge.

Report the highest status-ladder rung actually reached. Never call a numpy preview a client capture.
If spawn exposure and open fronts conflict, report the trade-off instead of picking silently.
