# Royal Parade Halloween — Halloween edit of Royal Parade Night (v1.0 + v1.1, 2026-10-21)

Source: `RoyalParadeNight.vxl` + `.txt` (Bradley & Mile, "courtesy of Sauerkraut"); no mode hooks in the .txt, so default CTF/TDM placement applies.
Goal (Dylan): keep the map basically the same, make it Halloween — horse-drawn carriages instead of cars, jack-o'-lanterns at spawn.
v1.1 (Dylan, after checking v1.0 in the alohacraft viewer): red-spawn guard → huge skeleton with a machine gun; a similar giant mummy in blue spawn; red and green slime/blood vines on the buildings. "Everything else looks good."

**Status (v1.1):** generated · exported · parser-validated (own reader + pyspades `vxl_c.cpp` load_vxl from piqueserver master 3dfc0a6, solid + surface colours identical) · v1.0 viewed by Dylan in the alohacraft.cc viewer · **not** server-loaded · **not** client-inspected in a game client · **not** playtested. My views are a numpy raycaster, not a game client.

## Original map facts (measured)
* 512 x 512 strip city: land x 0–511, y 159–347; street level z 57 (6 above water); buildings to z ~16; ground NOT solid to the bottom.
* Default CTF spawns (x 0–127 / 384–511, y 128–383, topmost voxel) cover the two roundabouts: islands centred (36,256) and (481,257), r 15.
* 19 road vehicles (10 cars, 4 fire engines, double-decker, parked bus, 2 parade floats, 1 truck) with headlight glows painted on the asphalt; 4 floating jets (flypast); giant royal-guard figure at x 393–410, y 209–219 (east = red spawn).

## Changes
| item | change |
|---|---|
| palette | colour grade: teal night tint → violet slate (3-anchor colour matrix, so the painted glows stay smooth), yellow lights → amber, grass → dead ochre, hedges/trees → autumn rust/orange, asphalt → violet-black; whites kept |
| cars (10) | black / purple / white funeral hearses, 1 black or skeleton horse, skull coachman, 2 lanterns |
| double-decker + parked bus + 1 fire engine | Victorian double-deck horse omnibus: maroon, lit windows, orange/black advertising boards, ghost passengers on the knifeboard, 2 horses |
| fire engines (2) | bow-top fortune-teller caravan (vardo), candle windows, stove pipe |
| truck + 1 fire engine | hay cart heaped with pumpkins, scarecrow mate |
| parade floats (2) | pumpkin coach on vine wheels, carved glowing face, 2 skeleton horses |
| roundabouts (spawn) | pumpkin patch: soil + vine spirals, hollow 11 x 11 x 8 giant jack-o'-lantern (carved face on ±x, crouch-in through the grin, top ≤ 9 above street so a spawn on it takes no fall damage), ring of 10 small jack-o'-lanterns |
| 23 hedge planters / 14 posts | small jack-o'-lanterns on top |
| jets (4, floating) | giant bats in the same spots (still floating, as the jets were) |
| royal guard (v1.1) | removed; **giant skeleton** (36 tall, origin 393,206, faces the boulevard): see-through rib cage, ember eye sockets, belt-fed machine gun at the hip with muzzle flash, brass ammo belt down to a 3-tier ammo-crate stack (h 10 / 7 / 3) |
| blue spawn (v1.1) | **giant mummy** (36 tall, origin 73,192, plaza north of the west roundabout, faces the boulevard): bandage wraps, green eye slit, arms forward holding a brass Gatling, hanging bandage strips, gold/lapis sarcophagus + canopic jars as its step-down |
| building walls (v1.1) | colour-only vines and drips from roof/wall top edges (seed 1031, ~480 strands: green slime vines, crimson blood vines with leaves, blood drips, glowing slime drips); no geometry change, so no new climb routes |
| street | amber lantern glow pooled around every new lantern (74) |
| water | dark violet; painted "Royal Parade / By Bradley" credit kept, recoloured orange/bone |
| .txt | name 'Royal Parade Halloween', version 1.1, authors kept, water_damage 2, heavens_color (150,112,168,255) in extensions, fog (160,128,176) |

## Checks
* Every new prop is face-connected to the street (checkprops.py); the only floating pieces are the 4 bats and 19 original 2-voxel edge stubs.
* Clear street width beside each carriage is the same as beside the original vehicle, or 1 narrower.
* Default spawn landing (v1.0): street-level share 68.4 → 66.5 % (blue), 68.6 → 66.6 % (green); the extra spawns land on pumpkins and carriages.
* Giants: a few head/shoulder columns of each are spawn candidates (topmost voxel). The step-down routes (gun → crates/sarcophagus → street) keep each drop ≤ ~8–10 by design, but this is **untested in game**; the original guard (20 tall) had the same issue.

## Generator
`vxl.py` (reader/writer), `grade.py`, `props.py` (original prop models incl. `giant_skeleton`, `giant_mummy`), `vines.py` (wall painter), `convert.py` (deterministic, seed 1031; needs `lab57.npy` = scipy label of solid z<57 on the original), `checkprops.py`, `raycast.py`.

## Open / next
* Load on the server and look at it in OpenSpades/BetterSpades/aos_web; check the spawn-on-giant descent and how the fog and heavens_color change the look.
* Optional extras not done (they would change the map): bunting across the boulevard (makes a rooftop bridge), moon / extra sky decor, cobwebs.
