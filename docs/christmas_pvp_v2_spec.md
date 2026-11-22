# Christmas PVP v2: cozy Christmas evening rework as Babel (2026-11-22)

Source: `ChristmasPVP.vxl` + `.txt` by **GTR-CODE** ("Exported from Minecraft", planetminecraft *mapa-boxpvp-free*).
Brief (owner, 2026-11-22): "recolored / reworked keeping them 90-100% similar but better atmosphere".
Owner's answers:
* light rework (~90 % same);
* cozy Christmas evening;
* glow blocks;
* Babel;
* lights on the walls and coaster rails;
* keep the name, version 2.0;
* keep the giant centre trees as assist structures;
* light spawn cover outside the ±20 squares.

**Status:** generated · exported · parser-validated (own reader + pyspades `VXLData.generate()` identical) ·
**server-loaded** (kit probe, babel: platform 3200 cells, babel extension and .txt loaded) · **not** client-inspected ·
**not** playtested. All images are numpy previews.

## Original (measured)
* Walled arena x 91–421, y 132–381. The perimeter wall rises to z 0. Floor z 62, solid to the bottom. Mirrored x' = 512 − x, except the PLAY letters and the ? block.
* Two giant Christmas trees x 209–238 / 274–303, y 236–270. Their tops reach z 3, just under the platform ends.
* Bright day palette: snow (190,203,210); 9.5 % of the arena top had a max channel above 212.

## Changes
| item | change |
|---|---|
| grade | dusk-blue snow ramp (no snow above 212); wall gradient from deep blue to a lilac rim; other colours get a cooler, darker OKLab grade with the hue kept; baked lighting + AO |
| ponds | frozen look: cracks, frosted rim (paint only; still water geometry) |
| glow | 692 sources (lamp heads, path stars, warm windows, amber/red/yellow bulbs on walls, rails and giant trees); 95 274 stored colours; `.txt` 2.39 MB (compact writer) |
| wall lights | garland swags painted on the plain wall core at z 13–18 (paint only, no new footholds) |
| spawn cover | per side, outside the squares: 3 lit firs at x 145 / 367, y 244/256/268 (18 tall, crown radius ≤ 6 in 4 tiers, 4 air under the crown so you can walk under), drifts ≤ 2, gift pile ≤ 3, parked sleigh x 154–162 / 350–358; mirrored exactly |
| geometry diff | +3 886 / −0 voxels; nothing in the spawn squares or the platform volume |
| .txt | name 'Christmas PVP', version '2.0', author 'shywolf91 + AI', description credits GTR-CODE; fog (188,170,198); `babel` True, `water_damage` 0, glow keys; no spawn hooks |

## Validation
| check | result |
|---|---|
| parser / pyspades | PASS |
| platform volume z ≤ 2 | PASS (0 voxels added) |
| spawn exposure, blue / red | 4.1 / 5.0 % hidden → **18.4 / 19.0 %**; viewers 5.8 / 5.9 → **4.3 / 4.5** (target ≥ 15 %, ≤ 10) |
| safe descent, enemy spawn, interiors, flank, platform not reachable on foot | PASS |
| colour (arena top) | luma p10/p50/p90 61/124/149; dark < 40: 0.01 %; max channel > 212: 1.7 %, all of it glow sources and their halos |
| inherited, waived | 1 419 floating Minecraft-export pieces (0 new); mirror mismatches (PLAY letters, ? block); 266 trap cells (same as the original); the floor at z 62 counts as "water" in the kit's spawn-square rule |
| front dressing | not met: the 18-tall firs are a row across the spawn path (you can walk under them, 10 apart). This is the cost of the cover target. |
| assist trees | crest at z 3, so a 1-block geometric gap. In the walk model you can't climb them on foot (highest reachable point z 60), so players build up through the foliage. |

## Known limits / next tests
* Look at it in aos_web / BetterSpades: the evening grade, bulb flicker, how the fog reads, and how the 2.4 MB glow `.txt` loads on the owner's glow server.
* Playtest building up through the giant trees, and walking under the cover firs.
* `water_damage` only applies with `map_extensions` loaded. The floor sits at water level (z 62).

## Regenerate
`python scenes/christmas_pvp/cp_main.py maps/christmas_pvp_v2 --stage art --deco-seed 3019137834`
(layout seed 20261122; sha256 3cd15ec2…4ceb). Checks: `cp_check.py`; renders: `cp_render.py <dir> --before`.
