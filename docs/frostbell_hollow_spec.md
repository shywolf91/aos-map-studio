# Frostbell Hollow — spec (v1.0 and v1.1)

**Status: server-loaded** (2026-11-10), v1.0 and v1.1. **v1.1 is the current version** (shorter arch gate). Loaded on a live piqueserver 1.4.2 in Babel mode by `aosmap.kit.probe`.
Not client-inspected and not playtested. The renders in `maps/frostbell_hollow_v1*/renders/` are numpy previews,
not client captures.

Christmas Eve alpine village at twilight. Stock Babel (piqueserver 1.4.2 `babel_script`), ground Babel, full
512 × 512, no assist structures. Branch `map/frostbell-hollow`, generator `scenes/frostbell_hollow/`, built with
`aosmap.kit`. Planned by Fable, implemented by Opus, reviewed by Fable `[USER 2026-11-10]`.

## Owner answers `[USER 2026-11-10]`

Full text is in `docs/knowledge/project_memory.md`. Short form:

| question | answer |
|---|---|
| mode | stock Babel, no assist structures reaching the platform |
| type | ground Babel, full map, ring of rocky pine-covered mountains (not white walls) |
| under the platform | flat ground, solid anchors, no enemy-side stairs |
| centre | Christmas market: stalls, tavern, giant spruce, ice rink, sleigh workshop, present crates, carousel, benches |
| flanks | railway (station, ridge tunnel, stopped train) / creek (pine forest, covered bridge, water mill) |
| water | walkable, `water_damage` 0 |
| extras | underground mine + cellar tunnels, sky decor, glow blocks, `heavens_color` twilight blue-violet |
| fog | left to Claude: bright, cool lavender-grey |
| tag | north-east corner, on the ground |
| must-haves | nativity stable, unique snowmen, sledding hill, toy-soldier gatehouse arches, chapel with bell tower, post office with mailbox, ice-sculpture garden |
| avoid | flat white snowfields, 1-block pillar fields, 1-voxel stripes, fake buildings, copyrighted characters, anything solid blocking spawn → tower zone |

### How three rules are read together `[DESIGN]`

* The brief says "avoid anything solid between spawn and the tower zone". The standing rule of the same day says
  "dress the front, never block it". They are read as one rule: the front gets low details a player walks around
  (≤ 5 voxels tall, lantern posts ≤ 6), and never a wall, screen or building that stops movement.
* The toy-soldier gatehouse arch is the one tall object on the front. The owner asked for it at the village edge
  with an open passage. It is built with at least 60 % of its width open across the front band and no pier wider
  than 5 voxels. It is also the main cover against spawn camping from the platform.
* If the spawn-exposure targets (≤ ~10 viewers per spot, ≥ 15 % hidden) cannot be met with the front this open,
  the numbers are reported to the owner. Nothing more is added to the front without asking.

## Layout

Mirror `x' = 512 − x` (`x512`, column 255 copied into 256). Coordinates below are the west (blue) half and the
centre axis. z = 0 is the sky; a "floor z" is the solid voxel a player stands on. `[DESIGN]` unless tagged.

### Elevations

| area | floor z |
|---|---|
| valley floor, market, front, anchors | 50 (±1 gentle noise outside the anchors) |
| village and spawn square | 48–49, gentle mounds, no holes |
| railway embankment (north flank) | 49 |
| creek (south flank) | water at z 63; banks slope from 50 down to 61 over about 28 voxels; ice shelves at z 62 |
| mountain ring | rises from 48 to peaks at z 8–14; nothing above z 6 |
| underground floor | 59 (3–4 air above, at least 3 solid between tunnel roof and surface) |

Build gap from the anchor ground to the platform (z 1) is about 48. The platform cannot be reached on foot.

### Zones (west half; east is the mirror)

