# Yulehaven Isles — spec (v1.0)

**Status: server-loaded** (2026-11-15). The map loaded on a live piqueserver 1.4.2 in Babel mode via `aosmap.kit.probe`. Checks passed:
platform 3,200 cells, `babel` + `water_damage 1` + `heavens_color` + glow keys read, fog read, and 400 sampled spawns per team on the
stock squares at z 47–48. **Not client-inspected and not playtested.** The renders in `maps/yulehaven_isles_v1/renders/` are
numpy previews, not client captures.

Christmas Eve in a Nordic fishing archipelago. Two rocky spawn islands of red and ochre fishing cabins face each
other across a dark winter sea. An ice-locked cargo ship sits on the central islet under the platform, and skerry
chains run along both flanks. Stock Babel (piqueserver 1.4.2 `babel_script`), island Babel, no assist structures.
Branch `map/yulehaven-isles`, generator `scenes/yulehaven_isles/`, built with `aosmap.kit`.

## Owner answers `[USER 2026-11-14]`

The full brief is in `docs/knowledge/project_memory.md`. The three follow-up answers were:

| question | answer |
|---|---|
| sea caves (the sea is the bottom layer, nothing can pass under it) | roofed wading passage: the caves under each spawn island open into a short rock-roofed sea passage that comes up in the islet's own cave |
| lighthouse / chapel position on the flank chains | at one team's end: lighthouse at the Blue end of the north chain, chapel at the Red end of the south chain |
| `water_damage` | 1 |

### How the brief is read `[DESIGN]`

* "Shallow wading routes" can't be literal: all AoS water has the same depth (z 63 = seabed). Wading means standing
  in water, and every water cell does damage. Every water edge is a z 62 lip (beaches, rock hops, ice, pier
  ladders), so a wader steps straight out. The wading lanes are painted lighter on the seabed.
* "Ice-locked": the lagoon in the islet and the trawler basin are solid ice at z 62, flush with the water, so every
  fishing hole has a step out.
* Balance by role: each team has one tall landmark at its flank end (Blue: lighthouse, north; Red: chapel, south) and
  one other (Red: Yule goat, north; Blue: ice-fishing camp, south). The post office (Blue) and the sauna (Red) share
  one mirrored shell.

## Layout

Mirror `x' = 512 − x` (`x512`, column 255 copied into 256). Coordinates are the west (Blue) half and the axis.
z = 0 is the sky. A "floor z" is the solid voxel a player stands on. Every number lives in `scenes/yulehaven_isles/yh_spec.py`.

### Elevations

| area | floor z |
|---|---|
| spawn square (stock 98–138 × 236–276) | 48, gentle mounds to 47 |
| front crest x 148–153 (y 232–280) | 45, rising 0.6 per column from the square, then down to the anchor |
| tower anchor ground x 200–212, y 236–276 | 52 flat, solid to the bottom; sheer 10-voxel enemy face into the channel; no stairs |
| island plateau / villages | 48 ± granite domes up to 5 |
| beaches | 62 lip → 60, then rising to the plateau over about 22 voxels |
| central islet | rim 62 → 58, frozen lagoon (ice) 62, north outcrop peak 42, south plateau 53 |
| skerries | peaks 50–55 |
| caves | Blue chamber floor 60; islet chamber floor 61; passage over the water (water node 63, air z 59–62) |

Build gap from the anchor ground to the platform is about 50 blocks. The highest walkable point near the platform is z 44
(the ship), 42 blocks below the platform, so the platform can't be reached on foot.

### Zones (west half; east is the mirror unless marked one-off)

