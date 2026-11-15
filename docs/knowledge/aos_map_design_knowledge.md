# Ace of Spades 0.75 Map Design — Complete Knowledge Base

Consolidated 2026-10-30 from the AoS_Map_Making project: technical research, the `aosmap` toolchain, the aloha.pk
Babel rotation guide, the Build and Shoot heightmap tutorials, 15+ maps built and iterated, and every standing rule
the owner (Dylan / shywolf91) has set. Target: classic **Ace of Spades 0.75** (vanilla, OpenSpades, BetterSpades)
on **piqueserver / pyspades 1.4.2**, Python 3.11. Not the Jagex/Steam game.
Updated 2026-11-08: the custom Babel variant is redefined as **Babel with assist structures** (§7.1, §8.5, §8.8).

**Evidence tags** used throughout:

| tag | meaning |
|---|---|
| `[SRC]` | read in source code (piqueserver 1.4.2, OpenSpades, BetterSpades) |
| `[RUN]` | observed by running real code (pyspades, a live server, our tools, measurements on real maps) |
| `[DERIVED]` | computed from source equations, not confirmed in a client |
| `[GUIDE]` | stated by a community guide (aloha.pk rotation guide, Build and Shoot tutorials) |
| `[USER]` | the owner's stated decision or feedback — a standing rule unless noted |
| `[DESIGN]` | design guideline / judgement, not a fact |
| `[OPEN]` | not yet verified |

**Status ladder** for every map — report the highest rung actually reached, never skip one:
`researched → specified → generated → exported → parser-validated → server-loaded → client-inspected → playtested`

---

## Contents
1. Cheat sheet
2. The VXL file format (+ verified reference reader/writer)
3. Ground, collapse and water
4. Player movement
5. Map metadata (`.txt`)
6. Block protection
7. Game modes
8. Babel design rules (the project's main mode)
9. General layout and balance
10. Art direction
11. Fog, sky, night maps and glow blocks
12. House rules (naming, tags, author, spawns, questions)
13. Toolchain
14. Workflow: prompt → playable map
15. Validation checklist
16. Gotchas we hit
17. Map portfolio and what each one taught
18. Reference-map measurements
19. Legacy heightmap + colourmap workflow
20. Open questions
21. Sources

---

## 1. Cheat sheet

| Thing | Value |
|---|---|
| Map size | 512 × 512 columns × 64 voxels; x, y 0..511; z 0..63 |
| Vertical axis | **z = 0 is the top of the sky, z = 63 the bottom.** Height above bottom = 63 − z |
| Axes in practice | x runs west → east, y north → south (top-down image row = y) |
| Water | a column whose z = 62 is air is open water; z = 63 is always solid (water surface / seabed) |
| Unbuildable + indestructible | everything at z ≥ 62 `[SRC]` |
| Grounded | 6-face connected to any solid voxel with z ≥ 62; edges/diagonals don't count `[SRC][RUN]` |
| Player | 0.9 × 0.9 footprint; 3 air voxels to stand, 2 crouched; auto-steps 1 voxel |
| Jump / fall | jump apex ~1.6 voxels; fall damage from ~10, lethal ~20 `[DERIVED]` |
| Draw distance | ~110 voxels in game — nothing beyond is visible `[USER]`; fog blends everything past ~60 `[RUN]` |
| Colour | 0xAARRGGBB little-endian (bytes B, G, R, A); A = cosmetic shade byte, write 0x80 |
| Metadata | `<mapname>.txt` beside `<mapname>.vxl`; Python executed by piqueserver |
| Stock Babel platform | x 206–305, y 240–271, z 1, colour (0,255,255), **script-built — never in the VXL** |
| Stock Babel bases | (118, 256) team1 / (394, 256) team2; spawns random ±20 on the topmost voxel; intel (256, 256) |
| Owner's server | stock piqueserver, normal script list, team1 Blue (0,0,255), team2 Red (255,0,0) `[USER]` |
| File size | typical finished maps 2.4–5.2 MB |

---

## 2. The VXL file format

### 2.1 Layout `[SRC]` (pyspades vxl_c.cpp, OpenSpades GameMap::Load)
* **No header.** Columns are stored **y outer, x inner**: `for y in 0..511: for x in 0..511: <column>`.
* Each column is a list of **spans**. Span header = 4 bytes **N, S, E, A**:
  * **N** = length of this span in 4-byte units (header + colours). **N = 0 marks the last span** of the column.
  * **S** = first z of the top-colour run; **E** = last z of that run (**inclusive**).
    From this span's air start down to S − 1 is air; S..E are solid voxels whose E − S + 1 colours follow the header.
  * **A** = z where this span's air begins (meaningless in the first span). It also closes the *previous* span's
    bottom-colour run: that span's K = N − 1 − (E − S + 1) bottom colours belong to z = A − K .. A − 1.
  * Between a span's top run and its bottom run everything is **implicit solid** (hidden, colourless).
    In the last span everything below E down to z 63 is solid.
* Colour = 4 bytes **B, G, R, A** (little-endian uint32 0xAARRGGBB).

### 2.2 Details that matter for writers `[SRC][RUN]`
* **Surface rule** (which voxels store colours): solid and (z == 0 or any in-map face neighbour is air).
  Out-of-map x/y and below z 63 count as solid, so map-edge faces are not "surface".
* **The 4th colour byte is cosmetic only.** pyspades `make_color` writes 0x80; `update_shadows` writes 127 − occlusion;
  OpenSpades replaces it with 100; BetterSpades/libvxl masks it off. Reference maps carry 127/109/37, 128, 255, 100, 168.
* pyspades emits **zero-length top runs (E = S − 1)** for buried caves / hidden surface voxels; every pyspades server
  sends these to clients, so a reader **must** accept them.
* Hidden voxels carry no colour after a pyspades load; `get_point()` reports (0,0,0) for them (this is why Arena gates
  must be ≤ 2 thick — §7.3).
* Quirks in the wild: "void columns" (whole column air including z 63, e.g. 10yearsaloha) load in pyspades;
  OpenSpades copies the z 62 colour to z 63 when z 62 is coloured; some editors store colours on hidden voxels (harmless).
* Always force z = 63 solid for new maps.
* Tested: our project writer (`aosmap/vxl.py`) is **byte-identical to pyspades `generate()`** on all 36 reference files
  (34 distinct maps), shade byte included `[RUN]`.

### 2.3 Verified minimal reference reader/writer (Python + numpy)
Re-tested 2026-10-30: **byte-identical** round trip on CloudSmash1.vxl (canonical pyspades encoding); on normandie.vxl
(written by another editor) occupancy and every surface colour identical, bytes differ only by encoding choices. ~3 s per map.

```python
import struct
import numpy as np
X = Y = 512; Z = 64

def read_vxl(data: bytes):
    solid = np.zeros((X, Y, Z), bool); color = np.zeros((X, Y, Z), np.uint32); p = 0
    for y in range(Y):
        for x in range(X):
            cs, cc = solid[x, y], color[x, y]
            while True:
                n, s, e, a = data[p], data[p+1], data[p+2], data[p+3]
                for i, zz in enumerate(range(s, e + 1)):
                    cc[zz] = struct.unpack_from("<I", data, p + 4 + 4*i)[0]
                if n == 0:                       # last span: solid from s to the bottom
                    cs[s:] = True; p += 4 + 4*(e - s + 1); break
                k = n - 1 - (e - s + 1)          # bottom-colour count
                pb = p + 4 + 4*(e - s + 1); p += 4*n
                na = data[p + 3]                 # next span's air start
                cs[s:na] = True
                for i in range(k):
                    cc[na - k + i] = struct.unpack_from("<I", data, pb + 4*i)[0]
    return solid, color

def surface_mask(solid):                         # pyspades is_surface
    air = ~solid; s = np.zeros_like(solid); s[:, :, 0] = True
    s[1:] |= air[:-1]; s[:-1] |= air[1:]
    s[:, 1:] |= air[:, :-1]; s[:, :-1] |= air[:, 1:]
    s[:, :, 1:] |= air[:, :, :-1]; s[:, :, :-1] |= air[:, :, 1:]
    return s & solid

def write_vxl(solid, color, force_bottom=True) -> bytes:
    solid = solid.copy()
    if force_bottom: solid[:, :, 63] = True
    surf = surface_mask(solid); out = bytearray()
    for y in range(Y):
        for x in range(X):
            so, su, co = solid[x, y], surf[x, y], color[x, y]; k = 0
            while k < Z:
                air = k
                while k < Z and not so[k]: k += 1
                ts = k
                while k < Z and su[k]: k += 1
                te = k
                while k < Z and so[k] and not su[k]: k += 1
                bs = k; z = k
                while z < Z and su[z]: z += 1
                if z != Z:                       # real bottom colours (air follows)
                    while k < Z and su[k]: k += 1
                be = k
                out.append(0 if k == Z else (te - ts) + (be - bs) + 1)
                out.append(ts); out.append((te - 1) & 0xFF); out.append(air)
                for zz in range(ts, te): out += struct.pack("<I", int(co[zz]))
                for zz in range(bs, be): out += struct.pack("<I", int(co[zz]))
    return bytes(out)

def rgb(r, g, b, shade=0x80):                     # colour helper
    return (shade << 24) | (r << 16) | (g << 8) | b
```

**Independent checks after writing:** reload with your own reader; load with pyspades `VXLData` and compare
`generate()` bytes; decode with D-VXLMapPreview or view on alohacraft.cc.

---

## 3. Ground, collapse and water

* **Grounding** = a 6-face path to a solid voxel with z ≥ 62. Same rule in pyspades `check_node`, OpenSpades
  `GameMapWrapper` and BetterSpades `map.c` `[SRC]`. A block touching only by an edge or corner is floating `[RUN]`.
* **Collapse runs only around a destroyed voxel** (destroy_point → check_node on its 6 neighbours). There is **no sweep
  at map load**, so floating authored pieces hang there until someone breaks a block next to them `[SRC]`.
* **check_node ignores protection.** Destroying an allowed (player) block next to floating authored geometry drops
  the authored geometry too (test: 10 voxels removed incl. a 9-voxel protected slab) `[RUN]`.
  → Grounding ≠ indestructible, and floating authored geometry is a griefing vector even on protected maps.
* **Floating authored pieces are opt-in** `[USER]`: fun and distinctive (witches, crows, bats, moons), used only when
  the brief asks. List them in the validator's `expect_floating`; everything else floating is an error.
* Shipped maps float a lot (JunglePush 740 components, Shenlong 288, t_o_r_t_u_g_a 118k voxels) `[RUN]` — don't copy that.
* **Hidden tethers:** Cloud Smash hangs its whole 674k-voxel cloud level on four 1–2-voxel stalks down to z 62.
  Cutting one removes 1 voxel; cutting all four drops the map `[RUN]`. Used for our sky-level name plates (one stalk).
* **Redundancy:** removing one voxel of a pillar removes 1 voxel; removing a full pillar layer dropped 287 voxels of
  roof `[RUN]`. Matters wherever authored blocks are destructible.
* **Ground must be solid all the way down** (like remus/normandie) unless a tunnel or underground structure is built
  there on purpose `[USER]`. The bottom layer is water or whatever block is put there. Islands get seabed foundations.
* **Water:** collision treats z 63 as z 62, so players stand on the seabed and "wade" when eye z > 61. **All water
  is the same wading depth** — without damage a player can walk across the whole sea to the map edge `[SRC]`.
* `water_damage` (map_extensions script) hits on each position update with position.z ≥ 61, in **every** water column
  (lagoons too); Push forces it to 100 (instant death). `boundary_damage {left,right,top,bottom,damage}` damages
  outside a rectangle — deadly edges with a safe near-shore sea `[SRC]`. "Island play" is a server choice, not geometry.
* Practical: every pit, pool, creek and cave floor needs a walk-back-out route (escape steps), and the sea needs pier
  stairs or shelves back to land.

---

## 4. Player movement

| Quantity | Value | Evidence |
|---|---|---|
| Footprint | 0.9 × 0.9 (±0.45) | world_c.cpp boxclipmove `[SRC]` |
| Standing clearance | **3 air voxels** (~2.7 tall) | `[SRC]` |
| Crouched clearance | **2 air voxels** | `[SRC]` |
| Auto step-up | **1 voxel**; not while sprinting or crouching, not looking steeply down | `[SRC]` |
| Jump apex | ~1.6 voxels (a 2-voxel ledge needs jump + step) | `[DERIVED]` |
| Fall damage | starts ~10 voxels, ≥ 100 dmg at ~20 voxels | `[DERIVED]` |
| Spawn | hook z = floor voxel; server places the eye 2.4 above (z − 2.4) | player.py `[SRC]` |

Design rules `[DESIGN]`:
* Stairs = **1-voxel risers**. Walkways ≥ 3 wide. Doorways ≥ 2 wide × 3 tall. Ceilings ≥ 4 where people should jump.
* Drops > 9 must be deliberate; ≥ 20 is lethal — fine as a cliff edge if a safe descent exists.
* **Guard rails / cheek walls must be 2 high** — a 1-voxel lip is auto-stepped over into the fall.
* Under trees: lowest branches ≥ 4 above ground so players walk underneath; trunks ≥ 6 apart in groves.
* Jump/fall figures still need in-client confirmation (the diagnostic map has 1/2/3 ledges, 3/2 tunnels, 10/20 drops) `[OPEN]`.

---

## 5. Map metadata — `<map>.txt`

piqueserver executes the file and reads only these names (piqueserver/map.py `[SRC]`):
`name, version, author, description, extensions, apply_script, time_limit, cap_limit, gen_script,
get_spawn_location(connection), get_entity_location(team, entity_id), on_map_change, on_map_leave,
on_block_destroy(connection, x, y, z, mode), is_indestructable(protocol, x, y, z)` plus `fog = (r, g, b)` (server.py).

* Entity ids: BLUE_FLAG 0, GREEN_FLAG 1, BLUE_BASE 2, GREEN_BASE 3; `connection.team.id` 0 = team1, 1 = team2, −1 spectator.
* A hook returning `None` falls back to default placement: a random **land** column (z 62 solid) in x 0–127 (team1) /
  384–511 (team2), y 128–383, at the **topmost** solid voxel — it can land on roofs.
* **Entities settle**: at load and after every block change, flags/bases drop onto the topmost solid voxel of their
  column. A roof or overhang above an intel/base/CP x,y catches it `[SRC][RUN]`.
* `on_block_destroy`: any falsy return (including `None`) **denies** the destroy.
* `extensions` only matters for keys some script reads. Stock map_extensions reads `water_damage`, `boundary_damage`,
  `disabled_commands`. `user_blocks_only` inside extensions does nothing — it is a server config option.
* Keys the owner's maps use `[USER]`: `'babel': True`, `'water_damage': <n>`, `'heavens_color': (r, g, b, a)` (sky colour
  set separately from fog; read by his setup, not by stock 1.4.2 `[OPEN]`), `'glow_enabled'` + `'glow_stored_colors'`
  (glow maps, §11.4).
