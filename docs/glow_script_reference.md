# Glow script reference (aloha.pk `glow.py` v0.1, by Mile)

Status: **reference only, read in source `[SRC]`** (owner supplied `glow2.py`, 2026-11-15). Nothing here was run.
The script itself is **not stored in this repo**: it is a community redistribution (header: Ace of Spades community +
aloha.pk) and `AGENTS.md` §10 keeps other people's work out of the repo. These notes are the distilled behaviour.

## 1. What it is, and where it runs

* A **PySnip-era Python 2 script** for the aloha.pk server (`has_key`, `from commands import add, alias`, hard-coded
  `/home/aloha/PySnip/base/feature_server/` path, `detectclient.py` dependency).
  It **does not load on stock piqueserver 1.4.2** (our target, `AGENTS.md` §2). On stock, the `.txt` keys
  `glow_enabled` / `glow_stored_colors` are inert and only the light baked into the VXL is visible.
* It makes blocks glow **dynamically while the round is played**: placing or breaking a bright block recolours the
  nearby solid voxels over the network. Voxlap (0.75 classic) clients are excluded (`client_info.client == ord('a')`)
  because they can't take the extra colour updates; they get `is_glow = False`.
* Enabled per map in `map.txt`:
  ```python
  extensions = {'glow_enabled': True, 'glow_stored_colors': {}}
  ```
  `on_map_change` loads `glow_enabled` into `MAP_IS_GLOW` and uses the `glow_stored_colors` dict **by reference** as the
  live `STORED_COLORS` table (so the dict grows during the round).

## 2. Data model

| name | meaning |
|---|---|
| `STORED_COLORS[(x,y,z)] = (r,g,b)` | the voxel's **unlit/original colour**. For a light source it is the source colour itself. |
| `VOXEL_PROC_GLOW[(x,y,z)] = (r,g,b)` | pending recolours; drained one random voxel at a time. |
| light source | a voxel in `STORED_COLORS` with **any channel == 255** (`255 in STORED_COLORS[p]`). |
| lit voxel | any other solid voxel whose current colour is the stored colour plus light. Its channels are clamped to **254**, so a lit voxel can never be mistaken for a source. |

Consequences for the map `.txt` (matches the format already inferred in the knowledge base §11.4):
* `glow_stored_colors` should hold every **source** at its VXL colour, and every **lit** voxel at its *pre-light*
  colour, so a server running the script can undo the light when a source is broken.
* Author sources must have a 255 channel. Nothing else is needed to mark them.
* Black voxels (0,0,0) are skipped by the glow pass.

## 3. Algorithm (constants: radius `value = 7`, `tolerance = 5`)

**Source placed** (`glow_block_user`, in `on_block_build`):
1. Count sources in the box `a±5` (`range(a-5, a+5)`, so −5…+4) → `toleranceVal = 2 + count` (the new source is
   already stored, so a lone source gives 3).
2. For every solid voxel in the box `a±7` with Euclidean distance `d ≤ 7` (and not black):
   `new = old + (source − d/7 × source) / toleranceVal − 1`, per channel, int, clamped 0…254.
   Voxels with all channels < 255 only; sources are left alone. The voxel's original colour is saved to
   `STORED_COLORS` the first time it is lit.
3. The queue is drained by `callLater` at 0.005 s steps (`processvoxels`), random order, each sending `SetColor` +
   `BlockAction` as player id 33 to clients with `is_glow`.

**Plain block placed near sources** (`glownupon_block_user`): the new block is lit by every stored source within
`tolerance 5`, same formula with the *neighbour's* colour and `/toleranceVal − 1`, so a wall built next to a lamp picks
up its light. Drained by `trigger()` at 0.05 s steps.

**Source broken** (`unglow_block_user`): the same formula is subtracted, never going below the stored colour.
Grenade destruction (`GRENADE_DESTROY`) skips the un-glow; the block's `STORED_COLORS` entry is deleted either way.

**Our inferred fit** (`aos_map_design_knowledge.md` §11.4: `stored + source × 0.32 × (1 − d/6.5)`) is the lone-source
case of this: `1/toleranceVal = 1/3 ≈ 0.33`, radius 7 (the script), minus the constant 1. Note that **dense sources
divide each other's strength** in the live script (`toleranceVal` grows with nearby sources), while the VXL bake sums
them. A clamped bake is therefore brighter than the live script would be in a crowded cluster.

## 4. Player-facing controls and limits

| item | behaviour |
|---|---|
| `/glow` | toggles glow for the caller (not for classic clients). The name is added to / removed from `DISABLED_USERS_GLOW` (persisted in `img/userdata/DISABLED_USERS_GLOW.txt` on map change). |
| `/glowmap` | moderator/admin: toggles `MAP_IS_GLOW` for the whole server. |
| `ANTI_LAG_LINE = True`, `ANTI_LAG_LIMIT = 5` | a line build of more than 5 blocks (non-god players) does **not** glow; instead `empty_lights` stores each block 25 darker (`sub = 25`) and queues it. |
| `PALETTE_TOGGLE = True`, `PALETTE_PLAYER` | the 7 player palette colours `(255,31,31) (255,143,31) (255,255,31) (31,255,31) (31,255,255) (31,31,255) (255,31,255)` are **not** glow sources when a player builds them (they return early, before being stored). |

## 5. What this means for our maps

* **Keep source colours off the player palette.** Our source set (255,255,255), (255,95,95), (255,255,95),
  (95,255,255), (255,175,95), (95,255,95) already avoids every `PALETTE_PLAYER` colour, so a player can't fake a lamp
  and the script treats ours as real sources. Don't use a stored source with a 31/143 off-channel.
* **Light clamps at 254**, which confirms the existing rule "nudge lit voxels that clamp onto palette colours by −1":
  the script itself does the same thing (255 is reserved for sources).
* **Radius is 7, falloff linear.** Plan lamps with ~7 voxels of influence; sources closer than ~5 weaken each other in
  the live script. Spread lamps out instead of clustering.
* **Glow reaches built blocks too.** Players who build near a lamp get lit blocks. That is by design, not a bug.
* Use only on servers that run the script (owner's aloha.pk setup). On stock piqueserver the baked light is all there is.
  Voxlap players see baked light only.
* The script does not touch fog or `heavens_color`; those stay separate (`aos_map_design_knowledge.md` §11.1–11.2).

## 6. Open items `[OPEN]`

* Whether the owner's live server still runs this exact version (`v0.1 Public Release`) and `detectclient.py`.
* `glow_stored_colors` size limits on the owner's server (the dict is parsed from `.txt` on map load; hallweebalohabeta's
  size is the largest sample we have).
* The bake in our generators sums sources; the live script divides. Not yet compared on a running server.