| zone | where | notes |
|---|---|---|
| spawn island | x 36–212, y 146–366 | granite, heath, gravel beaches with a seaweed band, spruce groves |
| north village | x 96–153, y 196–232 | 2 two-storey cabins + 1 one-storey; north cabin 3 is spawn cover on the NE corner |
| south village | x 96–153, y 280–308 | 2 two-storey cabins + the smugglers' shed (stair down to the cave) |
| west / shore cabins | x 52–73 | net loft (2 storeys), west cabin, two stilt cabins on the shore |
| front (dressed, open) | x 143–199, y 236–276 | two walk-through fish sheds (8 × 7, 9 tall) on the crest, upturned boat on trestles, fish-crate stacks, firewood stack, net reel, kicksled |
| inner north shore | x 160–207, y 140–214 | boathouse half over the water (sea doors open, slip with a stair out), trawler frozen at the dock (hold, wheelhouse, gangway, mast with lights), stockfish racks, lobster-pot stacks |
| inner south shore | x 160–211, y 296–372 | post office (Blue) / sauna (Red), same shell, pier south into the sea; granite spine over the cave tunnel |
| channel + rock hops | x 201–229, y 217–222 | seven 3 × 3 rocks one water column apart (centre 61, rim 62) |
| wading lanes | y ≈ 202 and y ≈ 315 | painted lighter on the seabed (still water, still damaging) |
| central islet (self-symmetric) | x 226–286, y 178–344 | ice lagoon with the cargo ship, outcrop + spruce (north), plateau + bonfire ring (south) |
| cargo ship | x 248–264, y 220–291, deck z 50 | hull breaches at ice level on both sides; hold (two stairs to the deck), forecastle cabin, deckhouse mess + wheelhouse, funnel, two masts to z 28 |
| bonfire ring | (256, 322), r 11 | 8 standing stones 6–9 tall, log ring, painted ember bed with glow; not a blocker |
| north flank chain | y 72–150 | pier → S1 → rope bridge → S2 → broken pier (one sunk, sagging stretch) → S3 → rope bridge → M (axis) → mirror |
| south flank chain | y 361–439 | y-mirror of the north chain |
| underground | Blue chamber (106, 318); tunnel east at y 316–318 under the shore spine; passage x 186–242 at y 318 (20 water cells, roof toothed with 10 slabs so it isn't a dry walkway); islet chamber (256, 318) with a stair up to the plateau at y 305; sea-cave mouth in the south headland (110, 360) | |

### One-offs (cosmetic boxes; placed after the mirror)

| object | where | notes |
|---|---|---|
| lighthouse | (90, 70), north chain, Blue end | red with white bands, spiral stair (plinth under the first steps), lamp room floor z 26, gallery, cone roof, helix of string lights, lamp glow |
| Yule goat | (422, 72), north chain, Red end | giant straw goat with red ribbon bands, curled horns, beard; belly 8 above the ground (walk under it) |
| stone chapel | (422, 439), south chain, Red end | nave with pews, altar, candles and lancet windows; bell tower with a square spiral stair to the bell loft |
| ice-fishing camp | (90, 439), south chain, Blue end | ice shelf, three enterable A-frame tents, fishing holes with stools and rods, a small fire |
| decorated spruce | islet outcrop (256, 192) | kit conifer, h 18, star (glow) and baubles |
| giant mailbox | Blue post office | red box on a post with a flag, letters jammed in the slot and spilt over the ground |
| sauna jump tower | Red sauna pier end | platform 5 above the deck with a stair and a board over the sea |
| snowmen (8) | beaches | driftwood arms, buoy head or belly, three random details each (hat, pipe, lantern, scarf, buttons, sign) |
| present crates (24) | beaches | 2–4 voxel boxes with ribbon crosses |
| iceberg + tag | SW corner | "YULEHAVEN ISLES" in red on an ice plate at z 8 (sky level), on one ice stalk from the iceberg peak (grounded) |

The sites for the lighthouse, goat and chapel are levelled into their skerries with a skirt no steeper than 1 per voxel.

### Sky decor (opt-in, asked for)

A sleigh-and-reindeer silhouette (2× scale, south sea), five snow clouds and three faint aurora curtains along the north
edge (teal-green hem to violet top). Every piece is ≥ 60 from the platform, not over a spawn square, and has ≥ 8 voxels of
air below. All are listed in `build.json` → `sky_objects`. **Collapse caveat:** a player block built against a sky piece,
once broken, drops that piece for the round.

### Glow (owner's glow format, knowledge base §11.4)

557 sources: candles in a third of the windows, string lights under every eave (one bulb every 3), lighthouse lamp + helix,
trawler mast stays, ship lanterns and mast lights, spruce star + baubles, bonfire embers, chapel candles + windows, the
ice-camp fire and snowman lanterns. Lit voxels are baked into the VXL; `glow_stored_colors` holds the originals.

### Metadata (`yulehaven_isles.txt`)

`fog = (172, 174, 192)` is a cool lilac-grey, a hue the granite, timber, red and sea palette doesn't use, and neutral between
the two teams. Extensions: `babel: True`, `water_damage: 1`, `heavens_color: (46, 74, 112, 255)` (the key takes one colour;
it's a teal-violet in between), `glow_enabled`, `glow_stored_colors`. There are no spawn hooks (owner rule). The `.txt` is
2.1 MB because of the glow table.

**Water damage:** `map_extensions` subtracts `water_damage` HP each time the client sends a position update while it's
in water (z ≥ 61) `[SRC]`. The rate of those updates is set by the player's client, so a bot can't measure it.
`[OPEN]` Check in-client how fast HP drops while wading, and whether 1 needs to go up.

## Validation (`maps/yulehaven_isles_v1/validation.json` has every number)

| check | result |
|---|---|
| own reader / re-encode | identical, every surface voxel coloured, z 63 solid |
| pyspades 1.4.2 `generate()` | byte-identical; 0 / 20,000 solid and colour mismatches |
| floating components | 0 unintended (sky pieces listed as expected) |
| mirror | 0 solid / 0 material mismatches outside the one-off boxes |
| platform volume / ground under both ends | 0 voxels / both ends z 52, no water columns (red x 300–305 included) |
| spawn squares | all land, z 47–48, no roofs, mirror-equal |
| safe descent, enemy spawn, flank routes | all pass (graph model) |
| trap cells | 0 |
| interiors | 60 / 60 rooms and floors reachable, each with a way out |
| platform on foot | no (42 blocks to build) |
| anchors | no walk-on steps on the enemy face |
| front dressing | pass: 9 objects on 10 % of the front, all ≤ 10 tall, every 8-column section ≥ 84 % free |
| spawn cover | pass: 59 % on the enemy side within 20, 60 % rear backdrop |
| under the platform | pass: anchor ends flat (range 0) and prop-free; the strip is 43 % land (sea channel), so its coverage part is n.a.; ship tops ≥ 25 below the platform |
| centre footprint | pass: median object footprint 36 cells (74 objects) |
| **spawn exposure** | **WAIVED** `[USER 2026-11-15]`: Blue 9.97 viewers per spot, 0.5 % hidden; Red 9.62, 1.1 % hidden (targets ≤ 10 and ≥ 15 %); measured fail, reported as waived |
| wading (yh_checks) | spawn → islet 6 water cells, → enemy spawn 3, → islet sea cave 6; no dry route from island to islet or enemy island; the passage roof is not a dry crossing |
| determinism | same `veg_seed` (3401930456) → same SHA-256 in a fresh process (`e4d2e7cd…b645a9`) |
| live server | loads; Babel on; platform 3,200 cells; extensions and fog read; spawns on the stock squares |

### Spawn exposure trade-off (waived by the owner, 2026-11-15)

From the platform's west edge the spawn squares are 68–108 voxels away and 47 voxels lower, about a 30–35° view
down. Cover only hides a spawn spot if it stands in the front corridor right next to the square and is about
20 tall. The front rules cap front objects at 10 tall and keep every section at least 50 % free. A 3-high crest and
two 9-tall fish sheds keep viewers per spot at or under 10, but hide only 0.5–1.1 % of spots. Spawn cover outside the
front (cabins, boulders, spruce) passes its own rule but can't block a line of sight from the platform. The options were:

1. **Accept it** (Elderveil's waiver was the same trade-off). **Chosen by the owner on 2026-11-15.** Declared in
   `yh_spec.py` `waivers` and `build.json`; `validation.json` reports both rows as `waived` with the measured numbers.
2. Add a tall, walk-through arch at each village edge, like Frostbell Hollow's gate. That gate hid 58 % of spawn
   spots with a solid band at z 28–40.
3. Lower the spawn squares into a dell behind a taller natural ridge. That changes the "open front" feel.

## Known limits

* **Spawn exposure is waived, not met.** Almost every spawn spot can be seen from the platform; expect some
  spawn camping from the platform's ends.
* Client FPS and the 2.1 MB `.txt` are untested in a client.
* The north chain needs a 3-cell wade to reach its middle skerry; the south chain is dry (y-mirror rounding at a pier
  landing). Both chains have the same length and cover.
* The Yule goat reads well from the side; from above it's a straw blob.
* Snow covers about 21 % of terrain tops (patchy), 4,310 roof voxels; whites capped at 212.

## Regenerate

```bash
python scenes/yulehaven_isles/yh_main.py maps/yulehaven_isles_v1 3401930456
python -m aosmap.kit.probe maps/yulehaven_isles_v1 --mode babel --out maps/yulehaven_isles_v1/probe.json
python scenes/yulehaven_isles/yh_render.py maps/yulehaven_isles_v1
```

`--graybox` builds the gameplay-only reference; leave out the seed for a fresh OS seed (owner rule: vegetation is
non-deterministic, and the seed is saved in `build.json`).
Server test config: game mode `piqueserver.game_modes.babel`, scripts `piqueserver.scripts.map_extensions` (needed for
water damage) and `piqueserver.scripts.babel_script`, plus the normal list.