* Harness gotcha: map.py uses `importlib.util` without importing it; standalone test scripts must
  `import importlib.util` first or the `.txt` silently fails ("Error while loading map info"). A normal server is fine.
* `cap_limit`: babel_script sets `map_info.cap_limit = 1`, but StateData on a live server showed the config default (10)
  — rotation admins set it per map `[RUN]`.

**House template (Babel):**
```python
name = 'The Hollow Crown'
version = '1.1'
author = 'shywolf91 + AI'
description = 'Halloween Babel: build from the citadel courtyard to the sky platform.'
fog = (168, 164, 178)
extensions = {
    'babel': True,
    'water_damage': 0,
    # 'heavens_color': (34, 24, 58, 255),   # optional sky colour (owner's setup)
}
# No get_spawn_location / get_entity_location hooks (owner rule) — mode defaults place spawns.
```

**Push template** (Push *requires* coordinates):
```python
extensions = {'push': True, 'push_spawn_range': 5,
              'push_blue_spawn': (x, y, z), 'push_blue_cp': (x, y, z),
              'push_green_spawn': (x, y, z), 'push_green_cp': (x, y, z),
              'water_damage': 100}
```
`'push': True` is convention; 1.4.2 push.py doesn't read it (the mode comes from `game_mode`).

---

## 6. Block protection

* **`user_blocks_only = true`** (server config.toml, 1.4.2): only player-built blocks can be destroyed — by **anyone**
  (no team ownership) `[SRC][RUN]`.
  * A grenade is cancelled entirely if any of its 27 voxels is protected; the spade also checks z ± 1, so spading a
    block lying on authored ground is refused.
  * `user_blocks` is in-memory; collapse-removed user blocks stay listed (harmless).
* **Owner's preferred policy** `[USER]`: authored map protected, players build, opponents destroy player blocks.
  Implemented as `server_scripts/authored_protect.py` (load after babel_script), live-tested with bots:

| Action | stock `user_blocks_only` | `authored_protect` |
|---|---|---|
| shoot authored ground | refused | refused |
| red shoots blue's block | destroyed | destroyed |
| blue shoots own block | destroyed | destroyed (refused with `team_can_destroy_own = false`) |
| red spades blue's block standing on authored ground | refused | block removed, ground intact |
| grenade on blue's blocks next to authored ground | whole grenade cancelled | blocks removed, ground intact |

  Partial removals are broadcast as individual DESTROY_BLOCK packets so clients stay in sync. `'authored_protect': False`
  in extensions disables it per map. Bot clients must hold the trigger for weapon block damage to register.
