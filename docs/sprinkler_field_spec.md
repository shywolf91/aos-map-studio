# Sprinkler Field — spec (v1.0)

**Status: server-loaded** (2026-11-15). The map loaded on a live piqueserver 1.4.2 in Babel mode via
`aosmap.kit.probe`: platform 3,200 cells at z 1, `babel` + `water_damage 0` + `glow_enabled` read, fog read, intel at
(256, 256, 1), 400 sampled spawns per team on the stock squares at z 49–50. **Not client-inspected and not
playtested.** The renders in `maps/sprinkler_field_v1/renders/` are numpy previews, not client captures.

**Label: Babel, assist structures** (knowledge base §8.8). A lawn just after watering, seen by a person the size
of an ant. The scale idea comes from the game Grounded; no landmark, character or name is taken from it. Stock
Babel (`babel_script`), ground Babel, towers still built from the ground. Branch `map/sprinkler-field`, generator
`scenes/sprinkler_field/`, built with `aosmap.kit`. A different map from Backyard Babel (no toys, dollhouse,
sandcastle or fence).

## Owner answers `[USER 2026-11-15]`

| question | answer |
|---|---|
| relation to Backyard Babel v5.0 | a new, different map |
| playstyle | Babel with assist structures |
| setting | three concepts offered; picked **Sprinkler Field** |
| extras | glow blocks, underground layer, floating sky decor (no `heavens_color`) |

## Layout

West half is built and mirrored `x' = 512 − x` (column 255 copied into 256); axis objects and one-offs are placed
after the mirror. Soil floor z ~52, rolling 50–54, solid to the bottom except the ant nest. All numbers live in
`scenes/sprinkler_field/sf_spec.py` (`SPEC`, with every change from the first draft in `SPEC['deviations']`).

| zone | where (west / axis) | notes |
|---|---|---|
| spawns | stock (118, 256) / (394, 256) ± 20 | gentle mound, floor z 49–50, no props, no roofs |
| fronts | x 139–199, y 236–276 | open; 8 low objects (2–8 tall), soil crest 3 above the spawn floor at x 148–153 |
| anchors | x 200–212 / 300–312, y 236–276, z 52 | flat, solid to the bottom, no objects, no tunnels, no raised face |
| under the platform | x 212–300, y 240–271 | puddle, pebbles, low clover, bottle cap; ≥ 42 air to the platform |
| **assist 1: tripod sprinkler** | hub (256, 210), north of the platform | climb a stepped leg → collar deck → spiral round the body → head deck (z 9) → spray arm → T-bar landing x 240–272, y 235–237, z 6 |
| **assist 2: garden trowel** | axis, south of the platform | soil heap → blade rib → stepped handle → end cap at (256, 276), z 11 |
| garden hose | north flank, y ~116–132 across the whole map | walk-through pipe (outer radius 6); per half: two walk-under arches, a rut, a split section; top walkable; feeder hose down the axis to the sprinkler |
| south flank | mud trail y 384–396, brick edging y 404–412 | bricks 34 long with 9-wide gaps |
| ant nest | entrances A (112,168), B (218,172), C (112,344), D (218,338) + mirrors | tunnels 5 wide, floor z 60, 4 air; north and south chambers; queen chamber on the axis links both halves; glowing fungi |
| centre | x 81–431, y 150–362 | grass tussocks (blades 25–40 tall, 3×2 bases), clover canopies, dandelions, pebbles, mushrooms, acorns, twigs, curled leaves, bottle cap, pinecone; 7–10 voxel gaps |
| one-offs | periphery | brass spigot (W hose end), hose reel (E hose end), tipped flowerpot (SW), gardening glove (SE), snail shell (NE), plant label stake (NW), sneaker footprint and dropped valve key (S) — all enterable or climbable |
| corner tag | x 6–98, y 495–505, on the ground | `SPRINKLER FIELD` only |
| sky decor | 6 dandelion seeds, 2 dragonflies | expected floating; nearest is 126 from the platform, ≥ 12 air below, none over a spawn square |

