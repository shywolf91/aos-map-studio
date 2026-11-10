# Bloomhop Kingdom — v1.0 spec, build and validation (2026-11-09)

Platformer-world ground Babel for stock piqueserver 1.4.2 (`piqueserver.game_modes.babel` + `babel_script` + `map_extensions`). Full 512 × 512. The theme takes its cue from classic side-scrollers: bright terraced hills, giant mushrooms, chunky toy blocks, brick towers and castle keeps. **Every asset is original.** The map contains no Nintendo characters, enemies, logos or signature props.

**Status:** generated ✔ · exported ✔ · parser-validated ✔ (own reader plus pyspades `VXLData.generate()`, both byte-identical) · server-loaded ✔ (headless piqueserver 1.4.2, babel mode, "Map loaded successfully") · client-inspected ✘ · playtested ✘.
Renders come from a numpy raycaster, not from the client. Route checks use a voxel-graph model (3 air voxels to stand, 1-voxel auto-step, drops ≤ 9 counted as safe), not a collision simulation.

## Owner answers (asked before building)
* Concept: **Bloomhop Kingdom** (chosen from Bloomhop / Cinder Keep / Cloudstep Meadows / a mix).
* Layout: full 512 × 512 ground map.
* Water: light damage. `water_damage 5`, applied to the two ponds.
* Extras: underground layer, glow blocks, sky decor. Bright sky colour was not picked, but a daytime `heavens_color` is still set (see below).

## Layout (team 1 / blue authored on the west half; mirrored x' = 511 − x)
| element | where | z (top) |
|---|---|---|
| Castle-hill plateau | x 30–152, y ~200–312, edges vary with noise | 46 (1-voxel humps, mowed-stripe grass) |
| Spawn square (stock ±20) | x 98–138, y 236–276 | 45–46, 94 % flat, nothing overhead |
| **Bloomhop Keep** (spawn keep) | x 42–72, y 238–274 | Three floors at z 46/39/33 plus a roof walk at z 27 with battlements. Straight stairs between all floors. East main arch door (13 wide) plus N/S doors, windows on every floor, hearth, long table, bunks, map table. Four turrets with conical roofs, reached from the roof walk. Roof cupola. Team banner on the east face (blue/red). Lanterns either side of the door. |
| Keep cellar + secret passage | cellar under the keep (floor z 53), stair down from the ground floor | Winding 4-wide passage north with green glow moss. It exits as a low balcony on the plateau's north slope (~y 188). |
| Courtyard | fountain at (85, 256), two flower beds | — |
| **Mushroom Gate** | two giant mushrooms at the plateau front (stems ~(154, 229)/(154, 283)) whose caps meet over the front lane | Caps at z 23–29. ~15 voxels of open clearance under them. They hide the spawn from the platform. Hanging glow lanterns. |
| Front terraces | x 152–168 | 1-voxel risers, 2 wide, from 46 down to 54 |
| Tower terrace / anchor | x 150–212, y 226–286 | 54. **Sheer 3-voxel brick face at x 212/213 on the enemy side; no stairs.** Its north and south sides slope gently. |
| Under the platform | x 213–298 | 57 |
| **Toy-block hill** (centre) | x 236–275, y 236–275 | Tier 1: 8×8×6 blocks (top z 51) with N–S and E–W walk-through tunnels (4 high, glow lanterns). Tier 2: 3×3 blocks (top z 45). Accent block at z 41. 1-voxel stairs on the N and S faces only (x 244–249 / 262–267). A glowing chamber inside tier 2, reached by corridors from the tier-1 roof. |
| Mushroom grove | x 214–236 around the platform band | Cap tops kept at z ≥ 40 under the platform footprint |
| Toy-wall ruins | (214, 206) and (214, 300) + mirrors | Low cover walls of toy blocks with a walk-through gap |
| Mushroom cottages | (178, 192) red cap, door south; (182, 322) teal cap, door north (+ mirrors) | Enterable: ground room, stair to a loft under the hollow cap, round windows, dormer, chimney, porch lantern |
| Stepblock Lookout | (202, 136) + mirror | Hollow brick tower: four doors, windows, inner spiral stair to a railed deck at ~z 36 with a glow lamp |
| Ponds | centred (255.5, 168) and (255.5, 344), 52 × 38, water z 63 | Banks step down 1 voxel at a time. Arched wooden footbridge across the north pond, stepping stones across the south pond, lily pads |
| Brick arches | (162, 209), (196, 311), (98, 340) + mirrors | Open arches over the paths |
| North flank | lane y ~70–110 (\|y − 256\| ≈ 146–186) | Dome hills (decorative, not climbable), hollow logs, windmill knoll |
| Windmill | knoll (255.5, 84), floor z 47 | Spiral stair to the top floor (z 27), N/S doors, windows, X sails on the south face |
| South flank — Bramble Ridge | y ~400–440, top z ~38–40 | Two open-cut stairways up the north face (x ~162, ~224 + mirrors). The south meadow lane runs at y ~392. |
| **Glowroot Tunnel** (underground) | y ~413–418 under the ridge, floor z 58, 4 air | Two portals per side (x 132, 196 + mirrors) with stone frames, cyan glow crystals, hanging roots |
| Grotto + Thornwall Fort | grotto under (255.5, 418); fort ruin on the ridge top x 240–271, y 408–434 | Crystal cavern with a painted pool. A spiral stair links the fort courtyard and the grotto. The roofless fort has broken walls, gates, windows and rubble. |
| Secret vault | south of the grotto through a 3-wide passage (y 433–452) | Treasure chest plus a glow lamp |
| Sky decor (opt-in floating) | 8 clouds over the N and S flanks, 2 arcs of 5 floating toy blocks (N) | 18 floating pieces, nearest 134 voxels from the platform, none over a spawn square |
| Corner tag | "BLOOMHOP KINGDOM", SW corner ground, x 8–91, y 490–496, on a levelled strip | Name only |
| Vegetation (non-deterministic) | grove density field | 232 bloom trees (each gets 3 random details out of 11: fruit, flowers, vines, roots, band, mushrooms, nest, sub-lobe, glow bulb, litter, two-tone). 68 giant mushrooms (3 of 7 details each). 240 bushes, 68 bloom lanterns (glowing flowers along paths), 51 flower patches. Each mirrored partner is a different random plant of the same size class. |

