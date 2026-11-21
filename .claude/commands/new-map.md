---
description: Design and build a new AoS map from a brief, through the full pipeline
argument-hint: <brief>
---
Brief: $ARGUMENTS

Follow AGENTS.md (§3–§5, §11 git workflow) and the knowledge base. **This session acts as `aos-guru`**
(`.claude/agents/aos-guru.md`; roles, gates and handoff formats in `docs/agent_pipeline.md`): it talks to me,
briefs `map-designer`, `map-builder` and `map-runner`, reviews every handoff and owns every commit.

**Step 0 — classify the scope and route models** (owner, 2026-11-18; saves usage without lowering quality).
Say the tier in one line before step 1, and re-classify if my answers change the scope.

| tier | brief looks like | guru (this session) | concepts | design + implementation | evidence |
|---|---|---|---|---|---|
| **S** | edit/recolour/glow/fog/`.txt` change of an existing map, version bump, small fix | short, no concepts unless asked | — | `map-runner`, or `map-builder` for a code change | `map-runner` |
| **M** | a normal new map in a style we have built before | full questions; review every stage | `map-designer` (Sonnet) | `map-builder` (Opus): questions, SPEC, stages | `map-runner` (Sonnet) |
| **L** | `[recreate]`, assist structures, new mode, new island style, many unique structures, or anything we have not built before | full; careful SPEC review; review every stage | `map-designer` | `map-builder` | `map-runner` |

Rules for every tier: talking to me, reviewing every handoff (ACCEPT / REVISE / ESCALATE) and every commit stay in
this session; subagents never talk to me directly. Hand subagents a self-contained brief (SPEC path, files to touch, what done looks like). If the session
cannot spawn subagents, do the work here and say so in the hand-off.

Steps:

1. Sync and branch. In the main checkout: `git checkout main && git pull`, then `git checkout -b map/<slug>`.
   In a worktree (main is held by the main checkout): `git fetch origin && git checkout -b map/<slug> origin/main`.
2. Read AGENTS.md §4, **`docs/craft_standard.md`** (structures, spawns for every mode, release gate; open
   `docs/img/craft/structures_good_vs_bad.png`), `docs/knowledge/project_memory.md` (newest entries win) and
   knowledge base §14. Snow, winter or any palette-led theme: `docs/colour_palette_guide.md` too.
   Ask my standard questions (mode/script, Babel type, full map or island, water, extras: underground,
   sky decor, glow, heavens_color, fog, corner tag, must-have objects). **Stop until I answer.**
3. `map-designer` drafts three distinct concepts with mockups (`scenes/<slug>/concept/`); review them (gate G1),
   then offer them to me and recommend one, unless I already gave a concept. **Stop for my pick.**
4. `map-builder` phase A returns its design questions with recommended defaults; pass me the ones still open.
   **Stop for my answers.** Log my answers and pick in `docs/knowledge/project_memory.md` (`- [stated] … (date)`).
5. `map-builder` phase B puts every number in a SPEC dict in `scenes/<slug>/`; review it (gate G2). Build the graybox with `aosmap.kit`
   (`canvas`, `structures`, `symmetry`). Register every structure (`build.json` `structures`: name, box, role).
   Run `python -m aosmap.kit.babel_checks` (Babel) and `python -m aosmap.kit.craft_checks <dir> --mode <mode>`
   (spawn gates for every mode) and fix failures. `map-runner` gathers the evidence; review (gate G3). Commit "graybox" and push.
6. Art pass in its own module (`aosmap.kit.palette` ramps, `color.lighting`, `veg`, `tag`, `sky`). The art pass
   must not change gameplay geometry. Re-run every check, including `craft_checks` (building gates) and
   `tools/palette_audit.py`. Then the **visual review** (`docs/craft_standard.md` §5): close-ups of every main
   building and both spawns next to the exemplar sheet, one verdict line each. Rework anything plainer than the
   exemplars before committing "art pass" (`map-runner` evidence + player-height views, gate G4). The same review repeats at release; quality must not drop as the build
   goes on.
7. Export `.vxl` + `.txt` and `build.json` (`aosmap.kit.build`). Cross-check with our reader and pyspades.
   Run the live server probe (`python -m aosmap.kit.probe`) in the target mode. Render previews and label
   them numpy previews.
8. Write `docs/<slug>_spec.md` (status ladder, owner answers, layout table, validation table, limits,
   regenerate commands). Put the map, renders, `build.json` and `validation.json` in `maps/<slug>_v1/`.
   Update the catalogue in `docs/agents_reference.md` §9 and `docs/knowledge/map_sources.md`.
   Release evidence from `map-runner`; the guru signs off the release gate (G5) before I am asked to inspect.
9. Release commit, push, open a PR into main. Never merge.

Report the highest status-ladder rung actually reached. Never call a numpy preview a client capture.
If spawn exposure and open fronts conflict, report the trade-off instead of picking silently.
