# Babel zone study: spawn, tower zone and centre (2026-11-13)

Goal (owner): improve spawns, tower zones and central areas of our Babel maps **while keeping our design system**,
using the community collection (aloha.pk maps repo, `map_collection/`, read-only) and our two best maps,
**Silverpine Hunt v2.2 (SH)** and **The Wicker King's Harvest v1.1 (WKH)**, as benchmarks.
This document gives measurements and **proposals**. They are not owner rules. Every proposal is tagged and says
how it relates to an AGENTS.md §4 rule. Conflicts are flagged and left unresolved.

Status of the community maps: **parsed** only. Thumbnails are numpy previews (`out/zone_study/thumbs/`, git-ignored).

## 1. Tools and how to rerun

| file | what |
|---|---|
| `aosmap/kit/zones.py` | zone metrics as pure functions on the solid array (+ `params`); fast span-header decoder; LOS, horizontal free rays, max-flow crossing width, symmetry type, map class |
| `aosmap/kit/babel_checks.py` | `run_all(...)` now also writes a report-only `zone_profile` section (no pass/fail; other sections unchanged) |
| `tools/babel_zone_study.py` | corpus runner: finds Babel maps, parses `.txt` with `ast` (never executed), dedupes, profiles, writes `out/zone_study/metrics.json` + `metrics.csv` (cache in `out/zone_study/cache/`) |
| `tools/babel_zone_analysis.py` | distributions, percentiles, benchmark comparison, exemplars, thumbnails → `out/zone_study/analysis.json`, `analysis.md`, `thumbs/` |
| `tests/test_kit.py` | 5 new fast tests for `zones.py` on synthetic canvases (decoder, exits/min cut, enclosure, flat-map values, rays/LOS/symmetry, roof vs deck) |

```
python tools/babel_zone_study.py --workers 5      # ~3.5 min on DRAGONSPIRE (238 maps), cached afterwards
python tools/babel_zone_analysis.py               # ~20 s
python -m aosmap.kit.babel_checks maps/<map>      # validation now includes zone_profile (+~2 s)
```

## 2. Method and definitions `[RUN]` unless noted

Stock 1.4.2 Babel constants (`BABEL_DEFAULT`) are assumed for every map: platform x 206–305, y 240–271, z 1; bases
(118,256)/(394,256); spawn squares ±20 on the topmost voxel. Every metric is computed for both teams (blue, red =
enemy direction mirrored) and the tables use the **mirrored average**.

Fields per column: `top` = topmost solid z; `water` = top ≥ 62; height = 63 − top.
**Ground baseline** = grey opening of the height field with a 25 × 25 window; **object column** = height − baseline ≥ 2
and not water. Features narrower than 25 count as objects (houses, trees, walls, cars, narrow ridges); anything wider
(big buildings, broad hills) counts as ground. **Unreliable on sky/bridge maps** (the baseline under decks is the sea).
**Roof column** = an air gap ≥ 3 under the topmost voxel closed by a dry floor ≤ 20 below (a spawn there is a roof
spawn). **Deck column** = any other air under the top (deck or bridge over water or a lethal drop).
Walkability = kit `Nav` ('hc' rules: 4 neighbours, 1-voxel step, drops ≤ 9 safe). Eye = floor − 2.4, head = floor − 2.2.
LOS marches 0.5 steps through solid voxels **plus the script platform**. Point-to-point LOS is cut at **128 voxels
horizontal (fog)**. The platform-viewer exposure is the kit's calibrated model, which ignores fog.

| zone | cells (blue; red mirrored) |
|---|---|
| spawn square | x 98–138, y 236–276; spawn floor = median top z |
| rings around it | Chebyshev distance 0–8 / 8–20 / 20–40 outside the square, split into enemy-facing / rear / lateral sides |
| front (tower zone) | x 139–211, y 236–276; anchor = the 6 columns under the platform end (x 206–211) |
| own tower-zone ground (exposure eyes) | x 168–211 (kit `tower_zone` default) |
| under-platform strip | x 212–300, y 240–271 |
| central zone | x 150–362, y 130–382 |

Spawn: top-z mean/min/max/std, **near-mode share** (within ±1 of the mode), **roughness** (mean |Δz| between
4-neighbours), roof/deck/water columns; height vs front, centre ground, map median land, platform (drop, angle);
**enclosure**: mean solid volume above the spawn floor and **cover3** = share of ring cells that rise ≥ 3 above the
spawn floor (hides a standing player), per ring and side; **exits**: ring cells at r = 1/8/20 reached from the
square without leaving the box (open share, exit count, narrowest, total width); **exit min cut** = max number of
vertex-disjoint walking paths from the square to the ring 40 out (= cells a team must fill to seal it; *sealable*
if ≤ 10, `[DERIVED]` threshold); platform viewers/hidden % (kit calibrated); share of spawn spots seen from own
tower-zone ground and from the centre ground under the platform; steps spawn spot → own platform end (median) and
detour ratio.
Front: height profile, slope, height vs spawn and centre, flat share (±1 of median), water share, lowland share
(≥ 20 below the spawn floor = sky/bridge drop), land width through the corridor (min, p50), object share / count
(≥ 4 cells) / height p50 p90 max / footprints, free share (min over 8-column sections), largest empty disk,
anchor height, **build gap** = highest cell reachable from own spawn within 12 of the platform end → platform,
walk-on rows on the anchor's enemy face (kit `anchor_checks`), free LOS toward the platform and in 16 directions,
share of front cells visible from the enemy tower-zone ground.
Centre: strip ground z, water, objects, min gap to the platform; zone land/object share, objects per 10k columns,
object height and footprint, built volume per column, **gap width** (2 × distance-transform value on the ridge of free
ground: p10/p50/p90), largest empty disk, indoor share (walkable cells with solid above the headroom), multi-level
share, **crossing width** (max vertex-disjoint W→E walking paths inside the zone, Menger = min cut in cells),
lanes at x = 255–256, horizontal LOS mean / p90 (400 sampled walkable cells × 16 rays, cap 128), share of centre cells
seen from each platform end's ground, high-ground columns ≥ 6 above an end within 40. Routes: spawn → enemy spawn
steps, centre-avoiding flank (kit band) and its length ratio, whole-map crossing width. Map: land share, height
percentiles, symmetry type (xor/union mismatch of solid voxels z < 62 under x512, x511, y512, y511, point511,
point512; exact ≤ 2 %, `~` ≤ 10 %, else none).

**Map class** (rule): `sky_bridge` if front lowland share ≥ 0.5; else `island` if map land share < 0.5; else `ground`.
`assist` if the build gap ≤ 4 for either team. **Main set** = stock-fit (both spawn squares < 50 % water and < 50 % roof
columns) and not mirrored only across y (rotated). Everything below uses the main set unless stated.

## 3. Corpus

