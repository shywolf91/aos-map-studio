# Tower of Babel: three concepts (slug `babel-ideas`)

Concept stage only. Nothing is built, no SPEC, no `.vxl`. Sketches: `concept_1.png`, `concept_2.png`, `concept_3.png`
(made by `mockup.py`, all labelled "concept mockup - not a map").

Brief: open ("some Tower of Babel map ideas"), stock Babel (piqueserver 1.4.2 `babel_script`), 512 x 512. The per-map
questions are not asked yet, so the three concepts deliberately differ in Babel style (ground / island / assist
structures), mood (amber afternoon / misty jade dawn / blue-hour rain) and layout logic. All three avoid the themes the
rotation is full of (Halloween, Christmas and snow, pirates and sea forts, steampunk, backyard, platformer, elven ruins).
None of them is a desert, karst or Mesoamerican map in the existing catalogue.

Conventions used below: Blue base left (118,256), Red base right (394,256), as in stock (Red's tower corridor is
x 301-384). Platform x 206-305, y 240-271, z 1; players stand at z 0. Mirror is `x' = 512 - x` unless stated. "Gap" is
how many voxels a builder must still add between the best anchor ground (or assist top) and the platform. Landmark
sizes are footprint x height in voxels and are meant to meet `docs/craft_standard.md` §0 (main buildings at least 200
cells of footprint and 12 tall, pitched or distinct roofs, two or more volumes, real rooms and openings, dressed yard of
8+ props, kit palette ramps + baked light).

---

## Concept 1: SUNSCAR REACH (ground Babel, desert salt flat, late-afternoon amber)

**Pitch.** A dried-out salt sea and the ruined observatory-caravanserai of a vanished trading people: sandstone
hoodoos, a giant sundial, glass-works that once melted sand with mirrors. Pure ground Babel, you build from the dirt.

### 1. How it plays
* **Spawn.** Each team spawns in a palm-and-tent oasis camp on firm alluvial flat (z 46, relief +/-1). Behind and beside
  the spawn: palms, tents, a stone cistern (cover for the 35 % rule). The front toward the platform is open sand with
  low dune shoulders and cairns.
* **Crossing the front.** About 75 voxels of open sand, broken by 4-15 low dune ridges, cairns and half-buried
  columns (front dressing), all walk-around or walk-over. The ground rises 1-2 voxels in swells, never a wall.
* **Tower race.** Both teams anchor on the sand shelf at x 206-211 / 300-305 (no stairs on the enemy-facing side;
  the shelf edge is a gentle dune slope facing the enemy only if it is a slope, no steps). Tower zone x 176-208 / 304-336,
  32 wide, open sand with scattered builder cover (sandstone slabs, crates, kiln pots) so griefers cannot pinch it.
  The gap is long: about 44 voxels of tower.
* **Centre fights.** A salt pan with evaporation dikes (low walls 2-3 tall, 8-9 voxel lanes), a field of ~20 hoodoos
  (3-7 wide, 8-22 tall, 7-10 apart), the Caravanserai courtyard north, the Heliostat Court south, and the Great Gnomon
  between the courtyard and the platform. Under the platform a hoodoo cluster gives 15-45 % cover with at least 25 air.
* **Flank.** The Wash: a dry canyon (floor z 52, walls to z 46, 10-14 wide) along y ~96 north and y ~416 south, about
  160 from centre. It is a covered flank with ledges and side gullies that rejoin the pan. Players in it cannot see the
  platform.
* **Getting down.** There is no real altitude: spawns are on the ground, mesa shelves (z 24-30) at the N/S edges have
  sloped sand ramps on their outer side and the Cistern Stair on the south flank. Nothing to fall from.
* **Roles.** Sniper: Great Gnomon viewing deck (z 16, reached by an inside stair, well over 110 from spawns) and the
  mesa shelves. Builder: spawn-side sand shelf, tower hidden behind slabs and hoodoos; the Heliostat Court's glass
  panels are a "mirror wall" they can duck behind. Rusher: the Wash, then up the side gullies into the pan.

