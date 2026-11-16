# Glow script reference (aloha.pk `glow.py` v0.1, by Mile)

Status: **reference only, read in source `[SRC]`**. Nothing here was run on a server.
Two versions were supplied by the owner on 2026-11-15; the **second (piqueserver / Python 3 port) is the current one** and
is described below. Differences from the first (PySnip / Python 2) are in §7.
The script itself is **not stored in this repo**: it is a community redistribution (header: Ace of Spades community +
aloha.pk) and `AGENTS.md` §10 keeps other people's work out of the repo. These notes are the distilled behaviour.

## 1. What it is, and where it runs

* A **piqueserver-style script** (`from piqueserver.commands import command`, `apply_script(protocol, connection,
  config)`, Python 3). API calls checked against the installed piqueserver 1.4.2 `[SRC]`: `client_info` dict,
  `on_client_info`, `send_contained(..., rule=)`, `map.get_color` (returns `None` for air), `map_info.extensions`,
  `@command` all exist. **So it should load on our target server**, unlike the first version.
* Setup requirements on the server:
  * Put it in the scripts folder and list it in `config.toml` `scripts`.
  * The file `./server_data/DISABLED_USERS_GLOW.txt` **must already exist** (path is relative to the working
    directory; it is opened at import, so a missing file stops the script loading). An empty file is enough.
  * Enable it per map in `map.txt`:
    ```python
    extensions = {'glow_enabled': True, 'glow_stored_colors': {}}
    ```
    `on_map_change` reads `glow_enabled` into `MAP_IS_GLOW` and uses the `glow_stored_colors` dict **by reference** as the
    live `STORED_COLORS` table (it grows during the round). A map without `glow_stored_colors` keeps the previous map's table.
* It makes blocks glow **dynamically while the round is played**: placing or breaking a bright block recolours nearby
  solid voxels over the network (`SetColor` + `BlockAction`, player id 33) to clients with `is_glow`.
* Without the script, the `.txt` keys are inert and only the light baked into the VXL is visible.

## 2. Data model

| name | meaning |
|---|---|
| `STORED_COLORS[(x,y,z)] = (r,g,b)` | the voxel's **unlit/original colour**. For a light source it is the source colour itself. |
| `VOXEL_PROC_GLOW[(x,y,z)] = (r,g,b)` | pending recolours; drained one random voxel at a time. |
| light source | a voxel in `STORED_COLORS` with **any channel == 255** (`255 in STORED_COLORS[p]`). |
| lit voxel | any other solid voxel: stored colour plus light, every channel clamped to **254**, so it is never mistaken for a source. |

Consequences for the map `.txt` (matches the format already inferred in the knowledge base §11.4):
* `glow_stored_colors` should hold every **source** at its VXL colour and every **lit** voxel at its *pre-light* colour,
  so the script can undo the light when a source is broken. Keys are `(x, y, z)` tuples (the `.txt` is Python).
* Author sources need a 255 channel. Nothing else marks them.
* Black voxels (0,0,0) are skipped by the glow pass.

## 3. Algorithm (constants: radius `value = 7`, `tolerance = 5`)

**Source placed** (`glow_block_user`, from `on_block_build`):
1. Count stored sources in the box `a±5` (`range(a-5, a+5)`, i.e. −5…+4) → `tolerance_val = 2 + count`. The new source is
   already stored, so a lone source gives 3.
2. For every solid voxel in the box `a±7` with Euclidean distance `d ≤ 7` (not black):
   `new = old + (source − d/7 × source) / tolerance_val − 1` per channel, int, clamped 0…254. The voxel's original
   colour is saved to `STORED_COLORS` the first time it is lit. Voxels with a 255 channel (sources) are left alone.
3. The queue is drained by `callLater` at 0.005 s steps (`process_voxels`), random order.

**Plain (non-255) block placed near sources** (`glownupon_block_user`): the new block is lit by every stored source within
5 voxels, using the *source's* colour, `1/tolerance_val`, falloff over `tolerance 5` (not 7), and the same −1. A wall built
next to a lamp picks up its light. Drained by `trigger()` at 0.05 s steps.

