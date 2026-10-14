# Drowned Cathedral — Halloween Babel (2026-10-14)

> **v2 (rotated redesign after playtest feedback) is in `docs/drowned_cathedral_v2_spec.md`.** This page documents v1.

**Status:** specified · generated · exported · parser-validated · **server-loaded** (live Babel, piqueserver 1.4.2,
stock script list, blue/red) · **not** client-inspected in BetterSpades/OpenSpades/aos_web · **not** playtested.

Generator: `scenes/drowned_cathedral.py` (seed 1414) + prefabs `scenes/drowned_cathedral_props.py`.
Check: `scenes/drowned_cathedral_check.py`. Map files: `maps/drowned_cathedral_v1/`. Server config:
`server_test/dc_babel/config.toml`. Previews: `docs/img/drowned_cathedral/` (first-person views from the new
`tools/fp_view.py` ray marcher — an approximation, not a client capture).
SHA-256 of the VXL: `7ea2e5ce…f344a0` (3.67 MB). Same bytes under another PYTHONHASHSEED and on Python 3.11 / 3.13.

## Concept
A gothic cathedral has sunk into a fen at dusk. The old town around it drowned with it: half-sunk houses with lit
windows, cypress groves hung with moss, lily pads, stone causeways. Each team spawns in a chapel precinct on the
old quay and builds its Babel tower from a stone mole (pier) that juts out over the fen toward the platform. The
cathedral's surviving crossing tower (the bell tower) rises from the water beneath the centre of the platform.

## Babel rules applied (piqueserver 1.4.2 `babel_script.py`, read 2026-10-14)
* Platform x 206–305, y 240–271, z 1 (script-generated, protected); z ≤ 2 kept empty above it (checked: 0 voxels).
* Bases fixed at (118, 256) / (394, 256); spawns random ±20 on the topmost voxel → the spawn squares are flat z 40
  paving with nothing on them (checked: 0 columns off z 40).
* Destroy rule: blue may destroy only while standing at x > 288, red only at x < 224 → **in the centre band
  x 224–288 nobody can remove blocks**. Consequence: anything players place inside the cathedral is permanent, so
  the bell tower has two mirrored stair cores (one per side) and wide (3–5) flights.
* Build rule: a team can't build while standing in the enemy's protected corridor (x 128–211 / 301–384, y 240–272)
  — that is exactly each team's esplanade, so towers grow from your own mole.

## Layout (west half authored, mirrored x' = 512 − x; occupancy mirror exact except the sky sign)
| element | where | notes |
|---|---|---|
| spawn square | x 98–138, y 236–276, z 40 | ring-paved, clear; blue/red banners on the gatehouse (outside) |
| precinct | x 84–148, y 190–322 | chapel (N), ossuary with skull shelves (S), graveyard (W), hanging tree, calvary, well, pumpkin patch |
| cover screen | arcade x 141–143 + gatehouse x 140–144, y 226–286, top z 31 / 24 | 6 arches + 9-wide gate: cover from platform snipers, many exits |
| tower zone | x 148–205, y 228–284, z 40 (mirror 307–364) | open flagstones outlined by a dark band; **no props** |
| mole | x 151–205, y 212–300, top z 40 | 22-voxel masonry quays on three sides: pilasters, cornice, ivy, iron rings; parapet + lanterns outside the zone |
| quay stairs | x 160–179, y 213–216 (N) / 296–299 (S) | 1-voxel risers, balustrade, landing at z 59 |
| fen | ellipse semi-axes 150 × 196 round (256, 256) | water (z 62 air, wading), mud hummocks, 34 drowned houses, ~900 cypress, lilies, reeds |
| causeways (z 59) | quay foot x 206–210; spurs to the aisle doors (y 188 / 324) and transept door; axis causeways N/S with lychgates | dry routes; the fen itself is walkable water |
| cathedral | nave along y on x = 256: façade towers + rose y 136–151, nave 152–243, transepts x 214–297 / y 236–275, crossing tower x 244–268 / y 244–267, choir 268–329, apse r 24 | flying buttresses, ruined clerestory, stained glass, flooded aisles, checker floors |
| bell tower | walls to z 23, merlons z 22, pinnacles to z 18; belfry floor **z 32** | twin stair cores (58 → 32, ~29 risers), bell hung from a beam, clock face stopped at midnight on the E/W faces, gargoyles |
| signature | sky plate z 4–5 over the bottom-right corner (x 321–508, y 486–508) | "Drowned Cathedral / Designed by shywolf91 and AI" + jack-o'-lantern emblem painted on top of a 2-voxel dark plate (plain underside), held by one hidden stalk; forest underneath left as generated (`signature.mode = 'sky'`, `clear = False`; 'ground'/'raised' still available); built-in 5×7 font `aosmap/pixelfont.py` |
| fog | (152, 174, 168) | bright slate-green tint — user rule from testing: fog channels ≥ 150 or maps look too dark (night maps get a bright tint); still tinted, not white |

## Validation (2026-10-14; route model preliminary — 3-voxel standing clearance, 1-voxel auto-step, 2-voxel jumps)
* Reader OK; **pyspades `VXLData` load → `generate()` is byte-identical**; piqueserver `Map` loads the `.vxl` + `.txt`
  (extensions `babel`, `water_damage`). Floating components: **0** (48 tiny ruin orphans pruned at build).
