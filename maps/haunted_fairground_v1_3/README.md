# Haunted Fairground — v1.3 (Tower of Babel)

An autumn fair abandoned mid-season, on the layout of `Ruins.vxl`. Darker violet-dusk atmosphere.

## What changed from v1.2
- **Renamed** to "Haunted Fairground": map name in the metadata, the corner tag ("HAUNTED FAIRGROUND", sea floor, south-west corner, x 10–226, y 486–499), and the file names (`haunted_fairground.vxl` / `.txt`, rotation name `haunted_fairground`). Geometry identical to v1.2.

## What changed from v1.1
- **Corner tag:** the map name only is painted in amber on the sea floor in the south-west corner , with a dark drop shadow. Nothing else changed in the geometry; the voxel occupancy is identical to v1.1.
- **Fog:** now a bright lavender-dusk tint, (158, 146, 182), per the project's fog rule (channels around 150 or above). The dark palette carries the spooky mood instead of the fog.

## What changed from v1.0
- **No platform in the VXL.** `babel_script.py` paints it at load time. Confirmed on a running server: the platform appears in cyan even though the file has none.
- **The Midnight Pavilion replaces the funhouse.** It is the main contested building.
  - Same footprint and storey heights as the Ruins central building: x 219–292, y 262–308, six storeys, roof deck at z = 15.
  - Every storey has rooms, corridors, doorways and windows.
  - Four switchback stairwells, two per team side, run from the ground floor to the roof.
  - Other features: a double-height lobby (atrium), a mirror-hall storey, a north loggia under the platform, and a crenellated roof deck.
- **The Ferris wheel is now a secondary point.**
  - It is larger (radius 23, peak z = 5), with open gondola buckets players can stand in.
  - A new two-storey operator station has rooms and a stair to its roof.
  - Two iron ramps run from the station roof to a deck beside the hub (z = 29).
- **No solid buildings.** Every building can be entered:
  - **Ghost-train rides:** two floors, dark maze, coffins, upper gallery. They now sit on Ruins' north bastion, reached by a timber pier.
  - **Caravans:** cabins with a door, steps, windows and a fortune-teller's table.
  - **Tents:** walk-in, with a crystal ball.
  - **Giant jack-o'-lantern:** walk-in, lit amber inside.
- **Spookier autumn look.**
  - Darker, desaturated palette, with a lilac ground mist in the low hollows.
  - Bare, gnarled trees with crows, alongside the autumn ones.
  - A fenced graveyard on each lobe, lit jack-o'-lanterns along the paths, cobwebs and coffins inside.

## Files
| File | |
|---|---|
| `haunted_fairground.vxl` | map, md5 `85371df7731fb0c46cadefb277c01f71` |
| `haunted_fairground.txt` | piqueserver metadata (name, version 1.3, fog, extensions) |
| `generate.py` + `vxlio.py` + `load.py` + `Ruins.vxl` | generator; `python3 generate.py` reproduces the VXL byte-for-byte (SEED 1031, needs numpy + scipy) |
| `pavilion_floor_plans.png` | floor plans of the pavilion; purple marks stair and atrium openings |
| `overhead.png`, `oblique_*.png`, `closeup_*.png` | quick previews from my own renderer, not a game client |

## Server setup (piqueserver)
```toml
rotation = ["haunted_fairground"]
game_mode = "piqueserver.game_modes.babel"
scripts = ["piqueserver.scripts.babel_script"]
# optional protected-map policy (server-wide): only player-placed blocks can be destroyed
user_blocks_only = true
```

## Validation (v1.1)
| Check | Result |
|---|---|
| VXL round-trip with an independent reader | identical occupancy |
| Platform voxels in the VXL | 0 |
| Ground under both platform ends (x 206–211, x 300–305) | land, no water columns |
| Corner tag | sea floor only; nothing above it |
| piqueserver (master `3dfc0a6`) with babel + babel_script | loaded; script painted the platform; fog (158, 146, 182) applied; cap_limit = 1 |
| Floating geometry | none; one face-connected structure resting on the water layer |
| Left/right mirror | exact (0 differing voxels) |
| Spawn squares (x 98–138 and 374–414, y 236–276) | no props, no water, surface z 50–58 |
| Babel tower strips (x 128–211 and 301–384, y 240–272) | no props |
| Interior reachability (approximate walker) | pavilion: all six storeys 100 %, roof deck reachable · station 99 %, hub deck reachable · ghost trains 88 % (the rest is the sealed attic) · caravans 100 % · tents 98 % · jack-o'-lantern 98 % |
| Heights (platform at z = 1) | pavilion roof deck z = 15 (parapet z = 13–14), the same height as Ruins · wheel peak z = 5 · hub deck z = 29 |

The interior reachability check is approximate. It assumes a 3-voxel-tall player who can step up 1 voxel and drop any distance; it is not AoS's real movement code.

Status: generated / exported / parser-validated / server-loaded. Not yet client-inspected or playtested.

## Things to test in game
1. **Doorways and stairs.** Doorways are 2 wide and 3 tall, and stair steps rise 1 voxel. Check that players walk through and up without jumping.
2. **Pavilion roof to platform.** The roof is 14 blocks below the platform, and the north loggia sits directly under it. Check how fast each team can build up from there.
3. **Wheel peak.** It reaches z = 5. Can players climb the rim or gondolas and build across to the platform? If that is too strong, shrink the wheel.
4. **Fog.** Check (158, 146, 182) against the dark palette in OpenSpades and BetterSpades; adjust with `/fog` live if needed.
5. **The two ghost-train doors.** The east door has steps; the south tunnel mouth opens onto the bastion forecourt. Check both are easy to use.
