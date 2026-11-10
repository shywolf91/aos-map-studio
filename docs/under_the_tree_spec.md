# Under the Tree — v1.0 spec, build and validation (2026-11-09)

Christmas Babel for stock piqueserver 1.4.2 (`piqueserver.game_modes.babel` + `babel_script` + `map_extensions`).
Full 512 × 512, **Babel with assist structures** (knowledge base §8.8). Giant-scale living room on Christmas Eve:
players are toy-sized on a rug between two sofas, with the Christmas tree at the north wall and the fireplace at the
south wall. Every asset is original. No snow anywhere (the "too white" complaint cannot apply).

**Status:** generated ✔ · exported ✔ · parser-validated ✔ (own reader re-encode and pyspades 1.4.2
`VXLData.generate()`, both byte-identical) · server-loaded ✔ (headless piqueserver 1.4.2, Babel, probe script) ·
client-inspected ✘ · playtested ✘.
Renders are numpy previews (`aosmap.render`, `tools/fp_view.py`), not client captures. Route checks use the
`aosmap.nav` voxel-graph model, not a collision simulation.

## Owner answers (asked before building) `[USER]`
* Concept: **Under the Tree** (from Under the Tree / Yuletide Market / Gingerbread Hollow).
* Babel type: **assist structures**.
* Extras: **glow blocks** and **sky decor**. No underground layer.
* Mood: **warm evening** (slightly darkened warm grade, bright warm fog).

## Layout (west half authored, mirrored x' = 511 − x)
Floorboards top z 58, area rug top z 57. No water anywhere (`water_damage 0`). Ground solid to the bottom.

| element | where | z / notes |
|---|---|---|
| Area rug | x 62–449, y 146–366 | green field, star motif, burgundy + gold border; wrinkles 0–2 high (max 1 in fronts and spawns) |
| Spawn gift box (blue W / red E) | walls x 90–148, y 226–286, top z 44 | open-top box wrapped **around** the ±20 square. Whole front open; two rear doors and two doors per side wall. Tissue-paper floor z 56–57 (43 % of stock spawn samples at 56). Lantern posts (glow) on the four corners, bow and tissue tufts on the walls, all outside the square |
| Fronts + tower zones | x 139–219, y 230–282 | bare rug, nothing over 1 high |
| **Gift mountain** (assist structure) | tier 1 x 220–291, y 206–305, roof z 44 | twin-peak stack of presents on the centre line. Tier 1 is a walk-through hall (W/E doors 10 wide, N/S doors 20 wide, windows, lamps, inner stair up into the tier-2 room). On it, a north and a south stack: tier 2 roof z 30, tier 3 roof z 17, tier 4 top **z 4**, each a hollow room with doors. Toy-block stairways (1-voxel risers, 4 wide) link every level. Both summits end at y 238 / 273, one column outside the platform footprint |
| Valley under the platform | tier-1 roof, y 239–272 | open terrace at z 44 with three low parcels (≤ 4 high) |
| Nutcracker | (192, 198) + mirror | 41 tall, on a drum pedestal |
| Wrapping-paper roll | x 108–164, y 206 + mirror | walk-through cardboard core, unrolled sheet |
| Toy blocks | x 150–180, y 160–176 | three 14³ blocks; letters J O Y (west), N E L (east) |
| Cookie plate + mug of milk | centre line, y 133–193 | gingerbread man, star cookies, two-handled mug |
| Ornament tray | x 146–193, y 298–335 + mirror | 3 × 2 cardboard cells, doors between cells and outside, baubles in four cells |
| Teddy bear, spinning top | (106, 330), (130, 306) + mirror | bear 37 tall, seated, scarf |
| Book stack, toy drum | x 198–238, y 330–355; drum centre line y 341 | three books with block steps up each level |
| Candy canes, floor baubles | several | canes lie flat, 3-wide stripes |
| Christmas tree | trunk (255.5, 62), stand, skirt r 46 | three bough tiers (attach z 27 / 14 / 3, radius 96 / 86 / 74), tinsel, 86 hanging ornaments, 68 fairy lights |
| Toy railway | stadium loop, straights y 20 and y 120, x 150–361, arcs r 50 | sleepers + rails 1 high. Push-pull train on the south straight: two locomotives (enterable cabs, footboard steps) and a hopper car of baubles on the centre line |
| Railway tunnel hill | (100, 70) + mirror | walk-through bore, bottle-brush trees, lamps |
| Sofas | x 6–66, y 140–372 + mirror | underside z 43: a 14-high crawl space with lost coin, marble, pencil, sock, dust bunnies. Knitted throw |
| Fireplace | x 186–325, y 468–505 | brick arch (opening x 214–297), walk-in firebox with grate, logs, embers and flames (glow), mantel z 12–16 with candles, clock and garland, four stockings |
| Hearth slab | x 176–335, y 440–505 | slate, z 56, 1-step border |
| Sleeping cat | centre line, y 386–436 | one-off, placed after the mirror |
| Slippers, firewood baskets, poinsettias | south flank, both sides | slipper toe is a walk-in cave |
| Fairy-light cord | west wall socket → tree (+ mirror) | 1-high cord, a glow bulb every 14 |
| Walls | N, S, W, E edges, 6 thick | baseboard + striped wallpaper |
| Sky decor (opt-in floating) | sleigh + 4 reindeer x 192–304, y 358–370, z 0–22; 4 paper snowflakes at y 176 / 350–352 | ≥ 87 from the platform, none over a spawn square, ≥ 30 air below |
| Corner tag | "UNDER THE TREE", SW corner floor, x 12–94, y 492–498 | name only |
| Scatter per half (random) | whole map except keep-outs | 16 parcels (4 enterable), 21 baubles, 15 candles (glow), 11 toy soldiers, 16 pine cones, 10 walnuts, 8 peppermints, 8 ribbon curls, 24 pine sprigs (3 random details each from 7) |

