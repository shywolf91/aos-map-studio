# Janjira Sound v1: [recreate] of newfort by JoJoe Stinky (2026-11-16)

**Status:** specified · generated · exported · parser-validated (own reader round trip byte-identical; pyspades 1.4.2
`generate()` byte-identical) · **server-loaded** (piqueserver 1.4.2, `game_modes.babel` + `babel_script`, probe below) ·
**not** client-inspected · **not** playtested. Every view in this report is a numpy preview, not a client capture.

Credit: the layout this map recreates is *newfort* by **JoJoe Stinky**. The `.txt` description says so.

Owner answers (2026-11-15, `docs/knowledge/project_memory.md`):
1. Distance: "faithful but mixture of your recommend and beautified". Read as the same islands, causeway and two-fort
   layout, with the Reimagine fixes (spawn squares, anchors, real forts) and a full art pass.
2. Style: classic island (`docs/classic_island_style.md`).
3. Theme: "try something new but keep to number 1".
4. Symmetry: left to Claude. The original 180° rotation is kept.
5. Water: walkable.
6. `boundary_damage`: kept.
7. Extras: decided by Claude from the theme.
8. Name: picked by Claude.

Concept picked: **B "Janjira Sound"** (Konkan sea forts, basalt walls, domed bastions, banyan and coconut groves,
monsoon sea; a beached dhow and a stepped well as landmarks; heavens_color storm violet-grey; a few glow lamps; no sky
layer). "Do your recommend". The owner raised no objection to wading flanks, to a terrain-and-grove centre, or to
keeping the rotation symmetry.

## 1. Original (newfort.vxl + newfort.txt)
| item | value |
|---|---|
| SHA-256 | `c5a521f35e5b2cad40f8426d66e9239889736a17a28055ad78e781813def3880` (2,251,768 B; not canonical pyspades encoding) |
| `.txt` | name newfort, author JoJoe Stinky, version 1; extensions `babel`, `boundary_damage`; no fog, no spawn hooks |
| identity | four wooded islands round a sand causeway on the Babel axis, a fort with two towers at each spawn, two inner towers per side, hut islets at the ends, 83 % sea, 180° rotation symmetry |

### Map DNA, measured `[RUN]` (`out/recreate/newfort/analysis.md`)
* **Mostly sea.** 83.0 % of columns are water. Land sits at z 57–61 (heights 2–6), with knolls to z 54.
* **Symmetry.** 180° rotation (top-z match 96.5 %); not an x-mirror (83 %).
* **Babel faults.**
  * Water under both platform ends (39 / 38 columns), so the anchors are unequal (z 47–63).
  * Spawn squares span z 43–63.
  * 18 % of spawn spots land on roofs and 3.5 % in water.
  * The spawn squares are not equal (23 %).
  * Build gap 46. Spawn exposure 5.5 viewers per spot, 24–29 % hidden (mostly because spots are on roofs).
* **Zones.** The front is packed (object share 0.50, worst section 7 % free). Rear backdrop 0.10–0.13. The strip
  under the platform is 63 % objects, with 120+ prop columns on each anchor end.
* **Art.**
  * 4 hue families.
  * Near-black walkable tops: 7.5 % (darkest luma 12.8).
  * 9.7 % of surface voxels exceed the white cap.
  * 1.4 % of the top view is pure blue.
* **Defects.** 6 floating voxels and 1 sealed air pocket.

### Element ledger
| element | verdict | result in Janjira Sound |
|---|---|---|
| four wooded islands round a causeway | Keep | NW / SW islands + rotated NE / SE, warped natural coasts, knolls z 55, banyan and coconut groves |
| sand causeway on the Babel axis | Keep, beautify | x 92–420, lane y 236–276 always land; natural shores (coves to the lane edge, lobes to ~9 out, two sand spits a side), beach ring; worn laterite cart track |
| fort at each spawn | Reimagine | real fort: curtain wall x 86–91 with wall-walk z 47, crenels, casemates, rear gate, two stair flights; corner bastions r 10 with 3 levels, terrace z 39, domed chhatri; gate-bastions r 6 flanking the lane |
| two inner towers per side | Reimagine | round watch towers r 8 at (220,203) / (190,314), terrace z 41, chhatri, mast with pennant (saffron / teal), low yard wall |
| hut islets at the ends | Keep | two islets per side: domed shrine, fisher hut with porch, rear sandbank dune joined by sand bars |
| roof / water spawns | Remove | spawn squares: 0 roof columns, 0 water, z 59–60 |
| water under the platform ends | Remove | flat solid anchor ground z 57, x 200–216 / 296–312, y 240–272, prop-free |
| packed front, packed strip | Replace | 9 low objects on 14.7 % of the front; strip 25.4 % low objects |
| centre | Add | stepped well (baoli) 17 × 17 at (256,256), rack shelters, cannon, boats, crates |
| one-off | Add | beached dhow on its own sandbar (south, asymmetric) with hold, deck, raked mast, furled lateen sail, painted prow eye, stern lantern |
| painted sea | Add | jade shallows haloing every shore → slate-teal deep, wave bands, channel currents, sandbar ghosts, reefs, foam, tide rose |

