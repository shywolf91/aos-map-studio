# AGENTS.md — start here (any AI assistant working on this repo)

This repo is a prompt-to-map pipeline for **classic Ace of Spades 0.75** maps (`.vxl`) and their piqueserver
metadata (`.txt`). It contains the VXL toolchain (`aosmap/`), map generators (`scenes/`), finished maps
(`maps/`), validators, renderers, server test configs and the design knowledge collected while building them.

Owner: shywolf91. Last consolidated 2026-11-09 (moved from the claude.ai Project "AoS_Map_Making" to Claude Code).

> Claude Code reads `CLAUDE.md`, which imports this file. Codex, opencode, Cursor and most other agents read
> `AGENTS.md` directly. Keep the rules in this one file.

---

## 1. Read in this order

1. **This file.** It holds the owner's standing rules (§4).
2. `docs/knowledge/project_memory.md` is the owner's decision and feedback log (every `[USER]` rule with its date,
   plus the history of each map request). Newest entries win.
3. `docs/knowledge/aos_map_design_knowledge.md` is the newest, most complete knowledge base (2026-10-30, updated
   2026-11-08): format, physics, metadata, modes, Babel design rules, art direction, fog/glow, house rules, toolchain,
   workflow, checklist, portfolio, reference measurements. `aos_map.md` is the older (10-13) version of it.
4. `docs/vxl_and_runtime_reference.md` is the source-verified technical reference, with file and function citations.
5. `docs/babel_rotation_guide_notes.md` covers Babel spawn-camping rules and the calibrated spawn-exposure targets.
6. `docs/project_brief/` holds the original project brief, the role instructions and the per-mode design prompts.
7. Read the spec of the newest map closest to your task (§9):
   * `docs/under_the_tree_spec.md` and `docs/bloomhop_kingdom_spec.md` are the newest Babel examples (2026-11-09).
   * `docs/remus_recreate_report.md` is the template for a `[recreate]` job.

`docs/knowledge/aos_map_designer_agent_prompt.md` is a self-contained system prompt for other AIs.
`docs/toolchain_and_art_kit.md`, `docs/phase2_exporter_validation.md` and `docs/heightmap_colourmap_tutorials.md` are
deeper background. Read them when you touch those areas.

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

These come from the owner's decisions and playtest feedback, 2026-10-12 → 2026-11-09 (dated log:
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

