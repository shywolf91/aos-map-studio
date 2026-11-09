# Highland Loch Castle — spec, build and validation (2026-11-03)

**Mode:** stock piqueserver 1.4.2 Babel (`piqueserver.game_modes.babel` + `babel_script` + `map_extensions`). The script builds the platform at z 1, x 206–305, y 240–271. It is not in the VXL.
**Type:** island Babel, 512 × 512 × 64. **Author:** `shywolf91 + AI`. **Layout seed:** 20261102 (fixed). **Vegetation seed:** 351370359 (drawn from the OS, saved in `build.json`).

**Status ladder:** generated ✔ · exported ✔ · parser-validated ✔ (own reader + pyspades byte-identical) · server-loaded ✔ (headless piqueserver 1.4.2, babel mode) · client-inspected ✘ · playtested ✘

Route checks use a voxel-graph model (3 air voxels to stand, 1-voxel steps, 2-voxel jumps, drops), not a collision simulation. Renders are numpy previews, not client captures.

## Owner answers (asked before building)
- **Footprint:** the loch is ringed by highlands. Heather and bracken shores and crags run along the map edges, and the flank routes follow the shores.
- **Loch water:** wadeable, `water_damage 5`. Each broken bridge stops 5 voxels short of the rock: build the gap or wade it.
- **Set pieces:** one each, on neutral flanks along the centre line: the signal tower on a north knoll, the boat house and sheep fold on the south shore.
- **Fog:** grey-green mist `(152, 168, 154)`; `heavens_color (178, 192, 182, 255)`.

## Layout (team 1 / blue authored; mirrored x' = 512 − x)
| element | where | notes |
|---|---|---|
| Loch | superellipse x ≈ 34–478, y ≈ 106–406 | Shallow everywhere: players wade on the z 63 bed. Painted bed: shallow sand-green to deep peat, plus grey-green mist bands and weed beds. |
| Castle islet | ellipse round (110, 256); plateau x 64–160, y 198–314 at z 52 | Crag cliffs drop to ledges (z 58–60) and shingle |
| Curtain wall | x 80–156, y 206–306, 3 thick, walk z 40 | Ruined tops with merlons; four corner drum towers with spiral stairs to the wall walk and tower tops; north breach with rubble; south postern; inside stair to the north walk |
| Spawn courtyard | stock square x 98–138, y 236–276 | Cobbles at z 52. A flagstone dais (1 step) surrounds the base (118, 256). Two gapped 1-high ruined footings. Nothing higher than 1 voxel inside the square. |
| **Loch Gate** (east front) | x 152–157, y 234–278 | Open arched passage 33 wide (y 240–272), 5–10 high. Solid masonry z 26–42 above hides the spawn from the platform. Gate towers have stairs to the gate walk (z 26). Team banners hang on the courtyard face. |
| Keep | NW, x 83–108, y 209–230 | 4 floors (z 52/45/38/31) with stairs between, windows and slits, hearth, collapsed NE corner, banner |
| Great hall | SW, x 83–110, y 284–303 | Roofless with gables and roof beams. Doors on the north and east, a loft with a stair, hearth and long table. |
| Courtyard props | outside the spawn square | Well, kitchen-garden beds, hay cart, stable lean-to with hay and trough, practice dummies, barrels |
| West gate + bridge | gate y 252–260; bridge x 30–65, deck z 53 | Intact arched bridge to the west landing (x 8–32, z 53). Paths lead down to the north and south shore terraces (rear and flank access). |
| East apron | x 157–168, y 232–280 | Steps 52 → 55 to the bridge. Stairs at both ends lead down to the islet ledge (safe descent). |
| Broken bridge | x 163–184, y 252–260, deck z 55 | Three piers and arches; the deck ends jaggedly at x 181–184. Fallen stones lie in the water off the line. |
| Gap | x 185–189 | Open water (wade, 8 drop from the deck), or build across |
| Henge rock | superellipse round (256, 256), x 190–322, y 212–300, z 56 | Anchors x 206–211 / 300–305 at z 56. A carved stair out of the water (y 262–268) on each team's own side. Gentle beaches on the north and south. Flagstone path to the henge. |
| Henge | r 15 stone circle (12 stones, 7–11 high), recumbent stone south, ring cairn | Bank r 20–24 at z 54 with gaps at N/E/S/W; floor z 55 |
| Chapel isle | (256, 166) | Roofless chapel: west door, north and south doors, east window with mullion, bell-cote with bell, altar, grave slabs; crosses outside |
| Crannog | (256, 346) | Timber deck on piles at z 59. Round wattle hut with a conical thatch roof and doors N/S. Landing steps out of the water on both sides. |
| Skerries | (184, 160), (182, 356), (118, 142), (116, 372) + mirrors | Pines and birches, cairns |
| Signal tower | knoll (256, 56), base z 30 | Lighthouse-style harled tower with a spiral stair. Gallery (z 14) with railing, beacon brazier, lantern openings, slate cap. Stair path up the knoll. |
| Boat house | x 241–271, y 394–424 | Stone with a hollow slate roof. Water slip with a rowing boat, side walkways, back door. Outside: slipway, mooring posts, an upturned boat. |
| Sheep fold | (256, 462), r 26, flattened terrace | Dry-stone fank with three pens, gates N/S, hay rack; 9 sheep inside, 12 more on the hills |
| Crags | 4 per side | Crag-and-tail outcrops with jointed ledges and mossy tops; cliff faces the loch |
| Bothy, peat bank | (136, 60), (138, 456) + mirrors | Enterable bothy (thatch, chimney, hearth); peat cuttings and stacks |
| Vegetation | non-deterministic, positions mirrored | 226 Scots pines, 218 birches (spring green or golden), 40 rowans, plus heather, bracken, fern, reeds and boulders. Each plant gets 3 random details. |
| Corner tag | "HIGHLAND LOCH CASTLE", SW corner ground, x 8–126, y 490–496, z 32 | Name only, on a levelled strip |

