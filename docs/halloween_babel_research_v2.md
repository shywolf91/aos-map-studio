# Halloween Babel pair — research + concepts (2026-10-15)

**Brief (Dylan, 2026-10-15):** research two new Halloween Babel maps — one full 512 × 512 map and one island map
(like swag2). **Do not generate yet.**

**Status:** researched · concepts specified · **nothing generated, exported or tested.** The overhead image that goes
with this doc (`halloween_babel_schematics.png`) is a flat layout schematic at true map coordinates, not a render.

Tags: `[SRC]` checked in piqueserver v1.4.2 source today · `[RUN]` measured today on the project's VXL files ·
`[GUIDE]` aloha.pk rotation guide v1.8 · `[USER]` Dylan's standing rules · `[DESIGN]` proposal, untested.

---

## 1. Rules both maps must follow

**Stock Babel (piqueserver v1.4.2 tag, commit e555d21, `scripts/babel_script.py`)** `[SRC]`
* Platform x 206–305, y 240–271, z 1, colour (0, 255, 255); keep z ≤ 2 empty over it.
* Bases (118, 256) and (394, 256). Spawns: base ± 20 in x and y, at `map.get_z` = the **topmost solid voxel** →
  spawn squares x 98–138 / 374–414, y 236–276 must be flat land with nothing on them (an island map must put land
  under both whole squares).
* Build ban: a player can't build while standing in the **enemy's** tower corridor (blue blocked at x 301–384,
  red at x 128–211; y 240–272). Spade ban: no spading while standing in your **own** corridor.
* Destroy rule: blue is refused while standing at x ≤ 288, red while standing at x ≥ 224.

**Correction to earlier project notes `[SRC]`:** the destroy rule tests the **destroyer's position**, not the
block's. So "nobody can remove blocks in x 224–288" (Drowned Cathedral spec) is too strong: nobody *standing* in that
band can destroy, but a red player standing at x < 224 can still shoot or grenade a block at x 250. Player blocks in
the centre are hard to clear, not permanent. Worth fixing in `drowned_cathedral_spec.md` and `aos_map.md` §7.

**Dylan's standing rules `[USER]`:** solid ground to the bottom (islands get seabed foundations); floating pieces
only if requested; no AI spawn hooks in the `.txt`; bright fog tint (channels ≥ ~150); name tag in a corner
("<map name>" / "Designed by shywolf91 and AI"); a safe way down from spawn to the tower zone and to ground level;
spawns covered from the platform, never on roofs; mirrored for balance.

**Guide targets `[GUIDE]` + project checks:** ≤ ~10 platform viewers per spawn spot, ≥ 15 % of spawn spots hidden;
no sealable single exits; no 1-voxel pillar fields or high-contrast 1-voxel stripes; no glaring fog.

## 2. Water and the sea — what an island map actually gets `[SRC]`

* Water is one layer: a column with z 62 air over the z 63 floor. **All water is the same wading depth**, so without
  damage a player can walk across the whole sea, out to the map edges and around to the enemy side.
* `water_damage` (map extension, `scripts/map_extensions.py`): on each position update with position.z ≥ 61 the
  player loses that many HP. It covers **every** water column, lagoon included. How often position updates arrive
  is client-driven — not yet measured, so the right value needs an in-game test.
* `boundary_damage {left, right, top, bottom, damage}` (same script): damage outside a rectangle. This makes the
  map edge deadly while the near-shore sea stays safe.
* So "island play" is a server choice, not a geometry fact. swag2 is described by the guide as the lava map whose
  island play comes from the lava; we don't have its `.txt`, so whether it uses `water_damage` is unverified.

## 3. Reference study (measured today, not copied)

Method: our own VXL decoder → top-surface height map and colours (scratch script, numpy). "Rough gap" = straight
distance from the closest top surface (3×3 flat-ish) to the platform; **no walkability check**, so it can count a
roof nobody can reach. Spawn exposure figures are from the earlier calibrated `sightline.py` run.

### Island / sea maps
| map | water | landmasses ≥ 200 cols | spawn floor z (median) | under platform | rough gap | palette | guide / exposure |
|---|---|---|---|---|---|---|---|
| **swag2** | 76 % | 3 (main + 2 islets) | 61 | z 59, central building to z 27 | 43 | 76 % red, black sea — dark red ground, tombstone grid, dead trees, spine bones at spawn | "lava map with tombstones", too-open spawn but works, island play from the lava; 8.6 viewers |
| islandbabel | 80 % | 6 | 61 | z 61 (4 % water) | ~56 | sand 64 % orange / 34 % yellow, cyan sea | 9.0 viewers, 100 % exposed |
| babelpocalypse | 63 % | 11 (main + 10 islets) | 44 | central hill to z 9 | ~8 | green/yellow | "open but not too bad"; 7.8 viewers |
| t_o_r_t_u_g_a | 60 % | 18 | ~50 | z 48 | — | | only 14 % of land columns solid to the bottom; heavy floating |
| alexandria-babel2 | 69 % | 4 | 58 | pyramid | ~4 | 78 % orange | works; 7.9 viewers |
| GoonassaultJapan | 87 % | 1 | 62 | tower to z 11 | ~15 | green + purple | spawn squares **28–30 % water** → some stock spawns land in water |

