# Cursed Skull Reef — spec (v1.0)

**Status: server-loaded** (2026-11-16). The map loaded on a live piqueserver 1.4.2 in Babel mode via `aosmap.kit.probe`:
platform 3,200 cells, `babel` + `water_damage 1` + glow keys read, fog read, 400 sampled spawns per team on the stock
squares at z 47–48, intel at (256, 256, 1). **Not client-inspected and not playtested.** The renders in
`maps/cursed_skull_reef_v1/renders/` are numpy previews, not client captures.

**Babel, assist structures** (AGENTS.md §4 custom variant, knowledge base §8.8), island Babel in the **current**
(dense, authored) island style. A bright moonlit storm night over a cursed pirate reef. Two mirrored harbour isles are
joined by a shoal neck under the platform. A half-sunk galleon and a cannon fort sit in the north lagoon, and a
skull-shaped crag with a sea cave sits in the south lagoon, where a maelstrom is painted on the sea. Beached mast
wrecks next to each platform end are the assist structures. Original designs only: no film names, logos, characters
or copied landmarks.

Generator: `scenes/cursed_skull_reef/` (built with `aosmap.kit`). Branch: `ccr-e22e20a5-bpypq9`. The session
harness required this branch, so it replaces the usual `map/cursed-skull-reef`.

## Owner answers `[USER 2026-11-15]`

| question | answer |
|---|---|
| island style | current (dense, authored, like Yulehaven Isles); not classic; build only this one |
| concept | a mix of "Skull Cove Archipelago" and "Shipwreck Graveyard" → Babel with assist structures |
| mood | moonlit night + cursed stormy sea: a *bright* moonlit storm night |
| water | `water_damage` 1 (as Yulehaven), so the flanks run over islets, not through the sea |
| extras | glow blocks, floating sky decor; no underground layer; ground solid to the bottom |

### Defaults chosen where the brief was silent `[DESIGN]`

* **Assist structures:** a mirrored pair (one per team) next to each platform end, instead of one central
  structure. This gives equal access by mirror, and the tower corridors stay free for normal building.
* **Assist gap:** 5 blocks up plus about 5 across, a "short build". Elderveil used 10. Tune it after a playtest
  (knowledge base §8.8: a tiny gap can end rounds too fast).
* **Neck:** a dry sand shoal at z 61 (z 62 lip). Standing on it does no water damage: the server checks the player's
  position z ≥ 61, and a player standing on a z 61 block is at about z 59 `[SRC]` piqueserver
  `scripts/map_extensions.py`.
* **Fog** `(156, 184, 170)`: a pale ghost-jade. Green is neutral between Blue and Red, and the palette (sand,
  timber, bone, olive palms, blue-teal sea, warm lamps) does not use it. Min channel 156.
* **No `heavens_color`:** the owner didn't ask for it.
* **Corner tag** "CURSED SKULL REEF": painted on a low sandbar in the SW corner, on the ground (owner rule: map name
  only).
* **One-off balance by role:** each team gets one tall shore landmark (Blue: ruined tavern on stilts; Red: lighthouse
  stump) and one landmark on its first south-chain islet (Blue: rum-barrel dock; Red: gallows).

## Layout

Mirror `x' = 512 − x` (`x512`, column 255 copied into 256). Coordinates are the west (Blue) half and the axis.
z = 0 is the sky. A "floor z" is the solid voxel a player stands on. Every number lives in
`scenes/cursed_skull_reef/csr_spec.py` (`SPEC`).

### Elevations

| area | floor z |
|---|---|
| spawn square (stock 98–138 × 236–276) | 48, gentle mounds to 47; driftwood boardwalk patches painted on the sand |
| front crest x 148–153 | 45 (3 above the spawn floor), then down to the anchor |
| tower anchor ground x 200–212, y 236–276 | 52 flat, solid to the bottom; sheer 9–10 voxel enemy face onto the neck; no stairs |
| isle plateau / town | 48 ± relief; rear ridge x 50–84 rises up to ~8 above the plateau (spawn backdrop) |
| beaches | 62 lip → 60, then rising to the plateau |
| shoal neck x 213–299, y 238–274 (+ shoulders y 226–237 / 275–286) | 61 (dunes 60, lip 62) |
| fort islet / skull islet | plateau 52 / 54 |
| flank skerries | peaks 51–55 |

