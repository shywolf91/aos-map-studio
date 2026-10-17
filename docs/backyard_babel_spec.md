# Backyard Babel — miniature-world backyard Babel (v2.0, 2026-10-16)

v2 is a full rewrite after tester feedback on v1 ("empty, big gaps, centre empty, ground shouldn't be green, needs
many varied plants and lots of junk, non-deterministic generation"). Also from Dylan: don't default to structures
between spawn and tower zone, and don't raise the tower zone — players like building towers.

**Status:** specified · generated · exported · parser-validated (own reader + pyspades 1.4.2) · server-loaded
(piqueserver 1.4.2, `piqueserver.game_modes.babel` + `babel_script`) · **not** client-inspected · **not** playtested.
Renders are numpy previews.

## Layout
* **Playable core** x 81–430 × y 131–380 (350 × 250), centred on the platform. Everything outside is environment.
* **Ground**: earth-coloured layered soil (humus / mid / dry / clay tones, grit, cracks, isolated moss-turf patches),
  dirt mounds, 1-voxel max slope (slope limiter), shallow painted puddles (solid, not water).
* **Tower anchors**: flat ground-level dirt patches under each platform end, x 190–226 / 286–322, y 236–276, z 50
  (towers are built from the ground, ~49 blocks). Nothing is placed on them.
* **Spawns**: flat dirt squares (base ±21, z 50) inside a clearing of tall grass/weeds with open N/S/E/W exits.
  Grove plants are random but each one is mirrored exactly to the other team → identical cover. No walls/screens.
* **Under the platform**: a puddle, small junk (caps, coins, buttons, dice, marbles…), low clover/moss/mushrooms.
  Height cap near the platform (x 186–326, y 200–312): nothing taller than 12 (z ≥ 38).
* **Core cover**: ~26 mirrored slots of junk (cans, paper balls, toy bricks, balls, juice boxes, newspapers, pencils,
  bottles, chip bags, pots, watering cans, rocks, twigs, rope, toy shovels) + ~95 mirrored plant clusters + fill.
  Positions/types mirrored, every instance generated independently (≈85 % column match).
* **Outer ring**: dense (~7-voxel jittered grid) plants 10–40 tall, ~190 junk items, rocks, fallen leaves, twigs, acorns.
* **Set pieces**: yellow-or-random-colour bicycle lying in the north grass, garden bench (west), tree stump with an axe
  (south), toy monster truck (north-centre, in the core), rubber boots (east, one standing, one fallen).
  Each gets a 7-voxel apron kept clear of plant stems.
* **Corner tag** SW, "BACKYARD BABEL" painted on the ground.

## Plants (10 + extras), after Grounded's harvestable flora
grass blade (bent, twisted, broken, dry-tipped variants), flowering/seed grass, clover (3-leaf, rare 4-leaf, pale
chevron), dandelion (toothed rosette, bloom or seed puff, partly blown puffs), bur weed (branching, spiky burs),
husky weed (broad veined leaves + seed spike), thistle (spiny lobed leaves, purple heads), sprig/seedling,
mushrooms (bolete/button/ochre/spotted clusters), moss cushions with sporophytes, flowers (daisy/tulip), fern;
litter: fallen leaves, twigs, acorns, pebbles. Every plant call is randomised.

## Non-determinism and reproducibility
Each run draws a new random seed from the OS; the seed is printed and saved in `build_info.json`.
`python3.11 world.py OUTDIR --seed N` rebuilds that exact map. Delivered v2.0: seed **1609119889**, SHA-256 `969de31d…`.

## Validation (v2.0)
| check | result |
|---|---|
| own reader round trip / pyspades 1.4.2 | identical; 0/40 000 solid, 0/20 000 colour mismatches |
| floating components | 0 (62 tiny fragments, 149 voxels, removed at build time) |
| platform clearance | 0 voxels at z ≤ 2; highest voxel z 5 |
| ground under platform ends | z 50 both sides (live server too) |
| spawn squares | flat z 50, 3-air clearance; live server 400 spawns/team all z 50 |
| spawn exposure from platform edge | blue 77.6 % hidden (0.5 viewers/spot), red 76.6 % (0.7) |
| routes (no building/jump/crouch) | spawn → own anchor 98 / 97 steps; back 101 / 97; enemy anchor 193 / 191 |
| highest walkable without building near platform | z 39 |
| dead-end cells (model) | 11 701 of ~305 000 reachable — pockets under dense foliage; real players can crouch/dig out |
| coverage | core 65 % plant columns / 21 % prop; outer 72 % / 33 % |
| VXL size | 7.6 MB (≈3× normandie) — check client load time / FPS |

## Open points
* Client performance with ~4 000 plants is untested.
* Foliage pockets: model says ~4 % of walkable cells can't be walked out of without crouching/digging.
* Set pieces are toy-scale (a bike at true bug scale would be bigger than the map).
* Puddles are painted solid voxels (water in AoS only exists at z 63).

## Regenerate
`python3.11 world.py OUTDIR [--seed N]`, `python3.11 validate2.py OUTDIR`, `python3.11 render2.py OUTDIR/backyard_babel.vxl OUTDIR`.
Kit `vox.py`, plants `flora.py`, props `props.py`, layout `world.py`; uses `vxlio.py`, `noise.py`, `build.py` (font).
