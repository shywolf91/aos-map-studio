# VXL + Runtime Technical Reference (source-verified)

Target: piqueserver/pyspades **1.4.2** (tag v1.4.2, commit e555d210, 2026-07-08), Python 3.11.
Clients read: OpenSpades master ff9b3e7 (2024-06-02), BetterSpades master a695aaa (2025-07-30) + libvxl.
Research date: 2026-10-12. Every row cites the file it was read from. **[SRC]** = read in source,
**[RUN]** = observed by running that code, **[DERIVED]** = computed from source equations, not playtested.

Supersedes the "unresolved" items of the Phase 1 research report (questions 2–5, 8–9).

## 1. Format

| Fact | Evidence |
|---|---|
| 512×512 columns × 64; x,y 0..511; z 0..63, **z=0 = top of sky**, z=63 bottom | pyspades/vxl_c.h MAP_X/Y/Z [SRC] |
| File order: y outer, x inner; no header | vxl_c.cpp load_vxl / save_vxl loops [SRC] |
| Span = N,S,E,A + colours; N=0 last span; E inclusive; bottom colours end at next span's A | vxl_c.cpp load_vxl [SRC]; OpenSpades GameMap::Load identical [SRC] |
| Colour = little-endian 0xAARRGGBB (bytes B,G,R,A) | vxl_c.cpp write_color [SRC] |
| **4th byte is cosmetic shade only.** pyspades make_color writes 0x80; update_shadows writes 127-occlusion; OpenSpades replaces it with 100; BetterSpades/libvxl masks `& 0xFFFFFF` | vxl.pyx, vxl_c.cpp, OpenSpades GameMap.cpp swapColor, libvxl.c [SRC]; reference maps carry 127/109/37, 128, 255, 100, 168 [RUN] |
| Surface rule: solid and (z==0 or any in-map face neighbour air); out-of-map x/y and below z=63 count as solid | vxl_c.cpp is_surface [SRC] |
| pyspades writer emits **zero-length top runs (E = S−1)** for buried caves; every pyspades server sends these to clients | vxl_c.cpp save_vxl [SRC]; reproduced in tests [RUN] |
| Hidden voxels carry no colour after a pyspades load; get_point() reports (0,0,0) for them | vxl.pyx get_color / vxl_c.h get_color [SRC] |
| Spec-violating "void column" (S=64, E=63, whole column air incl. z=63) loads and re-emits in pyspades | 10yearsaloha x=0 column line [RUN] |
| OpenSpades copies the z=62 colour to z=63 when z=62 is coloured | GameMap.cpp Load [SRC] |

## 2. Ground, collapse, water

| Fact | Evidence |
|---|---|
| **Grounded = 6-face connected to any solid voxel with z ≥ 62.** Diagonal/edge contact does not count | vxl_c.cpp check_node; BetterSpades map.c (y≤1 ground, DIRECTION_MASK 6); OpenSpades GameMapWrapper roots at z=63 [SRC]; diagnostic diag block = floating [RUN] |
| Collapse runs only around a destroyed voxel (destroy_point → check_node(destroy=True) on 6 neighbours). **No sweep at map load** | vxl.pyx destroy_point; map.py load [SRC] |
| **check_node ignores protection.** Destroying an allowed (player) block next to floating authored geometry deletes the authored geometry | vxl_c.cpp [SRC]; diagnostic: 10 voxels removed incl. 9-voxel authored slab [RUN] |
| Floating geometry is common in shipped maps (JunglePush 740 comps, Shenlong 288, t_o_r_t_u_g_a 118k voxels) | 35-map scan [RUN] |
| **Design policy (user, 2026-10-12): floating pieces are an opt-in feature** — fun and distinctive, used only when a brief asks for them; default authored geometry is grounded. When requested, list them in the scene's `expect_floating` and accept/mitigate the collapse caveat above | user preference |
| Sky maps can stay grounded through a few hidden **tethers**: Cloud Smash hangs its whole cloud level (674k voxels) on four 1–2-voxel stalks to z=62. Cutting any one removes 1 voxel; cutting all four drops the map | pyspades destroy_point on CloudSmash1 [RUN] |
| z ≥ 62 voxels cannot be built or destroyed | pyspades/player.py block handler, vxl.pyx build_point/destroy_point [SRC] |
| Water: column with z=62 air. Player collision treats z=63 as z=62 → player stands at the bottom, "wading" when p.z > 61 | world_c.cpp clipbox, boxclipmove [SRC] |
| `water_damage` (map_extensions) applies when position.z ≥ 61; push forces it to 100 | scripts/map_extensions.py; game_modes/push.py on_map_change [SRC] |

## 3. Player movement (for route validation)