## 2. Janjira Sound layout (west half authored, rotated (x, y) → (512 − x, 512 − y); z down)
All numbers come from `scenes/janjira_sound/js_spec.py` (`SPEC`).

| zone | where | notes |
|---|---|---|
| spawn squares | x 98–138 / 374–414, y 236–276, z 59–60 | gentle mounds, nothing standing in them, no canopy over them |
| plaza | x 92–150, y 222–290 | packed earth; two shrubs and a keg stack at the corners (spawn cover) |
| fort | wall x 86–91, y 204–308 | wall-walk z 47 with parapet and merlons; 4 casemates (doors 2 × 3); rear gate y 252–260 (4 high); stairs x 92–94 from y 234 → 223 and 278 → 289 |
| corner bastions | (96,204), (96,308), r 10 | floors z 59 / 53 / 47 (door to the wall-walk) / terrace 39; helical stair; chhatri, dome crown z 31, brass finial |
| gate-bastions | (150,226), (150,286), r 6 | terrace z 45, ring-pillar dome; outside the lane |
| causeway | x 92–420 | crest 59 → 57 from x 146 to 200; anchor ground z 57 flat; beach ring z 61–62 |
| front | x 139–199, y 236–276 | two notched garden walls, two cannons, guard hut with kegs, bullock cart, crates, shrub (all ≤ 5 tall) |
| strip under the platform | x 212–300, y 240–271 | rack shelter with net rack, crates, cannon, boat, shrub per side; baoli at the centre (kerb z 56, pool floor z 62) |
| channels | y ≈ 228–234 / 278–284 (shore-following), x 160–247 | 7 wide, wadeable; two spits per side reach in |
| NW / SW islands | blobs at (185,206) and (196,310) + lobes | knolls z 55; watch towers; boat shed; beached boat; field walls; banyan and palm groves |
| west islets | (64,216), (66,296), r 16 | knolls z 53; domed shrine, fisher hut; rear sandbank dune z 54 with palms |
| mid-channel sandbars | (256,196), (256,316) | flat z 62 flank hops |
| dhow | sandbar x 228–284, y 322–348 | one-off after the rotation; mast top z 36; ≥ 51 from the platform |
| boundary | x 32–480, y 160–352 | all land and props inside; `boundary_damage` kept from the original |

* **Palette.** Three hue families cover 90 % of surfaces:
  * warm earth: sand, laterite track and walls, timber, thatch;
  * cool basalt greys;
  * greens.
* **Brightness.** Lime-plaster domes are capped at max channel ≤ 206. Lamps are the only voxels over 212.
* **Fog** (190,184,178). Only 0.05 % of surface voxels are within 12 per channel of it, so the hue is absent from
  the palette.
* **`heavens_color`** (124,116,146,255).
* **Glow.** 23 warm lamps (255,175,95), all existing voxels recoloured:
  * bastion doorways;
  * wall-walk braziers on merlon tops;
  * the islet shrine doors;
  * 4 baoli corner lamps;
  * the dhow stern lantern.

  4,226 lit voxels are stored in `glow_stored_colors`.
* **Vegetation.** 9 banyans and 6 palms per side with this seed.
  * Banyan details: figs, prayer ribbons, nest, dead limb, trunk moss, root tint.
  * Palm details: coconuts, dry frond, trunk rings, shoot, fallen nut.
  * Each plant gets three random details, and per-plant hues with a lighter top and cooler underside.
* **Corner tag.** "JANJIRA SOUND" painted on the sea in the NW corner; no credit line.

