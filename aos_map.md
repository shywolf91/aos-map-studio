# aos_map.md — Ace of Spades 0.75 map-making knowledge base

Consolidated 2026-10-13 from the aosmap project (research, exporter, validators, Kestrel Spires).
Last updated 2026-10-13 (Kestrel art v2, Hollowfen Halloween Babel+CTF map, BetterSpades inspection, fog findings).
Target: classic AoS **0.75** clients (OpenSpades, BetterSpades, vanilla) + **piqueserver 1.4.2**
(pyspades), Python 3.11. Detailed per-topic docs live in `docs/`; this file is the single place to start.

**Evidence tags** — every rule below is marked:
`[SRC]` read in source code · `[RUN]` observed by running real code (pyspades/piqueserver, our tools, a live
server) · `[DERIVED]` computed from source equations, not playtested · `[USER]` your stated decision ·
`[DESIGN]` our design guideline (judgement, not fact) · `[OPEN]` not yet verified.

Status ladder used for every map: researched → specified → generated → exported → parser-validated →
server-loaded → client-inspected → playtested. Never skip a rung when reporting.

---

## 1. Cheat sheet

| Thing | Value |
|---|---|
| Map size | 512 × 512 columns × 64 voxels; x, y 0..511; z 0..63 |
| Vertical axis | **z = 0 is the top of the sky, z = 63 the bottom.** "Height" = 63 − z |
| Water | a column whose z = 62 is air is open water; z = 63 is always the water surface voxel |
| Unbuildable / indestructible | everything at z ≥ 62 |
| Grounded | 6-face connected to any solid voxel with z ≥ 62 (edges/diagonals don't count) |
| Player | 0.9 × 0.9 footprint; needs 3 air voxels standing, 2 crouched; auto-steps 1 voxel |
| Jump / fall | jump apex ~1.6 voxels; fall damage from ~10, lethal at ~20 `[DERIVED]` |
| Spawn hook z | return the floor voxel's z; the server places the eye 2.4 above (z − 2.4) |
| Colour | 0xAARRGGBB little-endian (bytes B, G, R, A); A = cosmetic shade byte, write 0x80 |
| Metadata | `<mapname>.txt` next to `<mapname>.vxl`; it is Python executed by piqueserver |
| Babel platform (stock) | x 206–305, y 240–271, z 1, colour (0,255,255); intel (256,256); bases (118,256)/(394,256) |
| Your server | stock piqueserver, normal scripts, team1 Blue (0,0,255), team2 Red (255,0,0) `[USER]` |

---

## 2. The VXL file format

* No header. Columns are stored **y outer, x inner** (for y in 0..511: for x in 0..511). `[SRC]` pyspades vxl_c.cpp
* Each column is a list of **spans**. A span header is 4 bytes **N, S, E, A**:
  * N = length of this span in 4-byte units (header + colours); **N = 0 marks the last span** of the column.
  * S = first z of the top-colour run, E = last z of that run (**inclusive**). From this span's air start down to
    S − 1 is air; S..E are solid voxels whose E − S + 1 colours follow the header.
  * A = z where this span's air begins (unused in the first span). It also closes the *previous* span's
    bottom-colour run: that span's remaining K = N − 1 − (E − S + 1) colours belong to z = A − K .. A − 1.
  * Between a span's top run and its bottom run everything is **implicit solid** (hidden, colourless); in the last
    span everything below E down to 63 is solid.
* The pyspades writer emits **zero-length top runs (E = S − 1)** for buried caves; every pyspades server sends
  these to clients, so readers must accept them. `[SRC][RUN]`
* Surface rule (which voxels get colours stored): solid and (z == 0 or any in-map face neighbour is air).
  Out-of-map x/y and below z = 63 count as solid, so map-edge faces are not "surface". `[SRC]`
* Colour bytes: B, G, R, A. **A is cosmetic shade only**: pyspades writes 0x80 (`make_color`) or 127 − occlusion
  (`update_shadows`); OpenSpades replaces it with 100; BetterSpades/libvxl masks it off. `[SRC]`
* Hidden voxels have no colour after a pyspades load; `get_point()` reports (0,0,0) for them. `[SRC]`
  (This is why Arena gates must be ≤ 2 thick — see §7.)
* Quirks seen in real maps: "void columns" (whole column air including z = 63; 10yearsaloha) load fine in
  pyspades `[RUN]`; OpenSpades copies the z = 62 colour to z = 63 `[SRC]`; some editors store colours on hidden
  voxels (harmless).
* **Our writer (`aosmap/vxl.py write_vxl`) is byte-identical to pyspades `generate()`** on all 36 reference files
  (34 distinct maps), colours and shade byte included. `[RUN]` It forces z = 63 solid unless `force_bottom=False`.

## 3. Ground, collapse and water

* **Grounding** = 6-face path to a solid voxel with z ≥ 62. Same rule in pyspades `check_node`, OpenSpades
  `GameMapWrapper`, BetterSpades `map.c`. `[SRC]` A block touching only by an edge is floating `[RUN]`.
* **Collapse runs only around a destroyed voxel** (destroy_point → check_node on the 6 neighbours). There is no
  sweep at map load, so floating authored pieces sit there until someone breaks a block next to them. `[SRC]`
* **check_node ignores protection.** Destroying an allowed (player) block next to floating authored geometry
  drops the authored geometry too (diagnostic: 10 voxels incl. a 9-voxel protected slab). `[RUN]`
  → Grounding ≠ indestructible, and floating authored geometry is a griefing vector even on protected maps.
* **Floating authored pieces are opt-in** — only when the brief asks for them. `[USER]` When used, list them in
  `validate(expect_floating=...)` so they are reported as intended with a collapse-risk warning.
* Shipped maps float a lot (JunglePush 740 components, Shenlong 288, t_o_r_t_u_g_a 118k voxels). `[RUN]`
* Sky maps can stay grounded through hidden **tethers**: Cloud Smash hangs its whole 674k-voxel cloud level on four
  1–2-voxel stalks down to z 62. Cutting one removes 1 voxel; cutting all four drops the map. `[RUN]`
* Water: collision treats z = 63 as z = 62, so players stand on the seabed and "wade" when z > 61. `[SRC]`
  `water_damage` (map_extensions script) applies at position z ≥ 61; Push forces it to 100. `[SRC]`

## 4. Player movement (for route design and the route checker)

| Quantity | Value | Evidence |
|---|---|---|
| Footprint | 0.9 × 0.9 (±0.45) | world_c.cpp boxclipmove `[SRC]` |
| Standing clearance | 3 air voxels (~2.7 tall) | `[SRC]` |
| Crouched clearance | 2 air voxels | `[SRC]` |
| Auto step-up | 1 voxel; **not while sprinting or crouching**, not looking steeply down | `[SRC]` |
| Jump apex | ~1.6 voxels (so a 2-voxel ledge needs jump + step) | `[DERIVED]` |
| Fall damage | starts ~10 voxels, ≥ 100 dmg at ~20 voxels | `[DERIVED]` |

Practical rules `[DESIGN]`: stairs = 1-voxel risers; walkways ≥ 3 wide; ceilings ≥ 4 above walk surfaces where
you want people to jump; drops > 9 should be deliberate; lethal drops (≥ 20) are fine as cliff edges if a safe
descent exists. Jump/fall figures still need in-client confirmation (the diagnostic map has 1/2/3 ledges,
3/2 tunnels, 10/20 drops for exactly that). `[OPEN]`

## 5. Metadata — the `<map>.txt` file

piqueserver executes the file and reads these names (piqueserver/map.py `[SRC]`):
`name, version, author, description, extensions, apply_script, time_limit, cap_limit, gen_script,
get_spawn_location(connection), get_entity_location(team, entity_id), on_map_change, on_map_leave,
on_block_destroy(connection, x, y, z, mode), is_indestructable(protocol, x, y, z)`, plus `fog = (r, g, b)`
(server.py). Anything else is ignored.

* Entity ids: BLUE_FLAG 0, GREEN_FLAG 1, BLUE_BASE 2, GREEN_BASE 3; `connection.team.id` 0 = team1, 1 = team2. `[SRC]`
* A hook returning `None` falls back to default placement: a random **land** column (z 62 solid) in x 0–127
  (team1) / 384–511 (team2), y 128–383, at the topmost solid voxel — it can land on roofs. `[SRC]`
* **Entities settle**: after load and after every block change, flags/bases drop onto the topmost solid voxel of
  their column. A roof or overhang above an intel/base x,y will catch it. `[SRC][RUN]`
* `on_block_destroy`: any falsy return (including `None`) **denies** the destroy. `[SRC]`
* `extensions` only matters for keys some script reads. map_extensions reads `water_damage`,
  `boundary_damage {left,right,top,bottom,damage}`, `disabled_commands`. `user_blocks_only` inside extensions
  does nothing — it's a server config option. `[SRC]`
* Harness gotcha: map.py uses `importlib.util` without importing it; standalone test scripts must
  `import importlib.util` first or the `.txt` silently fails to load. A normal server is unaffected. `[RUN]`
* Generate it with `aosmap.meta.map_txt(...)`; lint with `check_map_txt(path)`.

Minimal Babel example (what Kestrel Spires ships):
```python
name = 'Kestrel Spires'
version = '0.1'
author = 'aosmap (art v1)'
description = 'Babel: build from your mesa spire to the sky platform.'
fog = (196, 170, 140)
extensions = {'babel': True, 'water_damage': 0}
# + optional get_spawn_location / get_entity_location hooks (CTF fallback; Babel replaces them)
```

## 6. Block protection

* **`user_blocks_only = true`** (server config.toml) exists in 1.4.2: only player-built blocks can be destroyed,
  by **anyone** (no team ownership). `[SRC][RUN]`
  * A grenade is cancelled entirely if any of its 27 voxels is protected; the spade also checks z ± 1, so spading a
    block lying on authored ground is refused. `[SRC][RUN]`
* **Your preferred policy** `[USER]`: authored map protected, players build, opponents can destroy player
  blocks. Implemented as **`server_scripts/authored_protect.py`** (load after babel_script). Live-tested with
  bots on 1.4.2 `[RUN]`:

| Action | stock `user_blocks_only` | `authored_protect` |
|---|---|---|
| shoot authored ground | refused | refused |
| red shoots blue's block | destroyed | destroyed |
| blue shoots own block | destroyed | destroyed (refused with `team_can_destroy_own = false`) |
| red spades blue's block standing on authored ground | refused | block removed, ground intact |
| grenade on blue's blocks next to authored ground | whole grenade cancelled | blocks removed, ground intact |

  Ownership is tracked by team in memory; partial removals are broadcast as individual DESTROY_BLOCK packets so
  clients stay in sync. Map extension `'authored_protect': False` disables it per map.
* Even fully protected maps can lose **floating** authored geometry through collapse (§3). Keep authored geometry
  grounded unless floating was requested.

## 7. Game modes (piqueserver 1.4.2)

Identify the exact script before designing; a mode's name doesn't define its rules.

### Babel — `game_mode = "piqueserver.game_modes.babel"` + `piqueserver.scripts.babel_script` `[SRC][RUN]`
* The **script builds the sky platform** at z 1, x 206–305, y 240–271, colour (0,255,255), protected. These are
  module constants — some servers modify shape/colour `[USER]`; treat them as parameters (`BABEL_DEFAULT`).
* **One intel** (onectf ONE_CTF) at `one_ctf_spawn_pos` (default 256,256; map extension overrides) on the
  platform. Carry it to **your own base**: (118,256) team1, (394,256) team2. cap_limit forced to 1 per round.
* Dropped off the platform → intel returns. Carrier is killed after 150 s (`allowed_intel_hold_time`).
* Spawns: random within ±20 of your base, at the topmost voxel.
* Anti-grief: can't build while standing near the enemy tower corridor (team1 x 301–384, team2 x 128–211,
  y 240–272); a team can destroy blocks only once past x 288 (team1) / below x 224 (team2) — i.e. not on its own half.