| zone | x | y | notes |
|---|---|---|---|
| mountain ring | 0–40 | all (and y 0–40, 472–511) | rock faces, dark pines, off-white caps; walkable foothills, passable |
| village | 44–150 | 180–330 | houses on the west, north and south of the spawn square, lanes ≥ 8 wide |
| spawn square (stock) | 98–138 | 236–276 | clear land, +4 no-prop margin (94–142, 232–280) |
| chapel with bell tower | 58–90 | 244–268 | behind the spawn; nave, bell tower to z ≈ 26 with stairs, candles (glow) |
| post office | 100–126 | 196–222 | counter room + sorting room, mailbox overflowing with letters outside |
| village houses (3–4) | 48–140 | 184–232, 282–326 | timber and stone, gingerbread trim, upper floors, furniture |
| toy-soldier gatehouse | 146–151 | 222–290 | passages z 41–49, gallery room z 30–39 with stairs in the end towers, roof z 28; ≥ 60 % open across y 232–280; two toy-soldier statues at the outer ends |
| front (dressed, open) | 152–199 | 232–280 | low props only: sleds, firewood, hay bales, hand cart, rocks, low bushes, benches, one open one-room hut at each edge of the band; every north–south section ≥ 70 % free |
| tower anchor ground | 200–211 | 236–275 | flat z 50, solid to the bottom, prop-free, no stairs on the east face |
| under the platform | 212–300 | 236–276 | flat cobbles, only props ≤ 2 tall |
| market north | 160–255 | 130–232 | stalls (enterable, 4 per side), present-crate stacks, benches, lantern posts |
| market south | 160–255 | 280–384 | stalls, crate stacks, ice-sculpture garden around the rink |
| north flank: railway | 44–255 | 46–126 | track along y ≈ 84; ridge spur with a 5 × 5 tunnel at x 150–176 and a walk-around path south of the spur |
| south flank: creek | 44–255 | 386–466 | creek along y ≈ 430 through pine groves; water mill at x ≈ 150 |

### Centre-axis one-offs (self-mirrored about x = 255.5)

| object | centre (x, y) | size | notes |
|---|---|---|---|
| station | 256, 68 | 28 × 12 | small enterable station north of the track, platform canopy |
| stopped train | 256, 84 | 60 × 5 | locomotive + 3 open carriages; listed as an asymmetric box |
| nativity stable | 256, 116 | 14 × 10 | open-fronted stable, figures, star lantern |
| mulled-cider tavern | 256, 148 | 32 × 24 | ground floor, upper floor, cellar linked to the tunnels |
| giant village spruce | 256, 190 | radius ≤ 13, top z ≥ 12 | 50 voxels north of the platform edge; ornaments and star glow |
| carousel | 256, 292 | radius 8 | open, walk-through, ≤ 8 tall |
| ice rink (frozen pond) | 256, 326 | 34 × 22 | ice blocks at floor level, low kerb with gaps |
| sleigh workshop | 256, 366 | 30 × 20 | open floor plan, wide doors, a sleigh inside |
| covered bridge | 256, 432 | deck z 52, y 414–450 | crosses the creek valley north–south |
| sledding hill | 256, 476 | y 448–500 | run from z ≈ 30 down to 50, sleds |

Each village also has the chapel, the post office and a gatehouse (mirrored pairs). The singular set pieces are on
the axis so that neither team is closer to them.

### Underground `[DESIGN]`

* Two entrances per village: a house cellar stair near (72, 300) and a mine adit in the hillside near (50, 210).
* Tunnels 3 wide, floor z 59, with wider elf-mine chambers (carts, crystal and lantern glow).
* Exits in the market through stall cellar hatches near (190, 180) and (190, 330), each with a stair.
* The two sides join through the tavern cellar on the axis.
* No tunnel under the tower corridor east of the gatehouse (x 150–215, y 232–280), so anchors stay solid.
* Every chamber and tunnel is in the interiors test: reachable from a spawn and with a way out.

### Sky, glow, colour

* Sky decor (expected floating, listed): a sleigh-and-reindeer silhouette near (256, 60, z 6–10) and four cloud
  puffs. All ≥ 60 from the platform, not over spawn squares, ≥ 8 air below. Collapse caveat applies.
* Glow sources from the fixed palette, warm first: (255,175,95), (255,255,95), white for the star,
  (95,255,255) sparingly on ice sculptures. No red sources. Baked with `aosmap.kit.color.bake_glow`.
* Snow is off-white with blue-grey shade, max channel ≤ 212. Floors luma ≥ 40. Large areas are broken up with
  cobbles, stone, timber, evergreens and warm light. No snowfield wider than about 24 voxels without a break.
* Fog `(166, 160, 188)`. `heavens_color (52, 44, 104, 255)`.
* Corner tag "Frostbell Hollow" in the north-east corner (high x, low y), painted on the ground.

## Checks to pass before the art pass

`python -m aosmap.kit.babel_checks` (all sections), plus: front openness per north–south section, gatehouse open
share, tunnel exclusion under the tower corridor, interiors for every room, floor and tunnel, both flanks
walkable end to end with similar route length (within 10 %).

## As built (v1.0) `[RUN 2026-11-10]`