## 3. Validation (final build, sha256 `866d4704…580820`, veg seed 132910545)
| check | result |
|---|---|
| reader round trip / pyspades `generate()` | identical / identical; z 63 solid |
| deterministic rebuild (veg seed 132910545) | same SHA-256 in two fresh processes; `.txt` identical |
| art pass geometry | solid array asserted unchanged (build.json `art.solid_unchanged`) |
| floating | 0 (none before cleanup either) |
| rotation mismatch (solid + material) | 0 outside the dhow box `[228,284,322,348]` |
| platform volume / z ≤ 3 within 1 column | 0 / 0; live probe: platform 3,200 cells |
| ground under both platform ends | z 57, 0 water, range 0; anchors x 200–216 / 296–312 flat z 57, 0 prop columns |
| spawn squares | z 59–60, 0 roof, 0 water, mirror-equal under rotation 1.0; live probe 400 spawns per team: blue z 60 ×272 / 59 ×128, red z 60 ×275 / 59 ×125, all inside x 98–138 / 374–414, y 236–276 |
| build gap | **53 / 53** (2-tier crate stack under the platform, top z 55) |
| platform reachable on foot | no |
| enemy-face walk-on steps on raised anchors | n/a (anchors not raised) |
| safe descent | tower zone 30 / 31 steps; 100 % of reachable ground without damaging drops |
| traps | 0 |
| interiors | 62 / 62 reachable with a way out (casemates, wall-walks, every bastion and tower level and terrace, shrine, hut, guard huts, boat shed, rack shelters, baoli, dhow hold and deck) |
| spawn ↔ spawn | 236 / 236 steps (same as newfort) |
| flank (kit band 130–210) | passes, but only through sea outside the boundary box |
| flank on the islands (\|y − 256\| ≥ 50–70 in x 176–336, inside the boundary) | exists both ways, 340 steps, needs wading (no dry route) |
| spawn exposure | **9.24 / 9.35 viewers per spot (≤ 10 met); 0 % hidden (≥ 15 % NOT met)**, see §6 |
| zone: front_dressing | PASS: 9 objects, share 0.147, all ≤ 10 tall (max 5), worst 8-column section 0.683 free |
| zone: spawn_cover | PASS: enemy side 0.306, rear backdrop 0.324 |
| zone: under_platform | PASS: share 0.254, ≥ 45 air, anchor ends range 0, 0 prop columns |
| zone: centre_footprint | N/A (central zone land 0.47 < 0.50); measured with the land threshold relaxed: median footprint 97 cells (pass) |
| clearance to the platform (3D / plan) | NW watch towers 43.6 / 25 (the 25 is the low yard wall; the tower body is ≥ 28); SW towers 50.5 / 32.9; gate-bastions 65.5 / 48.1; dhow 72.9 / 59 |
| boundary box | 0 columns outside |
| classic island table | **8 / 8** in range: water 81.0 %, landmasses 4, neck 53, structure components 81, 1.43 structure voxels per land column, roofed 11.2 %, 15,504 surface colours, 3 hue families. Info rows out of range: main share 79.9, aspect 2.74 (the newfort layout) |
| centre-zone structure footprint (classic budget 15–30 %) | 14.8 % with this seed (14.8–15.4 % across the seeds tried) |
| art metrics (`tools/art_metrics.py`, recreate analysis §6) | hue families 3; coherence 2.44; side − top −15.3 L*; neighbour jump 4.2; bright share 0.7 %; pure team hue 0 % / 0 %; darkest walkable luma 65.5 (p1 84.2); near-black walkable 0 %; over the white cap: 23 voxels, all lamps |
| painted sea | 3,361 colours; L* std 10.5; shore halo +31 L* |
| `.txt` | loads through piqueserver `Map`: author `shywolf91 + AI`; no spawn hooks; babel, water_damage 0, boundary_damage, heavens_color, glow_enabled, glow_stored_colors (4,226) |
| live probe (`maps/janjira_sound_v1/probe.json`) | ok: loaded, txt loaded, babel extension, 3,200 platform cells, fog (190,184,178), bases z 59, intel at (256,256,1), boundary_damage present |

## 4. Fidelity (`tools/recreate_analysis.py --compare`)
* **Layout.** Height-field correlation 0.406; equal top z in 80.4 % of columns; mean |Δh| 1.25.
  The layout reads as newfort's: four islands, a causeway, forts at the spawns, towers on the islands, hut islets
  at the ends, the rotation kept.
* **Routes.** The spawn ↔ spawn route is unchanged at 236 / 236 steps.
* **Babel.** The build gap rose from 46 to 53 because the roof perches near the platform are gone. Exposure went from
  5.5 viewers / 24–29 % hidden (roof spawns) to 9.2–9.35 viewers / 0 % hidden (open ground spawns).
* **Art.** Hue families 4 → 3, coherence 1.6 → 2.44, bright share 3.4 → 0.7 %, pure blue 1.42 → 0 %.
* **Problems** 21 → 3. Two of the three are the exposure rows. The third, "spawn squares are not mirrored", comes
  from the tool testing an x-mirror; under the map's rotation the squares are equal (kit check 1.0).

