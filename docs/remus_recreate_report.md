# Remoria v1: [recreate] of remus (2026-11-06)

**Status:** specified · generated · exported · parser-validated (own reader round trip byte-identical; pyspades 1.4.2
`generate()` byte-identical) · **server-loaded** (piqueserver 1.4.2, `game_modes.babel` + `babel_script`, probe below) ·
**not** client-inspected · **not** playtested. Every view in this report is a numpy preview, not a client capture.

Owner answers: Seven Hills · Reimagine · Babel only · Ruined Rome · concept **B Capitol Hill** · walkable water ·
underground + sky layer + glow · "craft a better name" → **Remoria**, the city Remus chose on the Aventine in the legend.

## 1. Original (remus.vxl, project file)
| item | value |
|---|---|
| SHA-256 | `986fa1d987605ac53fb4f7bdc7e1fda63ef8612a25828ded802d8ce963042b87` (2,953,712 B, canonical pyspades encoding) |
| `.txt` | not supplied, so author/settings unknown. Credited as "remus" in the description |
| identity | Roman river city: red-tile blocks on a street grid, a meandering N–S river, a Colosseum (SW), an obelisk park (NW), a rotunda (E edge), a fountain circus, courtyard pool blocks |

### Map DNA, measured `[RUN]`
* **One flat level.** 61 % of columns are street at z 62; buildings rise 5–11. 98 % of ground-floor interiors are walkable; 26 % of roofs are reachable.
* **Cosmetic river.** 1 deep, 2-voxel kerb; you can wade across anywhere; the 2 bridges are decorative; 0/40 water traps.
* **Not mirrored** (40.5 % top-z match) but fair: spawn↔spawn 236 / 236 steps.
* **Babel.** Platform volume clear and land under both ends, but the highest point walkable near the platform is z 60 → **build gap 59**. 50–58 % of spawn spots land on roofs; a timber pergola over T1's spawn; an indoor pool in T2's square. The east platform end sits over a roof (z 53–56) with a 20-tall courtyard tree, the west end over street → unequal anchors.
* **Exposure** (our tool): 53–55 viewers/spot, 7–9 % hidden (normandie on the same tool: 48–56, 1–5 %).
* **Art.** 4 hue families; coherence 2.45; **44 % of the top view is pure red (g = b = 0) roof**, i.e. the red team's hue; 17.7 % bright share; 173 floating pieces (2,071 voxels); 439 sealed air pockets; a 73-tall obelisk to z 1.

### Element ledger
| element | verdict | result in Remoria |
|---|---|---|
| Roman identity, terracotta/travertine, river | Keep | kept, ruined; terracotta no longer pure red (182,90,62) |
| river through the centre | Reimagine | runs N → **Cloaca culvert under Capitol Hill** → pillared cistern → flooded Colosseum |
| Colosseum | Reimagine | moved to the south centre line, **flooded arena (naumachia)**, walk ring, broken north facade |
| obelisk | Reimagine | fallen in three granite pieces on the forum beside its pedestal |
| rotunda / temples | Replace | Capitoline temple ruin on the summit with a colossal marble head |
| flat street grid | Replace | Capitol Hill (4 terraces) + 3 edge hills a side + river flats |
| roof spawns, pergola | Remove | spawn squares: 0 roof columns, 0 water |
| floating awnings, sealed rooms | Remove | 0 unintended floating; orphan pass removed 730 fragments (2,097 voxels) |
| bridgehead, flanks, underground | Add | summit (gap 23), aqueduct-deck north flank, Colosseum south flank, cistern/catacombs/culvert |

## 2. Remoria layout (west half authored, mirrored x' = 512 − x; z down)
| zone | where | notes |
|---|---|---|
| spawn squares | x 98–138 / 374–414, y 236–276, z 56–58 | rolling, rubble ≤ 2 high, no roofs, no water |
| spawn district | x 40–160 | 8 insulae/domus (2–3 storeys, stairs, windows, courtyards), ruined thermae behind spawn (dry plunge pools, mezzanine stair, apse) |
| Arch of Remus | x 156–165, pylons y 224–238 / 274–288 | 35-wide opening over the corridor; switchback stairs in each pylon to an **attic walk at z 27** |
| porticoes | x 166–206, y 198–203 / 309–314 | broken colonnades + back wall with doors, a toppled column in the road |
| Capitol Hill | ellipse rx 74, ry 92 at (256,256) | terraces z 52 / 44 / 36, **summit z 28**; notched stairs (rise 1) on the west face outside the corridor (y 212–220, 292–300) and north/south faces |
| temple | summit, podium z 26 | broken peristyle (z 12–20 tops), brick cella, **colossal marble head**, fallen drums, bronze tripod braziers |
| underground | cistern x 222–290, y 224–288, air z 49–61 | 3×3 pillars + ribs + lamps; river channel through it; **temple vault stairs** x 242–244 / 268–270 (z 27 → 62); **catacombs** y 226–228 and 284–286 from sunken dromos x 176, cross gallery x 212–214, loculi niches |
| Cloaca culvert | x 240–272, y 166–346 | towpath ledges z 61, escape steps every 20; portals at y 200 / 311; footbridges over the open cut at y 183 / 329 |
| river flats | z 59 | quays, escape steps every 38; ruined bridges y 142–150 and 364–372 |
| forum (N) | x 150–236, y 104–178 | roofless basilica, colonnade, rostra with stairs, fallen obelisk |
| aqueduct (N flank) | y 90–95, deck walk z 41, ~164 from centre | continuous across the map and over the river; ramps at x 32 and 148 (mirrored) |
| Colosseum (S flank) | centre (256,438), ~182 from centre | flooded r < 29, seats to z 50, walk ring z 50, south facade to z 30, radial stairs at 150°/210°, arena steps out at 135°/225° |
| edge hills | NW, W, SW + mirrors; edge range | warped domes, partial 3-voxel terraces; pine groves |
| unique objects | marble head, bronze wolf on plinth, fallen obelisk, chariot wheel on the arch, flooded naumachia, loculi | |