## Validation (`validation.json`, `roundtrip.json`, `probe.json`)
| check | result |
|---|---|
| Own reader re-encode / pyspades `generate()` | byte-identical ✔ / byte-identical ✔, 0 / 20 000 sampled colour mismatches |
| Same seed → same SHA-256 in a fresh process | ✔ `88f85662…` |
| z 63 solid everywhere | ✔ |
| Floating components | 0. Build fragments removed: 12 (1–3 voxels). Vegetation fragments removed: 989 (canopy pieces cut by masks or the map edge). |
| Mirror before centre pieces and vegetation | 845 voxels differ, all at x 257–287 (centre-line set pieces only) |
| Platform volume z 0–2 + 1 margin | 0 voxels ✔ |
| Ground under both platform ends | z 56 rock, both sides ✔ |
| Spawn squares | z 51–52, no water, mirror-equal ✔ |
| Trap nodes (wading allowed) | 0. Six pocket voxels were raised automatically. |
| Routes, wading (blue / red) | own anchor 78.6 / 79.6 · henge 127.6 · enemy anchor 175 / 176 · enemy spawn 293 · chapel 156 / 159 · crannog 161 / 162 · boat house 244 / 245 · fold 275 / 274 · signal gallery 320 / 320 · keep top 88 · wall walk 86 · hall loft 31.5 |
| Safe descent (no damaging drops) | same costs as above ✔ |
| Dry flank route avoiding \|y − 256\| < 130 between the islets | ✔ cost 852, via the west bridges and the shore terraces |
| Platform reachable without building | no ✔ |
| Build gap | 51.3 (from the gate-tower top, z 22). Ground towers start at z 56 (55 to build); the henge bank is z 54. |
| Spawn exposure | blue 20.6 % exposed, 0.7 viewers per spot; red 15.0 %, 0.5 (targets ≤ 10 viewers, ≥ 15 % hidden) ✔ |
| Live server (piqueserver 1.4.2, babel) | "Map loaded successfully" · fog read · platform 3 200 cells · intel (256, 256, 1) · bases at z 51 (dais) · bot spawns at z 49.6 inside both squares |
| `.txt` | parses: babel True, water_damage 5, heavens_color |
| Art metrics | 6 hue families (target 2–4) · coherence 2.16 ✔ · side − top −4.6 L* (target −10 … −20) |

## Known limitations / next steps
- **Loch Gate trade-off.** The gate arch over the front is a structure between spawn and tower zone. The passage is 33 wide and open, but this is the "occasional, not default" pattern. Without it, the spawn was 100 % exposed to the platform. Owner decision: keep it, or remove it and accept the exposure.
- **Bridge gap jump:** whether a sprint-jump clears 5 voxels from the deck (z 55) to the rock edge (z 61) is unverified. If it does, it's a skill shortcut, the same for both teams.
- **`water_damage 5`:** the rate per position update has not been measured; test one wade across the gap.
- **Hue families 6:** heather purple and bracken rust come from the brief. Golden birches and rowan berries add the rest. Muting them is an option.
- **Unverified in a client:** stair headroom (spiral and straight, from the graph model), crouch spots, fog and heavens colour, and FPS at 2.75 MB.
- `heavens_color` only works on servers whose scripts read it (the owner's convention); stock 1.4.2 ignores it.

## Files
`maps/highland_loch_castle_v1/` holds:
- `highland_loch_castle.vxl` and `highland_loch_castle.txt`
- `build.json`, `validation.json`, `roundtrip.json`, `art_metrics.json`, `probe.json`, `server_load.log`
- `renders/`: top-down view, 2 overviews, 12 ground views and a contact sheet

`scenes/highland_loch_castle/` holds the generator:
- `hlc_spec.py`: SPEC and material ids
- `hlc_terrain.py`: heightfield
- `hlc_geo.py`: primitives
- `hlc_build.py`: castle, bridges, henge, set pieces
- `hlc_veg.py`: trees, ground cover, sheep
- `hlc_color.py`: colour pass
- `hlc_main.py`: build and export
- `hlc_check.py`: gameplay checks
- `hlc_render.py`: previews
- `hlc_core.py`: VXL encode/decode, noise

`server_test/hlc_babel/config.toml` is the server test config.

**Regenerate** (Python 3.11 venv with piqueserver 1.4.2, numpy, scipy, pillow):
```
cd scenes/highland_loch_castle
python hlc_main.py ../../maps/highland_loch_castle_v1 351370359   # omit the seed for new vegetation
python hlc_check.py ../../maps/highland_loch_castle_v1
python hlc_render.py ../../maps/highland_loch_castle_v1
piqueserver -d ../../server_test/hlc_babel
```
