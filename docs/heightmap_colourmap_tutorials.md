# Heightmap + colourmap workflow — notes from the Build and Shoot tutorials (read 2026-10-14)

Sources: two forum tutorials by **Influx** (Build and Shoot, July 2013), supplied as PDF prints:

* *How To: Create Colourmaps Using GIMP* — buildandshoot.com/forums/viewtopic.php?f=38&t=4922
* *How To: Create Custom Heightmaps in GIMP* — buildandshoot.com/forums/viewtopic.php?f=38&t=4984

The site itself is blocked from our workspace, so these notes come from the PDFs.

Tags:
* `[GUIDE]` — the tutorial says it.
* `[SRC]` — checked in the piqueserver 1.4.2 source.
* `[RUN]` — we measured it.
* `[OPEN]` — not yet verified.

## How the old pipeline worked
* **Two 512 × 512 images make the terrain.** The heightmap sets each column's height, and the colourmap sets its top colour `[GUIDE]`.
* **Converter:** they are combined into a `.vxl` by *Bildramer's Ace of Spades bitmap converter* (v1.1): `converth.exe` plus `sdl.dll`, run through an edited `example.bat` that names the two images. It writes `map.vxl` `[GUIDE]`.
* **Image format:** save both images as **24-bit BMP**. Other BMP variants scrambled the colours for a forum user `[GUIDE]`.
* **Heightmap first:** "heightmaps are much more important than colourmaps — heightmaps dictate the gameplay and this is mainly where maps are made or broken" `[GUIDE]`.
* **Don't generate from the colourmap alone:** a map built from the colourmap only gets a jagged heightmap `[GUIDE]`.
* **The tools stop at terrain:** props and buildings come afterwards, in VOXED or a similar editor `[GUIDE]`.

## Height scale
* **Layer numbers:** the tutorial counts height in *layers*. Layer 0 is water (z = 63), and layer 1 is the "unbreakable layer" (z = 62) `[GUIDE]`.
  * This matches pyspades. Both `destroy_point` and `build_point` refuse z ≥ 62, and so does `player.py` (`if z >= 62: return`) `[SRC]`.
  * So layer *n* = height *n* = z 63 − n.
* **Digging room:** the tutorial puts its lowest ground on **layer 3**, which leaves "2 blocks of digging space until you hit layer 1" `[GUIDE]`.
* **Height cap:** its guide only goes up to **layer 50**: "a map will never need to go higher than that… the closer you get to 63 blocks high, the less room there is for people to build structures at that height" `[GUIDE]`.
* **Grey values.** We measured the tutorial's height colour guide (51 bars, layers 0–50) from the PDF print `[RUN]`:
  * Layer 0 is grey 0.
  * Layers 1–50 come out as grey **≈ 4 × (layer + 1)**: 8, 12, 16 … 100, then ±2 jitter from the print, up to 206 at layer 50.
* **Two tools, one level apart.** The old pyspades map editor reads **h = (r + g + b) / 12**, i.e. grey ÷ 4, with black = water (infogulch/pyspades wiki, "Map Editor Tips").
  * Bildramer's converter, judging by this guide, puts the same grey **one level lower** (grey ÷ 4 − 1).
  * One likely reading: grey ÷ 4 counts solid voxels including the water voxel. That is unverified `[OPEN]`.
  * Before feeding a heightmap to a specific tool, check its convention with a test image of a few known greys.
* **Our export:** `vxl_analyzer.py heightmap_raw.png` writes grey = 4 × height, the pyspades-editor convention.

## Colourmap technique `[GUIDE]`
1. Sketch the layout first: roads, hills, cover, and where the fighting will happen. The final map follows the sketch loosely.
2. Build it in layers, in this order (top to bottom):
   * **Road** — drawn with the pencil tool so the edges are hard; a voxel game needs crisp edges.
   * **Road Dirt** — the road selection grown by 3 px and filled brown.
   * **Dirt 1–3** — grunge brushes, "Make Seamless", a little Gaussian blur, and opacity around 48 %.
   * **Grass** — a base fill.
3. Add **HSV noise** to the base colours: "too much uniform colour looks bad on a map".
   * Higher holdness keeps colours closer to the base; higher value gives more variation.
   * For white, grey and black, keep hue and saturation noise at 0.
4. **Make the edges tile.** Roads that leave the map must line up perfectly with where they come back in on the opposite edge, and dirt layers are made seamless. The tutorial assumes the map is seen tiled at its boundaries.
   * Whether 0.75 clients actually show the map wrapped is unverified for OpenSpades and BetterSpades `[OPEN]`.

## Heightmap technique `[GUIDE]`
1. Put the colourmap at half opacity over an empty "Heights" layer, so the terrain is drawn to fit the roads and features.
2. Draw **each height level as its own flat, brightly coloured region**. Use a different colour for every level; similar colours are allowed, but never the same one twice.
   * Trace the outline of the next level up with a 1-px pencil, then fill it.
   * Repeat level by level, like drawing contour lines.
3. Gameplay shaping while drawing:
   * Add valleys between hills.
   * Put a slight rise in a valley floor, so players can advance unseen.
   * Fill areas that look empty with a hill or valley, or later with props.
   * Avoid big areas of one level, which come out flat.
   * Where two levels sit too close together, the result is a wall or a steep slope; edit it if that isn't intended.
4. Duplicate the colourful layer, then recolour each level to its grey from the guide: select by colour, then fill or paint over. Tick off each level as it's done, and keep the colourful copy for later corrections.
5. After converting, look for mistakes such as a wrong colour partway along a slope, which shows up as a sudden jump of several blocks.

## What this means for our pipeline
* **Our generators already terrace the same way.** `heightfield(terrace=…)` produces stepped contours, and plateaus are deliberate. The tutorial's level-by-level approach confirms that **contour-step terrain is the community norm**, not a shortcut.
* **Adopt as defaults:**
  * Lowest playable ground at least 2 blocks above the unbreakable layer: height ≥ 3, z ≤ 60.
  * Terrain tops at or below about height 50 where building matters.
  * Roads with hard edges and a dirty border 2–4 voxels wide.
  * Dirt and wear patches as blurred, low-opacity overlays rather than per-voxel noise.
* **Per-voxel HSV noise is the classic look.** 1mirror2forts' grass measures coherence 1.27 and top noise 4.96 L*, which is what HSV noise produces.
  * Our target of coherence ≥ 1.5 deliberately goes further: structured variation such as blurred patches and ramps.
  * Both read as "not flat", but ours avoids shimmer at distance.
* **Possible tool:** a `heightmap + colourmap → VXL` importer in `aosmap`, so maps can be drawn in GIMP and then go through our protection, metadata and validation steps. It would need a `--levels` offset to match either grey convention.
