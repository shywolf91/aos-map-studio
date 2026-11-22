# Royal Parade Snow Night v2: moonlit Christmas parade as Babel (2026-11-22)

Source: `RoyalParadeSnowNight.vxl` + `.txt` by **Bradley & Mile** ("courtesy of Sauerkraut").
Brief (owner, 2026-11-22): "recolored / reworked keeping them 90-100% similar but better atmosphere".
Owner's answers:
* light rework (~90 % same);
* moonlit snow night;
* glow blocks;
* Babel;
* festive vehicles;
* bunting and lights;
* snow details;
* keep the name, version 2.0;
* light spawn cover outside the ±20 squares.

**Status:** generated · exported · parser-validated (own reader + pyspades `VXLData.generate()` identical) ·
**server-loaded** (kit probe, babel: platform 3200 cells, babel extension and .txt loaded; `probe.json`) ·
**not** client-inspected · **not** playtested. All images are numpy previews.

## Original (measured)
* Strip city x 0–511, y 159–347, street at z 56, buildings up to z ~44 near the centre. Hand-built, not mirrored. 4 floating jets.
* Only 48 top colours. Snow (221,221,221), water (153,217,234), fog (230,230,250). Every top voxel had a max channel above 212, so it read as white daylight.

## Changes
| item | change |
|---|---|
| grade | blue moonlit snow (max channel ≤ 176, hue ~262), navy water (luma ~45), shaded brick/stone facades; unique surface colours 10 077 → 41 991 |
| windows | 544 window units; the lit ones light the room behind or a candle on the sill (199 glow sources) |
| festive vehicles | 2 gift trucks, 2 tree floats, 2 Santa sleighs with reindeer, all inside the original footprints and no taller; the other 19 vehicles get a parade paint job only; the clear street width doesn't change |
| bunting & lights | paint on facades and lamp posts (863 bulbs, 185 of them glow, amber/yellow); nothing spans the boulevard |
| snow details | 12 snowmen, kerb drifts, 570 icicles; quay ice is paint only (water damage still applies) |
| street | 24 new lamps with amber glow |
| spawn cover | per side, outside the squares: a 24-tall great tree on the median, a tree float, a gift stack, a parked sleigh, drifts and a snowman |
| tag | "SNOW NIGHT" painted on the water above the kept "Royal Parade / By Bradley" credit (recoloured gold/frost) |
| geometry diff | +8 014 / −141 voxels (0.99 % of the solid); 0 changes in the spawn squares, under the platform (x 200–312, y 234–277) and the platform volume |
| .txt | name 'Royal Parade Snow Night', version '2.0', author 'shywolf91 + AI', description credits Bradley & Mile and Sauerkraut; fog (168,160,196); `babel` True, `water_damage` 2, `heavens_color` (78,74,128,255), glow keys (477 sources, 58 838 stored colours, 3.3 MB); no spawn hooks |

## Validation
| check | result |
|---|---|
| parser / pyspades | PASS |
| platform volume, ground under both platform ends | PASS |
| spawn exposure, blue / red | 5.4 / 6.6 % hidden → **16.1 / 19.0 %**; viewers 8.8 / 8.6 → **5.7 / 5.4** |
| safe descent, enemy spawn, interiors, platform not reachable on foot, new floating 0 | PASS |
| front lanes | at every front x: at least 3 lanes 3+ wide, or one lane 8+ wide |
| colour | land top luma p50 221 → 116; max channel > 212: 100 % → 0.27 % |
| inherited failures (the original fails them too) | mirror; car roofs in the spawn squares (roof spawns); no flank route; walk-on steps on the enemy face of the anchors; nothing in the strip under the platform; sea trap (7-high quay) |
| front dressing | not met: the cover is tall (24-tall great tree, float, gift stack). Lower layouts closed the lanes to 1–2 voxels wide. |

## Known limits / next tests
* Look at it in a client: fog and `heavens_color`, the glow wash on roof snow, and how the 3.3 MB `.txt` loads.
* Walk the north lane near x 139–142 (a parked sleigh and a drift make it zig-zag).
* Inherited roof spawns in the squares were left alone under "light rework".

## Regenerate
`python scenes/royal_parade_snow_night/rpsn_main.py maps/royal_parade_snow_night_v2 --deco-seed 3560922333`
(layout seed 20261122). Summary: `rpsn_summary.py`; renders: `rpsn_render.py`.

## Recolour-only variant (2026-11-22)
The owner asked for "100% original versions just recolored". Output: `maps/royal_parade_snow_night_v2_recolor/`
(`RoyalParadeSnowNight_recolor.vxl` + `.txt`, name 'Royal Parade Snow Night Recolor', version 2.0, same fog
(168,160,196), `heavens_color` (78,74,128,255), `water_damage` 2, glow keys, no spawn hooks).

**Status:** generated · exported · parser-validated (pyspades `generate()` identical) · server-loaded (kit probe in
babel: platform 3200 cells, babel extension and .txt loaded, `probe.json`) · not client-inspected · not playtested.

**What differs from v2:** no voxels added or removed. The vehicles get a parade paint job only: no gift stacks, tree
floats or rebuilt sleighs. There are no new lamps, snowmen, drifts, icicles, great trees or spawn cover, and none of
v2's 141 removals. What the variant keeps is all colour: the moonlit grade, navy water, painted quay ice, lit windows
(room or sill light on existing voxels), string lights and bunting on existing facades, and the "SNOW NIGHT" +
"Royal Parade / By Bradley" water tag. The 14 original 2-column street posts act as the lamps: an amber source sits on
each open-topped cap, with a pool painted around it. All 390 glow sources are existing surface voxels with an open
face; the .txt stores 56,069 glow colours.

| check | result |
|---|---|
| geometry vs original | **+0 / −0 voxels**, asserted in the build (`build.json` `geometry_vs_original`) |
| spawn exposure, blue / red | 5.4 / 6.6 % hidden, 8.78 / 8.56 viewers per spot: the original's values, so the targets are not met (owner's choice) |
| colour | land top luma p10 / p50 / p90 99 / 115 / 139 (original 221 throughout); max channel > 212: 0.19 % of tops (original 100 %); 39,282 unique surface colours (original 10,077); 0 glow-palette collisions |
| kit rows | the same as the original: mirror, roof spawns in the squares, trap, flank, anchor face, front dressing, spawn cover and the under-platform strip fail |

Regenerate: `python scenes/royal_parade_snow_night/rpsn_main.py maps/royal_parade_snow_night_v2_recolor --variant recolor --deco-seed 387005701`
(renders: `rpsn_render.py <dir> --variant recolor`). v2 still rebuilds byte-identically with `--deco-seed 3560922333`.