| Quantity | Value | Evidence |
|---|---|---|
| Footprint | 0.9 × 0.9 (±0.45) | world_c.cpp boxclipmove [SRC] |
| Standing height / clearance | ~2.7 → **3 air voxels** | offsets 0.9 + 1.35, try_uncrouch [SRC] |
| Crouched clearance | **2 air voxels** | crouch offsets 0.45 + 0.9 [SRC] |
| Auto step-up | **1 voxel**, only when not crouching, **not sprinting**, not looking steeply down | boxclipmove climb branch [SRC] |
| Jump apex | ~1.6 voxels | move_player v.z = −0.36 [DERIVED] |
| Fall damage | starts ~10 voxels, ≥100 dmg at ~20 voxels | FALL_DAMAGE_VELOCITY 0.58, scalar 4096 [DERIVED] |
| Spawn | hook z = floor voxel; player.spawn subtracts 2.4 | pyspades/player.py spawn [SRC] |

Jump/fall numbers need in-client confirmation (diagnostic scene has 1/2/3 ledges, 3/2 tunnels, 10/20 drops).

## 4. Metadata (`<map>.txt`) — attributes piqueserver reads

`name, version, author, description, extensions, apply_script, time_limit, cap_limit, gen_script,
get_spawn_location(connection), get_entity_location(team, entity_id), on_map_change, on_map_leave,
on_block_destroy(connection, x, y, z, mode), is_indestructable(protocol, x, y, z)` — map.py [SRC];
`fog = (r, g, b)` — server.py set on map change [SRC].