### 2. Layout (512 grid, z as depth, 0 = top)
| zone | where | z | notes |
|---|---|---|---|
| Spawn oasis | Blue x 98-138, y 236-276 (camp x 60-170); Red mirror | surface 46 | clear and flat inside the +/-20 square |
| Open front | x 138-206 / 306-374 | 45-47 | dunes <= 3 tall, cairns, 4-15 objects |
| Anchor shelf | x 196-211 / 300-316, y 232-280 | 45 | solid under both platform ends |
| Tower zone | x 176-208 / 304-336, y 236-276 | 45 | 32 wide, builder cover |
| Centre zone | x 156-356, y 150-362 | pan 47 | hoodoos, dikes, three set pieces |
| Wash (flank) | y ~90-102 and ~410-422, full width | floor 52 | ramps at x 90, 200, 312, 422 |
| Mesa shelves | N y 0-60 and S y 452-512 | 24-30 | outer slopes, edge fringe |
| Corner mesas | (46,60) and mirrors | 26 | corner tag room on the ground |
Safe way down from spawn: none needed (ground start). Ground is sandstone and salt to z 62; the bottom is just stone.

### 3. Landmarks
1. **The Great Gnomon** (256,210), 14 x 14 x 30 tall: a sundial obelisk of banded sandstone with a hollow shaft, inside
   stair, viewing deck at z 16, a carved scale ring on the salt around it. Map name hook ("the Sundial map").
2. **Heliostat Court** (256,322), r 26: ring of 12 tilted pale-glass mirror panels around a furnace hall with a pitched
   tile roof. Real doors and a kiln room.
3. **The Caravanserai** (256,158), 84 x 36 x 14: walled courtyard with arcades, stable bays, a two-storey gate tower,
   well in the yard. A main building (several volumes, pitched roofs).
4. **Dunewreck** (256,98), 40 x 12 x 16: a land-sailing ship's hull beached in the Wash, ribs open, mast fallen across it.
5. **Cistern Stair** (256,416), 30 x 30 x 8 deep: a stepped well with a roofed arcade, a place to hide and a sniper-safe way down.
6. **Needle Gates** (140,120) and (372,396), 22 x 16 x 20: natural sandstone arches on the corner mesas, a slow
   diagonal flank crossing. (A rotationally placed pair; they are different arches.)

### 4. Distinctive
First desert in the rotation. Ground Babel. A sunlit, warm, open map in a rotation full of night, snow and sea. Sight
lines are long and the sun-baked ochre ground has real value structure (sand, salt, terracotta, shadowed canyon).

### 5. Numbers
Spawn floor z 46; anchor shelf z 45; build gap about 44 (stock, no assist). Front: 8-12 dune/cairn objects, 1-3 tall.
Fog: pale lilac-grey (190,175,205), hue absent from the ochre palette, neutral between blue and red. Salt cap max
channel about 212. Floor luma >= 80 (nothing dark).

### 6. Risks
* **Art:** a desert can read as flat orange. Needs the palette guide: sand ramp with pink and olive shadows, salt
  highlights capped, canyon shade. Hoodoos must look carved (strata courses), not like pillars.
* **Play:** wide open sand favours snipers; hoodoos and dikes must carry the centre. The tower race is long.
* **Owner rules:** the open front plus a platform up at z 1 above flat sand is the classic spawn-camping set-up.
  Expect exposure to fail on hidden share (compare Frozen Icebreaker 7.9 % hidden, accepted). Terrain can help:
  a 4-6 tall dune lip around the sides and back of the spawn plus palms, with the front side open, raises the
  hidden share without blocking the front. If the owner wants a walk-through gate it would cost the "open front".

---

## Concept 2: JADEWATER KARSTS (island Babel, paddy lake, misty jade dawn)

**Pitch.** Limestone karst needles standing in a shallow terraced-paddy lake under morning mist. Each team's island is
a stepped rice-terrace plateau, the middle is a forest of stone towers with stilt walkways and a floating-feeling
market, and the tower race happens between water and mist.