### Zones (west half; the east half is the mirror unless marked as a one-off)

| zone | where | notes |
|---|---|---|
| harbour spawn isle | x 30–214, y 140–372 | pirate town of 9 real houses (1–2 storeys; 3 with a broken roof or corner), west harbour with 2 lamp-lit piers and moored rowboats, rope-and-post fence behind the spawn, 2 treasure-chest alcoves in rock outcrops |
| front (dressed, open) | x 139–211, y 236–276 | 2 walk-through fisher huts (9 tall), upturned rowboat, crate stacks, barrel cluster, cannon on its carriage, log pile, ship's anchor, lobster-pot stacks |
| shoal neck under the platform | x 212–300, y 240–271 | hull ribs of an old wreck (axis, walk-through), capsized longboat, big anchor, coral heads, fallen mast and yard, barrels, cannon, sea chests with coins |
| assist mast wreck | x 213–229, y 204–236, beached on the neck shoulder | broken-off galleon stern: hold, gun deck with cannons, main deck, quarterdeck over a captain's cabin; breaches into the hold from the neck sand and the isle shore; a spiral rope-and-plank stair round the mizzen mast up to a crow's-nest ring at z 8 |
| half-sunk galleon (axis) | x 246–266, y 158–226 | bow sunk awash at the fort islet, stern raised on a reef bar that joins the neck; sloped decks (1 in ~4.5); hold, gun deck with ports and cannons, quarterdeck over the captain's cabin, broken masts with torn sails; entry through a breach in the transom |
| cannon fort (axis) | x 230–282, y 122–156 on the fort islet | 3-thick curtain walls with a rampart walk and embrasures, south gate, SW/SE bastion towers (2 storeys + gun roof), north wing (magazine + 2-storey barracks), courtyard stair to the rampart, well, flagstaff with a black flag, cannons |
| skull crag (axis) | x 226–286, y 316–376 on the skull islet | cranium top z 10; jaw over a sea cave (pool fed by the lagoon, rock ledges, teeth, treasure alcove with glowing coins); a stair tunnel inside the skull up to two eye-socket rooms that look north at the platform (green glow) |
| bridge ruin (axis) | x 254–258, y 275–339 | rope-and-plank bridge from the neck over the maelstrom into the skull's jaw; sagging broken middle with rails gone (centre line walkable) |
| lagoon links | — | rope bridges from the isle to the fort islet and to the skull islet; axis piers from the fort islet north to the north chain and from the skull islet south to the south chain |
| north flank chain | y 63–127 | pier → N1 → rope bridge → N2 → broken pier → N3 → rope bridge → M (axis); moored brig at N1 (hold, cabin, two masts, gangway) |
| south flank chain | y 384–448 | y-mirror of the north chain |

### One-offs (placed after the mirror; cosmetic boxes in `build.json`)

| object | where | notes |
|---|---|---|
| ruined tavern on stilts | Blue NW shore (40, 156) | 2 storeys on stilts over the water, broken corner, outside stair, boardwalk, hanging sign, lamps |
| lighthouse stump | Red NE shore (472, 156) | round stone tower, broken crown, spiral stair to a lamp deck at z 30 with a brazier (glow) |
| rum-barrel dock | Blue S1 islet (124, 399) | dock warehouse, jetty with lamp posts, barrel pyramids, jib crane with a barrel net |
| gallows | Red S1 islet (388, 399) | scaffold with a stair, trap door, crossbeam with nooses, crow cage, green lamp |
| heeled-over brig | beside the north chain's middle islet (256, 58) | brig lying on its side (68°), plank floor inside, two hatches with rubble steps from the beach, mainmast lying across the islet |
| corner tag | SW sandbar x 4–116, y 486–508 | "CURSED SKULL REEF" painted on the sand |

### Vegetation (art pass; non-deterministic by owner rule)

