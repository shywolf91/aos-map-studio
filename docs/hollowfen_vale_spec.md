# Hollowfen Vale — Halloween Babel + CTF, single central village (2026-10-13)

**Status:** specified · generated · exported · parser-validated · server-loaded (live **Babel** and live **CTF**,
piqueserver 1.4.2) · **client-inspected in BetterSpades** · **not** inspected in OpenSpades · **not** playtested.

Variant of Hollowfen requested 2026-10-13: *one village in the middle with blue and red spawns either side, no
building inside the tower build zones, the village can extend beyond the middle, some rolling hills.*
Interpretation used: "tower build zones" = the stock babel_script tower corridors between each spawn and the
platform; they contain **no authored structures, trees or props** (open meadow), so each team builds its tower
from the ground there. Same dusk theme, prefabs and fog as Hollowfen v1.

Generator: `scenes/hollowfen_vale.py` (seed 1038; reuses `hollowfen_props.py` and the material/house/church/forest
functions in `hollowfen_art.py`). Check: `scenes/hollowfen_vale_check.py`. Map files: `maps/hollowfen_vale_v1/`.
Server configs: `server_test/vale_babel`, `server_test/vale_ctf`.

## Layout (west half authored + mirrored x' = 512 − x; church pasted whole on the centre line)
| element | where | notes |
|---|---|---|
| spawn hills | domes at (118, 256) / (394, 256), top z 47 | spawn squares x 98–138 (mirror), clear; team banners (blue / red) around them |
| **tower build zones** | x 139–212 and 300–373, y 228–284 | open meadow rising from the spawn hill to the village level; **0 structures** (checked) |
| market green (under the platform) | x 220–292, y 214–298 | flagstones, 8 market stalls, hay, lanterns, giant jack-o'-lantern at the centre — all ≤ 6 tall |
| church (neutral) | x 244–268, y 147–196 | nave north–south, door north, tower at the south end facing the green; stair to the belfry (z 32) |
| churchyard | around the church | graves, dead trees |
| cemetery (neutral) | x 222–290, y 316–392 | wall, gates, mausoleum, dead trees; ~76 graves across cemetery + churchyard |
| village quarters | x 142–210 and 302–370, both north (y 100–212) and south (y 300–412) | 6 lanes per side, 90 houses + 12 hillside cottages (both sides) |
| farms (CTF intel) | behind each spawn hill, intel (52, 256) / (460, 256) | pumpkin field, barn, farmhouse, scarecrows |
| rolling hills + forest | everything else | ~3,300 trees; ponds with reeds; witch's huts in clearings (N and S, both sides) |
| witches | 6 at the map edges, broom z 15–21 | requested floating scenery |
| fog | (118, 92, 124) | same as Hollowfen v1 |

## Validation (2026-10-13; route model preliminary)
* Floating: 6 components = the 6 witches; 0 unexpected. Reader OK. Deterministic (same bytes under another
  PYTHONHASHSEED). SHA-256 1b5ceb3f…43ed5, 4.69 MB.
* **Tower zones:** 8,436 columns, **0 with any structure** above the terrain. Spawn squares: 0 structures.
* **Babel:** platform not reachable without building (both teams). Ground gap from the zone edge: 56 (straight up).
  Nearest authored structure to the platform: 49 (a market lantern) → the village hands out ~7 voxels of free
  scaffolding at most, in neutral ground. Walkable gap 53 (top of a market prop). Church belfry is 184 walk / ~56
  straight-line from the platform — no shortcut. Live: platform 3,200/3,200, intel (256,256,1), bases z 47,
  spawns on the hilltops (eye z ~46).
* **CTF:** intel z 51 on both farms (= ground), tents z 47 on the hilltops; 50/50 spawn hook points standable.
  Live: flags (52,256,51)/(460,256,51), tents on the hills, spawns on the hills. Carry enemy intel → own tent 354.
* Routes from spawn (team1 / team2): green 103.4 / 103.4 · cemetery gate 105.8 / 105.8 · mausoleum 136.9 / 136.9 ·
  church door 161.4 / 161.4 · belfry 184.1 / 186.3 (shared tower, non-symmetric spiral) · own intel 46.0 / 46.0 ·
  enemy intel 330.9 / 330.9 · enemy spawn 264.1 / 264.1.
* Art metrics: 5,497 colours, 4 hue families, coherence 1.44 (just under the 1.5 target; forest leaf noise),
  side −12.4 L*.

## Client notes (BetterSpades)
* The green tent at each base in the screenshots is the client's own Babel/CTF base model, not map geometry
  (the first camera was placed inside it).
* Spawn hills read as stepped grassy domes with the team banners; the meadow zones are clearly open; the church
  clock tower is the landmark from the green.

## Risks / things to watch
* Ground Babel: 56 straight up is at the long end (islandbabel ~56). If rounds stall, raise the meadow toward the
  platform (both zones) or lower the platform on the server.
* The market green sits under the platform; dropped intel returns, but players will fight on it — watch spawn-hill
  sightlines across the open zones (snipers on the hilltops).
* Destructible terrain: the spawn hills can be dug; the tower meadows can be trenched (classic play).
* Coherence slightly low in the forest; a calmer leaf palette would raise it.