### 1. How it plays
* **Spawn.** Terraced plateau island (surface z 42): the spawn is a flat terrace with a farmhouse yard, drying racks,
  stone steps and bamboo clumps for cover. Rice terraces step down to the lake in 2-voxel risers: this is the safe way down.
* **Crossing the front.** Two broad earth dikes (paddy walls 8 wide) from the plateau to the middle, plus wading
  through the shallow lake (seabed z 59, walkable, slow in the open and visible). Dikes run between low karst stubs and
  reed beds (front dressing). The solid anchor ground continues out to x 216 / 296 so both platform ends have ground.
* **Tower race.** Anchor on the plateau tip; zone x 176-208 / 304-336 is a flat rice terrace, 32 wide. Gap about 41.
  Boats and bamboo scaffold bundles give builders cover.
* **Centre fights.** ~17 karst pillars (r 6-12, z 14-30) with plank bridges at z 38-40, pavilions on five, a stilt
  market on the south side, the Bamboo Aqueduct arcing over the north causeway, and one tall pagoda pillar. Gaps are
  7-10 between pillars. Under the platform stand four lower pillar stumps (15-45 % cover, over 25 air).
* **Flank.** A chain of bamboo-grove islets north and south (y ~50 and ~462) joined by plank causeways, 160-210 from
  centre. Mist and bamboo hide movement and the bridges are narrow but have wading alternatives either side.
* **Getting down.** From any pillar top an exterior stair or rope-less plank ramp (wide, 4 voxels) descends to the
  lake; the lake is shallow and walkable, so falling in is safe.
* **Roles.** Sniper: Cloud Ladder summit and the Bell Pagoda pillar (no pillar within 100 of a spawn square carries
  a perch). Builder: plateau tip, hiding behind boats and haystacks, tower bridging off a pillar for an extra hand-hold. Rusher:
  the dikes and the wading lines under the stilt market.

### 2. Layout
| zone | where | z | notes |
|---|---|---|---|
| Spawn plateau | Blue x 30-216, y 190-322; Red mirror | top terrace 42 | terraces 42 / 44 / 46 down to lake |
| Spawn squares | x 98-138 / 374-414 | 42 | flat terrace, farmstead |
| Anchor ground | x 196-216 / 296-316 | 42 | solid under platform ends |
| Karst forest (centre) | x 156-356, y 150-362 | pillars 14-30 | 7-10 gaps, bridges, shallow lake between |
| North and south chain | y 30-80 and 432-482 | 38-44 | bamboo islets, flank route |
| Waterfall scar | (256,24) | cliff to 18 | north edge |
| Lake | whole remainder | seabed 59, surface near 58 | walkable, no authored deep water |
Ground is solid to the seabed under every island and pillar (no floating rock). `water_damage` set to 0 (lake), unless the owner wants it.

### 3. Landmarks
1. **Moon Gate Bridge** (256,356), 36 x 12 x 22: a round stone gate over a plank bridge, big enough to walk through,
   with a lantern pavilion either end. The name people will use.
2. **Cloud Ladder** (256,126), 22 x 22 x 30: the tallest pillar with a switchback stair carved into it and a small
   shrine on top.
3. **Bell Pagoda** (236,330), 18 x 18 x 26: a five-tier pagoda on a pillar, hollow and reachable, real floors and stairs.
4. **Waterfall Scar** (256,24), 40 x 14: a cliff with a pouring waterfall (blue and white blocks) and a pool.
5. **Cormorant Raft Village** (256,460), 40 x 14: huts on stilts and rafts with nets and perches.
6. **Bamboo Aqueduct** (256,188), 36 x 10 x 12: a long raised bamboo-pipe channel on trestles; walkable top.

### 4. Distinctive
New: karst and paddy terrace; island-style but shallow and wadeable (not open sea). Brings vertical stone texture
and mist. Island style, with a wider flank than Cursed Skull Reef or Yulehaven.

