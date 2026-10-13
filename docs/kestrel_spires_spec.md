# Kestrel Spires — Babel map (graybox v1 2026-10-12 · art v1 2026-10-13 · art v2 2026-10-13)

**Status (art v2, current):** specified · generated · exported · parser-validated · server-loaded (live Babel) ·
**client-inspected in BetterSpades** (real client, spectator, Mesa software GL) · previewed in aos_web ·
**not** inspected in OpenSpades · **not** playtested.
Layout below is unchanged by both art passes (all route/gap/spawn numbers re-checked).

Mode: stock piqueserver 1.4.2 `piqueserver.game_modes.babel` + `piqueserver.scripts.babel_script`
(normal scripts, blue/red teams, optional `authored_protect` after babel_script).
Generator: `scenes/kestrel_spires.py` (seed 7317, `SPEC` dict = this document's numbers).
Checks: `scenes/kestrel_spires_check.py`, `tools/babel_live_check.py`.

## Layout (west half authored, mirrored x' = 512 − x; z down, smaller z = higher)
| element | where | height |
|---|---|---|
| script sky platform + intel | x 206–305, y 240–271; intel (256, 256) | z 1 |
| spawn mesas | centre (112, 256) / (400, 256), radii 54 × 52, back terraces z 15 / 21 | deck z 10 |
| spawn plaza | x 98–138, y 236–276 (exactly the script's ±20 spawn square) | z 10 |
| arch → sentinel spire (main bridgehead) | arch x 166–177, y 252–260, steps 10 → 13; spire r 6.5 at (178, 256) | top z 13 |
| flank fingers (secondary bridgeheads) | (168, 226), (168, 286), r 4.5, stepped buttress ramps from the rim | top z 17 |
| slot stair (descent / return) | 4-wide gully x 86–132, y 214–217, 1-voxel steps, tunnel out to the canyon floor | 10 → 56 |
| canyon floor | y 172–340 | z 56 |
| river under the platform | x 228–284, stepped banks x 214–227 (z 56 → 61) | water |
| outer canyon walls (scenery) | y 150–171, 341–362 | tops z ~6–12 |

## Validation (automated; route model preliminary)
* 0 floating components; strict reader OK; no team-colour clashes (blue 0,0,255 / red 255,0,0).
* Platform **not reachable without building** for either team.
* Spawn zones: all 1,681 columns at z 10 for both teams; equal under mirror (1.00).
* Walk costs from spawn, identical for both teams (max difference 0.0): spire top 40.6 · fingers 35.5 ·
  slot-stair foot 81.6 · own canyon floor 153.8 · enemy canyon floor below their spire 371.7 ·
  river bank 280.3 · canyon floor → own spawn 175.6 · river → bank 46.5.
* Build gaps (straight line to the platform's standing surface): spire 25.1 / 25.9 (22–23 out, 12 up);
  fingers 39.4–40.6 (34–35 out, 12–13 sideways, 16 up). Reference range 5–56.
  The 1-voxel team difference is the stock script's own platform offset (platform symmetric about 255.5, bases about 256).
* Live server (piqueserver 1.4.2 babel): platform 3,200/3,200 cells in the map clients receive; intel at
  (256, 256, 1); bases (118, 256, 10) / (394, 256, 10); bots spawned at eye z 7.6 (standing on the z 10 deck);
  fog (196, 170, 140) from the .txt. Same file SHA as delivered.

## Metadata
`kestrel_spires.txt`: name, author, fog, `extensions = {'babel': True, 'water_damage': 0}` (`babel` is read by
babel_script only when its ALWAYS_ENABLED is False). Includes CTF-fallback spawn/entity hooks that babel
mode replaces; CTF play is **not** designed or balanced.

## Risks / things to watch in play
* Cliffs from the mesa to the canyon are lethal drops (46 voxels); the slot stair is the safe way down.
* Enemies can climb your slot stair from the canyon into your spawn mesa (symmetric; intended counterplay, watch for spawn camping).
* Players may build up the outer walls to near-sky perches (they are ~70 voxels from the platform's long edge).
* Babel's anti-grief stops teams destroying blocks on their own half; the canyon floor under the enemy spire is the intended place to cut enemy towers.
* Water damage is off: falling into the river is survivable and the stepped banks lead out.

## Art pass v1 (`scenes/kestrel_spires_art.py`, seed 7317)
Built on `build_graybox(mirror_output=False)`, then mirrored. Walk surfaces (spawn plaza, arch, ramps, stair) get a
4-voxel air keep-out and a 3-column 2D buffer so no prop lands on a route.
* **Rock:** banded sandstone (`StrataShader`: warped, slightly tilted ochre→rose strata, darker sides/undersides),
  separate wall palette for the outer canyon walls, caprock crust on every exposed top, rimrock lip at the deck edge,
  vertical cliff flutes z 16–53.
* **Landmarks:** sentinel spire tapers below z 30 and carries a 15×11 kestrel relief (pale bird on a carved dark niche,
  1 voxel deep) facing the river; arch has a curved underside; flank fingers are hoodoos (neck r 2.7, flared base, cap)
  reached by ramps carved down to 3-voxel rock bridges.
* **Cliff dwellings:** two alcoves on each inner face (y 234–247, 265–278, z 24–35) with two plaster rooms each
  (T-doors, windows, vigas only where the wall survives) and ladder poles. Scenery only — not reachable on foot.
* **Deck:** concentric paving rings around the spawn base, 7 caprock outcrops, 4 rain basins, junipers (41) and
  grove-gated sage clumps (300) kept off routes and the ±22 spawn square; 22 talus boulders at the cliff feet.
* **Canyon/backdrop:** gravel and wet-sand floor, turquoise painted z 63 river (|x−256| ≤ 30), desert haze elsewhere.
* Metadata: author `aosmap (art v1)`, same extensions and fog.

### Art v1 validation (2026-10-13)
* 0 floating components (8 floating vigas and a shortcut ledge were found and fixed during the pass); reader OK;
  no team-colour clashes; spawn zones all z 10, mirror 1.00; platform unreachable without building.
* Routes (identical both teams): spire top 41.8 · fingers 35.5 · slot-stair foot 81.6 · own canyon 158.3 ·
  enemy canyon 376.3 · river bank 285.4 · canyon → spawn 180.1 · river exit 46.5. Small rises vs graybox come from
  route-side props; build gaps unchanged (spire 25.1 / 25.9, fingers 39.4–40.6).
* Art metrics (tools/art_metrics.py): 4,285 colours, 2 hue families, coherence 1.72, side −16.8 L* —
  inside the measured reference range (tradeoff 1.63 / −10.5, alpine 2.21 / −18.5, normandie 2.26).
* Live server (piqueserver 1.4.2 babel, port 32921): map loaded in 0.51 s; platform 3,200 / 3,200 cells;
  intel (256, 256, 1); bases z 10; bots spawned at eye z 7.6 on both decks; fog (196, 170, 140).
  SHA-256 ff49b7f8…7a43.
* Note (found during v2): v1 colours came from a shader seeded with Python's randomised `hash()`, so the
  delivered v1 file (`maps/kestrel_spires_art_v1`) can't be regenerated byte-for-byte; geometry can. Fixed since.

### Known art limitations / next iteration ideas
* Canyon floor between the mesas is still broad and plain (gravel tone only); candidates: dry wash channels, low
  ledges, scattered cover — must be re-checked for route parity and new camping spots.
* Deck outcrops read as small mushrooms at distance; could be lower and wider.
* The south dwelling is largely hidden behind the south hoodoo when seen straight on.
* Outer walls are banded but flat in plan; a few buttresses/side canyons would break the long faces.

## Art pass v2 (`scenes/kestrel_spires_v2.py`, called by `kestrel_spires_art.py`; seed 7317)
`python scenes/kestrel_spires_art.py out/kestrel_spires_art2` (v2, default) · `... --v1` rebuilds v1.
* **Canyon floor:** two meandering dry washes per side (terraced 1/2/3-deep profile, so every edge is a
  1-voxel step — never a trap), grey wash bed with pebbles, pink cut banks; desert-pavement patches;
  5 slickrock benches in the inner canyon (three 1-voxel tiers, top 3 above the floor = crouch cover);
  2 sandstone fins by the river (7–9 high, sheer, tops unreachable); 8 cottonwoods along washes and banks.
* **Outer walls:** 12 tapered buttresses (sheer bottom 6, crust-free so ledges don't speckle) and 4 walk-in
  slot recesses with shadow-lined interiors.
* **Cliff dwellings v2:** arched alcove mouths with shadow lining, a two-storey tower with a setback terrace,
  a room block and a parapet court; the two dwellings mirror their layout (north/south).
* **Deck outcrops:** low three-tier mini mesas (1-voxel tiers) replace the mushroom stacks.
* **Fog:** lilac dusk **(200, 188, 206)**, chosen by comparing four fogs in BetterSpades (see below).
* Fixes found on the way: red-side spawn paving showed stripes (pattern wasn't mirrored) — fixed;
  `SurfaceShader` used Python's randomised `hash()` → colours differed between runs — fixed (crc32), with a test.

### Art v2 validation (2026-10-13)
* 0 floating components; reader OK; no team-colour clashes; spawn zones z 10, mirror 1.00; platform unreachable.
* Routes (identical both teams, parity 0.0): spire top 40.6 · fingers 35.5 · slot-stair foot 82.7 ·
  own canyon 159.3 · enemy canyon 383.7 · river bank 288.8 · canyon → spawn 180.0 · river exit 46.5.
  Build gaps unchanged (spire 25.1 / 25.9, fingers 39.4–40.6).
* **Canyon perches** (new check): highest point reachable on foot in the canyon = 4 above the floor (v1: 6).
* Art metrics: 5,765 colours, 2 hue families, coherence 1.58, side −14.5 L* (in reference range).
* Live server (piqueserver 1.4.2 babel): loaded; platform 3,200/3,200; intel (256,256,1); bases z 10;
  bots spawn on both decks; fog (200,188,206) from the .txt. SHA-256 59fe3cb3…04b3.
* **BetterSpades** (master a695aaa, built here, spectator, `tools/betterspades_capture.sh`): map received from
  the server and rendered; renders in `docs/img/betterspades_v2.png`. Gun models were stand-ins (asset pack
  unreachable) — irrelevant to map rendering.

### What the real client showed
* AoS fog is strong: past ~60 voxels everything blends toward the fog colour. With the v1 tan fog the
  sandstone dissolved (same hue). Compared live with `/fog`: tan (v1), pale blue (178,196,214),
  lilac (200,188,206), bright haze (232,214,188). Lilac separates rock from sky, keeps the cyan platform
  distinct, and its hue sits between the team colours (blue fog would hide the blue team more at range).
* Spire + kestrel relief, hoodoos, washes and the red paving read well up close. Wash pebbles were too
  bright ("sugar cubes") → toned down and thinned.
* From the platform the bases (~138 away) are beyond the fog — normal for Babel, but worth knowing.

### Remaining ideas
* OpenSpades inspection (different lighting/AO than BetterSpades).
* Playtest: canyon raids under the enemy spire, slot-stair camping, bench/fin cover value.
