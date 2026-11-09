# Graveyard of the Forgotten — The Bone Cathedral (v1.0, 2026-10-19)

Halloween **ground Babel** for AoS 0.75 / stock piqueserver 1.4.2, built from the owner's brief: a cursed cemetery
basin around a ruined gothic cathedral whose missing vault has been replaced by the rib cage and spine of a colossus,
with two giant skeletal hands breaking out of the earth north and south of it. Teams spawn in walled churchyards,
walk an open flagstone front through a bone gate, and build their towers from wide paved courtyards that flank the
cathedral's transepts. Gameplay geometry is mirrored `x' = 512 − x`; the hands are the only cosmetic asymmetry
(both centred on the axis, so neither team is closer).

**Status:** specified · generated · exported · parser-validated (own reader + pyspades 1.4.2) · server-loaded
(piqueserver 1.4.2, `game_modes.babel` + `babel_script` + `map_extensions`, blue/red) · **client-inspected**
(screenshots in the real BetterSpades client a695aaa, spectator camera, software GL) · **not** playtested, **not** seen
in the owner's aos_web client.

Map files: `maps/graveyard_of_the_forgotten_v1/graveyard_of_the_forgotten.vxl` + `.txt` (3.00 MB,
SHA-256 `6a03ba92…022d86`). Generator: `scenes/graveyard_forgotten/` (seed 1313).

## Babel integration (stock 1.4.2, read in installed source)
* `babel_script.py`: platform x 206–305, y 240–271, z 1 (cyan, protected); bases (118, 256)/(394, 256); spawns random
  ±20 on the topmost voxel; one intel at (256, 256) on the platform `[SRC]`.
* `.txt`: `'babel': True`, `'water_damage': 0`, fog `(164, 170, 162)` (pale grey-green graveyard mist, brightness
  ~165, hue absent from the charcoal/bone/brown palette, neutral between blue and red). **No** spawn/entity hooks
  (owner rule).
* **Cap limit finding `[SRC]`+`[RUN]`:** `server.set_map` computes `max_score = map_info.cap_limit or default` *before*
  `set_map()` triggers `babel_script.on_map_change`, which only then sets `map_info.cap_limit = 1`. On a fresh stock
  server the bots received `cap_limit 10` in StateData (the config default). `babel_script`'s own header tells admins
  to set `cap_limit` in config. Older notes saying "cap_limit forced 1" describe `map_info`, not the live score limit.
  This map leaves the cap to the rotation admin.

## Layout (west half; east is the mirror)
| element | where | notes |
|---|---|---|
| basin floor | z 44 everywhere in the cruciform consecrated ground | spawn yards, fronts, courtyards and cathedral floor are one level: no raised tower zone, no descents needed |
| spawn square | x 98–138, y 236–276, z 44 | packed gravel, nothing on it (keep-clear volume enforced after all props) |
| churchyard ring | iron railing on a stone footing, x 94–142, y 232–280 | outside the square; gates N/S (x 111–125, arched, skull pillars), W (y 250–262, to the chapel), **E front y 243–269 (27 wide)** |
| bone gate | pylons x 140–145 at y 236–242 / 270–276, arch over the front | vertebra arch, underside 11–20 above the path, skull keystones, ghost lantern; team banners on the courtyard face. Breaks sightlines from the platform to the back half of the spawn square (see exposure) |
| gate tombs | (149, 226) / (149, 286) | mausolea flanking the front, doors toward the path, team banners |
| ossuary chapel | (64, 256), faces east | large mausoleum with spire behind the spawn; bone piles |
| yard trees | 6 big dead trees outside the ring, 2 with gibbet cages | no branch over the square |
| front | x 143–155, y 243–269 | flagstones, open |
| **tower courtyard** | x 156–211, y 222–290 (3 864 cells), z 44 | paved flags with dark edging, **no props, nothing above** (checked); the platform's anchor columns x 206–211 lie inside it |
| transept lane | x 212–218 | grass lane with a path between courtyard and transept |
| west front | towers x 217–235, y 122–141, top z 8, sheared slate spires to z ~1 | buttresses, string courses, open belfry lancets, blind lancets, crenellated parapet, skull gargoyles |
| façade screen | y 136–141 | portal (stepped archivolts, fallen door leaves), skull frieze, rose window (r 6.6, tracery, purple/blood/green glass, a third broken), gable cross at z 6 |
| nave | walls x 236–239, y 142–237, top z ~20 (crumbled to ~29 near the crossing) | 9 stained-glass lancets per side, side door y 192, bone flying buttresses on stone piers (x 226–229), femur columns, broken pews, ledger slabs, ghost candelabra, the **fallen spire** lying along the axis in three pieces |
| **rib cage** | rib pairs every 9 from y 146 to 218; spine on the axis z 10–12, y 142–222 | ribs spring from the wall tops, bulge outward and arch to the vertebral spine; two snapped (stubs + fragment on the floor). Ends ≥ 18 short of the platform's edge |
| crossing (fallen bell tower) | x 238–274, y 238–274, under the platform | 5-thick walls 12–19 high, fractured corner piers to z ~20; north/south walls torn open (nave ↔ crossing ↔ choir); arch to each transept; the **cracked great bell** lies on its side half-sunk on the axis; charred beams, rubble skirts |
| transept | x 219–237, y 244–268 | broken side walls 8–14, end gable (z ~17) with pointed doorway onto the courtyard lane and a green-glass oculus |
| choir + apse | walls y 275–330, apse r 18 round (256, 330) | lower ruin, red/purple lancets, raised dais, altar with blood cloth, skull and ghost candles, a **bone reredos** (skull wall), two broken rib stubs |
| precinct | x 206–256, y 94–378 | parvis paving north of the façade, lawn graves, lanterns |
| north hand (reaching) | rooted in a burial mound at (256, 62) | radius + ulna, carpals, four metacarpals, fingers splayed to z ~1, thumb, **ring finger snapped** (fragment lies on the mound); dark earth, ghost-lit cracks, flattened gravestones |
| south hand (clawing) | crater at (256, 438) | forearm bursting up from the crater floor, palm down, four long fingers arching over the lip and **dug into the ground** (you can walk under the finger arches), hooked thumb, the giant skull's crown breaking the soil behind, glowing fissures |
| cemetery | hills z 34–44 around the basin | ~600 gravestones in 7 types (round, cross, slab, obelisk, ringed cross, fallen, broken stump; ~40 % of the upright ones leaning), walled or railed plots with gates, 24 mausolea, 4 crypts with 6-deep stairs to vaults (coffin niches, ghost candles), 6 skull-rock outcrops, 10 murky pools (painted surface, no water physics), open graves with coffins, bone piles, ghost lanterns along winding flagstone paths |
| dead forest | rising rim, z 14–30 at the edges | ~380 twisted leafless trees, a few gibbet cages |
| corner tag | SW, ground strip x 14–168, y 496–502 | "GRAVEYARD OF THE FORGOTTEN" only |

Palette: charcoal stone, weathered grey, bone/ivory, dark brown earth, dead olive grass; accents ghost green (lamps,
cracks, glass), muted purple and blood red (glass, altar). Ghost-light "pools" are painted onto the ground around lamps
(colour device; no renderer lighting assumed).

## Validation (`maps/graveyard_of_the_forgotten_v1/validation.json`; routes are a graph model, not a collision sim)
| check | result |
|---|---|
| own reader round trip | re-encode identical, every surface voxel coloured, z 63 solid, 0 water columns |
| pyspades 1.4.2 `VXLData.generate()` | **byte-identical**; 0/20 000 solid and colour mismatches; `get_z` at both bases 44 |
| floating components | **0** (254 orphan twigs/pane fragments ≤ 60 voxels removed at build) |
| mirror (x' = 512 − x) | 0 solid / 0 material mismatches outside the two hand boxes |
| platform volume z 0–2 (+1 margin) | 0 voxels |
| under the platform | highest authored voxel z 16 (15 below the slab); nearest authored voxel 15 (transept gable coping) |
| ground under platform ends | blue x 206–211 and red x 300–305: all z 44, solid to the bottom |
| spawn squares | 1 681/1 681 cells at z 44, both teams |
| courtyard | 3 864 cells all z 44, 0 voxels above |
| routes (team1 / team2) | own platform end 68 / 69 · crossing 108 · apse altar 155 · façade portal 220 · enemy spawn 236 · claw-hand arches 242 · reaching hand 261 — parity ≤ 1 (the 255.5 platform centre) |
| traps | 7 isolated cells (5 forest pockets on the rim at z 32, 1 on the claw hand's wrist); every crypt, pool and grave walks back out |
| build gap | highest walkable point within 24 of the platform z 41 → **39 blocks**; platform not reachable on foot |
| highest walkable spots | z 14, the north rim hills behind the reaching hand (≥ 220 from the platform and both spawns) |
| spawn exposure (platform edge → spawn heads) | blue **5.2** viewers/spot, **15.4 %** hidden; red 5.0, 17.0 % (targets ≤ 10, ≥ 15 %). Without the bone gate: 10.1 / 9.5 viewers, 1.4 % hidden |
| art metrics (`tools/art_metrics.py`) | 8 648 colours, 4 hue families, coherence 1.61, side − top −10.0 L* (all inside the reference bands) |
| live server | loads in 0.2 s; babel on; `map_info.cap_limit` 1; fog + extensions read; platform 3 200 cells; 400 sampled spawns per team all z 44 in the squares; intel (256, 256, 1) |
| live client (bots) | spectator receives the map with all 3 200 platform cells; blue/red bots spawn at eye z 41.6 inside their squares; StateData cap 10 (see cap finding) |
| real client | BetterSpades screenshots in `client_betterspades/` (views listed in `views.txt`) |
| determinism | same SHA-256 on Python 3.11 (numpy 2.4.6) and 3.13 (numpy 2.5.3), different `PYTHONHASHSEED` |

## Design trade-offs to judge in play
* **Bone gate over the front.** Your rule is open fronts and no default structures between spawn and tower zone.
  The gate keeps the full 27-wide front open at ground level (underside ≥ 11 up) but it *is* an overhead structure
  on the front, and it is what makes the spawn-camping targets pass (1.4 % → 15–17 % hidden). Set
  `SPEC['bone_gate'] = False` in `gf_terrain.py` for plain banner pillars instead; exposure then fails the targets.
* **Ground Babel, 39-block climb.** Same as the Wicker King and Drowned Cathedral. There is no central shortcut: the
  bell-tower stump and transept gables are not walkable, and the rib cage stops 18 short of the platform.
* **Destroy band.** Stock rule: blue can't remove blocks while standing at x ≤ 288, red at x ≥ 224, so towers built
  near the cathedral are hard to clear from your own side.
* The north rim hills (z 14) are the highest walkable ground; they are far outside fog range of the spawns and
  platform, but a sniper could sit there.

## Known limits / next tests
* Not playtested. Check in aos_web/BetterSpades with players: fog density (pale grey; try `/fog` brighter or a lilac
  tint if it reads too flat), stained-glass readability, whether the bone gate feels like a "screen".
* Pools are painted ground, not water.
* Hand fingertips and façade spires reach z ~1; nothing is near the platform.
* Route numbers are a graph model (3 air to stand, 1-voxel step, drops ≤ 9), not a collision simulation.

## Regenerate
```
cd scenes/graveyard_forgotten
python gf_main.py ../../maps/graveyard_of_the_forgotten_v1          # VXL + TXT + build.json (+ mat.npy, git-ignored)
python gf_check.py ../../maps/graveyard_of_the_forgotten_v1 --pyspades --exposure
python gf_render.py ../../maps/graveyard_of_the_forgotten_v1         # numpy previews -> renders/
python gf_render_hands.py ../../maps/graveyard_of_the_forgotten_v1   # hand close-ups
```
Modules: `gf_terrain.py` (SPEC + height field), `gf_props.py` (materials + prop library), `gf_cathedral.py`,
`gf_hands.py`, `gf_build.py` (layout, plots, forest, mirror, cleanup), `gf_color.py`, `gf_main.py`, `gf_check.py`.
Server: `server_test/gf_babel/config.toml` (stock script list + `babel_script`; the `gf_probe` script writes
`probe.json` and stops the server — drop it to run normally). Real-client capture: `tools/betterspades_capture.sh`
(placeholder weapon assets because `aos.party/bsresources.zip` is unreachable from the sandbox).
