# The Hollow Crown (v1.1, 2026-10-20; v1.0 2026-10-19)

Halloween **ground Babel** for AoS 0.75 / stock piqueserver 1.4.2, built from the owner's brief "Tower of Babel: The
Hollow Crown" and its top-down mock-up: a cursed medieval kingdom around the ruined **Blackthorn Citadel**. Teams
spawn in war camps outside the walls, walk an open causeway, pass under the **Crown Gate** and build their towers
from the citadel's flagstone courtyard. North: the **Weeping Graveyard** under its hill chapel; south:
**Hollowshade Village**; behind each camp, the **Whispering Woods**. Gameplay geometry is mirrored `x' = 512 − x`.

**Status:** specified · generated · exported · parser-validated (own reader + pyspades 1.4.2) · server-loaded
(piqueserver 1.4.2, `game_modes.babel` + `babel_script` + `map_extensions`, blue/red) · client-received (bots:
spectator gets all 3 200 platform cells, both teams spawn in their squares) · **not** client-inspected in a real
client, **not** seen in aos_web, **not** playtested. Renders are numpy previews, not client captures.

Map files: **v1.1** `maps/the_hollow_crown_v1_1/the_hollow_crown.vxl` + `.txt` (3.33 MB, SHA-256 `d2566086…d651c4`);
v1.0 kept in `maps/the_hollow_crown_v1/` (SHA-256 `27bd986b…977a57`). Generator: `scenes/hollow_crown/` (seed 1347,
builds v1.1). Same SHA-256 in a fresh process.

## v1.1 — every building is real (owner rule 2026-10-20) `[USER]`
Owner: all structures must be enterable, with rooms, windows and stairs. Audit of v1.0 and what changed:
| structure | v1.0 | v1.1 |
|---|---|---|
| village houses (36) | doors were solid blocks, windows painted on, no stairs | open front door (leaf swung inside); stone ground floor split into a front room (hearth, table) and a back room by a partition with a doorway; 1-wide stair through a hole in the floor to the jettied upper storey (bedroom, chest); 3-storey houses get a second stair to the top floor; 2 x 2 window openings on every storey (about a third of the upper ones are lit amber glass), attic window in the street gable; exterior stone chimney; village props kept out of doorways |
| mausolea (12) | solid stone blocks | hollow: open pointed doorway between columns, marble floor, sarcophagus with bones, candles, side slit windows |
| crypt entrances (2) | stairs to a sealed iron door | stairs lead through an opening into a 7 x 7 vault (4 high) with coffin niches, an open sarcophagus and ghost candles |
| corner towers (4) + gate drum towers (4) | sealed (drums solid) | hollow paved rooms with a doorway from the ward, head-height slit window openings, a brazier inside; NW/SW tower rooms also open onto the alleys behind the barracks / chapel |
| barracks | upper floor unreachable, windows painted | stair up to the half-fallen upper floor; window openings on both floors; side door |
| Royal Apartments | upper two floors unreachable, no outside windows | two stair flights (ground → floor 2 → floor 3) in the west room; window openings through the back wall and west gable on every floor |
| castle chapel | one door | second door to the south lane |
| hill chapel | bell tower sealed from the nave | doorway nave → bell tower, low tower window openings, bell rope |
| Great Hall, tents, shrines, market stalls | already open | unchanged |
Checked by a new `interiors` test in `hc_check.py`: 120 recorded interior points (every room and floor, both halves)
must be reachable on foot from a spawn and lead back out to the courtyard (graph model).

## Mock-up → stock Babel `[DESIGN]`
The mock-up puts blue north and red south of the castle. Stock `babel_script` fixes the bases at (118, 256) and
(394, 256) `[SRC]`, so the layout is **rotated 90°**: approaches run west/east. The mock-up's single pumpkin field
(blue side) and single village (red side) would unbalance the teams, so each camp gets a **mirrored pair of pumpkin
fields**, the **graveyard + crypts** take the north band and the **village** the south band, both centred on the
axis (neutral). Dead forest fills the rim and corners as drawn.

## Babel integration (stock 1.4.2)
* Platform x 206–305, y 240–271, z 1 (script-built); bases (118, 256) / (394, 256); spawns ±20 on the topmost voxel;
  intel (256, 256) on the platform `[SRC]`.
* `.txt`: `'babel': True`, `'water_damage': 0`, fog `(168, 164, 178)` (pale moonlit lilac-grey, brightness ~170,
  low saturation, neutral between blue and red). **No** spawn/entity hooks (owner rule).
* Cap limit: StateData showed **cap 10** live (config default; `babel_script` sets `map_info.cap_limit = 1` after the
  score limit is taken — same finding as Bone Cathedral). Rotation admins set it.