* `on_block_destroy`: **any falsy return (incl. None) denies** the destroy — player.py [SRC].
* Entity ids: BLUE_FLAG 0, GREEN_FLAG 1, BLUE_BASE 2, GREEN_BASE 3; team.id 0 = team1, 1 = team2, −1 spectator [SRC].
* Default CTF placement without hooks: random **land column** (z=62 solid) in x 0–127 (team1) / 384–511 (team2), y 128–383, at the **topmost** solid voxel → can land on roofs — team.py, vxl_c.cpp get_random_point [SRC].
* map_extensions keys: `water_damage`, `boundary_damage {left,right,top,bottom,damage}`, `disabled_commands` [SRC].
* **Entities settle**: at map load and after every block change, `update_entities` drops each flag/base onto the **topmost solid voxel** of its column (or lifts it out if buried). The z a hook returns barely matters; a roof or overhang above an intel/base x,y will catch it — pyspades/server.py update_entities [SRC + RUN].
* A hook returning `None` falls back to default placement (random land column in the team's default zone) — piqueserver/server.py FeatureTeam [SRC]. Cloud Smash's `.txt` tests `GREEN_BASE` twice, so GREEN_FLAG returns None and green's intel is random every reset [RUN].
* `extensions` only matters for keys some script reads. `'user_blocks_only': True` inside `extensions` (Cloud Smash) has **no effect** in stock 1.4.2; it is a server config option [SRC grep].
* Loader quirk: piqueserver/map.py uses `importlib.util` without importing it. A normal server run has it loaded already; standalone test harnesses must `import importlib.util` first or the `.txt` silently fails ("Error while loading map info") [RUN].

## 5. Protection

* **`user_blocks_only = true`** (server config) exists in 1.4.2: every block not in `protocol.user_blocks` is indestructible; player-built blocks are destructible by **anyone** (no team ownership) — server.py:144, 355, 589 [SRC].
* Grenade is cancelled entirely if **any** of its 27 voxels is indestructible; spade checks z±1 too — piqueserver/player.py on_block_destroy [SRC].
* user_blocks is in-memory; collapse-removed user blocks stay listed (harmless stale entries) [SRC].
* **Consequence:** under user_blocks_only, authored geometry is safe from direct damage, but only **grounded** authored geometry is safe from collapse griefing (§2).

## 6. Mode specifics (1.4.2)

| Mode | Verified rules that constrain map authoring |
|---|---|
| Push | Required keys `push_blue_spawn, push_green_spawn, push_blue_cp, push_green_cp` (raises otherwise); optional `push_spawn_range` (5), `push_cp_protect_range` (8), `push_blue/green_build_area` (x1,y1,x2,y2). Ownership is **by colour**: a voxel whose byte-HLS hue+saturation equals a team colour counts as that team's block; `protect_map_blocks` protects everything else. **Authored palettes must avoid team H/S** (defaults config.toml (0,0,255)/(0,255,0); any r=g=0 blue or r=b=0 green shade collides). The enemy intel is placed at your spawn x,y with z=1 and **settles onto the topmost surface there** — keep spawn and CP columns free of roofs/overhangs [SRC + RUN]. User template (`aosmap.validate.push_extensions`): `{'push': True, 'push_spawn_range': 5, 'push_blue_spawn': (x,y,z), 'push_blue_cp': (x,y,z), 'push_green_spawn': …, 'push_green_cp': …, 'water_damage': 100}` — `'push': True` is the documented convention; 1.4.2 push.py does not read it (the mode comes from config `game_mode`). `check_push()` validates spawn squares, intel/CP settling and team-colour clashes. |
| Babel (`babel` + `babel_script`) | Platform is **script-generated** at z=1, x 206–305, y 240–271, colour (0,255,255), protected; bases fixed at (118,256) and (394,256), spawns ±20; intel at platform ends z=0; cap_limit forced 1. A player can't build while standing near the enemy's tower (team1: x 301–384, team2: x 128–211; y 240–272) and can't spade own-team blocks while standing in their own corridor; a team can destroy blocks **with any tool** only once past x 288 (team1) / below x 224 (team2), i.e. not on its own half. Intel returns if dropped off the platform; carrier killed after 150 s. **Maps must leave z ≤ 2 free over the platform area and provide land at both base coordinates.** [SRC] These are module constants, so servers sometimes change the platform's shape/colour (user report): treat them as server parameters (`BABEL_DEFAULT` in `validate.py`) and read the target server's script. Reference babel maps keep the platform volume empty and come in two styles — **sky babel** (abridgetoofar, tradeoff, anticbridgebabelv2: 57–97 % of each ±20 spawn square is a deck at z 2–13) and **ground babel** (alexandria-babel2, islandbabel, babelpocalypse) — with matched spawns (abridgetoofar, tradeoff exact 180° rotations; anticbridgebabelv2 ~0.99 mirror) [RUN]. |
| Arena | `arena_blue_spawns`, `arena_green_spawns` (tuples of tuples; singular legacy keys accepted), `arena_gates` (one coord per gate), `arena_max_spawn_distance`. BUILDING_ENABLED = False (building variant needs a script change). Gates: 6-face flood fill of **exact RGB**; hidden voxels read (0,0,0) so **gates must be ≤ 2 voxels thick**; same-colour decoration touching a gate is absorbed; recursive fill → keep gates < ~900 voxels. Round 180 s, 15 s between rounds [SRC + RUN]. |
| CTF | Built in. Use get_spawn_location/get_entity_location hooks for authored layouts (defaults above). |
| Hallway | A map name in the default rotation comment, not a mode [SRC]. |

## 7. Reference-map lessons (measured, not copied)

**Cloud Smash** (Lostmotel; CTF-style `.txt`, 2.47 MB, canonical pyspades encoding):
* Sky map: all play space at z 8–23 over open water, x 82–429, y 197–306; water_damage 100.
* **Painted backdrop:** the z=63 water plane is a 512×512 sunset-sky painting — 27,994 of the map's 28,109 colours. The playable cloud uses only **111** colours (whites and teal-greys). Cheap, huge visual effect, zero gameplay cost → available as `Scene.paint_bottom()`.
* **Exact mirror across x** (height map 1.000), spawn lists mirrored (x ↔ 511−x), spawn heights identical (mean z 13.27 both sides).
* **Grounding by hidden tethers** (§2): four 1–2-voxel stalks; integrity relies on server-side `user_blocks_only = true`.
* Its `.txt` has two defects in 1.4.2: GREEN_FLAG unhandled (random green intel), and `user_blocks_only` placed in `extensions` (ignored).

## 8. Babel objective (stock 1.4.2, verified in game_modes/babel.py + scripts/babel_script.py)

* **One intel.** babel.py runs onectf in ONE_CTF mode: both flags are placed at `one_ctf_spawn_pos` (default (256, 256); map extension `one_ctf_spawn_pos` overrides) at `get_z`, i.e. on top of the script platform. Taking it hides your own flag; carry it to **your own base** (118,256 / 394,256) to score; cap_limit forced to 1.
* Dropped off the platform → intel returns ("returned to the heavens"); carrier killed after `allowed_intel_hold_time` (150 s).
* Reference **build gap** (closest walkable spot → platform top, from `nav.babel_route_check`): anticbridgebabelv2 6, alexandria-babel2 5 (central tower), tradeoff ~17 (sky decks), abridgetoofar ~54 (bridging), islandbabel ~56 (climb from sea). None reachable without building.

## 9. Protection script `authored_protect` (live-tested 2026-10-12)

Bots joined piqueserver 1.4.2 as real blue/red players (tools/bot_protect_test.py); a spectator then downloaded the server's map to verify voxels.

| Action | stock `user_blocks_only = true` | `authored_protect` |
|---|---|---|
| shoot authored ground | refused | refused |
| red shoots blue's block | destroyed | destroyed |
| blue shoots own block | destroyed | destroyed (or refused with `team_can_destroy_own = false`, tested) |
| red spades blue's block standing on authored ground | **refused** (spade also hits the ground) | block removed, ground intact |
| grenade on blue's blocks next to authored ground | **entire grenade cancelled** | blocks removed, ground intact |

Partial results are sent as individual DESTROY_BLOCK actions so client maps stay in sync. Weapon block damage requires the client's trigger to be held (`weapon.shoot`), as real clients do.
Server under test mirrored the user's: stock 1.4.2, normal script list, team1 blue (0,0,255), team2 red (255,0,0). **Push palette consequence with red team:** avoid pure reds (g = b = 0) as well as pure blues (r = g = 0).
