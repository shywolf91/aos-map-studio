# Northgale Freighter v1.2 (v1.0, v1.1 kept): classic island Babel on a freighter (2026-11-16)

## v1.2 (2026-11-16): ship detail pass + storm fog `[USER]`
Owner: loves the map, but a user said the ship "looks rather unpromising" next to their oil-platform map. Asked what
to improve on the ship only, and for darker fog "but not pitch black night" so it looks stormy and the glow pops.
He chose all four proposed upgrades and fog "Storm dusk". The platform screenshot was a craft reference only: nothing
copied. Gameplay layout unchanged (same SPEC numbers for spawns, fronts, strip, anchors, holds, routes; same seeds).
`maps/northgale_freighter_v1_2/`, SHA-256 `e4fad6a9…`.

| upgrade | what changed |
|---|---|
| deck & rails | Steel-grey tiled deck (soft 1-in-8 plate seams, rust patches). Hatch panels stay green with white borders, numbers at double size. Yellow walkway lane edges. 2-wide yellow/dark hazard stripes round crane pedestals, deckhouses, stair heads and the deck hatch. Yellow handrails (posts every 3, continuous top rail) on every bulwark: 1,198 columns, hull, forecastle and stern. Rails on the long sides of the open deck hatch (ends left open). |
| skyline | The 4 crane jibs are raised red/white lattice booms (2×2, 44 long), reaching outboard over the sea from z 25 to z 10, with a red tip light, a cable and a yellow hook block. 3D distance to the platform is 37 or more; they point away from it. Bridge-roof helideck: slate deck, white perimeter, yellow touchdown circle, white H, yellow kerb, 8 green perimeter lights, stairs up from both bridge wings. Radar mast moved to the roof corner, 3 white radar/satellite domes. Taller, wider funnel (top z 3) with a 14-lump billowing plume, dark to pale downwind. |
| deck kit & lights | Red fire main and grey service pipe along both hatch edges (1 high, stepped over). Red fire stations, life-raft canisters on racks, gooseneck vents, barrel clusters. 12 floodlight masts along both rails with warm lamps. |
| hull & bridge | Bulbous bow at the waterline. Anchors with hawse pipes on both bows. Soft hull plate seams, a pale belting line, lit forecastle portholes. Navy band at every bridge floor, orange roof band, 45 ceiling lamps inside the bridge rooms (light shows through the windows). |
| fog / sky | fog (170,164,190) → **(112,114,134)** "Storm dusk"; heavens_color (52,58,96) → (44,48,70). This is a per-map exception to the bright-fog rule, by owner request. Floors still luma ≥ 40 (`enforce_brightness`). |

Glow sources 144 → 213. Checks `[RUN]`: all 19 kit rows pass, unchanged from v1.1. Spawn exposure is the same:
blue 8.41 / 16.3 %, red 7.56 / 17.5 %. Interiors 45 / 45 (adds the two helideck stairs). 0 floating, 0 traps,
mirror 0. Centre rule N/A. Live probe passes, classic table 4 / 8. Same seed → same SHA-256 in fresh processes.
Not client-inspected: the darker fog and the glow need a look in aos_web or BetterSpades.

---

# v1.1 record

## v1.1 (2026-11-16): bigger lighthouses with glow `[USER]`
Owner feedback on v1.0: "the map is awesome. one slight tweak. can we make the lighthouse prop a tad bigger and add
glow blocks inside and maybe around". Only the two lighthouses changed (same layout seed, same veg seed 3975672189);
v1.0 stays in `maps/northgale_freighter_v1/`, v1.1 is `maps/northgale_freighter_v1_1/` (SHA-256 `70624aeb…`).

| | v1.0 | v1.1 |
|---|---|---|
| tower | solid striped post, r 2.3, 14 tall, 1 lamp | **enterable** tower r 6 (13 wide), 26 tall (ground z 52 → gallery z 26, cap z 15), red/white bands, stone plinth r 7.5 |
| inside | none | door toward the ship, square winding stair (2-wide treads, 2 thick, round a 3×3 core) to the gallery, window slits |
| top | small gallery | gallery r 8.2 with rail, open lantern room (8 posts, red roof r 6.2, cone cap, finial) |
| glow | 1 white lamp | 30–31 sources each: 3×3×2 light cluster + bright top on the stair core, 4 wall lamps spiralling up inside, 4 amber lamps on the gallery rail, 2 door lamps, 5–6 lamp posts round the base (amber) |

