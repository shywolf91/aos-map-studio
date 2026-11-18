# AGENTS.md — start here (any AI assistant working on this repo)

This repo is a prompt-to-map pipeline for **classic Ace of Spades 0.75** maps (`.vxl`) and their piqueserver
metadata (`.txt`). It contains the VXL toolchain (`aosmap/`), map generators (`scenes/`), finished maps
(`maps/`), validators, renderers, server test configs and the design knowledge collected while building them.

Owner: shywolf91. Last consolidated 2026-11-09 (moved from the claude.ai Project "AoS_Map_Making" to Claude Code).

> Claude Code reads `CLAUDE.md`, which imports this file. Codex, opencode, Cursor and most other agents read
> `AGENTS.md` directly. Keep the rules in this one file.

---

## 1. What to read (only what the task needs)

This file is loaded in every session; keep it lean. Read the rest **on demand**, and for big files read only the
section you need (each has a Contents list — grep the heading, then read that range).

| task | read |
|---|---|
| any map design/build | `docs/knowledge/project_memory.md` (newest entries win), then the matching sections of `docs/knowledge/aos_map_design_knowledge.md` (§7–§11 design, §14 questions, §15 checklist) |
| Babel spawns / zones | `docs/babel_rotation_guide_notes.md`; `docs/babel_zone_study.md` (2026-11-13; four §9 targets adopted in §4, rest proposals) |
| island brief | `docs/classic_island_style.md` (required, two island styles §4) |
| `[recreate]` | `docs/remus_recreate_report.md` (template) |
| format / runtime / toolchain | `docs/vxl_and_runtime_reference.md`, `docs/kit.md`; deeper: `docs/toolchain_and_art_kit.md`, `docs/phase2_exporter_validation.md`, `docs/heightmap_colourmap_tutorials.md` |
| example of a finished map | the spec of the newest similar map (catalogue: `docs/agents_reference.md` §9; newest Babel examples `docs/under_the_tree_spec.md`, `docs/bloomhop_kingdom_spec.md`) |
| original brief / per-mode prompts | `docs/project_brief/` |
| git, catalogue, lessons, Claude Code tooling | `docs/agents_reference.md` |
| git question, small fix, doc edit | nothing beyond this file |

`aos_map.md` is the older (10-13) knowledge base. `docs/knowledge/aos_map_designer_agent_prompt.md` is a
self-contained system prompt for other AIs.

## 2. Target environment

| | |
|---|---|
| Server | **stock piqueserver / pyspades 1.4.2** (tag v1.4.2, commit e555d210), normal script list |
| Teams | team1 **Blue (0,0,255)**, team2 **Red (255,0,0)** |
| Toolchain Python | **3.11**, with numpy, scipy and pillow; piqueserver 1.4.2 is installed for the pyspades cross-check |
| Clients | OpenSpades, BetterSpades, vanilla 0.75; the owner tests mostly in his own web spectator client `aos_web` (localhost) |
| Map size | 512 × 512 × 64; **z = 0 is the sky top, z = 63 the bottom**; z ≥ 62 is unbuildable and indestructible |

Use the code of the target server for compatibility decisions. If the docs and the source disagree, the source wins.
Never import mechanics from the Jagex/Steam Ace of Spades. It is a different game.

## 3. Working rules (honesty and method)

* **Status ladder.** Every map is described with the rung it actually reached:
  `researched → specified → generated → exported → parser-validated → server-loaded → client-inspected → playtested`.
  Never claim a rung you didn't reach. Numpy previews are not client inspection.
