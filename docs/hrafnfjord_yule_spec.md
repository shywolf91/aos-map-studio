# Hrafnfjord Yule v1.0: Viking-age Yule Babel (+ stock CTF)

Polar-night Viking Yule on a frozen fjord. A full-height ice fjord widens into a packed ice bay under the Babel
platform. Each shore has a village (Skali mead hall with antler gables, smithy, longhouse with byre, bathhouse,
naust boat sheds with beached longships). The Raven Gate arch spans the north ice, Skogarborg-style Yule forest and
beacon towers cover the fells, and Sleipnir stands on the south ice. Built 2026-11-20/21 through the agent pipeline
(aos-guru → map-designer → map-builder → map-runner), branch `map/nordic-christmas`.

## Owner answers `[USER]` (2026-11-20)

| question | answer |
|---|---|
| mode | stock Tower of Babel (babel_script, standard, no assist structures), "but also can be played in ctf" |
| map | full 512 × 512; layout, centre, tower zones, spawns, flanks, snow and palettes left to the agents |
| theme | Viking-age Yule / Nordic winter village; polar night with glow blocks |
| water | none: frozen river / lake / coast in ice colours (solid land) |
| extras | glow blocks, floating sky decor (moon, sleigh, …); underground only if it fits (not used) |
| fog, corner tag | agents' choice: fog (176,164,196), heavens_color (44,40,88,255); tag SW on the ground |
| concept (popup) | hybrid of concept 1 "Hrafnfjord" + concept 3 "Skogarborg" (`scenes/nordic-christmas/concept/`) |
| CTF strips (popup) | open farmland, low cover only, no roofs |
| name (popup) | "Hrafnfjord Yule" |
| spawn cover (popup) | keep the fronts open; if under 15 % hidden, waive it |

## Status ladder

researched → specified → generated → exported → parser-validated → **server-loaded** (piqueserver 1.4.2, Babel, glow
`.txt` accepted, 2026-11-21). The stock CTF server loaded the graybox (2026-11-20); our probe can't sample CTF spawns
without hooks, so CTF placement was simulated (below). **Not client-inspected, not playtested.** All renders are
numpy previews.

## Layout (SPEC: `scenes/nordic-christmas/nordic_christmas_spec.py`; west half, east = 512 − x)

| element | where (west) | notes |
|---|---|---|
| land / spawn / anchors | z 40 | spawn mounds z 39–41 |
| ice | z 43; bay ellipse (256,256) rx 43 ry 72 → x 213–299; fjord channel x 231–281 full height | grey-green ice, walkable banks |
| anchors | x 206–212 / 300–306, y 236–275, flat z 40 | solid to z 63, no props |
| tower zones | x 181–212 / 300–331, y 240–271 (32 wide) | ground-built |
| spawn squares | x 98–138 / 374–414, y 236–276 | ±4 no-prop margin |
| front x 139–211 | 12 low objects, 5.8 % share | lateral berms y 214–240 / 272–298 |
| CTF strips | x 0–127 / 384–511, y 128–383 | farmland: stepped stooks, hesjer, julenek, frozen pond, rear hills |
| bay | Thing-Rock barrow + Lawspeaker's rock (under platform, 30 % cover, ≥ 26 air), 2 frozen-in longships, 4 ice huts, pressure ridges, Pyre Holm, Rune Holm | 7–10 gaps |
| villages | mead hall 132–178 × 148–172, smithy, 4 naust 186–210, longhouse 140–178 × 308–330, bathhouse | 40 registered structures |
| fells | stave church 138–162 × 72–96 (tiered, dragon heads), 2 beacons, 2 hunting lodges, forest belts y 0–112 / 400–511 | flank routes y ~104 / ~408 |
| landmarks | Raven Gate x 222–290 × 96–108 (crown z 18, spiral stairs in both legs, carved ravens), Yule pyre, rune ring, Sleipnir 246–266 × 440–458 | |
| sky (expected floating) | moon, sleigh + 6 reindeer, 2 ravens, 10 aurora ribbons | ≥ 114 from platform, ≥ 10 air below |
| corner tag | "HRAFNFJORD YULE", SW ground, x 6–98, y 495–505 | |