* **Map requirements**: leave z ≤ 2 free over the platform area; provide land at both base coordinates;
  near-identical spawn areas for both teams `[USER]`; platform must not be reachable without building.
* Note the stock asymmetry: platform is symmetric about x = 255.5, bases about x = 256 → mirror maps with
  x' = 512 − x and accept a 1-voxel build-gap difference.
* Styles in your references `[RUN]`: **sky babel** (abridgetoofar, tradeoff, anticbridgebabelv2 — decks at z 2–13
  around spawn) vs **ground babel** (alexandria-babel2, islandbabel, babelpocalypse). Build gap (closest walkable
  point → platform top): anticbridge 6, alexandria 5, tradeoff ~17, abridgetoofar ~54, islandbabel ~56.
* "Stairways/ledges/return-descent tower" Babel = **custom variant** unless a script supports it.

### Push — needs the push game mode script `[SRC][RUN]`
* Required extensions: `push_blue_spawn, push_green_spawn, push_blue_cp, push_green_cp` (server raises without
  them). Optional: `push_spawn_range` (5), `push_cp_protect_range` (8), `push_blue/green_build_area` (x1,y1,x2,y2).
* Your template `[USER]`:
  `{'push': True, 'push_spawn_range': 5, 'push_blue_spawn': (x,y,z), 'push_blue_cp': (x,y,z),
  'push_green_spawn': ..., 'push_green_cp': ..., 'water_damage': 100}` (`aosmap.validate.push_extensions`).
  `'push': True` is convention; 1.4.2 push.py doesn't read it (mode comes from `game_mode`).
