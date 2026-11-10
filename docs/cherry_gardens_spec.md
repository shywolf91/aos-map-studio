# Cherry Gardens — v1.0 spec (2026-11-06)

A spring ground Babel on a full 512 × 512 map. Each spawn is a hillside tea-house estate. Below the estates,
stepped rice terraces lead down into a valley of koi ponds, blossom groves, stone lanterns and footbridges. At the
bottom sits a stone ritual pavilion on a moat island under the platform. A waterfall-fed stream runs from the
north headwall, through the bamboo thicket, splits into two arms around the moat, and drops into the south gorge.
Ring hills close the edges.

This is a fresh rebuild of the same brief as `cherry_terrace_gardens_spec.md`, with the same owner choices. The
older build's generator was never brought into the repo.

**Status:** generated → exported → parser-validated (our reader + pyspades 1.4.2 `VXLData`, byte-identical
`generate()`) → **server-loaded** (stock piqueserver 1.4.2, babel mode: platform built, fog sent, both teams spawned).
**Not yet** client-inspected in aos_web / OpenSpades / BetterSpades, and not playtested.

## Owner decisions `[USER]`
* Fresh build, same choices as Cherry Terrace Gardens.
* `water_damage 0`: paddies, ponds, stream and moat are walkable.
* Bamboo thicket on the north flank, waterfall gorge on the south flank. Both teams share both flanks.
* Pavilion: low and enterable, with an upper gallery. Lanterns are painted (no glow blocks).
* Sky decor: 3 kites and 3 petal clouds (opt-in floating pieces).
* Vegetation is non-deterministic: an OS seed is drawn per build and saved as `veg_seed` in `build.json`.
  v1.0 uses `veg_seed = 1943792076`.

## Layout (`SPEC` in `scenes/cherry_gardens/cg_terrain.py`)
| element | where | top z |
|---|---|---|
| valley floor | d = abs(x − 256) < 30 | 40 |
| plinth / moat island | r < 17 around (256, 256); moat r 17–24 (water z 41) | 38 |
| ritual pavilion | 23 × 23, dais z 37, gallery z 31, two-tier swept roof, gold finial ~z 9 | — |
| tower anchors | blue x 191–211, red 301–321, y 238–273; sheer dressed-stone east/west faces, no stairs | 35 |
| front corridor | y 226–286, one continuous 1-voxel ramp from valley (d 30, z 40) to plateau (d 110, z 26) | — |
| paddies | 2-voxel stone-walled terraces at d 64–110, y 150–224 and 288–350; stone stairways every 18 rows | 35→27 |
| spawn plateau | d 110–215, flat with +1 humps | 26 / 25 |
| spawn estate | two-storey tea house x 52–74 / y 245–267 (mirrored), garden wall, 2 koi ponds, 2 rock gardens | 26 |
| gate grove | 5 large walk-under cherries on the plateau's front edge (x ≈ 147–151) | canopy ≥ 5 above ground |
| bamboo flank | y 56–130, plateau z 30, lane y 92–100 kept clear | 30 |
| headwall + waterfall | north centre, cliff z ~10 → pool z 31 | — |
| gorge flank | y ≈ 402–440, floor z 46, 3-ledge noisy walls, ramps up to the plateau at d 150–200 | 46 |
| ravine | stream cut through the south rim, walkable banks z 40, stair beside the falls into the gorge | 40–46 |
| ring hills | rolling, z ~5–26, pines and mossy outcrops | — |
| corner tag | "CHERRY GARDENS" painted on flattened ground, NW corner (x 12–97, y 6–16) | 6 |

Valley set pieces per side: 2 small open tea pavilions, 4 valley koi ponds plus 1 rim pond (koi, lily pads, reeds,
bank stones), 1 rock garden plus 2 in the estate, 4 ceremonial timber gates in total (corridor, bamboo lane, gorge,
and one valley path), a lens-island shrine on each stream arm, about 8 arched footbridges plus 4 moat bridges,
stepping stones, and about 40 stone lanterns in 3 styles.

Vegetation (west half, mirrored):
* 230 trees in 5 cherry forms (spreading, weeping, young, gnarled, umbrella). About 7 % have soft-green canopies.
  Each tree gets 3 random details out of 10.
* 54 bamboo clumps, 26 hill outcrops, cloud-pruned pines, azalea understory and hedges.
* 43 moss/fern curtains on the gorge and headwall faces.

## Validation (`maps/cherry_gardens_v1/validation.json`)
| check | result |
|---|---|
| our reader | re-encode byte-identical; every surface voxel coloured; z 63 solid |
| pyspades 1.4.2 `VXLData` | `generate()` byte-identical; 0 / 40 000 solid and colour mismatches; `get_z` at the bases = 25 |
| reproducible | same SHA-256 (`358dd1a0…`) in a fresh process with `--seed 1943792076` |
| floating components | 0 unintended. The 6 sky pieces are expected. 984 voxels of foliage fragments were removed at build |
| sky rules | ≥ 67.5 from the platform, none over a spawn square, ≥ 8 air below each piece |
| mirror (excluding tag + sky) | 0 solid / 0 material mismatches |
| platform cells z 0–2 (+1 margin) | empty |
| ground under platform ends | blue x 206–211: z 35 on all columns. Red x 300–305: z 35–38 (the accepted 6 vs 5 anchor-column offset) |
| spawn squares | top z 25/26 only, mirror-equal, no water or roof |
| platform reachable without building | no |
| build gap | highest walkable point near the platform is z 30 (pavilion gallery rail): 29 voxels / 28 blocks. The brief asked for 25–40 |
| route model, spawn → enemy spawn | 252 steps for both teams (direct through the valley); spawn → own anchor 68; anchor → back to spawn 68 |
| pavilion | floor reached at 107, gallery at 120; tea-house upper floor reached at 52 |
| spawn exposure from platform | blue 73.2 % / red 76.0 % of spots hidden; 0.64 / 0.59 viewers per spot (max 6). Targets: ≥ 15 %, ≤ 10 |
| live server | piqueserver 1.4.2 babel: map loaded, `.txt` parsed (name, fog (224, 196, 178)), platform 3 200 / 3 200 cells, blue spawned (119.5, 237.5), red (406.5, 256.5) |

## Known limits / next tests
* Check in aos_web / BetterSpades. Judge the peach fog and `heavens_color`, and check FPS over the bamboo thicket
  and the 460 cherry trees.
* About 250 "trap" cells in the route model. All of them are foliage perches on the rim and ring-hill trees and
  on bamboo crowns next to higher ground. You can drop off them, but the drop is over 9 voxels. None are in the
  central zone or the fronts.
* The anchors can be stepped onto from their north and south sides via the corridor ramp. There are no stairs on
  the enemy-facing face, as the rule requires.
* The gorge walls are better than a sheer plane, but they are still the plainest part of the map. They are the
  first candidate for an art pass, along with the corridor's lantern rows, which may read as dense.
* Spawn cover from the gate grove is strong (about 75 % hidden). If players find the fronts too enclosed, thin the
  grove from 5 trees to 3.
* Route checks are a graph model, not proof of in-game movement.

## Regenerate
```
cd scenes/cherry_gardens
python cg_main.py ../../maps/cherry_gardens_v1 --seed 1943792076   # omit --seed for a fresh garden
python cg_check.py ../../maps/cherry_gardens_v1 --pyspades --exposure
python cg_render.py ../../maps/cherry_gardens_v1
```
Server test config: `server_test/cg_babel/config.toml` (port 32935).
