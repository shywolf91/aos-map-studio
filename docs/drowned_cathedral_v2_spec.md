# Drowned Cathedral v2 — rotated layout + safe descents (2026-10-14)

**Status:** specified · generated · exported · parser-validated · **server-loaded** (live Babel, piqueserver 1.4.2,
stock script list, blue/red) · **not** client-inspected in BetterSpades/OpenSpades/aos_web · **not** playtested.

Generator: `scenes/drowned_cathedral_v2.py` (seed 1414, built on the v1 generator `scenes/drowned_cathedral.py`).
Check: `scenes/drowned_cathedral_v2_check.py`. Map files: `maps/drowned_cathedral_v2/` (`drowned_cathedral_v2.vxl`
+ `.txt`, 3.59 MB, SHA-256 `3c93cf28…eff407`; same bytes under another PYTHONHASHSEED and on Python 3.11 / 3.13).
Previews: `docs/img/drowned_cathedral_v2/` (first-person views from `tools/fp_view.py`, an approximation, not a
client capture). v1 is unchanged (`maps/drowned_cathedral_v1/`, byte-identical after the shared-code changes).

## Why v2
Tester feedback on v1: *"the map is too tall… I'd play it rotated 90 degrees… players might find it difficult to get
down from the platform."* Dylan's reading: players need a safe way down from where they spawn to the tower build zone
and to ground level (the rest of the map).

A literal 90° turn of v1 breaks stock Babel: `babel_script` fixes the bases at (118, 256) / (394, 256) and the
platform at x 206–305, y 240–271, so the rotated file put spawns in the fen (1,114 water columns) and on the ruins,
mirror symmetry dropped to 0.53 and spawn exposure rose to 8.8 viewers per spot. v2 is a redesign around the same rules.

## What changed
| | v1 | v2 |
|---|---|---|
| cathedral axis | nave north–south, across the teams' line | nave **east–west between the teams**: west front + nave + crossing tower + east nave + east front, x 206–305, so the platform lies along the nave like a lid |
| fronts | one façade (north) | **twin fronts**, one facing each tower zone, with rose window (r 4.5) and a gable kept low (apex z 23) so it gives no build shortcut |
| transepts | x 214–297 (short) | north/south arms y 190–322 into the fen lobes, with an arcade (2×2 piers every 11, pointed arches), two surviving vault ribs, slumped floor slabs and tomb chests; great window + door at each end |
| fen | ellipse 150 × 196 (taller than wide) | ellipse **195 × 150** (wider than tall), drowned town in north and south lobes (12 houses per half) |
| ways down from spawn / zone | one 4-wide stair per mole face | **6 ghats per team** (20–24-wide stepped stone banks, 1-voxel risers, z 40 → 59): two on each face of the mole, one on each face of the spawn precinct; plus a **gallery** through each front at zone level (portal z 35–39) with two 3-wide flights down into the nave |
| guard rails | — | ghat cheek walls, gallery parapet and flight rails are **2 high** (no auto-step over a 1-voxel lip into a fall) |
| one-way pockets | 2,698 nodes per half (flooded aisles/pools you can step into but not climb out of) | **about 55 per half** (114 on the map): an escape-step pass adds 2-stone stairs (z 61 → 60 → floor 59) to every pocket of 3+ nodes |

Unchanged from v1: spawn precinct (chapel, ossuary, graveyard, gatehouse screen), mole + tower zone (x 148–205,
flat z 40, no props), bell tower with belfry floor z 32 and twin stair cores, sky-level signature
("Drowned Cathedral / Designed by shywolf91 and AI"), fog (152, 174, 168), no spawn hooks in the `.txt`.

## Validation (2026-10-14; route model preliminary — 3-voxel standing clearance, 1-voxel auto-step, 2-voxel jumps)
* Reader OK; **pyspades `VXLData` load → `generate()` byte-identical**; piqueserver `Map` loads `.vxl` + `.txt`
  (extensions `babel`, `water_damage`; no spawn/entity hooks). Floating components **0**. Mirror (x' = 512 − x)
  occupancy match 0.99896 (only the sky sign differs).
* Tower zones 6,612 columns, all flat z 40; spawn squares all z 40.
* Platform not reachable without building. Build gap **39** from your own esplanade, **30** from the bell-tower
  ledge (as v1). Nearest authored voxel to the platform 17 (bell-tower pinnacle, z 18).
* **Safe descent** (nav graph with every fall ≥ 10 removed): every target is reached from spawn with **no fall
  damage** and at the same cost as with falls allowed — esplanade edge 66 · ghat foot 62 · precinct ghat foot 72 ·
  gallery 84 · nave floor 110 · fen water 117 · crossing 123 · belfry 168 · north transept door 182 · enemy
  esplanade 203 · enemy spawn 289. 16,396 of 16,562 fen nodes per half reachable without fall damage, and from all
  of them a player can walk back up to spawn without fall damage.
* **Unguarded edges on the descent routes: 0** (5,316 route nodes on ghats, parvis, gallery, flights; an edge counts
  when a walking player, auto-stepping a 1-high lip, would drop 10+).
* Route parity team1 vs team2: **0.0** on every target.
* Spawn exposure: 62.8 / 62.4 % exposed, **3.8 / 3.5 viewers per spot** (targets ≤ 10), unchanged from v1.
* **Live** (headless piqueserver 1.4.2, babel + babel_script, blue/red): fog (152, 174, 168); intel (256, 256, 1);
  bases z 40; the client receives 3,200 platform cells and the map differs from the file only there; 6 default bot
  spawns all on the precinct squares (eye z 37.6).
* Art metrics: 8,098 colours, 4 hue families, coherence 1.47 (v1 1.37; inside the 1.4–2.5 reference band).

## Risks / things to watch in playtests
* **Gallery vs esplanade:** the gallery is a second zone-level entry into the nave right under the platform's ends.
  It is not a shortcut (nothing above it is walkable), but expect fights at the portals.
* **Centre no-destroy band** (stock script: nobody can remove blocks at x 224–288) now covers the crossing, both
  transepts and the east half of each nave. Player blocks placed there are permanent.
* Remaining one-way spots (about 55 per half) are small: beams inside the crossing tower and the quay cornice ledges. Getting
  off them costs a damaging drop or one placed block.
* Not yet seen in a real client: fog tint, stained glass, the ghats' readability as stairs.

## Make it yourself
```powershell
.\venv\Scripts\python scenes\drowned_cathedral_v2.py out\drowned_cathedral_v2        # ~20 s
.\venv\Scripts\python scenes\drowned_cathedral_v2_check.py out\drowned_cathedral_v2  # routes, safe descent, gaps
```
Server: copy `drowned_cathedral_v2.vxl` + `.txt` into `maps/`, add `"drowned_cathedral_v2"` to `rotation`, Babel
game mode + `babel_script` as for v1 (`server_test/dc_babel/config.toml`).
