# Classic island map — style guide

Status: **researched** (2026-11-15). No map has been built in this style yet. Every number below comes from
`tools/island_style_metrics.py` or `aosmap/sightline.py` run on 2026-11-15 `[RUN]`, unless it is tagged otherwise.

## 1. Trigger and decision

**Owner, 2026-11-15** `[USER]`, verbatim:
> "when we make island maps i want our current style of island map plus a more classic version as attached. when
> "classic island map" is specified make a more classic island map."

He attached utopia2, islandbabel, babelpocalypse and toast (community maps: the **classic** style) and yulehaven_isles
(one of our own recent island maps: the **current** style).

**What it means** (confirmed by the owner the same day):
* Island maps now come in two named styles.
* **Current** is our dense, authored house style (yulehaven_isles, Wicker King's Harvest, Sunken Reef Atoll). It stays
  the default for an island brief.
* **Classic** is used when the brief says **"classic island map"**. It means one natural island in a painted sea with
  sparse, simple props, as described in this guide.

* Build **only the style the brief names**: one map per brief, not both versions `[USER]` (asked and answered
  2026-11-15: "Only the named one").

The reference maps are other people's work. Measure them locally from `refs/`; never copy them, their objects, their
landmarks or their terrain into the repo or into a map.

## 2. Reference measurements `[RUN]`

Tool: `python tools/island_style_metrics.py <maps…> --json out.json`. Spawn exposure: `aosmap.sightline.babel_spawn_report`.
Definitions are in the tool's docstring. The ones that matter here:
* **Land** is a column whose solid run from z 63 reaches z 62 or higher. **Water** is a column whose z 62 is air,
  which is the engine's definition (`docs/vxl_and_runtime_reference.md` §2) `[SRC]`.
* **Terrain** is the height field after a 17-column grey opening, so trunks and huts are removed.
* **Structure** means grounded solid voxels at least 2 above the terrain. This counts trees, huts, ships and bridges together.
* **Floating** means not 6-connected to z ≥ 62. These are clouds, planes and leaf fragments.

In all five maps the sea is a painted z 63 plane. Every column whose ground top is z 60–62 is sand, dirt, rock or snow
coloured, never water coloured. So z 62 counts as land: it is a 1-high beach that the player stands on above the water.

### 2.1 Character

| map | style | one-line character (from the renders) |
|---|---|---|
| islandbabel | classic | flat sand island, two lobes joined by a long neck, sandbag rings and palms, two tall ships and small boats, flat cyan sea, "ISLAND babel" tag painted on the sea |
| toast | classic | one palm-ringed dumbbell island: two sand plazas with palm groves between them, a shallow lagoon in the middle, two plank bridges, caustic-painted sea; painted tag reads "Toast By JoJoe Stinky" |
| utopia2 | classic | one rectangular grassy plateau with cliffs, a single red-roofed house, scattered small trees, two palm islets, heavy cloud layer, painted sea with sand shallows and dark deeps |
| babelpocalypse | classic | one green hourglass island on a raised plateau (spawn z 44), grey bunkers, a central keep on a hill under the platform, palm/pine islets with piers, two ships, a snowman, three planes and clouds in the sky |
| yulehaven_isles | **current** (contrast) | two dense snowy town islands and a central islet, a ring of plank-bridged islets, many real buildings, piers, ships, lighthouse, sky decor, tag |
| wicker_kings_harvest v1 | **current** (second contrast, ours, `maps/`) | one round pumpkin island packed with set pieces |

### 2.2 Layout

| metric | islandbabel | toast | utopia2 | babelpocalypse | yulehaven | wicker |
|---|---|---|---|---|---|---|
| file size (MB) | 2.17 | 2.27 | 2.48 | 2.65 | 2.59 | 2.43 |
| water % | 80.6 | 80.1 | 75.1 | 70.8 | 64.8 | 48.7 |
| landmasses ≥ 200 cols (specks < 200) | 6 (93) | 1 (0) | 3 (0) | 9 (36) | 20 (193) | 1 |
| main island share of land % | 92.8 | 100 | 89.3 | 86.5 | 85.1 | 99.0 |
| main island bbox x / y | 4–508 / 127–341 | 65–446 / 172–369 | 50–461 / 125–365 | 35–476 / 178–356 | 30–482 / 150–367 | — |
| main aspect x/y | 2.35 | 1.93 | 1.71 | 2.47 | 2.08 | 1.07 |
| main fill of bbox % | 43.4 | 69.1 | 58.8 | 83.8 | 79.4 | — |
| neck: min y width, middle third | 56 | 64 | 142 | 47 | 4 | 370 |
| lobe: max y width | 160 | 198 | 188 | 178 | 218 | — |
| terrain height med / p90 / max | 1 / 2 / 3 | 2 / 5 / 10 | 9 / 17 / 22 | 17 / 20 / 31 | 9 / 16 / 20 | — |
| terrain slope (mean \|Δh\|) | 0.018 | 0.117 | 0.209 | 0.263 | 0.195 | 0.251 |
| cliff steps ≥ 3 % | 0.00 | 0.03 | 0.34 | 0.38 | 0.57 | 1.57 |
| shore profile: median terrain h at 1 / 4 / 8 / 16 / 32 from water | 1/1/1/1/2 | 0/2/4/4/1 | 1/2/4/9/14 | 1/6/12/17/19 | 1/3/4/10/15 | — |
| beach ring (≤ 6 from water) at h ≤ 2 % | 100 | 73.9 | 82.5 | 40.9 | 67.7 | — |
| x-mirror agreement, land cols (axis) | 0.38 (511−x) | 0.97 (511−x) | 0.94 (511−x) | 0.83 (511−x) | 0.88 (512−x) | 0.99 |

### 2.3 Detail density, palette, sea, sky

| metric | islandbabel | toast | utopia2 | babelpocalypse | yulehaven | wicker |
|---|---|---|---|---|---|---|
| structure components ≥ 20 vox | 46 | 63 | 59 | 72 | 127 | 261 |
| structure voxels per land column | 0.33 | 1.29 | 1.21 | 1.69 | 1.96 | 0.60 |
| structure footprint % of land | 7.6 | 38.7 | 34.0 | 18.2 | 41.9 | 18.9 |
| structure footprint % of centre zone (x 81–431, y 156–356) | 3.4 | 26.5 | 28.8 | 18.8 | 31.6 | 11.9 |
| roofed land columns % | 5.3 | 9.8 | 6.8 | 10.2 | 21.2 | 7.3 |
| authored surface colours | 14,681 | 9,808 | 1,962 | 22,414 | 45,665 | 8,945 |
| hue families (90 %) | 1 | 3 | 4 | 4 | 7 | 3 |
| sea-plane colours | 31,023 | 14,785 | 245 | 9,542 | 959 | 690 |
| sea L* std / halo (L* near − far) | 3.5 / +4.2 | 5.9 / −0.1 | 19.0 / +12.2 | 3.6 / −0.9 | 6.6 / +9.9 | — |
| land top luma p5 / med / p95 | 126 / 153 / 172 | 101 / 182 / 220 | 26 / 133 / 234 | 78 / 138 / 223 | 71 / 93 / 182 | — |
| floating comps (voxels, z range) | 3 (51, 47–60) | 571 (1,573, 34–48) | 16 (201,898, 0–28) | 73 (133,255, 0–41) | 12 (7,687, 4–12) | 0 |

The toast floating count is leaf fragments, 2.8 voxels per component on average. The utopia2 and babelpocalypse
counts are their cloud and plane layers.

### 2.4 Stock Babel checks

| check | islandbabel | toast | utopia2 | babelpocalypse | yulehaven |
|---|---|---|---|---|---|
| spawn squares land % (blue / red) | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 | 100 / 100 |
| spawn ground z (median) | 61 / 61 | 62 / 62 | 53 / 53 | 44 / 44 | 48 / 48 |
| spawn-square cols with something > 2 high above an air gap % | 1.1 / 0.2 | 0.1 / 0.0 | 4.5 / 3.2 | 22.8 / 22.5 | 0 / 0 |
| ground under platform ends, land % (blue / red) | 100 / 100 | 90.6 / 90.1 | 100 / 100 | 100 / 100 | 100 / 100 |
| solid voxels z ≤ 2 (whole map / over platform) | 0 / 0 | 0 / 0 | 5,265 / 0 | 1,250 / 0 | 0 / 0 |
| spawn exposure: exposed % (t1 / t2) | 99.8 / 100 | 100 / 100 | 95.7 / 97.1 | 87.1 / 81.0 | 99.5 / 98.9 |
| platform viewers per spawn spot | 8.8 / 9.3 | 9.1 / 9.2 | 8.7 / 9.2 | 8.0 / 7.5 | 10.0 / 9.6 |

Corrections to the earlier first-pass numbers, which used "land = topmost voxel above z 62":
* That rule counts clouds and planes as land, so babelpocalypse read 63 % water and 11 landmasses.
* It counts z 62 beaches as water, so toast's spawn squares read as almost all water and islandbabel's red square as 80 % land.
* With the engine's water definition, all four classic refs have **fully land spawn squares**. Toast's spawns sit on a
  1-high z 62 beach, and z ≥ 62 is unbuildable and indestructible `[SRC]`, so players can't dig in there.

## 3. Classic vs current

| aspect | classic (4 community refs) | current (yulehaven_isles; Wicker for contrast) |
|---|---|---|
| shape | **one** dominant island along x, often a dumbbell (two lobes + neck 47–64 wide) or a plain slab; 1–9 landmasses ≥ 200 cols | yulehaven: two town islands + central islet + a ring of bridged islets (20 landmasses ≥ 200 cols, neck 4); Wicker: one round island (aspect 1.07) |
| water / land share | 70.8–80.6 % sea | 64.8 % (yulehaven), 48.7 % (Wicker) |
| terrain | natural height field, smooth blobby coast, no terraces or streets; flat (islandbabel max 3) to plateau with cliffs (utopia2, babelpocalypse); slope 0.02–0.26 | similar slope (0.20–0.25) but more cliff steps (0.57–1.57 %), streets, quays, plazas |
| palette | 1–4 hue families; 1,962–22,414 surface colours; one material per zone with fine noise or soft height bands | 7 hue families, 45,665 colours (yulehaven); Wicker 3 / 8,945 |
| sea | painted z 63 plane is a big share of the identity: flat cyan with fine noise (islandbabel, 31k colours), caustics (toast), shallows + deeps (utopia2, L* std 19) | painted dark sea with halos (yulehaven 959 colours, halo +9.9) |
| props | repeated simple vocabulary: palms, pines, sandbag rings, bunkers, piers, 1–2 ships; 46–72 structure components | 127 (yulehaven) – 261 (Wicker) components; many one-offs |
| buildings | 0–~10 simple huts/bunkers; roofed land 5–10 % | many real buildings; roofed 21 % (yulehaven) |
| landmarks | 0–2 modest ones (utopia2 house; babelpocalypse keep + snowman) | several per map |
| sky | often a cloud layer and/or planes (utopia2, babelpocalypse); islandbabel and toast have none | opt-in sky decor (yulehaven has some) |
| detail density | 0.33–1.69 structure voxels per land column | 1.96 (yulehaven); 0.60 (Wicker) |
| file size | 2.2–2.7 MB | 2.4–2.6 MB: **does not separate the styles** |

What the measurements say:
* Most of the difference is in **layout and prop count**: water share, one landmass with a neck, number of structures, roofed share.
* Palette is the other difference: hue families and colour count.
* Detail per column only separates yulehaven. Wicker King's Harvest is as sparse per column as the classic refs, but
  it has 261 separate pieces on one round island. So "classic" is not just "less stuff".

## 4. Classic target ranges (used by the tool)

`[DERIVED]` from the four classic refs' envelope, rounded outward. "Separates" means yulehaven falls outside the range.
Only one contrast map was used to set this (Wicker was measured afterwards as a check), so treat the ranges as a first
calibration, not a definition. The refs fall inside their own envelope by construction, so they don't prove anything.

| metric | classic range | yulehaven | wicker | separates? |
|---|---|---|---|---|
| water % | 68–84 | 64.8 ✗ | 48.7 ✗ | yes (weak, 6 points) |
| landmasses ≥ 200 cols | 1–10 | 20 ✗ | 1 ✓ | yes |
| neck: min y width | 40–150 | 4 ✗ | 370 ✗ | yes |
| structure components | 0–90 | 127 ✗ | 261 ✗ | yes |
| structure voxels per land column | 0–1.8 | 1.96 ✗ | 0.60 ✓ | yes (yulehaven only) |
| roofed land columns % | 0–13 | 21.2 ✗ | 7.3 ✓ | yes (yulehaven only) |
| authored surface colours | ≤ 26,000 | 45,665 ✗ | 8,945 ✓ | yes (yulehaven only) |
| hue families (90 %) | 1–4 | 7 ✗ | 3 ✓ | yes (yulehaven only) |
| main share, aspect, slope, cliff %, footprint %, sea colours, mirror | info only | — | — | no: the refs spread too widely, or yulehaven sits inside |

## 5. Recipe for a classic island map `[DESIGN]`

These numbers come from the refs (§2) and do not copy any of their shapes.

1. **Footprint.** One main island, 50–65 k land columns (refs 47–66 k), bbox about 380–505 × 180–240 (x × y), aspect 1.7–2.5.
   Pick a shape:
   * (a) a **dumbbell**: two team lobes 160–200 wide in y, joined by a neck 45–65 wide (islandbabel, toast);
   * (b) a **slab or hourglass**: a broad rectangle with a waist (utopia2, babelpocalypse);
   * (c) a **crescent or bent dumbbell**, our own option, not in the refs.

   Add 0–6 satellite islets of 300–3,500 columns and sandbars on the flanks. Keep sea at 70–80 % of the map.
2. **Height profile.** Smooth fBm or blurred-blob height field, no terraces or contour steps. Choose a low island
   (terrain max 3–10, spawns z 61–62, islandbabel/toast) or a plateau (spawn z 44–53, terrain max 20–30 with a 2–6
   column cliff band; utopia2/babelpocalypse). Terrain slope ≤ 0.3, cliff steps ≤ 0.5 %. The owner likes low ground,
   ~3–10 above water (knowledge base §8.5), which favours the low island.
3. **Shore band.** A beach ring 4–8 columns wide at h 0–2 that rises inland. The refs reach h 4 at 8 columns
   (toast/utopia2), or rise faster to h 12 (babelpocalypse). Measure `beach_ring_low_pct` (refs 41–100 %).
4. **Palette.** 2–4 hue families. Build it as one material per height or zone band: wet sand → dry sand → grass/dune →
   rock. Use soft gradients along height and distance-to-shore plus fine per-voxel noise (±2–4 %). No patchwork.
   Aim for ≤ 26 k surface colours.
5. **Painted sea** (knowledge base §10.3, Cloud Smash technique; `Scene.paint_bottom()`). This is half the look.
   * Paint a depth gradient from the distance-to-land field: pale turquoise shallows (≤ ~12 from shore) → mid → deep.
   * Paint reef and sandbar patches in the shallows.
   * Use low-amplitude caustic noise or a warped cellular pattern (domain-warped, per §10.3).
   * The refs range from flat noise (islandbabel, sea L* std 3.5) to a strong halo (utopia2, +12 L*). Aim for a
     visible halo of +5 … +12 L* near the shore.
6. **Props.** A small, repeated vocabulary of 2–4 kinds, 40–90 structure components in all:
   * palms or pines, in groves along the coast and between the lobes (toast's ring);
   * low sandbag rings or bunkers;
   * piers to the islets;
   * 1–2 moored ships or boats on the flanks, outside the fronts.

   Keep under 1.8 structure voxels per land column and ≤ 13 % roofed land columns. Vegetation still follows §6(a).
7. **Landmarks.** At most one or two modest ones: a house, a keep on a hill, a lighthouse, one quirky object. Neutral
   on the centre line or as a mirrored pair. A landmark under the platform shortens the build gap; measure it
   (babelpocalypse ~8).
8. **Sky.** None by default. A cloud layer or planes are a classic signature, but sky decor is **opt-in**, so ask (§6(a)).
9. **Tag.** The map name painted on the sea plane in a free corner (islandbabel and toast do this). It fits the owner's
   corner-tag rule (name only).
10. **Fog.** Bright, with a hue absent from the palette and neutral between blue and red. Sand plus a turquoise sea
    leaves lilac or mauve free (knowledge base §11.1).

## 6. How the owner's standing rules apply (AGENTS.md §4)

### (a) Unchanged and non-negotiable

| rule | how it applies to classic |
|---|---|
| Always ask before building; offer three concepts | unchanged; add the §7 questions |
| All Babel `[SRC]` facts (platform x 206–305 / y 240–271 / z 1, bases, ±20 spawn squares, build ban, destroy rule, intel) | unchanged |
| Never put the platform in the VXL; keep z ≤ 2 clear above it | unchanged. utopia2 (5,265) and babelpocalypse (1,250) have clouds at z ≤ 2 elsewhere; none over the platform. Keep sky decor ≥ 60 away anyway |
| Spawn squares fully land, clear, gentle, no roofs | unchanged. babelpocalypse has something > 2 high over an air gap in 22.8 % of its square columns; don't copy that |
| Solid ground under both platform ends | unchanged. Toast has 9–10 % water under its ends (lagoon); a classic map still needs full anchor ground |
| No stairs on the enemy-facing side of anchors; open fronts; no default screens or raised tower zone; no authored ramp | unchanged; classic layouts satisfy these naturally |
| Safe way down from spawn to tower zone and ground | unchanged; matters for the plateau variant (cliff band needs ramps or ghats) |
| Ground solid to the bottom, seabed foundations under islands | unchanged |
| Fog ≥ ~150, hue not in palette, neutral; not too white (snow max channel ~212), floors luma ≥ 40 | unchanged. utopia2's land p5 luma is 26 (cliff shadows), below our floor rule |
| `author = 'shywolf91 + AI'`; corner tag = name only; no AI spawn hooks | unchanged |
| Floating pieces opt-in | unchanged. Clouds and planes are classic, but **ask**; if used, follow knowledge base §11.3 |
| Every structure that exists is real and enterable | unchanged. Classic has few buildings, and each one is real (doors, rooms, stairs); a bunker is a real room, not a solid block |
| Vegetation: non-deterministic seed saved in build.json, groves, gradients, three random details per plant | unchanged. Classic simplicity lives in **layout and density**, not in crude plants |
| Beauty is the top priority; never copy the refs' objects, landmarks or terrain | unchanged. "Classic" names a style, not permission to reproduce islandbabel or toast |
| Keep versions side by side; validate twice; status ladder | unchanged |

### (b) Rules in tension with the classic look

Each reconciliation below is `[DESIGN]` and `[OPEN]` until the owner confirms it. No owner rule is dropped.

| rule | tension | proposed reconciliation |
|---|---|---|
| Don't leave the centre empty; pack the ~300–400 × 150–250 zone (2026-10-28) | classic centres are open: islandbabel puts 3.4 % of the centre zone under structure, babelpocalypse 18.8 %, yulehaven 31.6 % | Fill the centre with **gameplay terrain** rather than buildings: dunes, a palm grove belt, a lagoon with sandbars, one modest landmark under or near the platform. Target 15–30 % structure footprint in the centre zone (toast/utopia2 level). Ask whether "classic" relaxes this rule. |
| Loves unique one-off objects | classic uses a repeated vocabulary with 0–2 landmarks | Allow 1–2 one-offs as the landmark budget (babelpocalypse's snowman is the precedent), plus small hidden easter eggs that don't add clutter. Ask how many he wants. |
| Flank route 130–210 from centre along the edges | a classic island is ~380–450 wide in x and ~180–240 in y. 130–210 from (256,256) in y lands in the sea or on the islets | Carry the flanks on the **satellite islets and sandbars** (walkable shallows, `water_damage` 0) or on the island's beach ring where the lobes are wide enough (y ± 90–120). Ask whether wading flanks are acceptable. |
| Spawn exposure ≤ ~10 viewers per spot, ≥ 15 % hidden | all classic refs meet the viewer target (7.5–9.3) but hide only 0–19 % (islandbabel 0.2 %, toast 0 %, utopia2 3–4 %, babelpocalypse 13–19 %); open low islands are fully visible from the platform | Cover from palm/pine groves and dune ridges **outside** the ±20 square on the platform side, as on our other maps; or a plateau spawn (babelpocalypse) whose cliff lip hides part of the square. Report the measured trade-off; don't silently accept 0 % hidden. |
| Every area gets artistic detail; spread structures | classic has big empty sand or grass expanses | Detail goes into the **ground and sea paint** (gradients, wet-sand lines, tide pools, reefs) rather than objects; keep the periphery passable. |
| No flat expanses (knowledge base §10.6, Backyard Babel) | islandbabel's terrain is 1–3 high everywhere | Gentle low-amplitude dunes (h 1–6), never perfectly flat; spawn squares gently rolling. |

### (c) Zone rules added on main, 2026-11-10 / 2026-11-13

This guide was written before these rules were merged, so they were not measured on the classic refs `[OPEN]`.
They apply to a classic island map like every other standing rule (AGENTS.md §4, `docs/babel_zone_study.md`):

| rule | effect on a classic island |
|---|---|
| Dress the front, never block it: 4–15 low objects on 5–30 % of the front, 90 % ≤ 10 tall, every 8-column section ≥ 50 % free | fits the classic prop set (low bunkers, sandbag rings, bushes, rocks, boats on the sand). The front may not be bare sand. Tall palms count against the height target, so keep palm groves beside the front, not on it |
| Don't leave the strip under the platform bare: low objects on 15–45 % of x 212–300, y 240–271, ≥ 25 air to the platform | on a low island (ground z ~61) the air target is easy. A lagoon or neck under the platform needs low objects on it, and the anchor ground stays flat and prop-free |
| Anchor the centre with room-sized pieces: median object footprint ≥ 25 cells | pulls against "sparse props". Meet it with a few larger simple pieces (a hut, a wreck, a rock outcrop) instead of many small ones; it also suits the 0–2 landmark budget |
| Fronts must not be completely flat and empty | same reconciliation as §6(b) "no flat expanses": gentle dunes plus the low objects above |

Measure these with the kit's zone checks on the first classic build and report any that fail.

Where the classic refs break our rules (do not imitate):
* **toast**: water under the platform ends (9–10 %); palms reaching z 28 under the platform; 571 floating leaf fragments.
* **babelpocalypse**: things standing in the spawn squares (22.8 % of square columns have something > 2 high above an air gap); sky decor at z ≤ 2 (not over the platform).
* **utopia2**: clouds at z 0–2; land p5 luma 26 (< 40); land max channel p99 253 (near white).
* **islandbabel**: weak mirror (0.38 on land columns); 0.2 % of spawn spots hidden.

## 7. Questions to ask before a classic island map

These add to knowledge base §14 step 2. The ask-first rule still applies.
1. Island shape: dumbbell with a neck, slab/hourglass, or crescent? Low island (spawns z ~61) or plateau (spawns z ~44–53)?
2. Climate and palette: tropical sand/palm, temperate grass/pine, snow (≤ 212 max channel), desert?
3. Sea look: flat calm, caustics, shallows halo with reefs, night sea?
4. Landmark budget: none, one, or two? Which (house, keep, lighthouse, wreck)? Any one-off object?
5. Centre: does "classic" relax the "don't leave the centre empty" rule, or should the centre carry dunes, groves and a landmark?
6. Flanks: walkable shallows and islets (`water_damage` 0), or cursed water with the flank on the island itself?
7. Sky: clouds, planes, birds, or nothing (opt-in)?
8. Ships or boats moored on the flanks?

## 8. Validation

Run the normal checklist (knowledge base §15, `aos_map.md` §12) plus:
```
python tools/island_style_metrics.py maps/<map>_vN/<map>.vxl --json maps/<map>_vN/island_style.json
```
* Report the classic comparison table in the map's spec.
* The 8 separating metrics (§4) should all be in range. Explain any that aren't.
* The "info" rows are context only.
* The tool's Babel block repeats the stock checks: spawn squares land, platform ends, z ≤ 2. It does not replace
  `check_babel`, `spawn_exposure`, the route graph or a server load.
