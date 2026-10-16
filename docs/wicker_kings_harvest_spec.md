# The Wicker King's Harvest — Halloween island Babel (v1.0 + v1.1 sky layer, 2026-10-16)

An original pumpkin-island Tower of Babel map built from your top-down mockup brief: the whole island is a carved
jack-o'-lantern seen from above — scalloped orange rim lobes, two triangular eye pits, a stepped nose basin and an
interlocking-tooth grin trench — with a ritual clearing under the script platform, a farm hamlet on each cheek, a
giant woven Wicker King on the forehead and a curling stem in the north notch. Gameplay geometry is mirrored
`x' = 512 − x`; only the stem is a deliberate cosmetic asymmetry.

**Status:** specified · generated · exported · parser-validated (own reader + pyspades 1.4.2) · server-loaded
(piqueserver 1.4.2, `game_modes.babel` + `babel_script` + `map_extensions`) · **not** client-inspected
(BetterSpades / OpenSpades / your aos_web) · **not** playtested. Renders are numpy previews, not a game client.

## Mode integration (stock piqueserver 1.4.2, read in installed source)
* `babel_script.py`: platform x 206–305, y 240–271 at z 1, colour (0,255,255); bases (118,256)/(394,256);
  spawns random in ±20 at the topmost voxel; `ALWAYS_ENABLED = True`, else `extensions['babel']` decides —
  the `.txt` sets `'babel': True` so it also works on servers that turned ALWAYS_ENABLED off.
* No spawn/entity hooks in the `.txt` (your rule): the mode defaults place everything.
* `water_damage: 0`; fog `(176, 160, 186)` (lilac dusk, brightness ~174, hue absent from the orange/olive
  palette, neutral between blue and red).

## Layout (west half; east is the mirror)
| element | where | notes |
|---|---|---|
| plateau (face) | z 44 | flat over spawn yard, fronts, clearing, platform corridor |
| rim lobes | 14 lobes, crowns z ~31–35 | pumpkin skin over rock; grooves drop to plateau level and to the coast notches |
| rocky shelf + cliffs | coast ring z 54–61 | orange skin to z ~50, grey strata below, wet rock at the waterline |
| spawn yard (blue) | stock square x 98–138, y 236–276, z 44 | packed earth, straw litter, cart ruts; only 2-high bales and a 1-high trough inside; dry-stone wall 2 high **outside** the square with N/S/W gates and a 22-wide east gate |
| gate oaks + silos | oaks (148,241)/(148,271), silos (150,227)/(150,285) | frame the east gate; canopies start 9 above ground (walk under), none overhang the spawn square; they are the spawn's cover from the platform |
| barn | x 84–114, y 192–214 | gambrel roof, cupola, open doors (south), hay loft; east barn is weathered grey |
| farmhouse, sheds, wind pump | (84–98, 288–302), (156–163, 211–218), (85–92, 308–314), wind pump (106,290) | lit windows, porch lamp |
| fields | (100–130,146–184), (96–128,322–352), (214–246,142–172), (174–232,410–432), (196–232,306–326) | fenced, furrowed, pumpkins, a scarecrow in each |
| eyes | triangles (138,207)–(224,207)–(183,116) | terraced 2/5/7/9 deep, floor z 53, two stair ramps each, broken walkway at z 48, timber shoring with amber lamps, ember fissures |
| nose | (237,318)–(275,318)–(256,283) | 1-voxel stepped basin to z 50, plank bridge E–W at plateau level |
| grin | corners (132/380, 294), lips sag 46/100 | floor z 53, rising to plateau at the corners; 3 upper + 2 lower interlocking teeth (plateau promontories), plank bridges at x 186/256/326, stairs from both lips, floor boardwalk + lanterns |
| ritual clearing | r 48 at (256,256) | packed earth rings, 12 standing stones (r 34, 4–6 high), fire pit, stakes, bales, pumpkins |
| Wicker King | plinth (256,122), top z ~0 | woven legs/torso/head, arms spanning x ~220–292, ember eyes, hanging lanterns, twig crown, standing-stone ring |
| stem | base (230,88) | ribbed stalk rising ~31 then hooking west; vines and tendrils; placed after mirroring |
| piers | grooves k = 8, 10, 12 (+7 south on the axis) | plank piers at the water line with posts and lamps, rowboats, stair cut up the groove to the plateau |
| sea | z 63 painted | deep blue-black, teal shallows, foam line, faint moon glint NE, rock islets with jack-o'-lanterns |
| corner tag | sea floor x 10–158, y 494–501 | "THE WICKER KING'S HARVEST" only |