### Babel (the main mode so far)
* **Balanced spawns.** Both spawns should be mainly similar; usually the team's half is mirrored `x' = 512 − x`.
  * They may differ in structure.
  * **The fronts (spawn → tower zone) must be open** and give neither team an advantage.
* **Don't default to structures or screens between spawn and tower zone.** Many players dislike them.
  They're fine occasionally, but they must not become every map's pattern.
* **Don't default to a raised tower zone.** Players like building towers from the ground.
* **Solid ground directly under both ends of the script platform** (stock x 206–211 / 300–305, y 240–271),
  so towers can anchor on each side.
* **No stairs on the enemy-facing side** of a team's tower-anchor ground. They make it too easy to climb up to that team's tower.
* **A safe way down** is required from spawn to the tower zone and to ground level (the rest of the map).
  * Feedback on Drowned Cathedral v1: it was too tall and hard to get down.
* **Spawn camping from the platform** is the classic way Babel maps fail.
  * Cover spawns with trees, walls, buildings or terrain, but not inside the stock ±20 square, because players spawn on the topmost voxel.
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

1. Extract the requirements: mode and exact script, theme, features, references, server/client target, protection policy, symmetry, outputs.
2. Verify the mode in source. Never assume rules from a mode's name.
3. Propose **three distinct concepts**, unless the owner gave a clear concept or asked to build straight away. Recommend one.
   * Some briefs say "do not build yet". Then stop at concepts.
4. Write a spatial spec: bounds, elevations, landmarks, routes, spawns, objectives, anchors, descents.
   Put the numbers in a `SPEC` dict in the generator as the single source of truth.
5. Graybox, then check: floating components, mirror, platform clearance, anchors, spawn squares, routes, descents, traps, build gaps, spawn exposure, building interiors (every room/floor reachable; see `scenes/hollow_crown/hc_check.py` → `interiors`).
6. Art pass in a separate module, then re-run every check.
7. Export `.vxl` + `.txt`. Cross-check with pyspades, load on a live piqueserver in the mode, render previews.
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

* Mirror first, then place cosmetic or asymmetric pieces (stem, witches, sky decor).
* Mirroring leaves column 256 empty unless you copy 255 into it.
* Props must test the surface they land on. Keep spawn squares, anchors, walkways and objective columns in a no-prop mask.
* Enforce face contact for trunks, branches, roofs and vigas. Diagonal-only contact floats, and floating pieces collapse.
* Sky decor only reads within ~65 voxels. Fog (~128) and the 64-voxel ceiling stop backdrops from carrying across the map.
  Birds narrower than ~13 voxels vanish.
* Dense foliage creates walk-out pockets (Backyard Babel). Check for trap cells, and keep foliage off spawn fronts.
* A painted z = 63 sea or sky (Cloud Smash technique) gives a large visual payoff at zero gameplay cost.
* Big maps are fine for the server, but watch the file size: Backyard Babel is 7.6 MB, about 3× normandie. Client FPS is untested.

## 9. Map catalogue

| map | mode | latest | status | where the source lives |
|---|---|---|---|---|
| Kestrel Spires | sky Babel | art v2 / v3 | client-inspected (BetterSpades) | `scenes/kestrel_spires*` |
| Hollowfen | Babel + CTF | art v1 | client-inspected (BetterSpades) | `scenes/hollowfen*` |
| Hollowfen Vale | Babel | v1 | server-loaded | `scenes/hollowfen*`, `docs/hollowfen_vale_spec.md` |
| Drowned Cathedral | Halloween Babel | v2 (rotated redesign) | server-loaded; v1 playtested by a tester | `scenes/drowned_cathedral*` |
| spinline | joke Babel (pinline-style) | v1.4 | client-loaded by owner | **zip from its chat**; spec `docs/spinline_spec.md` |
| Brimstone Atoll | Halloween island Babel | v1.3 | server-loaded | **zip from its chat**; spec `docs/brimstone_atoll_spec.md` |
| Witchwood Isles | Halloween island Babel | v1.0 | server-loaded | **zip from its chat**; spec `docs/witchwood_isles_spec.md` |
| Backyard Babel | Grounded-style backyard Babel | v5.0 | server-loaded | **zip from its chat**; spec `docs/backyard_babel_spec.md` (v2 spec kept) |
| The Wicker King's Harvest | Halloween island Babel | v1.0 / v1.1 (sky) | server-loaded | `scenes/wicker_kings_harvest/` |
| Graveyard of the Forgotten — The Bone Cathedral | Halloween ground Babel | v1.0 | client-inspected (BetterSpades screenshots) | `scenes/graveyard_forgotten/`, `docs/graveyard_of_the_forgotten_spec.md` |
| The Hollow Crown | Halloween ground Babel | v1.1 (v1.0 kept) | server-loaded + bots | `scenes/hollow_crown/`, `docs/hollow_crown_spec.md` |
| Death Swamp | Push (first) | v1.0 | server-loaded + bots | `scenes/death_swamp/`, `maps/death_swamp_v1/`, `server_test/push_ds/`; spec `docs/death_swamp_spec.md` |
| Haunted Fairground | Halloween island Babel (Ruins layout) | v1.3 | server-loaded | **zip from its chat**; spec `docs/haunted_fairground_isles_v1.md` |
| Ferrari's Revenge (Skull River) | Babel | v3 | parser-validated | **zip from its chat**; spec `docs/skull_river_spec.md` |
| Royal Parade Halloween | community-map edit (Bradley & Mile) | v1.1 | parser-validated; viewed on alohacraft | **zip from its chat**; spec `docs/royal_parade_halloween_spec.md` |
| 1river2night v2.2 | night recolour + glow | v2.2 | parser-validated | **zip from its chat**; spec `docs/1river2night_v2_spec.md` |
| Bikini Atoll (Detonation) | Push glow edit (IAmYourFriend) | v1.2 | parser-validated | **zip from its chat**; spec `docs/bikini_atoll_detonation_spec.md` |
| Silverpine Hunt | Halloween snow Babel | v1.x → v2.2 (+sky) | server-loaded | **zip from its chat**; specs `docs/silverpine_hunt_spec.md`, `docs/silverpine_hunt_v2_spec.md` |
| Mossglade Pond | ground Babel | v1.0 | server-loaded | **zip from its chat**; spec `docs/mossglade_pond_spec.md` (owner decisions open) |
| Lantern Bazaar Canals | ground Babel | v1.0 | server-loaded | **zip from its chat**; spec `docs/lantern_bazaar_canals_spec.md` |
| Highland Loch Castle | island Babel | v1.0 | server-loaded | **zip from its chat**; spec `docs/highland_loch_castle_spec.md` |
| Sunken Reef Atoll | island Babel | v1.0 | server-loaded | **zip from its chat**; spec `docs/sunken_reef_atoll_spec.md` |
| Clockwork Skyyard | steampunk sky Babel | v1.0 | server-loaded | **zip from its chat**; spec `docs/clockwork_skyyard_spec.md` |
| Cherry Terrace Gardens / Cherry Gardens | spring ground Babel | v1.0 (rebuilt as Cherry Gardens) | parser-validated / server-loaded | **zip from its chat**; specs `docs/cherry_terrace_gardens_spec.md`, `docs/cherry_gardens_spec.md` |
| Remoria ([recreate] of remus) | ground Babel | v1.0 | server-loaded | **zip from its chat**; report `docs/remus_recreate_report.md` |
| Bloomhop Kingdom | platformer-world ground Babel | v1.0 | server-loaded | **zip from its chat**; spec `docs/bloomhop_kingdom_spec.md` |
| Under the Tree | Christmas Babel, assist structures | v1.0 | server-loaded | **zip from its chat**; spec `docs/under_the_tree_spec.md` |

Maps marked "zip from its chat" were built in Claude's sandbox. Their generator code is in the zip delivered in that
chat (links: `docs/knowledge/map_sources.md`). Unpack it under `scenes/<map>/` and `maps/<map>_vN/` to bring them into the repo (see §11).

## 10. Not in the repo (by design)

* **Reference maps** (`refs/`, ~36 community `.vxl` files) and the **Babel map rotation guide v1.8 PDF** (aloha.pk).
  They are other people's work: use them locally, but don't push them to a public repo. Our distilled notes are in `docs/`.
* Local config (`opencode.jsonc`) and update bundles (`_updates/`).

## 11. Working in Claude Code (since 2026-11-09)

* Work happens in `D:\Ace of Spades\Aos_Map` on the owner's Windows PC (DRAGONSPIRE). Use Python 3.11 in a venv with
  `requirements.txt` + `piqueserver==1.4.2`. Shell commands in docs are written bash-style; on Windows use
  `python` from the venv and adjust `cp`/paths.
* Put reference maps in `refs/` (git-ignored). Read them with `aosmap.vxl.read_vxl`.
* **Importing a map from a chat zip:** unzip into `_updates/<map>/` (git-ignored), then move the generator into
  `scenes/<map>/` and the outputs into `maps/<map>_vN/`, run its check script, and update §9's "where the source
  lives" column. Large build artefacts (`mat.npy`, `*.npy`) stay git-ignored.
* **Recording new decisions:** when the owner states a new preference or rule, append it to
  `docs/knowledge/project_memory.md` (`- [stated] … (date)`) and, if it's a standing rule, add it to §4 here.
  That file replaces the claude.ai Project memory.
* Finish every map with `docs/<map>_spec.md` (status ladder, layout table, validation table, limits, regenerate).
* Commit per map version; don't push `refs/` or the rotation-guide PDF.

### Git workflow — keep GitHub up to date, one branch per map `[USER]` (2026-11-10)
The owner wants every Claude session (claude.ai and Claude Code) to keep `https://github.com/shywolf91/Aos_Map`
current at all times. This is standing permission to pull, branch, commit and push for map work.
1. **Before any map work:** `git checkout main && git pull`. Never start from a stale tree.
2. **One branch per map:** `git checkout -b map/<map-slug>` (e.g. `map/under-the-tree`). A new version of an
   existing map gets its own branch too (`map/<map-slug>-v2`). Non-map work (toolchain, docs, setup) uses
   `tooling/<topic>` or `docs/<topic>`.
3. **Commit as you go** — at least after the graybox, after the art pass, and at release — and **push the branch
   after each commit** (`git push -u origin map/<map-slug>`), so the work is never only on one machine.
4. **When the map is released**, open a PR into `main`, then update the §9 catalogue, `docs/<map>_spec.md`,
   `docs/knowledge/project_memory.md` and `docs/knowledge/map_sources.md` on the same branch.
   Merge only when the owner says so.
5. Large build artefacts (`*.npy`) and `refs/` stay git-ignored. If a file is over ~50 MB, ask before committing it.
6. If a push fails (auth, rejected), say so plainly and leave the work committed locally; never force-push `main`.
