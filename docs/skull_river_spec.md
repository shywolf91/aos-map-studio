# Skull River — Babel (2026-10-20)

(Renamed by the owner to **"Ferrari's Revenge"**, 2026-10-20.)

Generator: `gen_skull_river.py` (seed 1031). Ground height is a parameter: `VALLEY=<z> python gen_skull_river.py <out>`.

| version | VALLEY | ground above water | tower gap (bank/bridge) | notes |
|---|---|---|---|---|
| v1 | 34 | 29 (deep gorge, 1mirror2forts style) | 33 / 31 | user: ground too close to platform |
| low test | DROP=10 of v1 | 19 | 43 / 41 | rejected: skull shortened |
| v2 | 59 | 4 | 58 / 56 | full v1 skull + ground→mouth stairs |
| **v3 (current)** | 53 | 10 (≈1river2night z55) | 52 / 50 | ruined-castle spawns |

## Layout (exact mirror via dx = |x−256|)
* Toxic river N→S down x 256 (water z 63), from the skull pool (y≈120) to a cave in the south ring; narrows to half-width 20 at the bridge; mirrored step-outs (one step per voxel) on both banks.
* One bone bridge (vertebra deck, rib railings, skull corner posts, vertebra piers) at y 244–268 under the platform; deck z VALLEY−2 … VALLEY.
* Mountain ring rises RING = max(24, 0.6·(VALLEY−10)) above the valley; north massif (crest z 0–9) holds the skull.
* Props: dead trees, fossil ribcage (north), toppled columns + ruined arch (south), bone litter, painted "SKULL RIVER" tag on the SW mountaintop.

## Skull (v1 geometry kept in all versions; face y ≈ 94–124, z 0–60)
* Eye chambers floor 26, nose reliquary floor 41 (crouch crawlway, bone throne easter egg), mouth chamber floor 49 with teeth, hub floor 34, tunnel to the massif face (z 34) and eye-chamber lookout balcony (z 26).
* When VALLEY > 49: mirrored stone stairs climb from the ground up the jaw flanks into the mouth; old cheek doors become high lookouts with a knee lip.

## Ruined castle spawns (v3)
Wrapped around the stock ±20 spawn square (x 98–138, y 236–276), which stays a flat flagstone courtyard (no roof spawns, no props inside):
* Keep west of the courtyard (x 62–88): 2 storeys, jagged collapsing walls, doorway to the courtyard + back door, windows both storeys, 7-step stair to a half-collapsed upper floor, partial roof with broken beam ends, crates inside.
* Corner towers NW/SW: hollow, doorway to the courtyard, 12-step stair hugging the wall to a lookout floor, broken crown with a collapsed back.
* Curtain walls N and S (3 thick, ~8 high, merlons, breaches to rubble); front (toward the tower zone) open between two broken gate piers.

## Validation (v3: generated / exported / parser-validated)
* pyspades VXLData loads it: 0/20000 solid mismatches, 0 get_z mismatches; independent reader round-trip exact.
* 0 floating components; mirror exact outside the tag patch.
* Spawns flat at z 52 both sides; platform clear; ground z 53 under both platform ends.
* Preliminary walk check: all skull rooms reachable from the ground (reliquary at crouch); keep upper floor and both tower lookouts reachable from the spawn courtyard.
* Not yet: server-loaded, client-inspected, playtested.

## Open
* In-client look of the green water plane; fall damage from the high skull exits; water_damage 1 may be mild for "toxic"; curtain wall-walk not connected to a stair.