| step | count |
|---|---|
| `.vxl` in the collection | 1114 |
| Babel candidates (`'babel': True` in extensions, or "babel" in file/name/description, or named in the rotation guide) | 259 (our own maps in the collection skipped: autumnnormandie, brimstone_atoll, drowned_cathedral(×2), drowned_cathedral_v2, haunted_fairground, islandwinter, witchwood_isles) |
| decoded | 259 (0 failures) |
| unique after dedupe (top z within 1 block on ≥ 97 % of columns) | **226** (e.g. 1river2forts = 1river2white/dark/night/forts-snow; tradeoff = tradeoffnight; trademas = tradeoffv2/tradeoffdark-*; xmasfire2 = crossfire2/halloweenfire2/crossfire2-snow; jsweet = pinline/pinline2/bridgeme; abridgetoofar = abridgetoodark; full list in `metrics.json` `aliases`) |
| profiled | 226 + our 12 = 238 (0 failures) |
| **main set** | **158** (61 not stock-fit: 51 water spawn squares, 10 roof squares; 7 y-mirrored/rotated: BGTimberTownBabel, anticbridgebabelv3, babelstairs, ellipdrift, koth, satellite, waterfrontv2babel) |

Classes, all 226: island 149, ground 60, sky_bridge 17; assist 3. Main set: island 98, ground 52, sky_bridge 8.
Symmetry, all 226: none 142, x511 25 (+14 approx), x512 2 (+9 approx), point511 13 (+8 approx), point512 1 (+1),
y511 3 (+6), y512 1 (+1). **Most community Babel maps are not mirrored** under our threshold (normandie included).

Guide labels (rotation guide v1.8 section headings, matched by file stem; `[GUIDE]`):
* **good** = "Maps that work fairly well" (26 names). 17 in the main set: JoeyRaysBayou, babelpocalypse, battlefarm,
  bigasssideforts, crossfire3, halongbabel, hezeehills, makewar, newfort, normandie, oasis, oasis2, roadisland,
  swag2, yarr, yubacore, yukon. **Excluded from the main set** because the stock squares are water or roofs: lard,
  plateau, trademas, tradeoff(+night), skullfort, swampcanyon, nine_eye_babel, GoonassaultJapan. These are probably
  run with custom spawns on aloha, so stock-geometry metrics would describe positions nobody spawns on.
* **problem** = "can be problematic" + "Problematic" (13 names). 8 in the main set: AtlasNovus, TowerDive, blackwidow,
  matrix_babel, stackattack (+ the jsweet/pinline group), summerfields, turtlesoup, winter.
* rotation = named in any rotation string (41 in the main set). HallweebWIP is not in the collection.

**The label sets are small (17 vs 8).** I ran Mann–Whitney U on 48 metrics. Only one has p < 0.05: central objects
per 10k columns (good 8.7 vs problem 2.5, p = 0.029). About 2.4 would reach p < 0.05 by chance, so **no metric
separates good from problem maps reliably.** The guide's failures are mostly about things these metrics don't see
(lag, griefing, water, fog brightness).

## 4. Caveats

* Stock constants are assumed for every map. Aloha runs custom spawn positions and platform types on many maps, and
  `.txt` spawn hooks are ignored by stock `babel_script`. A map measured at the stock squares may not be played there.
* We have no popularity or playtest data, only the guide's labels and the owner's ranking of our maps.
* Routes and crossing widths come from a graph model (the kit Nav), not a collision simulation.
* Exposure: the platform-viewer model ignores fog (as calibrated). Ground LOS is cut at 128. Neither models player
  height differences beyond eye/head offsets, transparency or partial cover.
* The object/baseline estimate is a heuristic (25-voxel window). It is unreliable on sky/bridge maps and counts
  narrow terrain ridges as objects. Large buildings read as ground.
* Uninformative in practice: `steps_to_own_end` (grid-dominated, ~68–93 everywhere), flank ratio (≈ 1.93 for almost
  every map because of the fixed band geometry), central LOS p90 (saturates at 128), `seen_from_enemy_tower_zone`
  for the front (mostly beyond fog range).
* Correlation with "rotation staple" or "good" is weak evidence (N above). Our benchmark comparison is N = 2 vs 10.

## 5. Distributions (main set, N = 158) vs benchmarks

Percentile of each of our maps in the community main set in brackets. "verdict" compares SH/WKH with our 10 other
maps: **clear** = both benchmarks outside the others' range; **weak** = both on the same side of the others' median and
≥ 0.5 community IQR away; otherwise no clear difference.

