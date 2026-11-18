# Tradeoff Christmas v1.0 — spec

Christmas retheme of **Tradeoff** by aloha.pk (community map; tower geometry is unchanged). Built 2026-11-18.

**Status ladder:** generated → exported → parser-validated (own reader + pyspades 1.4.2 `generate()` byte-identical,
`.txt` loads). **Not** server-loaded, **not** client-inspected, **not** playtested. Renders in `renders/` are numpy previews.

## Owner decisions `[USER]` (2026-11-18)
Retheme + new props (not a full `[recreate]`); keep blue/red team hues; extras: glow lights, floating sky decor, night mood
with `heavens_color`; same mode as the original (no mode keys, no spawn hooks); corner tag on the ground.

## Original map `[DERIVED]`
Flat floor (only z = 63 solid, one voxel) with two hollow 61-high towers (shell walls 3 thick, floor slabs every 8 z, roof at
z = 2, 6 roof holes each) in an interlocking C shape: blue upper-left, red lower-right, 180° rotation symmetric, plus a fan
of 6-high fins on each inner curve. 5 sealed air pockets of 21 708 voxels exist in the original. Mode and spawns are not in
the supplied file; none are set here.

## What changed
| area | change |
|---|---|
| Towers (geometry) | **None.** Only recoloured; the only added voxels in the tower footprint are 224 fairy-light bulbs at z = 1 on the roof edge |
| Tower outsides | wide diagonal candy bands (blue/lite blue, red/lite red) with a snow ledge on every floor line; roof edge = candy ring |
| Tower roofs | team-tinted snow (blue-grey / pink-grey), not white |
| Tower interiors | blue and red checker floors with cream, ice-stone / peppermint walls, pine-green accents, navy / burgundy darks |
| Floor | moonlit snow (max channel capped near 212), glassy ice patches with cracks; no near-black |
| Props on the floor | 210 pine trees (3 random details each: ornaments, snow, tinsel, lights, canes, berries; star on top), 26 snowmen, ~115 gifts, 40 candy-cane lamps, 28 snow boulders |
| One-offs | giant tree (40 high, lit, at 256,256), 2 gingerbread houses (door, windows, chimney, lit room), 2 igloos (tunnel door, lamp), 3 nutcrackers (14+ high), parked sleigh with 2 reindeer |
| Floating sky layer (opt-in) | flying sleigh + 4 reindeer, 6 snow-cloud islands (trees, gifts, hanging baubles), 8 snowflakes; all z 6–44 over the edge strips, none over the towers |
| Glow | 1260 glow sources, 72415 lit voxels baked; `glow_stored_colors` in the `.txt` (5 MB vxl) |
| Corner tag | "Tradeoff / Christmas" painted on the ground, bottom-right (x 438–490, y 476–492); original aloha.pk tag removed per the no-credit-line rule, credit kept in the `.txt` description |
| `.txt` | name, author `shywolf91 + AI`, `fog = (182, 166, 208)`, `heavens_color = (34, 36, 96, 255)`, `glow_enabled`, `glow_stored_colors` (73 675 entries, 2.9 MB); no spawn/entity hooks, no mode keys |

Props keep a 9-voxel margin off the towers and the map edge; trees are spaced for 7+ voxel gaps and their tiers start 3 above
the ground, so the floor stays walkable. Giant tree, houses and igloos are real (gingerbread/igloo interiors connect to the outside).

## Validation `[RUN]`
| check | result |
|---|---|
| strict reader / re-encode identical | OK / identical |
| pyspades 1.4.2 `generate()` identical, ours == pyspades | True / True |
| z = 63 solid everywhere | True |
| tower geometry vs original | 0 voxels changed in the footprint outside the z = 1 bulbs |
| floating components | 17 total, all of them the listed sky pieces (0 unexpected); 22 stray decoration voxels removed by the cleanup pass |
| gingerbread / igloo interiors reach outside | all True |
| floor luma min / median | 76 / 189 (rule: floors ≥ ~40) |
| `.txt` loads | yes (exec'd like piqueserver's map loader) |

Expected floating (collapse caveat: if a player block next to one is broken it drops for the round):
flying sleigh + 4 reindeer (118–190, 50–76, z 8–26), 6 cloud islands, 8 snowflakes. Full boxes in `build.json`.

## Known limits / not tested
* Not loaded on a live server, not seen in a client (fog, glow look, FPS with 5 MB of colour-heavy geometry untested).
* Mode is unknown from the supplied file: spawns/objectives of the original `.txt` (not supplied) must be merged by the owner.
  Props sit only on the open floor and avoid the towers, so tower-top play is unchanged.
* Glow keys are inert on stock piqueserver; the baked light still shows. White glow is not used (dense sources wash to white).
* Tower roofs are the only z < 3 spaces (roof at z = 2), so roof decor is limited to the 1-voxel bulb row.
* Tree/prop placement is non-deterministic by rule; seed `20261118` rebuilds this exact map.

## Regenerate
```bash
python scenes/tradeoff_christmas/tc_build.py <tradeoff.vxl> maps/tradeoff_christmas_v1 --seed 20261118
python scenes/tradeoff_christmas/tc_check.py maps/tradeoff_christmas_v1/tradeoff_christmas.vxl <tradeoff.vxl> maps/tradeoff_christmas_v1/build.json maps/tradeoff_christmas_v1/validation.json
python scenes/tradeoff_christmas/tc_render.py maps/tradeoff_christmas_v1/tradeoff_christmas.vxl maps/tradeoff_christmas_v1/renders
```
Without `--seed` a new OS seed is drawn and saved in `build.json`. The original `tradeoff.vxl` is not stored in the repo.
