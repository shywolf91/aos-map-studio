# aosmap.kit: the shared map-making kit (2026-11-10)

New maps import from `aosmap/kit/` instead of copying `*_core.py`, `*_check.py`, `*_render.py` and friends into
every `scenes/<map>/` folder. Older generators are left exactly as they were (their maps still rebuild
byte-identical).

## Modules and where each came from

| module | what it does | merged from |
|---|---|---|
| `codec` | `encode` (byte-identical to pyspades 1.4.2 `generate()`), `decode`, `pack_rgb`, `surface_mask`, `pyspades_crosscheck` (generate + 20k sampled voxels) | `gf/hc/wkh/sph_core.py` (near-identical copies), Bloomhop `vxlcore.py` + `vxlenc.c` (Linux `.so`), Haunted Fairground `vxlio.py` + `load.py`, `ww_core.py` |
| `noise` | crc32 seeding, `value_noise2`, `fbm2`, `hash3`, `os_seed()` for vegetation | the cores, Bloomhop `noise.py` |
| `canvas` | `Canvas`: `solid`, `rgb`, `mat`, `H`, `keep`, `glow`, `expect_floating`, `interiors`; `box/carve/hollow_box/cylinder/cone/ellipsoid/line/fill_terrain`, `poly_mask`, face-connected `line_points` | Bloomhop `geo.World`, `gf/hc/wkh_build.poly_mask`, `ds_core.line_voxels`, `aosmap/scene.py` |
| `structures` | `straight_stair` (4 climb room), `switchback_stair`, `spiral_stair`, `door`, `window`, `building` (multi-storey, real doors/windows/stairs, records interiors) | `hc_build` (`stair_run`, `interior`), Bloomhop `builds` (`straight_stair`, `spiral_stair`), Haunted Fairground `stair_flight/stack`, `door`, `windows_on`; `sph_structs` |
| `symmetry` | `mirror_canvas` / `mirror_west_to_east` (`x512` with the column-256 fix, or `x511`), `mirror_mismatch`, `floating_components`, `split_expected`, `remove_orphans`, `standable`, `fill_pits` | `gf_build.mirror_west_to_east`, `ds_core.mirror_x`, the cores' `fold_x`, Bloomhop `remove_orphans`, `wkh/sph_build.cleanup`, `ds_build.remove_debris`, `wkh_terrain.fix_pockets` |
| `color` | `mix/shade/ramp/hex_rgb/luma`, `lighting` (baked light + AO), `bake_glow` (returns `glow_stored_colors`), `team_recolor`, `enforce_brightness` (floors luma ≥ 40, whites ≤ 212), `colour_stats` | Bloomhop `geo.py` + `main.lighting/bake_glow`, `gf/hc/wkh_color`, `ds_color.ramp3`, `sph_color._blend` |
| `veg` | `broadleaf`, `conifer`, `bush`, each with **three random details** and a two-palette blend; `palette_family`; `plant_groves` (groves, `can_place` tests the landing surface and no-prop zones); every plant is pruned to face-connected voxels | `sph_trees`, Bloomhop `veg.py`, `wkh_props.big_tree`, `ww_gen.big_tree` |
| `tag` | `paint_tag`: map name only, on the ground in a corner, levels only the strip under it | `gf/hc_color.paint_tag`, `wkh/sph_main.paint_tag`, Bloomhop `corner_tag`, Haunted Fairground `corner_tag`, `ww_font` |
| `sky` | `moon`, `cloud`, `bird`, `bat`, `stamp`; `place()` searches for a clear spot that meets the rules (≥ 60 from the platform, not over a spawn square, ≥ 8 air below) and records it | `wkh_sky`, `sph_sky`, Bloomhop `sky_decor` |
| `babel_checks` | the full suite → `validation.json` + `summary()` pass/fail table; CLI `python -m aosmap.kit.babel_checks <dir>` | `hc/wkh/sph/gf_check` (Nav, exposure, floating, sky rules, mirror, platform, spawn squares, routes, traps, interiors, build gap), Bloomhop `check.py` (8-neighbour rules, its exposure, anchor step), `aosmap.validate.check_babel`, `aosmap.sightline` |
| `zones` | report-only zone profile (spawn, tower zone / front, centre metrics; fast span-header decoder; LOS, free rays, max-flow crossing width, symmetry type, map class) - definitions in `docs/babel_zone_study.md` | new (2026-11-13, Babel zone study) |
| `probe` | live piqueserver 1.4.2 probe in a temp config dir (platform cells, extensions, fog, intel, 400 spawns per team); CLI `python -m aosmap.kit.probe <dir>` | `server_test/*/scripts/{hc,gf,sph}_probe.py`, `ww_probe.py`, `aosmap.pipeline` |
| `build` | `export` (`.vxl` + `.txt` + `build.json` + `mat.npy`/`terrain_H.npy`), `map_txt`, `check_txt` (owner rules), `glow_extensions`, `determinism_check` | every `*_main.py`, `aosmap/meta.py` |
| `preview` | `topdown`, perspective `view` with fog, `render_dir`; every image is stamped "numpy preview - not a client capture" | `hc/wkh/sph_render.py`, Bloomhop `render.py` |