### 5. Numbers
Spawn terrace z 42; anchor ground z 42; build gap about 41. Karst tops z 14-30 (all 11 or more below the platform;
none an assist). Mist: z 63 painted cloud sea (visual only). Fog: pale rose-grey (200,185,195), brightness 150+.

### 6. Risks
* **Art:** limestone cliffs must show strata and overhangs without looking like columns. Water needs a colour that
  isn't flat teal. Heavy foliage risk (bamboo) near spawn fronts.
* **Play:** pillars at z 14-30 over the lake are the best sniper nests; pagoda and Cloud Ladder tops can see the platform and spawn
  fronts. Must stay 100+ from spawn squares. Wading slows rushers, which helps defenders.
* **Owner rules:** closest to "no screens", but pillars crowd the centre (must keep 7-10 gaps). Spawn exposure is
  the usual open-front problem on a plateau, and terraces behind the spawn plus bamboo give cover; the front stays open.
  Possible tension: a lake with seabed may count as "island = water", the owner's rule is only that islands get seabed foundations.

---

## Concept 3: VERDIGRIS STAIR (Babel with assist structures, overgrown step-pyramid jungle, blue-hour rain)

**Pitch.** Two ruined step pyramids, the Sun Stair to the north and the Moon Stair to the south, reach toward the
platform from either side. Each ends in a broken causeway arm that stops 7 voxels short of the platform lip, 8 below
it. A rainy twilight jungle with glow-lit shrines. A Babel built around the idea of a stair that was never finished.

### 1. How it plays
* **Spawn.** A jungle clearing (z 44) with a ring of fern thickets, fallen idols and a cave-mouth ruin behind; relief +/-1.
* **Crossing the front.** An overgrown processional way (4-15 low objects: toppled columns, moss mounds, stone
  basins, glow-lamp posts) with open lanes. Nothing blocks. Canopy trees only in groves off to the sides, never on the front.
* **Tower race.** The ground tower: zone x 176-208 / 304-336, 32 wide, a flat plaza with scattered stelae as cover.
  Gap 44 from the ground. The assist: a team can reach z 9 by climbing either pyramid (stairs on all faces, so equal for both teams
  and no stair on an anchor-ground enemy side), then needs to add about 8 up and 7 across to get to the platform:
  roughly 12 to 15 blocks, bridging in view of everyone. Contestable, never a ready-made path. Gap is reported per structure: Sun 8 up + 7 across, Moon 8 + 7.
* **Centre fights.** The two pyramids (56 x 56 each) with the plaza between them, the Ball Courts (walled sunken courts)
  west and east of the north pyramid, the Root Cage under the platform (strangler-fig roots, 6-18 tall, at least 25
  air above), the Coil Wall across the south, shrines and basins. 7-10 gaps, many doors.
* **Flank.** A stream flows from the cenote on the north (y ~98) west and east to the map edge (y ~60-110).
  Walking the bank gives a long shaded flank; shallow wading at several points. South flank passes the Mossy Head.
* **Getting down.** Every pyramid face has a wide stair (4 voxels); the cenote has stepped sides. Nothing is
  taller than 35 voxels from the ground.
* **Roles.** Sniper: the pyramid terraces (from z 20 up; kill-lane over the platform). Builder: ground plaza with
  stelae cover or the assist bridge (riskier, in view). Rusher: stream bank, ball courts, then up pyramid stairs
  to harass the bridge builders.

### 2. Layout
| zone | where | z | notes |
|---|---|---|---|
| Spawn clearing | Blue x 60-170, y 208-304; Red mirror | 44 | cave-ruin behind, fern ring |
| Processional front | x 138-206 / 306-374 | 44 | open |
| Anchor ground | x 196-211 / 300-316 | 44 | no stairs facing the enemy |
| Tower zone | x 176-208 / 304-336 | 44 | 32 wide |
| Sun Stair | x 222-290, y 150-218 | top 9 | stairs on four faces; causeway arm y 218-233 |
| Moon Stair | x 222-290, y 294-362 | top 9 | arm y 278-294 |
| Root Cage | (256,256) r 22, under platform | 44 up to 26 | roots only |
| Ball Courts | x 150-214 and 298-362, y 168-198 | sunk to 47 | walled, three openings each |
| Cenote | (256,98) rx 34, ry 22 | water at 46 | stepped sides |
| Coil Wall | y 370-396, x 150-362 | 38-44 | serpentine, openings every 9 |
Pyramids solid to the ground (stepped masonry with interior rooms). Edges and the arms are the only things near the platform;
the arms are *not* a ramp, they end 7 short of the lip and 8 below.