* Classic Babel maps on the owner's server are **destructible terrain** (solid to the bottom); no protection script is
  needed for the ground rule `[USER]`.
* Even fully protected maps lose **floating** authored geometry through collapse (§3).

---

## 7. Game modes (piqueserver 1.4.2)

Identify the exact script and its version before designing; a mode's name doesn't define its rules. Native protocol
modes: CTF and Territory Control. Included piqueserver modes: Arena, Babel, FFA, Infiltration, OneCTF, Push, TDM, TOW.
Everything else (Zombies, Fort Wars, KOTH, Domination, Parkour, sports, Running Man…) is a community family that needs
an actual script before you design to it.

### 7.1 Babel — `game_mode = "piqueserver.game_modes.babel"` + `piqueserver.scripts.babel_script` `[SRC][RUN]`
* The **script builds the sky platform** at z 1, x 206–305, y 240–271, colour (0,255,255), protected (3,200 cells).
  These are module constants; servers sometimes change shape/colour — treat them as parameters and read the target
  server's script. aloha.pk runs platform variants (normal, pinpoint, random, big hole, diamond, checkerboard, open,
  fork, reversed pp) `[GUIDE]`.
* **Never put the platform in the VXL**, and keep z ≤ 2 (plus a 1-voxel margin) empty over it.
* **One intel**: babel.py runs onectf in ONE_CTF mode at `one_ctf_spawn_pos` (default 256, 256; extension overrides)
  on the platform. Take it to **your own base** — (118, 256) team1, (394, 256) team2. babel_script sets
  `map_info.cap_limit = 1`, but only after the server has read the score limit, so the live cap is the config default
  (10 on a fresh server) — leave it to the rotation admin `[SRC][RUN]`.
* Dropped off the platform → intel returns ("returned to the heavens"). Carrier killed after 150 s.
* **Spawns**: random within ±20 of your base, on the **topmost voxel** → spawn squares x 98–138 / 374–414, y 236–276.
  Stock babel_script **ignores** the map's spawn/entity hooks.
* **Build ban**: a player can't build while standing in the **enemy's** tower corridor (team1 blocked at x 301–384,
  team2 at x 128–211; y 240–272). **Spade ban**: no spading while standing in your **own** corridor.
* **Destroy rule** (tests the **destroyer's position**, not the block's): team1 is refused while standing at x ≤ 288,
  team2 while standing at x ≥ 224. Player blocks in the centre are hard to clear, not permanent — a red player at
  x < 224 can still shoot a block at x 250. (Corrects an older note that "nobody can remove blocks in x 224–288".)
* Asymmetry: the platform is symmetric about x = 255.5, the bases about x = 256 → mirror with x' = 512 − x and accept a
  1-voxel route difference (68 vs 69 is normal).
* **Map requirements**: z ≤ 2 empty over the platform; **solid ground directly under both platform ends**
  (x 206–211 and 300–305) so towers can anchor; land under both whole spawn squares; platform not reachable without
  building (standard Babel — relaxed for the assist-structure variant, §8.8).
* Styles: **sky babel** (abridgetoofar, tradeoff, anticbridgebabelv2 — decks at z 2–13 around spawn) and **ground
  babel** (alexandria-babel2, islandbabel, babelpocalypse, normandie). Island babel = ground babel on islands.
  Island maps come in two styles `[USER]` (2026-11-15): **current** (our dense authored style, the default) and
  **classic** (when the brief says "classic island map"). The classic style is one natural island in a painted sea
  with sparse props; see `docs/classic_island_style.md`.
* **Custom variant: Babel with assist structures** `[USER]` (2026-11-08) — stock Babel rules, but the map provides
  climbable structures (ruins, a tall tree, a crag…) that reach the platform on foot or with a short build, so players
  can get the intel without building a tower in their tower zone. Runs on stock babel_script. Full rules §8.8.
* Seasonal scripts can break it: aloha's `snow.py` "broke the platform regularly" `[GUIDE]`.

### 7.2 Push `[SRC][RUN]`
* Each team spawns (±`push_spawn_range` around its spawn, topmost voxel) with the **enemy's** intel lying at its own
  spawn; it scores by carrying that intel to its **own** CP. Intel resets 3 min after a drop or on falling into water.
* Required extensions: `push_blue_spawn, push_green_spawn, push_blue_cp, push_green_cp` (mode raises without them).
  Optional: `push_spawn_range` (5), `push_cp_protect_range` (8), `push_blue/green_build_area` (x1,y1,x2,y2).
  This is the one place AI-authored spawn coordinates are unavoidable — tell the owner and keep them easy to edit.
* `water_damage` forced to 100 → every gap must be bridged; the bridge-building challenge is the mode. **No authored
  walkable bypass.**
* **Block ownership is by colour** (byte-HLS hue + saturation of the team colours); `protect_map_blocks` protects the
  rest. Authored palettes must avoid team H/S: with blue/red teams no pure blues (r = g = 0) and no pure reds
  (g = b = 0). Death Swamp clamps every authored channel to 6..249 → 0 hits `[RUN]`.
* Enemy intel is placed at your spawn x,y with z 1 and settles onto the topmost surface → keep spawn and CP columns free
  of roofs/overhangs.
* Can't build within 8 of your own CP; can't build inside the enemy's build area.
* Reference gaps measured: JunglePush 14–17, Shenlong 8–11 per water gap, twin parallel lanes, 3–4 gaps per lane.

### 7.3 Arena `[SRC][RUN]`
* Extensions `arena_blue_spawns`, `arena_green_spawns` (tuples of tuples), `arena_gates` (one coord per gate),
  `arena_max_spawn_distance`. `BUILDING_ENABLED = False` — building arena is a script change.
* Gates open by 6-face flood fill of **exact RGB**; hidden voxels read (0,0,0) → **gates ≤ 2 thick** (a 3-thick gate
  opened only 40 of 120 voxels); same-colour decoration touching a gate is absorbed; keep gates < ~900 voxels.
  Round 180 s, 15 s between rounds.

### 7.4 CTF
Built in. Default placement as §5. Use `get_spawn_location` / `get_entity_location` for authored layouts (only when
the owner supplies coordinates). Several base entrances; a central fast route and covered flanks.

### 7.5 Dual-mode layout pattern (Babel + CTF on one map) `[DESIGN]`
Put CTF tents on the Babel base coordinates and CTF spawns on the Babel ±20 squares; keep those squares flat and
prop-free; give each side its bridgehead inside its own Babel corridor so the babel_script anti-grief zones protect it.

### 7.6 Other modes
Hallway is a map name in the default rotation, not a mode. TC, TDM, FFA, Infiltration, OneCTF, TOW, Zombies, Last
Stand, Fort Wars, Domination, KOTH, Intel RPG, Parkour, Build, sports, Running Man and weapon-restricted play all have
design briefs in `ace_of_spades_075_map_design_prompts.md`; read the actual script before designing any of them.

---

## 8. Babel design rules (the project's main mode)

These combine the owner's standing feedback `[USER]`, the aloha.pk rotation guide `[GUIDE]` and our measurements `[RUN]`.

### 8.1 The guide's five rules `[GUIDE]`
1. Not unbalanced — neither team may have an unfair advantage.
2. Spawn design must not let spawn camping empty the server (but not "spawn fort on every map" either).
3. Spawn/tower protection must not be prone to **self-grief** or blocking.
4. Cater to different play styles — variety across a rotation.
5. Avoid spawns **too close to or too low under the platform** (steep angle = powerful camping).

### 8.2 Zones of a Babel map (stock coordinates)
```
 x:  0 ............ 98–138 ........ ~139–212 ..... 206–305 ..... ~300–373 ........ 374–414 ............ 511
     rear/flank     SPAWN SQUARE    FRONT +        PLATFORM       FRONT +           SPAWN SQUARE   rear/flank
                    (team1 base     TOWER ZONE     (z 1, script)  TOWER ZONE        (team2 base
                     118,256)       y 236–276                     y 236–276          394,256)
 y 240–272 = tower corridors (anti-grief zones); centre combat zone ≈ x 81–431, y 156–356
```

### 8.3 Spawns
* Spawns land on the **topmost voxel** of a random column in the ±20 square: **nothing on the square** taller than
  ~2 voxels, **no roofs or overhangs** over it (roof spawns = can't get down; guide's "lard"), no water, no holes.
* Spawns should **not be 100 % flat**, but easy to spawn on and navigate — gentle mounds/rolls, no pits `[USER]`.
* Both spawns mainly similar; they may differ in structure but the **fronts (spawn → tower zone) must be open** and
  give neither team an advantage `[USER]`. Mirror the gameplay geometry.