## Validation (`validation.json` in the map folder)
| check | result |
|---|---|
| own reader round trip | re-encode identical, every surface voxel coloured, z 63 solid |
| pyspades 1.4.2 `generate()` | byte-identical; 0/20 000 solid and colour mismatches; `get_z` at both bases 44 |
| floating components | 0 (20 stray leaf/twig voxels are removed by the build's cleanup pass) |
| mirror | 0 solid / 0 material mismatches outside the stem's cosmetic box (x 208–257, y 70–131 and its mirror) |
| platform clearance | 0 voxels at z 0–2 over the platform or its 1-voxel margin |
| ground under platform ends | blue x 206–211 and red x 300–305: all z 44, solid to the bottom |
| spawn squares | 1653/1681 cells at z 44, 28 on bales/trough (z 42–43), 0 water, mirror-equal |
| routes (preliminary graph) | spawn → own platform end 68 (blue) / 69 (red; stock platform centred on 255.5); spawn → enemy spawn 236; → Wicker King 218 both |
| traps | 0 standable cells between z 44 and 61 that cannot walk back to the plateau |
| water exit | 100 % of sea cells can walk back up (shelf → pier stairs) |
| build gap | highest walkable point within 24 of the platform z 41 → 39 blocks to reach platform level; platform not reachable on foot |
| spawn exposure (platform edge → spawn heads) | blue 7.4 viewers/spot, 18.8 % hidden; red 6.8, 19.7 % (targets ≤ 10, ≥ 15 %) |
| live server | loads, babel on, cap_limit 1, platform 3 200 cells, fog + extensions read, 400 sampled spawns per team: z 44 (a few on bales), intel (256,256,1) |
| determinism | same SHA-256 `6d7f8064…` in the cloud build (Python 3.11, numpy 2.x) and on your PC's Linux VM (Python 3.10, numpy 2.2.6, scipy 1.15.3) |

## v1.1 — floating sky layer (opt-in, `--sky`)
v1.1 is v1 plus 16 intentional floating pieces (1 280 voxels), placed last (after mirroring and cleanup) by
`wkh_sky.py`. Map files: `maps/wicker_kings_harvest_v1_1/` (same file names, `.txt` version '1.1'); v1 stays in
`maps/wicker_kings_harvest_v1/`.

| piece | where | notes |
|---|---|---|
| crows ×9 | ring r 28–36 around (256,118), z 4–11, circling counter-clockwise | 13-wide seen-from-below silhouettes, raised wing tips, bone beak |
| bats ×6 | around the stem's hook, (192–240, 46–84), z 6–19 | 15-wide scalloped wings, ember eyes |
| crescent moon | (318,70) over the NE sea, z 1–31, R 15, 2 thick | faces the island centre; pale with darker maria |

Placement rules, checked in `validation.json → sky_layer`: ≥ 89 from the platform (rule ≥ 60), nothing over either
spawn square, ≥ 10 air below every piece (rule ≥ 8), each piece placed with 2 voxels of clearance so none touches
the map (all 16 report as separate floating components; 0 unexpected floating). Mirror check excludes the pieces
(cosmetic). Everything else is unchanged from v1 (routes, traps, exposure 18.8 / 19.7 % hidden).

What testing showed (approximate fog preview, not a client): crows and bats read clearly through the lilac fog,
crows even from the clearing's edge; 5-wide birds were invisible and were enlarged. The moon only reads from the
NE lobes (~65 away) — AoS fog (~128) and the 64-voxel ceiling stop a sky backdrop from carrying across the map;
placed behind the Wicker King it was hidden entirely, so it sits off the NE coast as a lookout easter egg.

Caveat: a player can drop a piece for the round by building against it and breaking that block (pyspades collapse
check; protection scripts don't prevent it). A map reload restores it.

Live server (v1.1): loads, babel on, platform 3 200 cells, fog/extensions read, spawns z 44 (a few on bales).
SHA-256 `3074e0d9…`, identical in the cloud build and on your PC.

## Known limits / open points
* Not seen in a real client yet. Check in aos_web / BetterSpades: the lobes' orange against the lilac fog, the
  eye/grin readability at distance, and whether the moon-glint sea paint shows in your client's water.
* Rim-lobe outer edges are 20+ voxel cliffs onto the rocky shelf — lethal by design at the map edge; pier stairs
  are the way back from the sea.
* Spawn cover comes from the gate oaks + silos at the yard's east gate (front stays open, 22 wide). If players
  dislike them, removing the oaks drops hidden spawn spots to ~0 %.
* Babel anti-grief corridor (no building near the enemy tower) is stock; nothing on the map works around it.
* Jump/fall/route numbers are a graph model, not a collision sim.
* Next: client look, fog check with `/fog`, playtest.

## Regenerate
`scenes/wicker_kings_harvest/` (numpy, scipy, pillow; pyspades optional for `--pyspades`):
```
python wkh_main.py ../../maps/wicker_kings_harvest_v1      # VXL + TXT + build.json (+ mat.npy, git-ignored)
python wkh_main.py ../../maps/wicker_kings_harvest_v1_1 --sky   # v1.1 with the floating sky layer
python wkh_check.py ../../maps/wicker_kings_harvest_v1 --exposure [--pyspades]
python wkh_render.py ../../maps/wicker_kings_harvest_v1    # preview renders
```
Seed 1031; layout numbers in `wkh_terrain.SPEC` and the top of `wkh_build.py`; colours in `wkh_color.C`.
Server probe used for the live check: `server_test/wkh_babel/` (`scripts/wkh_probe.py` writes `probe.json`).