| metric | comm. p10 | p25 | p50 | p75 | p90 | ground p50 | good p50 | problem p50 | MWU p | SH (pct) | WKH (pct) | our others median | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| platform viewers / spawn spot | 5.4 | 7.1 | 8.58 | 9.46 | 10.41 | 8.37 | 7.76 | 8.7 | 0.67 | 6.75 (21) | 7.12 (25) | 3.11 | weak |
| spawn spots hidden from platform % | 0 | 1.25 | 7.7 | 21.14 | 34.23 | 8.22 | 15.95 | 32.48 | 0.5 | 20.1 (74) | 19.25 (74) | 35.15 | weak |
| angle platform end -> base (deg) | 19.92 | 26.32 | 30.52 | 32.34 | 33.56 | 30.65 | 29.85 | 27.25 | 0.31 | 27.1 (28) | 25.9 (24) | 27.45 | no clear difference |
| spawn square within +-1 of mode | 0.37 | 0.44 | 0.56 | 0.82 | 0.92 | 0.73 | 0.46 | 0.48 | 0.67 | 0.98 (94) | 0.99 (94) | 1 | no clear difference |
| spawn roughness (mean abs dz) | 0.08 | 0.2 | 0.56 | 0.93 | 1.37 | 0.37 | 0.85 | 0.93 | 0.63 | 0.1 (13) | 0.02 (3) | 0 | no clear difference |
| cover>=3 share, 0-8 enemy side | 0 | 0 | 0.12 | 0.3 | 0.74 | 0.12 | 0.19 | 0.12 | 0.66 | 0.31 (76) | 0.45 (82) | 0.16 | weak |
| cover>=3 share, 8-20 enemy side | 0 | 0.02 | 0.13 | 0.31 | 0.68 | 0.16 | 0.25 | 0.11 | 0.32 | 0.35 (80) | 0.41 (83) | 0.17 | weak |
| cover>=3 share, 8-20 lateral | 0 | 0.06 | 0.21 | 0.34 | 0.53 | 0.22 | 0.27 | 0.29 | 0.75 | 0.41 (80) | 0.18 (47) | 0.24 | no clear difference |
| cover>=3 share, 20-40 rear | 0 | 0 | 0.09 | 0.24 | 0.52 | 0.18 | 0.12 | 0.22 | 0.68 | 0.42 (85) | 0.72 (94) | 0.23 | weak |
| spawn exit min cut (cells) | 47.45 | 71.12 | 111 | 140.25 | 156 | 132 | 119.5 | 127 | 0.66 | 120 (56) | 92 (39) | 99.5 | no clear difference |
| spawn spots seen from own tower-zone ground | 0.47 | 0.66 | 0.83 | 0.97 | 1 | 0.87 | 0.71 | 0.82 | 0.68 | 0.99 (85) | 1 (95) | 0.95 | no clear difference |
| spawn spots seen from centre ground | 0.05 | 0.32 | 0.59 | 0.85 | 0.96 | 0.6 | 0.56 | 0.5 | 0.89 | 0.99 (92) | 1 (97) | 0.89 | no clear difference |
| front height vs spawn (blocks) | -10.54 | -2.86 | 0.06 | 2.06 | 7.09 | 0.34 | 0.02 | -2.44 | 0.34 | 0.69 (63) | 1.68 (70) | 0.93 | no clear difference |
| front flat share (+-1 of median) | 0.15 | 0.29 | 0.56 | 0.77 | 0.87 | 0.64 | 0.54 | 0.6 | 0.63 | 0.97 (97) | 0.88 (91) | 0.68 | weak |
| front object share | 0.06 | 0.16 | 0.33 | 0.49 | 0.66 | 0.26 | 0.41 | 0.29 | 0.51 | 0.03 (6) | 0.12 (19) | 0.2 | no clear difference |
| front objects (count) | 1 | 2 | 4 | 6.5 | 9.15 | 4.25 | 4.5 | 1.75 | 0.05 | 2 (24) | 2 (24) | 4 | no clear difference |
| front object height p90 | 4 | 8 | 12.75 | 23.62 | 34.5 | 11 | 15.5 | 24.25 | 0.07 | 17.8 (61) | 15 (54) | 27 | weak |
| front min free share per 8-col section | 0 | 0 | 0.12 | 0.45 | 0.72 | 0.35 | 0.12 | 0.03 | 0.53 | 0.73 (91) | 0.37 (69) | 0.4 | no clear difference |
| build gap (blocks) | 25.6 | 38 | 49 | 53.88 | 56 | 48 | 51.5 | 47.5 | 0.54 | 41 (30) | 42 (31) | 47.5 | no clear difference |
| front LOS toward platform | 29.32 | 40.4 | 58.7 | 81.85 | 107.67 | 56.45 | 53.55 | 74.25 | 0.24 | 88.3 (78) | 106.85 (90) | 63.8 | weak |
| min gap under platform (blocks) | 6.7 | 20 | 32 | 43 | 48 | 32 | 32 | 18 | 0.15 | 39 (67) | 36 (55) | 38 | no clear difference |
| under-platform object share | 0.01 | 0.18 | 0.32 | 0.51 | 0.66 | 0.23 | 0.41 | 0.31 | 0.34 | 0.02 (11) | 0.01 (10) | 0.16 | no clear difference |
| central zone object share | 0.07 | 0.16 | 0.26 | 0.37 | 0.48 | 0.23 | 0.32 | 0.29 | 0.32 | 0.24 (44) | 0.15 (22) | 0.25 | no clear difference |
| central objects per 10k cols | 1.61 | 3.34 | 6.86 | 12.76 | 18.28 | 9.84 | 8.72 | 2.5 | 0.03 | 34.14 (96) | 30.25 (95) | 15.4 | weak |
| central object height p90 | 8 | 12.73 | 21 | 31 | 41.9 | 17.4 | 25.3 | 26.8 | 0.61 | 35 (80) | 11 (20) | 23.5 | no clear difference |
| central built volume / col | 0.34 | 1.21 | 2.26 | 3.92 | 6.16 | 1.71 | 3.05 | 4.32 | 0.84 | 3.77 (74) | 0.83 (17) | 3.23 | no clear difference |
| gap between objects p50 | 2.33 | 4 | 6 | 10 | 16 | 8 | 6 | 2.83 | 0.56 | 6 (53) | 8 (66) | 6 | no clear difference |
| largest empty disk diam | 16 | 24.1 | 32.95 | 52.35 | 79.25 | 51.95 | 31.1 | 35.3 | 0.86 | 51.1 (73) | 68 (86) | 53 | no clear difference |
| central indoor share | 0 | 0.03 | 0.1 | 0.22 | 0.32 | 0.08 | 0.12 | 0.26 | 0.44 | 0.2 (72) | 0.02 (21) | 0.17 | no clear difference |
| central multi-level share | 0 | 0 | 0.02 | 0.07 | 0.21 | 0.01 | 0.02 | 0.02 | 0.98 | 0.05 (66) | 0.01 (44) | 0.01 | no clear difference |
| central crossing width (cells) | 0 | 13 | 45.5 | 87 | 124.7 | 73.5 | 44 | 24.5 | 0.56 | 123 (90) | 94 (79) | 74.5 | no clear difference |
| central LOS mean | 36.94 | 45.02 | 58.4 | 72.68 | 87.26 | 60.65 | 55.8 | 59.6 | 0.44 | 43.9 (22) | 64.5 (60) | 45.05 | no clear difference |
| central cells seen from platform ends | 0.25 | 0.31 | 0.44 | 0.56 | 0.66 | 0.45 | 0.42 | 0.42 | 0.73 | 0.4 (44) | 0.59 (81) | 0.47 | no clear difference |
| whole-map crossing width | 0 | 14.25 | 55 | 111 | 253.6 | 170 | 72 | 28.5 | 0.56 | 222 (88) | 115 (77) | 168 | no clear difference |
| map land share | 0.14 | 0.22 | 0.34 | 0.84 | 1 | 0.96 | 0.37 | 0.67 | 0.58 | 1 (96) | 0.51 (67) | 0.98 | no clear difference |

Additional community distributions (main set, p10/p25/p50/p75/p90): roof columns in the spawn square
0/0/66/186/353 of 1681; central object footprint p50 14/24/40/127/468 cells (ours: SH 19, WKH 10, FH 21, HC 16,
GF 7, BK 60, WI 9, HF 45, DC2 15, HV 110, Hf 15, KS 41).

### Our maps on the same metrics (value, community percentile)

SH Silverpine Hunt v2.2, WKH Wicker King's Harvest v1.1, FH Frostbell Hollow v1.1, HC The Hollow Crown v1.1,
GF Graveyard of the Forgotten v1.0, BK Bloomhop Kingdom v1.0, WI Witchwood Isles v1.0, HF Haunted Fairground v1.3,
DC2 Drowned Cathedral v2, HV Hollowfen Vale v1, Hf Hollowfen (art v1), KS Kestrel Spires (art v3). All are
stock-fit; classes: KS sky_bridge, WI/HF island, rest ground.

