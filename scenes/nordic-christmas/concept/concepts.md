# Nordic Christmas (viking-age yule) - three concepts

Brief: stock piqueserver 1.4.2 Babel (standard, no assist structures) that also plays in stock CTF; full 512x512; viking-age yule village; polar night + glow blocks; frozen water only (ground solid, ice = ice-coloured land, z=63 may be painted ice); sky decor (moon, sleigh); fog matched to palette.

All images are "concept mockup - not a map". Coordinates: x 0-511, y 0-511, z 0 = sky top, 63 = bottom. West half described; east is x' = 512 - x.

## Shared rules for all three (so each concept only states differences)

- **Tower zones**: W x 176-208, E x 304-336, y 240-271 (32 wide, 48-80 from centre). Ground under both platform ends (x 206-211 / 300-305, y 240-271) is solid. No stairs/ramps on the enemy-facing side. Towers are built from the ground.
- **Fronts**: spawn (x 98-138) to tower zone: open lane y ~225-287, dressed only with low passable details (drystone walls <=2, haystacks <=3 with conical tops, woodpiles, sleds, drying racks, rune cairns <=3, split-rail fences with gaps >=7).
- **CTF strip** (get_random_location, no hooks): spawns, intel and tent land on the TOPMOST voxel of a random column in Blue x 0-127 / Red x 384-511, y 128-383. So the strip holds NO roofs, no standable treetops, no flat tops. Only gently modelled ground, low cover (<=3), steep/tiny tips. Buildings and forest sit at x >= 128 or y < 128 / y > 383. The intel will land in this strip, ~380+ voxels from the enemy. CTF raiders therefore cross the whole map and fight in the centre/flanks; no authored cover in the strip means a defender can see the intel; the strip is wide open on purpose, defenders use the dressing and the adjacent village wing.
- **Babel spawn cover** must not sit inside the +-20 squares (x 98-138, y 236-276). Cover is placed at 24-60 voxels from base (berms, spruce groves, drystone, low turf walls). Measure with `aosmap/sightline.py` (<=10 platform viewers per spot, >=15 % hidden).
- **Under the platform** (x 212-300, y 240-271): 15-45 % coverage with >=25 air, keep z <= 2 empty.
- **Palette cap**: snow max channel ~212, floors luma >= 40. Polar night = darker palette + bright glow.
- Sky decor >= 60 from the platform, never over spawn squares; it reads only within ~65 voxels so it hangs over the flank routes. Floating pieces are opt-in; here the owner asked for them. State the collapse caveat (breaking a player block next to a floating piece drops it for the round); keep >= 8-10 air below, none over play centre.
- Glow blocks are the Christmas light: warm window/hearth amber, a little rune-blue, aurora teal. Aim ~3-5k glow blocks, never in 1-voxel stripe patterns.
- No copyrighted characters: "Yule rider" sleigh with generic reindeer (no red nose, no named characters).

---

# CONCEPT 1 - "Hrafnfjord" (the raven-fjord thing-field)

**1. Pitch.** A frozen fjord runs the full height of the map and swells into an ice bay under the Babel platform; a Thing-Rock isle, rune ring, Yule pyre, smithy and mead hall pack the bay's shores. A viking law-assembly at midwinter.

**2. How it plays.**
- Spawn: shelf of snow meadow with berms and spruce at the sides. Walk east across the open lane to your tower zone (~50 voxels). The bay shore is 20 voxels beyond.
- Tower race: bay is open ice, so the platform is fully visible; the boat-shed rows (x 190-214, y 190-228 / 284-322) give cover for the builders on both sides without blocking the front. Beached longships in the sheds can be climbed (stern deck, 6 high) for rifle perches.
- Centre fights: the ice bay is a duel ground; Thing-Rock isle (r ~17, 10 high, rune-stone ring, hollow barrow room beneath open on 3 sides) is the contested mid-point. Pyre (north shore) and rune ring (south shore) are the two cover clusters; smithy and Skali mead hall bracket each team's wing.
- Flank: forested fell ridges at y ~100 and y ~412 (156 from centre) with the Raven Gate arch spanning the ice at the north and a stave church on each fell. The ice lane up the fjord is the fast-but-exposed route.
- Sniper: Raven Gate arch top (26 high, reached by outside stair on the *team-neutral* north face), church bell loft, longship masts. Builder: sheds + low walls + the open anchor ground. Rusher: ice lane and bay, mead hall as the room to clear.
- Down: all knolls have 2-wide stair or slope sides; no spawn is raised.

