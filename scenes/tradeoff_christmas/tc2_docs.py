"""Writes docs/tradeoff_christmas_v2_spec.md from build.json + validation.json (run from the repo root)."""
import json

b = json.load(open('maps/tradeoff_christmas_v2/build.json'))
v = json.load(open('maps/tradeoff_christmas_v2/validation.json'))
t = b['tree']
spec = f"""# Tradeoff Christmas v2.0 — spec

Second Christmas version of **Tradeoff** by ei8htx / aloha.pk (v1 kept in `maps/tradeoff_christmas_v1/`, spec
`docs/tradeoff_christmas_spec.md`). Built 2026-11-18 from the owner's feedback: v1 put props on the outer floor, but that
floor is **deadly water** (`water_damage` 25). v2 keeps the water, adds one giant tree in the middle and puts the sky decor
in the outer regions. Inspiration (craft only): the owner's other version `trademas` (topographic snow roofs, ornaments on
the web strands).

**Status ladder:** generated → exported → parser-validated (own reader, pyspades 1.4.2 `generate()` byte-identical, `.txt`
loads with the original hooks). **Not** server-loaded, **not** client-inspected, **not** playtested. Renders are numpy previews.

## Owner decisions `[USER]` (2026-11-18)
* Keep deadly water; no props in the outer regions; sky decor in the outer regions.
* Giant Christmas tree in the middle: "mixture of landmark/below reach and assist". Blue and red towers as before.
* Icy deadly water; keep the original .txt hooks and extensions (water_damage 25, babel, orange heavens/fog, spawn rects, bases).

## Original map `[DERIVED]`
Flat water floor (only z = 63 solid, orange, water_damage 25), two hollow 61-high towers (roof z = 2, floors every 8, 12 shafts),
spawn rects on the tower ends (x 108–128 and 384–404, y 246–266), bases at (118, 256) / (394, 256), Babel flag set. The
"spider web": 10 thin bars at z 9–12 reaching out from the inner curves. The stock Babel platform (z = 1, x 206–305,
y 240–271) hangs over the water gap; nothing original is solid in its volume.

## What changed
| area | change |
|---|---|
| Tower geometry | **none**; only added voxels in the tower footprint: {b['roof_bulbs']} roof-edge fairy-light bulbs (z = 1, none in the spawn rects or near the platform) and 10 hanging baubles under the web tips |
| Tower outer walls | team colour with snow ledges and three rows of garland swags (pine green, coloured bulbs, red bows with gold knots) |
| Roofs | team-tinted snow with topographic contour lines; candy-striped edge ring |
| Web strands | red/white candy canes with a big bauble hanging from each tip |
| Water | cold teal with ripple lines (luma median {v['water_luma_min_median'][1]:.0f}, min {v['water_luma_min_median'][0]:.0f}); still reads as deadly water, no ice floes (they would mislead players) |
| Centre landmark | giant tree on a seabed island at (256, 256): island r 19 (snow top z = 60, step rings z = 61 dry / z = 62 wet), tree {t['height']} high (star at z {t['star_z']}), tinsel / baubles / berries, 7 gift boxes, 3-wide candy-ribbon staircase ({t['stair_steps']} steps, 1 up per step) to a gold landing |
| Sky decor (outer water only) | flying sleigh + 4 reindeer, 8 snow-cloud islands (trees, gifts, baubles), 10 snowflakes; z 6–44 |
| Glow | {b['glow_sources']} sources, {b['glow_lit_voxels']} lit voxels baked; no white sources (dense white washes colours out) |
| Corner tag | "Tradeoff / Christmas" painted on the water floor, bottom-right, no credit line |
| `.txt` | original hooks, `water_damage` 25, `babel`, orange `heavens_color` and fog kept verbatim (not AI-authored); name, version and author (`shywolf91 + AI`) changed, credit to ei8htx in the description; glow keys added |

## Centre tree as assist (Babel `[DESIGN]`)
It stands in the neutral zone (x 206–305, where both teams may build). Build gap to the platform underside (z = 2):
**stair top {v['gap_stair_top_to_platform_underside']} blocks**, **tree top {v['gap_star_to_platform_underside']} blocks**; the star is not a standing
spot. Reaching the island means crossing about 30 voxels of deadly water from either tower (mirror symmetric, equal for both
teams). That saves a lot over building from the water floor (about 60), so treat it as a light assist and shorten the tree if
it proves too strong.

## Validation `[RUN]`
| check | result |
|---|---|
| strict reader / re-encode / pyspades generate identical | OK / identical / {v['pyspades_generate_identical']} |
| z = 63 solid; original voxels removed in the footprint | {v['z63_all_solid']} / {v['removed_original_voxels_in_footprint']} |
| footprint changes outside bulbs + tip baubles | {v['footprint_changes_outside_allowed']} |
| new solid in platform volume (x 196–315, y 230–281, z 0–3) / in spawn rects | {v['new_solid_in_platform_volume']} / {v['new_solid_in_spawn_rects']} |
| props on the outer water (z ≥ 50, outside the island) | {v['props_on_water_outside_island_z>=50']} |
| floating components | {v['floating_total']} (all listed sky pieces; unexpected {v['floating_unexpected_count']}); the original has {v['original_floating_components']} |
| staircase walk (step ≤ 1) from the island edge | reaches feet z {v['walk_from_island_edge_highest_feet_z_reached']} (landing) |
| `.txt` loads (3.11 venv, original hooks present) | yes |

Expected floating (collapse caveat: breaking a player block next to one drops it for the round): sleigh + reindeer, 8 clouds,
10 snowflakes (boxes in `build.json`), all over open water.

## Known limits / not tested
* No live server, no client; water damage rate, glow look and FPS unmeasured. Spawn exposure not measured (spawn rects unchanged).
* Assumes water damage applies at player z ≥ 61: the island top (z = 60) should be dry, the outer step ring (z = 62) is wet.
* The platform checks only cover our additions; the stock script builds the platform.
* Cloud-island tree details are non-deterministic by rule; seed `{b['seed']}` rebuilds this exact map.

## Regenerate
```bash
python scenes/tradeoff_christmas/tc2_build.py <tradeoff.vxl> <tradeoff.txt> maps/tradeoff_christmas_v2 --seed {b['seed']}
<venv>/python scenes/tradeoff_christmas/tc2_check.py maps/tradeoff_christmas_v2/tradeoff_christmas.vxl <tradeoff.vxl> maps/tradeoff_christmas_v2/build.json maps/tradeoff_christmas_v2/validation.json
python scenes/tradeoff_christmas/tc_render.py maps/tradeoff_christmas_v2/tradeoff_christmas.vxl maps/tradeoff_christmas_v2/renders
```
"""
open('docs/tradeoff_christmas_v2_spec.md', 'w', encoding='utf-8').write(spec)