49 plants in 20 groves (west half, mirrored): 32 leaning coconut palms, 13 gnarled dead trees and 4 mangroves on
stilt roots. Each plant has three random details (coconuts, dead fronds, hanging rope, lanterns, nests, moss, vines,
roots, mushrooms, crow cages and others), with two-colour gradients from the base to the tips. The seed is
`veg_seed` in `build.json` (this build: 213280709). Plants stay off the spawn squares, the front band, the anchors,
the neck and the doors. 2 frond voxels that overhung the spawn square were cleared.

### Sky decor (opt-in, asked for)

13 floating pieces, all listed in `build.json` → `sky_objects`:

* a ghost galleon silhouette (950 voxels, NW sea);
* a crescent moon (south edge);
* 6 storm clouds;
* 5 bats over the south chain.

Each piece is at least 125 voxels from the platform (rule: 60), none is over a spawn square, and each has at least
25 voxels of air below it (rule: 8). **Collapse caveat:** if a player builds a block against a sky piece and that
block is broken, the whole piece falls for the rest of the round.

### Glow (owner's glow format, knowledge base §11.4)

186 sources (12 of them on the one-offs), 23,453 lit voxels. They are:

* candles in a third of the windows;
* dock and pier lamp posts;
* ship lanterns (galleon, brig, wreck sterns);
* fort torches;
* green "cursed" lights: the skull's eye sockets, the crow's nests and the bridge ruin;
* yellow treasure glow in the skull cave and the alcoves;
* the tavern lamps, the lighthouse brazier, the rum-dock lamps, the gallows lamp and the heeled brig's lanterns.

Lit voxels are baked into the VXL, and `glow_stored_colors` holds the original colours. The `.txt` is 1.3 MB because
of the glow table.

### Metadata (`cursed_skull_reef.txt`)

* `fog = (156, 184, 170)`
* extensions: `babel: True`, `water_damage: 1`, `glow_enabled`, `glow_stored_colors`
* `author = 'shywolf91 + AI'`
* no spawn or entity hooks (owner rule)
* `check_txt`: ok. Water damage needs `piqueserver.scripts.map_extensions` in the server script list.

## Assist structures (Babel with assist structures) `[RUN]` graph model

