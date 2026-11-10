# Clockwork Skyyard: spec, build and validation (2026-11-05)

**Mode:** stock piqueserver 1.4.2 Babel (`piqueserver.game_modes.babel` + `babel_script` + `map_extensions`). The script builds the platform at z 1, x 206–305, y 240–271; it is not in the VXL.
**Type:** full 512 × 512 sky Babel, steampunk dockyard. **Author:** `shywolf91 + AI`.
**Seeds:** layout 20261105 (fixed). Props, furniture and sky decor: 1338561173 (drawn from the OS, saved in `build.json`).

**Status ladder:** generated ✔ · exported ✔ · parser-validated ✔ (own reader and pyspades, byte-identical) · server-loaded ✔ (headless piqueserver 1.4.2, babel) · client-inspected ✘ · playtested ✘

Route checks use a voxel-graph model (3 air to stand, 1-voxel steps, drops ≤ 9 counted safe), not a collision simulation. Renders are numpy previews, not client captures.

## Owner answers (asked before building) `[USER]`
- **Dock height:** high, spawn deck at z 16. Gap of about 32 from the prow tip to the platform.
- **Lower yard:** a walkable foundry floor at z 54. Its two canals are toxic: `water_damage 10`.
- **Airships:** one moored airship per dock, plus floating sky decor (drifting blimps and smoke puffs).
- **Light:** glow-block lamps (hallweebalohabeta format) on a slightly darker grade, under amber dusk fog `(198, 158, 112)` with `heavens_color (226, 182, 126, 255)`.

## Layout (team 1 / blue authored; mirrored x' = 512 − x; centre pieces built symmetric about x = 256)
| element | where | notes |
|---|---|---|
| Foundry floor | everywhere inside the border crags, z 54 | Flagstones, cobbled streets, gravel yards, iron plate pads, painted rails. Solid to z 63. |
| Border crags | about 22–40 wide around the map edge, tops z 10–30 | A 7-high brick quay wall at the foot, ridged rock above. Six slender soot stacks per side. |
| Dock bastion (spawn) | crag around (106, 256). Deck is a superellipse 52 × 46, n 4, at z 16 | Brick dock wall under the rim, iron I-beams down the cliff, strata rock below. The deck is riveted iron plate with a brass rim band. |
| Spawn square | stock x 98–138, y 236–276 | z 16, plus six 1-high hatches at z 15. Nothing else is in the square: it is enforced to stay clear. |
| Prow | x 150–178, y 240–272 (32 wide) | Iron pier on struts. Rails 2 high, with a 9-wide open gap at the tip (y 252–260) for bridge building. Bollards, and mooring masts at (155, 232) / (155, 278). |
| Gantry (spawn cover) | x 146–151, y 219–293. Girder z 5–10, hollow legs with doors | A box girder over the whole front. Players walk under it (z 11–15 clear, 59 wide). This is the cover line toward the platform; see the trade-off below. |
| Moored airship | hull x 58–112, y 190–203. Envelope x 52–118, z 0–10 | Deck level with the dock (z 16), reached by a gangway. Wheelhouse, a cargo hold with a hatch stair, portholes, side engine pods, stern prop, fins. Rigged to the envelope and tied to a mooring mast on the north landing. |
| Hammerhead crane | base (78, 292), jib to y 344 at z 2–3 | Enterable cab. A crate hangs on the hook over the south yard. |
| Back deck | x 54–97 | Two-storey dock office (verdigris roof), iron winch house, two stacks, cargo, lamps |
| Descents (N and S, mirrored in y) | stair head x 90–100 → stair 1 (run 1) east to a landing at x 121–160 (z 36) → stair 2 east to the floor at x 179 | 45° flights with 2-high rails and newel posts at the top. The landing also serves the viaduct and the catwalk. |
| Signal stair tower | x 22–36, y 249–263, bridged to the deck | Interior square spiral, deck → floor. Slit windows. |
| Viaduct flank (N and S) | leg x 122–132 from the landing, then a run along y 100–110 / 402–412 to the mirror | Deck z 36, parapets, arches down to the floor (walk under). Rails, sleepers, pier lamps and a signal gantry. Locomotive and wagon (north) and three wagons (south) leave 2-wide walkways. |
| Catwalk | landing → cog tower gallery, z 36 | Iron grating, rails, posts down to the floor |
| Cog towers | (176, 166) / (176, 346), r 8, top z 14 | Brick, with a gallery ring at z 36 and a spiral stair from the floor to the lantern room (z 18). A brass great-gear (R 9) and a meshing copper gear face the centre. Copper cone, glow lantern. |
| Toxic canals | x 182–330, y 194–204 and 308–318 | Water at z 63 with a painted green bed and green glow seams in the walls. Stepped beaches at both ends and side stairs at the centre. |
| Brass bridges | x 196–203, 226–233, 250–262 and their mirrors, on both canals | Humped deck, brass rails, iron arch ribs, lamps at the corners |
| Sluice gates | x 191–192 over each canal's beach | Iron frame with a brass gear |
| Boiler hall (under the platform) | x 216–296, y 222–290, walls to z 30, slate gable ridge z 20 | Nave doors W and E (21 × 9), doors N and S. Four riveted boiler drums with steam domes. Fireboxes with glowing grates face the nave. Mezzanine at z 44 with four corner stairs. Clerestory windows, trusses, roof vents. The Great Governor stands in the nave and a sign gear hangs over each nave door. The roof is not reachable on foot. |
| Hall chimneys | (256, 213) / (256, 299), r 5, top z 12 | Brass bands, soot crown. No stairs. |
| Clocktower (north centre) | x 246–266, y 128–148, top z 6 + copper spire | Doors on four sides and a square spiral to the clock room (z 20). Brass dials (7:10) north and south, cornices, belfry openings. |
| Beam-engine house (south centre) | x 238–274, y 362–388 | Beam floor with stairs, steam cylinder, twin flywheels. The beam runs out of the north gable to a pump well. |
| West yards | NW: Gearworks (two storeys, sign gear), gasometer (r 16 lattice frame, enterable), steam-hammer forge, foundry (crucible pour), coal yard (heaps, tipple, wagons). SW: arched airship hangar (half-built frame, gallery), water tower, gear boneyard (giant gears on chocks, spare boilers), rail yard (turntable, engine shed). Inner: valve houses. | Every building is enterable, with stairs to every floor. |
| Pipes | overhead copper/verdigris runs on portal frames (walk under); low pipe runs with crossing gaps | Cover off the main lanes |
| Sky decor (floating, opt-in) | 5 blimps (one freighter) and 6 smoke puffs, near the edges and over the foundry / tipple / shed | ≥ 130 from the platform, none over a spawn square, ≥ 9 air below. **Collapse caveat:** a player block touching one, once destroyed, drops that piece for the round. |
| Corner tag | "CLOCKWORK SKYYARD" painted on the SW yard floor, x 34–136, y 462–469 | Name only, with a soot shadow. 7 letter cells landed on rail and were skipped. |