* **No AI spawn hooks** in the `.txt` — use mode defaults, or the owner specifies exact spawns later `[USER]`.
* **Cover from the platform** is the main quality bar. Measured target: **≤ ~10 platform-edge viewers per spawn spot,
  ≥ 15 % of spawn spots hidden, and no open deck level with the platform** (§18 table). Cover = trees, walls, buildings,
  terrain, gate arches — placed **outside** the ±20 square (cover inside it becomes something players spawn on top of;
  keep anything inside ≤ 2–3 high).
* Fix for near-level sky spawns: a **staggered pair of tall walls/ridges** between spawn and platform whose spans overlap
  so every straight line is blocked (Kestrel v3: 100 % exposed / 26 viewers → 12.7 % / 0.2).
* No single-entrance or sealable spawn; several exits (N/S/W gates + a wide front gate works well).

### 8.4 Fronts and tower zones
* **Nothing solid may block players between spawn and the tower zone.** Structures there are fine if there is an
  opening to pass through (a 33-wide gate arch, an arcade with 6 arches and a 9-wide gate) — a solid blocker only when
  the owner asks `[USER]`. Examples he gave: aos.party/view/413, aos.party/view/1248.
* Many players dislike screens between spawn and tower — OK occasionally, not a default `[USER]`.
* **Don't default to a raised tower zone** — players like building towers from the ground `[USER]`.
* Tower-construction zone: **32 voxels wide, 44–135 voxels from the centre** (= the stock corridor) `[USER]`. Keep it
  prop-free (ground cover and litter only), on solid support.
* Same-team players can't destroy voxels in it (anti-grief). Known exploit: griefers **switch teams** to block narrow
  passages in the zone — avoid narrow passages there `[USER]`.
* A team's tower-anchor ground must **not have stairs on the enemy-facing side** (too easy for the enemy to climb to
  that team's tower) `[USER]`.
* **No authored platform/ramp leading to the tower** unless asked `[USER]`.
* Players need a **safe way down** from spawn to the tower zone and to ground level (the rest of the map) `[USER]` — the
  Drowned Cathedral v1 failure. Use wide stepped banks ("ghats", 20–24 wide, 1-voxel risers) with 2-high cheek walls.

### 8.5 Build gap (how far players must build)
* Standard Babel: platform must be unreachable on foot. Measure the gap from the highest walkable point within ~24 of
  the platform to platform level. (The assist-structure variant, §8.8, deliberately shrinks or removes this gap.)
* References: anticbridgebabelv2 6, alexandria-babel2 5 (central tower), tradeoff ~17 (sky decks), abridgetoofar ~54,
  islandbabel ~56. Our maps: Kestrel 25 (sentinel spire) / ~40 (flanks), Drowned Cathedral 39 / 30 from the bell tower,
  Hollow Crown 40, Wicker King 39, Silverpine 40–41, Skull River v3 50–52.
* Most rated maps put **some** central feature under the platform (gaps 4–15). A central bridgehead (belfry, summit,
  pavilion roof) shortens the race and makes a contested point — expect fights there; if rounds end too fast, lower it.
* **Free-scaffolding check**: report the nearest authored structure to the platform per side; anything players can
  climb near the platform shortcuts the build. Tall landmarks near the platform (Ferris wheel peak z 5, pinnacles z 18)
  need a test.
* Platform too low → rounds too fast (hexclimb); too high → "summerfields way too low" style complaints `[GUIDE]`.
* Ground too close to the platform felt wrong to the owner on Skull River; he likes ground like 1river2night /
  1mirror2forts: low, only ~3–10 blocks above water, with tall terrain at the edges `[USER]`.

### 8.6 The centre and the rest of the map `[USER]` (standing feedback 2026-10-28)
* **Don't leave the centre empty.** Most combat happens in a central zone of ~300–400 × 150–250 voxels: pack it with
  gameplay elements and distinct objects to the same standard as the periphery (ask if the theme wants it empty).
* **Centre traversal** easy on foot: no bridge/stair building needed to reach the enemy spawn. Large structures are fine
  if easy to navigate — many wall openings, **7–10 voxel gaps** between structures; not a labyrinth; direct movement
  with only minor detours.