Flank routes: north lane y ~100–140 (train, tunnel hills, parcels under the boughs), south lane y ~380–440 (cat,
slippers, baskets), side lanes under the sofas.

Palette: warm wood, forest-green rug, wrapping-paper schemes (9, picked at random per parcel and per side), brick,
slate, sofa teal-grey. Baked key light from above/south + ambient occlusion, warm-evening grade (0.95, 0.88, 0.82),
walkable luma floor 44.
Glow: 168 sources in the fixed glow palette, 28,502 lit voxels baked into the VXL and listed in
`glow_stored_colors`. Fog `(192, 168, 156)`, `heavens_color (58, 40, 52, 255)`.

## .txt
`name 'Under the Tree'`, `version '1.0'`, `author 'shywolf91 + AI'`, extensions `babel True`, `water_damage 0`,
`heavens_color`, `glow_enabled True`, `glow_stored_colors` (28,670 entries, 1.1 MB). No spawn/entity hooks.

## Validation (`maps/under_the_tree_v1/validation.json`, `server_probe.json`)
| check | result |
|---|---|
| Own reader re-encode / pyspades 1.4.2 `generate()` | byte-identical ✔ / byte-identical ✔ |
| Server load (piqueserver 1.4.2, babel + babel_script + map_extensions) | "Map loaded successfully", `.txt` extensions read, platform 3,200 cells, intel (256, 256, 1), bases z 57 ✔ |
| Live spawn samples (400 per team) | all on z 56–57, x 98–138 / 374–414 ✔ |
| z 63 solid, water columns | all solid, 0 water ✔ |
| Floating | 103 face-connected pieces, all intended sky decor (5 objects). 41 build fragments (131 voxels) removed automatically. 0 unintended ✔ |
| Platform volume z 0–3 (+1 margin) | 0 voxels ✔ (highest voxel under the platform z 40) |
| Ground under both platform ends | rug z 57, solid to the bottom ✔ |
| Spawn squares | z 56–57, nothing overhead, nothing over 2 high, mirror-equal 1.00 ✔ |
| Fronts + tower zones | 0 columns over 2 high ✔ |
| Mirror | solid equal 99.92 %; all 6,599 differing voxels are the cat, sky decor, corner tag and drumsticks ✔ |
| Spawn → own tower zone | 42 / 43 |
| Spawn → enemy spawn on foot | 237 / 237 ✔ |
| Flank routes avoiding the centre | north 517, south 465 ✔ |
| **Assist structure** | both teams walk to all four summit landings (nearest 238 / 239, far side 246–247). Platform not reachable without building. **Build gap 4.5** (4 up, 2 across) from (242, 238, z 4) for both teams |
| Interiors | 53 / 53 recorded rooms reachable from both spawns and exit back ✔ |
| Traps | 0 nodes you can walk into but not out of ✔ |
| Floor reachable | whole map 99.2 %, combat zone 99.6 % |
| Spawn exposure from the platform edge | **100 % exposed**, 9.5 / 9.6 viewers per spot, 32° (targets ≤ 10 viewers ✔, ≥ 15 % hidden ✘) |
| Art metrics | 5 hue families (target 2–4), coherence 2.04 (≥ 1.5 ✔), sides −6.3 L* vs tops (target −10…−20) |
| Reproducible | same seed → same SHA-256 and same `.txt` in a fresh process ✔ |
| VXL | 4.6 MB |

Relaxed for the assist variant: "platform far from any walkable point" and the free-scaffolding check.

## Known limits / next tests
* **Spawn exposure trade-off:** the open front leaves every spawn spot visible from the platform edge (9.5 viewers,
  no hidden spots). Options: accept, or add a gift-tag arch / parcels at the front corners.
* **Round length:** a 4-block build from the summits may end rounds fast. Tune by lowering tier 4 (one line in
  `SPEC['mountain']`).
* **Centre destroy rule:** nobody standing at x 224–288 can destroy blocks (stock script), so player blocks on the
  mountain are hard to clear.
* **Sky decor collapse caveat:** building against a floating piece and breaking that block drops the piece for the round.
* Glow keys and `heavens_color` are read by the owner's setup only; stock 1.4.2 ignores them (baked light still shows).
* Not checked in a client: fog and sky colour, glow look, FPS at 4.6 MB, stair headroom, the 1.1 MB `.txt` load time
  on the live server.
* Name not checked against aos.party.

## Regenerate
```
cd scenes/under_the_tree
python utt_main.py ../../maps/under_the_tree_v1 420769744     # omit the seed for new decoration
python utt_check.py ../../maps/under_the_tree_v1
python utt_render.py ../../maps/under_the_tree_v1
```
Layout seed 20261225 (fixed). Decoration seed 420769744.
SHA-256 `facd03d162ec292aeecd8a70607eca5237b11997cf22f922b7dd9b4905196956`.
Server test: `server_test/utt_babel` (`piqueserver -d server_test/utt_babel`, writes `probe.json`).
