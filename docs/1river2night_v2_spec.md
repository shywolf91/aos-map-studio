# 1river2night v2 / v2.1 / v2.2 — night recolour + glow blocks (2026-10-27)

Goal (Dylan): keep 1river2night's night mood but drop the "too black" look players dislike; use glow blocks like hallweebalohabeta. Iterations: v2 moonlit (too bright for him) → v2.1 "in between" → **v2.2 current**: "a tad darker, not like the original", with dark fog/sky for a Halloween night-twilight vibe.

**Status (all):** generated · exported · parser-validated (own reader round trip: solid + surface colours identical) · **not** server-loaded · **not** client-inspected · **not** playtested. Views are a numpy raycaster.

## Versions
| version | DARK grade | top-surface median luminance | fog | heavens_color |
|---|---|---|---|---|
| original 2night | — | 3 | ? (no .txt) | ? |
| v2 moonlit | 1.0 | 62 | (118,128,172) | (46,52,96,255) |
| v2.1 | 0.45 | 28 | (118,128,172) | (46,52,96,255) |
| **v2.2** | **0.38** | **24** | **(58,44,86)** dark indigo-violet | **(34,24,58,255)** |
Glow strength is never scaled by DARK, so lanterns pop more as the base darkens. hallweeb median = 47.
Note: v2.2's fog is far below the ~150 brightness Dylan earlier found acceptable — done on his explicit request; check in client.

## Original (measured)
* Babel ground map (1river2X family). Ground z ~55, border mountains to z ~8, N–S river (water z 63), central bridge, cobble road spawn→spawn, walled spawn yards with 2-storey shrine at (97,256)/(428,256), 10 statues, ~240 small trees. Not mirrored exactly (hand-built).
* Colours almost all 0–5 per channel. 1riveralmost2night is the same map at ~13/255, greyed.
* Light was faked with large neon-green pools painted on the grass around statues/lamp spots.

## Glow blocks — what hallweebalohabeta actually contains (inferred from data, no script source found)
* `.txt` extensions: `'glow_enabled': True`, `'glow_stored_colors': {(x,y,z): (r,g,b), …}` (153 473 entries).
* Sources = voxels in a fixed palette whose stored colour equals the VXL colour: (255,255,255), (255,95,95), (255,255,95), (95,255,255), (255,175,95), (95,255,95).
* Every other entry is a voxel near a source: **VXL colour = stored colour + source × 0.32 × (1 − d/6.5)** (additive, linear falloff, d = Euclidean voxel distance, summed over sources, clamped). Fitted on isolated sources; matches to ~1 unit.
* Lighting is **baked into the VXL**; stored colours let a glow-aware server undo/redo it when blocks change. On stock piqueserver the keys are inert but the baked light still shows.

## Changes (all versions)
| item | change |
|---|---|
| palette | teal-green meadow, slate-blue strata mountains with moss, dusky earth banks, night-blue river with N–S ripples, slate cobbles, brick+ivy spawn walls (ivy follows the original's green pattern), moonstone statues/shrines/bridge, two-tone teal trees |
| pools | original pool layout kept as soft light, tinted by nearby glow sources (inverse-distance blend) |
| glow sources (216) | amber lanterns on statue tops, shrine pillar lights (both floors) and spawn gate posts; green beacon on shrine cupolas; cyan wall-corner lanterns; yellow bridge-rail lanterns; cyan ground lights at the 10 old pool centres; cyan river-bank moss every 14 voxels; 52 glow mushrooms (26 per half) |
| geometry | only +52 voxels (mushrooms, 1 voxel each, on grass, off the road); nothing removed; platform volume clear |
| .txt | author 'shywolf91 + AI', babel True, glow_enabled + 21 572 stored colours; fog/heavens per table |

## Open
* Load on server; check fog/heavens in client (dark fog may hide players too much at range).
* Confirm whether the target server runs a glow script (if not, nothing changes visually — light is baked).
* River-bank moss slightly heavier on the east half (61 vs 48 cyan sources); river is off-centre.
* No water_damage set (original .txt unknown).

## Regenerate
`DARK=0.38 python convert.py out/1river2night_v2_2` (seed 1031) + `classify.py`, `vxl.py`, `noise.py`; `poolg.npy` = gaussian σ4 of the original top-surface green channel. The .txt is written from `<out>_stored.pkl`.
