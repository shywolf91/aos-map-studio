# Sunken Reef Atoll: spec, build and validation (2026-11-03)

**Mode:** stock piqueserver 1.4.2 Babel (`piqueserver.game_modes.babel` + `babel_script` + `map_extensions`). The script builds the platform at z 1, x 206–305, y 240–271; it is not in the VXL.
**Type:** island Babel (summer atoll), 512 × 512 × 64. **Author:** `shywolf91 + AI`.
**Seeds:** layout 20261103 (fixed). Spawn-cover palms: cover seed 2 (fixed; chosen by an exposure sweep). Vegetation, coral, props and sky: 2102350655 (drawn from the OS, saved in `build.json`).

**Status ladder:** generated ✔ · exported ✔ · parser-validated ✔ (own reader and pyspades, byte-identical) · server-loaded ✔ (headless piqueserver 1.4.2, babel) · client-inspected ✘ · playtested ✘

Route checks use a voxel-graph model (3 air to stand, 1-voxel steps, drops), not a collision simulation. Renders are numpy previews, not client captures.

## Owner answers (asked before building) `[USER]`
- **Water:** walkable shallows, `water_damage 0`. AoS water is the single z 63 layer, so the darker channel is a painted bed you can walk across. Teams reach each other on foot; the Babel challenge stays vertical.
- **Footprint:** a full atoll reef ring near the map edges, with surf and open sea outside it. The ring carries the flank routes.
- **Wreck:** heeled over and split in two, enterable, masts broken well below the platform.
- **Sky decor:** gull flocks and cloud puffs near the edges (opt-in floating pieces).
- **Fog:** pale cyan `(160, 208, 216)`, brightness ≥ 150 per channel. `heavens_color (170, 214, 232, 255)`.