**Source broken** (`unglow_block_user`): the same formula is subtracted, never below the stored colour. Grenade
destruction skips the un-glow. The block's `STORED_COLORS` entry is deleted in both cases.

**Fit to our inferred bake** (`aos_map_design_knowledge.md` §11.4: `stored + source × 0.32 × (1 − d/6.5)`): that is the
lone-source case, `1/3 ≈ 0.33`, radius 7, minus 1. In the live script **dense sources divide each other's strength**
(`tolerance_val` grows with each nearby source), while our VXL bake sums them. A clamped bake in a crowded cluster is
brighter than the live script would make it.

## 4. Player-facing controls and limits

| item | behaviour |
|---|---|
| `/glow` | toggles glow for the caller; refused for "Ace of Spades" (classic) clients. Name is added to / removed from `DISABLED_USERS_GLOW` (written to `./server_data/DISABLED_USERS_GLOW.txt` on every map change). |
| `/glowmap` | moderator/admin: toggles `MAP_IS_GLOW` for the whole server. |
| `ANTI_LAG_LINE = True`, `ANTI_LAG_LIMIT = 5` | a line build of more than 5 blocks (non-god) does **not** glow: `empty_lights` stores each block 25 darker and queues it. |
| `PALETTE_TOGGLE = True`, `PALETTE_PLAYER` | the 7 player palette colours `(255,31,31) (255,143,31) (255,255,31) (31,255,31) (31,255,255) (31,31,255) (255,31,255)` are **not** sources when a player builds them (early return before they are stored). |

## 5. What this means for our maps

* **Keep source colours off the player palette.** Our source set (255,255,255), (255,95,95), (255,255,95), (95,255,255),
  (255,175,95), (95,255,95) avoids every `PALETTE_PLAYER` colour, so a player can't fake a lamp and the script treats ours as
  real sources. Don't store a source with a 31 or 143 off-channel.
* **Light clamps at 254**, which confirms our rule "nudge lit voxels that clamp onto palette colours by −1".
* **Radius 7, linear falloff.** Plan lamps with ~7 voxels of influence; sources closer than ~5 weaken each other in the
  live script, so spread lamps out.
* **Glow reaches built blocks too.** Players who build near a lamp get lit blocks. That is by design.
* On servers without the script, the baked light is all there is. Fog and `heavens_color` are separate
  (`aos_map_design_knowledge.md` §11.1–11.2).

## 6. Things to watch `[DERIVED]`

* **Classic-client detection probably doesn't fire.** `is_glow` is only set to `False` in `on_client_info`, and
  piqueserver 1.4.2 calls that only after a `VersionResponse` (`pyspades/player.py:706–734`). A vanilla 0.75 client
  doesn't send one, so it keeps the default `is_glow = True` and still receives glow updates. `/glow` does refuse it
  correctly, because the missing `client` key defaults to "Ace of Spades". Client `'a'` is named "ACE" by piqueserver
  and is treated as glow-capable. Unverified on a live server.
* Dense lamp clusters: see §3 (strength division). Test lamp spacing on a running server before tuning the bake.
* A missing `server_data/DISABLED_USERS_GLOW.txt` stops the script at import.

## 7. Changes from the first (PySnip / Python 2) version

* Python 3 / piqueserver API: `@command`, `.get()` instead of `has_key`, `BlockAction()` created per voxel instead of the
  old global `block_action`, no hard-coded `/home/aloha/...` path, no `detectclient.py` dependency.
* Classic detection moved from `client == ord('a')` (in `on_spawn`) to the `client_info` dict (in `on_client_info`).
* `color is None` guards in `on_block_build` and `on_line_build` (they return without calling the parent hook).
* `process_voxels` also clamps the colour to 0…255 before `make_color`.
* The glow maths is unchanged. The `/ tolerance_val - 1` precedence is now written explicitly but evaluates the same.

## 8. Open items `[OPEN]`

* Whether the owner's live server runs this version and where `server_data/` points.
* `glow_stored_colors` size limits on the owner's server (hallweebalohabeta's size is our largest sample).
* Compare our summed bake with the live script's divided strength on a running server.
