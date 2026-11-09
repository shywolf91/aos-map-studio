# Backyard Babel (v5.0, 2026-10-28)

(The earlier v2.0 spec is kept as `docs/backyard_babel_v2_spec.md`.)

The backyard of one giant house: a toy dollhouse under the Babel platform, a packed centre, rolling ground, a
fenced yard and unique set pieces. Built to Dylan's 2026-10-28 feedback (saved in project memory as standing
rules).
* The centre must be packed and easy to cross on foot.
* Flank route 130–210 voxels from the centre.
* Passable periphery.
* Draw distance ~110 voxels.
* Plants non-deterministic, with smooth varied colours and three random details each.
* No flat ground.
* No platform leading to the tower.

**Answers to the build questions:**
* House stays at the map edge.
* Dollhouse directly under the platform.
* Gentle rolls everywhere, softer in the spawn and tower zones.
* From v4, keep only the painted fence name. The ant hill, pergolas and gravel path were removed.

**Status:** specified · generated · exported · parser-validated (own reader + pyspades 1.4.2) · server-loaded
(piqueserver 1.4.2, Babel). **Not** client-inspected or playtested. Renders are my own previews.

## Layout
Coordinates: x runs west→east, y north→south, z down. The yard surface is ~z 50 and rolls everywhere.

| zone | where | rules |
|---|---|---|
| spawns | stock (118,256) / (394,256) ±20 | strict: nothing > 2 voxels above the ground, not even overhangs; get_z 48–51 |
| fronts + tower zones | x 139–212 / 300–373, y 236–276; tower zone x 121–212 (32 wide, 44–135 from the centre) | strict as above; ground cover and litter only |
| dollhouse | x 218–294, y 226–286, centred under the platform, 30 tall (floor z 49, roof ridge z 20) | pink/white with a lilac roof. Real structure: arched doors on all 4 sides (9 wide), mirrored stairs to the upper floor, two bedrooms with a partition door, balconies N/S, shuttered windows, heart windows, chimneys. Furniture: sofas, counters, canopy beds, wardrobes, chandelier. Built on a 1-voxel plinth with a step ring |
| fashion doll | (256, ~214), on the mirror axis north of the dollhouse | generic, unbranded, ~28 tall on a stand; random hair, dress and skin colours |
| combat zone | x 81–431, y 156–356 | mirrored twins: 28 large toys/objects + 14 tall single plants (30–40) + ~65 medium plants + ground cover. 7–9 voxel gaps between features. Open lanes: E–W y 192–201 / 311–320; N–S x 160–169, 236–245 + mirrors |
| spawn backs | x 82–94 and spawn sides | tall plants behind and beside the spawns, never in front |
| flank ring | north trail y 112–124 (~138 from centre); side trails x 66–78 / 434–446 (~184); south = patio y 396–439 | worn-dirt trails, connected to the spawn rear exits |
| periphery | rest | spaced plants with no overlaps, moderate junk, set pieces |
| house | exterior wall along the south edge (house_ext.py) | unchanged from v4 |
| fence | W / N / E, painted "BACKYARD BABEL" on the north fence | unchanged from v4 |

**Set pieces:**
* Sandbox with a sandcastle in the NE corner: curtain walls, 4 towers with flags, a gate, a hollow keep, a moat
  mark and shells. Stone steps lead in, and a toy pail sits in the sand.
* North strip: stump with axe, toy monster truck, wading pool with a rubber duck, bicycle lying down.
* East strip: garden gnome, wheelbarrow, gas grill, bench.
* West strip: covered firewood stack (log rounds, tarp, bricks, bungees) and a pair of rubber boots.
* A few small puddles in the periphery.

**Toys in the centre:** pink toy car, teddy bears, tea set with stools, rocking horses, letter-block towers,
beach balls, jump rope, pails, plus soda cans, juice boxes, dice, watering cans and the like. All are randomly
rotated and scaled.

## Plants (flora2.py)
* **Species:** the 12 v2 species plus sunflower, foxglove, allium and coleus.
* **Colour:** each plant picks one of 9 foliage families and gets a smooth smoothstep gradient from base to tip,
  keeping the original vein and edge contrast.
* **Flowers:** only real flowers get a per-species flower palette. Mushrooms, burs and seed heads keep their
  natural colours.
* **Details:** each plant gets exactly 3 different random details from 14: ladybug, dew, chewed holes (never
  cutting the plant apart), snail, caterpillar, autumn patch, variegation, withered tips, bud, aphids,
  butterfly, berries, bee, moss collar.
* **v5.0 counts:** foliage families emerald 135, forest 126, chartreuse 83, olive 74, teal 65, sage 56,
  bronze 37, plum 24, coleus 20, silver 19.

## Validation (seed 2818246686, SHA-256 9e7bef26…)
| check | result |
|---|---|
| round trip / pyspades | identical; 0/40 000 solid, 0/20 000 colour mismatches |
| floating | 0 (38 small fragments / 189 voxels dropped at build) |
| platform clearance | 0 voxels at z ≤ 2; highest voxel z 3 |
| ground under platform ends | ground z 50–53, solid to the bottom |
| spawns | live server: 400/400 per team on ground z 48–51 |
| fronts | 0 columns with anything ≥ 3 high |
| flat ground | 0.5 % of 9×9 windows are level (built surfaces only: patio, dollhouse) |
| mirror | combat-zone column tops 99.0 % |
| routes (no building) | spawn → own tower zone 88/89; → enemy spawn 278/278; dollhouse ground 133/134; dollhouse upstairs 162/193 (the doll-side room is on the west, behind the partition door); sandcastle court reachable |
| flank routes (avoiding ±130 of the centre) | north 574/574, south 682/684 |
| reachability on foot | periphery ground 99.9 %, combat-zone ground 99.6 % |
| spawn exposure from platform | 0 % hidden: with open fronts and no pergola, both spawns are fully visible from the platform edge (equal for both teams) |
| VXL | 5.2 MB |

## Open points
* Spawns are visible from the platform; this is the trade-off of open fronts with no pergola. Options: a
  pergola-style overhead, moving the spawns, or accepting it.
* The dollhouse roof is ~19 blocks below the platform (accepted).
* Client FPS has not been tested.

## Regenerate
* Build: `python3.11 v5/world5.py OUTDIR [--seed N]`. Every run is new; the seed is saved.
* Validate: `python3.11 v5/validate5.py OUTDIR`.
* Render: `python3.11 v5/iso.py OUTDIR/backyard_babel.vxl OUT.png [--scale 2]`.
