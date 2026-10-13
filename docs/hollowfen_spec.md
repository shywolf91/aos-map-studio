# Hollowfen — Halloween Babel + CTF map, art v1 (2026-10-13)

**Status:** specified · generated · exported · parser-validated · server-loaded (live **Babel** and live **CTF**,
piqueserver 1.4.2) · **client-inspected in BetterSpades** (spectator, Mesa software GL) · **not** inspected in
OpenSpades · **not** playtested.

Brief (user, 2026-10-13): full 512 × 512 Halloween map like normandie / remus; haunted village with church,
cemetery, forest; dusk atmosphere; witches flying at sky level as easter eggs (not near platform or spawns).
Answers: balance Babel and CTF equally; classic destructible terrain (no protection script), solid ground to the
bottom like remus/normandie; witches are pure scenery.

Generators: `scenes/hollowfen.py` (layout + graybox, `SPEC`, seed 1031) · `scenes/hollowfen_art.py` (art) ·
`scenes/hollowfen_props.py` (original prefabs) · checks `scenes/hollowfen_check.py`.
Map files: `maps/hollowfen_art_v1/`.

## Reference study (measured, not copied)
| map | ground | underground | layout |
|---|---|---|---|
| remus | flat z 62, buildings to z ~51 | 73 % columns fully solid | dense city, river, CTF |
| normandie | rolling z 54–62 | 94 % fully solid | countryside, central stone village, hedgerows, scattered woods |
| waterfrontv2babel | valley z 20–62 | 94 % | ground Babel, central village on a river loop |
| 1mirror2forts | high plateau z ~8 over water | — | mirrored forts |
Benchmarks taken: 2–3-storey houses ~10–14 to the ridge, trees 6–10 tall, ground z 54–62, solid underground.

## Layout (west half authored, mirrored x' = 512 − x; z down)
| element | where | notes |
|---|---|---|
| village ground | z 57 (players stand on 57, eye 54.6) | solid to z 62; forest hills z 49–57; rim ridge toward map edges |
| spawn square = Babel spawn zone = CTF spawns | x 98–138, y 236–276 | flagstones, nothing on it (spawns are all on z 57) |
| lanes | lane_n y 231–235, lane_s y 277–281 (cobble), back lanes y 205 / 307, farm lane y 256 | dirt roads loop north/south through the forest to the bogs |
| houses | 28 per side on shared plots | timber-framed, 2–3 storeys, jetties, lit/dark windows, chimneys; ground floor enterable |
| church | nave x 150–182, y 248–264; tower x 183–193, y 251–261 | stair inside the tower to the **belfry deck z 32** (Babel bridgehead); spire 1-in-3 (not walkable) to z ~12 |
| cemetery (neutral midfield) | x 210–302, y 198–314, ground z 56 | 2-high wall, 5 gates per side incl. N/S; mausoleum at the centre under the platform |
| bogs | centres (256, 132), (256, 380) | open water to z 62, stepped mud banks; boardwalks y 130–133 / 379–382 on posts |
| farm (CTF intel) | x 26–86, y 238–274; intel (56, 256) / (456, 256) | pumpkin field, barn, farmhouse, scarecrows |
| CTF tents | (118, 256) / (394, 256) | = Babel bases |
| witches | (70,92), (196,56), (448,84), (86,438), (318,462), (452,404), broom z 15–21 | floating by request; ≥ 184 from the platform, ≥ 134 from either spawn square |
| witch's hut (easter egg) | NW forest clearing (40, 120) + mirror | crooked hut, green cauldron |
| fog | (118, 92, 124) mauve dusk | chosen in BetterSpades from 4 candidates |

## Validation (2026-10-13; route model preliminary)
* Floating components: 6 = the 6 witches (requested); 0 unexpected. Reader OK. Deterministic (same bytes under a
  different PYTHONHASHSEED). SHA-256 95faaeae…836e.
* **Babel:** platform not reachable without building (both teams). Build gap 33.6 from the belfry deck (13 out,
  31 up). Spawn squares all z 57, mirror-equal 1.00. Live server: platform 3,200/3,200, intel (256,256,1), bases z 57,
  bots spawn standing on the squares (eye z 54.6), fog from the .txt.
* **CTF:** intel settles at z 57 on both farms, tents z 57 on the squares; 50/50 hook spawn points standable.
  Live server: flags (56,256,57) / (456,256,57), tents on the squares, spawns on the squares.
* Routes from spawn (identical both teams, parity 0.0): belfry 90.7 · cemetery gate 77.1 · mausoleum 111.6 ·
  north boardwalk 175.6 · south boardwalk 174.4 · own intel 42.0 · enemy intel 327.0 · enemy square 265.0 ·
  carry enemy intel → own tent 348.4.
* Boardwalks: 588 deck cells, 100 % clear (3 air above). Highest walkable point outside the towers: the rim ridge at
  the map edge (z 27), far from all objectives.
* Art metrics: 5,550 colours, 4 hue families, coherence 1.70, side −12.2 L* (normandie 4 / 2.26, remus 4 / 1.64).
* Counts: 56 houses, 2 churches, ~106 graves, ~3,990 trees (pine, autumn broadleaf, dead), 98 field pumpkins,
  22 lamps, 6 witches, 2 witch huts.

## What the real client showed (BetterSpades)
* Reeds were being placed on the bog boardwalks and blocked them — fixed, and a boardwalk clearance check added.
* A roadside jack-o'-lantern landed on Blue's CTF intel spot (intel would rest on it) — fixed (roadside props only
  in the forest); the CTF check confirms intel z 57.
* The well blocked the axis from the square to the church door — moved to the corner of the green.
* Fog: mauve (118,92,124) keeps the lit windows and lanterns glowing and sits between the team colours; deep violet
  read too dark, amber blended with the autumn trees and the red team, blue dusk favoured the red team's visibility.

## Risks / things to watch in play
* Destructible terrain: houses and the church can be dug through and collapse when undermined (classic play).
  The church tower stair hangs on the tower walls — digging the tower walls drops treads.
* Belfry is a strong sniper nest over the cemetery and squares (symmetric for both teams).
* Spire as scaffolding: builders can place blocks on the 1-in-3 spire steps to reach z ~12 (gap ~21) — faster than
  building from the belfry. Intentional shortcut for now; watch whether it dominates.
* Witches can be reached by building and knocked down (collapse rules); scenery only.
* CTF carry route is long (~348); if rounds drag, move intel closer (farm → back of village).