## Validation (`validation.json`, `extra_checks.json`, `probe.json`, `art_metrics.json`)
| check | result |
|---|---|
| Own reader re-encode / pyspades `generate()` | byte-identical ✔ / byte-identical ✔; 0 / 20 000 solid and colour mismatches |
| Same seeds → same SHA-256 in a fresh process | ✔ `4dd44380…` |
| z 63 solid | ✔ |
| Floating components (excluding sky decor) | **0**. Cleanup removed 345 stray voxels. 12 expected sky components (12 740 voxels). |
| Mirror, outside the declared boxes (hall, clocktower, engine house: chiral spiral stairs) | 0 voxels differ |
| Platform volume z 0–2 + margin | 0 / 0 ✔ |
| Ground under the platform ends | x 206–211 and 300–305: floor z 54 on every column ✔ (on an iron plate pad, prop-free) |
| Spawn squares | z 16 (1 617 cells) / z 15 hatches (64), mirror-equal ✔. Live: 400 sampled spawns per team at z 16/15 inside x 98–138 / 374–414. |
| Spawn exposure (targets ≤ 10 viewers, ≥ 15 % hidden) | blue 0.81 viewers per spot, 90.7 % hidden; red 0.83 / 90.7 % ✔ (worst spot 26) |
| Build gap | 31.8 from the prow tip (178, 252, z 16). The platform is not reachable on foot. Ground towers from the anchor floor build 53 tall. The nearest authored voxel to the platform is the hall roof ridge, 18 below (not reachable). |
| Trap cells (reachable but no walk-out) | 0 (the graph now refuses drops through solid neighbour columns) |
| Canal cells that walk out | 100 % ✔ |
| Floor reachable from spawn | 100 % ✔ |
| Routes, cost from spawn (blue = red) | prow tip 32 · floor below the deck 145 · own anchor floor 164 · cog lantern 192 · hall mezzanine 202 · hall nave 218 · engine beam floor 247 · viaduct mid 275 / 278 · clock room 303 / 297 · enemy spawn 368 |
| Flank route (avoids \|y − 256\| < 130 for x 180–332) | ✔ cost 544, over the viaducts |
| Interiors reachable | dock office upper 46, airship deck 46 / hold 56, crane cab 33, gantry legs 24, back tower floor 110, valve house 169, foundry 190, forge 212, engine shed 247, hangar gallery 303, coal tipple 310, gasometer 330, Gearworks upper 333 |
| Live server (piqueserver 1.4.2, babel) | "Map loaded successfully" (0.15 s). Fog read. Extensions parsed (`glow_stored_colors` 41 229 entries). Platform 3 200 cells, intel (256, 256, 1), bases at z 16. |
| Glow | 340 sources (orange lamps and furnaces, yellow mast and train lamps, green canal seams). Baked: lit = stored + source × 0.32 × (1 − d/6.5). |
| Art metrics | 3 hue families ✔ · coherence 1.24 (target 1.4–2.5, a little busy: flagstone joints and plate seams) · side − top −11.2 L* ✔ · relief 18.9 |

