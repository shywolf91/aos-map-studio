# Death Swamp — Push map spec (v1.0, 2026-10-19)

Original Push map inspired by the owner's swamp battle-map screenshot (teal water with dark halos round every
island, olive moss-crusted boulder clusters, bare black dead trees, amber firefly specks) and the name
"Death Swamp". Reference maps used for craft/density only: JunglePush and Shenlong (both push; measured: twin
parallel lanes, 3–4 water gaps of ~10–17 per lane). No objects, landmarks or terrain copied.

**Status:** generated · exported · parser-validated (our reader + pyspades `VXLData.generate()` byte-identical) ·
**server-loaded on live piqueserver 1.4.2 push** (spectator + one bot per team) · eye-level previews from
`tools/fp_view.py` (numpy, **not** a client capture) · **not client-inspected** (BetterSpades/OpenSpades/aos_web) ·
**not playtested**.

## Mode facts used `[SRC]` piqueserver 1.4.2 `game_modes/push.py`
* Each team spawns (random ±`push_spawn_range` around its spawn, topmost voxel) with the **enemy's** intel lying at
  its own spawn; it scores by carrying that intel to its **own** CP. Intel resets 3 min after a drop, or on falling
  into the water plane.
* `push_blue_spawn/cp`, `push_green_spawn/cp` are **required** (the mode raises without them) → this map has to
  ship spawn coordinates even though the owner's general rule is to leave spawn hooks out. No
  `get_spawn_location`/`get_entity_location` hooks are written (push.py installs its own).
* `water_damage` is forced to 100 and map_extensions applies it on every position update at z ≥ 61 → the swamp
  is instantly lethal. Every island gap must be bridged.
* `protect_map_blocks = true` (default): only blocks whose HLS hue+sat equal a team colour are destructible. All
  authored channels are clamped 6..249, so no authored colour can match blue (0,0,255) or red (255,0,0) —
  `check_push` reports 0 hits.
* Can't build within 8 of your own CP; can't build inside the enemy's `push_*_build_area`.

## Layout (blue = west lane; red = exact mirror x' = 511 − x)
| element | blue (west) | notes |
|---|---|---|
| Spawn pad | (170, 462), z 55, 15×15 flagstones + teal rune border | open sky (intel settles at z 55), boulder ridge on the channel side for cover |
| Islands (push order) | S (z 55) → I2 (54) → I3 (56) → I4 (55) → North Isle (53) | plateaus ±1 terraced; banks step down 1 voxel at a time to the water |
| Water gaps (shortest) | 16.0 · 16.1 · 14.0 · 14.0 | references: JunglePush 14–17, Shenlong 8–11 |
| Central channel | 44 water between lanes (lane max x 233) | leviathan ribs stand in it, feet ≥ 9 from any island |
| Control point | (184, 96), z 53 | 23-wide flagstone dais, two rune rings, standing-stone ring with entrances S and E |
| Landmark | leviathan skull on the mirror axis, (255.5, 68) | horns, crest, eye sockets, nostrils, teeth; splits the two CPs |
| Bridgeheads | closest coast points of each gap, kept clear (r 10), flanked by amber-lantern mooring posts | readable "build here" marks |
| Build areas | blue (96,150)–(240,508), red (272,150)–(416,508) | enemy can't build in your lane; channel + North Isle open |
| Corner tag | "DEATH / SWAMP" painted on the water plane, SW corner | name only |

Walk costs inside each island (landing → landing, nav model): S 53.9, I2 70.2, I3 79.9, I4 74.3, N 51.7 — identical
for both teams (mirror mismatch 0 voxels).

## Art
* Palette (hue families: teal water, olive/khaki rock-moss-peat-bone, dark bark, amber accents):
  water deep (58,126,130) / mist (98,164,158) / ink halo (30,62,72); rock (72,72,58)→(160,156,122) with moss caps
  (92,100,48)→(160,154,70); peat with darker bog hollows; bark (52,48,44)→(78,70,60); bone (214,206,174) with algae
  stain toward the waterline; amber lanterns/glowcaps (246,178,70); teal runes (92,156,146).
* Painted z = 63 water (Cloud Smash technique): fbm mist, ink halos (exp falloff 10) round every land column,
  faint ripple rings, clustered algae and lily pads, firefly glints, edge vignette.
* Props: noise-warped boulder mounds (some with the screenshot's dark hollow), dead trees with root flares /
  cypress knees, radiating spiky branches, hanging moss and shelf fungi; drowned-tree groves in the outer swamp;
  six unreachable boulder islets; reeds and cattails on banks; standing stones; mooring lanterns.
* Fog (178,172,192) pale lilac-grey: brightness ≥ 150, absent from the palette, neutral between blue and red.

## Validation (`maps/death_swamp_v1/validation.json`)
| check | result |
|---|---|
| floating components | 0 (4 carve fragments, 19 voxels, auto-removed per half before mirroring) |
| mirror mismatch | 0 voxels |
| `check_push` (spawn squares 11×11, intel settle, CP settle, team colours) | pass: intel settles z 55, tents z 53, 0 team-colour hits |
| spawn → own CP without building | **unreachable** for both teams (nav model; building not modelled) |
| every island's landings connected on foot | yes |
| reader round-trip / pyspades `generate()` | identical / byte-identical |
| determinism | same SHA-256 in a fresh process: `5722dccf…6e9fe5` |
| live server (push, Blue/Red) | map + .txt loaded; fog (178,172,192); team1 flag at red spawn (341,462,55), team2 flag at blue spawn (170,462,55); bases at (184,96,53)/(327,96,53); bots spawned on their pads (eye z 52.6) |
| size | 2.38 MB, 6,097 colours |

## Known limits / risks `[OPEN]`
* Not seen in a real client yet; fp_view previews only approximate colours and fog.
* Cross-channel sightlines: islands at the same y face each other ~44–100 voxels apart (typical push "gallery").
  Mound placement on the inner banks is random-but-mirrored; tune if one stretch plays too exposed.
* The rib arches give a cheap crossing point between lanes for anyone who builds ~9 blocks to a rib foot; with the
  build areas set, an enemy still can't build into your lane, so they only gain a firing position.
* Water trees' root knees (z 62) are standable mini-platforms ≥ 12 from any island and never in a lane gap.
* `cap_limit` on the test server was the server default (10); set it per your rotation.
* Spawn coordinates are AI-authored because push requires them — adjust `push_*_spawn` / `push_*_cp` in the .txt
  if you prefer other spots (keep the intel column free of overhangs).

## Regenerate
```
python scenes/death_swamp/ds_main.py maps/death_swamp_vN            # art build + checks + renders
python scenes/death_swamp/ds_main.py out/death_swamp_graybox --graybox
piqueserver -d server_test/push_ds                                   # maps/ holds death_swamp.vxl + .txt
python tools/babel_live_check.py 32941                               # works for push too (flags/bases/spawns)
```
Seed `ds_core.SEED = 6613`; all numbers live in `ds_layout.SPEC`.