**3. Layout (512 grid).** Land z ~40 (spawn z 40, anchors z 38; ice z 44, so shore banks are 4 high). Ice fjord x 231-281 whole height, bay ellipse centre (256,256) rx 46 ry 72. Thing-Rock isle (256,256) r17, under the platform (ensure coverage 15-45 %). North forest belt y 0-112, south y 400-511. Wings: Skali mead hall (132-178, 150-174), smithy (140-164, 186-206), longhouse (140-178, 296-320), boat sheds as above, stave churches (138-166, 78-106). Raven Gate (232-280, 96-108) across the ice at x 256. Pyre (244-268, 136-160), rune ring centre (256,352) r20. Farm pond (frozen) in strip at (52,330) r 30x18.
CTF strip: open snow farmland, frozen farm pond, haystacks, low fences, sleds, turf mounds <=3. Villages sit just outside at x 130-180 and in the forest belts. Intel lands in the strip; flows: ice lane (centre), the fell ridges (flank).

**4. Landmarks.**
- **Raven Gate** (26 tall stone arch spanning the ice, 48 wide, glowing runes) - the map's name image.
- Yule Pyre (16 high stacked log bonfire, fire-glow core, ringed by logs).
- Thing-Rock isle with runed Lawspeaker's rock and barrow room.
- Skali mead hall (46x24, 2 floors, hearth, benches, loft).
- Beached longship sheds (2 x 2, climbable decks).
- Stave church on each fell (dragon-head gables, bell loft).
- Frozen farm pond with ice-fishing holes (decor in the strip).

**5. Distinctive.** Ground Babel with a wide ice-bay centre (not a market, not a ship at centre; ships are props on the shore). A strong N-S lane the rotation lacks.