## Check suite

Every check in AGENTS.md §5 step 5 and knowledge base §15:

| section | rule |
|---|---|
| `reader`, `pyspades` | own reader, re-encode identical, pyspades `generate()` identical or 0/20k mismatches |
| `floating_components`, `sky_layer` | 0 unintended; intentional pieces listed and checked against the sky placement rules |
| `mirror` | solid + material mismatch outside the tag / sky boxes and the cosmetic boxes (`cosmetic_asymmetric_bbox`, or a list `cosmetic_asymmetric_boxes`) (`x512` or `x511`) |
| `platform_volume_voxels`, `platform_margin_voxels`, `ground_under_platform_ends` | platform cells empty, solid ground under both ends |
| `spawn_squares` | top-z histogram, flat share, water columns, **roof columns**, mirror-equal share |
| `routes` | own platform end, enemy spawn (safe and any-drop graphs), custom targets, reachable share |
| `safe_descent` | tower zone reached with drops ≤ 9; share of ground reachable without damaging drops **(new)** |
| `trap_cells`, `exits` | standable cells you can reach but cannot walk back from |
| `interiors` | every recorded room/floor reachable from a spawn and has a way out |
| `flank` | spawn → enemy spawn with the centre band removed (|y − 256| 130–210), north and south **(new)** |
| `build_gap`, `assist_structures` | highest reachable point near the platform; per-structure gap for assist Babel **(new)** |
| `anchors` | enemy-face step and graph walk-on rows; fails only for a raised anchor that can be walked onto **(new)** |
| `periphery` | share of ground columns reachable without building **(new, report only)** |
| `zone_profile` | report-only (no pass/fail): every `aosmap.kit.zones` metric for both teams + mirrored average, centre, routes, map class; compare against the community distributions in `docs/babel_zone_study.md` **(new)** |
| `spawn_exposure` | viewers per spot and hidden share against the ≤ 10 / ≥ 15 % targets; presets `calibrated` (= `aosmap.sightline`, the calibrated model) and `bloomhop` |
| `zone_rules` → `front_dressing` | **pass/fail** (owner rule 2026-11-13): per team, 4–15 front objects on 5–30 % of the front band, ≥ 90 % of them ≤ 10 tall, every 8-column section ≥ 50 % walkable ground. `build['front_exempt_boxes']` (owner-requested gates) are left out of count/share/height, listed in `front_exempt`, still in the free-share test **(new)** |
| `zone_rules` → `spawn_cover` | **pass/fail**: per team, ≥ 25 % of the enemy-facing ground within 20 of the spawn square rises ≥ 3 above the spawn floor; ≥ 30 % of the rear ground 20–40 behind it does (0–8 / 8–20 rings reported) **(new)** |
| `zone_rules` → `under_platform` | **pass/fail**: strip x 212–300, y 240–271 has 15–45 % object columns and ≥ 25 air between every strip top and the platform; both anchor ends (6 columns under each platform end) top-z range ≤ 1 and 0 object/roof/deck columns **(new)** |
| `zone_rules` → `centre_footprint` | **pass/fail**: median footprint of the objects (≥ 4 cells) touching the central zone x 150–362, y 130–382 ≥ 25 cells **(new)** |

