# Floebreaker (Day / Night) — spec and validation

**Mode:** ice-floe ground Babel, stock piqueserver 1.4.2 `babel_script`. **Author field:** `shywolf91 + AI`.
**Origin:** `[recreate]` of `arctic_icebreaker.vxl` (author unknown, no `.txt` supplied), depth *Reimagine*.
Report: `docs/floebreaker_recreate_report.md`. Files: `maps/floebreaker_v1/`.

## Status ladder (honest)
| rung | day | night |
|---|---|---|
| generated / exported | yes | yes |
| parser-validated (own reader, byte round trip) | yes | yes |
| pyspades `VXLData.generate()` byte-identical | **yes** | **yes** |
| piqueserver `Map()` load, `.txt` keys read | **yes** | **yes** |
| live piqueserver (Babel mode) + 2 bots | **yes, on a dev build of the day map** (platform 3200/3200 cells, bases 118 / 394, both spawns in their zones) | not run live |
| client-inspected | **no** (numpy renders only) | **no** |
| playtested | **no** | **no** |

Not exercised by any test: `boundary_damage` (no bot walked into the sea) and the glow keys (inert on stock piqueserver).

## Layout (SPEC in `scenes/floebreaker/fb_terrain.py`)
| item | value |
|---|---|
| Island | ellipse ~178 × 196 around (256, 256), irregular coast and floes, plain surface z 59, 54.7 % land |
| Platform / bases | stock: x 206–305, y 240–271, z 1 (script-built, not in the VXL); bases (118,256) / (394,256) |
| Spawn squares | gentle ±1 mounds (z 58–59), no props; base camps sit ~34 behind each (outside the ±20 square) |
| Tower zone / front | solid ground under both platform ends (anchor land 100 %, ends flat and prop-free). Front dressed per the 2026-11-13 zone rules: 11 objects (low boulders, ice blocks, a skiff, a supply cache, a mound), 11 % of the front, p90 height 7, every 8-column section ≥ 67 % free |
| Strip under the platform | 9 low boulders, ice blocks, a cache and a skiff per side: 29 % of the strip, all ≥ 25 below the platform |
| Spawn cover | two staggered glacier fins per team (x 142–156, mirrored), crest z ~29, overlapping y spans so no straight line passes; walkable around both ends. **Declared front exemption** (see limits). Enemy-side cover within 20: 29 %; rear backdrop 20–40: 46 %: a broken ice ridge behind each spawn with exits |
| Ship | icebreaker N–S on x 244–267, bow y 58, stern y 170: hull sides 10 high, hold, three superstructure levels and a roof; hollow, glow lamps inside |
| Whale skeleton | x 242–269, y 310–424: spine, 7 rib pairs, skull gate, tail |
| Centre pack | 4 research camps (huts, tents, drums, crates, sleds, lamp posts), 4 weather towers (2 floors + roof), 2 ice-fishing huts, ponds, crevasses, ice arches, ~44 ice-spire clusters, boulder groves, penguin colonies, flag lines |
| Rim | 12 glaciers up to 26 high with ice-cave tunnels (each with a side gallery), ~38 faceted icebergs in the sea ring |
| Flank | north and south coasts (130–200 from the centre) walkable |
| Water | `water_damage` off (sea is wadeable); `boundary_damage` box x/y 28–484, damage 1 |
| Corner tag | "Floebreaker" painted on the sea floor, south-east (x 396–460, y 470–476), name only |
| Fog | day (204,184,186) rose-pearl; night (172,156,206) bright violet. Neither hue is in the palette; both are neutral between blue and red |
| `heavens_color` | day (158,200,238,255); night (46,34,104,255). Read only by the owner's setup |
| Sky decor | day: clouds, gulls, ice crystals. Night: aurora ribbons, stars, moon. All expected-floating, ≥ 64 from the platform, not over spawns or the ship |
| Glow | 213 sources (ship interior, lamps, camp lanterns, cave and crevasse crystals); light baked into the VXL, `glow_stored_colors` in the `.txt` (format inferred, knowledge base §11.4) |