### 3. Landmarks
1. **The Sun Stair** (256,184), 56 x 56 x 35: stepped pyramid, 9 tiers, a stair on each face with a vine-choked
   shrine and a ruined temple volume on top (two volumes plus roofed gallery). A main building. Name candidate.
2. **The Moon Stair** (256,328), 56 x 56 x 35: the sister pyramid, differently ruined (collapsed corner, cave-mouth base).
3. **The Root Cage** (256,256), 44 x 40 x 18: a giant strangler fig that swallowed a shrine, a walk-through cage of roots
   under the platform.
4. **The Cenote** (256,98), 68 x 44, 14 deep: a sinkhole pool ringed by lit shrines, stepped sides, a roofed side cave.
5. **Coil Wall** (256,383), 212 long: a low serpent-scaled wall winding across the south in an S, 3-6 tall, with
   gates every 9; the carved head ends at the east side.
6. **Ball Courts** (182,183) and (330,183), 64 x 30 x 8: sunk, walled courts with stone rings and a viewing loggia (twin,
   dressed differently).
7. **Mossy Head** (256,428), 24 x 20 x 16: a colossal half-buried stone head; hollow, you can walk in through the mouth.

### 4. Distinctive
New: Mesoamerican-flavoured (original designs, no named sites) jungle ruin; the only concept with a real "Babel
with assist structures" and a stair-themed identity that suits the Tower of Babel. Night-lit (blue hour + glow blocks)
and humid, in a rotation of snow and sea. Colours green, teal, grey stone and amber glow.

### 5. Numbers
Spawn z 44; anchor ground z 44; ground gap about 44. Assist tops z 9, gap to the platform 8 up and 7 across, equal
on both sides (north and south are 180-degree twins, tiny differences in decoration only). Fog: soft peach (205,190,175)
or pale lilac if the palette ends up warm; brightness 150+. Glow lamps and shrines carry the evening. `heavens_color`
optional (ask).

### 6. Risks
* **Art:** the pyramids are large (two buildings of 56 x 56 x 35), so stepped masonry can look like a stack of
  boxes. Needs real facade work: tier recesses, stairs with balustrades, carvings, vines, moss gradients. Heavy
  to build to the craft standard.
* **Play:** pyramids are strong sniper platforms over the centre and platform; the assist is contestable but its
  holder sees everything. Bridge builders are exposed. The assist is only 8 + 7 from top, so it might trivialise the tower race:
  the gap can be widened (arm stops 10 short) after playtest.
* **Owner rules:** the pyramids are structures near the front line but off the spawn-to-tower lane, so fronts stay
  open. Spawn exposure faces the same open-front trade-off. Pyramids are "tall things near the platform":
  keep them 20+ off the anchors. The Root Cage fills under-platform space; check the 15-45 % rule.

---

## Recommendation: concept 3 (Verdigris Stair)

1. It is the only one that makes the Babel idea itself the identity (a half-built stair), and the assist structure
   rule is an owner-defined variant he can judge on equal access, with the gap reported per structure.
2. It has the strongest unique one-offs (Sun and Moon Stair, Root Cage, Mossy Head), matching his taste, with the
   most different mood in the rotation (blue-hour jungle + glow).
3. It has the best mix of centre density (pyramids, courts, roots) and open fronts, while the layout is clean for a
   builder to implement.

If time or craft risk is the worry, concept 1 is the safest build (fewer huge structures). Concept 2 has the best visual
beauty potential but the most terrain and water complexity.