Palette: travertine/marble (warm cream, capped at 214) · Roman brick/terracotta · olive grass/umbrella pine/cypress ·
teal water. Fog (190,178,182); `heavens_color` (214,196,178,255). Glow: 50 amber sources (braziers, arch, cistern pillars,
catacomb torches, Colosseum walk ring), 8,282 lit voxels stored. Sky layer: 4 crow flocks + 4 cloud wisps (50 expected floating pieces).
Vegetation: 215 umbrella pines, 52 cypresses, 22 shrubs, each with 3 random details (cones, nest, ivy, dead branch, bleached patch, flowers…).

## 3. Validation (final build, sha256 `0e4a3684…fd6ab`)
| check | result |
|---|---|
| reader round trip / pyspades `generate()` | identical / identical; z 63 solid |
| deterministic rebuild (veg seed 1597721682) | same SHA-256 in a fresh process |
| floating | 0 unintended; 50 expected (sky) |
| mirror mismatch (geometry) | 0 voxels |
| platform volume z 0–3 | empty; script platform = 3,200 cells live |
| ground under both platform ends | land, z 44 (T2 terrace) |
| spawn squares | z 56–58, 0 roof columns, 0 water (live probe: 400 samples per team, z 56–58) |
| build gap | **23 / 23** (summit walk z 24); nearest authored voxel to the platform z 12 (columns/head) |
| platform reachable on foot | no |
| spawn ↔ spawn | 236 / 236 steps (same as remus) |
| ground + masonry reachability | 99.58 % (vegetation tops excluded) |
| interiors under roofs | 91.5 % reachable |
| traps | 0 / 300 sampled nodes; water exits 0 / 60 trapped |
| safe descent (falls ≥ 10 removed) | 99.0 % of reachable nodes |
| flanks | north and south flank routes connect spawn to spawn |
| key spaces reachable | aqueduct deck 944/944 · arch attic · cistern · catacombs · temple stairs · Colosseum ring |
| spawn exposure | **5.1 viewers/spot, 37 % hidden** (remus 53 / 8 % on the same tool) |
| art metrics | coherence 2.18 · neighbour jump 10 · bright 3.3 % · side − top −9.6 L* · no pure team hues |
| `.txt` | loads; author `shywolf91 + AI`; no spawn hooks; babel, water_damage 0, heavens_color, glow keys |

## 4. Fidelity
Heightfield correlation with remus is 0.01, so the terrain is fully reimagined, as intended. The river still runs
N→S through the centre and under the platform. The route length is identical (236). Symmetry rose from 40 % to 100 %
(geometry). Landmark roles: Colosseum SW → south centre (flooded); obelisk NW → forum (fallen); river → culvert +
cistern; street grid → hill terraces.

## 5. Problem ledger
| remus problem | status |
|---|---|
| build gap 59, no bridgehead | **fixed**: 23 from the summit (contested centre) |
| roof spawns 50–58 %, pergola, indoor pool | **fixed**: 0 |
| unequal anchors at the platform ends | **fixed**: both z 44, mirrored |
| cosmetic river, flat single level | **fixed**: 4 terraces, culvert + cistern, flooded arena, aqueduct deck, arch attic |
| exposure 53 viewers | **improved**: 5.1 viewers, 37 % hidden |
| pure-red roofs, 17.7 % bright | **fixed**: no team hues, 3.3 % bright |
| floating pieces, sealed rooms | **fixed** (floating); interiors 91.5 % reachable |

## 6. Known risks / test in game
1. **Summit = king of the hill.** Everyone can reach z 24–26, so a 23 build gap may make rounds fast. If so, lower the summit (raise its z) in `SPEC['hill']`.
2. The **arch attic (z 27)** is a perch over your own spawn's front; enemies can climb the pylons. Watch for camping.
3. The temple columns and the marble head reach z 12 under the platform, so blocks built on them shorten towers. Check in game.
4. The tower anchors are on the T1/T2 terrace with a retaining wall beside them (a raised tower zone, which the concept implies).
5. The glow keys are inert on stock piqueserver; the baked light still shows.
6. Fog and heavens colour are untested in a client. The art is a v1: insulae read boxy, and the head reads soft at distance.

## 7. Regenerate
```
python3 make.py out/remoria_v1 1597721682     # geometry + veg + sky + paint + glow + .vxl/.txt (≈7 s)
python3 check.py out/remoria_v1/scene.npy     # validation json (≈4 min)
python3 preview.py out/remoria_v1/remoria.vxl out/remoria_v1/preview
piqueserver -d <dir with server_config.toml, maps/, scripts/probe.py>
```
Layout seed 1753 (`SPEC['seed_layout']`); vegetation seed drawn per run and saved in build.json.
