# Toolchain, Route Checker and Art Kit (2026-10-12)

## Viewing maps in the user's client (aos_web)
`tools/aosweb_capture.cjs <map.vxl> <outdir> <views.json>` drives the user's Ruby/Opal aos_web client
(offline "Open VXL map" mode) in headless Chromium and screenshots camera views. Views use AoS eye
coordinates (z down); the client maps AoS (x, y, z) → three.js (x, 63 − z, y). Setup used: Ruby 3.3.6,
webrick from GitHub v1.9.1 (rubygems blocked here), libenet7, Playwright Chromium. Software WebGL is
slow on detailed maps: render distance 160, viewport 1100×640, and the script releases its bridge
session (the bridge allows 4). `bin/probe.rb aos://<ip-int>:<port>` also joined the headless server
as a spectator and received the map and its `.txt` fog colour.

## Route checker (`aosmap/nav.py`) — preliminary
Standing = 3 air voxels above a solid voxel (2 = crouch-only, ×3.3 cost); moves to 8 neighbours;
1-voxel auto-step; 2-voxel "jump" edges (needs in-client confirmation); drops ≥10 flagged as damaging,
≥20 excluded as lethal; water nodes excluded when water_damage. No building modelled — exactly what
shortcut checks need. Verified on the diagnostic course (ledges 1/2/3, tunnels 3/2, drops 10/20).
Reports: `babel_route_check` (platform reachable without building? build gap per team),
`ctf_route_parity` (walk cost spawn → objective per team, ratio).

## Art calibration (`tools/art_metrics.py`) — measured on the user's references
| target | reference range | why |
|---|---|---|
| hue families (90 % of surface) | 2–5 → aim 2–4 | restrained palettes |
| spatial coherence of top colour (dL@4 / dL@1) | 1.4–2.5 (per-voxel jitter = 1.0) | variation must be structured, not noise |
| side faces vs tops | −5 … −34 L* → aim −10 … −20 | hand-shaded depth |
| shading style | flat painted (Shenlong 184 colours, 74 % equal neighbours, ~11 L* steps) or fine gradients (tradeoff/alpine/alexandria, steps ~1–2 L*) | choose one per material |

## Art kit (`aosmap/art.py`)
* `value_noise` / `fbm` — deterministic, seedable, smooth.
* `ramp(stops, t, steps)` — linear-light colour ramps; `steps` for flat painted bands.
* `SurfaceShader` — top vs side vs underside ramps, height term, coherent noise, baked crevice darkening; plug into `Material(shader=...)`.
* `heightfield(... terrace, shore_z, terrace_cover)` + `apply_heightfield(... cliff_mid)` — patchy stepped contours, sloped shorelines, rock on steep faces; every column filled to z 62 (grounded).
* Prefabs: `tree` (face-connected trunk/branches/crown; 0 of 200 crownless after fix), `boulder`, `house` (gabled, eaves, windows), `stairs` (1-voxel risers). `stamp()` places them on a floor voxel.
* `Scene.paint_bottom()` — painted z = 63 backdrop (Cloud Smash technique).
Showcase (`scenes/kit_showcase.py`): 0 floating components, coherence 1.38, 3 hue families, sides −15.6 L*.
