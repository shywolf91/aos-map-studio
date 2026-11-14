# Elderveil — spec (v1.0)

**Status: server-loaded** (2026-11-14). Loaded on a live piqueserver 1.4.2 in Babel mode by `aosmap.kit.probe`.
Not client-inspected and not playtested. The renders in `maps/elderveil_v1/renders/` are numpy previews, not
client captures.

An original dark-fantasy map: a forest valley swallowed by the pale-stone ruins of a vanished elder people, on a misty
morning. Monster-hunter camps have moved into the old outposts. **Babel, assist structures** (light): stock
piqueserver 1.4.2 `babel_script`, plus one mirrored pair of climbable ruined spires that shorten the climb but do not
replace tower building. Full 512 × 512 ground. Branch `map/elderveil`, generator `scenes/elderveil/`, built with
`aosmap.kit`.

No characters, symbols, creatures or named places from any existing game or book. Everything is original.

## Owner answers `[USER 2026-11-13]`

| question | answer |
|---|---|
| concept | B, overgrown elven ruins ("Elderveil"), build now |
| mode | Babel with assist structures, "not overwhelming" |
| map type | Claude decides |
| mood and season | Claude decides |
| water | walkable (`water_damage` 0) |
| extras | floating sky decor and glow blocks (no underground, no `heavens_color`) |
| corner tag | at sky level (corner: Claude decides) |
| must-haves | not given (Claude decides) |
| what players loved | the artistry of Wicker King's Harvest and Silverpine Hunt |

## Decisions taken for the owner `[DESIGN]`

* **Map type:** full 512 × 512 ground valley, ringed by forested cliffs topped with broken elder walls (rock, moss
  and trees, not bare walls). Ground Babel varies the rotation after the Christmas maps.
* **Mood:** misty early morning in late summer. Pale gold light, deep greens, moss, white-grey stone, a few warm
  hunter campfires and cool blue rune-light. No snow, no orange-black Halloween palette.
* **Fog:** `(176, 172, 190)`, a pale lilac mist: bright, neutral between blue and red, a hue the palette doesn't use.
* **Assist, "not overwhelming":** one mirrored pair of ruined elder spires, not a central giant. Each spire's
  highest walkable point leaves a **build gap of 8–12 blocks** to the platform (normal tower: about 46). That is a
  real shortcut but still needs a contested build. The climb is outside, exposed, with broken floors and landings.
* **Corner tag:** north-west corner, at sky level: a 2-voxel pale stone plate above the cliff ring with a plain dark
  underside and one hidden stalk down to the ground (knowledge base §12.5).
* **Spawns:** mirrored. Each team spawns in the courtyard of a ruined elder outpost turned hunters' camp.

## Layout

Mirror `x' = 512 − x` (`x512`, column 255 copied into 256). Coordinates are the west (blue) half and the centre
axis. z = 0 is the sky; a floor z is the solid voxel a player stands on.

### Elevations

| area | floor z |
|---|---|
| valley floor, front, anchors, under the platform | 50 (gentle ±1 relief outside anchors and spawn squares) |
| spawn courtyard | 48–49, gentle mounds, no holes |
| sunken plaza (north centre) | 53, reached by wide steps on every side |
| root amphitheatre (south centre) | 50 down to 53 in terraces |
| south flank: waterfall pool and stream | water at z 63; banks slope down; shallow wading shelves at z 61–62 |
| north flank: aqueduct | ground 49; walkable deck on top at z 38–40 on intact spans |
| cliff ring | rises from 48 to crests at z 10–16; nothing above z 6 |

### Zones (west half; east is the mirror)

| zone | x | y | notes |
|---|---|---|---|
| cliff ring | 0 to 30–60 | all edges | irregular, spurs and coves, forested ledges, broken walls on crests; walkable foothills |
| spawn square (stock) | 98–138 | 236–276 | clear land; + 4 no-prop margin |
| ruined outpost (spawn camp) | 50–150 | 190–322 | broken curtain walls with wide breaches, a gate tower, a hall with an upper floor, hunters' tents, trophy racks, a cart, a campfire; lanes ≥ 8 |
| front (dressed, open) | 139–199 | 236–276 | low ruin pieces ≤ 5 tall: fallen column drums, a toppled statue torso, moss mounds, a hunter's sled-cart, ferns, one roofless one-room shrine; zone-rule front targets |
| tower anchor ground | 200–211 | 236–275 | flat z 50, solid to the bottom, prop-free, no stairs on the east face |
| under the platform | 212–300 | 236–276 | low ruins: column stubs, a fallen elder head, root humps, a broken mosaic floor; 15–45 % covered, ≥ 25 air; x 200–217 and mirror clear |
| assist spire | about 178–200 | about 206–228 | ruined round spire north of the front band, outside it and outside the strip; external broken stair, landings, a collapsed floor; top 8–12 blocks below the platform; contestable from all sides |
| sunken plaza | 180–255 | 130–215 | marble plaza at z 53: dry fountain on the axis, ring of broken statues, arcades, mosaic |
| root amphitheatre | 180–255 | 300–380 | a giant ancient root system arching over terraced stone seats; walk-under arches with ≥ 4 air |
| north flank: aqueduct | 44–255 | 60–120 | a broken elder aqueduct along y ≈ 88, arches to walk under, intact spans to walk on, collapsed sections with rubble ramps |
| south flank: mushroom hollow and pool | 44–255 | 392–470 | a waterfall from the south cliff into a pool, a stream along y ≈ 430, giant glowing mushrooms, a stone footbridge |