* **Block ownership is by colour** (HLS hue + saturation of the team colours). Authored palettes must avoid team
  hue/saturation: with blue/red teams, no pure blues (r = g = 0) and no pure reds (g = b = 0). `check_push()` lints.
* Enemy intel is placed at your spawn x,y z 1 and settles — keep spawn and CP columns free of roofs.
* Bridge-building is the core challenge: don't author a free crossing.

### Arena `[SRC][RUN]`
* Extensions `arena_blue_spawns`, `arena_green_spawns`, `arena_gates` (one coord per gate), `arena_max_spawn_distance`.
* `BUILDING_ENABLED = False` — an arena with building is a requested variant (script change).
* Gates open by 6-face flood fill of **exact RGB**; hidden voxels read (0,0,0) → **gates ≤ 2 thick**; same-colour
  decoration touching a gate gets absorbed; keep gates < ~900 voxels (recursive fill). Round 180 s, 15 s break.

### CTF
Built in. Use `get_spawn_location` / `get_entity_location` hooks for authored layouts (defaults in §5).

### Hallway and other names
"hallway" is a map name in the default rotation, not a mode `[SRC]`. Treat Hallway and other community names
as layout briefs until a real script defines objective and rules.

## 8. Server setup that was tested

`server_test/kestrel/config.toml` (piqueserver 1.4.2, run with `piqueserver -d server_test/kestrel`):
```toml
name = "kestrel babel test"
port = 32921
game_mode = "piqueserver.game_modes.babel"
rotation = ["kestrel_spires"]
scripts = ["piqueserver.scripts.rollback", "piqueserver.scripts.protect",
           "piqueserver.scripts.map_extensions", "piqueserver.scripts.disco", "piqueserver.scripts.votekick",
           "piqueserver.scripts.trusted", "piqueserver.scripts.ratio", "piqueserver.scripts.passreload",
           "piqueserver.scripts.blockinfo", "piqueserver.scripts.squad", "piqueserver.scripts.afk",
           "piqueserver.scripts.babel_script", "authored_protect"]
[team1]
name = "Blue"
color = [0, 0, 255]
[team2]
name = "Red"
color = [255, 0, 0]
```
Put `<map>.vxl` + `<map>.txt` in `<config dir>/maps/`, custom scripts in `<config dir>/scripts/`.
`map_extensions` must be in the script list for `water_damage` to work.

