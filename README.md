# aosmap — prompt-to-VXL map pipeline for classic Ace of Spades 0.75

Python toolkit for authoring, exporting and validating `.vxl` maps for AoS 0.75 clients
(OpenSpades, BetterSpades, vanilla) on **piqueserver 1.4.2**.

**Start with [`aos_map.md`](aos_map.md)** — the knowledge base (VXL format, collapse/protection rules, modes,
metadata, art calibration, workflow, validation checklist, open questions).

## What's in here

| Path | What |
|---|---|
| `maps/kestrel_spires_art_v2/` | Kestrel Spires (Babel) **art v2 — current**, ready to drop into a server's `maps/` |
| `maps/kestrel_spires_art_v1/` | art v1 as first delivered |
| `maps/kestrel_spires_graybox_v1/` | the same layout as a function-coloured graybox |
| `aosmap/` | library: VXL reader/writer, scene + materials, art kit, validators, route graph, metadata, renders |
| `scenes/` | map generators (`kestrel_spires.py` graybox, `kestrel_spires_art.py` art pass) and their `_check` scripts |
| `tools/` | reference comparison, art metrics, movement sim, live-server bots, aos_web screenshot driver |
| `server_scripts/authored_protect.py` | piqueserver script: authored map protected, players build, enemies destroy player blocks |
| `server_test/*/config.toml` | the headless server configs used in testing (kestrel = Babel) |
| `docs/` | detailed references and the Kestrel Spires spec; `docs/img/` renders |
| `tests/` | byte-level VXL tests |

## Setup (Windows, PowerShell)

Python **3.11** is the tested version.

```powershell
cd "D:\Ace of Spades\Aos_Map"
py -3.11 -m venv venv
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\python -m pytest -q tests
```

(Linux/macOS: `python3.11 -m venv venv && venv/bin/pip install -r requirements.txt`.)
`piqueserver` is only needed for the runtime checks and live-server tools; if its wheel won't install on your
Python, the generators and validators still work with `numpy scipy pillow`.

## Make the map yourself

```powershell
.\venv\Scripts\python scenes\kestrel_spires.py out\kestrel_spires            # graybox
.\venv\Scripts\python scenes\kestrel_spires_art.py out\kestrel_spires_art2   # art v2 (same seed -> same bytes; --v1 for v1)
.\venv\Scripts\python scenes\kestrel_spires_check.py out\kestrel_spires_art2 # routes, parity, gaps, perches, floating
.\venv\Scripts\python tools\art_metrics.py out\metrics.json out\kestrel_spires_art2\kestrel_spires.vxl
```
`art_metrics.py` takes the **output JSON first**, then maps.

Things worth playing with:
* `SPEC` in `scenes/kestrel_spires.py` — every layout number (mesa radii, deck height, spire/finger positions,
  stair, river). Change, rebuild, re-check.
* Material colours and shaders near the top of `build()` in `scenes/kestrel_spires_art.py`; the v2 canyon,
  walls, dwellings and outcrops live in `scenes/kestrel_spires_v2.py` (`WASHES` = the wash centre lines).
* `FOG_V2` in `kestrel_spires_art.py` — or try fogs live on a server with `/fog r g b` as admin.
* `SEED` — changes noise, vegetation and prop placement, not the layout.

## Run it on a server

```powershell
copy maps\kestrel_spires_art_v2\* server_test\kestrel\maps\
.\venv\Scripts\piqueserver -d server_test\kestrel          # Babel, port 32921, blue/red
.\venv\Scripts\python tools\babel_live_check.py 32921      # bots: platform, intel, bases, spawns, fog
```
Or copy the two files into your own server's `maps/` and add `kestrel_spires` to its rotation with
`game_mode = "piqueserver.game_modes.babel"` and `piqueserver.scripts.babel_script` in `scripts`.

## Real-client screenshots (Linux)

`tools/betterspades_capture.sh` joins a running server in the real BetterSpades client as a spectator and
screenshots camera positions from a views file (setup steps are in the script header; it needs
`tools/betterspades_camfile.patch` applied to a BetterSpades checkout).

## Coordinates

x, y ∈ 0..511, z ∈ 0..63, **z = 0 is the top of the sky**, z = 63 the bottom (water plane). Height = 63 − z.
`Scene` box ranges are inclusive. Babel maps are authored on the west half and mirrored x' = 512 − x.

## Working alongside Claude

Repo location: `D:\Ace of Spades\Aos_Map`. Claude keeps working in its own copy and drops updates as git
**bundles** into `_updates\` inside this folder (ignored by git). Keep your experiments on your own branch so
updates never clash:

```powershell
git switch -c play                                   # your sandbox branch (once)
git fetch _updates\<name>.bundle main:claude          # bring Claude's latest main in as branch 'claude'
git switch main; git merge --ff-only claude          # update main
git switch play; git merge main                      # pull it into your work when you want
```
If you haven't changed anything, `git pull _updates\<name>.bundle main` on `main` is enough.
To hand your changes back, commit on `play` and say so — Claude can read the folder.

## Pinned environment (what was actually tested, 2026-10-12/13)

| Component | Version |
|---|---|
| Python | 3.11.17 |
| piqueserver / pyspades | 1.4.2 (PyPI cp311 wheel; tag v1.4.2 commit e555d210) |
| numpy / scipy / pillow / pytest | 2.4.6 / 1.17.1 / 10.4.0 / 9.1.1 |
| pyenet / Twisted | 1.3.17 / 26.4.0 |
