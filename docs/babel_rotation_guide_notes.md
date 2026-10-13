# Babel rotation guide — distilled lessons for map design (read 2026-10-13)

Source: *Babel map rotations guide* v1.8 (aloha.pk community, author "Snailmcsnailton", Feb 2023, 52 pages;
in the project files as `Babel map rotation guide v1.8.pdf`). It is a server-curation guide: which existing maps
survive in aloha.pk's Babel rotation and why. Below: its rules, the failure modes it names, server practice, and
how each maps onto our pipeline. Tags: `[GUIDE]` = stated in the guide (community experience, not code);
`[SRC]` = checked in piqueserver 1.4.2 source; `[RUN]` = we measured it.

## 1. The guide's five rules for Babel maps `[GUIDE]`
1. Not unbalanced — neither team may have an unfair advantage.
2. Spawn/design must not let spawn camping empty the server (but not "spawn fort on every map" either).
3. Spawn/design must not make spawn-block protection or tower protection prone to **self-grief**.
4. Cater to different play styles — variety across the rotation.
5. Avoid spawns **too close to the platform or too low**: the angle makes spawn camping very powerful and can lock
   whole teams.

## 2. Failure modes named, with examples `[GUIDE]`
| failure | examples in the guide | our rule / check |
|---|---|---|
| Spawn camping from the platform | tradeoff "spawncamp hell"; turtlesoup (sunken spawn, steep angle, open to platform); TowerDive "spawn camp paradise"; oasis, bridgeyard, babelstairs too open | **spawn exposure check** (`aosmap/sightline.py`, below); require cover between platform and spawn |
| Spawn camping fixed by design | trademas = tradeoff lowered + spawn protected; crossfire3 spawn "covered a bit from platform"; swampcanyon/JoeyRaysBayou/xmasfire2/oasis2 trees cover spawn; normandie trees, walls, objects; roadisland bushes/cars so some spawns are out of platform sight; hezeehills/halongbabel/skullfort covered or fortified spawns | cover = trees, walls, buildings, terrain between spawn and platform; "not every spawn in line of sight" |
| Spawning on roofs, can't get down | lard | spawn zones clear of roofs/tall props (we already enforce: Babel spawns land on the topmost voxel) |
| Self-grief / blocking | halongbabel cave spawn can be blocked; pinline/pinline2/jsweet "griefer paradise… empties server"; turv towers stuck to platform | no single-entrance spawns; no narrow chokes that one player can seal |
| Unsupported towers griefed | pincushion "towers tend to be griefed due to lack of support" | give tower zones solid ground / supports; avoid building over voids |
| Unbalanced | stackattack (a house makes one team's build much easier → "no go"); HaLongBay (unmirrored, favours blue); ravenloft (red more open spawn, less height to build from); blackwidow (one building) | mirror gameplay geometry; **free-scaffolding check** (nearest authored structure to platform per side) |
| Uneven but compensated | yarr: one side higher ground, the other has a tree to bridge from | acceptable only if measured equal (build gap per side) |
| Platform too low / too high | summerfields "way too low"; makewar low but a cliff behind spawn gives a tower start; hexclimb "might play out too quickly due to the height" | build gap in the reference range; report per bridgehead |
| Lag | matrix_babel (lots of one-block pillars), mazemountain "a bit annoying with lag" | avoid dense 1×1 pillar fields; watch voxel count / column complexity |
| Visual fatigue / readability | tradeoff "bright annoying fog"; tradeoffnight "darker, better for the eyes"; 1river2white "too white to read text on voxlap"; hiesville "rows of yellow blocks with 1-block spacing" flicker, "insanely distracting" | avoid very bright fogs/whites; no high-contrast 1-voxel stripes; check HUD readability against fog |
| Cap limit | cheesus, anticbridgebabelv2 "would benefit from 20 cap" | note expected round length in the spec |
| Broken in repo | alpine "bugged and won't load", chute "refuses to advance" | always server-load test (our alpine copy parses fine — their issue may be the repo file/metadata) |

## 3. Server / rotation practice on aloha.pk `[GUIDE]`
* Rotation = list of map names with straight quotes (`"tradeoff", "swag2", …`); a wrong or missing name stops the
  server from starting. Test rotations on the aloha test server with `!rotation name1 name2 …` (in game or IRC);
  that is a test only — real rotation changes go to sysadmins with per-map settings.
* **Per-map settings beside the name:** platform type and fog. Platform types mentioned: normal, pinpoint, random,
  big hole, diamond, checkerboard, open, fork, "reversed pp". Fog overrides e.g. hexclimb `70 120 80` / `50 80 50`.
* Tents/spawns in the guide's example come from the map's `.txt` hooks (`get_entity_location`,
  `get_spawn_location`). **Stock piqueserver 1.4.2 ignores those in Babel**: babel_script replaces both hooks
  with fixed bases (118, 256)/(394, 256), spawns random ±20 on the topmost voxel `[SRC]`. aloha runs custom scripts
  (platform variants, spawn protection, tower protection, "Ferraris spawn protection zones"). → Our maps target
  stock behaviour but also ship `.txt` hooks so a server like aloha's can use them.
* Testing tips: use the dev environment with aloha's scripts; set spawn time 0.
* `snow.py` "broke the platform regularly" — seasonal scripts can interfere with Babel.
* Rotation size ~15–24 maps, sometimes weighted toward a favourite; maps grouped by type to keep variety.
* Map discovery: aos.party/view/<id> pages, Lostmotel's 3D listing (community.aloha.pk), old aloha repository.

## 4. What we added to the pipeline because of this guide `[RUN]`
**Spawn exposure check** — `aosmap/sightline.py`: eyes on the platform perimeter (z −1.4) → heads on a 2-voxel
grid of each ±20 spawn zone (stock spawn rule), straight-line visibility through the map + platform, fog ignored.
Calibration on rated maps (stock base positions; aloha may spawn elsewhere on some of these):

| map (guide verdict) | exposed % (t1/t2) | platform viewers per spawn spot | depression angle | spawn floor z |
|---|---|---|---|---|
| tradeoff — "spawncamp hell" | 96 / 95 | **61** | 0.7° | 2 |
| abridgetoodark — rotation staple | 100 / 100 | **56** | 1.3° | 3 |
| anticbridgebabelv2 — works (cap 20) | 67 / 62 | 16 | 8.3° | 12–14 |
| waterfrontv2babel — rotation | 100 / 100 | 13 | 15.9° | 26 |
| battlefarm — "kind of open, some cover" | 97 / 100 | 9.0 | 31.6° | 56 |
| swag2 — "too open but works" | 97 / 99 | 8.6 | 34.4° | 61 |
| islandbabel | 100 / 100 | 9.0 | 34.4° | 61 |
| babelpocalypse — "open but not too bad" | 87 / 81 | 7.8 | 25.2° | 44 |
| normandie — protected spawn | 90 / 96 | 8.2 | 33.5° | 58–60 |
| alexandria-babel2 — works | 95 / 93 | 7.9 | 33.1° | 58 |
| GoonassaultJapan — "open spawn" | 86 / 88 | 7.9 | 34.9° | 62 |
| hallweebalohabeta — rotation | 59 / 72 | 7.2 | 31.5° | 62 |
| TowerDive — "spawn camp paradise" | 62 / 63 | 5.1 | 31.4° | 57 |

Reading it: almost every Babel spawn is *mostly* visible from somewhere on the platform edge, so "% exposed" alone
does not separate good from bad. **Viewers per spawn spot** does: spawns at platform height (sky decks, angle < ~10°)
are seen by 25–60 edge positions at once (tradeoff's camping problem). Ground maps sit at ~5–10 viewers; the ones
the guide likes add cover so a share of spawn spots is hidden (hallweeb 30–40 %, normandie 5–10 %). TowerDive shows
the metric is not everything — it fails for water and hard building, not exposure.
Working targets for our maps (preliminary, to refine with playtests): **≤ 10 viewers per spot, ≥ 15 % of spawn
spots hidden, and no sky-deck spawn at platform height without a cover line toward the platform.**

Our maps, same check:
| map | exposed % | viewers | angle | verdict |
|---|---|---|---|---|
| Kestrel Spires v2 | 100 / 100 | **26** | 5.9° | spawn deck nearly level with platform and open → tradeoff-like camping risk; needs a cover line |
| Hollowfen v1 | 92 / 91 | 7.4 | 32.6° | normandie-like; acceptable, more cover would help |
| Hollowfen Vale v1 | 100 / 100 | 10.3 | 28.2° | open hilltops; needs cover on the platform side |

## 5. Checklist additions (also in aos_map.md §12)
- [ ] spawn exposure: viewers per spot ≤ ~10, ≥ 15 % hidden, no level-with-platform open deck
- [ ] no single-entrance or sealable spawn; no griefable choke on the only route out
- [ ] tower zones have solid support (no building over voids that one cut collapses)
- [ ] no 1-voxel high-contrast stripes / pillar fields (flicker, lag)
- [ ] fog not glaring/white; HUD text readable against it
- [ ] spec states expected platform type (stock = solid "normal"), fog, cap-limit advice for rotation admins