| metric | SH | WKH | FH | HC | GF | BK | WI | HF | DC2 | HV | Hf | KS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| platform viewers / spawn spot | 6.75 (21) | 7.12 (25) | 1.67 (1) | 0.01 (1) | 5.12 (9) | 2.6 (3) | 0.54 (1) | 9.81 (84) | 3.62 (4) | 10.13 (88) | 7.4 (29) | 0.21 (1) |
| spawn spots hidden from platform % | 20.1 (74) | 19.25 (74) | 58.5 (96) | 99.45 (99) | 16.2 (70) | 32.9 (88) | 78.9 (99) | 0 (9) | 37.4 (91) | 0 (9) | 8.5 (52) | 87.4 (99) |
| spawn square within +-1 of mode | 0.98 (94) | 0.99 (94) | 1 (98) | 1 (98) | 1 (98) | 1 (98) | 1 (98) | 0.94 (91) | 1 (98) | 0.63 (58) | 1 (98) | 1 (98) |
| spawn roughness | 0.1 (13) | 0.02 (3) | 0.04 (6) | 0 (2) | 0 (2) | 0.02 (3) | 0 (2) | 0.08 (11) | 0 (2) | 0.12 (15) | 0 (2) | 0 (2) |
| cover>=3, 0-8 enemy side | 0.31 (76) | 0.45 (82) | 0.1 (48) | 0.08 (46) | 0.47 (84) | 0.19 (60) | 0.53 (87) | 0.01 (33) | 0.54 (88) | 0 (14) | 0.13 (53) | 0.28 (73) |
| cover>=3, 8-20 enemy side | 0.35 (80) | 0.41 (83) | 0.26 (69) | 0 (9) | 0.21 (63) | 0.71 (92) | 0.6 (89) | 0 (20) | 0.01 (22) | 0.01 (23) | 0.34 (78) | 0.14 (53) |
| cover>=3, 20-40 rear | 0.42 (85) | 0.72 (94) | 0.29 (78) | 0.26 (76) | 0.17 (63) | 0.63 (92) | 0.21 (68) | 0.26 (76) | 0.15 (59) | 0.43 (86) | 0.09 (50) | 0.07 (47) |
| spawn exit min cut | 120 (56) | 92 (39) | 101 (44) | 84 (35) | 58 (16) | 132.5 (65) | 67 (22) | 112 (51) | 98 (44) | 124 (58) | 126 (59) | 98 (44) |
| spawn seen from centre ground | 0.99 (92) | 1 (97) | 0.97 (91) | 1 (93) | 0.94 (84) | 0.95 (86) | 0 (3) | 1 (93) | 0.68 (56) | 0.84 (73) | 0.53 (43) | 0 (3) |
| front flat share | 0.97 (97) | 0.88 (91) | 0.87 (90) | 0.84 (87) | 0.95 (95) | 0.58 (55) | 0.05 (2) | 0.55 (48) | 0.9 (91) | 0.66 (63) | 0.7 (67) | 0.05 (2) |
| front object share | 0.03 (6) | 0.12 (19) | 0.17 (28) | 0.16 (25) | 0.05 (8) | 0.3 (45) | 0.56 (82) | 0.35 (54) | 0.09 (16) | 0 (1) | 0.3 (43) | 0.22 (36) |
| front objects (count) | 2 (24) | 2 (24) | 15 (97) | 5 (61) | 1 (10) | 3 (35) | 9 (89) | 3 (35) | 2 (24) | 1 (10) | 8 (82) | 11 (95) |
| front object height p90 | 17.8 (61) | 15 (54) | 24 (76) | 34 (89) | 25 (79) | 29 (84) | 37 (92) | 5 (14) | 19 (64) | 2 (1) | 33 (88) | 43 (95) |
| front min free share / 8-col | 0.73 (91) | 0.37 (69) | 0.58 (81) | 0 (17) | 0.56 (80) | 0.07 (45) | 0 (17) | 0.37 (69) | 0.43 (72) | 0.98 (99) | 0.52 (80) | 0 (17) |
| build gap | 41 (30) | 42 (31) | 47 (43) | 40 (28) | 42 (31) | 50.5 (56) | 37 (24) | 48 (47) | 37 (24) | 55 (83) | 54 (77) | 54 (77) |
| front LOS toward platform | 88.3 (78) | 106.85 (90) | 99.9 (85) | 118.65 (95) | 56.25 (46) | 71.35 (65) | 47.35 (35) | 40.05 (24) | 42.25 (29) | 113.6 (92) | 38 (23) | 71.6 (66) |
| min gap under platform | 39 (67) | 36 (55) | 46 (85) | 40 (70) | 14 (17) | 38 (64) | 38 (64) | 11 (15) | 16 (18) | 48 (90) | 35 (54) | 54 (95) |
| under-platform object share | 0.02 (11) | 0.01 (10) | 0.01 (10) | 0 (5) | 0.37 (58) | 0.52 (75) | 0.08 (17) | 0.3 (49) | 0.64 (89) | 0.03 (11) | 0.23 (37) | 0 (5) |
| central object share | 0.24 (44) | 0.15 (22) | 0.2 (35) | 0.26 (51) | 0.16 (25) | 0.33 (64) | 0.09 (15) | 0.24 (46) | 0.32 (64) | 0.22 (37) | 0.37 (75) | 0.26 (51) |
| central objects per 10k | 34.14 (96) | 30.25 (95) | 29.69 (94) | 9.84 (67) | 12.8 (75) | 22.64 (92) | 7.61 (53) | 6.12 (47) | 18 (90) | 30.25 (95) | 21.53 (91) | 11.13 (71) |
| gap between objects p50 | 6 (53) | 8 (66) | 11.31 (81) | 4 (29) | 6 (53) | 7.21 (62) | 8 (66) | 4 (29) | 4 (29) | 6 (53) | 4.47 (43) | 10 (76) |
| largest empty disk diam | 51.1 (73) | 68 (86) | 57.3 (79) | 108.3 (96) | 72.5 (89) | 48.7 (70) | 22 (19) | 34 (51) | 62.6 (83) | 76 (89) | 30 (40) | 30.5 (42) |
| central indoor share | 0.2 (72) | 0.02 (21) | 0.17 (65) | 0.22 (75) | 0.05 (29) | 0.25 (81) | 0.14 (59) | 0.28 (85) | 0.09 (45) | 0.17 (64) | 0.26 (82) | 0.05 (30) |
| central crossing width | 123 (90) | 94 (79) | 176 (96) | 85 (72) | 46 (50) | 77 (68) | 7 (18) | 76 (67) | 8 (19) | 125 (90) | 73 (66) | 0 (8) |
| central LOS mean | 43.9 (22) | 64.5 (60) | 57.7 (47) | 43.1 (20) | 47 (29) | 39.8 (16) | 67.6 (65) | 47.2 (29) | 36.8 (10) | 42.3 (19) | 29.5 (4) | 49.9 (34) |

## 6. What SH and WKH share (that our other maps lack), zone by zone

N = 2 vs 10. Every item below is "weak" by the rule in §5; **none is "clear"**.