p = 'docs/agents_reference.md'
s = open(p, encoding='utf-8').read()
old = "| Tradeoff Christmas (aloha.pk Tradeoff retheme) | community-map Christmas edit, mode unknown | v1.0 | parser-validated | `scenes/tradeoff_christmas/`, `maps/tradeoff_christmas_v1/`, spec `docs/tradeoff_christmas_spec.md` |"
new = ("| Tradeoff Christmas (ei8htx / aloha.pk Tradeoff retheme) | community-map Christmas edit, Babel (original hooks kept) | v1.0 (floor props, superseded) / v2.0 | parser-validated | "
       "`scenes/tradeoff_christmas/` (`tc_build.py` v1, `tc2_build.py` v2), `maps/tradeoff_christmas_v1/`, `_v2/`, specs `docs/tradeoff_christmas_spec.md`, `docs/tradeoff_christmas_v2_spec.md` |")
assert old in s
open(p, 'w', encoding='utf-8').write(s.replace(old, new))

p = 'docs/knowledge/project_memory.md'
m = open(p, encoding='utf-8').read().rstrip('\n')
m += f"""
- [stated] Tradeoff Christmas feedback (2026-11-18): the outer floor is deadly water (water_damage 25), so no props out there; keep it. Wants a better recreation, a giant Christmas tree in the middle, sky decor in the outer regions; his own version `trademas` is inspiration. Answers: tree = mixture of landmark (below reach) and assist; blue/red towers as before; icy deadly water; keep the original .txt hooks/extensions. Tradeoff's .txt shows Babel, spawn rects on the tower tops, bases at x 118/394, orange heavens/fog, author ei8htx.
- [built] Tradeoff Christmas v2.0 (2026-11-18): parser-validated; water kept, centre tree island with ribbon staircase (gaps to the platform underside: stair top {v['gap_stair_top_to_platform_underside']}, tree top {v['gap_star_to_platform_underside']}), garland murals, candy web strands with baubles, sky decor outside. v1 kept. Not server-loaded or client-inspected.
"""
open(p, 'w', encoding='utf-8').write(m + '\n')