Release build: vegetation seed **4015401698** (OS-drawn, saved in `build.json`), layout seed 20261110.
`.vxl` 2,851,828 bytes, SHA-256 `d5efd6fb15b999386dd5a290461ae1762a3877e0abc4fce85e35bdf0f5d1eab0`.
`.txt` 2,491,178 bytes (45,114 `glow_stored_colors` entries; parses in about 0.4 s).

### Deviations from the layout above

* Post office at x 96–122 (not 100–126), a T shape with a parcel wing, to keep an 8-wide lane.
* Gatehouse spans y 220–292 (not 222–290) so a two-flight stair fits in each end tower.
* Covered bridge has earth abutments at z 52 (y 398–413, 451–461); the sledding hill runs y 462–500.
* Creek meanders 430 ± 9, 7–13 wide, banks 24 wide; the mill is placed from the creek line.
* Market: organic plaza with six lanes and 17 stalls per side (spec said 4), smallest gap 7.
* Villages: 4 houses (3 with wings), a barn, 3 sheds, a well, woodpiles, open fence segments.
* Mountain ring is 27–56 deep with spurs and coves. Highest solid voxel is z 7.
* Tag: the NE corner is mountain, so the tag is painted on flat ground in the NE quarter (x 356–454, y 105–115).
* Ice-sculpture garden blocks are carved as bell, fir, obelisk, seal and cairn; harp and angel are on feature pads.
* About 22 % of windows are filled with glowing glass and are not see-through.
* Not built: chimney smoke, reeds, rail bends.
* Tree and grove positions come from the vegetation seed. Terrain, buildings, market, front props, feature pads,
  outcrops and the giant spruce are fixed by the layout seed.

### Validation

| check | result |
|---|---|
| own reader, re-encode | identical |
| pyspades 1.4.2 `generate()` | identical; 0 / 20,000 sampled mismatches |
| floating components | 0 unintended; 5 expected (sleigh x 228–279, y 48–66, z 8–9, and 4 clouds), sky rules met (≥ 126 from the platform, ≥ 15 air below, none over a spawn) |
| mirror (`x512`) | 0 solid and 0 material mismatches outside the declared boxes (train, tag, pads, sky) |
| platform volume, z ≤ 2 margin | clear; nothing solid at z ≤ 6 |
| ground under platform ends | flat z 50 both ends, no water |
| spawn squares | tops z 48/49, 0 water columns, 0 roof columns, margins prop-free |
| spawn exposure (calibrated) | blue 2.92 viewers per spot, 72.6 % hidden; red 2.65, 72.6 % hidden (targets ≤ 10, ≥ 15 %) |
| front openness | worst north–south section 81.6 % free; tallest prop 6 (4 lantern posts), others ≤ 5 |
| gatehouse | 73.5 % open across the front band, widest pier 5 |
| build gap | 46 blocks, both teams; platform not reachable on foot |
| anchors | flat, not raised, prop-free |
| routes | enemy spawn 236 steps for both teams; safe descent to the tower zone 30 / 31 |
| flanks | north 456, south 458 steps (0.4 % apart), same for both teams |
| trap cells | 0 |
| interiors | 172 rooms, floors, tunnels and chambers, all reachable with a way out |
| underground | 5,100 cells, 100 % reachable from each spawn, 100 % walk-out; 0 tunnel air under the tower corridor |
| largest featureless flat patch | 22 (limit 24) |
| periphery reachable | 87.2 % (tree tops count as unreachable columns) |
| graybox vs art collision | 0 unallowed standable-cell changes |
| colours | near-white surface 0.24 %; min floor luma 40.5; top-surface median luma about 90; glow sources warm, none red |
| seeds | 6 test seeds and the release seed all pass 26 / 26 with 0 traps and 0 floating |
| reproducibility | same vegetation seed gives the same SHA-256 in two fresh processes |
| `.txt` | `check_txt` ok; author `shywolf91 + AI`; no spawn hooks; glow keys are `(x, y, z)` tuples |
| live server (piqueserver 1.4.2, babel) | loaded; platform 3,200 cells at z 1; intel (256, 256, 1); 400 spawns per team inside the stock squares at z 48/49; fog and extensions read |
| tests | `pytest`: 22 passed |

Route, trap and interior results come from a graph model, not from play. The colour figures were measured at
seed 12345 before tree placement became seed-driven.

### Known limits and open points

* Not seen in any client: fog, `heavens_color`, the glow look and FPS are unverified.
* `glow_*` and `heavens_color` are read by the owner's server setup only. Stock 1.4.2 shows the baked light.
  How a glow-aware server handles 45k entries is untested.