* **Evidence tags.** In docs, mark rules as `[SRC]` (read in source), `[RUN]` (observed running real code),
  `[DERIVED]`, `[USER]` (owner's decision), `[GUIDE]` (community guide), `[DESIGN]` (judgement) or `[OPEN]`.
* **Never invent** VXL format details, `.txt` keys, config options or API calls. The keys piqueserver reads are listed in `aos_map.md` §5.
* **Validate every export twice.** Read it back with our reader, and with `pyspades.vxl.VXLData` (byte-identical `generate()`).
  Then load it on a real piqueserver in the target mode.
* **Graybox first.** Check gameplay before decorating. The art pass must not change gameplay geometry.
* Builds must be reproducible. Use a fixed seed and `zlib.crc32` for hashing, never Python's `hash()`.
  Same seed → same SHA-256 in a fresh process.
  * Vegetation and decoration placement is **non-deterministic by owner rule**: draw an OS seed per build and save it
    (`build.json`) so that exact map can be rebuilt. Layout seeds stay fixed.
* **Beauty is the top artistic priority.** A valid but crude VXL is a prototype, not a finished map.
  The reference maps are for craft and detail density only. Never copy their objects, landmarks or terrain.

## 4. Owner's standing rules `[USER]`

These come from the owner's decisions and playtest feedback, 2026-10-12 → 2026-11-13 (dated log:
`docs/knowledge/project_memory.md`). Follow them unless a brief says otherwise.

### Process
* **Always ask questions before building a map** — never build without the answers (question list: knowledge base §14).
  Then offer three concepts unless he supplied one.
* `[recreate]` tag + attached `.vxl` = analyse that map and redesign it with new life through the normal pipeline
  (example: `docs/remus_recreate_report.md`). Edits of community maps otherwise stay "relatively the same" and credit
  the original author.
* `.txt` author is always `author = 'shywolf91 + AI'`.

### General
* **Ground is solid all the way down** (like remus/normandie), unless a tunnel or underground structure is intended.
  * The bottom layer is water, or whatever block is put there. Islands get seabed foundations.
  * No protection script is needed for this.
* **Floating authored pieces are opt-in.** Add them only when asked.
  * When used, list them as expected floating, keep them well away from play (e.g. ≥ 60 from the Babel platform,
    ≥ 8–10 air below, never over spawns) and state the collapse caveat. Breaking a player block next to a floating piece drops it for the round.
* **No AI-authored spawn coordinates.** Leave `get_spawn_location` / `get_entity_location` hooks out of `.txt` files
  and use the game-mode defaults; the owner supplies exact spawns himself if needed.
  (Stock `babel_script` ignores those hooks anyway.)
* **Fog:** brightness ~150+ per channel. Night maps get a bright tint, not a dark fog.
  * Pick a fog hue the palette doesn't use, and keep it neutral between blue and red.
  * Never use near-black floors. Luma ≥ ~40, because a luma ~10 floor read as pitch black in a client.
* **Corner tag:** paint only the map name, with no credit line.
  * Put it on the ground (painted on ground blocks or 1 above) in a free corner.
  * Use sky level only when that corner's scenery suits it. Clear only the area under the tag.
* Keep finished versions side by side (`maps/<name>_v1`, `_v2`, …). Never overwrite a released version.
* **Every structure is real** (2026-10-20): open doorways, real rooms, window openings, stairs to every upper floor,
  furniture, places to explore/hide. No solid boxes, no painted doors. Validate with an interiors reachability test.
* **Don't leave the centre empty** (2026-10-28). Most combat is in a central ~300–400 × 150–250 zone: pack it with
  distinct objects and gameplay elements, crossable on foot (7–10 voxel gaps, many openings, not a labyrinth).
* **Flank route** along the edges, 130–210 voxels from the centre. **Periphery passable** — no packed/overlapping props.
* Every area (centre and skirts) gets artistic detail; spread structures out. He **loves unique one-off objects**.
* Draw distance is ~110 voxels.
* **Vegetation:** non-deterministic, varied colours with smooth gradients, **three random details per plant**,
  groves not even scatter, striking and intricate.
* Players hate maps that are **too white** (snow: cap max channel ~212) and **too black** (floors luma ≥ 40).
* Optional extras he often picks: glow blocks (format in knowledge base §11.4), a floating sky-decor layer, an
  underground layer, `heavens_color`. Ask; don't assume.