What swag2's layout actually is: one **butterfly-shaped main island** (x 46–469, y 111–402) at a low z 57–62,
spawns on the wings, a dense tombstone field across the middle, and **a ring of about a dozen small islets linked by
plank bridges** around it (most of them join the main landmass, so the scan counts 3 masses). The bridges and islets
are the "island play" — flank loops over a hostile sea.

### Full-map references
| map | water | spawn z | under platform | rough gap | note |
|---|---|---|---|---|---|
| normandie | 0 % | 59 / 60 | z 59 | ~36 | not mirrored (0.16 height match) yet fair; 94 % solid underground; walls, hedges, village |
| alpine | 0 % | 58 / 52 | peak to z 9 | ~8 | central mountain + serpentine roads + dense forest; bases 6 apart in median height |
| battlefarm | 0 % | 56 | barn to z 32 | ~31 | |
| remus | 6 % | 60 / 57 | z 62 | | dense city, river |
| hallweebalohabeta | 21 % (painted plane) | 62 | z 3 | ~4 | Halloween-palette city (red/blue/purple); 59 / 72 % exposed (good cover) |

Takeaways: (1) most rated Babel maps put **some** central feature under the platform — short gaps (4–15) on
alpine, babelpocalypse, alexandria, Goonassault, hallweeb; ours have used 25–40. (2) island refs sit at 60–80 %
water. (3) both island references are rated "open" — cover at spawn is the thing to beat. (4) planeassault_halloween
has 99 % water and both stock spawn squares are entirely water, so it must rely on a non-stock spawn setup (no
`.txt` to confirm) — not a template for stock Babel.

Themes already used in this project (avoid repeating): haunted timber village + church + cemetery (Hollowfen,
Hollowfen Vale), sunken gothic cathedral in a fen (Drowned Cathedral), unpicked: Gallows Hill, Ghost Ship Cove,
Pumpkin Hollow Carnival, Witch's Cauldron. Lava + tombstones is swag2's identity, so the island avoids lava.

---

## 4. Full 512 × 512 map — three concepts

| | **A. Grimspire Pass** (recommended) | B. Blackthorn Manor | C. Witchwood |
|---|---|---|---|
| identity | a cursed mountain pass: black crag with a ruined lich's watch-keep under the platform, an old mine tunnel through it, larch forests turning rust-orange, stone hamlets in the valleys | haunted country estate: two mirrored mansions on terraces, hedge maze between, a dead glasshouse and family mausoleum under the platform | colossal blackwood trees in a mire; spawns in root-ringed clearings; a hollow "mother yew" under the platform with shelf-fungus stairs |
| Babel style | ground spawns + central king-of-the-hill summit | pure ground Babel | ground spawns + central tree |
| spawn floor | z 54 | z 52 | z 54 |
| build gaps (target) | ~45 from your knoll; ~25 from the summit deck | ~50 from the lawn | ~45; ~28 from the yew deck |
| new for the project | central mountain + through-tunnel (guide praises tunnel play on SkullFort / roadisland) | hedge maze as cover | giant-tree scale |
| art risk | medium (crag + keep) | low–medium | **high** (huge trees easily look crude; foliage noise) |
| play risk | central race ends rounds early if the summit is too high; tunnel sealing | long build, plays like Hollowfen Vale | crowns become free scaffolding; lag from foliage |

**Why A:** it adds two playstyles the rotation set doesn't have yet (central hill race and a tunnel flank), it's
close in spirit to alpine without reusing alpine's snowy massif or roads, and its height drama sits in the centre,
not between spawn and ground — so the "too tall / hard to get down" problem from Drowned Cathedral v1 doesn't
return. Overlap to note: like Drowned Cathedral it has a contested central bridgehead; B is the pick if you want a
map with no central shortcut at all.

### 4.1 Grimspire Pass — spatial spec `[DESIGN]`
West half authored, mirrored x' = 512 − x. z down; ground solid to z 63.