Palette: grass greens (sunnier on high ground, lusher in low meadows), warm banded platformer soil, cream ashlar, terracotta roofs, warm brick. Accents: toy-block coral, gold and mint, and mushroom caps.
Glow: 181 sources in the fixed glow palette (amber lanterns, yellow bloom bulbs and chambers, cyan/green crystals, a few pink cap dots). Light is baked into the VXL and stored in `glow_stored_colors`.
Fog `(196, 204, 214)`, `heavens_color (128, 184, 238, 255)`.

## .txt
`name 'Bloomhop Kingdom'`, `author 'shywolf91 + AI'`, `version '1.0'`, extensions `babel True`, `water_damage 5`, `heavens_color`, `glow_enabled True` + `glow_stored_colors` (22.5k entries). No spawn/entity hooks (owner rule).

## Validation (`validation.json`)
| check | result |
|---|---|
| Own reader re-encode / pyspades 1.4.2 `generate()` | byte-identical ✔ / byte-identical ✔ |
| Server load (piqueserver 1.4.2, babel + babel_script + map_extensions) | "Map loaded successfully" ✔ (`server_load.log`) |
| z 63 solid everywhere | ✔ |
| Floating components | 18, all intended sky decor. 39 build fragments (≤ a few voxels) removed automatically. |
| Platform volume z 0–3 (+1 margin) | clear ✔ |
| Ground under both platform ends | z 54 land ✔ |
| Spawn squares | z 45–46, no water, no overhead, mirror-equal 1.00 ✔ |
| Spawn exposure from the platform edge | 67.8 % exposed, 3.5 viewers per spot, 32 % hidden (targets ≤ 10 viewers, ≥ 15 % hidden) ✔ |
| Safe way down spawn → tower zone | ✔ (cost 30 / 31 steps, no drop ≥ 10) |
| Enemy spawn reachable on foot without building | ✔ (cost 236 both teams) |
| Platform reachable without building | no ✔ |
| Build gap | 44 for both teams (from the toy-hill tier-2 stairs top, z 45). From the anchor terrace it is 53. |
| Anchor front (enemy side) | sheer 3-voxel step everywhere at y 240–272 ✔ |
| Solid mirror equality | 98.5 % (differences are vegetation variants and sky decor only) |
| Reachable top surface | 61 %. The unreachable rest is the ring-hill boundary, the dome hills, and tree/mushroom tops (`renders/reach.png`). |

## Known limits / next tests
* **Mushroom Gate trade-off:** the front lane passes under two giant caps (open, ~15 clearance). This is the "structure on the front with an opening" pattern, used here because the open front exposed 99.8 % of spawn spots to 14.5 platform viewers each. Owner can drop it with one line in `main.py`.
* **Toy hill as a tower base:** it gives a 44-block build from the centre, against 53 from the anchors. Its stairs are on the N/S faces only. Both teams share it (it sits on the centre line). Lower or remove tier 2 if it becomes the default tower spot.
* `water_damage 5` rate is unmeasured, and so is whether the stepping stones (2-voxel gaps) need a jump or a short wade.
* Dome hills on the north flank and the ring hills are not climbable without building (by design). The flank lanes run between them.
* Not yet checked in a client: fog/heavens colour, glow look, stair headroom (graph model only), FPS at 3.3 MB.
* `heavens_color` and the glow keys are read only by the owner's setup. Stock 1.4.2 ignores them, but the baked glow still shows.

## Regenerate
```
cd src
python main.py ../out/v1 955290020    # omit the seed for new vegetation
python check.py ../out/v1
python render.py ../out/v1
```
Layout seed 20261109 (fixed in `spec.py`). Vegetation seed 955290020. SHA-256 `1070ada274ad8ea02c227998788b0d71138e0cab243c4de1a81ede29fa1f4839`.
`libvxlenc.so` is built from `vxlenc.c` with `gcc -O2 -shared -fPIC -o libvxlenc.so vxlenc.c`.
