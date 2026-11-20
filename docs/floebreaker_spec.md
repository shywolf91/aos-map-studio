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
| Tower zone | open ice plain, solid under both platform ends (anchor land 100 %), litter only inside the corridor |
| Spawn cover | two staggered glacier fins per team (x 142–156, mirrored), crest z ~29, overlapping y spans so no straight line passes |
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
| build gap (both teams equal) | **55.1** (from z 45 at (191,212)) | same |
| ship floors reachable: hold / deck / level B / bridge / roof | 100 / 100 / 100 / 94 / 100 % | same |
| spawn exposure from platform edge, blue / red | 65.1 % / 62.6 % of spots exposed, **3.8 mean viewers**, 35–37 % hidden | same |
| land top-surface luma p5 / median | 141 / 200 | 83 / 109 (measured before the last grade tweak; re-run `art_metrics`) |
| snow max channel | ≤ 212 (capped); 0 % of land below luma 40 | |

Ship-interior and route checks are a graph model, not play. The unreachable 6 % of bridge nodes are small wing alcoves.

## Known limits and trade-offs (please read)
1. **Spawn cover vs open fronts.** 62–65 % of spawn spots still see at least one platform viewer, but only ~4 viewers on average (target ≤ ~10) and 35–37 % of spots are hidden (target ≥ 15 %). Hiding more needs taller walls in the tower corridor. The fins stand in the first ~20 voxels of each team's corridor; both ends are open so players walk around them. Say if you'd rather have fewer fins and accept more exposure.
2. **Not an assist map.** The highest standable point within 60 of the platform is z 45; nothing climbs to the platform.
3. Platform centred on 255.5 vs bases on 256 gives 6 vs 5 anchor columns (accepted in the rules) and the 65.1 vs 62.6 % exposure difference.
4. Floating sky decor can be dropped for a round by building against it and breaking that block; a reload restores it.
5. `boundary_damage` damage = 1 is a guess at "mild"; per-tick rate unmeasured. The sea inside the box is wadeable, so players can walk to the box edge.
6. Decor placement is non-deterministic by owner rule: the released build's seed is in `build.json` (3543353394). Layout seed is fixed (7311).

## Regenerate
```bash
bash scenes/floebreaker/release.sh [decor_seed]
```
That rebuilds `maps/floebreaker_v1` and runs every check (needs the repo venv python for the pyspades step; set `VENV_PY`). To rebuild the exact released maps: `python scenes/floebreaker/fb_main.py maps/floebreaker_v1 --seed 3543353394`.
Server test config: `server_test/floebreaker/config.toml` (put the four map files in its `maps/`).
