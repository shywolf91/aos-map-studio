# Brimstone Atoll — Halloween Island Babel (v1.3)

**v1.3 (2026-10-16):** scattered islands cut to **6 in total**, evenly spread: a witch's-hut isle in the NW/NE corners, a crypt-ruin
isle in the SW/SE corners (mirror pairs), a standing-stone circle on the north edge and a sea-stack rock on the south edge
(both on the centre line). The old gallows and lighthouse rocks were removed to keep the count.

**v1.2 (2026-10-16):** corner tag reduced to just the map name, at 2× scale (v1.2 also had 15 islets, cut in v1.3).

**v1.1 (2026-10-15):** each team now has a **tower-anchor shelf** — flat ground at z 42, solid to the seabed,
directly under its end of the platform, so towers can be anchored to ground in front instead of hanging off the skull.
The skull's back door was narrowed to one lane to close a straight sightline through the skull into spawn (see below).

Haunted basalt archipelago: two cemetery islands with a gothic mausoleum screen and a giant hollow
skull bridgehead each, two fossil-ribcage crescents to the north and south, a ruined chapel behind each
spawn, six small themed islands in the outer sea, and a swamp sea. Mirrored `x' = 512 − x`.

**Status:** generated · exported · parser-validated (own reader + pyspades 1.4.2) · server-loaded
(piqueserver 1.4.2, `game_modes.babel` + `babel_script`) · **not** client-inspected · **not** playtested.
Screenshots here come from a numpy ray-caster preview, not a game client.

## Install
Copy `brimstone_atoll.vxl` + `brimstone_atoll.txt` into your server's `maps/`, add `"brimstone_atoll"` to
`rotation`. Tested config:
```toml
game_mode = "piqueserver.game_modes.babel"
scripts = ["piqueserver.scripts.map_extensions", "piqueserver.scripts.babel_script"]  # plus your usual list
```
`.txt` has no spawn/entity hooks on purpose (stock babel_script replaces them; your standing rule).

## Layout (team 1 / west; team 2 is the mirror)
| element | where | heights |
|---|---|---|
| spawn court (cobble cemetery deck) | x 94–142, y 232–280; stock ±20 box x 98–138, y 236–276 fully flat | z 42 |
| court exits | north gate x 112–124 (13 wide), south gate (same), crypt portal through the mausoleum y 250–262 (13 wide) | low 2-high cemetery wall elsewhere |
| mausoleum screen | core x 143–155, y 238–274; wings x 144–148, y 214–298; end towers; belfry spire tip z 8 | roof ridge z 20 |
| skull bridgehead | centre (170, 256); internal 3-flight switchback stair (1-voxel risers), doors: crypt (back, lane A only, y 250–253), mouth (east), north, south | crown court floor z 20, 2-high rim to z 18 |
| **tower-anchor shelf** | spur from the promontory, x 178–211, tapering y 230–282 → 238–274; ground under the platform at **x 206–211, y 240–271** (team 2: x 301–305, the stock platform is centred on 255.5); flagstone causeway from the skull mouth, anchor apron x 203–211, bone line on the ground under the platform edge (x 206 / 305), lantern posts at the apron corners | flat z 42, solid to z 63; columnar cliffs, basalt skirt z 54/58/61 |
| inner slot stairs | promontory (184,232)→shore and (184,280)→shore, cheek walls, lantern posts | z 42 → 61 |
| other slot stairs | north/south lawns, NW/SW lobes, west shore; 3 per crescent side | → 61 |
| ribcage crescents | arc centre (256, 169) R 62, apex y ≈ 93–131; south = y-mirror | ridge z 38, horn plateaus z 30 (guard rail to z 28), rib apexes z ≈ 28 |
| chapel ruin | hill top (58, 256) | floor z 34, spire tip z 4 |
| scattered islands (6 total) | witch's hut on stilts with cauldron (70, 70) + mirror (442, 70) · crypt ruin with sarcophagus (72, 440) + mirror (440, 440) · standing-stone circle (256, 32) · sea-stack rock (256, 480) | ground z 52–57, 1-voxel hex-basalt terraces from the beach; stacks to z ≈ 41 |
| name tag | "BRIMSTONE ATOLL" painted on the sea floor, SW corner, x 10–187, y 492–505 | z 63 |