* Platform not reachable without building (both teams). Build gaps: **39** from your own esplanade edge;
  **30** from the bell tower (the string-course ledge outside the belfry lancets, z 31; belfry floor 31).
  Nearest authored voxel to the platform: 17 (a pinnacle finial, z 18 — only reachable by building).
* Route parity (team1 vs team2): **0.0** on every target. From spawn: esplanade edge 66 · stair landing 60 ·
  transept door 103 · crossing floor 137 · belfry 188 · portal 184 · enemy esplanade 319 · enemy spawn 323.
* Spawn exposure (platform-edge eyes → spawn heads, fog ignored): 62.8 / 62.4 % exposed, **3.8 / 3.5 viewers per
  spot**, 24° depression, **37 % of spawn spots hidden** (targets: ≤ 10 viewers, ≥ 15 % hidden — better than every
  calibrated reference map).
* **Live** (headless piqueserver 1.4.2, babel + babel_script, blue/red): fog (152, 174, 168) (re-checked live after the change); intel (256, 256, 1);
  bases z 40; the client receives 3,200 platform cells and the downloaded map differs from the file only there;
  bot spawns all on the precinct squares (eye z 37.6).
* Art metrics: 8,210 colours, 4 hue families, coherence 1.35 (just below the 1.4–2.5 reference band — foliage and
  grass noise), per-material side − top: stone −14…−20, quay −17, foliage −21. The global side − top (−4.4) is a
  material-mix artefact: tops are mostly dark grass, sides mostly pale stone.

## Risks / things to watch in playtests
* **Bell tower race:** the centre is a 30-block build vs 39 from the esplanade, but it costs a 188-voxel walk
  (stairs into the fen, causeway, cathedral, 29 risers) and is open to both teams. Expect fights in the belfry; if
  rounds end too fast, lower the belfry floor (`tower.belfry_floor`) or remove the outer string-course ledge.
* **Griefing in the centre:** nobody can remove blocks in x 224–288 (stock script). Two stair cores make a full
  seal harder, not impossible.
* **Fen falls:** the quays are 22 high — a fall is lethal (≥ 20). Stairs and causeways are the intended routes.
* **No spawn hooks in the `.txt`** (user rule: no AI-authored spawn coordinates). Spawns come from the game mode: stock
  babel_script bases 256 ∓ 138 / y 256, ±20 on the topmost voxel. Re-tested live: 12 default spawns (6 per team) all
  landed on the flat z 40 squares (x 98–138 / 374–414, y 236–276). Add hooks by hand after review if a server needs them.
* Not yet seen in a real client: check the fog brightness/tint, stained-glass readability and the clock face in
  BetterSpades/OpenSpades, and the platform's cyan against the fog.

## Make it yourself
```powershell
.\venv\Scripts\python scenes\drowned_cathedral.py out\drowned_cathedral          # ~10 s
.\venv\Scripts\python scenes\drowned_cathedral_check.py out\drowned_cathedral    # routes, gaps, exposure, floating
.\venv\Scripts\python tools\fp_view.py out\drowned_cathedral\drowned_cathedral.vxl out\view.png 112 256 37.6 230 256 14 --babel
```
Server: copy `drowned_cathedral.vxl` + `.txt` into the server's `maps/`, add `"drowned_cathedral"` to `rotation`,
`game_mode = "piqueserver.game_modes.babel"` and `piqueserver.scripts.babel_script` in `scripts`
(see `server_test/dc_babel/config.toml`). Rotation admins: platform type normal, cap limit as usual.

## Sky-level map info (2026-10-14) — now the main build
The main map now uses this configuration. `maps/drowned_cathedral_v1_skytag/` holds the earlier test build (before the
south-edge forest fix below), kept for reference.

### South-edge forest fix
The tree grid started at y 1 but stopped at y 502, and the last rows sat under earlier crowns, so the south edge was
bare next to the north (tree cover 0.34 vs 0.47 in the outer 20 rows). A gap-only infill pass along y 491–507 brings
it to 0.48 vs 0.47; every existing tree is unchanged.

### Test variant notes
`maps/drowned_cathedral_v1_skytag/drowned_cathedral_skytag.vxl` (+ `.txt`), built by `scenes/drowned_cathedral_skytag.py`
(same seed and geometry; `signature.mode = 'sky'`, `clear = False`, `sky_z = 4`).
* The forest under the tag is untouched. The tag is painted on a 2-voxel plate at z 4–5 over x 321–508, y 486–508
  (plain dark underside, so no mirrored lettering from below), held by one hidden stalk down to the ground → 0 floating.
* Validation: reader OK, pyspades load/re-save byte-identical, piqueserver Map load OK, **live Babel load OK** (fog, platform
  3,200 cells, spawns on the squares), routes/parity/build gaps/spawn exposure identical to the main map. The halves differ
  only by the plate.
* Renders: `docs/img/drowned_cathedral_skytag/`. If the stalk is cut (destructible terrain) the plate falls — it's in the
  forest corner, outside the play space.