## 5. Problem ledger
| newfort problem | status |
|---|---|
| water under both platform ends, unequal anchors | **fixed**: solid flat z 57 both ends, equal |
| roof spawns 18 %, water spawns 3.5 %, square z 43–63 | **fixed**: 0 / 0, z 59–60 |
| spawn squares unequal (23 %) | **fixed**: equal under the rotation (1.0) |
| 2.9–3.9 % of spawn spots cannot walk to their platform end | **fixed**: all reach it |
| front packed (share 0.50, a section 7 % free) | **fixed**: 0.147, worst section 0.683 free |
| rear backdrop 0.10–0.13 | **fixed**: 0.324 |
| strip 63 % objects, props on the anchor ends | **fixed**: 25.4 %, 0 prop columns |
| 6 floating voxels, 1 sealed pocket, non-canonical file | **fixed**: 0, 0, canonical |
| near-black floors 7.5 %, 9.7 % over the white cap, pure blue 1.4 % | **fixed**: darkest walkable luma 65.5, only lamps over 212, 0 % team hue |
| spawn exposure 24–29 % hidden (from roof spawns) | **regressed** to 0 % hidden; viewers 9.2 (≤ 10). Open-front trade-off, §6 |

## 6. Known risks / test in game
1. **Spawn exposure.** The hidden share is 0 % against the ≥ 15 % target; viewers per spot are 9.24 / 9.35 (≤ 10 is
   met). Only the platform's west-edge eyes see the square, and their rays run along the lane, so only a screen in
   the lane can hide spots.
   * Measured on the built map, a 6-high wall across the whole lane at x 139–140 gives 11.8 % hidden.
   * A 10-high wall gives 24.9 %; a 10-high wall with an 11-wide gap gives 16.3 %.
   * A +4 terrain crest over x 139–150 gives 5.2 %.

   The owner rules forbid blocking the front, so it is left open as built (coordinator decision, 2026-11-16). **The
   trade-off awaits the owner.**
2. **Flanks are wading routes.** The boundary box (x 32–480, y 160–352, kept from newfort) leaves no dry land
   130–210 from the centre. The island flank runs 70–75 from the centre along the islands' outer beaches and has to
   wade the mid channel. The kit's default flank band passes only through sea outside the boundary, where players take
   boundary damage.
3. **Centre zone rule N/A.** The central zone is 47 % land (< 50 %), so `centre_footprint` reports N/A. With the
   threshold relaxed the median footprint is 97 cells (pass). The centre-zone structure footprint is 14.8–15.4 %
   depending on the vegetation seed, right at the classic budget's 15 % floor.
4. **Glow keys are inert on stock piqueserver.** The baked light still shows.
5. **Untested in any client.** Fog, `heavens_color`, the painted sea and the lamps have only been seen in numpy
   previews.
6. **Watch-tower perch.** The NW watch-tower terraces (z 41) sit 25 in plan from the platform footprint (43.6 in 3D).
   Watch whether they become sniper perches over the anchors.
7. **Classic metrics are near their limits** (components 81 of 90, roofed 11.2 of 13 %). Later decoration must
   re-run `tools/island_style_metrics.py`.

## 7. Regenerate
```
. .venv/bin/activate
python scenes/janjira_sound/js_main.py maps/janjira_sound_v1 132910545     # build + checks (~17 s)
python scenes/janjira_sound/js_render.py maps/janjira_sound_v1              # numpy previews
python -m aosmap.kit.babel_checks maps/janjira_sound_v1                     # axis point512 read from build.json
python tools/island_style_metrics.py maps/janjira_sound_v1/janjira_sound.vxl
python tools/art_metrics.py out/art.json maps/janjira_sound_v1/janjira_sound.vxl
python -m aosmap.kit.probe maps/janjira_sound_v1 --mode babel --out maps/janjira_sound_v1/probe.json
python tools/recreate_analysis.py refs/newfort/newfort.vxl --compare maps/janjira_sound_v1/janjira_sound.vxl --out out/recreate/janjira_cmp
```
* The layout seed 20261115 is fixed (`SPEC['layout_seed']`).
* The vegetation seed is drawn from the OS per build and saved in `build.json`; pass it back to rebuild the exact map.
* Code: `scenes/janjira_sound/` (`js_spec`, `js_build`, `js_art`, `js_main`, `js_checks`, `js_render`).
* Rotation support: `aosmap.kit.symmetry` axis `point512`.