* **Spawn: a middle exposure band, not the extreme.** SH 6.75 viewers / 20 % hidden, WKH 7.1 / 19 %. Both sit near
  the community median for viewers (p21–25) and p74 for hidden. Our other maps are spread to the extremes: HC 0.01 /
  99 %, WI 0.5 / 79 %, KS 0.2 / 87 %, FH 1.7 / 59 % on one side; HV 10.1 / 0 % and HF 9.8 / 0 % on the other. This is
  the most consistent benchmark trait, but whether the extremes play worse is a playtest question.
* **Spawn: cover concentrated on the enemy side plus a rear backdrop.** cover3 on the enemy side is 0.31–0.45 in the
  0–8 ring and 0.35–0.41 in the 8–20 ring (community p50 0.12–0.13, p76–83). Rear backdrop at 20–40 is 0.42 and 0.72
  (community p50 0.09; others median 0.23; no other map of ours is above both). GF, DC2 and WI also have high near
  enemy-side cover, so near cover alone does not single out the benchmarks.
* **Spawn: no difference** in floor height, angle (26–27°), flatness (all our maps are 0.94–1.0 near-mode, see 7.1),
  exit min cut, or visibility from the centre ground (almost all ours ≥ 0.9).
* **Front: open, flat, long sightlines, few low-ish objects.** Flat share 0.97 / 0.88 (others median 0.68), LOS
  toward the platform 88 / 107 (others 64), objects 2 / 2 with height p90 18 / 15 (others p90 median 27). These
  maps predate the 2026-11-10 "dress the front" rule, so this describes the old bare-front style, not a target.
* **Front: no difference** in build gap (41–42; others 37–55), height vs spawn, land width, front object share.
* **Centre: many small objects.** 34 / 30 objects per 10k columns (community p50 6.9, p90 18). Several of our other maps
  are also high (FH 30, HV 30, BK 23, Hf 22), so this is a house-style trait rather than a benchmark trait.
* **Centre: no difference** in object share, gaps (6 / 8), largest empty patch, indoor share, crossing width, LOS.
  The two benchmarks differ a lot from each other here: WKH has low built volume (0.83), low indoor share (0.02) and
  short objects (p90 11); SH has 3.8, 0.20 and 35.
* **Under the platform: both are empty** (object share 0.01–0.02, gap 36–39). FH, HC and HV are too. So emptiness
  under the platform does not distinguish the benchmarks either.

## 7. Where our maps sit against the community (all 12)

1. **Spawn floors are flatter than almost every community map.** Near-mode share is 0.94–1.0 for 11 of 12 (p91–98),
   and roughness is 0–0.12 (p2–15). Community p50 is 0.56 and 0.56 (ground maps: 0.73 and 0.37). This holds even
   though AGENTS.md says spawns should be "not 100 % flat".
2. **Fronts are flatter and emptier.** Front flat share is 0.84–0.97 in 7 maps (community p50 0.56), and front object
   share is 0–0.17 in 7 maps (community p50 0.33, ground 0.26, good 0.41).
3. **Under-platform strips are emptier.** 8 of 12 are ≤ 0.08 object share (community p50 0.32; p25 0.18). The minimum
   gap to the platform is in the normal range (community p50 32).
4. **Centre objects are smaller and more numerous.** Footprint p50 is 7–21 cells for most maps (community 40), and
   objects per 10k columns are p67–96.
5. **Spawn spots are visible from the centre ground** (0.84–1.0 for 8 maps; community p50 0.59). Fog-limited LOS
   from x 212–300 at standing eye height.
6. **Our two water/structure-heavy maps fail on crossing:** DC2 crossing width 8 and WI 7 (community p50 45.5, ground
   73.5). KS 0 (sky).
7. Spawn exit min cut is lowest on GF (58, p16) and WI (67, p22). Neither is sealable by the ≤ 10 definition.

## 8. Exemplars (patterns, not art)

The selection criteria are stated in `tools/babel_zone_analysis.py`. Guide-problem maps are excluded, and good/rotation
maps are listed first. Thumbnails are in `out/zone_study/thumbs/<zone>_<map>.png` (numpy previews).

**Spawn**: viewers ≤ 9, hidden ≥ 15 %, not sealable, ≤ 20 roof and water columns. **6 pass** (matrix_babel also passes
but is a guide problem, for pillar lag):
* makewar (good, ground): the spawn sits in a round basin, 0.82 roughness, only 42 % near-mode. Its rim and boulders
  give cover3 of 63 % / 69 % on the enemy side and 66 % lateral. 7.7 viewers, 25 % hidden, exit min cut 94.5.
* hexclimb (rotation, island): a high ridge on the enemy side only (76–78 % cover), open laterally and behind;
  3.8 viewers, 60 % hidden. The guide warns its height may make rounds quick.
* 2keep (rotation, island): uneven floor (22 % near-mode), no enemy-side cover; hidden 34 % comes from terrain
  relief, with lateral cover of 33 %. Exit min cut 52.5.
* holes_hills (rotation, ground): rolling floor (29 % near-mode, roughness 0.6) with evenly spread 22–27 % cover on
  all sides; 8.3 viewers, 15 % hidden.
* BlueHouseCoreaBabel2 (island): flat floor (100 % near-mode) with 34–46 % enemy-side cover and 33 % rear backdrop;
  7.0 viewers, 28 % hidden, exit min cut 154.
* dedust2x2 (ground): roughness 1.06, cover 29–37 % front and lateral, none behind; 8.2 viewers, 21 % hidden.

**Tower zone / front**: no water under the anchor, land width ≥ 32, object share 0.05–0.30, object height p90 ≤ 10,
min free share per 8-column section ≥ 0.5, build gap 15–55, front within ±6 of the spawn. **11 pass; none of our
12 maps passes** (ours fail on object height or on object share/free share).
* roadisland (good): a straight road through the band with ~4 vehicle-sized objects (p90 6 high, 20 % cover). The
  front is 80 % flat and every 8-column section keeps ≥ 64 % free ground. Build gap 47.
* royalparadenight (rotation): 8 low objects (p90 10, 16 % cover) along a flat street (84 % flat), ≥ 66 % free per
  section, LOS toward the platform 88.
* 1river2forts (rotation, ground): 4 low objects (p90 5.5, 8 %) on a 92 % flat bank, build gap 52.5.
* greencoast (ground): 15 small objects (p90 6) covering only 5 %, with ≥ 87 % free per section. This is the "many
  small low details" pattern closest to the 2026-11-10 rule.
* BusanPortBabel, Stormhaven_Babel, rorkesdrift_babel, EgliseBabelV2 (rising +5.9 toward the platform),
  cloudsmash_babel, alamo_babel, TwoMafiasBridged: same band of 4–16 objects, 5–23 % cover, height p90 ≤ 10.