## Validation (release build, SHA-256 7423485efef06dad…, 2,964,228 bytes; `.txt` 4.2 MB, loads in ~1.1 s)

| check | result |
|---|---|
| determinism (fresh process) | same SHA-256 `[RUN]` |
| parser, re-encode, pyspades `generate()` | byte-identical |
| `.txt` | author 'shywolf91 + AI', no hooks, `'babel': True`, water_damage 0, fog, heavens_color, glow_enabled, 76,145 glow keys (all on solid) |
| babel_checks | 18 PASS + 2 WAIVED (spawn exposure); 4 zone rules pass |
| mirror / floating | 0 solid mismatch outside cosmetic boxes; only the 16 declared sky objects float |
| routes (graph model) | safe descents, flanks 470 / 474, 0 trap cells, 56/56 interiors (Raven Gate crown, church loft, beacons, barrow), build gap 31 |
| craft_checks babel / ctf | 40/40 structures; Babel spawns and CTF strips pass |
| CTF strip simulation (stock rule, 2000 draws + all columns) | 0 % roofs, 0 % treetops, 0 % stranded, ~3.3 % on low prop tops |
| palette_audit | 0 % snow over 212, max top luma 198, tops < 40 ≈ 0 %; ground p10/p90 78/163 |
| geometry diff vs graybox | 11,415 added / 1,128 removed, all inside declared `art_additions` / sky / tag boxes; routes unchanged |
| live probe (babel) | platform 3200 cells, spawns and intel placed |

## Spawn exposure vs open front: waived `[USER]` (2026-11-20)

0 % of spawn spots hidden; mean platform viewers Blue 10.98, Red 10.00. The map is exactly mirrored. The Blue/Red
difference is the `babel_checks` viewer sampler's phase (it samples the west platform end one column more), not the
map. The owner chose open fronts over gates or taller berms. Recorded in `build.json` `waivers`.

## Visual review (craft_standard §5; numpy close-ups in `maps/hrafnfjord_yule_v1/renders/closeups/`)

| piece | verdict |
|---|---|
| Raven Gate | matches: arch ring, keystone, battered legs, two carved ravens, rune bands; hero of the map |
| mead hall | matches: antler gables, continuous roof snow, eave lights, framing trees |
| longhouse + byre, smithy, naust | match |
| longships | match: strakes, shield rows, striped awning, dragon prow |
| stave church | matches after round 3: tiered svalgang → nave → clerestory → tower → spire |
| Thing-Rock, pyre | match |
| Sleipnir | reads as an eight-legged horse; still blocky, below the exemplars' finesse |
| rune ring, bathhouse, beacon, ice huts | acceptable, plainer than the exemplars |
| spawns, CTF strips | designed farmland yards, not bare fields |

## Known limits

* Not seen in any client: glow look, fog distance, flicker and FPS untested. The Raven Gate crown view needs a client frame.
* CTF spawns/intel/tent placement simulated, not observed in a live CTF round (probe tool needs hooks).
* On a server that loads `babel_script` in a CTF rotation, the platform is built on this map anyway.
* Floating sky pieces collapse for the round if a player block next to one is broken.
* Corner-tag levelling clears a 2-voxel margin around the tag text (kit `paint_tag`).
* Full-strip CTF object tops differ by 4 columns (1,078 vs 1,082) because the stock strips aren't exact mirrors under x' = 512 − x.

## Regenerate

```
python scenes/nordic-christmas/nc_main.py maps/hrafnfjord_yule_v1/graybox 3483926697 3764651784
python scenes/nordic-christmas/nc_main.py maps/hrafnfjord_yule_v1 3483926697 3764651784 --art 20261121
python -m aosmap.kit.babel_checks maps/hrafnfjord_yule_v1
python -m aosmap.kit.craft_checks maps/hrafnfjord_yule_v1 --mode babel   # and --mode ctf
python tools/palette_audit.py maps/hrafnfjord_yule_v1/hrafnfjord_yule.vxl --fog 176,164,196
python -m aosmap.kit.probe maps/hrafnfjord_yule_v1 --mode babel
```
Layout seed 2026112001 (fixed); vegetation 3483926697, decor 3764651784, art 20261121 (OS-drawn, saved in `build.json`).