**6. Numbers.** Spawn floor z 40; anchor ground z 38 (gap ~36 per side); front dressing <=3 high; centre isle top z 30; stave church spire z 8.
**Names/art.** Palette families: (a) night snow-slate (150,160,182)/(196,204,214); (b) tarred timber (96,68,46)/(132,92,58); (c) turf/pine (44,74,60)/(72,98,70); (d) ice (112,158,186)/(150,196,214) kept cool-green-grey not saturated blue. Glow: amber windows (255,176,64), pyre (255,120,30), runes (120,180,255), aurora (90,255,200). Fog (176,164,196) lilac-mauve; heavens_color (44,40,88,255). Corner tag SW ground (x 8-60, y 470-500), map name only. Underground: NO (the open ice bay is the feature; an underground layer would fight the fjord's sightlines).
Sky decor: crescent moon (256,38) z 8, r 16 glowing; Yule-rider sleigh + 6 reindeer arc over north fell at (310-440, 60) z 10-14; aurora ribbon along y 20-40 (glow, 2 high).

**7. Risks.** Art: ice bay and ice lane could read as "icy-blue everything" (Frozen Icebreaker); mitigate with warm timber/amber glow, grey-green ice. Play: bay is open, snipers at the Raven Gate dominate the north; add pillar cover and two shielded bays. Rules: strip forces villages away from spawn edges; the fjord splits the map N-S (stay passable: ice is walkable and the bay is 92 wide, no narrow chokes).

---

# CONCEPT 2 - "Haugr" (the barrow downs)

**1. Pitch.** Windswept heather moor with burial mounds; twin hollow barrows flank the platform lane and an underground "draugr road" links them. Yule lights burn on the graves.

**2. How it plays.**
- Spawn in shallow dells ringed by rim hills 26-36 out (z -6); exits are wide gaps toward the platform so no sealing. The front is a gently falling moor.
- Tower race: tower zones are moor ground with rolling cover on the north/south sides; the barrow hills overlook but not the build zone. Barrows are 14 high, 30 radius, with entrances on all four sides.
- Centre: King's Barrow (256,190) and Queen's Barrow (256,322): enterable burial halls with a grave ship outline, glowing grave goods. Underground draugr road (z 50-57) joins both, plus spurs to shafts at (160,130) and (160,382). Surface: Seven Sisters stone ring (178,160)/(178,352), dwarf forge cave (145-177, 306-332).
- Flank: frozen river bank routes y ~120 / 392 (136-144 from centre) with the Whale-Jaw Gate (256,92) bridging the river.
- Sniper: Whale-Jaw Gate crown, rim hills (but exposed on the moor). Builder: dells + moor swell cover. Rusher/flanker: underground draugr road, river bank.
- Down: all slopes <=1:2 walkable; barrow tops reach by stairs outside.

**3. Layout.** Land z 42-46 rolling, anchors z 42 (gap ~40), rim hills z 34-36. River N y 70-102, S y 410-440, ice z 46. Shieling hamlets (20-100, 40-66) outside strips. Stave church on a rise (140-166, 392-416). CTF strip: grave field - rounded cairns <=2, stone stubs, no roofs; intel lands among cairns. Underground: **YES** (barrow passages). Barrow tunnels z 50-57 under the platform, with openings (enterable from the barrows, 7+ wide) never vertical shafts under tower zones; ground stays solid elsewhere, bottom ice-painted z 63.

**4. Landmarks.** **Whale-Jaw Gate** (24 tall paired jaw bones, map's name image), King's Barrow hall, Queen's Barrow with ship-grave, Seven Sisters ring (7 x 9-high menhirs), dwarf-forge cave (glowing forge), stave church, wolf-pit snow fort (decor).

**5. Distinctive.** Rolling terrain + underground play (only underground-yes concept), more brown/heather mood, quieter Christmas read (candles on graves, Yule lights).

**6. Numbers.** Spawn floor z 42; anchors z 42 (gap ~40); rim hills z 34; barrows top z 28. Palette: (a) dusk heather (96,86,104)/(122,110,128); (b) snow patches (176,182,196) <=55 % cover; (c) turf-brown (84,74,58); (d) ice (132,168,186). Glow: grave candles amber (255,176,70), forge (255,110,30), rune teal (100,230,220), aurora (150,255,170). Fog (176,190,172) sage-grey; heavens_color (38,44,70,255). Corner tag SE ground (x 450-505, y 470-500). Sky: moon + halo ring (80,456) z 10; sleigh arc (330-470, 50) z 8-12; falling-star glow shards over the south river.

**7. Risks.** Art: brown-grey moor could read dull; use varied heather, glow density. Play: rolling terrain makes spawn-exposure measuring and tower anchors need care; underground layer adds trap risk (needs interiors/reachability test, every tunnel with 2+ exits). Rules pull: underground requires owner consent ("only if it works well"); outer rim hills near spawn pull against "open fronts" (they sit behind/side only).

---

# CONCEPT 3 - "Skogarborg" (the Yule wood)

**1. Pitch.** A dense winter forest with a grand antler-gabled hall and a ring fort; exposed frozen lakes on the north and south flanks. Closed, atmospheric centre vs open ice flanks.

**2. How it plays.**
- Spawn in a cleared field fringed with spruce groves outside the squares. Open front lane (y 224-288) cut through the forest.
- Tower race: forest edges flank the tower zones; lane open. Platform area has a sparse birch/pine grove (15-45 % coverage, >=25 air) so towers rise from a clearing.
- Centre: Yule Wood (x 186-326, y 166-346, groves with 7-10 gaps, many trails) with 4 enterable hunting lodges, Antler Hall (north, 46x24 two floors) and the ring fort (south, r 28 palisade ring with four gates and four barracks). Fights go grove to grove.
- Flank: frozen lake ice routes (y ~68 / 444, 188 from centre) with beacon towers (stair-up, glowing fire) - fast, exposed, sniper heaven, so the forest centre is the counter.
- Sniper: beacons, Antler Hall roof ridge walk, ring fort gate towers. Builder: forest edges + lodges. Rusher: Yule Wood trails.
- Down: beacons and hall have inside stairs; forest slopes gentle.

**3. Layout.** Land z 40 (spawn z 40, anchors z 40, gap ~38); lake ice z 44. Lakes (256,68) 78x34 and (256,444) 78x34. CTF strip: felled charcoal clearings - stumps <=2, log stacks, brushwood, thin saplings; true forest starts at x >= 128 and y < 128 / y > 383. Hunting lodges (180-204, 176-196) and (180-204, 316-336). Antler Hall (234-280, 140-164); ring fort (256,356) r 28.
Underground: NO (forest atmosphere would be lost; tunnels not needed).

**4. Landmarks.** **Antler Hall** (elk antler gables 12 high, map's name image), ring fort "Fyrkat" (geometric ring with gates), beacon towers (24 high, 4), hunting lodges (4), charcoal-burner clearings with huts, lake-ice fishing weirs (decor).

**5. Distinctive.** Forest-dominant ground Babel (vs rotation's snowy villages/ice) with a strong closed vs open contrast.

**6. Numbers.** Palette: (a) spruce night (28,52,44)/(44,72,62); (b) bark/timber (84,60,44); (c) snow (168,176,190) cap 212; (d) glow-lit bronze (170,126,60). Glow: windows amber (255,176,64), beacons (255,120,30), wreath (255,210,90), aurora teal (90,255,200). Fog (190,176,150) straw-sand (hue unused by palette, neutral between blue/red); heavens_color (30,46,64,255). Corner tag NW ground (x 8-60, y 8-40). Sky: moon (256,30); giant Yule wreath ring (256,484) r 26 vertical, glowing; sleigh arc (80-200, 480).

**7. Risks.** Art: dark forest may look black, so keep floor luma >= 40 and brighten with glow trails; vegetation density can bring lag (groves, not even scatter, no 1x1 pillar fields). Play: forest centre vs tower fronts - dense trees must stay off the front lane or the platform area becomes enclosed and builder pockets arise; test trap cells. Rules: "nothing solid between spawn and tower zone" - forest sits beside the lane, not on it.

---

## Recommendation

**Concept 1 (Hrafnfjord).** It is the most legible for both modes: the open ice lane + bay gives clear Babel play and an obvious CTF flow, the ice/forest/strip layout fits the CTF strip with villages cleanly outside it, and it has the strongest one-off hero (Raven Gate) plus unique pyre and Thing-Rock. It also avoids concept 2's underground-trap risk and concept 3's dark-forest/lag risk. Mitigate the "icy-blue" look with warm timber and amber glow.

## Rule tensions

1. CTF strip x 0-127 / 384-511, y 128-383 vs "pack the edges with a village": buildings/forest pushed to x >= 128 and y < 128 / y > 383; strips are open fields.
2. Babel spawn cover vs open fronts: cover only at 24-60 from base, not in the ±20 squares; trade-off reported if hidden share < 15 %.
3. Floating sky pieces opt-in (owner asked): keep >= 60 from platform, >= 8-10 air, none over spawns; collapse caveat.
4. Concept 2 underground layer: needs owner approval and extra reachability testing.
5. Concept 3: forest density vs front openness/lag.

## Questions for the owner that change the concept

1. Is the CTF strip's open farmland (no buildings in the 128x256 corner) acceptable, or should the strips get steep-roof buildings anyway?
2. Underground layer: yes for concept 2 only?