## Known limitations / next steps
- **Gantry = a structure on the front.** The box girder spans the spawn front. It is open below (59 wide, 5 high), but it is the "occasional, not default" pattern. It is what takes exposure from 100 % to 9 % visible. Owner decision: keep it, or thin it to the legs plus a lighter truss and accept more exposure.
- **Long walk to the floor:** spawn → own anchor floor is 164 graph steps (sky-Babel style). Most fights will be bridge building between the prows, plus the hall and canal centre.
- **`water_damage 10`:** the per-tick rate is unmeasured. Wade one canal in game before release.
- **`.txt` is 1.3 MB** because of the glow dict (hallweeb has about 150 k entries, so this is in range). On a server without a glow script the baked light still shows; the keys are inert.
- **Unverified in a client:** stair headroom (45° flights, spirals), walking under the gantry and the airship belly, the viaduct walkways past the train, fog/heavens colours, glow look, and FPS at 3.7 MB.
- The amber fog is close to the brass/copper palette. Silhouettes rely on the darker iron and brick. Check in game that brass at range doesn't vanish into the fog.
- `heavens_color` only works on servers whose scripts read it (the owner's convention); stock 1.4.2 ignores it.

## Files
`maps/clockwork_skyyard_v1/` holds `clockwork_skyyard.vxl`, `clockwork_skyyard.txt`, `build.json`, `validation.json`, `extra_checks.json`, `art_metrics.json`, `probe.json`, `server_load.log`, `mat.npy` and `renders/`.
`scenes/clockwork_skyyard/` holds the generator:
- `cs_spec.py`: SPEC and materials
- `cs_core.py`: VXL codec, noise
- `cs_geo.py`: canvas and primitives
- `cs_struct.py`: stairs, spirals, shells
- `cs_terrain.py`: terrain
- `cs_dock.py`: team side
- `cs_centre.py`: hall, canals, clocktower, engine
- `cs_art.py`: set pieces and dressing
- `cs_sky.py`: sky decor
- `cs_color.py`: colour, light, glow
- `cs_build.py`: orchestration
- `cs_main.py`: export
- `cs_check.py`: checks
- `cs_render.py`: previews

`server_test/cs_babel/` holds the test config and probe.

**Regenerate** (Python 3.11 venv with piqueserver 1.4.2, numpy, scipy, pillow):
```
cd scenes/clockwork_skyyard
python cs_main.py ../../maps/clockwork_skyyard_v1 1338561173   # omit the seed for new props/sky
python cs_check.py ../../maps/clockwork_skyyard_v1 --pyspades --exposure
python cs_render.py ../../maps/clockwork_skyyard_v1
cp ../../maps/clockwork_skyyard_v1/clockwork_skyyard.{vxl,txt} ../../server_test/cs_babel/maps/
cd ../../server_test/cs_babel && piqueserver -d .     # drop "cs_probe" from scripts to keep it running
```
