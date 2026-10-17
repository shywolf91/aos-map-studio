# spinline — joke Babel map (2026-10-16, v1.4)

Status: generated / exported / parser-validated (own reader + pyspades 1.4.2, 0 mismatches, byte-identical re-encode) /
server-loaded (stock piqueserver 1.4.2: babel game mode + babel_script + map_extensions, .txt loads without error) /
spawn-checked with the real server functions / client-loaded by user (v1.0 "pitch black" → fixed in v1.1).
Not playtested.

## What pinline is (measured from pinline.vxl + the user's pinline.txt)
* Entire map = z=63 bottom layer painted with a smooth dark-red wash (≈ (110,11,5), luma ~40); one grey line
  (768 voxels, ≈ #806967 ± 3 per channel), 2 voxels wide, 1 tall (z=62), x 64–447 at y 255–256.
  Every column is one 8-byte span → file exactly 2 MiB. The 768 water cells under the line have no stored colour.
* pinline.txt (izzy/danke): `extensions = {'water_damage': 100}` — the water kills, the line is the only ground.
  Hooks: spawn at (70,256)/(440,256) at get_z−1 (on the line); bases (70,256,63)/(440,256,63).

## Verified server behaviour (piqueserver 1.4.2 source)
* `babel_script` (ALWAYS_ENABLED = True) overwrites `map_info.get_spawn_location` and `get_entity_location` on map
  change → **.txt spawn/base hooks are ignored on stock Babel**. Its rule: base (118,256)/(394,256) +
  randint(−20,20) on x and y, z = map.get_z (topmost voxel). So pinline's own hooks only work on servers with
  custom babel scripts (e.g. aloha); on stock, pinline spawns mostly land in deadly water.
* `map_extensions.on_position_update`: if 'water_damage' in extensions and player position z ≥ 61 → hit.
  Standing on the z=62 line keeps the player above that; standing in the z=63 water layer does not.
* pyspades spawn: position = (x+0.5, y+0.5, z−2.4).
* Quirk: piqueserver.map.Map.load_information uses importlib.util without importing it; fine inside the
  server, but a standalone test must `import importlib.util` first or the .txt silently fails to load.
* A .txt that fails to parse is only logged ("Error while loading map info") and the map still loads — with
  no extensions, so water_damage silently disappears. Always re-test the .txt load after editing it
  (an apostrophe inside a single-quoted description did exactly this once).

## spinline
* Path: the user's spiral image, traced at 1.15 voxels/px, radius 238, centre (256,256). v1.4: skeletonised →
  single longest path (inner curl → outer tail, ~10,480 voxels) → Gaussian-smoothed (sigma 3) → redrawn at a
  constant 6-voxel width (drawn line median), z=62, one connected component. Measured width 5.7–7.2 (pixel steps),
  median 6.0; rings ≥ 14 voxels apart centre-to-centre → water gaps ≥ 8. (v1.0–1.3 used the raw drawing, 2–12 wide.)
* Blocks (v1.4): every z=62 voxel (spiral + discs) gets a random colour from pinline's own 768 line colours.
  Tag uses pinline's median line grey.
* Water (v1.3): copied colour-for-colour from pinline.vxl's z=63 layer (all 190,359 visible cells match;
  pinline's 768 hidden cells nearest-neighbour filled). History: v1.0 near-black → v1.1 deep indigo → v1.3 pinline red.
* Spawn discs (v1.2): solid z=62 discs r=30.5 at (118,256) and (394,256), covering the stock ±20 zones
  completely and joining the spiral.
* .txt: name, version 1.4, author, description, fog (150,158,180), water_damage 100, pinline-style hooks
  reproducing the stock rule (same zones) for servers that keep hooks; bases at disc centres.
* Check results: 0 of 3,362 zone cells off-ground; 20,000 spawns per team through babel_script.get_spawn_location
  and through the .txt hook all at z=62.
* Tag painted on the floor top-left: "spinline" (2×) / "Designed by shywolf91 and AI" (1×).
* Generator: `build_spinline.py spiral.jpg out pinline.vxl` (seed 7591) + vxl.py + centerline.py (needs
  scikit-image); spawntest.py; spinline_package.zip.

## Lessons
* Don't use near-black floors (v1.0 luma ~10 read as pitch black). Pinline-level brightness (luma ≥ ~40) minimum.
* On stock Babel, guarantee spawns with geometry under the ±20 zones, not with .txt hooks.
* For a traced drawing, skeleton → longest path → smooth → constant-width stroke gives a clean uniform line that
  still follows the hand-drawn path (an ideal fitted spiral drifted: ring spacing isn't constant).