Zone rules: thresholds in `params.ZONE_RULES` (override per call: `run_all(zone_rules={'front': {'objects': (3, 15)}})`).
A zone that is not land (land share < 0.5: water front, sky deck, void strip) is `N/A` with the reason; a declared
`run_all(zone_rules_skip={'rule': 'reason'})` or `build['zone_rules_skip']` is `SKIP` with the reason. Both count as
`ok` in `summary()` but print their status. Objects use `terrain_H` when the map supplies it, otherwise an estimated
ground with gentle relief filtered out; the output says which (`object_ground`). Each FAIL prints the number that
failed and by how much (`babel_checks.format_row`). Definitions: `docs/babel_zone_study.md` §9 "Zone rules".

Route checks are a graph model (3 air to stand, 1-voxel step with 4 voxels of climb room, drops ≤ 9 safe,
≤ 19 survivable), not a collision simulation. `rules='hc'` is the 4-neighbour model of the gf/hc/wkh/sph checkers;
`rules='bloomhop'` is Bloomhop's 8-neighbour model that also requires the landing column to be clear.

## Acceptance (`tools/kit_acceptance.py`) [RUN 2026-11-10]

Each map was rebuilt from its own generator in a scratch dir (all three byte-identical to the released files) and
the kit suite was run with that map's settings:

| map | legacy values compared | result |
|---|---|---|
| The Hollow Crown v1.1 | 18 (reader, pyspades, floating, mirror solid + material, platform, ends, spawn tops ×2, spawn mirror, routes ×2 incl. 4 custom targets, build gap, exposure ×2, traps, 120 interiors) | 18 / 18 |
| Silverpine Hunt v2.2 | 18 (same set, 3 custom targets, trap band, 3 exits) | 18 / 18 |
| Bloomhop Kingdom v1.0 | 14 (re-encode, z63, floating, platform, spawn squares ×2, mirror, routes ×2, build gap ×2, anchor step, exposure ×2) | 14 / 14 |

Finding: Bloomhop's old `check.py` measured red spawn exposure on x 373–413 (the 511 − x mirror of blue's square),
but the stock server spawns red at 394 ± 20 = x 374–414 (the live probe confirms x 374–414). On the real square,
red is 3.85 viewers per spot and 30.8 % hidden (old report: 3.51 and 32.2 %). It still meets the targets. The kit
reproduces the old number exactly when given the old square.

New checks on the three maps: flank routes exist both ways; safe-descent share 100 %; Bloomhop anchors raised with
a 3-voxel sheer enemy face and 0 walk-on rows; Bloomhop has 23 trap cells (old report had no trap check: a pocket
near (125–129, 451–452, z 44) and one near (253–256, 417–419, z 45)).

## Using it

`scenes/kit_example/kit_example_main.py` is a working template: SPEC dict → terrain → anchors → an enterable house
→ groves (OS seed saved) → orphan cleanup → mirror → lighting → brightness rules → tag → export → checks. Same seed
gives the same SHA-256 in a fresh process. Its open spawns fail the exposure targets, as a graybox should report.

```bash
python scenes/kit_example/kit_example_main.py out/kit_example 12345
python -m aosmap.kit.babel_checks out/kit_example --out out/kit_example/validation.json
python -m aosmap.kit.probe out/kit_example --mode babel
python -m aosmap.kit.preview out/kit_example
```

Open: `structures.switchback_stair` and `spiral_stair` are ported but have no interiors test yet; Push / CTF
check suites still live in `aosmap.validate` (`check_push`).