**Centre**: object share ≥ 0.12, crossing width ≥ 40, gap p50 6–14, flank exists, LOS mean ≤ 60. **12 pass**
(stackattack also passes but is a guide problem):
* hezeehills (good, ground): a grid of short free-standing wall segments and pavilions with 6-voxel gaps, a long
  building under the platform (54 % of the strip, gap 32), 43 % object cover, LOS mean 35.5, crossing width 87.
* babelpocalypse (good): 24 % cover, 12.6 objects/10k, a hill under the platform (gap 7), crossing 91.
* yukon (good): 30 % cover, gaps 8.5, 28 % of the strip under the platform covered (gap 40), multi-level 8 %.
* yarr (good): dense (65 % cover), few large objects (2.8/10k), 33 % indoor, 34 % multi-level, crossing 122, gap 7
  under the platform.
* binladenfire3, ruins_onigiri, HolidayResortBabel, vippers_nes, GrozniiBabel, Stormhaven_Babel, CooolzgradeCity,
  SOLO_Babel: 16–46 % cover, gaps 6–11, crossing 72–148, LOS mean 40–58.

Our maps pass the spawn criteria in 9 of 12 cases (not HF, HV, Hf) and the centre criteria in 5 (SH, FH, GF, BK, HV).
None pass the front criteria.

## 9. Proposed guidance

> **Owner decision `[USER 2026-11-13]`:** items **7, 2, 11 and 12** are adopted as standing rules (AGENTS.md §4).
> The other items remain proposals. The kit still reports all of them without pass or fail.

Each item gives a target, its evidence, its relation to an existing rule and a possible kit check. These are
proposals for the reviewer/owner, not rules. Kit checks would read `R['zone_profile']`.

### Spawn
1. **Exposure band: platform viewers 5–9 and hidden 15–40 % (soft), never above ~75 %.** `[RUN]` SH/WKH 6.75–7.1 /
   19–20 %; community p25–p75 viewers 7.1–9.5, hidden p75 21 / p90 34; good p50 7.8 / 16 %. Among the 48 guide-labelled
   main-set maps the most hidden is hezeehills (good) at 75 %. Next come problem maps at 56–68 % (stackattack,
   matrix_babel, AtlasNovus), so a high hidden share is not a quality sign. HC (99 %) and KS (87 %) are above every
   labelled map. Relation: **refines** "≤ ~10 viewers, ≥ 15 % hidden" by adding an upper bound. Weak evidence (N = 2,
   and good vs problem p = 0.5–0.67). Check: `avg.spawn.platform_viewers_mean`, `platform_hidden_pct`.
2. **Enemy-side cover ring: cover3 ≥ 0.25 in the 0–8 and 8–20 enemy-facing rings, plus a rear backdrop ≥ 0.3 in
   20–40.** `[RUN]` SH/WKH 0.31–0.45, 0.35–0.41, 0.42–0.72; community p75 0.30–0.31 / 0.24; good p50 0.19 / 0.25.
   Relation: **confirms and quantifies** "cover spawns with trees, walls, buildings or terrain, but not inside the ±20
   square". Check: `avg.spawn.enclosure.r*_enemy_cover3`, `r20_40_rear_cover3`.
3. **Spawn floor relief: near-mode share 0.6–0.9 and roughness 0.15–0.5.** `[RUN]` Community ground p50 0.73 / 0.37,
   all p50 0.56 / 0.56; our maps 0.94–1.0 / 0–0.12 (p2–15). Good maps are rougher (0.85), but not significantly
   (p = 0.63). makewar and holes_hills are the patterns (basin, rolling floor). Relation: **refines** "spawns not
   100 % flat but easy to spawn on (gentle mounds, no holes)"; we currently do not meet our own rule by this measure.
   Possible tension with "easy to spawn on" and "no holes": keep the kit's pit/trap checks. Check: `near_mode_share`,
   `roughness`.
4. **Exit min cut ≥ 60 cells** (flag ≤ 40; sealable ≤ 10). `[RUN]` Community p10 47, p25 71, p50 111; ours 58–132.
   `[DERIVED]` thresholds. Relation: **quantifies** "no sealable single-exit spawns". Check: `exit_min_cut`.
5. **Do not copy roof columns into spawn squares.** `[RUN]` Community squares often contain roof/canopy columns
   (p50 66 of 1681, p75 186). lard (guide: spawn on roofs) has ~850. Relation: **confirms** our stricter rule (0 roofs).
   No change proposed. Check: `roof_cols` (already in `spawn_squares`).
6. *Observation, not a proposal:* spawn spots seen from the centre ground at eye height (fog 128) are 0.84–1.0 on 8
   of our maps vs a community p50 of 0.59. If the owner wants less centre-to-spawn harassment, a target of ≤ 0.8 is the
   community p63. `[DERIVED]` No label evidence (good 0.56 vs problem 0.50, p = 0.89).

### Tower zone / front
7. **Dress the front with 4–15 low objects: object share 0.05–0.30, object height p90 ≤ 10, every 8-column section
   ≥ 50 % free.** `[RUN]` Front exemplars (11 maps incl. roadisland, good). Community front objects p50 4 (p25–p75
   2–6.5). Height p90: community p50 12.75, good 15.5 vs problem 24 (p = 0.075, weak). Ours: SH 0.03 share / 2
   objects, WKH 0.12 / 2, and our height p90 is 15–43. Relation: **confirms and quantifies** the 2026-11-10 "dress the
   front, never block it… nothing tall" rule. Check: `avg.front.object_share`, `objects`, `object_h.p90`,
   `free_share_min_section8`.
8. **Front flat share 0.55–0.85 (some relief, no walls).** `[RUN]` Community p50 0.56, p75 0.77, ground 0.64. Ours
   0.84–0.97 for 7 maps. `[DERIVED]` Relief adds cover without blocking. Relation: **refines** "fronts must be open";
   also compatible with "don't default to a raised tower zone", since the front height vs spawn stays within ±3
   (community p25–p75 −2.9..+2.1). Check: `flat_share`, `raised_vs_spawn`.
9. **Build gap 38–54 blocks for standard Babel.** `[RUN]` Community p25–p75 38–54, p50 49; benchmarks 41–42; good 51.5
   vs problem 47.5 (p = 0.54). Relation: **confirms** current practice (§8.5 references). Check: `build_gap_blocks`.
10. **Front LOS toward the platform 40–90 (median).** `[RUN]` Community p25–p75 40–82. Ours are 88–119 on 5 maps.
    `[DERIVED]` This is a side effect of item 7, not an independent target. Relation: none. Check:
    `los_toward_platform_mean`.

### Centre
11. **Put low objects under the platform: strip object share 0.15–0.45, min gap to the platform ≥ 25.** `[RUN]`
    Community p25–p75 0.18–0.51, good p50 0.41. Gap: community p50 32, good 32 vs problem 18 (p = 0.15, weak).
    8 of our 12 maps are ≤ 0.08 (both benchmarks included). Relation: **refines** "don't leave the centre empty".
    **Conflicts in part** with knowledge base §8.5, which says "most rated maps put some central feature under the
    platform (gaps 4–15)": measured, only p10 is below 7, and the median gap is 32. **Interacts with** the
    free-scaffolding check and with "no authored ramp to the tower": objects must not shorten the gap below the
    standard range unless the map is the assist variant. Check: `centre.strip.object_share`, `min_gap_to_platform`.
