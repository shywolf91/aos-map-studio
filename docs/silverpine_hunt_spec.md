# Silverpine Hunt: Halloween snow-forest Tower of Babel (v1.0 + v1.1 sky layer, 2026-10-30)

Silverpine Hunt is an original full-map Babel (512 × 512, not an island). A moonlit snow basin is ringed by
terraced slate mountains. Each spawn has a hunters' lodge, and the werewolf den sits under the script platform as a
cave-and-ruin complex. Landmarks are spread across the whole map rather than packed together:

* a frozen waterfall, an ice cave and a frozen lake to the north;
* a silver-mine massif with a flank tunnel to the south;
* a trapper camp, a rune circle, a trap line and a ruined moon-chapel with its graveyard in the four quadrants.

Gameplay geometry is mirrored `x' = 512 − x`. The only cosmetic asymmetry is the corner tag.

**Status:**
* Reached: specified · generated · exported · parser-validated (own reader + pyspades 1.4.2) · server-loaded
  (piqueserver 1.4.2, `game_modes.babel` + `babel_script` + `map_extensions`).
* Not reached: client-inspected (BetterSpades / OpenSpades / aos_web) · playtested.
* Renders are numpy previews, not a game client.

## Brief → decisions
| brief item | decision |
|---|---|
| full map or island | `[USER]` full 512 basin (mountain ring like 1mirror2forts, cliffs for the falls/mine) |
| "players hate too-white maps" | snow is 27 % of the top-down view; it sits mostly on ledges and clearings. Snow is shaded blue-grey/lilac with a max channel of ~210. Forest floors are rust needles and moss, open ground mixes winter grass, earth and slush. Top-down mean luma is 115, and only 10 % of pixels have luma > 175 (`build.json → ground_stats`). |
| Halloween / spooky | werewolf, wolf-skull gate, gnawed bones and blood snow, trophy tree hung with cages, coats and antler skulls, jack-o'-lanterns at the lodges, a jack-o'-lantern snowman, candles, rune stones, graveyard, purple wolfsbane, red ember eyes in the den |
| spread out, centre AND skirts detailed | centre: den, crag + werewolf, skull gate, ruined keep corners, kill site, trophy knoll, mine yard. Skirts: lake + falls + ice cave, trapper camp, rune circle, trap line, chapel + graveyard, mine portals, mountain forest |
| spawns not 100 % flat but easy | 41×41 square on gentle 1-voxel mounds (z 46/47) with no pits; only props ≤ 2 high inside the square (fire ring, low sled, crate, 1-high woodpile, small pumpkins) |
| little between spawn and tower zone | the front (x 138–212, y 234–278) is open snow with a trodden lane. A log gateway with a 37-wide opening and its beam 12 up stands at x 142. Six walk-under silver pines flank the front with crowns 10+ up. |
| like Wicker King's Harvest | same validation suite, the same no-spawn-hook policy, the same opt-in sky layer pattern |
| Q2 fog | `[DESIGN]` dusky lilac `(170, 160, 190)` (brightness ~173, a hue the palette doesn't use, between blue and red), plus `heavens_color (96, 102, 156, 255)` |
| Q3 lake | `[DESIGN]` walkable frozen ice (z 50, 4 below the basin) with black-ice patches and natural crack lines. No water damage anywhere (`water_damage 0`); z 63 is never exposed. |
| Q4 sky layer | `[USER]` yes, as v1.1 |
| Q5 den | `[USER]` a werewolf plus bones, nest and claw marks |

## Layout (west half; east is the mirror)
| element | where | notes |
|---|---|---|
| basin floor | z 46 (rolling ±1.6) | PZ; tower corridor, anchors and den floor exactly z 46 |
| mountain ring | edges, z ~6–43 | 4–6 high strata with wandering edges; ledge snow / gravel / rock; spruce on ledges; four rocky spurs |
| spawn square (blue) | x 98–138, y 236–276 | z 46/47 mounds; stock ±20 spawn rule |
| hunters' lodge | x 92–130, y 196–224 | 2 floors, log courses with notched corners, porch with lanterns and pumpkins; doors S×2, W, E; partition; stair to the upper floor; fireplace and chimney; furnished; candle windows; antlers |
| watchtower | x 72–78, y 253–259 | 16-high interior square spiral stair, railed lookout, pyramid roof, lantern |
| smokehouse, kennel, woodshed | (96–106, 288–297), (112–124, 290–298), (128–135, 289–297) | hanging meat and pelts; straw stalls; firewood |
| log gateway | x 142, y 236–276 | wolf skull + antlers, team banners (blue / red), lanterns |
| cover pines | (150,226) (149,284) (164,218) (163,294) (180,226) (179,287) | 25–30 high silver pines that you walk under |
| trapper camp (NW) | ~(118, 112) on a knoll | tent, campfire, drying racks, cage, sled, shed, stacked traps, hunters' blind with a stair |
| frozen creek + pond | lake outlet → (92, 170) pond → west mountains | 2-deep ice bed, 1-step banks |
| rune circle | (176, 164) knoll | 7 carved stones with silver crescents, altar with a blood bowl, candles |
| trap line | ~(168, 342) | 8 bear traps, snares, overturned wagon, blind, elk carcass, wolfsbane |
| moon-chapel + graveyard (SW) | chapel x 90–116, y 362–378 on a knoll; yard x 120–154 | apse, altar with silver crescent, broken pews, half-fallen roof, breach, NE bell tower with a stair; headstones, crosses, an open dug-up grave |
| frozen lake | centre (256, 94), r 68 × 40 | ice shack (enterable), fishing holes, broken sled |
| frozen waterfall | x 236–276 on the north cliff | column-sculpted ice curtain, frozen brow with icicles, plunge mound |
| ice cave | behind the falls, entrance at the west foot (x ~228–234) | domed chamber with glowing crystals, silver ore and a frozen hunter |
| kill site | (256, 140) | elk ribcage + antler skull, blood snow, broken sled, bones |
| crag + werewolf | crag (256, 200) r 30 × 16, top z 41 | werewolf ~35 tall, arms raised, snarling toward the platform; red eyes, chest blaze, mane spikes, claws; tail to the ground |
| den floor (under the platform) | x 212–300 | open earth and needles, bones, barricades, skull stakes; ruined keep corners at (214–236, 212–230) and (214–238, 282–300), 5–9 high with arches and doorways |
| nest pit + nest hall | pit r 7 at (256, 256); hall r 32 × 21, floor z 56 | twin stair down the pit; straw / pelt nest, bones, a gnawed hunter, ember eyes in side alcoves, claw / blood marks |
| den passages | north: under the crag → exit at y ~176; south: up into the skull | both are 9–11 wide ramps |
| wolf-skull gate | cranium (256, 304), mouth opens south at y ~334 | hollow, eye sockets with ember eyes, fangs, lower jaw on the ground (1-high chin), ramp down to the den |
| trophy tree | (256, 370) knoll | giant dead oak, 8 limbs, cages / coats + hats / lanterns / antler skulls / pelts, crows, bones, candles |
| mine massif | superellipse (256, 452) r 92 × 56 | 4-high strata, 7-high rim step |
| silver-mine tunnel | y 412–420, floor z 46, air z 41–45 | shoring every 6, lanterns, rails, ore chamber (x 198–212), portals at x ~181 / 331 with carts and a spoil heap |
| mine yard + headframe | x 234–278, y 388–412 | 22-high pithead with a sheave wheel over a capped shaft, hoist houses, ore carts, ore piles |
| corner tag | SW mountain shelf x 8–102, y 492–503 | "SILVERPINE HUNT" only |

Forest: 630 trees, all non-uniform. Each tree has its own height, girth, tier rhythm, edge jag and a two-palette blend
from 8 foliage palettes, plus 3 random details (snow caps, icicles, lanterns, ribbons, claw marks, nests, cones, dead
branches, rust, charms, frost, moss).

| type | count |
|---|---|
| spruce | 206 |
| silver (Scots) pine | 60 |
| snag | 152 |
| sapling | 212 |

Scatter (west half before mirroring): 90 boulders, 22 fallen logs, 26 stumps, 28 bear traps, 29 bone piles, 26
wolfsbane patches, 39 saplings, 11 lantern posts.

## Validation (`validation.json` in each map folder)
| check | v1.0 | v1.1 |
|---|---|---|
| own reader round trip | re-encode identical, every surface voxel coloured | same |
| pyspades 1.4.2 `generate()` | byte-identical; 0/20 000 solid and 0 colour mismatches; `get_z` at bases 46 / 46 | same |
| floating components | 0 | 0 unexpected; 19 expected sky pieces |
| mirror | 0 solid / 0 material mismatches outside the tag box | same (sky pieces excluded) |
| platform clearance | 0 voxels at z 0–2 over the platform or its margin | same |
| ground under platform ends | blue x 206–211 and red x 300–305 all z 46, solid to the bottom | same |
| spawn squares | 1611 / 1681 cells at z 46–47, 70 on low props (z 44–45), 0 water, mirror-equal | same |
| routes (graph) | spawn → own platform end 68 (blue) / 69 (red); → enemy spawn 236; → mine tunnel 148; → nest hall 92; → kill site 175 | same |
| traps | 0 standable cells between z 45 and 61 that can't walk back | same |
| exits | lake ice, cave floor and creek: 100 % can walk back to the basin | same |
| build gap | highest walkable within 24 of the platform: z 43 → 41 blocks to build; platform not reachable on foot | same |
| spawn exposure (platform edge → heads) | blue 6.9 viewers / spot, 21.8 % hidden; red 6.6, 18.4 % (targets ≤ 10, ≥ 15 %) | same |
| sky rules | n/a | min 69 from the platform (rule ≥ 60), none over a spawn, min air below 9 (rule ≥ 8) |
| live server | loads, babel on, cap_limit 1, platform 3 200 cells, fog + extensions (incl. heavens_color) read, 400 sampled spawns per team at z 44–47, intel (256, 256, 1) | same |
| determinism | v1 SHA-256 `b3123d6c…` identical in a fresh process (Python 3.11, numpy 2.4.6) | `8833384f…` |
| file size | 3.44 MB | 3.45 MB |

## v1.1 sky layer (opt-in, `--sky`)
| piece | where | notes |
|---|---|---|
| full moon | (242–270, 82–83), z 1–29 over the lake | craters, pale rim; frames the falls from the lake shore |
| crows ×8 | ring r 20–26 round the kill site (256, 142), z 20–25 | 13-wide silhouettes |
| bats ×6 | ring round the trophy tree (256, 370), z 14–19 | 17-wide wings, ember eyes |
| bats ×4 | over the mine yard | — |

Caveat (pyspades collapse check): building a block against a sky piece and then breaking it drops that piece for
the round. A map reload restores it.

Fog note: in the preview the moon shows behind the werewolf from the platform, but in game the fog (~128 voxels)
hides it from there. It reads from the lake shore and the kill site, which are 35–65 voxels away.

## Known limits / open points
* Not yet seen in a real client. Check in aos_web / BetterSpades:
  * the lilac fog against blue-grey snow;
  * whether the snow share still reads as "too white" to players;
  * the werewolf silhouette at 60–100 voxels;
  * lake crack lines;
  * dark den interiors (cave rock luma ~65).
* Den destroy rule (stock): standing in x 224–288 nobody can destroy blocks. Towers built from the den floor are as
  hard to clear as any centre build on stock Babel maps.
* The nest pit is open to the sky under the platform. A player who drops into it falls 10 to the nest floor, and the
  twin stair leads back up.
* Mountain cliffs are the boundary. Climbing them needs building, and falls from the upper strata are lethal by design.
* Route, jump and fall numbers come from a graph model, not a collision simulation.
* The mine tunnel and the den passages are 9–11 wide, wide enough that one player can't seal them easily. They can
  still be blocked with team blocks (the usual Babel griefing caveat).
* Next: client look, `/fog` tuning, playtest at representative player counts, FPS check in the dense forest.

## Regenerate
`scenes/silverpine_hunt/` needs numpy, scipy and pillow; pyspades is optional for `--pyspades`.
```
python sph_main.py ../../maps/silverpine_hunt_v1          # VXL + TXT + build.json (+ mat.npy)
python sph_main.py ../../maps/silverpine_hunt_v1_1 --sky  # v1.1 with the floating sky layer
python sph_check.py ../../maps/silverpine_hunt_v1 --pyspades --exposure
python sph_render.py ../../maps/silverpine_hunt_v1        # preview renders
```
* Seed: 1030.
* Layout numbers live in `sph_terrain.SPEC` and the top of `sph_build.py`; colours in `sph_color.C` / `FOL`.
* Modules:
  * `sph_terrain.py` heightfield
  * `sph_props.py` materials and small props
  * `sph_trees.py` vegetation
  * `sph_structs.py` buildings
  * `sph_landmarks.py` werewolf, skull, den, trophy tree, falls
  * `sph_sky.py`
* Server probe: `server_test/sph_babel/`. Copy the `.vxl`/`.txt` into `server_test/sph_babel/maps/`, then run
  `piqueserver -d server_test/sph_babel`, which writes `probe.json`.