## Layout (team 1 / blue authored; mirrored x' = 512 − x)
| element | where | notes |
|---|---|---|
| Lagoon | inside the ring | Painted z 63 bed: pale sand-aqua shallows by the shores, turquoise lagoon, a darker channel ringing the shelf with twin braids north and south to the ring, seagrass patches, and pale pools on the shelf. Deep blue ocean and a surf line lie outside the ring. |
| Crescent islet | inside circle A (128, 256, r 80), outside B (218, 256, r 66); horns at about (184, 199) / (184, 313) | Beach slope H 1 → 5 → plateau H 8, with dunes and dune grass. Every column is solid to z 63. |
| Spawn square | stock x 98–138, y 236–276 | z 54–55 (H 8 with gentle 1-step hummocks); nothing else in the square (enforced: vegetation is undone if it reaches the square) |
| Spawn cover | a palm ring outside the square: two rows on the beach front (x 141–151), rows north/south (y ≈ 230 / 282), a west column | Crowns lean away from the square. The trunks leave ≥ 7-voxel gaps, so the front stays open. Exact voxel mirror for red. |
| Lifeguard lookouts | (146, 226), (146, 286) | On stilts with a deck 9 high and a hut 5 × 5 with a window band and back door. Team-coloured roof and flag, lifebuoy, stair down the back. |
| Lighthouse stump | (70, 256), knoll | Whitewash and sandstone bands, r 6.5. East door toward the spawn, slit windows, spiral stair to a half-collapsed gallery (z 30), rusted lantern frame, the toppled lantern ring and masonry on the sand |
| Beach cabana / fishing shack | (104–116, 199–208) / (105–115, 303–311) | Cabana: stilted, thatched hip roof, doors S + E, porch steps, tiki counter, crates, barrel. Shack: driftwood walls, gable roof, net frame, crab pots. |
| Driftwood piers | y 212 and 299 into the lagoon; a back pier west | Posts every 4, deck H 3, broken ends, rowboats |
| Beach props | islets | Umbrellas + towels, deck chairs, surfboard rack, sandcastle with moat, volleyball net, kayaks, driftwood logs, bonfire, starfish |
| Anchor cay | x 196–211, y 232–279, z 56 (H 7) | Ground under the platform end (x 206–211) is z 56 on every column. Sand ramp on the team's own (west) side only. Cliffs face the enemy and the north and south. |
| Coral shelf | ellipse (256, 256), 70 × 92, reef flat H 2 | Lumps H 3–4 and tide pools with 1-step rims (no 2-voxel holes). 16 coral gardens, each with one dominant kind and colour (brain, staghorn, table, fan, tube sponges), sized large to small. Three mirrored pairs of walk-through coral arches. |
| **Split wreck** | bow half y 180–236 (deck faces blue), stern half y 276–332 (deck faces red), keels x 262 / 250 | 124-long tall ship, heeled 38°, point-symmetric about (256, 256). Verdigris copper sheathing, ochre gun band, plank strakes, coral encrustation. The break leaves all decks open, with exposed ribs. Gun ports and rot holes. Hold silted with reef sand. Gun deck and main deck joined by companion stairs under hatches. Forecastle bunks; stern cabin with table and gilded chest; quarterdeck wheel and stern lanterns; gilded lion figurehead and broken bowsprit; mast stumps with shrouds and a yard with a torn sail. |
| Wreck debris | gap y 236–276 under the platform | Snapped mainmast lying diagonally (low, walk-through gap), yard with draped canvas, cannons, crates, barrels, treasure chests with spilled gold, an anchor with chain, the ship's bell. Point-symmetric pairs. |
| Gull Rock | sea stack (256, 146), summit z 41 | Eroded, banded rock. Twin ledges climb from the south base round west and east to a north landing (h 9), then a cut stair to the summit. Ruined lookout walls, skull flag, gull nests, guano streaks. |
| Rope-bridge ruin | from each north horn's lookout tower (176, 201; deck H 7) toward Gull Rock | Plank bridge with hand ropes, broken about 40 % out with dangling planks; a short stub from the rock's west/east ledge. Not a crossing (no shortcut). |
| Turtle Cay | (256, 376) | Sand cay with a giant turtle-shell rock: hollow sea cave with neck, tail and side arches, scute pattern, head and flippers. Chest and gold inside. Palms. |
| North ring: fishing camp | (256, 54) | Stilt hut (doors N/S, steps), fish drying racks, overturned canoes, fire pit |
| South ring: coral fort | (256, 456) | Ruined bastion, 4-high walls with merlons, gateways N/E/W, inner steps to the wall walk, three cannons in embrasures, an enterable powder store, skull flagpole |
| Corner pieces | NW (66, 92) + mirror: castaway camp. SW (64, 420) + mirror: giant clam | Castaway: lean-to, SOS in stones (painted after the mirror so both sides read correctly), signal fire pile, half-built raft. Clam: tide-pool rocks round a gaping clam with a pearl. |
| Reef ring | superellipse 232 × 200, n 4, band about 18–36 wide | Sand motu (wider at N/S centre and the corners), palms, dune grass, coral rubble crest, coral heads on the ocean side |
| Lagoon patch reefs | 11 clusters per side | Low reef-rock bommies wrapped in coral heads, with open sand between |
| Sky decor (floating, opt-in) | 15 gulls in flocks (Gull Rock, both lighthouses, edges), 13 cloud puffs over the outer ocean | ≥ 72 from the platform, none over a spawn square, ≥ 19 air below. Collapse caveat: a player block touching one, once destroyed, drops it for the round. |
| Corner tag | "SUNKEN REEF ATOLL" painted on the sea floor, SW ocean, x 10–111, y 494–501 | Name only, with a 1-cell shadow |
| Vegetation | non-deterministic | 230 palms, each with 3 of 12 random details (coconuts, dead skirt, sprout, twin trunk, vine, nest, fallen coconuts, flowers, yellowing, kink, ring scars, epiphyte) and one of 8 tints. 53 sea-grape shrubs (3 of 8 details each), 331 grass tufts, 169 garden corals, 105 bommies. |