* `water_damage` needs `piqueserver.scripts.map_extensions` in the script list (it is 0 here).
* The sky pieces float by request. Breaking a player block attached to one drops it for the round.
* v1.0's gatehouse is a 73-long building with four 9-wide passages. v1.1 replaces it with the 33-long arch
  (section below).
* The mirrored west twin of the tag strip is a flat empty strip.

## v1.1: arch gate `[USER 2026-11-10]` `[RUN 2026-11-10]`

The owner asked to shorten the gatehouse and measure the cost. Six variants were measured with the release seed:

| variant | length | blue viewers / hidden | red viewers / hidden | targets met |
|---|---|---|---|---|
| full (v1.0) | 73 | 2.92 / 72.6 % | 2.65 / 72.6 % | yes |
| band (front width only, stair towers in the band) | 57 | 2.92 / 72.6 % | 2.65 / 72.6 % | yes |
| arch, unpolished (central gate) | 33 | 3.24 / 58.5 % | 2.98 / 58.5 % | yes |
| low (full length, solid only z 36–40) | 73 | 8.29 / 14.3 % | 7.42 / 19.0 % | no (blue) |
| twin towers with a light bridge | 59 | 8.30 / 14.3 % | 7.43 / 19.0 % | no (blue) |
| twin towers, open between | 10 each | 10.20 / 0 % | 9.98 / 0 % | no |
| none (statues only) | — | 10.21 / 0 % | 10.00 / 0 % | no |

Findings `[RUN]`: only about 11 of the 65 platform-rim eye positions can see the spawn square. Their sightlines
cross the gate line (x 146–151) between z 28 and z 40 and within y 236–276. So the solid band's **height** hides
the spawns; length outside y 236–276 hides nothing; cover placed beside the front changed no number.

The owner chose the arch. **v1.1 as built** (same vegetation seed 4015401698, so only the gate area differs):

* Gate footprint x 146–151, y 240–272 (33 long). Four piers (y 240–243, 250–252, 260–262, 269–272), three
  passages 6 / 7 / 6 wide at z 41–49. Players can also walk round both ends of the gate.
* Solid masonry band z 28–40 with a crenellated top and a raised centre block (z 24–27). It is a gate, not a
  building: no room, no doors or windows, no interior record. v1.0's walkable gallery is gone.
* Toy soldiers stand free on plinths at y 227–231 and 281–285, outside the front band, each holding a drum.
* The old end-tower ground has low hedge stubs, a sled, a lantern post and a snowman pad.
* `.vxl` 2,851,612 bytes, SHA-256 `a85dfaeb2fa04db0bc2e835a4f5173482a359a132cd8e73a5715c1651a238f2a`.
  `.txt` 2,533,055 bytes, `version = '1.1'`.

| check | v1.0 | v1.1 |
|---|---|---|
| all checks | 26 / 26 | 26 / 26 |
| spawn exposure blue (viewers / hidden) | 2.92 / 72.6 % | 1.78 / 58.5 % |
| spawn exposure red (viewers / hidden) | 2.65 / 72.6 % | 1.56 / 58.5 % |
| gate open share across the front band | 73.5 % | 71.4 % |
| widest pier | 5 | 4 |
| narrowest gate passage | 9 | 6 |
| interiors checked, all reachable | 172 | 164 |
| periphery reachable | 87.2 % | 86.8 % |
| front min free, featureless patch, flanks, build gap, traps, floating | 81.6 %, 22, 456 / 458, 46, 0, 0 | same |
| live server probe (piqueserver 1.4.2, babel) | loaded | loaded; platform 3,200 cells; 400 spawns per team in the stock squares |

Three other seeds with release 1.1 also pass 26 / 26 with 0 traps and 0 floating. Mean viewers fell below the
unpolished arch (3.24 → 1.78), probably because of the merlons and centre block; this was not isolated `[OPEN]`.

### Regenerate

```bash
python scenes/frostbell_hollow/fh_main.py out/frostbell_hollow_v1_1 4015401698                 # v1.1 (default release)
python scenes/frostbell_hollow/fh_main.py out/frostbell_hollow 4015401698 --release 1.0       # v1.0, byte-identical
python scenes/frostbell_hollow/fh_main.py out/new_build                                       # new random vegetation seed
python scenes/frostbell_hollow/fh_render.py out/frostbell_hollow_v1_1
python -m aosmap.kit.probe out/frostbell_hollow_v1_1 --mode babel
python scenes/frostbell_hollow/fh_main.py out/fh_exp 4015401698 --gate band                   # gate experiments
python scenes/frostbell_hollow/fh_main.py out/fh_graybox --graybox                            # gameplay geometry only
```
