# Lantern Bazaar Canals — spec, build and validation (2026-11-02)

**Mode:** stock piqueserver 1.4.2 Babel (`piqueserver.game_modes.babel` + `babel_script`). The script builds the platform at z 1, x 206–305, y 240–271. It is not in the VXL.
**Size:** 512 × 512 × 64, ground Babel. **Author:** `shywolf91 + AI`. **Layout seed:** 20261102 (fixed). **Vegetation seed:** 1146888284 (drawn from the OS, saved in `build.json`).

**Status ladder:** generated ✔ · exported ✔ · parser-validated ✔ (own reader + pyspades byte-identical) · server-loaded ✔ (headless piqueserver 1.4.2, babel mode) · client-inspected ✘ · playtested ✘

Route checks use a voxel-graph model (3 air to stand, 1-voxel steps, 2-voxel jumps, drops), not a collision simulation. Renders are numpy previews, not client captures.

## Owner answers (asked before building)
- Canals are walkable: `water_damage 0`. Every canal has 3-wide escape steps; none sit beside the tower anchors.
- Cistern: a sunken square with a low dome. The hall is enterable, and the dome top is z 40.
- Lanterns are painted brass and amber with warm light pools. No glow keys.
- Bazaar route has two parts: a roofed arcade street that drops into a vaulted under-street passage.

## Layout (team 1 / blue authored; mirrored x' = 512 − x)
| element | where | notes |
|---|---|---|
| Street level | z 57 | 6 above the water plane |
| Spawn plaza | x 92–146, y 228–284; z 55 (x > 112), 54 (x ≤ 112) | Mosaic star round the base. Two steps (56 → 57) down to the street at x 139–150. Only 1-high planters inside the ±20 square. |
| Terraced market quarter | x 8–150, y 150–362 | Rings T1 z 52, T2 z 49 and T3 z 46 around the plaza, each with houses and stalls. Stair flights between rings; quarter exits north, south and east. Parapets (2 high) on every drop ≥ 3, open at stairs. |
| Bell-tower lookouts | (47, 182) and (47, 330) on T2, mirrored | Square spiral stair to an open belfry (floor z 26) with a bronze bell |
| Front / tower zone | x 121–212, y 240–272 | Flat z 55–57. No props, no water. Colour-only boulevard inlays. Cypress rows and lantern posts line y 229–233 and 280–284, outside the corridor. |
| Grand canals | x 214–226 and 286–298, y 8–503 | Walkable. 9 bridges each, including a 17-wide arched bridge under the platform (y 248–264). Water gates in the north and south walls. |
| Cross, dyers' and loop canals | y 186–196 and 316–326; y 120–130 and 382–392; y 28–40 and 472–484 (centre) | Arched bridges (5 wide, 2-high rails, lantern posts) |
| Cistern island | x 227–285 | Between the grand canals |
| Sunken cistern square | x 232–280, y 214–298 | Three 1-voxel tiers down to z 60 |
| Cistern hall + dome | r 12 at (256, 256) | 4 arched doorways, 8 columns, stepwell pool, hanging lamps. Dome top z 40 (cupola + finial to z 34). |
| Colonnades (riwaq) | y 204–211 and 301–308 | Open arcades framing the square. The roof (z 50) cannot be climbed without building. |
| Minarets | (256, 196) and (256, 316) | Spiral stair to a balcony (floor z 27). Built after mirroring because the stair is chiral. |
| Dry dock (north flank) | x 232–280, y 46–134 | Stepped dock sides. Ship on keel blocks on the centre line (y 58–122). Gangplanks at street level reach hull breaches into the hold. Two hatches lead to the deck, plus a deckhouse, two masts and a rust caisson gate. |
| Roofed bazaar arcade (south flank) | x 34–196, y 410–420 | Shops on both sides; 3 open cross alleys; skylights; walkable roof |
| Under-street passage | x 201–311, y 410–420, floor z 62 | Air z 58–61 (4). Two aisles round a centre column row. Exits: island-centre stairwell, west and east quay stairwells, arcade stairs. |
| Sluice house | y 403–427 over each grand canal | Covered bridge on a weir. The passage crosses here because AoS water sits on the bottom plane, so nothing can pass under it. |
| Houses | 157 | All enterable. Doors kept off stair runs; internal stairs to every storey; windows; rugs and furniture. Roof styles: flat parapet roofs (domes, pergolas, canopies, jars, tanks), hollow hipped terracotta roofs, south-front loggias, mashrabiya balconies. 30 rooftop plank bridges; 69 lantern strings and striped shades across lanes. |
| Corner tag | "LANTERN BAZAAR CANALS" painted on the north wall walk, x 24–148, y 1–7 | Name only |
| Fog / sky | `fog (206, 176, 172)` warm rose haze; `heavens_color (226, 190, 164, 255)` | Fog hue is absent from the plaster and turquoise palette |