The lighthouses are placed after the mirror (a winding stair can't be mirrored), and they are identical.
Their boxes (x 243–269, y 105–131 / 381–407) are listed as cosmetic boxes for the mirror test.
Total glow sources: 93 → 144. Checks: all 19 kit rows pass as in v1.0 (interiors now 43 / 43 including both
lighthouse bases and galleries; 0 floating; 0 traps), centre rule N/A; live probe passes; classic table 4 / 8,
unchanged. Rebuild: `python scenes/northgale_freighter/nf_main.py out/nf 3975672189`. Renders `13_lighthouse.png`,
`14_lighthouse_inside.png`. Glow intensity can't be judged in the numpy previews; check it in a client.

---

# v1.0 record

**Status:** specified · generated · exported · parser-validated (own reader round trip byte-identical; pyspades 1.4.2
`generate()` byte-identical) · **server-loaded** (piqueserver 1.4.2, `game_modes.babel` + `babel_script` +
`map_extensions`, probe in `maps/northgale_freighter_v1/probe.json`) · **not** client-inspected · **not** playtested.
Every image in `maps/northgale_freighter_v1/renders/` is a numpy preview, not a client capture.

## Brief and owner answers (2026-11-16)
"Generate a Tower of Babel map, classic island map", with a screenshot of a cargo freighter (red/white hull, green
deck, tarped cargo and containers, a white bridge block with a funnel at the stern, a mast at the bow). Answers:

1. **Ship role:** the ship is big enough to act as the classic island. Both spawns and the tower zone are on the
   ship. There are areas under the deck to explore and use. The deck is at a middle height, not up near the platform.
2. **Shape:** no island as such; the cargo ship is the "island".
3. **Climate:** cold north sea.
4. **Water / extras:** walkable shallows and islets, sky decor, glow / night mood, and boundary damage ("aka deep
   sea").

The owner supplied the concept, so no three-concept round. Interpretations `[DESIGN]`:
* **"Middle height"** = the main deck at floor z 40: 23 above the sea and 39 below the platform.
* **"Deep sea"** = the `boundary_damage` box x 8–503, y 72–440, as on Janjira Sound. Inside it the sea is walkable
  (`water_damage 0`). Outside it the sea is painted darker beyond a line of lit buoys.

Stock Babel, no assist structures. Name "Northgale Freighter" picked by Claude; the ship's name on the hull is
"NORTHGALE". There is no copied branding from the screenshot.

## Layout (all numbers in `scenes/northgale_freighter/nf_spec.py`)
| element | where | notes |
|---|---|---|
| hull | x 13–494, beam y 204–308 (105 wide), sides z 38–62 | Raked bow (west, behind blue) and rounded counter stern (east, behind red). Oxblood topsides, white sheer strake, dark boot-top, rust streaks, draught marks, "NORTHGALE" on both bows and quarters. |
| main deck | floor z 40; hatch panels 1 high (z 39) in bays x 78–124, 153–198, 218–294 (mirrored) | Grey side gangways along both rails with yellow walkway lines. Hatch numbers 01–06. Bulwark 2 high. |
| spawn squares | x 98–138 / 374–414, y 236–276 | Deck z 40 with hatch panels z 39 on the rear two-thirds. Solid below (no hold under the squares), so 0 roof columns. |
| anchors | x 200–216 / 296–312 | Plain flat deck z 40, solid below, prop-free. |
| fronts | x 139–199 / 313–373 | 11 low objects each: edge container stacks (10 tall), single containers, tarped machinery, crates, cable drums, pallets, mushroom vents. |
| under the platform | x 212–300 | 2-high container stacks (top z 30, 28 air to the platform), a tarped excavator, crates, drums, and an open deck hatch with a 1-high coaming at the centre (x 244–268, y 246–266). |
| centre bands | y 207–235 / 277–305, x 150–362 | Four deck cranes: hollow pedestals with spiral stairs to the cab at z 28, jibs stowed on rest posts. Four companionway deckhouses. Containers, tarps, forklifts. |
| tween deck | floor z 50, x 80–432 | Full-beam fore and aft compartments, linked by side passages past the solid blocks under the spawns and anchors. Bulkheads with doors, pillars, open containers to hide in, lamps. Light wells over the lower hold. |
| lower hold | floor z 59, x 176–336, y 210–302 | Twin-cab diesel locomotive cargo, pillars, lamps. Stairs up to the tween deck. Side ports to the sea at x 250–262 on both sides, with steps from the water. |
| access | | 4 companionways per team (deck ↔ tween), 2 hold stairs per team (tween ↔ lower hold), 2 accommodation ladders per team down the hull to the sea (x 150–176 / 336–362), 2 side ports (centre), forecastle stairs. |
| bow (one-off, west) | x 13–72 | Raised forecastle z 35 with a store room below (door at the break), foremast with two lookout rings, yard and masthead light, twin windlasses, chain, bollards, stem light. |
| stern (one-off, east) | x 440–494 | Bridge x 446–478, 5 storeys (z 40 → roof z 10): real rooms, stairs to every floor, doors W/N/S. Bridge wings at the wheelhouse with green/red side lights, lifeboat balconies with orange enclosed lifeboats, radar mast, funnel (white, orange band, black top) with an attached smoke plume, poop deck with mooring winches and a flagstaff. |
| islets | 6 main (r 15–22) + 8 rocks, y ≤ 126 / ≥ 386 | Granite, lichen, heather, dark pines. Two fisher huts with lamps, two red-and-white beacons (white light; v1.1: enterable lighthouses), four plank piers toward the ship. |
| sea | z 63 painted | Lit shallows ramp inside the boundary, foam along the hull and beaches, a soft moonlight glitter streak. Deep navy outside the boundary, marked by 12 lit buoys (green north, amber south). |
| sky (opt-in floating) | 5 gulls, 4 clouds | All placed by `aosmap.kit.sky.place`: ≥ 60 from the platform, never over a spawn square, ≥ 8 air below. The collapse caveat applies: breaking a player block that touches a piece drops it. |
| tag | "NORTHGALE FREIGHTER", SE corner | Painted on the deep sea, outside the boundary. |
| `.txt` | fog (170,164,190), heavens_color (52,58,96,255) | `extensions`: `babel`, `water_damage 0`, `boundary_damage {left 8, right 503, top 72, bottom 440, damage 1}`, `glow_enabled`, `glow_stored_colors` (93 sources). Author `shywolf91 + AI`, no spawn hooks. |

Symmetry: x512 mirror of the core x 73–439, with the 1-column platform offset accepted. Bow and stern are cosmetic
one-off boxes x 0–72 and x 440–511 (y 186–326). The spawn squares are mirror-equal. The rear backdrops differ: blue
has the forecastle and foremast, red has the bridge. Both pass the 30 % backdrop rule.

## Validation (release build, veg_seed 3975672189) `[RUN]`
| check | result |
|---|---|
| reader / re-encode / pyspades | identical; 0 / 20k mismatches; z 63 solid |
| floating | 0 unintended; 9 expected sky pieces |
| mirror | 0 mismatches outside the cosmetic boxes |
| platform volume, ground under ends | clear; both ends z 40 flat |
| spawn squares | z 39–40, 0 water, 0 roof columns; the probe's 400 spawns per team all land at z 39–40 |
| routes | safe descent to the tower zone; enemy spawn reachable; flank north / south; 0 trap cells; platform not reachable on foot |
| interiors | 39 / 39 reachable with a way out (holds, companionways, crane cabs, bridge floors, wings, balconies, forecastle, huts, side ports) |
| spawn exposure (calibrated) | blue 8.41 viewers, 16.3 % hidden; red 7.56, 17.5 %: **both pass** (≤ 10 / ≥ 15 %) |
| zone rules | front dressing pass (11 objects, 18 %, all ≤ 10 tall, worst section 68 % free); spawn cover pass; under-platform pass; centre footprint **N/A** (central zone 45 % land: the sea). Relaxed measurement: median footprint 68 cells, pass. |
| build gap | 26 blocks from the highest reachable point near the platform (crane cab roof, z 28) to platform level, the same for both teams; 38 from the deck |
| nf_checks | 0 ground columns outside the boundary; water 75.7 %; anchors flat, 0 props; 0 solid at z ≤ 3 near the platform; fronts max 10 tall; crane clearance 27.7 to the platform (3D) |
| live probe | loaded, platform 3,200 cells, `.txt` loaded, babel extension on, blue spawns x 98–138, red x 374–414 |
| determinism | same veg seed → same SHA-256 in fresh processes (`15d46926…` for seed 12345) |

### Classic island table (`tools/island_style_metrics.py`): 4 / 8 in range
| metric | classic | this map | why |
|---|---|---|---|
| water_pct | 68–84 | 75.7 | in range |
| landmasses | 1–10 | 11 | ship + 6 islets + rocks (the brief asked for islets) |
| neck width | 40–150 | 105 | in range |
| struct components | 0–90 | 59 | in range |
| struct vox / land col | 0–1.8 | 3.9 | the deck sits over the holds, so the whole ship counts as "structure" |
| roofed % | 0–13 | 58 | the deck over the tween deck and holds (the brief asked for areas under the deck) |
| hue families | 1–4 | 7 | ship palette (oxblood, white, deck green, tarp blue, orange, container colours) |
| surface colours | ≤ 26000 | 12.8k | in range |

The misses come from the brief (a hollow ship is "roofed" by definition), not from dense authoring.

## Known limits / open points for the owner
* **The cranes are the highest reachable points near the platform.** The cab roofs are at z 28, 27.7 voxels (3D)
  from the platform edge, which cuts the build from 38 to 26 blocks. They are symmetric and stock Babel still holds
  (the platform can't be reached on foot). Say if you want them lower or the jib-rest end moved away.
* Asymmetric ends: blue's backdrop is the forecastle and mast, red's is the bridge. Both are behind the spawns and
  outside the front; the bridge is much taller. The bridge roof is 141 from the platform, so it gives no sniping line.
* The flank is a wade: down a gangway, along the shallows past the islets, back up the enemy's gangway or through a
  side port. It is long (graph model: about 540 steps spawn → spawn).
* The `boundary_damage` and `water_damage` rates are untested in game. `map_extensions` must be in the script list.
* The smoke plume and the foremast rings are attached decor, not floating.
* A numpy preview is not a client: check fog, glow and night grade in aos_web or BetterSpades.

## Regenerate
```bash
python scenes/northgale_freighter/nf_main.py out/nf 3975672189      # exact release map; omit the seed for a new vegetation draw
python -m aosmap.kit.probe out/nf --mode babel
python tools/island_style_metrics.py out/nf/northgale_freighter.vxl --json out/nf/island_style.json
python scenes/northgale_freighter/nf_render.py maps/northgale_freighter_v1
```