### Island maps — two styles `[USER]` (2026-11-15)
* **Current** (our dense, authored house style: yulehaven_isles, Wicker King's Harvest) stays the default for an island brief.
* **"classic island map"** in the brief = the classic style in `docs/classic_island_style.md`:
  * one dominant natural island along the Babel axis (often a dumbbell with a neck), 70–80 % sea, a few islets;
  * a smooth height field with a beach ring;
  * 2–4 hue families;
  * a painted z = 63 sea that carries much of the look;
  * a sparse, repeated prop vocabulary (palms, bunkers, piers, a ship) and at most one or two modest landmarks.

  Measured from utopia2, islandbabel, babelpocalypse and toast; check it with `tools/island_style_metrics.py`.
  Every other rule in this section still applies. Where classic pulls against one (packed centre, one-off objects,
  flank distance, spawn cover), the guide proposes a reconciliation to confirm with the owner.
* Build **only the style the brief names** — one map per brief, not both versions (owner, 2026-11-15).

### Babel (the main mode so far)
* **Balanced spawns.** Both spawns should be mainly similar; usually the team's half is mirrored `x' = 512 − x`.
  * They may differ in structure.
  * **The fronts (spawn → tower zone) must be open** and give neither team an advantage.
* **Dress the front, never block it** (2026-11-10, tester feedback; replaces "don't default to structures or
  screens between spawn and tower zone"). The spawn → tower-zone strip is the most played part of the map, so it
  must not be bare flat ground. Scatter small, low, theme-fitting details across it: vehicles, bushes, one-storey
  one-room houses, haystacks, rocks, or slightly larger items, but nothing tall.
  * Players must move through it without obstruction: no wall, screen or structure that stops movement from
    spawn to the tower zone, and the space must still read as open.
  * A slight tower-building advantage from these objects is fine as long as both sides are symmetric.
  * It should look neither unnaturally empty next to the rest of the map nor like an out-of-place anomaly.
  * **In numbers** (2026-11-13, from `docs/babel_zone_study.md`): 4–15 low objects covering 5–30 % of the front;
    90 % of them no taller than 10 voxels; every 8-column north–south section at least 50 % free.
    A gate the owner asked for is reported separately and does not count against the height target.
* **Don't default to a raised tower zone.** Players like building towers from the ground.
* **Don't leave the strip under the platform bare** (2026-11-13). Low objects cover 15–45 % of the strip
  (x 212–300, y 240–271), with at least 25 voxels of air between their tops and the platform, so nothing becomes
  free scaffolding. The anchor ground under both platform ends stays flat and prop-free.
* **Anchor the centre with room-sized pieces** (2026-11-13). Alongside the small one-off props, the central zone
  has a few larger objects, so the typical (median) object footprint is 25 cells or more. Our earlier centres were
  made of many 7–21 cell props; community maps sit around 40.
* **Solid ground directly under both ends of the script platform** (stock x 206–211 / 300–305, y 240–271),
  so towers can anchor on each side.
* **No stairs on the enemy-facing side** of a team's tower-anchor ground. They make it too easy to climb up to that team's tower.
* **A safe way down** is required from spawn to the tower zone and to ground level (the rest of the map).
  * Feedback on Drowned Cathedral v1: it was too tall and hard to get down.
* **Spawn camping from the platform** is the classic way Babel maps fail.
  * Cover spawns with trees, walls, buildings or terrain, but not inside the stock ±20 square, because players spawn on the topmost voxel.
  * **Cover placement** (2026-11-13): at least 25 % of the ground on the enemy-facing side within 20 voxels of the
    spawn square carries cover 3 or more voxels tall, and at least 30 % of the ground 20–40 voxels behind the
    square is a backdrop (trees, buildings, terrain). Both benchmarks (Silverpine Hunt, Wicker King) have this.
    It never overrides "dress the front, never block it": if the two can't both be met, report the trade-off.
  * No roof spawns, no steep or low spawns right under the platform, no sealable single-exit spawns.
  * Targets: ≤ ~10 platform viewers per spawn spot, ≥ 15 % of spots hidden.
  * Measure with `aosmap/sightline.py`. Calibration and the rotation-guide rules are in `docs/babel_rotation_guide_notes.md`.
  * These rules pull against "open fronts". When both can't be met, report the trade-off to the owner instead of silently picking one.
* Avoid lag and flicker: no dense 1×1 pillar fields, no high-contrast 1-voxel stripes, no glaring or white fog.
* Vary playstyles across the rotation (sky babel, ground babel, island babel, joke maps).
* **Never put the platform in the VXL**; the script builds it.
* Spawns not 100 % flat but easy to spawn on (gentle mounds, no holes). Nothing solid blocks the front; structures
  on it need a walk-through opening (aos.party/view/413, /1248). Tower zone 32 wide, 44–135 from centre, no narrow
  passages (team-switch griefers block them), no authored ramp to the tower.
* **Custom variant = "Babel with assist structures"** (redefined 2026-11-08): stock Babel, but the map has climbable
  structures (ruins, tree, crag, mast…) that reach the platform on foot or with a short build. It is **not** a
  ready-made tower with the intel on top. Equal access, contestable, report build gap per structure, label the map.
  Full rules: `docs/project_brief/AoS_Map_Requirements.md` and knowledge base §8.8.

### Babel facts that constrain every map (stock 1.4.2) `[SRC]`
* The script builds the platform: x 206–305, y 240–271, z 1, colour (0,255,255).
  * **Keep z ≤ 2 empty above it.**
  * Servers may change these constants, so treat them as parameters (`BABEL_DEFAULT`).
* Bases are at (118,256) and (394,256). Spawns are random within ±20 at the **topmost solid voxel**, so squares x 98–138 / 374–414, y 236–276 must be clear, flat land.
* One intel at (256,256), on the platform. Carry it to **your own** base.
  * `babel_script` sets `map_info.cap_limit = 1`, but `server.set_map` reads `max_score` *before* that runs, so the
    live score limit is the config `cap_limit` (default 10; bots saw 10 in StateData, 2026-10-19). Admins set it.
  * A drop off the platform returns it; the carrier is killed after 150 s.
* Build ban: you can't build while standing in the enemy's tower corridor (blue x 301–384, red x 128–211, y 240–272).
  * Ending your anchor ground at x 211 / 301 means an enemy standing on it can't build.
* Destroy rule: the test is the **destroyer's standing position**, not the block's.
  * Blue is refused at x ≤ 288, red at x ≥ 224.
  * So centre blocks are hard to clear, not permanent. This corrects the stronger wording in older notes (Drowned Cathedral spec, `aos_map.md` §7).
* The platform is centred on 255.5 while the bases sit on 256, so a mirrored map gets 6 vs 5 anchor columns. That's accepted.
* `ALWAYS_ENABLED = True` in stock; also set `'babel': True` in extensions so maps work on servers that turn it off.
* `water_damage` only works with `piqueserver.scripts.map_extensions` loaded. It applies when the player's z ≥ 61.
  The per-tick rate is unmeasured.

## 5. Map request workflow

1. Extract the requirements: mode and exact script, theme, island style (current / classic), features, references, server/client target, protection policy, symmetry, outputs.
2. Verify the mode in source. Never assume rules from a mode's name.
3. Propose **three distinct concepts**, unless the owner gave a clear concept or asked to build straight away. Recommend one.
   * Some briefs say "do not build yet". Then stop at concepts.
4. Write a spatial spec: bounds, elevations, landmarks, routes, spawns, objectives, anchors, descents.
   Put the numbers in a `SPEC` dict in the generator as the single source of truth.
5. Graybox, then check: floating components, mirror, platform clearance, anchors, spawn squares, routes, descents, traps, build gaps, spawn exposure, building interiors (every room/floor reachable).
   Build with **`aosmap.kit`** and run `python -m aosmap.kit.babel_checks <dir>`, which does all of these (`docs/kit.md`; template `scenes/kit_example/`).
6. Art pass in a separate module, then re-run every check.
7. Export `.vxl` + `.txt` (`aosmap.kit.build.export`). Cross-check with pyspades, load on a live piqueserver in the mode (`python -m aosmap.kit.probe <dir>`), render previews (`aosmap.kit.preview`).
8. Write `docs/<map>_spec.md` with status, layout table, validation table, known limits and regenerate commands.
   Put the map, renders and `validation.json` in `maps/<map>_vN/`.
9. Hand off honestly: what was tested, what wasn't, the next tests. Iterate on the owner's or testers' feedback.

The full checklist is in `aos_map.md` §12. Route checks are a graph model, not proof of in-game playability.

## 6. `.txt` template (Babel)

```python
name = 'Map Name'
version = '1.0'
author = 'shywolf91 + AI'
description = 'Babel: ...'          # beware apostrophes inside single quotes; a .txt that fails to parse is only logged
fog = (176, 160, 186)               # bright, hue absent from the palette
extensions = {'babel': True, 'water_damage': 0}
# optional (owner's setup): 'heavens_color': (r, g, b, 255), 'glow_enabled': True, 'glow_stored_colors': {...}
# no get_spawn_location / get_entity_location hooks (owner rule)
```
A `.txt` that fails to load leaves the map running without extensions, and water damage silently disappears.
Re-test the load after every edit. Standalone harnesses must `import importlib.util` before using piqueserver's `Map()`.

## 7. Server test config

`server_test/*/config.toml` hold tested configs. The game mode is `piqueserver.game_modes.babel`.
Scripts include `piqueserver.scripts.map_extensions` and `piqueserver.scripts.babel_script`, plus the owner's normal list.
Optionally add `authored_protect` (`server_scripts/`). It protects authored geometry while letting opponents destroy player blocks.
Put maps in `<config dir>/maps/` and custom scripts in `<config dir>/scripts/`.

## 8. Lessons not to repeat

Moved to `docs/agents_reference.md` §8 — read it before a graybox or art pass.

## 9. Map catalogue

Moved to `docs/agents_reference.md` §9 (every map, version, status, where its source lives). Update it there.

## 10. Not in the repo (by design)

* **Reference maps** (`refs/`, ~36 community `.vxl` files) and the **Babel map rotation guide v1.8 PDF** (aloha.pk).
  They are other people's work: use them locally, but don't push them to a public repo. Our distilled notes are in `docs/`.
* Local config (`opencode.jsonc`) and update bundles (`_updates/`).

## 11. Working in Claude Code

Details (venv, importing chat zips, cloud sessions, `[recreate]` analysis, slash commands, shared kit, full git
steps) are in `docs/agents_reference.md` §11. The rules that apply every time:

* **Record new owner decisions in the same turn** `[USER]` (2026-11-10): append to `docs/knowledge/project_memory.md`
  (`- [stated] … (date)`) on a `docs/<topic>` branch, commit and push; standing rules also go into §4 here.
* **Git workflow** `[USER]` (2026-11-10) — standing permission to pull, branch, commit and push for map work:
  `git checkout main && git pull` first; one branch per map (`map/<slug>`, new version `map/<slug>-v2`; other work
  `tooling/<topic>` / `docs/<topic>`); commit after graybox, art pass and release and push after each commit; PR into
  `main` at release, merge only when the owner says so. Ask before committing files over ~50 MB; never force-push
  `main`; if a push fails, say so and leave the work committed locally.
* New maps use the shared kit `aosmap.kit` (`docs/kit.md`). Finish every map with `docs/<map>_spec.md`.