## Validation (`validation.json`)
| check | result |
|---|---|
| Own reader OK, re-encode byte-identical | ✔ |
| pyspades `VXLData.generate()` byte-identical | ✔ |
| Same seed → same SHA-256 in a fresh process | ✔ |
| z 63 solid everywhere | ✔ |
| Floating components | 0 (9 one-voxel fragments removed after vegetation) |
| Mirror before vegetation and minarets | 0 mismatched voxels |
| Platform volume z 0–2 + margin clear | ✔ |
| Ground under both platform ends | z 57 land, both sides |
| Spawn squares | z 53–55 (1-high planters only), no water, no roofs, mirror-equal ✔ |
| Tower zones | z 55–57, 0 water, no props |
| Trap nodes (reachable but no way back) | 0 |
| Land columns reachable | 98.8 % (the rest is mostly tiled roofs) |
| Interiors test (every room, floor, roof, tower, ship, arcade, passage) | 2200 / 2200 reachable |
| Routes, team 1 / team 2 (equal) | own anchor 69 · cistern hall 110 · minaret balconies 191–196 · enemy anchor 167 · ship hold 231 · arcade 217 · passage 212 · enemy spawn 259 |
| Safe-descent routes (no damaging drops) | same as above |
| Flank route avoiding \|y − 256\| < 130 | ✔ (cost 446) |
| Platform reachable without building | no |
| Build gap | 45.5 (minaret N balcony, 25 vertical / 38 horizontal). Ground towers start at z 57 (56 to build). |
| Art metrics | 2 hue families · coherence 1.77 · side − top −6.6 L* |
| Server load (piqueserver 1.4.2, babel) | "Map loaded successfully". Platform 3,200 cells. Fog and extensions read. 400 spawns per team at z 53–55 inside x 98–138 / 374–414. Intel at (256, 256, 1). |

**Spawn exposure: viewers per spot pass, hidden share fails.** 9.7 platform-edge viewers per spawn spot (target ≤ ~10) ✔. 0 % of spots hidden (target ≥ 15 %) ✘, the same trade-off as Mossglade Pond. The open front (owner rule) leaves the plaza visible from the platform edge 88 voxels away, at a 32° angle. Options: keep as is; add an arched gate or loggia screen with openings across the front; or move the spawn plaza 1–2 levels lower behind a terrace lip. **Owner decision.**

## Files
`maps/lantern_bazaar_canals_v1/` holds:
- the map: `lantern_bazaar_canals.vxl` and `.txt`
- previews: overhead and 2× overhead PNGs, 4 isometric views, 12 first-person views plus a contact sheet
- build and check output: `build.json`, `validation.json`, `art_metrics.json`, `server_load.log`, `probe.json`

`scenes/lantern_bazaar_canals/` holds the generator: `lbc_spec.py` (SPEC, materials, palette), `lbc_terrain.py`, `lbc_kit.py` (houses, stalls, vegetation), `lbc_structures.py` (set pieces), `lbc_build.py`, `lbc_color.py`, `lbc_main.py` and `lbc_check.py`.

**Regenerate** (Python 3.11 venv with piqueserver 1.4.2):
```
cd scenes/lantern_bazaar_canals
python lbc_main.py ../../maps/lantern_bazaar_canals_v1 1146888284     # omit the seed for new vegetation
python lbc_check.py ../../maps/lantern_bazaar_canals_v1
piqueserver -d ../../server_test/lbc_babel                                # probe.json, then exits
```

## Known limitations / next steps
- **Spawn exposure** decision (above).
- **Under-canal passage:** it crosses the grand canals over sluice weirs under covered bridges, so it does not run beneath water. A true under-water passage is not possible in AoS.
- **Unverified in a client:** jump and step figures, crouch, ladders not used. The minaret and bell-tower spiral treads have 3-voxel headroom per the graph model. Fog and heavens colour, renderer shading, and FPS on a 4.65 MB map with 157 houses are also unchecked.
- **Free scaffolding:** the minaret balconies (z 27) are the highest walkable points near the platform, with a gap of 45. The dome top (z 40) and colonnade roofs cannot be climbed without building, but players can build onto them, so test whether a dome-top bridgehead shortens rounds.
- **Art:** the house kit is procedural (four roof styles, loggias, balconies), so blocks can still read as repetitive from above. Candidates for a v1.1 art pass: a caravanserai courtyard set piece, varied house footprints (L-shapes, courtyards), and more distinct landmarks in the NW/SW low town.