## Validation (`validation.json`, `probe.json`, `art_metrics.json`)
| check | result |
|---|---|
| Own reader re-encode / pyspades `generate()` | byte-identical ✔ / byte-identical ✔; 0 / 20 000 solid and colour mismatches |
| Same seeds → same SHA-256 in a fresh process | ✔ `8493cce9…` |
| z 63 solid everywhere | ✔ |
| Floating components (excluding sky decor) | 0. Cleanup removed 526 stray voxels (mostly frond tips and small prop fragments). |
| Mirror, non-vegetation, outside the wreck box / sky / tag | 5 voxels differ |
| Platform volume z 0–2 + 1 margin | 0 voxels ✔ |
| Ground under platform ends | blue x 206–211: z 56 on every column. Red x 300–305: z 56 (x 300 is shelf z 61, the accepted 6-vs-5 column offset). |
| Spawn squares | z 54–55, no water, mirror-equal ✔. Live: 400 sampled spawns per team at z 54/55, x 98–138 / 374–414. |
| Trap cells (reachable but not leavable, drops ≤ 19 allowed) | 0. 30 ground pocket voxels were raised automatically. |
| Routes, cost from spawn (blue / red) | own anchor 58 / 58 · enemy spawn 248 / 252 · wreck bow deck 120 / 127 · stern deck 134 / 126 · Gull Rock summit 249 / 249 · Turtle cave 206 / 206 · fishing camp 295 · fort wall walk 298 · own lighthouse gallery 52 · own lifeguard deck 17 |
| Flank route avoiding \|y − 256\| < 130 between the islets | ✔ cost 462, along the reef ring |
| Platform reachable without building | no ✔ |
| Build gap | 54 blocks from the anchor cays (z 56). 41 from the highest reachable wreck point near the platform (z 43, equal for both teams). |
| Spawn exposure (targets ≤ 10 viewers, ≥ 15 % hidden) | blue 5.1 viewers per spot, 28.1 % hidden; red 4.7 / 28.8 % ✔ |
| Live server (piqueserver 1.4.2, babel) | "Map loaded successfully" (0.20 s). Fog and `heavens_color` read. Platform 3 200 cells. Intel (256, 256, 1). Bases z 55. |
| `.txt` | parses: babel True, water_damage 0, heavens_color |
| Art metrics | 5 hue families (target 2–4: sand, aqua, green, coral pink/orange, purple, all from the brief) · coherence 1.32 (target 1.4–2.5, a little busy) · side − top −18.5 L* ✔ · relief 21.3 |

## Known limitations / next steps
- **Wreck shortcut.** The wreck's reachable top near the platform is z 43, so building from it saves about 13 blocks over the anchor cays. Both teams can reach it equally, and it sits under the neutral centre. Owner decision: accept it as a contested high point, or lower the break ends.
- **Wreck symmetry is point-symmetric, not mirrored.** The bow half (forecastle) faces blue and the stern half (taller stern castle) faces red. Reachability is near-equal (deck costs 120/134 vs 127/126), but the silhouettes differ.
- **Busy colour (coherence 1.32, 5 hue families).** The coral palette is what the brief asked for. Fewer garden colours or bigger single-colour gardens would calm it.
- **Unverified in a client:** fog/heavens colours, the heeled decks' walkability (graph model only), the Gull Rock ledges, the spiral stair headroom, and FPS at 2.8 MB.
- `heavens_color` only works on servers whose scripts read it (the owner's convention); stock 1.4.2 ignores it.

## Files
`maps/sunken_reef_atoll_v1/` holds:
- `sunken_reef_atoll.vxl` and `sunken_reef_atoll.txt`
- `build.json`, `validation.json`, `art_metrics.json`, `probe.json`, `server_load.log`
- `renders/`: top-down view, 2 overviews, 11 ground views and a contact sheet

`scenes/sunken_reef_atoll/` holds the generator:
- `sra_spec.py`: SPEC and material ids
- `sra_terrain.py`: heightfield
- `sra_geo.py`: primitives (huts, roofs, stairs, spiral stair)
- `sra_build.py`: set pieces
- `sra_wreck.py`: the split heeled wreck, debris, arches
- `sra_veg.py`: palms, shrubs, coral, beach props
- `sra_sky.py`: gulls and clouds
- `sra_color.py`: colour pass and painted lagoon
- `sra_main.py`: build and export
- `sra_check.py`: gameplay checks
- `sra_render.py`: previews
- `sra_core.py`: VXL codec and canvas

`server_test/sra_babel/` holds the test config and probe script.

**Regenerate** (Python 3.11 venv with piqueserver 1.4.2, numpy, scipy, pillow):
```
cd scenes/sunken_reef_atoll
python sra_main.py ../../maps/sunken_reef_atoll_v1 2102350655   # omit the seed for new vegetation
python sra_check.py ../../maps/sunken_reef_atoll_v1 --pyspades --exposure
python sra_render.py ../../maps/sunken_reef_atoll_v1
cp ../../maps/sunken_reef_atoll_v1/sunken_reef_atoll.{vxl,txt} ../../server_test/sra_babel/maps/
cd ../../server_test/sra_babel && piqueserver -d .    # drop "sra_probe" from scripts to keep it running
```