### Centre-axis one-offs (symmetric about x = 255.5)

| object | centre (x, y) | notes |
|---|---|---|
| moonwell | 256, 170 | dry fountain basin with a rune ring (cool glow), in the sunken plaza |
| elder library ruin | 256, 120 | enterable, two floors with stairs, fallen shelves, reading alcoves |
| fallen statue of an elder queen | 256, 200 | original figure, lying broken across the plaza edge, walk-over and walk-under |
| ancient heart-tree | 256, 340 | the root amphitheatre's tree; trunk off the platform line, canopy well clear of the platform |
| standing rune circle | 256, 410 | stones with cool rune glow beside the stream |
| footbridge and waterfall | 256, 440 | stone bridge over the stream; waterfall from the south cliff behind it |

### Sky, glow, colour

* **Sky decor (expected floating, listed):** three or four small floating ruin islets (broken elder balconies with a
  hanging root and a rune glow) and a flock of crows (each bird ≥ 13 voxels wide). All ≥ 60 from the platform, not
  over spawn squares, ≥ 8 air below, nothing at z ≤ 6. Collapse caveat applies.
* **Glow sources (fixed palette):** warm (255,175,95) for campfires, lanterns and hall windows; cyan (95,255,255) for
  rune stones, the moonwell and the islets; green (95,255,95) sparingly on giant mushrooms; white only for one or two
  focal points. No red.
* **Palette families:** pale elder stone (warm white-grey, ≤ 212), moss and forest greens, bark and timber browns,
  gold accents. Floors luma ≥ 40. Stone cracks and moss break up every large pale surface.
* **Vegetation:** the art centrepiece. Old-growth groves (giant oaks, beeches, firs), ferns, ivy on ruins, hanging
  roots, wildflower patches; three random details per plant, OS seed per build.

## Owner decision on spawn exposure `[USER 2026-11-13]`

The graybox measured about 10 platform viewers per spawn spot and 0 % of spots hidden (targets: at most about 10,
at least 15 % hidden). A ruined gateway arch across the front would give 44 % hidden (solid band z 34–40) or 83 %
(z 28–34). The owner chose to **leave the front open**. The spawn-exposure check is waived for this map and is
reported as waived, with its numbers, not as a pass.

## Rules that apply

All AGENTS.md §4 rules, including the four 2026-11-13 zone rules (front dressing, spawn cover, under the platform,
room-sized centre pieces) and the assist rules in knowledge base §8.8: equal access, contestable, z 0–2 + 1 margin
over the platform footprint empty, tower corridors usable, spawn exposure re-measured with the spires in place.
Relaxed checks for this variant: "platform not reachable without building" stays a pass (the spires still need a
build); the build gap is reported per structure.

## As built (v1.0) `[RUN 2026-11-14]`

Release build: vegetation seed **2243074186** (OS-drawn, saved in `build.json`).
`.vxl` 3,189,784 bytes, SHA-256 `de354987685297fd39ded48a9bb59f0b84503a0e059d151d48de1bb129ae8d62`.
`.txt` 736,833 bytes. Label: **Babel, assist structures**.

### Deviations from the layout above

* Spire footprint x 180–201, y 208–229. Top floor z 12.
* Gate tower: octagonal, 3 storeys, arched gateway through its base, at y 222–235 beside the front band.
  Hall: L-shaped with an apse and a collapsed corner. Bastion at y 277–290: an enterable broken tower base.
* Front: a fallen lintel block (5 tall) added; the roofless shrine sits just north of the band (y 226–234).
* Under the platform: an elder head (radius 7.5) and three 7 × 7 plinths with column stubs; no root humps.
* Aqueduct: gentle double bend (y 88 ± 6), three collapsed gaps per side with rubble stairs, a fallen span.
* Six minor ruin sites per side: collapsed colonnade, toppled obelisk, stair to nowhere, roofless chapel,
  hunters' lookout, monster-nest cave in a new crag at (36, 372).