| element | where | heights / notes |
|---|---|---|
| valley floor | everything outside the massif and rims | stepped meadows z 54–58, stream along the valley optional |
| spawn green | x 98–138, y 236–276 | flat z 54, flagstones, **nothing on it** |
| hamlet | x 66–146 around the green | 8 stone cottages per side (slate roofs, ridges ≤ z 42), well, smithy, cider press, pumpkin cart, wayside shrine, lantern posts; no roof overhangs the green |
| cover screen | x 141–145, y 230–252 and 260–282 | churchyard-style wall + barn row, top z 44, 8-voxel gate at y 252–260 plus open ends; tune with `sightline.py` to ≤ 10 viewers, ≥ 15 % hidden |
| tower zone | x 146–205, y 228–284 | open meadow rising to a knoll z 46 at x 186–205; **no props**; gap ≈ 45 (tune knoll 42–48) |
| the Grimspire (massif) | ellipse centre (256, 256), semi-axes 44 × 106 → x 212–300, y 150–362 | base z 56; cliff faces steeper than 1 per column (not walkable) except the trails |
| summit keep | deck x 244–268, y 236–276 | deck **z 26** → gap 25 straight up (tunable 24–30); broken towers, merlons; no tip higher than z 16 |
| switchback trails | north and south faces | 4 wide, 1-voxel risers, **2-high rails** on drop sides; z 56 → 26 |
| mine tunnel | x 212–300, y 253–259 | floor z 56, 5 air high, timber frames every 6, rails, ore carts in side pockets; two side galleries so one block line can't seal it |
| pass roads | y ≈ 124 and ≈ 388, x 60–452 | the main flank loops around the massif ends; ruined toll gates |
| rims | outer ~24 columns | forested ridges z 36–46, steep, frame the view |
| forest | the four quarters | rust larches (amber/orange ramps), black dead pines toward the crag; normal 1-trunk trees, no bare-pillar fields |
| name tag | a corner (sky or ground) | "Grimspire Pass" / "Designed by shywolf91 and AI" |
| fog | bright mauve-amber tint, e.g. (190, 168, 176) | tune in client |

Palette (3–4 families): cool slate basalt (neutral), larch rust + lantern amber (orange), olive meadow and moss
(yellow-green), a small witch-fire green accent in the keep windows. Original assets: lich keep, mine portal with
timber head-frame, ore cart, rail switch, larch, dead pine, stone cottage set, cider press, beehive skeps,
scarecrow, lantern post, crow perches on the toll gates.

Tunnel note: under the platform the destroy rule still lets each team clear blocks by shooting from their own
destroy side, so a sealed tunnel can be reopened from a portal — but test it.

---

## 5. Island map — three concepts