## Validation (release build, decor seed 3543353394)
| check | day | night |
|---|---|---|
| reader round trip identical | yes | yes |
| floating non-sky voxels | **0** | **0** |
| floating sky decor (expected) | 46 pieces / 9,739 voxels | 36 pieces / 8,274 voxels |
| platform volume z ≤ 2 empty | yes (`check_babel`: no findings) | yes |
| spawn zone heights | z 58–59, no water | same |
| blue ↔ red spawn route cost (graph) | 260.7 both ways | same |
| land reachable from a spawn | 96.3 % | 97.2 % |
| periphery (> 130 from centre) reachable | 96.6 % | 98.0 % |
| platform reachable without building | no | no |
| build gap (both teams equal) | **52** blocks (kit; highest reachable near the platform z 54) | same |
| ship floors reachable: hold / deck / level B / bridge / roof | 100 / 100 / 100 / 94 / 100 % | same |
| spawn exposure (kit, calibrated), blue / red | **3.84 / 3.76 mean viewers**, 34.9 % / 37.4 % hidden | same |
| repo Babel rules checker (`aosmap.kit.babel_checks`, 20 rows incl. 4 zone rules, mirror, traps, interiors) | **all pass** | **all pass** |
| mirror mismatch outside declared cosmetic boxes | 0 voxels (left half built, mirrored by array copy) | 0 |
| interiors reachable and exit (15 checked: huts, towers, ship floors) | 15 / 15 | 15 / 15 |
| trap cells | 0 | 0 |
| land top-surface luma p5 / median | 141 / 200 | 83 / 109 (measured before the last grade tweak; re-run `art_metrics`) |
| snow max channel | ≤ 212 (capped); 0 % of land below luma 40 | |

Ship-interior and route checks are a graph model, not play. The unreachable 6 % of bridge nodes are small wing alcoves.

## Known limits and trade-offs (please read)
1. **Spawn cover vs the "no walls, nothing too tall" front rule (needs your call).** Hiding ≥ 15 % of spawn spots from the platform needs ~25-tall cover in the first ~20 voxels of each team's front: with only low objects (≤ 10) I measured 1–2 % hidden, 7 % at 16 tall, 13 % at 20, 23 % at 26. I kept two staggered glacier fins (crest 29), which pass the exposure target (35–37 % hidden), and declared them as a front exemption (`front_exempt_boxes` in `build.json`, the checker's own mechanism). They are the only tall objects in the front; players can walk around both ends. If you'd rather have no walls at all, delete `FINS` in `scenes/floebreaker/fb_detail.py`: exposure then fails (≈ 1 % hidden, ≈ 9 viewers).
2. **Not an assist map.** The highest point you can reach near the platform is z 54 (52 blocks below it); nothing climbs to the platform.
3. Platform centred on 255.5 vs bases on 256 gives 6 vs 5 anchor columns (accepted in the rules) and the small blue/red exposure difference (34.9 vs 37.4 % hidden).
4. Floating sky decor can be dropped for a round by building against it and breaking that block; a reload restores it.
5. `boundary_damage` damage = 1 is a guess at "mild"; per-tick rate unmeasured. The sea inside the box is wadeable, so players can walk to the box edge.
6. Decor placement is non-deterministic by owner rule: the released build's seed is in `build.json` (3543353394). Layout seed is fixed (7311).

## Regenerate
```bash
bash scenes/floebreaker/release.sh [decor_seed]
```
That rebuilds `maps/floebreaker_v1` and runs every check, including the repo rules checker (`fb_rules.py`). It needs the repo venv python for the pyspades steps; set `VENV_PY`. To rebuild the exact released maps: `python scenes/floebreaker/fb_main.py maps/floebreaker_v1 --seed 3543353394`.
Server test config: `server_test/floebreaker/config.toml` (put the four map files in its `maps/`).