## 9. Layout and balance guidelines `[DESIGN]`

* Symmetric team modes: author one half and **mirror** (x' = 512 − x for Babel; copy x 255 into 256 so the axis
  column isn't empty — a real bug we hit). Cosmetic asymmetry only where routes, heights, cover and exposure stay equal.
* Plan per team: protected spawn exits, primary + secondary routes, flanks, chokepoints, objective approach and
  escape, build opportunities, boundaries.
* Check for: required-construction bypasses, sealable objectives, spawn traps, support exploits, unreachable
  camping perches, ways out of the play space. Water, walls and cliffs don't stop people by themselves.
* Babel specifics: give each team a **bridgehead** (closest point to the platform) plus 1–2 secondary build
  points; a safe descent/return route; a way to reach and cut enemy towers from below (their half is where you
  may destroy). Build gaps of ~20–40 sit mid-reference.
* Props must never land on walk surfaces: keep a 4-voxel air keep-out above routes and a 2–3 column buffer.
* Foundations must not create unintended walkable shortcuts across water/gaps/climbs (we caught a decorative
  ledge that cut a descent from 280 to 125 walk cost).

## 10. Art direction knowledge

Your priorities: beauty/craft is the top artistic goal; a valid but crude VXL is a prototype, not a map. Use the
references (Shenlong, Jungle Push, tradeoff, normandie, alpine, abridgetoofar, remus, swag2…) for craft and
density **only** — never copy their objects, landmarks or terrain arrangements. `[USER]`

**Measured calibration** (`tools/art_metrics.py` on your references `[RUN]`):

| Metric | Reference range | Target |
|---|---|---|
| hue families covering 90 % of surface | 2–5 | 2–4 (restrained palette) |
| spatial coherence of top colour (ΔL at 4 voxels / ΔL at 1) | 1.4–2.5 (random per-voxel jitter = 1.0) | ≥ 1.5 — variation must be structured |
| side faces vs tops | −5 … −34 L* | −10 … −20 L* (hand-shaded depth) |
| shading style | flat painted (Shenlong: 184 colours, ~11 L* steps) or fine gradients (tradeoff/alpine: ~1–2 L* steps) | pick one per material |

**Techniques that work** `[RUN]`:
* Separate geometry from colour: author with **material ids** (`Scene`), colour at export with shaders.
* `StrataShader` — warped, slightly tilted horizontal bands for sedimentary rock; darker sides/undersides; crust
  on exposed tops. `SurfaceShader` — top/side/under ramps + height term + coherent noise + crevice darkening.
  `PatternShader` — designed patterns (paving rings).
* **Painted z = 63 backdrop** (`Scene.paint_bottom`): Cloud Smash paints a sunset into the water plane — 27,994
  of its 28,109 colours — while the playable structure uses 111. Huge visual payoff, zero gameplay cost.
* Silhouette first: tapers, necks/flares (hoodoos), curved arch undersides, relief motifs carved 1 voxel deep
  with a dark niche behind a pale figure — reads at gameplay distance.
* Vegetation in **groves** (cluster-gated), not even scatter; sage-style speckle reads as noise.
* Contrast dwellings/buildings against their rock (plaster vs sandstone) or they vanish.
* Avoid: random colour noise, scattered cubes, flat empty expanses, oversized primitives as landmarks,
  decoration that blocks movement or hides players unfairly. Treat "lighting" as colour/composition only.
* Patterned shaders on mirrored maps must fold x (x > 255 → 512 − x) or the second half shows a different
  pattern (Kestrel's red paving came out striped).

**Fog** `[RUN]` (BetterSpades, 2026-10-13): AoS fog is strong — past ~60 voxels everything blends toward the
fog colour, and silhouettes are what survive. Rules that came out of testing Kestrel live with `/fog r g b`:
* Don't match fog to the dominant material (tan fog + sandstone = landmarks dissolve). Pick a hue the palette
  doesn't use so silhouettes separate.
* Keep the fog hue roughly neutral between the two team colours (blue fog hides blue players more at range).
* Check the mode's objective still reads against it (Babel's cyan platform vs a blue fog).
* Fog is server-side (`fog` in the `.txt`, `/fog` live) — cheap to iterate without re-exporting the map.

## 11. The aosmap toolchain (this repo)

```
aosmap/vxl.py       read_vxl (strict, reports caves/void columns) · write_vxl (pyspades-identical) · load/save · rgb()
aosmap/scene.py     Scene(name, seed): material ids, box/carve/hollow_box/point (inclusive), markers,
                    paint_bottom, to_voxelmap()  ·  Material(name, base, jitter, top, depth_ramp, shader)
aosmap/art.py       value_noise/fbm, ramp, hex_rgb, SurfaceShader, StrataShader, PatternShader, heightfield,
                    apply_heightfield, Prefab/stamp, tree, boulder, house, stairs
aosmap/validate.py  floating_components, validate(), check_babel, check_push, push_extensions,
                    push_team_colour_collisions, arena_gate_selection, spawn_check, settle_entity_z
aosmap/nav.py       preliminary route graph (3-air standing, step 1, jump 2, drops) · babel_route_check ·
                    ctf_route_parity · distances/path/zone_nodes
aosmap/meta.py      map_txt() / check_map_txt()
aosmap/render.py    top_down, isometric (4 views), contact_sheet
aosmap/pipeline.py  run_diagnostic: export → parser checks → real-piqueserver runtime checks → renders
scenes/             diagnostic, kit_showcase, babel_concepts, kestrel_spires (graybox), kestrel_spires_art, *_check
tools/              compare_refs, art_metrics, movement_sim, fetch_map_from_server, bot_protect_test,
                    babel_live_check, aosweb_capture.cjs, betterspades_capture.sh (+ betterspades_camfile.patch)
server_scripts/     authored_protect.py
```

**Making a map — workflow**
1. Requirements: mode + exact script, theme, features, references, player count, protection policy, symmetry.
2. Verify mode rules (§7) and server parameters (platform constants, team colours).
3. Concepts (usually three) → pick → **spatial spec** as a `SPEC` dict in the scene file (single source of truth).
4. **Graybox** with function colours; run the `_check` script (floating, mode checks, routes, parity, gaps).
5. **Art pass** in a separate scene file built on the graybox function; re-run every check; compare numbers.
6. Export `.vxl` + `.txt`, art metrics, renders (top-down, iso, close-ups), aos_web eye-level shots.
7. Load on a real piqueserver with the target mode (`tools/babel_live_check.py` for Babel).
8. Client inspection: `tools/betterspades_capture.sh` joins the server in real BetterSpades as a spectator and
   screenshots set camera positions (headless, Mesa software GL); try fogs live with `/fog`. Then OpenSpades,
   then playtest with people. Iterate.

**Commands** (venv with `requirements.txt`):
```
python -m pytest -q tests/
python scenes/kestrel_spires.py out/kestrel_spires            # graybox
python scenes/kestrel_spires_art.py out/kestrel_spires_art2   # art v2 (add --v1 for v1)
python scenes/kestrel_spires_check.py out/kestrel_spires_art  # validation.json
python tools/art_metrics.py out/metrics.json map1.vxl [map2.vxl ...]   # first arg is the OUTPUT json!
piqueserver -d server_test/kestrel                            # after copying the .vxl/.txt into its maps/
python tools/babel_live_check.py 32921
node tools/aosweb_capture.cjs map.vxl outdir views.json [http://127.0.0.1:8090]
```

## 12. Validation checklist

Automated (before any hand-off):
- [ ] strict reader OK; re-encode identical; bounds; z 63 solid
- [ ] 0 unintended floating components (requested ones listed in `expect_floating`)
- [ ] mode checks: `check_babel` / `check_push` / arena gate selection
- [ ] spawn clearance (floor + 3 air) and spawn-zone symmetry
- [ ] route reachability and team parity (`nav`), shortcut hunt, build gaps
- [ ] no team-colour clashes in authored palette
- [ ] entity settling (no roofs over intel/base/CP columns)
- [ ] art metrics within calibration; renders reviewed for floating props, blocked routes, noise
- [ ] canyon/ground perches: highest point reachable on foot near objectives/routes (Kestrel check)
- [ ] deterministic build: same seed → same bytes in a fresh process (no `hash()`, no unseeded RNG)
- [ ] `.txt` loads (`check_map_txt`), only real keys used

Live / in-game:
- [ ] server loads map + `.txt`, mode objects present (e.g. Babel platform 3,200 cells), fog colour
- [ ] spawns land where expected for both teams
- [ ] client inspection: colours, edges, landmarks at gameplay distance, landmark readability through fog
- [ ] movement: jumps, steps, crouch tunnels, fall damage, water exit
- [ ] objective pickup/return/capture/reset; build/dig/grenade permissions; protection script behaviour
- [ ] camping spots, spawn pressure, performance at real player counts

Route checks are preliminary (no real collision sim); never present them as proof of playability.

## 13. Kestrel Spires — current state

Sky-Babel, sandstone mesas over a canyon river. Generators: `scenes/kestrel_spires.py` (graybox, `SPEC`),
`scenes/kestrel_spires_art.py` (art; `build(version=2)` default, `--v1` for v1) + `scenes/kestrel_spires_v2.py`.
Seed 7317. Spec and numbers: `docs/kestrel_spires_spec.md`. Map files: `maps/kestrel_spires_art_v2/`.

* Status (art v2): generated · exported · parser-validated · server-loaded on live Babel · **client-inspected in
  BetterSpades** · **not** inspected in OpenSpades · **not** playtested.
* Spawn decks z 10 (±20 square fully flat), sentinel spire bridgehead (gap 25), two hoodoo flank fingers (gap ~40),
  slot stair descent, canyon floor z 56 with dry washes, slickrock benches and river fins, water_damage 0.
* Routes identical for both teams; platform unreachable without building; 0 floating components; highest
  walkable canyon point 4 above the floor.
* Fog: lilac dusk (200, 188, 206) since v2 (v1 used tan (196, 170, 140)).
* Next: OpenSpades look, playtest.

## 13b. Hollowfen — Halloween Babel + CTF (2026-10-13)

Haunted fen village at dusk, full 512 × 512, classic destructible terrain solid to the bottom. Generators:
`scenes/hollowfen.py` (shared layout + graybox), `hollowfen_art.py`, `hollowfen_props.py`, check `hollowfen_check.py`.
Spec: `docs/hollowfen_spec.md`. Map files: `maps/hollowfen_art_v1/`.
* Status: generated · exported · parser-validated · server-loaded in **Babel and CTF** · client-inspected in
  BetterSpades · not in OpenSpades · not playtested.
* One layout serves both modes: village squares = Babel spawn zones = CTF spawns + tents (118/394, 256); church
  belfry decks = Babel bridgeheads (gap 33.6); CTF intel on each village's pumpkin farm; neutral cemetery midfield
  under the platform; bog boardwalks as flank loops. Mirror parity 0.0.
* Witches are requested floating scenery, placed after mirroring; the check counts them and flags anything else.

**Dual-mode layout pattern** `[DESIGN]`: put the CTF tents on the Babel base coordinates and the CTF spawn hooks on
the Babel ±20 spawn squares, so both modes share one balanced spawn; keep those squares flat and prop-free; give
each side its own bridgehead inside its own Babel corridor (y 240–272, between its base and the platform) so the
babel_script anti-grief zones protect it.

## 14. Gotchas we hit (so you don't)

* `tools/art_metrics.py`'s first argument is the output JSON — passing a .vxl first overwrites it.
* Mirror first, then place free-standing scenery (witches) — anything placed before `mirror()` is duplicated.
* Decor scatter (reeds, roadside pumpkins) must test the surface it lands on: reeds landed on boardwalks and a
  pumpkin landed on a CTF intel spot. Keep objective columns and walkways in an explicit no-prop mask and check them.
* Never seed noise with Python's `hash()` — it's randomised per process, so builds stop being reproducible
  (art v1 shipped with this; `tests/test_determinism.py` now guards it). Use `zlib.crc32`.
* Mirroring with `mat[257:] = mat[1:256][::-1]` leaves column 256 empty → copy 255 into 256.
* Trees placed with diagonal trunk shifts lost their crowns to collapse → enforce face contact.
* Carving door openings removed the wall under roof beams → 8 floating vigas; place attachments only where the
  host voxel survives, then re-run `floating_components`.
* Push intel and CTF bases settle onto roofs; check `settle_entity_z`.
* Arena gates thicker than 2 never fully open.
* `on_block_destroy` returning `None` denies everything.
* Bot clients must hold the trigger (WeaponInput) for weapon block damage to register.
* aos_web in headless software WebGL is slow on detailed maps (~3–8 min per capture batch); keep render
  distance modest and release the bridge session (limit 4).

## 15. Open questions `[OPEN]`

1. In-client confirmation of jump height, step-up, crouch tunnels and fall damage (diagnostic course) —
   needs a controlled player, not the spectator capture.
2. How Kestrel reads in OpenSpades (BetterSpades done 2026-10-13).
3. Whether your live server's babel_script platform differs from stock (shape/colour/z).
4. Hallway / custom modes: need their actual scripts before designing to them.
5. Arena-with-building and the custom Babel stair/descent variant: need script changes, not just maps.

## 16. Sources and versions

* piqueserver / pyspades **1.4.2** (tag v1.4.2, commit e555d210, 2026-07-08): pyspades/vxl_c.cpp, vxl.pyx,
  world_c.cpp, player.py, server.py; piqueserver/map.py, server.py, player.py, game_modes/{babel,push,arena}.py,
  scripts/{babel_script,map_extensions,onectf}.py.
* OpenSpades master ff9b3e7 (2024-06-02): GameMap.cpp, GameMapWrapper. BetterSpades master a695aaa (2025-07-30)
  + libvxl.
* D-VXLMapPreview (rakiru) master, built with LDC 1.8.0 + dlib 0.7.1 — independent decode check.
* BetterSpades master a695aaa built locally (GLFW, sound off, Mesa llvmpipe under Xvfb) for real-client views.
* Your 36 reference VXLs + Cloud Smash `.txt`; your aos_web Ruby client.
* Tested environment: Python 3.11.17, numpy 2.4.6, scipy 1.17.1, pillow 10.4.0, pyenet 1.3.17, Twisted 26.4.0.