## Layout (west half; east is the mirror)
| element | where | notes |
|---|---|---|
| ground | z 42 everywhere in the play core (camps, fronts, courtyard, village) | no raised tower zone; solid to the bottom |
| spawn square | x 98–138, y 236–276, z 42 | packed ground, nothing above it (keep-clear) |
| war camp | low broken stone ring x 94–142, y 232–280 | gaps E (front, y 240–272), W, N, S; corner braziers, team banners at the front, 2 striped pavilions (team colour), carts, crates, weapon racks |
| front / causeway | x 139–163, y 226–286 | open path 13 wide on a 61-wide causeway between moat ends |
| **Crown Gate** | gatehouse x 164–173, drum towers r 8 at (168, 230) / (168, 282) | **33-wide pointed arch** (y 240–272), clear 14 high under the raised portcullis (apex 24 up); gold crown relief above; crenellated, machicolated |
| **courtyard (tower zone)** | flagstones x 172–340, y 201–311; keep-clear x 178–334, y 214–298, nothing above | inlaid dark crown mosaic under the platform; worn cobble path gate → anchor; anchor ground x 206–211 flat z 42 |
| curtain wall | x 166–171 (west), y 150–155 (N), y 357–362 (S), top z 22 | ruined crenellations, string course, buttresses, arrow slits; N and S stretches shattered in places |
| breaches + collapsed bridges | west wall y 188–202 and 310–324 | wall cut to the ground; bridge stubs over the moat with the middle span fallen; **rubble ramp** up from the moat bed — flank routes from the pumpkin fields into the ward |
| dry moat | 15 wide around the citadel, bed z 49, outer bank 1 step per cell | walkable ring; ends at the causeway |
| corner towers | r 14 at (172, 156) / (172, 356) | north pair: crenellated with corbel ring and a purple slate cone (one collapsed patch); south pair: shattered crowns |
| **Great Hall / throne room** | x 204–308, y 156–200 | roofless; 5-bay gothic arcade onto the courtyard (west bay's upper wall collapsed); rose window in the gable; stained lancets; marble checker floor; 3-step dais; **black throne** with spiked back and blood velvet; flanking purple-and-gold banners; snapped columns, fallen drum column, charred beams, broken banquet table, ghost candelabra; **the Hollow Crown** — a giant tarnished-gold crown tipped on the floor, one point snapped off |
| Royal Apartments | x 204–308, y 312–356 | three storeys cut open to the courtyard: ragged timber floors, canopy beds, fireplaces, wardrobes, paintings; purple slate roof over the back half with a collapsed section and bare rafters; two places where the wall has fallen let you walk into the ground floor |
| barracks (NW ward) | x 175–200, y 159–184 | two storeys, upper floor half fallen in, bunks, hearth, barrels |
| castle chapel (SW ward) | x 175–200, y 329–354 | roofless, rose window, stained lancets, altar with candles, pews |
| north / south moat bridges | x 248–264 | stone bridges with the middle span fallen; bricked-up posterns (no crossing) |
| pumpkin fields | x 88–150, y 158–222 and 290–354 | furrows and vine rows of pumpkins (some yellow, some carved), a giant carved jack-o'-lantern, two pumpkin-headed scarecrows, broken split-rail fence |
| Whispering Woods | x 0–90, corners, rims | ~420 twisted dead trees (claw-fingered branches, root arches, some with carved glowing faces), leaf litter, mossy boulders |
| stone circle | (46, 256), r 15 | 11 menhirs (one fallen, two leaning), a trilithon facing the camp, altar slab with ghost candles |
| shrines | (34, 150), (34, 362) | slate-roofed wayside shrines with candles and a pumpkin |
| **Weeping Graveyard** | y 52–125, x 122–390 | ~310 gravestones in 6 types (round, cross, tablet, slab, broken, obelisk; ~30 % leaning, ~35 % mossy), 12 gothic mausolea (gable roofs, pediments, columns, cyan door lamps), open burial pits with coffins and spoil heaps, crypt stairs to iron doors, railed family plots, cyan ghost lanterns, dead trees, low boundary wall |
| skeletal hands | (196, 86) / (316, 86), in sunken burial grounds | forearm bursting from heaved earth, 2×2 bones, clawed fingers reaching ~25–30 above the ground; ringed by graves on the terraces |
| hill chapel | (256, 40), plateau z 34 | buttressed nave, stained lancets, rose window and pointed door facing the graveyard, roof half fallen (bare rafters), bell tower with a broken spire |
| **Hollowshade Village** | y 380–475 | cobbled high street (y 418–426), main street (x 250–262) to the square (x 228–284, y 436–468); 36 crooked half-timbered houses (stone ground floor, jettied upper floors, steep black/purple slate roofs, chimneys, amber windows; ~30 % with collapsed roofs); market stalls with orange/purple awnings; **giant carved jack-o'-lantern** on the axis; wells, gallows, carts, barrels, lanterns |
| corner tag | SW ground, x 14–110, y 494–501 | "THE HOLLOW CROWN" only |

Palette (brief): charcoal/weathered stone, black slate + dark purple roofs, dead grass / muddy brown / grey dirt,
charcoal trunks, muted orange/amber pumpkins, pale grave stone + moss; accents blood red, ghostly cyan, sickly green.
Light pools around lamps and lanterns are painted on the ground (colour device; no renderer lighting assumed).

## Validation (`maps/the_hollow_crown_v1/validation.json`; routes are a graph model, not a collision sim)
| check | result |
|---|---|
| own reader round trip | re-encode identical, every surface voxel coloured, z 63 solid |
| pyspades 1.4.2 `VXLData.generate()` | **byte-identical**; 0/20 000 solid and colour mismatches; `get_z` at both bases 42 |
| floating components | **0** (367 orphan twig/fragment voxels removed at build, none > 40 voxels) |
| mirror (x' = 512 − x) | 0 solid / 0 material mismatches |
| platform volume z 0–2 (+1 margin) | 0 voxels |
| ground under platform ends | x 206–211 and 300–305: all z 42, solid to the bottom |
| spawn squares | 1 681/1 681 cells at z 42, both teams |
| routes (blue / red) | own platform end 68 / 69 · throne hall 142 · enemy spawn 236 · village square 254 · chapel door 280 · own stone circle 42 — parity ≤ 1 |
| **interiors (v1.1)** | **120 / 120** rooms and floors reachable from a spawn and back out (houses incl. upper/top floors, mausolea, crypt vaults, tower and drum rooms, barracks upper floor, all three apartment floors, both chapels, bell tower, Great Hall) |
| traps | 20 isolated cells of 247 364 ground cells (woods/rim pockets, under leaning gravestones), none in buildings; every pit, crypt, stair, moat and breach walks back out |
| build gap | 40 blocks from the courtyard (z 42) to platform level; platform not reachable on foot |
| spawn exposure (platform edge → spawn heads) | blue **0.0** viewers/spot, **100 %** hidden; red 0.01, 98.9 % (targets ≤ 10, ≥ 15 %) |
| art metrics (`tools/art_metrics.py`) | 9 453 colours, 3 hue families, coherence 1.76, side − top −10.5 L* (inside the reference bands) |
| live server (v1.1) | loads; babel on; `map_info.cap_limit` 1; fog + extensions read; platform 3 200 cells; 400 sampled spawns per team all z 42 in the squares; intel (256, 256, 1) |
| live client (bots) | spectator receives the map with all 3 200 platform cells; bots spawn at eye z 39.6 inside their squares; StateData cap 10 |
| determinism | same SHA-256 in a fresh process (Python 3.11, numpy 2.4.6) |

(Numbers above are for v1.1; v1.0 differed only in the building interiors: 12 trap cells, 321 orphans removed.)

## Design trade-offs to judge in play
* **The Crown Gate stands on the front by design.** Owner rule (2026-10-19): structures between spawn and tower zone
  are fine as long as there is an opening players walk through; only solid blockers are out. The passage is 33 wide
  and 14+ clear under the portcullis. Side effect: the gatehouse hides the spawn from the platform completely
  (0 viewers vs the <= 10 target), which is more cover than needed; raise the arch (`SPEC['gate']['spring']` / `'R'`)
  if playtests show platform holders need to see more.
* **Walled courtyard.** The tower zone is enclosed by castle walls by design (the brief's concept). The wall tops
  (z 22) are not reachable on foot; the nearest wall top is ~35 from a platform end, so building from it is not
  cheaper than building from the ground.
* Ground Babel, 40-block climb (Bone Cathedral 39, Wicker King similar).
* Destroy band (stock): blue can't remove blocks while standing at x ≤ 288, red at x ≥ 224.

## Known limits / next tests
* Not playtested and not seen in a real client. Check fog (lilac-grey; try brighter if it reads flat), stained
  glass and the courtyard mosaic from the platform.
* Wall walks and tower tops are scenery (no stairs); every building floor is reachable.
* Upper floors overlook the village and ward only; none is within 24 of the platform (build gap unchanged at 40).
* Route numbers are a graph model (3 air to stand, 1-voxel step, drops ≤ 9), not a collision simulation.

## Regenerate
```
cd scenes/hollow_crown
python hc_main.py ../../maps/the_hollow_crown_v1_1                    # VXL + TXT + build.json (+ mat.npy, terrain_H.npy)
python hc_check.py ../../maps/the_hollow_crown_v1_1 --pyspades --exposure
python hc_render.py ../../maps/the_hollow_crown_v1_1                 # numpy previews -> renders/
```
Modules: `hc_build.py` (SPEC, terrain, citadel, graveyard, village, woods, mirror, cleanup), `hc_props.py`
(materials + prop library), `hc_color.py`, `hc_core.py` (VXL writer/reader, noise), `hc_main.py`, `hc_check.py`,
`hc_render.py`. Server: `server_test/hc_babel/config.toml` (stock script list + `babel_script`; `hc_probe` writes
`probe.json` and stops the server — drop it to run normally).