## Validation (automated; `validation.json` has everything)
| check | result |
|---|---|
| own reader round trip (solid, stored = surface, colours) | identical |
| pyspades 1.4.2 load → `generate()` | byte-identical re-encode; 0/20 000 colour and solid mismatches |
| floating components (6-face to z ≥ 62) | **0** (whole map is one component) |
| pyspades `destroy_point` probes (crown rim, rib apex, twig, spire finial) | 1 voxel each, no cascade |
| mirror | solid and materials identical (tag excepted) |
| platform | z ≤ 2 clear (0 authored voxels, confirmed with the piqueserver map loader); the channel between the shelves (x 212–300) clear |
| anchor ground | team 1: x 206–211 (6 columns × y 240–271), team 2: x 301–305 (5 columns), every column top z 42 and solid to the bottom; both reachable from spawn on foot with safe drops only (97 / 98 steps) |
| spawn squares | both flat at z 42, nothing above; bases settle at z 42, intel at z 1 |
| server | piqueserver 1.4.2 Babel: map + `.txt` loaded; platform stamp fills 3 200 empty cells |
| route check (preliminary graph, not a collision sim) | base → crown 85 steps both teams, safe drops only; crown → base safe; channel water → base safe; base → horn 442 both |
| build gaps | crown court 35.5 (30 horizontal, 19 up); rim top z 18 is ~27 from the edge; horns 52 |
| spawn exposure (method calibrated on normandie/tradeoff/swag2) | 0 % of spawn spots visible from the platform, the enemy crown or the horns |
| ground sightlines into spawn, within 128 blocks, from enemy-reachable spots | own shelf + mouth front 0 %, channel water 0 %, enemy shelf/deck 0 %, scattered islands 0 %, north crescent ridge 15 % (≈3.6 viewers per spot, ~100 blocks away) |
| scattered islands | all 6 separate landmasses, each ≥ 208 from the platform; islet ground climbable from the water with 1-voxel steps (only sea-stack pillars, the cauldron rim and the space under the stilted hut are unreachable, by design) |
| shoreline | 65 % of shore water cells step straight onto land; the rest are cliffs beside beaches |
| glow share | 0.9 % of land surface (limit 5 %) |
| deterministic | fresh-process rebuild: same SHA-256 (v1.3 `2ff79e69…`) |

## Tower-anchor shelf notes (v1.1)
* **Why the tip stops at x 211 / 301:** babel_script refuses building to team 2 while standing at x 128–211 and to
  team 1 at x 301–384 (`get_protected_area`, source read). Ending each shelf exactly there means an enemy standing
  anywhere on your shelf can't build. One more column would put the tip outside that zone.
* **6 vs 5 columns:** the map mirrors on x = 256 (like the bases and the build-ban zones) but the stock platform
  spans x 206–305 (centre 255.5), so team 1 gets 6 columns of ground under the platform and team 2 gets 5.
  Making them equal would break either the mirror or the build-ban alignment; flag it if you'd rather have equal.
* Build gap from the shelf is straight up: 41 blocks from z 42 to the platform top (z ≤ 2 is no-build directly
  under the platform, so towers go up beside the edge at x ≤ 204 / ≥ 307 or under it to z 3).
  The skull crown (gap ~35) is still the shortest bridge.
* Your brief asked to keep the water channel under the platform clear; this change puts ground under its two ends.
  Intel reset is unaffected (`on_flag_drop` resets any off-platform drop).
* Sightline fix: with the shelf in front of the skull mouth, a line ran mouth → skull lane B → back door →
  crypt passage → spawn court. The back door now opens into lane A only (4 wide, 4 high); the stair mass and
  spine wall block every such line (0 % measured). Crypt → skull → north/south doors and lane B → mouth stay walkable.

## Flags against the brief (decisions taken)
1. Skull crown at z 18 alone can't block platform→spawn lines (they pass ~2 above it); the mausoleum roof does — measured 0 % exposed.
2. Crescents "centred near y 110" vs "~40 from the platform": arc apex y ≈ 110, horns curl to 44 horizontal / 52 3-D.
3. Intel reset doesn't depend on the channel: `on_flag_drop` resets any drop below z 0 or off the platform rectangle.
4. Carriers can't drop from the platform: fall damage starts ~10, ≥100 at ~20 (derived). Descents are the built tower → crown → skull stair; step-down ledges run deck → sea.
5. Fog (70, 150, 80) shipped as requested; `(150, 196, 150)` is commented in the `.txt` (`fog_compare.png`).
6. `'babel': True` is ignored in stock 1.4.2 (`ALWAYS_ENABLED = True`); `water_damage: 0` needs `map_extensions` loaded — both harmless.

## Known limitations / next tests
* Not seen in BetterSpades/OpenSpades/aos_web yet; fog, the swamp floor paint and the tag need a client look.
* Enemies who invade your island can stand on your shelf and shoot at your tower from below (destroy rule lets team 2 destroy while standing at x < 224) — normal Babel tower defence.
* Route graph models step-up 1 / drops only, no building — confirm the skull stair and slot stairs in game.
* Chapel hill overlooks the spawn (it's behind it, inside your base); the enemy can stand there only by crossing your island.
* Falling off a rib into the sea from ~30 high is likely lethal (water isn't verified to cushion falls).
* Central apex of each crescent has no inner rib (ribs that would cross the mirror axis are skipped).
* Protection is server policy: use `user_blocks_only` or your `authored_protect` script; the map is fully grounded, so collapse griefing of authored geometry isn't possible.

## Regenerate
`python3.11 build.py OUTDIR` (numpy, scipy, pillow; piqueserver 1.4.2 optional for the pyspades round trip). Seed 3110 in `ba_gen.py`.
Files: `ba_core.py` (noise, volume, VXL writer/reader), `ba_gen.py` (geometry, `SPEC`), `ba_shade.py` (palettes),
`ba_validate.py` (checks), `ba_render.py` + `renders.py` (previews), `build.py` (pipeline).
