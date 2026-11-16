# Witchwood Isles — Halloween island Babel (v1.0 final, 2026-10-16)

Twin witchwood islands (blue west, red east) around a glowing cauldron lagoon, and a standing-stone island under
the script-built platform with an **anchor mound directly under each end of the platform**. Mirrored `x' = 512 − x`.

**Status:** specified · generated · exported · parser-validated (own reader + pyspades 1.4.2) · server-loaded
(piqueserver 1.4.2, `game_modes.babel` + `babel_script` + `map_extensions`) · **not** client-inspected in
BetterSpades/OpenSpades by me (you viewed the graybox on alohacraft.cc) · **not** playtested. Renders are numpy
previews, not a game client.

## v1.0
Same map as art v1, with the corner tag reduced to the map name only (your standing tag rule).

## Changes since graybox v1.1
* **Bridge fix:** the north footbridge ended 4 voxels short of the central island (rounded corner). Both crossings
  now run from shore to shore; a new check confirms the footbridge alone joins each island to the centre (100 steps).
* **Spawn screen:** the two grey slabs (they were sightline cover against platform campers) are now two crooked
  half-timbered witch houses on the same footprints — stone plinths, timber frames, lit windows, jettied upper
  floors, steep sagging slate roofs, crooked chimneys. Solid inside so they still block sightlines.
* **Art pass everywhere:** see the table. Gameplay geometry (terrain heights, spawn squares, mound, stairs,
  crossings, pilings) is unchanged.
* **Water colour:** it's the painted seabed. The graybox had a hard ellipse of green; now it fades smoothly
  deep sea → lighter shallows round the islands → soft green glow round the centre.

## What's on the map (blue / west; red is the mirror)
| element | where | notes |
|---|---|---|
| village green (spawn) | plateau x 92–144, y 230–282, z 48; stock ±20 box x 98–138, y 236–276 | warm cobbles, painted rune ring with orange rune marks, moss at the edges; low 2-high dry-stone wall outside the box with north, south and west gates and gate lanterns; nothing inside the box sticks up |
| crooked witch houses (spawn screen) | A x 140–147, y 224–256; B x 150–157, y 256–288; zig-zag lane between | 2 storeys + roof, ridge z 26 |
| screen witch trees | (162, 239) and (162, 273), canopies kept at x ≤ 168 so the pilings have open sky | twisted trunks, purple canopies, hanging moss |
| giant crooked tree | knoll (62, 256) west of the green | 6-wide trunk, four limbs, hanging lantern |
| witch cottage | hill top x 114–127, y 156–166 | lit windows, chimney, picket garden with pumpkins, bubbling yard cauldron |
| pumpkin patch | hill (120, 350) | tilled rows, four carved jack-o'-lanterns, small pumpkins, scarecrow with a pumpkin head |
| graveyard | x 70–96, y 195–222 | headstones, crosses, corner lanterns |
| woods | 15 groves | witchwood (purple), dark pines, autumn trees, dead trees, leaf litter, toadstool fairy rings |
| boardwalk | y 252–259 (8 wide) | plank deck, posts to the seabed, rail posts with lanterns, rope rails with a gap mid-span |
| north footbridge | y 229–231 | rope bridge, now reaching both shores |
| mooring pilings | 3×3, six per side, top z 57 | banded weathered wood, mossy tops, open sky above |
| anchor mound | top x 196–211, y 240–271, z 40 (red x 301–316) | ashlar courses with moss, flagstone top, pale crescent painted on the enemy-facing face, lanterns at the two stair feet (both on your own apron) |
| central floor | z 56 | flagstones with moss in the joints, standing-stone ellipse, trilithon gate in front of each mound, big iron cauldron with green brew and an ember-log ring at (256, 256) |
| flank islets | (256, 138), (256, 374) | dead trees, lantern, gravestone, pumpkin |
| shore | | boulders along the coasts (up to 26 per side) |
| corner tag | sea floor (ground level), SW corner, x 10–186, y 486–499 | "WITCHWOOD ISLES" only |

## Validation (`validation.json` has every number)
| check | result |
|---|---|
| own reader round trip | solid identical, stored = surface, colours identical |
| pyspades 1.4.2 load → `generate()` | byte-identical; 0/20 000 solid and colour mismatches |
| floating components | **0** (whole map one grounded component) |
| mirror | 0 solid / 0 material mismatches |
| platform clearance | 0 authored voxels at z ≤ 2 over the platform (+1 ring) |
| ground under platform ends | blue x 206–211, red x 301–305, all z 40, solid to the bottom, inside each team's own build-ban corridor |
| spawn squares | both all land, flat z 48, 3-air clearance, base `get_z` 48 |
| live server | loads; Babel on; platform 3 200 cells; `water_damage 5` + fog read; 400 sampled spawns per team all z 48; intel (256,256,1); ground under the platform ends z 40 |
| routes (preliminary graph) | spawn → mound top 91 steps both teams, dry, no drop > 9; all mound-top cells return safe; footbridge alone 100 steps; enemy spawn → your mound top 221 (round to your apron); 0 trap cells |
| build gaps | mound top 39 straight up; pilings 61–66; highest walkable point near the platform z 39 |
| spawn exposure from the platform edge | blue 1.1 viewers/spot, 76 % hidden; red 1.0, 79 % hidden (targets ≤ 10, ≥ 15 %) |
| ground sightlines into spawn (≤ 128) | 0 % from enemy mound, central floor, boardwalk; 1.6 % from your own mound if invaded |
| glow share | 0.21 % of land tops (lanterns, windows, brew, jack faces) |
| deterministic | fresh-process rebuilds identical, SHA-256 `6b83ab22…` |

## Notes and open points
* 6 vs 5 anchor columns under the platform (stock platform centred on 255.5, bases/build-ban on 256).
* `water_damage: 5` per position update in water — rate unmeasured; one wading test needed.
* Mound sides are 16-voxel drops to the floor; the stairs are the safe way down. The stair rail top (z 39) is standable.
* The central floor still joins your apron round the mound ends, so enemies can walk round to your stairs (221 steps
  from their spawn). A one-way 3-voxel ledge could close it, at the cost of your own way back from the floor.
* Fog (182, 168, 150) is unchanged; try it live with `/fog` against the purple foliage.
* Next: look in BetterSpades/OpenSpades, playtest.

## Regenerate
`python3.11 build.py OUTDIR --art` (writes version 1.0) then `python3.11 renders.py OUTDIR` (numpy, scipy, pillow; piqueserver 1.4.2
for the pyspades round trip). Without `--art` it builds the graybox. Seed 3131; layout in `ww_gen.SPEC`, art in
`ww_art.py`, tag font in `ww_font.py`. `tools/ww_probe.py` is the server probe used for the live check.
