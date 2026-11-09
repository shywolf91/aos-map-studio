# Cherry Terrace Gardens — v1.0 spec (2026-11-06)

Spring ground Babel, full 512 × 512. Tea-house estates hold the spawns above stepped rice terraces; a valley of koi
ponds, blossom groves, stone lanterns and footbridges leads down to a stone ritual pavilion on a moat island under
the platform. Bamboo thicket on the north flank, waterfall gorge on the south flank, ring hills at the edges.

**Status:** generated → exported → parser-validated (two readers, byte-identical re-encode). **Not yet** pyspades
cross-checked, server-loaded or client-inspected. The pyspades 1.4.2 install was blocked in the build sandbox.

## Owner decisions `[USER]`
* water_damage 0: paddies, ponds, stream and moat are walkable.
* Flanks: bamboo thicket on one side (N), waterfall gorge on the other (S). Both teams share both flanks, so x-fairness holds.
* Pavilion: low and enterable, with a stair-up gallery inside. Lanterns are painted (no glow blocks).
* Sky decor: 3 kites and 3 petal clouds (opt-in floating pieces).

## Layout (`SPEC` in `scenes/cherry_terrace_gardens/ctg_build.py`)
| element | where | z (top) |
|---|---|---|
| valley floor | centre | 40 |
| pavilion plinth / moat island | r < 17 around (255.5, 256); moat r 17–24 | 38 / water 41 |
| pavilion | 22 × 22, posts z 31–36, gallery z 33, roof ridge ~z 26 | — |
| tower anchors | blue x 192–211, red 301–320, y 238–273 | 35 |
| anchor fronts | sheer 3-voxel dressed-stone wall at x 211 / 301, no stairs | — |
| spawn plateau | 45 × 45 around (118,256)/(394,256), mostly flat with +1 humps | 26 |
| spawn estates | two-storey tea house at x 48–76 (mirrored) with garden wall, 2 koi ponds, rock garden | 23 |
| paddies | 2-voxel terraces, x 152–204 (mirrored), y 150–226 and 286–350, crossed by stairs every 18 | 27–39 |
| bamboo flank | y 62–128, lane kept at y 92–100 | 30 |
| gorge flank | y 402–440, floor z 46, ramps up at both ends, waterfall from the stream ravine | 46 |
| stream | N rim → bamboo terrace → valley → moat → ravine → gorge falls; surface never rises going south | — |
| ring hills | rolling, z ~6–20 | — |

Valley set pieces per side: 2 small enterable tea pavilions, 5 koi ponds (stepping stones, koi, lily pads),
2 rock gardens, 3 ceremonial gates, ~6 stream bridges plus 3 moat bridges, ~40 stone lanterns, ~210 blossom trees
(pink, white, soft green; each tree gets 3 random details out of 7), 260 bamboo clumps, and low azalea hedges.

## Validation (`maps/cherry_terrace_gardens_v1/validation.json`)
| check | result |
|---|---|
| aosmap reader + independent reader | agree; re-encode byte-identical |
| reproducible | same SHA-256 in a fresh process (seed 20261106) |
| floating components | only the 6 sky pieces (3 petal clouds, 3 kites) + 3 two-voxel petal bits |
| platform cells z 0–2 | empty |
| platform reachable without building | no (both teams) |
| build gap | 34 voxels for both teams (stone lantern by the pavilion); the brief asked for 25–40 |
| spawn squares | flat z 26, mirror-equal 1.00, no water |
| spawn exposure from platform | 44.9 % / 44.2 % of spots exposed, 1.7 viewers each (target ≤ 10 viewers, ≥ 15 % hidden) |

## Known limits / next tests
* Run the pyspades `VXLData` cross-check and a live babel load. Check fog and heavens_color in aos_web.
* Bamboo uses 1 × 1 stalks in clumps. Check client FPS against the "laggy pillar field" rule.
* Gorge walls are plain grey stone and the ring hills are fairly simple. Both are candidates for an art pass.
* Route checks are a graph model, not proof of in-game movement.

## Regenerate
`python scenes/cherry_terrace_gardens/ctg_main.py maps/cherry_terrace_gardens_v1`, then
`python scenes/cherry_terrace_gardens/ctg_check.py maps/cherry_terrace_gardens_v1`
