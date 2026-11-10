# Frostbell Hollow — spec (v1.0)

**Status: specified** (2026-11-10). Nothing is generated yet. This file is updated at each rung of the status ladder.

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

## Validation, limits, regenerate

To be filled in after the build.