12. **Fewer, larger central objects alongside the vegetation: object footprint p50 ≥ 25 cells, objects per 10k
    3–20.** `[RUN]` Community footprint p50 40 (p25 24), objects/10k p50 6.9 (p90 18). Good 8.7 vs problem 2.5 is the
    only p < 0.05 result (0.029), and it is not robust to the 48 tests. Ours: footprint 7–21, objects/10k up to 34.
    `[DERIVED]` Very low counts (problem maps) and very high counts of tiny objects are both atypical. Relation:
    **refines** "pack the centre with distinct objects… loves unique one-off objects": keep the one-offs, but anchor
    them with a few room-sized pieces. Check: `centre.zone.object_footprint.p50`, `objects_per_10k`.
13. **Gaps between objects p50 6–10.** `[RUN]` Community p50 6, ground 8, p75 10; good 6 vs problem 2.8. Relation:
    **confirms** "7–10 voxel gaps" (community-typical is slightly tighter, 6). Check: `centre.zone.gap_width.p50`.
14. **Central crossing width ≥ 40 cells (graph min cut), whole-map ≥ 60.** `[RUN]` Community p50 45.5 (ground 73.5),
    good 44 vs problem 24.5 (p = 0.56). DC2 8, WI 7 and KS 0 are below community p20. Relation: **quantifies** "centre
    traversal easy on foot, many openings, not a labyrinth". Check: `centre.zone.crossing_width`,
    `routes.map_crossing_width`.
15. **Central LOS mean 40–75.** `[RUN]` Community p25–p75 45–73, ground p50 61. Hf 29.5 (p4) and DC2 36.8 (p10) are
    the tightest. Relation: **refines** "not a labyrinth". Check: `centre.zone.los_mean`.
16. **Largest empty disk in the central zone ≤ 60.** `[RUN]` Community p75 52, ground p50 52, good p50 31; HC 108 (p96).
    WKH (68) would fail this, so it is weak and conflicts with a benchmark. Relation: **refines** "don't leave the centre
    empty". Check: `centre.zone.largest_empty_diam`.

### Conflicts and tensions (flagged, not resolved)
* Item 3 vs "easy to spawn on / no holes": more relief raises the risk of pits. Needs the pit/trap checks.
* Item 1's upper hidden bound vs the existing "≥ 15 % hidden" rule: the rule has no upper bound, and HC (99 %) passes it.
* Item 11 vs knowledge base §8.5 "gaps 4–15" wording; item 11 vs the free-scaffolding check (objects under the platform
  shorten the build if tall).
* Item 16 vs WKH (a benchmark) at 68.
* AGENTS.md "Balanced spawns… mirrored" vs the corpus: 142 of 226 community Babel maps are not mirrored under our
  threshold (normandie, hezeehills, babelpocalypse among the good ones). No change proposed; it only means
  "mirrored" is our house rule, not a community norm.
* "Spawn camping from the platform" rules vs "open fronts" (already noted in AGENTS.md): items 7–8 add front cover,
  which helps both.

### Zone rules: the adopted items as kit checks (2026-11-13)

The owner adopted items 7, 2, 11 and 12 as standing rules (AGENTS.md §4). `babel_checks.run_all` checks them in
`R['zone_rules']` (`aosmap.kit.zones.zone_rules`) and adds four pass/fail rows to `summary()`. Thresholds are in
`params.ZONE_RULES` and can be overridden per call. Every rule is measured per team; the mirrored average is in `avg`.

**Objects.** When the map supplies `terrain_H`, ground = the higher of the terrain_H surface and the 25-window
opening baseline (`object_ground: 'terrain_H'`). Otherwise ground = the opening baseline, and each 8-connected
candidate component (≥ 2 above ground, not water) is kept only if ≥ 50 % of its boundary steps are ≥ 2 tall, or it has
an overhang (`'estimated'`). Gentle terrain with 1-voxel steps is relief, not an object. An object is a component of
≥ 4 cells. **Not applicable**: a zone whose land share is < 0.5 (front: not water and ≤ 19 below the spawn floor).
A declared `zone_rules_skip` / `build['zone_rules_skip']` prints `SKIP` with its reason.

| rule | metric keys (`R['zone_rules'][rule]['values'][team]`) | pass when (every applicable team) | exemption |
|---|---|---|---|
| `front_dressing` | `objects`, `object_share`, `object_heights`, `low_share`, `section_free_min` (+ `worst_section_x`) | 4 ≤ objects ≤ 15; 0.05 ≤ share ≤ 0.30; low_share (share of objects whose max height above ground ≤ 10) ≥ 0.90; every 8-column section ≥ 0.50 walkable | `build['front_exempt_boxes']`: those columns are left out of objects/share/heights, reported in `front_exempt` (object share, max height, open share), and still counted in the section test |
| `spawn_cover` | `enemy_0_20` (+ `enemy_0_8`, `enemy_8_20`, `rear_20_40`, `enemy_0_20_land_only`) | enemy_0_20 ≥ 0.25 and rear_20_40 ≥ 0.30 | — |
| `under_platform` | `object_share`, `min_air_all` (+ `min_air_objects`, `object_height_max`), `anchors[team].top_z_range`, `prop_cols` | 0.15 ≤ share ≤ 0.45; min_air_all ≥ 25; both anchors range ≤ 1 and prop_cols = 0 | — |
| `centre_footprint` | `footprint_p50` (+ `objects`, p25/p75, `objects_ge_25_cells`) | footprint_p50 ≥ 25 cells | — |

Definitions, and how ambiguous wording was resolved:
* **Front band**: x 139–211 / 300–373, y 236–276. It includes the anchor columns, which `under_platform` separately
  requires to be prop-free. An object counts if it touches the band. Its share is its cells inside the band divided by
  the band's non-exempt cells.
* **"90 % of them no taller than 10"** is read per object: the max height above ground of each object in the band.
  The share of objects ≤ 10 must be ≥ 0.90, so with fewer than 10 objects a single taller one fails.
  The per-cell p90 is also reported (`cell_height_p90`) but does not decide the rule.
* **"Every 8-column north–south section ≥ 50 % free"**: the band is cut into 8-column slices counted from the spawn
  edge; the last 9 columns form one slice, so there is no 1-column remainder. A cell is free when it has a standable cell within ±1 of the ground
  surface and is not water. Walking under an arch counts as free; a prop top does not.