| | **A. Leviathan Lagoon** (recommended) | B. Hexmoor Isles | C. Gloamhaven Stilts |
|---|---|---|---|
| identity | a black-basalt caldera ring around a bile-green lagoon; a colossal beached leviathan skeleton lies under the platform — skull on the north shore, spine across the lagoon, ribs arching over it; a ghost galleon aground on the south shore | swag2-style: one moth-shaped heath island with two witch-coven villages, and a loop of 8 standing-stone islets linked by plank bridges, violet sea | a lantern-lit fishing town on stilts over shallows, with two rocky spawn islets and boardwalk streets |
| structure | ring + lagoon + 6 islets | main island + islet loop | islets + boardwalks |
| spawn floor | z 50 | z 56 | z 52 |
| build gap (target) | ~44 from the inner shelf; rib apex never closer | ~50 | ~48 |
| spawn cover | the caldera **crest** sits between spawn and platform (built-in cover line) | stone walls only (swag2's weakness) | houses — roof-spawn risk |
| new for the project | ring island, lagoon under the platform, centre-line landmarks | archipelago loop | water-level town |
| art risk | medium (skeleton must be shaped, not primitive) | low | medium |
| play risk | lagoon damage if `water_damage` is on | open centre, bridges griefable | pile fields = lag (guide), boardwalk griefing |

**Why A:** the crest fixes the "too open" problem both island references share; the lagoon makes the centre
different from every map we've built; and the two centre-line set pieces (skull, galleon) are left-right symmetric
by nature, so they can sit on x = 256 without breaking the mirror. B is the closest to swag2's structure if you'd
rather stay near the reference.

### 5.1 Leviathan Lagoon — spatial spec `[DESIGN]`
Checked on the schematic mask (z down: "higher" = smaller z) `[RUN]`: land 35.5 % / water 64.5 % (references 60–80 % water); both spawn squares and
both build zones 100 % land; lagoon spans x 200–312 under the platform's x 206–305; mirror exact.

| element | where | heights / notes |
|---|---|---|
| sea | everywhere outside the ring and islets | z 63 plane painted (indigo at the edges → teal over reefs, the Cloud Smash backdrop trick) |
| caldera ring | ellipse (256, 256), semi-axes 205 × 150 → x 51–461, y 106–406 | solid to z 63; black sand beaches z 61 |
| spawn terrace | x 98–138, y 236–276 | flat z 50 on the outer shelf |
| crest | x 140–148, y 196–250 and 262–316 + inner baffle x 150–156, y 244–268 | top z 36 (14 above spawn), staggered so no straight line to the platform; exits ≥ 5 wide at y 250–262 (dog-leg) and round both ends |
| build zone | x 158–199, y 228–284 (mirror 313–354) | flat z 44, **no props**; gap ≈ 44 to the platform edge |
| inner descents | y ≈ 205 and ≈ 307 per side | ghat-style stepped banks z 44 → 61 with 2-high cheek walls |
| lagoon | ellipse 56 × 70 → x 200–312, y 186–326 | water painted bile-lime; same wading depth as the sea |
| spine causeway | x 253–259, y 186–326 | walkable deck z 58 with vertebra steps; the only dry crossing of the lagoon |
| ribs | every 10 in y, x 214–298 | 3 thick, tapering, feet in the lagoon floor; apex **no higher than z 44** so a rib never beats the zone gap |
| skull | north shore, x 232–280, y 150–192 | crown ≈ z 38; open jaw is a walk-through cave from the north arc to the spine; eye sockets as windows |
| ghost galleon | south shore, keel on x 256, y 318–384 | deck z 52, hold walkable with exits both sides, broken 2×2 masts, none higher than z 36 |
| satellite islets | (84, 128), (84, 384) 26 × 20; (34, 256) 14 × 26; mirrored | sea-witch hut, broken lighthouse stump, drowned bell shrine; low, far from the platform |
| bridges | 3 wide, rails, on 2×2 piles every 8 down to z 63 | flank loops ring ↔ islets (no 1×1 pile fields) |
| name tag | a corner | "Leviathan Lagoon" / "Designed by shywolf91 and AI" |
| fog | sea-mist, e.g. (172, 196, 188) | tune in client |

Palette: charcoal basalt + ash sand (neutral), bone ivory (warm neutral), bile lime lagoon + kelp moss (green),
wreck rust + lantern amber (orange), indigo-teal sea (blue). Original assets: leviathan skull, vertebra segments,
ribs with barnacles and kelp drapes, galleon hull with exposed frames, lantern buoys, sea-witch hut, driftwood
fences, crab-shell shrine.

**Sea decision (needed before building):**
1. classic — no damage; sea walkable everywhere (islandbabel).
2. cursed sea — `water_damage` > 0; every water column hurts, lagoon included; spine and bridges become the safe
   crossings (closest to swag2's "island play"). **Recommended.**
3. `boundary_damage` box around the island + islets; near-shore sea safe, edges deadly.

---

## 6. Validation plan (same harness as Drowned Cathedral v2)
Floating components 0 (unless opted in) · mirror match · spawn squares flat and clear · platform unreachable without
building · build gaps per bridgehead (zone, summit/spine/ribs) · nearest authored voxel to the platform · safe
descent graph with falls ≥ 10 removed, 0 unguarded edges · route parity 0.0 · spawn exposure ≤ 10 viewers, ≥ 15 %
hidden · tunnel / gate seal test (how many blocks close it) · art metrics (2–5 hue families, coherence 1.4–2.5) ·
live Babel load on piqueserver 1.4.2 · client look in BetterSpades / OpenSpades / aos_web · playtest.
Island only: `water_damage` per-tick rate measured in game before choosing a value.

## 7. Open questions
* Pick: Grimspire Pass (or B / C) and Leviathan Lagoon (or B / C).
* Island sea: classic, cursed (`water_damage`), or boundary box.
* Any opt-in floating scenery (e.g. ghosts or a flying ghost ship at sky level)?
* Before release: check the names against aos.party (891 maps listed; only page 1 scanned today).

## 8. Research log (2026-10-15)
* piqueserver tag v1.4.2 cloned from GitHub (commit e555d21): `scripts/babel_script.py`, `scripts/map_extensions.py`.
* 36 project VXL files decoded (remus duplicate skipped); island, Halloween and full-map tables above.
* Babel rotation guide v1.8 (project file) entries: swag2, babelpocalypse, roadisland, SkullFort, halongbabel,
  yarr, TowerDive, HallweebWIP.
* alohacraft.cc: the front page is a "VXL Test Page" with an isometric size field and no map list — not usable as a
  catalogue from here. aos.party: map pages `/view/{id}`, 891 maps on 28 pages; no Halloween names on page 1.
* Not used today: D-VXLMapPreview (no renders needed until there's geometry).

> Note (2026-10-16): the corner-tag rule changed after this doc — tags now show the map name only, no credit line.
