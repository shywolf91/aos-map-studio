# Mossglade Pond — spec, build and validation (2026-10-30)

**Mode:** stock piqueserver 1.4.2 Babel (`piqueserver.game_modes.babel` + `babel_script`). Platform is script-built at z 1, x 206–305, y 240–271, not in the VXL.
**Size:** 512 × 512 × 64. **Author:** `shywolf91 + AI`. **Seed:** 20261030 (trees, bushes, reeds and lily pads are seeded; saved in `build.json`).

**Status ladder:** generated ✔ · exported ✔ · parser-validated ✔ · pyspades byte-identical ✔ · server-loaded ✔ (headless piqueserver 1.4.2, babel mode, no load errors) · client-inspected ✘ · playtested ✘

Route checks are a voxel-graph model (3 air to stand, 1-voxel steps, drops), not a collision simulation. Renders are numpy previews, not client captures.

## Interpretation decisions (the brief left these open)
- **Water damage on:** `water_damage = 100` in the `.txt`. This is an assumption; lower it for a gentler pond.
- **"Shallow wading paths":** dry sandbars (floor 60–61, water floor 63) at x 228–231 and 281–284 across the bulbs. Any water column is lethal with damage on, so wading paths must stay dry.
- **Stepping stones:** three-wide pillars at the waist, x 255–257, top z 60–61, with one-voxel water gaps.
- **Pond:** hourglass. Waist half-width 14 at x = 256, bulbs 46 at x = 220 and 292. The platform (x 206–305) spans it lengthwise. Ground under the platform's west end (x 200–212) slopes from z 56 to 55; the east end is mirrored.
- **Tower zones:** x 121–212 and 300–391, y 240–272 (the stock corridor). Flat z 55, no props, supported.
- **Flank ravines:** centreline x ≈ 62 (186–202 voxels from centre), half-width 6.5, floor z 60, walls rising to z 55. Mirrored.
- **Ruins:** one walk-in ruin per side at x 136–170, y 166–190 (mirrored). Two rooms, a partition door, 5 one-voxel stairs to an upper slab at z 49, windows, a broken wall, and a collapsed corner.
- **Corner tag:** "MOSSGLADE / POND" painted on the north-west corner (owner rule: name only, no credit line). Colour only, no geometry.
- **Fog:** (178, 172, 192). Not specified in the brief; a neutral lilac-grey, chosen to avoid the cyan platform and sand banks.
- **Mirror:** terrain, pond, ravines, ruins, boulders and stones are mirrored about x = 256. Vegetation is seeded per run and not mirrored; route parity is checked after it.

## Results (`validation.json`, seed 20261030)
| Check | Result |
|---|---|
| VXL re-encode byte-identical (own writer and reader) | ✔ |
| pyspades `VXLData.generate()` byte-identical to the file | ✔ |
| Floating voxels after grounding pass | 0 (1 component, 0 removed) |
| z = 63 solid in every column | ✔ |
| Water cells in front or tower zones | 0 |
| Platform volume z 0–2 clear (margin included) | ✔ |
| Platform-end ground is land | ✔ (z 55–56) |
| Spawn squares, fronts, tower zones: flat, supported, no structures | ✔ (all six) |
| Mirror symmetry of terrain and water | ✔ |
| Ruin interiors: 5 of 5 points reachable on foot | ✔ |
| Route, no jumps: own spawn → own tower | 49 |
| Route: spawn → centre north / south | 158 / 157 |
| Route: spawn → causeway | 170 |
| Route: spawn → flank ravine (y 256) | 55 |
| Route: spawn → spawn (across centre) | 315 |
| Mirror parity, team 2 vs team 1 | within 1–2 (vegetation is not mirrored) |
| Build gap: highest walkable z near platform | 49 (≈ 48 voxels above the platform) |
| Server load (headless piqueserver 1.4.2, babel) | ✔ "Map loaded successfully" |

**Spawn exposure (owner rule: ≤ ~10 viewers per spot and ≥ 15 % hidden) — FAILS.** Viewers are platform-edge points (64) at z 0. Every spawn spot (121) is visible from all 64, with 0 % hidden. Cause: the requested open front is unobstructed, and the spawn sits 52 voxels below an open sky. Options: (a) keep as specified and report the trade-off; (b) add an arch or gate with openings in the front, which partly blocks sightlines and keeps passage open; (c) staggered tall walls, as on Kestrel Spires, which conflict with the brief's open front. Decision needed from the owner.

## Files (in `out/`)
- `mossglade_pond.vxl`, `mossglade_pond.txt`
- `mossglade_pond_overhead.png`, `mossglade_pond_centre_3x.png` (numpy previews, not client captures)
- `build.json` (seed, spec, counts), `validation.json`, `validate.log`, `server_load.log`
- `source/`: `mossglade_pond.py` (generator), `validate_mossglade.py`, `check_pyspades.py`, `server_test_config.toml`

**Regenerate:** `python3 mossglade_pond.py build 20261030` → `python3 validate_mossglade.py` → `python3 check_pyspades.py out/mossglade_pond.vxl` (venv with piqueserver 1.4.2, Python 3.11).

## Known limitations and next steps
- **Art:** the forest is procedural, with two detail passes on trees and no set pieces beyond the two ruins. Boulders are small (2–4 voxel radius), so the shore ring reads weakly from above. This is a prototype against the owner's beauty bar, not the finished look.
- **Unverified:** jump and fall figures (derived, not confirmed in a client), the water-damage tick rate, collision, objective behaviour, and client rendering in OpenSpades, BetterSpades or aos_web.
- **Owner decisions:** the water damage value, the spawn-exposure option above, and the fog colour.