* Rune circle at y 398 (not 410); footbridge spans y 410–462; twin waterfalls flank the bridge (x 240–247 and mirror).
* Heart-tree: twisting trunk with a walk-in hollow, seven roots of four kinds, forked limbs with separate crowns.
* Sky: four floating ruin islets and crows (13 expected floating pieces). Tag "Elderveil" at z 7–8 over the
  north-west crest on one stalk (tethered, not floating).

### Validation

| check | result |
|---|---|
| own reader, re-encode; pyspades 1.4.2 `generate()` | identical; identical |
| floating components | 0 unintended; 13 expected sky pieces, sky rules met (≥ 145 from the platform, ≥ 9 air below, none over a spawn) |
| mirror (`x512`) | 0 solid and 0 material mismatches outside the declared boxes |
| platform volume and margin; ceiling | clear; nothing solid at z ≤ 6 (top solid z 7) |
| ground under platform ends; anchors | flat z 50, no water; prop-free, no enemy-side stairs |
| spawn squares | tops z 48/49, 0 roof columns, 0 water columns, margins prop-free |
| **spawn exposure** | **WAIVED** `[USER 2026-11-13]`: blue 10.25 viewers per spot, 0 % hidden; red 10.0, 0 % |
| build gap | 48 from the anchor ground; 42 from the highest point near the platform (queen statue, z 44); **10 from each spire top** |
| platform reachable on foot | no |
| spire tops | 21 voxels horizontally from the platform edge, 11 below it; 144 steps from own spawn, 280 from the enemy spawn; safe way down |
| spire perch (report) | each spire top sees 92.5 % of its own side's spawn spots (8.4 eye positions per spot), 0 % of the other side |
| zone: front dressing | pass: 7 objects, 10.6 % covered, all ≤ 5 tall, worst 8-column section 74.7 % free |
| zone: spawn cover | pass: 28 % enemy side within 20, 61 % rear backdrop |
| zone: under the platform | pass: 15.4 % covered, ≥ 42 air, anchors flat and clear |
| zone: centre median object footprint | pass: 47 cells |
| traps; interiors; high floors | 0; 84 of 84 reachable with a way out; 32 high floors with a safe way down |
| front open (own check); featureless patch | worst column 73.2 % free; 21 (limit 24) |
| flanks north / south | 574 / 540 steps (5.9 % apart), same for both teams |
| periphery reachable; central crossing width | 82.0 %; 250 |
| graybox vs art collision | 0 unallowed reachable-cell changes (plants are the allowed category) |
| colours | top-surface median luma 85.9; min floor luma 40.6; near-white tops 0.09 %; 86 glow sources, none red |
| seeds | 3 other seeds pass every check with 0 traps and 0 unintended floating; spire gap 10 on each |
| reproducibility | same vegetation seed gives the same SHA-256 in two fresh processes |
| live server (piqueserver 1.4.2, babel) | loaded; platform 3,200 cells; 400 spawns per team inside the stock squares at z 48/49; fog and extensions read |
| tests | `pytest`: 34 passed |

Route, trap and interior results come from a graph model, not from play.

### Known limits and open points

* **Spawn exposure is waived, not met.** Every spawn spot is visible from the platform rim. Expect spawn camping
  once a team holds the platform.
* **The spires overlook their own side's spawn** (92.5 % of spots). An enemy who climbs a spire can camp from it.
* **Art below the Wicker King / Silverpine standard:** the fallen queen statue still reads largely as a pale slab at
  eye level; the elder head is small and simple; cliff faces have no sculpted buttresses or vines; trees are simpler
  than Silverpine's.
* Not seen in any client: fog, glow, mist tint, waterfall and FPS are unverified.
* `glow_*` keys are read by the owner's server setup only. Stock 1.4.2 shows the baked light.
* The sky pieces float by request. Breaking a player block attached to one drops it for the round. The tag hangs
  on one stalk; cutting the stalk drops the plate.
* Round length with a 10-block spire gap is untested; it may end rounds quickly (knowledge base §8.8).

### Regenerate

```bash
python scenes/elderveil/ev_main.py out/elderveil 2243074186   # omit the seed for a new random build
python scenes/elderveil/ev_render.py out/elderveil
python -m aosmap.kit.probe out/elderveil --mode babel
python scenes/elderveil/ev_main.py out/ev_graybox --graybox    # gameplay geometry only
```