* **Spawn cover** follows the AGENTS.md wording: **one combined share** over the enemy-facing ground 1–20 voxels
  (Chebyshev) outside the square. The study's per-ring rows (0–8, 8–20) are reported but do not decide the rule.
  * Enemy side is the wedge beyond the square's enemy-facing edge where forward distance ≥ lateral overhang; the
    rear is the mirrored wedge at 21–40.
  * Cover means the column top rises ≥ 3 above the spawn floor (the median top z of the square).
  * The denominator is all cells, water included. `enemy_0_20_land_only` is reported for island spawns.
* **Under the platform**: "≥ 25 voxels of air between their tops and the platform" is checked over **every**
  strip column, not only objects (the intent is that nothing becomes free scaffolding). Air = top z − platform z − 1.
  * "Low" has no separate height cap; the air rule bounds it.
  * The anchor ends are the 6 columns under each platform end, x 206–211 / 300–305, y 240–271. "Flat" means top-z
    range ≤ 1. "Prop-free" means no object, roof or deck column.
  * If the strip is not land but the anchors are, only the anchors are judged and the reason says the strip part
    was n.a.
* **Centre**: the footprint is the whole size of each object (≥ 4 cells, 8-connected) that touches x 150–362,
  y 130–382, even where it extends outside the zone. Zero objects is a fail.

**Baseline [RUN 2026-11-13]**: the files from this study, unchanged. "est." = estimated ground, since none of the
`maps/` folders ship `terrain_H.npy`. Frostbell uses its gatehouse exemption, `[[146,151,220,292],[361,366,220,292]]`.
Values are the mirrored average unless the teams differ.

| map | front dressing | spawn cover | under the platform | centre footprint |
|---|---|---|---|---|
| Silverpine Hunt v2.2 | FAIL: 2 objects (< 4), share 0.03, 0/2 ≤ 10 tall (20, 23); sections ≥ 0.98 | PASS: 0.34 / rear 0.42 | FAIL: share 0.021 < 0.15; air 39; anchors ok | FAIL: 19 |
| Wicker King's Harvest v1.1 | FAIL: 2 objects, share 0.12, 0/2 ≤ 10 (16, 16); sections ≥ 0.93 | PASS: 0.42 / 0.72 | FAIL: share 0.014; air 36; anchors ok | FAIL: 15.5 |
| Frostbell Hollow v1.1 (est., gate exempt) | FAIL: 10 objects, share 0.046 < 0.05 (short by 0.004), 10/10 ≤ 10; sections ≥ 0.71; gate: max 26 tall, open 0.66 | FAIL: 0.207 (short 0.043) / 0.293 (short 0.007) | FAIL: share 0.007; air 46; anchors ok | FAIL: 21 |
| Frostbell Hollow v1.1 (rebuilt, terrain_H, gate exempt) | PASS: 12 objects, share 0.051, 12/12 ≤ 10, sections ≥ 0.78 | FAIL: same | FAIL: same | FAIL: 21 |
| The Hollow Crown v1.1 | FAIL: 5 objects, share 0.16, 2/5 ≤ 10 (13, 13, 37) | FAIL: 0.026 / 0.258 | FAIL: share 0; air 40 | PASS: 25.0 |
| Graveyard of the Forgotten v1.0 | FAIL: 1 object (26 tall), share 0.05 | FAIL: 0.291 ok / rear 0.175 | FAIL: air 14 < 25 (share 0.36 ok) | FAIL: 7 |
| Bloomhop Kingdom v1.0 | FAIL: 3 objects, share 0.306 > 0.30, 0/3 ≤ 10, worst section 0.19 (blue) / 0.31 (red) | PASS: 0.54 / 0.63 | FAIL: share 0.519 > 0.45; air 38 | PASS: 60 |
| Witchwood Isles v1.0 | FAIL: 9 objects, share 0.56, 6/9 ≤ 10, a section 0.0 | FAIL: 0.576 ok / rear 0.21 | FAIL: share 0.08; anchors: blue 192 prop cols, red range 16 + 160 prop cols | N/A: central land 0.25 |
| Haunted Fairground v1.3 | FAIL: 2 objects, share 0.34, 1/2 ≤ 10, section 0.40 | FAIL: 0.004 / 0.26 | FAIL: air 11; anchors range 7, 1 prop col (share 0.29 ok) | PASS: 98 |
| Drowned Cathedral v2 | FAIL: 2 objects (13, 21), share 0.09 | FAIL: 0.18 / 0.147 | FAIL: share 0.64; air 16; anchors range 35, 38–39 prop cols | FAIL: 15 |
| Hollowfen Vale v1 | FAIL: 1 object, share 0.001 | FAIL: 0.007 / rear 0.43 ok | FAIL: share 0.028; air 48 | PASS: 110 |
| Hollowfen (art v1) | FAIL: 8 objects, share 0.29, 7/8 ≤ 10 (one 49) | FAIL: 0.272 ok / rear 0.094 | FAIL: anchors range 3, 23 prop cols (share 0.23, air 35 ok) | FAIL: 15 |
| Kestrel Spires (art v3) | N/A: front land 0.44 (sky decks) | FAIL: 0.186 / 0.075 | PASS (strip n.a., land 0.36; anchors range 0/1, no props) | PASS: 43.5 |
| roadisland (community) | FAIL: blue 3 objects (red 4), share 0.20, all ≤ 10, sections ≥ 0.61 | FAIL: 0.07–0.12 / 0.04–0.10 | FAIL: share 0.491 > 0.45; air 28; anchors range 6, 40–41 prop cols | PASS: 82 |
| greencoast (community) | FAIL: blue share 0.039 < 0.05; red 18 objects > 15; all ≤ 10 | FAIL: 0.004–0.154 / 0.08–0.24 | FAIL: share 0.117; anchors range 8–9, 23–24 prop cols | FAIL: 13 |

Of our 12 maps, as the `maps/` files stand:
* front: 0 pass, 1 n.a. Frostbell passes only with its own `terrain_H`, because the estimated ground gives 0.046.
* spawn cover: 3 pass (SH, WKH, Bloomhop).
* under the platform: 1 pass (Kestrel, strip part n.a.).
* centre: 5 pass (HC, Bloomhop, HF, HV, Kestrel), 1 n.a.

The two community front exemplars fail 3 of 4 rules each. Their fronts miss narrowly: roadisland blue has 3
objects, greencoast blue has share 0.039. Both have props on the anchor ends. So these thresholds are stricter in
combination than the community maps that suggested them. Saved in `out/zone_study/zone_rules_baseline.json`.

## 10. What was not done or verified
* No playtest and no client inspection. The proposals are measurement-based only.
* The guide labels cover 25 main-set maps. The good/problem tests are underpowered and uncorrected.
* Maps whose stock spawn squares are water or roofs (61, including 8 "good" maps) are excluded. Their real spawn
  geometry is unknown.
* `tools/kit_acceptance.py` was not rerun (it needs rebuilt map artefacts). Existing `run_all` sections are
  untouched, and only the new `zone_profile` key was added. `pytest -q`: 27 passed.
