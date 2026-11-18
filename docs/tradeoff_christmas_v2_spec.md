# Tradeoff Christmas v2.0 — spec

Second Christmas version of **Tradeoff** by ei8htx / aloha.pk (v1 kept in `maps/tradeoff_christmas_v1/`, spec
`docs/tradeoff_christmas_spec.md`). Built 2026-11-18 from the owner's feedback: v1 put props on the outer floor, but that
floor is **deadly water** (`water_damage` 25). v2 keeps the water, adds one giant tree in the middle and puts the sky decor
in the outer regions. Inspiration (craft only): the owner's other version `trademas` (topographic snow roofs, ornaments on
the web strands).

**Status ladder:** generated → exported → parser-validated (own reader, pyspades 1.4.2 `generate()` byte-identical, `.txt`
loads with the original hooks). **Not** server-loaded, **not** client-inspected, **not** playtested. Renders are numpy previews.

## Owner decisions `[USER]` (2026-11-18)
* Keep deadly water; no props in the outer regions; sky decor in the outer regions.
* Giant Christmas tree in the middle: "mixture of landmark/below reach and assist". Blue and red towers as before.
* Icy deadly water; keep the original .txt hooks and extensions (water_damage 25, babel, orange heavens/fog, spawn rects, bases).

## Original map `[DERIVED]`
Flat water floor (only z = 63 solid, orange, water_damage 25), two hollow 61-high towers (roof z = 2, floors every 8, 12 shafts),
spawn rects on the tower ends (x 108–128 and 384–404, y 246–266), bases at (118, 256) / (394, 256), Babel flag set. The
"spider web": 10 thin bars at z 9–12 reaching out from the inner curves. The stock Babel platform (z = 1, x 206–305,
y 240–271) hangs over the water gap; nothing original is solid in its volume.

## What changed
| area | change |
|---|---|
| Tower geometry | **none**; only added voxels in the tower footprint: 224 roof-edge fairy-light bulbs (z = 1, none in the spawn rects or near the platform) and 10 hanging baubles under the web tips |
| Tower outer walls | team colour with snow ledges and three rows of garland swags (pine green, coloured bulbs, red bows with gold knots) |
| Roofs | team-tinted snow with topographic contour lines; candy-striped edge ring |
| Web strands | red/white candy canes with a big bauble hanging from each tip |
| Water | cold teal with ripple lines (luma median 107, min 80); still reads as deadly water, no ice floes (they would mislead players) |
| Centre landmark | giant tree on a seabed island at (256, 256): island r 22 (snow top z = 60, step rings z = 61 dry / z = 62 wet), tree 44 high (star at z 12), tinsel / baubles / berries, 7 gift boxes, 3-wide candy-ribbon staircase (23 steps, 1 up per step) to a gold landing |
| Sky decor (outer water only) | flying sleigh + 4 reindeer, 8 snow-cloud islands (trees, gifts, baubles), 10 snowflakes; z 6–44 |
| Glow | 337 sources, 27583 lit voxels baked; no white sources (dense white washes colours out) |
| Corner tag | "Tradeoff / Christmas" painted on the water floor, bottom-right, no credit line |
| `.txt` | original hooks, `water_damage` 25, `babel` (fog and heavens changed, see Night mood), kept verbatim (not AI-authored); name, version and author (`shywolf91 + AI`) changed, credit to ei8htx in the description; glow keys added |

## Centre tree as assist (Babel `[DESIGN]`)
It stands in the neutral zone (x 206–305, where both teams may build). Build gap to the platform underside (z = 2):
**stair top 35 blocks**, **tree top 10 blocks**; the star is not a standing
spot. Reaching the island means crossing about 30 voxels of deadly water from either tower (mirror symmetric, equal for both
teams). That saves a lot over building from the water floor (about 60), so treat it as a light assist and shorten the tree if
it proves too strong.

## Validation `[RUN]`
| check | result |
|---|---|
| strict reader / re-encode / pyspades generate identical | OK / identical / True |
| z = 63 solid; original voxels removed in the footprint | True / 0 |
| footprint changes outside bulbs + tip baubles | 0 |
| new solid in platform volume (x 196–315, y 230–281, z 0–3) / in spawn rects | 0 / 0 |
| props on the outer water (z ≥ 50, outside the island) | 0 |
| floating components | 21 (all listed sky pieces; unexpected 0); the original has 0 |
| staircase walk (step ≤ 1) from the island edge | reaches feet z 36 (landing) |
| `.txt` loads (3.11 venv, original hooks present) | yes |

Expected floating (collapse caveat: breaking a player block next to one drops it for the round): sleigh + reindeer, 8 clouds,
10 snowflakes (boxes in `build.json`), all over open water.

## Known limits / not tested
* No live server, no client; water damage rate, glow look and FPS unmeasured. Spawn exposure not measured (spawn rects unchanged).
* Assumes water damage applies at player z ≥ 61: the island top (z = 60) should be dry, the outer step ring (z = 62) is wet.
* The platform checks only cover our additions; the stock script builds the platform.
* Cloud-island tree details are non-deterministic by rule; seed `20261119` rebuilds this exact map.

## Regenerate
```bash
python scenes/tradeoff_christmas/tc2_build.py <tradeoff.vxl> <tradeoff.txt> maps/tradeoff_christmas_v2 --seed 20261119
<venv>/python scenes/tradeoff_christmas/tc2_check.py maps/tradeoff_christmas_v2/tradeoff_christmas.vxl <tradeoff.vxl> maps/tradeoff_christmas_v2/build.json maps/tradeoff_christmas_v2/validation.json
python scenes/tradeoff_christmas/tc_render.py maps/tradeoff_christmas_v2/tradeoff_christmas.vxl maps/tradeoff_christmas_v2/renders
```

## Night mood and glow (update 2026-11-18, owner request: icy winter night, show off the glow blocks)
* `fog = (172, 190, 242)` (icy periwinkle, bright per rule, hue not used elsewhere) and `heavens_color = (22, 30, 96, 255)`
  (deep night blue); the original orange fog/heavens (255, 200, 120) / (250, 130, 40) are replaced.
* Whole map graded cooler and darker (x 0.72 / 0.80 / 0.95 on R/G/B) so the lights pop; glow voxels are not graded.
  Water luma min 60, so nothing near-black.
* Glow sources now 692 (97918 lit voxels in the `.txt`): tree lights + star, every second tree
  ornament, 3 glow spots on each big web-tip bauble, sleigh (hull rim lights, front lanterns, harness bells, Rudolph's nose),
  cloud-island baubles, roof-edge bulbs and 303 garland bulbs on the tower walls. No white sources.
