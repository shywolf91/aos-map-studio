# AoS map review kit — guide for an AI assistant (ChatGPT or similar)

You are helping a map-making project for **classic Ace of Spades 0.75** (piqueserver 1.4.2 server; OpenSpades /
BetterSpades clients). The project generates original `.vxl` maps from prompts. Your job here is to **measure and
review reference maps** with `vxl_analyzer.py` and write findings in a fixed format (section 7) that we can merge
into the project's knowledge base. You are a reviewer, not a map designer, for this task.

Files you should have: `vxl_analyzer.py` (this kit's analyzer; needs numpy + Pillow, scipy optional) and one or more
`.vxl` maps, sometimes with a same-named `.txt` metadata file.

---

## 1. Run it

In ChatGPT's Python tool, files are uploaded to `/mnt/data`. Process **one map per cell**, because a cell has a time limit. Reading a map takes about 3–8 s, `babel=True` adds about 5–15 s, and `iso=True` adds about 10 s.

```python
import sys; sys.path.insert(0, '/mnt/data')
import vxl_analyzer as va
va.selftest()                                    # prints "selftest ok"
va.run(['/mnt/data/normandie.vxl'], '/mnt/data/analysis', babel=True)   # babel=True for Babel/CTF-style maps
print(open('/mnt/data/analysis/normandie/report.md').read())
```

Then show the pictures:

```python
from PIL import Image
for f in ('top', 'height', 'sides'):
    display(Image.open(f'/mnt/data/analysis/normandie/{f}.png'))
```

Zoom in on anything interesting (landmarks, spawns, mid):

```python
m = va.load('/mnt/data/normandie.vxl')
display(va.iso(m, crop=(180, 200, 330, 310), view=0, s=3))   # x0, y0, x1, y1 inclusive; view 0-3 rotates 90°
print(va.column(m, 256, 256))                                  # solid runs and colours of one column
display(va.side_view(m, 'south'))
```

Finish with a comparison table: `va.run([...all maps...], '/mnt/data/analysis', babel=True)` writes
`summary.md` and `summary.csv`. Zip `/mnt/data/analysis` and offer it as a download.

**If you cannot actually see the rendered images, say so.** In that case, review from `report.md` only: the ASCII height map, the region grid and the numbers. Never describe visual details you did not see.

## 2. Format facts (verified against the piqueserver source; don't contradict them)
* The map is 512 × 512 columns, 64 voxels deep. x and y run 0–511.
* **z = 0 is the top of the sky and z = 63 is the bottom.** Height above water = 63 − z.
* z = 63 is the water plane. It is solid everywhere, and its colour is the water/ground colour. Some maps paint a picture into it; Cloud Smash paints a sunset.
* There is no header. Columns are stored y-major (x varies fastest). Each column is a list of spans: `N S E A` plus colours. Colours are B, G, R plus a shade byte, which clients mostly ignore.
* Voxels between coloured runs are solid but buried, and everything below a column's last span is solid.
* Only **surface** voxels store a colour; buried voxels have none. Renders cut the map open at its edges (and at
  `iso` crop boxes), so buried voxels show there as a **hatched grey "section"** — that is the cut, not map content.
  Black in a render is a real stored black colour.
* The ASCII height map uses 8 x-columns × 16 y-rows per character (monospace cells are ~1:2), so it stays square.
* Images use north up (y = 0 at the top) and west on the left (x = 0).
* Region-grid cells are 64 × 64: A–H run west→east, 1–8 north→south.
* The VXL holds geometry and colours only. Game mode, spawns, intel/tents, fog and protection come from the server, its scripts and the map's `.txt` metadata. A `.txt` file is Python, so the analyzer only reads it as text and never executes it.

## 3. Game facts that matter for review
* **Stock Babel** (piqueserver `babel_script`): the *script* adds a platform at z = 1 over x 206–305, y 240–271.
  * Team bases/tents are fixed at (118, 256) and (394, 256).
  * Players spawn at a random point within ±20 of their base, on the **topmost voxel** of the column. They can therefore spawn on roofs or tree crowns.
  * The intel sits on the platform, and players must build up to reach it.
  * aloha.pk runs custom scripts (platform variants, spawn protection), so a map's `.txt` hooks may matter there but not on a stock server.
* **CTF**: positions come from the map's `.txt` hooks or from server defaults. The analyzer does not know them, so describe the bases you can see, not assumed positions.
* **Push** (Shenlong, Jungle Push): the attackers must build a bridge or route toward the objective, and the map should keep that construction challenge.
* Team layouts are usually mirrored at x' = 512 − x (or 511 − x). The symmetry section measures this.
* Collapse: blocks not 6-face-connected to the ground can fall when damaged. "Floating components" counts those. Some are deliberate (decorative clouds, sky pieces), so judge them in context.

## 4. What the numbers mean, with calibration

**Art metrics** (surfaces above water). Ranges below were measured on references the project considers well made: normandie, remus, tradeoff, alpine, Shenlong, Cloud Smash and others.

| metric | meaning | reference range / our target |
|---|---|---|
| `hue_families_90` | 30° hue bins (plus one grey bin) needed to cover 90 % of the surface | refs 2–5; target 2–4 (restrained palette) |
| `coherence_4` | colour change at 4 voxels ÷ change at 1 voxel. 1.0 = random per-voxel noise; higher = structured gradients/patches | refs 1.4–2.5; target ≥ 1.5 |
| `side_minus_top_L` | median lightness of side faces minus top faces (L*, 0–100) | refs −5 … −34; target −10 … −20. Positive = sides lighter than tops (unusual; see why) |
| `top_equal_neighbour_pct`, `shading_step_dL` | flat-painted style (many equal neighbours, big steps) vs fine gradients (small steps of 1–2 L*) | Shenlong is flat-painted (~74 % equal, ~11 L* steps); tradeoff and alpine use fine gradients |
| `relief_16` | mean height range inside 16 × 16 chunks: terrain articulation | compare between maps |
| `surface_voxels_per_land_column` | vertical detail / structure density | ~1.0 = bare heightfield; higher = buildings, overhangs, vegetation |
| `columns_with_air_gap_pct`, `air_under_surface_mean` | columns with an air gap under solid (occupancy only — colours play no part): caves, hollow crust over water, overhangs, bridges, roofs, tree crowns; and mean air voxels between the surface and the water plane | normandie 5.7 % / 0.2 (solid ground); 1mirror2forts 79 % / 12 (a ~15-voxel crust over a cavern of water) |
| spec checks | bottom-layer holes and surface voxels without colour should be 0; colours stored on buried voxels are harmless | |
| `water_plane_colours` | colours in the z = 63 plane | > 1000 usually means a painted backdrop |

**Babel spawn exposure** (`babel=True`). Eyes are placed on the platform edge and heads on a 2-voxel grid of each spawn square. The check uses straight-line visibility and ignores fog, so it is an upper bound.

Calibration against the aloha.pk *Babel map rotation guide* v1.8 verdicts:

| map (guide verdict) | exposed % | viewers per spawn spot | angle° |
|---|---|---|---|
| tradeoff — "spawncamp hell" | 96 | **61** | 0.7 |
| abridgetoodark — rotation staple | 100 | **56** | 1.3 |
| anticbridgebabelv2 — works | 65 | 16 | 8.3 |
| waterfrontv2babel | 100 | 13 | 15.9 |
| battlefarm — "kind of open, some cover" | 98 | 9.0 | 31.6 |
| swag2 — "too open but works" | 98 | 8.6 | 34.4 |
| normandie — protected spawn | 93 | 8.2 | 33.5 |
| hallweebalohabeta | 66 | 7.2 | 31.5 |
| TowerDive — "spawn camp paradise" (fails for other reasons) | 63 | 5.1 | 31.4 |

"Viewers per spawn spot" separates the cases better than "% exposed":
* Sky-deck spawns level with the platform score 25–60, which is a camping risk.
* Ground maps score about 5–10.
* Good maps also hide a share of spawn spots behind trees, walls or terrain. Hallweeb hides 30–40 %, normandie 5–10 %.

The project's targets are ≤ ~10 viewers per spot, ≥ 15 % of spots hidden, and no open spawn deck level with the platform.

The **Babel geometry** section shows the distance from the nearest map voxel to the platform for each side. That distance is the building challenge, and a large difference between sides is a fairness flag.

## 5. Review procedure (per map)
1. Run the analyzer. Read `report.md` and look at `top.png`, `height.png` and `sides.png`.
2. **Identify the mode and layout.** Use the map name, the `.txt` file and the symmetry numbers. Which axis is mirrored? Where are the bases, the mid and the objectives?
3. **Landmarks.** Find 3–6 things a player would navigate by. For each, give its cell (e.g. D5) and coordinates. Iso-crop each one and describe its construction:
   * silhouette and scale in voxels;
   * materials and colour treatment;
   * how it is supported (grounded or floating).
4. **Gameplay structure.** Cover:
   * routes between bases;
   * chokepoints;
   * cover density;
   * high ground and perches;
   * water and hazards;
   * where players will build;
   * whether spawns are covered from the main threat.

   Use the region grid's `detail` values as a density map.
5. **Craft techniques worth learning.** Note how this map solves its problems:
   * terrain shaping (terraces, cliffs, smooth slopes);
   * colour ramps and height shading;
   * side-face darkening;
   * how buildings are detailed (windows, trims, roofs, interiors);
   * how vegetation is clustered;
   * backdrop painting;
   * how it avoids flat emptiness.

   Describe each as a **reusable technique**, not as a copy of an object.
6. **Problems.** Flag anything you find:
   * colour noise or 1-voxel stripes (flicker);
   * 1 × 1 pillar fields (lag);
   * unsupported pieces;
   * unfair asymmetry;
   * spawn camping;
   * glaring palettes;
   * places players can seal or exploit.
7. Write the **Reference Map Card** (section 7).

## 6. Rules
* Tag every claim with where it came from:
  * `[MEASURED]` — a number from the analyzer;
  * `[SEEN]` — something you saw in a render;
  * `[INFERRED]` — your reasoning;
  * `[UNVERIFIED]` — something you heard or remember.

  Never present in-game behaviour (fun, balance, lag) as measured. The analyzer only sees geometry and colours.
* Write **originality-safe** lessons. Our project must not copy reference maps' objects, landmarks or terrain arrangements. Write "a two-tone stepped roof with 1-voxel eaves reads well at 60 voxels", not "build normandie's church".
* Don't invent format details, metadata keys or server options. If unsure, say so.
* Keep coordinates in map voxels (x, y, z with z = 0 at the top).

## 7. Output format — one card per map (paste back to the project as Markdown)

```markdown
### <map name> — Reference Map Card
- **Mode / layout:** <Babel | CTF | Push | Arena | TDM | unknown> · mirrored on <axis> (<sym %> [MEASURED]) · theme: <…>
- **Key numbers [MEASURED]:** land <%>, height median/max <…>, overhang cols <%>, floating <n>, colours <n>,
  hue families <n>, coherence_4 <…>, side−top L* <…>, relief_16 <…>, detail <…>
  <Babel: spawn viewers t1/t2 <…>, hidden % <…>, nearest voxel to platform W/E <…>/<…>>
- **Layout summary:** 3–5 sentences: bases, mid, routes, chokepoints, elevation story.
- **Landmarks:** • <name> @ <cell, x,y> — <construction notes> [SEEN] …
- **Craft techniques to learn (originality-safe):**
  1. <technique — how it is built — why it works> [SEEN/MEASURED]
  2. …
- **Gameplay observations:** spawns, cover, perches, build spots, hazards [INFERRED unless measured]
- **Problems / risks:** …
- **Rules of thumb for our generator:** 1–3 concrete, testable statements
  (e.g. "dominant terrain hue family ≤ 2 with roads as the neutral third", "buildings 8–14 voxels tall on a 4–8 base relief")
- **Confidence / gaps:** what you could not see or verify
```

After all the maps, add **"Cross-map patterns"**: 5–10 rules of thumb supported by several maps, each citing the maps and numbers behind it. These are the most valuable output for us.

## 8. Maps we already know (for context)
* **Push:** Shenlong, JunglePush.
* **Babel / CTF:** tradeoff, normandie, alpine, abridgetoofar/abridgetoodark, remus, swag2, battlefarm, babelpocalypse, alexandria-babel2, islandbabel, hallweebalohabeta, TowerDive, anticbridgebabelv2, waterfrontv2babel.
* **Arena and other:** spacestationarena, submarinearena, hallway, cs_havana, de_aztecdefusal.
* **Painted-backdrop example:** CloudSmash1.

These are craft references only. Our own maps (Kestrel Spires, Hollowfen, Hollowfen Vale) are original designs.