* **Flank route** along the edges, **130–210 voxels from the centre**, so players can attack from the rear.
* **Periphery must stay passable** — no overlapping or tightly packed objects (Backyard Babel v4's periphery was impassable).
* Some players play the centre, others the outer skirts — **every area needs artistic detail**; spread structures out.
* Underground layers (dens, mines, crypts) are welcome as long as the top ground above them stays populated.
* Tunnels are praised by the guide (SkullFort, roadisland); give tunnels two side galleries so one block line can't seal them.

### 8.7 Failure modes named by the guide `[GUIDE]`
| failure | examples | our rule / check |
|---|---|---|
| spawn camping from platform | tradeoff "spawncamp hell", turtlesoup, TowerDive, oasis, bridgeyard | spawn exposure check |
| roof spawns | lard | spawn squares clear of roofs |
| self-grief / blocking | halongbabel cave spawn, pinline, jsweet | no single-entrance spawns, no sealable chokes |
| unsupported towers griefed | pincushion | solid support under tower zones |
| unbalanced | stackattack (a house helps one team), HaLongBay (unmirrored), ravenloft, blackwidow | mirror; free-scaffolding check |
| lag | matrix_babel (1-block pillars), mazemountain | no dense 1×1 pillar fields |
| visual fatigue | tradeoff bright fog, 1river2white too white for text, hiesville 1-block yellow stripes | no glaring fog, no 1-voxel high-contrast stripes |
| platform height | summerfields too low, hexclimb too quick | build gap in reference range |
| broken in repo | alpine, chute | always server-load test |

### 8.8 Custom variant: Babel with assist structures `[USER]` (defined 2026-11-08)
* **What it is:** normal Babel — stock `babel` + `babel_script`, script-built platform ("heaven"), one intel on it,
  carried back to your own base. The difference is the map: authored structures (ruins, a tall tree, a crag/cliff, a
  belfry, a broken aqueduct, a wreck's mast…) that players can climb to reach the platform and intel **easily, without
  building a tower in their tower zone**.
* **Not** a ready-made tower with the intel sitting on it (an earlier, wrong reading of this variant).
* An assist structure either reaches the platform on foot (step/jump onto it) or leaves only a **short build** (a few
  blocks) from its top. Report the build gap per structure.
* Building towers stays a real option; the structure is the faster, riskier, contested route.
* Rules:
  * **Equal access**: mirrored pairs (one per side) or one symmetric central structure with equal routes from both spawns.
  * **Contestable**: approachable and attackable from below and from the platform; never a sealed private stairway.
  * The climb is part of the fight: ledges, stairs, ramps, broken floors, gaps.
  * z 0–2 (+1 margin) over the platform footprint stays empty — come up beside or under it, not into it.
  * Tower corridors stay usable for normal building (open fronts, solid ground under both platform ends).
  * Spawn exposure: a structure top near platform height is also a perch over the spawns — run `spawn_exposure`.
  * Round length: a 0 or tiny gap can end rounds too fast (hexclimb) — tune by playtest.
  * Decide destructibility per map: destructible terrain lets players cut the structure (counterplay, also grief);
    protected maps keep it. Test whether cutting it changes balance.
  * House rules still apply (real enterable structures, grounded geometry, rich original detail).
* **Relaxed checks**: "platform not reachable without building" and the free-scaffolding check don't apply in their
  standard form; label such maps "Babel, assist structures" and say which checks were relaxed.
* **References that already lean this way** (gap from a central feature, §18.2): hallweebalohabeta ~4,
  alexandria-babel2 ~5 (pyramid), babelpocalypse ~8 (hill), alpine ~8 (central peak).
* No script change needed while the platform/intel/base rules stay stock — confirm on the target server.

---

## 9. General layout and balance `[DESIGN]`

* Symmetric team modes: author **one half and mirror** (x' = 512 − x for Babel; **copy x 255 into 256** so the axis
  column isn't empty — a real bug). Mirror first, then place free-standing cosmetic asymmetry (a stem, a moon, a tag).
* Centre-line set pieces that are left-right symmetric by nature (skull, ship keel, doll on a stand) can sit on x = 256
  without breaking the mirror.
* Patterned shaders on mirrored maps must fold x (x > 255 → 512 − x) or the second half shows a different pattern.
* Plan per team: protected spawn exits, primary + secondary routes, flanks, chokepoints, objective approach and escape,
  build opportunities, boundaries.
* Hunt for: required-construction bypasses, sealable objectives, spawn traps, support exploits, unreachable camping
  perches, ways out of the play space. Water, walls and cliffs don't stop people by themselves.
* Props must never land on walk surfaces or objectives: keep a no-prop mask over routes, spawn squares, tower zones,
  intel/CP/base columns; a 4-voxel air keep-out above routes; 2–3 column buffer.
* Foundations must not create walkable shortcuts (a decorative ledge once cut a descent from 280 to 125 walk cost).
* Every building is "real" (§10.5) — and interiors need their own reachability test.
* Vantage points: report the highest walkable point near objectives/routes; foothills climbable ~12 above the basin
  are a new vantage to playtest.
* Push: equal gaps per lane, readable bridgeheads (clear radius ~10, lantern mooring posts), twin lanes with a water
  channel between them; nothing walkable between lanes.

---

## 10. Art direction

### 10.1 Priorities `[USER]`
* **Beauty / craftsmanship is the top artistic goal.** A valid VXL with crude shapes or a flat ugly layout is a
  prototype, not a map. Never trade essential gameplay or compatibility for a screenshot.
* Craft references (density and detail only — **never copy** objects, landmarks, terrain arrangements or models):
  Shenlong, Jungle Push (push); normandie, remus, swag2, tradeoff, alpine, abridgetoofar (babel/CTF); plus the other
  project VXLs; MountainRoad and alpine_desaturated for natural mountains and calm snow.
* He **really likes unique objects** on maps — one-off, well-crafted set pieces (a toy monster truck, a stump with an
  axe, a silver forge, a beast ribcage, a stopped clock face).
* Players enjoyed Wicker King's Harvest; the owner called Silverpine v2's art pass a "major improvement".

### 10.2 Measured calibration (`tools/art_metrics.py` on the references) `[RUN]`
| metric | reference range | target |
|---|---|---|
| hue families covering 90 % of surface | 2–5 | **2–4** (restrained palette) |
| spatial coherence of top colour (ΔL at 4 voxels ÷ ΔL at 1) | 1.4–2.5 (per-voxel random jitter = 1.0) | **≥ 1.5** — variation must be structured |
| side faces vs tops | −5 … −34 L* | **−10 … −20 L*** (hand-shaded depth) |
| shading style | flat painted (Shenlong: 184 colours, 74 % equal neighbours, ~11 L* steps) or fine gradients (tradeoff/alpine/alexandria: ~1–2 L* steps) | pick one per material |
| neighbour colour jump, top-down mean | MountainRoad 34, alpine_desat 25 | Silverpine v1 was 56 ("too noisy"), v2 29 |
| top-down bright share (luma > 175) | 7–8 % | keep low; v2 1.4 % |

### 10.3 Techniques that work `[RUN]`
* **Separate geometry from colour**: author with material ids, colour at export with shaders.
* **Silhouette first**: tapers, necks/flares (hoodoos), curved arch undersides, relief carved 1 voxel deep with a dark
  niche behind a pale figure — reads at gameplay distance. Strong silhouettes survive fog.
* **Baked lighting** on every surface voxel: a key light (e.g. moonlight from high NW, normal from blurred occupancy) +
  ambient occlusion (gaussian of occupancy). This made Silverpine's slopes read as shapes. Keep base jitter tiny (±1.5 %).
* **Big calm value shapes**: dark forest masses against open shaded ground; smooth natural slopes rather than strata
  everywhere ("wedding-cake" strata with snow lines looked bad).
* **Continuous cover model** for ground: a smooth weight per column (shade, trampling on paths/yards, slope, a few big
  patches) blending ground colours — no hard material blobs, rectangles or patchwork.
* `StrataShader` (warped, slightly tilted bands for sedimentary rock, darker sides/undersides, crust on tops),
  `SurfaceShader` (top/side/under ramps + height term + coherent noise + crevice darkening), `PatternShader` (paving).
* Snow follows slope and altitude (steep faces show rock).
* **Painted z = 63 backdrop** (Cloud Smash: 27,994 of its 28,109 colours are a sunset painted on the water plane; the
  playable cloud uses 111). Huge payoff, zero gameplay cost: mist, ink halos round islands (exp falloff ~10), reefs,
  lily pads, foam lines, moon glint, edge vignette, painted name tags.
* Dwellings must contrast with their rock (plaster vs sandstone) or they vanish.
* Light pools painted on the ground around lamps = colour/composition device; don't assume renderer lighting.
* Domain-warped Worley noise for billowing clouds/cauliflower forms (plain Worley looks like cracked mud).

### 10.4 Vegetation `[USER][RUN]`
* Plants must **not be uniform**: non-deterministic generator, wide variety of unique colours with **smooth, pleasing
  gradients** (smoothstep base → tip) that fit the scene; striking, intricate, strong visual style.
* Each plant gets **three distinct random details** (e.g. ladybug, dew, chewed holes that don't cut the plant apart,
  snail, caterpillar, autumn patch, variegation, withered tips, bud, aphids, butterfly, berries, bee, moss collar).
* Sizes from ~10 voxels up to 30–40; tall ones placed individually; never in front of spawns (behind/beside is fine).
* **Groves, not even scatter**: a low-frequency grove field decides where forest stands; clearings hold an odd lone
  tree; each grove takes its palette from a slow field over a calm family of close greens (8 conifer greens worked).
  "Confetti trees" (8 random palettes, speckle, flecks) looked bad.
* Trees: face-connected trunk → branches → crown (diagonal trunk shifts lost crowns to collapse); root plinth down to
  the slope; snow caps over whole tier sectors, not single voxels.
* No bare-pillar fields (lag + ugly); single trunks with crowns. Speckled scatter (sage, frost, cones) reads as noise.
* Random scatter in moderation (Silverpine cut to ~650 tries); boulders and logs carry the scatter.

### 10.5 Buildings and structures `[USER]` (standing rule 2026-10-20)
* **No solid buildings.** Every structure (houses, churches, chapels, tombs, towers, mausolea, tents, rides) must be
  **real**: open doorways, real rooms, real window openings, stairs to every upper floor, furniture/props inside,
  places to explore and hide.
* Doorways 2+ wide × 3 tall; stair steps rise 1 voxel; partitions with doorways; jettied upper storeys, chimneys,
  lit windows (amber glass), collapsed sections for ruins.
* Validate with an **interiors test**: a list of recorded points (every room and floor) must be reachable on foot from a
  spawn and lead back out (Hollow Crown 120/120).
* After carving doors/windows, re-run floating checks — door cuts once left 8 floating roof beams.
* Ruins: missing walls and roofs, broken beam ends, rubble ramps; decrepit-castle spawns wrap around (never over) the
  spawn square.

### 10.6 Avoid
Random colour noise · generic scattered cubes · empty flat expanses (no flat level ground unless built surfaces —
Backyard Babel: 0.5 % of 9×9 windows level) · oversized primitive shapes as landmarks · repeated recolouring of one
layout · decoration that blocks movement or hides players unfairly · 1-voxel high-contrast stripes (flicker) ·
1×1 pillar fields (lag) · **maps too white** (players hate it — design snowy maps with that in mind; cap snow at a max
channel ~212) · **maps too black** (players hate it — lift floors to luma ≥ 40) · props packed so tightly the
periphery can't be walked.

### 10.7 Palettes that worked
* Halloween: charcoal/weathered stone, black slate + dark purple roofs, dead grass/mud/grey dirt, charcoal trunks,
  muted orange/amber pumpkins, pale grave stone + moss; accents blood red, ghostly cyan, sickly green.
* Swamp: teal water with ink halos, olive/khaki rock-moss-peat-bone, dark bark, amber lanterns.
* Snow forest: shaded snow (never white), 8 close conifer greens, slate rock, teal lake gradient.
* Keep 3–4 hue families; push maps must also clear team hue/sat.

---

## 11. Fog, sky, night maps and glow blocks

### 11.1 Fog `[RUN][USER]`
* AoS fog is strong: past ~60 voxels everything blends toward the fog colour; silhouettes survive.
* **Fog looks acceptable only at brightness ~150+** (owner testing). Night maps get a **bright tint**, not a dark fog.
  Two exceptions were made on explicit request (1river2night v2.2 (58,44,86), Bikini Atoll (78,40,38)) — flagged for
  client checks.
* Don't match fog to the dominant material (tan fog + sandstone = landmarks dissolve). Pick a hue the palette lacks.
* Keep the fog roughly neutral between the team colours (blue fog hides blue players more).
* Check the objective reads against it (Babel's cyan platform vs blue-green fog). Avoid glaring/white fogs (guide).
* Fogs used: lilac dusk (200,188,206), (176,160,186); slate-green (152,174,168); pale moonlit lilac-grey (168,164,178);
  lavender dusk (158,146,182); pale lilac-grey (178,172,192); bright mauve-amber (190,168,176).
* Fog is server-side (`fog` in `.txt`, `/fog r g b` live) — iterate without re-exporting.

### 11.2 Sky
* `heavens_color` (RGBA) sets the sky colour separately from fog on the owner's setup.
* The 64-voxel ceiling plus fog stop a sky backdrop from carrying across the map: a moon read only from ~65 away.

### 11.3 Optional floating sky layer (opt-in) `[USER][RUN]`
* Only when requested; built as a separate `--sky` variant (v1 vs v1.1).
* Rules: ≥ 60 (we used ≥ 67–89) voxels from the platform, nothing over a spawn square, ≥ 8–9 voxels of clear air
  below each piece, 2 voxels clearance so no piece touches the map; all listed as expected floating.
* Silhouettes must be big: 5-wide birds were invisible; 13–15-wide crows/bats read well through lilac fog.
* Caveat: a player can drop a piece for the round by building against it and breaking that block; reload restores it.

### 11.4 Night maps and glow blocks
* Night recolour as a **DARK grade** multiplier on the base palette; glow strength is never scaled by DARK, so lanterns
  pop more as the base darkens. Top-surface median luminance: original 1river2night 3 ("too black"), v2 62 (too bright),
  v2.2 24 (accepted "a tad darker"), hallweebalohabeta 47.
* **Glow-block format** (inferred from hallweebalohabeta's data; no script source found) `[RUN]`:
  * `.txt` extensions `'glow_enabled': True`, `'glow_stored_colors': {(x,y,z): (r,g,b), …}`.
  * Sources = voxels in a fixed palette whose stored colour equals the VXL colour: (255,255,255), (255,95,95),
    (255,255,95), (95,255,255), (255,175,95), (95,255,95).
  * Lit voxels: **VXL colour = stored colour + source × 0.32 × (1 − d/6.5)** (additive, linear falloff, Euclidean d,
    summed, clamped). Light is **baked into the VXL**; stored colours let a glow-aware server redo it when blocks change.
    On stock piqueserver the keys are inert but the baked light still shows.
  * Nudge lit voxels that clamp onto palette colours by −1 so only true sources match the palette.
* Lessons: red glow (255,95,95) reads as pink specks; dense sources wash colours to white; put glow where light sources
  would really be (lanterns, windows, forge mouths, mushrooms, shrine lights).

---

## 12. House rules (owner's standing rules) `[USER]`

1. **Always ask questions before building a map** — never build without the answers (§14 step 2 lists them).
2. Map ground solid to the bottom; floating pieces only on request.
3. **No spawn hooks** in `.txt` files (Push coordinates excepted, flagged).
4. **Author field**: `author = 'shywolf91 + AI'` in every `.txt`.
5. **Corner tag**: the map name only, no credit line (unless he says otherwise). Usually painted on the ground (or 1 level
   above) in a corner; at sky level when the scenery in that corner suits it better (2-voxel plate, plain dark
   underside, one hidden stalk). Only clear the area under the tag. Exclude it from the mirror check.
6. Every structure enterable with rooms, windows and stairs.
7. Fog brightness ~150+; night maps via bright tint.
8. Don't leave the centre empty; passable periphery; flank route 130–210 from centre; 7–10 voxel gaps.
9. Babel: open fronts, no default screens, no default raised tower zone, safe way down, no stairs on the enemy-facing side
   of tower anchors, solid ground under both platform ends, no platform in the VXL. Assist structures to the platform
   only when the assist-structure variant is requested (§8.8).
10. Vegetation non-deterministic, varied, three details per plant.
11. Keep old versions (v1 beside v2…); new versions get new folders and bumped `.txt` versions.
12. Toolchain targets Python 3.11; repo `D:\Ace of Spades\Aos_Map` (to be hosted on GitHub for other sessions/AIs).
13. He tests in his own Ruby spectator client **aos_web** (localhost) and the **alohacraft.cc** VXL viewer.
14. Edits of community maps keep the map "relatively the same" and credit the original author.
15. Island maps (2026-11-15): current style by default; "classic island map" in the brief → the classic style in
    `docs/classic_island_style.md`, checked with `tools/island_style_metrics.py`. Build only the
    style the brief names, not both.

---

## 13. Toolchain

### 13.1 Environment
Python 3.11, numpy, scipy, pillow; piqueserver 1.4.2 (`pip install piqueserver`, gives pyspades `VXLData` for byte
checks and a real server); pyenet + Twisted for bots; Playwright Chromium for headless captures; Xvfb + Mesa llvmpipe
for headless BetterSpades.

### 13.2 `aosmap` package (project repo)
```
aosmap/vxl.py       read_vxl (strict; reports caves/void columns) · write_vxl (pyspades-identical) · rgb()
aosmap/scene.py     Scene(name, seed): material ids, box/carve/hollow_box/point (inclusive), markers,
                    paint_bottom, mirror, to_voxelmap() · Material(name, base, jitter, top, depth_ramp, shader)
aosmap/art.py       value_noise/fbm, ramp (linear-light, optional steps), hex_rgb, SurfaceShader, StrataShader,
                    PatternShader, heightfield(terrace, shore_z), apply_heightfield(cliff_mid), Prefab/stamp,
                    tree, boulder, house, stairs
aosmap/validate.py  floating_components, validate(expect_floating=...), check_babel, check_push, push_extensions,
                    push_team_colour_collisions, arena_gate_selection, spawn_check, settle_entity_z
aosmap/nav.py       route graph (3-air standing, 1 step, 2-voxel jump edges, drops ≥10 damaging, ≥20 excluded,
                    water excluded when damaging) · babel_route_check · ctf_route_parity · distances/path
aosmap/sightline.py babel_spawn_report: platform-edge eyes → spawn heads (viewers per spot, % hidden, angle)
aosmap/meta.py      map_txt() / check_map_txt()
aosmap/render.py    top_down, isometric (4 views), contact_sheet
aosmap/pixelfont.py 5×7 font for painted name tags
aosmap/pipeline.py  export → parser checks → real-piqueserver runtime checks → renders
aosmap/kit/         (2026-11-10) shared kit for new maps: codec, noise, canvas, structures, symmetry, color, veg,
                    tag, sky, babel_checks (full suite + summary), probe (live server), build (export, .txt rules),
                    preview. Merges the per-map copies; reproduces the HC / Silverpine / Bloomhop reports (docs/kit.md)
tools/              art_metrics.py (FIRST ARG IS THE OUTPUT JSON), fp_view.py (numpy first-person raymarcher),
                    compare_refs, island_style_metrics (classic vs current island style), movement_sim, fetch_map_from_server, bot_protect_test, babel_live_check.py,
                    aosweb_capture.cjs, betterspades_capture.sh (+ camfile patch)
server_scripts/     authored_protect.py
scenes/<map>/       per-map generator: *_main.py (build), *_check.py (validation.json), *_render.py (previews);
                    numbers in a SPEC dict (single source of truth); colours in one module
```

### 13.3 Viewers and clients
| tool | use |
|---|---|
| aos_web (owner's Ruby/Opal client) | `tools/aosweb_capture.cjs <map.vxl> <outdir> <views.json>` in headless Chromium; AoS (x,y,z) → three.js (x, 63 − z, y); render distance 160; slow on detailed maps (3–8 min per batch); release the bridge session (limit 4) |
| BetterSpades | built locally, joins a live server as spectator, screenshots set cameras (`betterspades_capture.sh`); real client look + `/fog` tests. Gotcha: draws the tent model at Babel/CTF bases (green polygons if the camera sits inside) |
| OpenSpades | second real client — not yet used for inspection |
| D-VXLMapPreview (rakiru) | independent D-language decoder/renderer (LDC 1.8.0 + dlib 0.7.1) |
| alohacraft.cc | owner's web VXL viewer ("VXL Test Page", isometric) |
| aos.party/view/<id> | community map catalogue (891 maps) — check names for clashes, study layouts |
| fp_view.py / numpy renders | fast previews — label them "not a client capture" |

### 13.4 Server testing
```toml
# server_test/<map>/config.toml (piqueserver 1.4.2; run: piqueserver -d server_test/<map>)
name = "babel test"
port = 32921
game_mode = "piqueserver.game_modes.babel"       # or "...push", "ctf", "...arena"
rotation = ["map_name"]
scripts = ["piqueserver.scripts.rollback", "piqueserver.scripts.protect",
           "piqueserver.scripts.map_extensions", "piqueserver.scripts.disco", "piqueserver.scripts.votekick",
           "piqueserver.scripts.trusted", "piqueserver.scripts.ratio", "piqueserver.scripts.passreload",
           "piqueserver.scripts.blockinfo", "piqueserver.scripts.squad", "piqueserver.scripts.afk",
           "piqueserver.scripts.babel_script", "authored_protect"]
[team1]
name = "Blue"
color = [0, 0, 255]
[team2]
name = "Red"
color = [255, 0, 0]
```
`.vxl` + `.txt` go in `<config dir>/maps/`; custom scripts in `<config dir>/scripts/`. `map_extensions` must be listed
for `water_damage`. A probe script / spectator bot confirms: map loads, fog, extensions, platform 3,200 cells, intel
position, sampled spawn z per team (400 samples), client-received map == file except the platform.

### 13.5 Determinism
Every generator takes a seed and prints it; same seed → same SHA-256 in a fresh process. **Never seed with Python's
`hash()`** (randomised per process) — use `zlib.crc32`. Owner wants plant placement non-deterministic: draw a random seed
per run, **save it** in build.json so the build can be reproduced.

---

## 14. Workflow: prompt → playable map

1. **Extract requirements**: mode + exact script/version, full map vs island, theme, landmarks, features, references
   (screenshots, mockups, VXLs), player count, protection policy, symmetry, night/glow, output expectations.
2. **Ask before building** (mandatory). Typical questions:
   * Mode and server script (stock babel? platform variant? team colours? standard or assist-structure Babel?).
   * Full 512 × 512 or island; ground height relative to water; mountain ring or open edges.
   * Island: current style or **classic** (`docs/classic_island_style.md` §7 lists the classic questions)?
   * Which concept (offer three) and which landmark goes where (centre / edge / under the platform).
   * What fills the centre; any underground layer; flank style.
   * Water behaviour: classic walkable, cursed (`water_damage`), or boundary box.
   * Optional floating sky layer? Optional glow blocks / night mood?
   * Fog and sky colour (or leave to me), corner-tag placement (ground or sky, which corner).
   * Must-have unique objects; anything to keep from a previous version.
3. **Verify mode and technical rules** (§7) and server parameters.
4. **Three distinct concepts** (identity, Babel style, spawn floor z, target build gaps, what's new for the rotation,
   art risk, play risk) unless the owner supplied one; recommend one with reasons. Check themes already used.
5. **Spatial spec** as a `SPEC` dict: playable bounds, elevations, zones with coordinates, landmarks, routes, supports,
   hazards, spawns/objectives, construction areas, palette (3–4 families), original asset list, fog.
6. **Graybox** with function colours; run the check script (floating, mode checks, routes, parity, gaps, exposure).
7. **Art pass** on the graybox: terrain, materials, baked lighting, original props, vegetation, interiors. Re-run every check.
8. **Mirror**, then place cosmetic asymmetry, sky layer, corner tag; clean orphan fragments (drop small floating
   leftovers per half before mirroring — report the count).
9. **Export** `.vxl` + `.txt`; round-trip with own reader + pyspades.
10. **Renders**: top-down, isometric, eye-level from spawns / tower zones / landmarks; label as previews.
11. **Server-load** with the target mode; probe spawns, platform, intel, fog.
12. **Client inspection**: BetterSpades / aos_web / OpenSpades; fog live.
13. **Playtest** with people; iterate. Save a spec doc per map (status, layout table, validation table, risks, regenerate commands).

---

## 15. Validation checklist

**Automated (before any hand-off):**
- [ ] strict reader OK; re-encode identical; pyspades `generate()` identical (or 0 / 20,000 sampled solid + colour mismatches); z 63 solid
- [ ] 0 unintended floating components (requested ones listed)
- [ ] mirror mismatch 0 outside cosmetic boxes / tag
- [ ] mode checks: `check_babel` (platform volume z 0–2 + margin empty, ground under both platform ends, spawn squares) / `check_push` (keys, spawn squares, intel + CP settling, team colours) / arena gate selection
- [ ] spawn squares: land, no water, no roofs, nothing > 2 high, gentle not flat, mirror-equal
- [ ] fronts: 0 solid blockers; tower zones prop-free and supported; no enemy-side stairs on anchors
- [ ] route reachability + team parity (graph model), shortcut hunt, build gap per bridgehead, platform unreachable on foot (standard Babel) / assist-structure gaps reported and equal per team (§8.8 variant)
- [ ] safe descent: nav graph with falls ≥ 10 removed reaches every target; 0 unguarded edges on descent routes
- [ ] traps: 0 standable pockets you can't walk out of (or listed); water exit 100 %
- [ ] interiors: every recorded room/floor reachable and exits back out
- [ ] centre crossable on foot; flank routes avoiding ±130 of centre exist; periphery ≥ 99 % reachable
- [ ] spawn exposure: ≤ ~10 viewers per spot, ≥ 15 % hidden (or the trade-off reported)
- [ ] no team-colour clashes (Push); entity settling (no roofs over intel/base/CP columns)
- [ ] art metrics within calibration; renders reviewed for floating props, blocked routes, noise, stripes, pillar fields
- [ ] deterministic build (same seed → same bytes in a fresh process); seed saved
- [ ] `.txt` loads, only real keys, author `shywolf91 + AI`, no spawn hooks

**Live / in-game:**
- [ ] server loads map + `.txt`; mode objects present (Babel platform 3,200 cells); fog applied
- [ ] spawns land where expected for both teams
- [ ] client: colours, edges, landmarks at play distance, fog readability, HUD text readable
- [ ] movement: jumps, steps, doorways, stairs, crouch tunnels, fall damage, water exit
- [ ] objective pickup / return / capture / reset; build / dig / grenade permissions; protection script
- [ ] camping spots, spawn pressure, FPS in dense areas, real player counts

Route checks are a graph model (3 air to stand, 1-voxel step, 2-voxel jumps, drops), **not** a collision simulation —
never present them as proof of playability.

---

## 16. Gotchas we hit

* `tools/art_metrics.py`'s first argument is the **output** JSON — passing a .vxl first overwrites it.
* Mirror first, then place free-standing scenery — anything placed before `mirror()` is duplicated.
* `mat[257:] = mat[1:256][::-1]` leaves column 256 empty → copy 255 into 256.
* Decor scatter must test its landing surface: reeds landed on boardwalks, a pumpkin landed on a CTF intel spot.
* `hash()`-seeded noise broke reproducibility (art v1) — use `zlib.crc32`.
* Diagonal trunk shifts → crowns lost to collapse; enforce face contact.
* Door carving removed walls under roof beams → floating vigas; re-run floating checks after every carve.
* Push intel and CTF bases settle onto roofs — check settling.
* Arena gates thicker than 2 never fully open.
* `on_block_destroy` returning `None` denies everything.
* A literal 90° rotation of a Babel map breaks stock Babel (bases/platform are fixed) — redesign around the fixed axis.
* Mock-ups that put teams north/south must be rotated 90° for stock Babel; unbalanced mock-up features (one field, one
  village) get mirrored pairs or move to the neutral centre line.
* A z-threshold on a gradient gives a hard ring; Worley without warping looks like cracked mud.
* Painted-only windows/doors don't count as real buildings.
* Island maps: stock spawn squares must be entirely land (planeassault_halloween's are all water — needs a custom script;
  GoonassaultJapan's are 28–30 % water).
* Original maps with no colour stored on side faces render black/default — recolour every surface voxel in edits.
* Previews from numpy renderers aren't clients; BetterSpades draws tents at the bases.

---

## 17. Map portfolio and what each one taught

| map | mode / style | status reached | key lessons |
|---|---|---|---|
| Diagnostic scene | test | server-loaded (ctf, arena) | exporter = pyspades byte-identical; collapse bypasses protection; gate thickness; settling |
| **Kestrel Spires** (sky babel, sandstone mesas, seed 7317) | Babel | client-inspected (BetterSpades) | sky decks level with the platform = camping (26 viewers) → staggered overlapping walls fix it; don't match fog to sandstone |
| **Hollowfen / Hollowfen Vale** (haunted fen village) | Babel + CTF | client-inspected | dual-mode layout pattern; "good first attempts, keep at it"; tower corridors as open meadow |
| **Drowned Cathedral v1 → v2** (sunken gothic cathedral, seed 1414) | Babel | server-loaded | v1 "too tall, hard to get down" → v2 nave between the teams under the platform, twin fronts, 6 ghats per team, 2-high rails, escape steps in every pool; 3.8 viewers / 37 % hidden |
| **Witchwood Isles** (twin islands, cauldron lagoon, seed 3131) | island Babel | server-loaded | an anchor mound under each platform end; footbridges must run shore to shore (one ended 4 short); painted seabed fades deep → shallows → glow; `water_damage 5` (rate unmeasured) |
| **Wicker King's Harvest** (pumpkin island, seed 1031) | island Babel | server-loaded | players enjoyed it; mock-up as island shape; gate oaks/silos as spawn cover; sky layer rules; cosmetic stem placed after mirroring |
| **Backyard Babel v5** (Grounded-style yard, toy dollhouse) | Babel | server-loaded | packed centre, flank ring, passable periphery, no flat ground, plants with 3 details, unique set pieces; open fronts → 0 % hidden spawns (trade-off) |
| **Graveyard of the Forgotten — The Bone Cathedral** (seed 1313) | ground Babel | client-inspected (BetterSpades) | one basin level for spawns, fronts, courtyards (no descents needed); bone-gate arch breaks sightlines to the back of the spawn; live cap_limit = config default |
| **The Hollow Crown** (ruined citadel, seed 1347) | ground Babel | server-loaded + bots | Crown Gate arch on the fronts is OK (opening); "every building real" v1.1 + interiors test 120/120; art metrics in band |
| **Death Swamp** (seed 6613) | Push | server-loaded + bots | first push; gaps 14–16; channels clamped 6..249; painted water with ink halos; AI spawn coords unavoidable for Push |
| **Haunted Fairground** (on Ruins.vxl layout) | island Babel | server-loaded | no platform in the VXL; contested central building with switchback stairwells per side; Ferris wheel as secondary point; bright fog + dark palette |
| **Ferrari's Revenge / Skull River** | Babel | parser-validated | ground height relative to water as a parameter; explorable skull easter egg; ruined-castle spawns around the square |
| **Royal Parade Halloween** (edit of Bradley & Mile's map) | Babel edit | built | keep community maps "relatively the same": carriages for cars, jack-o'-lanterns at spawn |
| **1river2night v2.2** (edit) | Babel recolour | parser-validated | DARK grade; glow-block format; "too black" vs "too bright" — median luma ~24 accepted |
| **Bikini Atoll (Detonation)** (edit of IAmYourFriend's push map) | Push recolour | parser-validated | realistic mushroom cloud = mostly smoke with fire in creases; 0 voxels changed |
| **Silverpine Hunt v1 → v2.2** (werewolf snow forest, seed 1030) | Babel | server-loaded | v1 "slightly ugly, too noisy" → baked lighting, continuous cover, groves, sculpted ring mountains, better lodge; then denser top-ground centre over the underground den |
| Concept docs | — | specified | Grimspire Pass, Leviathan Lagoon, Brimstone Atoll, Spinline, babel_concepts_v1 (in the project) |

---

## 18. Reference-map measurements `[RUN]`

### 18.1 Babel spawn exposure (platform-edge eyes → spawn heads, fog ignored)
| map (guide verdict) | exposed % | viewers / spot | angle | spawn z |
|---|---|---|---|---|
| tradeoff — "spawncamp hell" | 96 / 95 | **61** | 0.7° | 2 |
| abridgetoodark — staple | 100 / 100 | 56 | 1.3° | 3 |
| anticbridgebabelv2 — works (cap 20) | 67 / 62 | 16 | 8.3° | 12–14 |
| waterfrontv2babel | 100 / 100 | 13 | 15.9° | 26 |
| battlefarm — "kind of open" | 97 / 100 | 9.0 | 31.6° | 56 |
| swag2 — "too open but works" | 97 / 99 | 8.6 | 34.4° | 61 |
| islandbabel | 100 / 100 | 9.0 | 34.4° | 61 |
| babelpocalypse — "open but not too bad" | 87 / 81 | 7.8 | 25.2° | 44 |
| normandie — protected spawn | 90 / 96 | 8.2 | 33.5° | 58–60 |
| alexandria-babel2 — works | 95 / 93 | 7.9 | 33.1° | 58 |
| GoonassaultJapan — "open spawn" | 86 / 88 | 7.9 | 34.9° | 62 |
| hallweebalohabeta | 59 / 72 | 7.2 | 31.5° | 62 |
| TowerDive — "spawn camp paradise" (water + hard building) | 62 / 63 | 5.1 | 31.4° | 57 |

Ours: Drowned Cathedral 3.8 / 37 % hidden; Wicker King 7.4 / 18.8 %; Silverpine 6.9 / 21.8 %; Hollow Crown 0.0 / 100 %;
Backyard Babel 0 % hidden (open fronts).

### 18.2 Island / full-map stats
| map | water | landmasses | spawn z | under platform | rough gap | notes |
|---|---|---|---|---|---|---|
| swag2 | 76 % | 3 | 61 | building to z 27 | 43 | butterfly island, tombstone field, ring of plank-bridged islets |
| islandbabel | 80 % | 6 | 61 | z 61 | ~56 | sand, cyan sea |
| babelpocalypse | 63 %¹ | 11¹ | 44 | hill to z 9 | ~8 | |
| toast² | 80 % | 1 | 62 | z 62 sand, lagoon; palms to z 28 | ~60 from ground | palm dumbbell, 2 plank bridges, caustic sea; 9–10 % water under the platform ends |
| utopia2² | 75 % | 3 | 52–53 | plateau z ~53, house to z 34 | ~50 from ground | cliff plateau, one house, cloud layer at z 0–28, painted shallows/deeps |
| alexandria-babel2 | 69 % | 4 | 58 | pyramid | ~4 | |
| GoonassaultJapan | 87 % | 1 | 62 | tower to z 11 | ~15 | spawn squares partly water |
| normandie | 0 % | — | 59/60 | z 59 | ~36 | not mirrored yet fair; 94 % solid underground |
| alpine | 0 % | — | 58/52 | peak to z 9 | ~8 | central mountain, serpentine roads |
| battlefarm | 0 % | — | 56 | barn to z 32 | ~31 | |
| remus | 6 % | — | 60/57 | z 62 | — | dense city, river |
| hallweebalohabeta | 21 % | — | 62 | z 3 | ~4 | Halloween city, good cover |
| Cloud Smash | sky | — | z 8–23 | — | — | exact mirror, painted sunset backdrop, 4 tethers |

¹ These earlier babelpocalypse cells used "land = topmost voxel above z 62", which counts its floating clouds and planes
as land. With the engine's water definition (z 62 air; `tools/island_style_metrics.py`, 2026-11-15), it is 70.8 %
water and 9 landmasses ≥ 200 columns. islandbabel's 80 % / 6 is unchanged under both definitions (80.6 % / 6).
² Measured 2026-11-15 with `tools/island_style_metrics.py`. The gap is rough, `[DERIVED]` from ground under the platform
to z 1. Full classic-vs-current tables: `docs/classic_island_style.md` §2.

---

## 19. Legacy heightmap + colourmap workflow (Build and Shoot tutorials, Influx 2013) `[GUIDE]`

* Two 512 × 512 images (24-bit BMP): heightmap (column height) + colourmap (top colour), combined by Bildramer's converter
  (`converth.exe`); props then added in VOXED.
* "Heightmaps are much more important than colourmaps — that's where maps are made or broken."
* Height counted in layers: layer 0 = water (z 63), layer 1 = unbreakable (z 62); lowest ground at layer ≥ 3 (2 blocks of
  digging); never above ~layer 50 where building matters.
* Grey conventions differ by one level between tools (pyspades editor h = (r+g+b)/12; Bildramer one level lower) —
  test with known greys first `[OPEN]`.
* Colourmap: hard-edged roads (pencil), dirt borders grown 3 px, grunge overlays ~48 % opacity, HSV noise on base colours
  (no hue/sat noise on greys); seamless edges.
* Heightmap: draw each level as its own flat region, contour by contour; valleys between hills, slight rises to advance
  unseen; avoid big single-level areas; adjacent levels too close = walls.
* Our generators terrace the same way (contour-step terrain is the community norm). Adopted defaults: ground ≥ height 3
  (z ≤ 60), building terrain ≤ height ~50, hard road edges with 2–4-voxel dirty borders, wear as blurred overlays.

---

## 20. Open questions `[OPEN]`

1. In-client confirmation of jump height, step-up, crouch tunnels and fall damage.
2. OpenSpades inspection of any project map.
3. Whether the owner's live server's babel_script platform differs from stock.
4. `water_damage` per-tick rate (client-driven position updates) — needed before choosing values for "cursed" seas.
5. Whether the target server runs a glow script; how `heavens_color` is consumed.
6. Whether 0.75 clients show the map tiled at its edges.
7. Hallway / custom modes / building arena need real scripts.
8. Client FPS on the densest maps (5 MB, 566k surface voxels).
9. Assist-structure Babel (§8.8): confirm it runs on the target server's babel_script unchanged; find by playtest which
   assist gaps (0 vs a few blocks) keep rounds from ending too fast.

---

## 21. Sources

* piqueserver / pyspades **1.4.2** (tag v1.4.2, commit e555d210, 2026-07-08): pyspades/vxl_c.cpp, vxl.pyx, world_c.cpp,
  player.py, server.py; piqueserver/map.py, server.py, player.py, game_modes/{babel,push,arena}.py,
  scripts/{babel_script,map_extensions,onectf}.py — https://github.com/piqueserver/piqueserver
* OpenSpades master ff9b3e7 (2024-06-02): GameMap.cpp, GameMapWrapper. BetterSpades master a695aaa (2025-07-30) + libvxl.
* D-VXLMapPreview — https://github.com/rakiru/D-VXLMapPreview · alohacraft.cc · aos.party
* VXL format — https://www.piqueserver.org/aosprotocol/mapformat.html
* piqueserver docs — https://docs.piqueserver.org/en/latest/included-gamemodes.html ,
  https://docs.piqueserver.org/en/latest/configuration.html
* *Babel map rotations guide* v1.8 (aloha.pk, Snailmcsnailton, Feb 2023) — project file
* Influx, *How To: Create Colourmaps / Custom Heightmaps in GIMP* (Build and Shoot, 2013) — PDF prints
* 36 project reference VXLs + Cloud Smash `.txt`; owner's aos_web client; project specs in `claude/*.md`