| structure | top reachable z | blocks to platform level | horizontal gap to the platform | route from own spawn / enemy spawn (hops, dry) |
|---|---|---|---|---|
| west mast wreck (Blue side) | 7 (rail stubs on the crow's-nest ring; the ring is z 8) | 5 | 5 | 218 / 292 |
| east mast wreck (Red side) | 7 | 5 | 5 | 218 / 292 (mirror) |

* **Equal access:** the pair is mirrored. Both teams reach both wrecks dry, with no wading.
* **Contestable:** each wreck is open from the sand, the isle shore, the decks and the platform. The spiral stair is
  open to the air the whole way up.
* **The intel can't be reached on foot:** the platform is not reachable without building (`platform_on_foot` passes).
* **Keep-out:** the z 0–3 volume over the platform footprint is empty (0 voxels).
* **Relaxed check:** the standard build gap ("highest reachable near the platform") reads 5 for both teams because
  of the wrecks. This is the intended assist, not a defect. The normal tower route from the anchor ground is about
  51 blocks.

## Validation (`maps/cursed_skull_reef_v1/validation.json` has every number)

| check | result |
|---|---|
| own reader / re-encode | identical, every surface voxel coloured, z 63 solid |
| pyspades 1.4.2 `generate()` | byte-identical; 0 / 20,000 solid and colour mismatches |
| floating components | 0 unintended; 13 sky pieces listed as expected, all within the placement rules |
| mirror | 0 solid / 0 material mismatches outside the one-off boxes |
| platform volume / ground under both ends | 0 voxels / both ends z 52, no water columns |
| spawn squares | all land, z 47–48, no roofs, mirror-equal |
| safe descent | tower zone reached with drops ≤ 9; 100 % of ground reachable without damaging drops |
| enemy spawn / flank | reachable on foot; flank routes north (470) and south (456), both dry (0 water cells) |
| trap cells | 0 |
| interiors | 81 / 81 rooms and floors reachable, each with a way out |
| platform on foot | no (assist gap 5, see above) |
| anchors (real faces x 212 / 300) | raised 10, 0 walk-on rows on the enemy face, both teams |
| front dressing | pass: 11 objects on 10.4 % of the front, all ≤ 10 tall, worst 8-column section 81 % free |
| spawn cover | pass: 58 % on the enemy side within 20, 77 % rear backdrop |
| under the platform | pass: neck is 95 % land, objects on 15.2 % of the strip, ≥ 46 air below the platform, both anchor ends flat (range 0) and prop-free |
| centre footprint | pass: median object footprint 36 cells (68 objects) |
| **spawn exposure** | **FAIL (not waived)**: Blue 9.96 viewers per spot, 0.9 % hidden; Red 9.61 viewers, 1.1 % hidden (targets ≤ 10 and ≥ 15 %) |
| dry routes (`csr_checks`) | every target reachable with 0 water cells: enemy spawn, fort rampart, galleon quarterdeck, skull cave and eye rooms, both chain middles, both crow's nests |
| zone profile | class "island" (report only) |
| colour | top-surface luma median 75.9, 0 % dark tops, 1,485 whites capped at 212, 0 floors raised |
| determinism | same `veg_seed` (213280709) → same SHA-256 in a fresh process (`6e067f09…2917f4b`) |
| live server | loads; Babel on; platform 3,200 cells; extensions and fog read; spawns on the stock squares |

### Spawn exposure trade-off (for the owner's decision; not waived)

This is the same open-front trade-off as Yulehaven Isles and Elderveil. Both of those had it waived by the owner,
but no waiver exists for this map, so the row is reported as FAIL.

From the platform's ends, the spawn squares are 68–108 voxels away and about 47 voxels lower. Cover hides a spawn
spot only if it stands in the front corridor right next to the square and is about 20 tall. The front-dressing
rules cap front objects at 10 tall and keep every 8-column section at least 50 % free. Viewers per spot already meet
the target (≤ 10), but only about 1 % of spots are hidden. The options are:

1. **Accept it**, as was done for Yulehaven and Elderveil, and declare it in `SPEC['waivers']`.
2. **Add a tall walk-through gate at each town edge**, like Frostbell Hollow's arch (it hid 58 %). It would need to
   be listed as an owner-requested `front_exempt_box`.
3. **Sink the spawn squares into a dell behind a taller natural ridge.** This changes the open-front feel.

## Known limits

* **Spawn exposure fails on hidden share** (see above). Expect some spawn camping from the platform's ends.
* **The assist gap of 5 + 5 is a guess.** Rounds may end fast. Tune `assist.nest_z` after a playtest (a nest at z 10
  gives a gap of 8).
* **Art gaps:**
  * the heeled-over brig reads as a log from close up;
  * the assist wrecks are boxy broken-off sterns;
  * the ghost galleon is a 2-thick silhouette;
  * the skull reads best from the north (platform side).
* **Untested:** client FPS and the 1.3 MB `.txt` have not been tried in a client. The water-damage rate per second is
  set by the client and can't be measured with a bot.
* **No interiors test for the spiral stairs** (kit `spiral_stair`), apart from the crow's-nest and lighthouse
  interior points, which both pass.

## Regenerate

```bash
python scenes/cursed_skull_reef/csr_main.py maps/cursed_skull_reef_v1 213280709
python -m aosmap.kit.probe maps/cursed_skull_reef_v1 --mode babel --out maps/cursed_skull_reef_v1/probe.json
python scenes/cursed_skull_reef/csr_render.py maps/cursed_skull_reef_v1
```

* `--graybox` builds the gameplay-only reference.
* Leave out the seed for a fresh OS seed (owner rule: vegetation is non-deterministic, and the seed is saved in
  `build.json`).
* Server test config: game mode `piqueserver.game_modes.babel`, with scripts `piqueserver.scripts.map_extensions`
  (needed for water damage) and `piqueserver.scripts.babel_script`, plus the normal list.