`.txt`: author `'shywolf91 + AI'`, fog (206, 186, 216), extensions `babel`, `water_damage 0`, `glow_enabled`,
`glow_stored_colors`; no spawn hooks.

## Validation (release build: veg_seed 2977889799, SHA-256 4d0431ec…9f49, 2,660,792 bytes)

| check | result |
|---|---|
| reader / pyspades | re-encode identical; `generate()` identical, 0/20k mismatches |
| floating | 0 unintended; 8 expected sky pieces |
| mirror | 0 solid / 0 material mismatches outside the cosmetic boxes (one-offs, sprinkler spiral, sky, tag) |
| platform volume | 0 voxels; nothing at z ≤ 3 over the footprint ± 1 |
| ground under platform ends | z 52 both ends, flat |
| spawn squares | tops z 49–50, 0 water, 0 roof columns |
| routes | enemy spawn 236 / 236 steps; safe descent to the tower zone 30 / 31; 0 trap cells; flank north 490, south 456 |
| interiors | 20 / 20 reachable with a way out |
| **assist: sprinkler landing** | reachable by both teams, 242 steps each; **build gap 4** for both |
| **assist: trowel cap** | reachable by both teams, 215 steps each; **build gap 9** for both |
| hose | 4 crossings per half, top walkable (81 % of top cells reachable) |
| ant nest | all 8 entrances reachable, 100 % of floor cells have a way back, 0 tunnel air in the no-tunnel boxes |
| zone rules | front dressing, spawn cover, under-platform strip, centre footprint: all pass |
| **spawn exposure** | **FAIL, not waived:** blue 10.15 viewers per spot, red 10.0; 0 % hidden for both (targets ≤ 10, ≥ 15 %) |
| art vs graybox | 0 voxels removed outside the tag strip; reachable cells and every measured path length identical |
| colours | floor luma min 40.6; max channel 212; no team-like red or blue |
| glow | 195 sources (dew, fireflies, tunnel fungi, spigot drip, nozzle droplets) |
| determinism | fixed veg_seed gives the same SHA-256 in two fresh processes; graybox SHA 089e7ef0… |

Relaxed for the variant: "platform not reachable without building" is read as the per-structure build gap.
Route checks are a graph model, not proof of in-game playability.

## Open points

* **Spawn exposure vs open fronts — owner decision pending.** Measured alternative: two walk-under giant clovers
  (16 tall) on each front at x 146 give 3.24 viewers and 41.7 % hidden, but break "low dressing only on the front"
  and fail the front-dressing rule (87.5 % of objects ≤ 10 tall, needs 90 %). The sprinkler head deck is also a perch.
* Sprinkler gap 4 may end rounds quickly; tune by playtest.
* The queen chamber joins both halves underground: a symmetric bypass under the hose. Watch for abuse in playtests.
* The `.txt` is 1.4 MB because `glow_stored_colors` has about 23k entries. It loads on the server.
* Collapse caveat: sky decor is floating by design. A player block built against a piece and then broken drops it
  for the round. The authored structures are destructible; cutting a sprinkler leg or the trowel handle is
  possible counterplay and possible grief (untested).
* Art doubts to check in a client: snail-shell banding reads blotchy, dandelion globes are mottled, dragonflies are
  thin from eye level, tunnel brightness.
* Suspected kit bug (not fixed here): `tag.paint_tag(level=True)` leaves filled voxels with material 0 and stale
  colours; worked around in `sf_paint.retexture_tag_strip`.
* Client FPS untested.

## Regenerate

```bash
python scenes/sprinkler_field/sf_main.py out/sprinkler_field_v1 [veg_seed]     # no seed = new OS seed, saved in build.json
python scenes/sprinkler_field/sf_main.py out/sprinkler_field_graybox --graybox
python -m aosmap.kit.probe out/sprinkler_field_v1 --mode babel
python scenes/sprinkler_field/sf_render.py out/sprinkler_field_v1
```
Rebuild the released file exactly with veg_seed `2977889799`.
