"""Janjira Sound: the single source of truth for every number in the generator (stage 1 = graybox).

A [recreate] of *newfort* by JoJoe Stinky (out/recreate/newfort/analysis.md): four wooded islands around a sand
causeway on the Babel axis, a sea fort at each spawn, two inner watch towers per side, hut islets at the ends,
> 75 % sea, 180-degree rotation symmetry. Theme: Konkan-coast sea forts (basalt curtain walls, round bastions with
small domed pavilions, banyan and coconut groves, monsoon sea). Classic island style (docs/classic_island_style.md).
Stock Babel (piqueserver 1.4.2 babel_script).

Symmetry 'point512': (x, y) -> (512 - x, 512 - y). Every number below is the WEST (blue) half; the source half is
x < 256 plus the x = 256 column for y <= 256 (aosmap.kit.symmetry). The baoli is self-symmetric and authored whole.
One-offs placed after the rotation (the beached dhow) are listed as cosmetic boxes.
z = 0 is the sky top, z = 63 the bottom; a "floor z" is the solid voxel a player stands on. Boxes are inclusive.
"""

SPEC = {
    'name': 'Janjira Sound', 'file': 'janjira_sound', 'version': '1.0', 'stage': 'art',
    'layout_seed': 20261115, 'axis': 'point512',
    'fog': (190, 184, 178),
    'boundary': {'left': 32, 'right': 480, 'top': 160, 'bottom': 352, 'damage': 1},
    'water_damage': 0,

    # ------------------------------------------------------------------ elevations (floor z)
    'z': {'sea': 63, 'lip': 62, 'beach': 61, 'land': 60, 'dune': 59, 'spawn': (59, 60), 'fort': 59,
          'anchor': 57, 'islet_knoll': 56},

    # ------------------------------------------------------------------ Babel (stock 1.4.2)
    'spawn': {'base': (118, 256), 'half': 20, 'keep_margin': 2},      # square x 98-138, y 236-276
    # flat anchor ground under the platform end; y 240-272 so the rotated red anchor (y 240-272) covers the stock
    # platform rows 240-271 too (the platform is centred on 255.5, the rotation on 256)
    'anchor': {'x': (200, 216), 'y': (240, 272), 'z': 57},
    'front': {'x': (139, 199), 'y': (236, 276)},
    'strip': {'x': (212, 300), 'y': (240, 271)},

    # ------------------------------------------------------------------ land shapes (west half; rotated)
    # causeway: shores wander outside the lane edges (u = 0 cove at the lane edge .. shore_max lobe), straight
    # (u = 1) beside the anchors and at the plaza; two sand spits per side reach into the channels
    'causeway': {'x': (92, 256), 'y': (235, 277), 'slope_x': (146, 200), 'shore_mean': 4.0, 'shore_amp': 5.0,
                 'shore_max': 9, 'beach_slope': 0.7,
                 'spits': [(172, 'N', 4), (234, 'S', 4)]},                                  # (x, side, length)
    'channels': {'north_y': (228, 234), 'south_y': (278, 284), 'x': (160, 247), 'width': 7},
    'plaza': {'x': (92, 150), 'y': (222, 290), 'corner_r': 8, 'mound_cell': 9},
    'fort_ground': {'x': (86, 97), 'y': (198, 314), 'corner_r': 2},        # paved strip at the wall foot (z 59)
    'fort_apron': {'x': (78, 124), 'y': (186, 326), 'corner_r': 16, 'warp': 8,   # natural ground round the fort
                   'outcrop': (0.66, 0.76), 'outcrop_x_max': 86},              # noise thresholds -1 / -2
    'gate_path': {'x': (76, 85), 'y': (251, 261)},
    'islands': {
        # (name, cx, cy, rx, ry, y clip (lo, hi), knolls [(x, y, R, z)])
        'NW': (185, 206, 62, 23, (0, 227), [(172, 203, 30, 55), (220, 203, 16, 57)]),
        'SW': (196, 310, 52, 26, (285, 511), [(198, 312, 28, 55)]),
    },
    'island_lobes': {'NW': [(146, 200, 24, 15), (228, 199, 20, 15), (196, 192, 26, 12)],
                     'SW': [(158, 318, 20, 15), (230, 316, 18, 15), (204, 326, 26, 12)]},
    'island_x_max': 247,
    'edge_noise': 0.22, 'warp': 7,
    'islets': [(64, 216, 16, 53), (66, 296, 16, 53)],               # (cx, cy, r, knoll z)
    'bars': [((74, 226), (88, 232), 2.5), ((76, 286), (88, 280), 2.5),   # islet -> fort sand bars (half width)
             ((70, 240), (66, 228), 2.5), ((70, 272), (68, 282), 2.5)],  # rear sandbank -> islets
    'rear_spit': {'x': (58, 85), 'y': (242, 270), 'dune': (67, 256, 15, 54)},   # gate -> sandbank (z 60 at the
                                                                                 # gate), a dune knoll behind
    'mid_islets': [(256, 196, 6), (256, 316, 6)],                      # flank hops in the mid channel

    # ------------------------------------------------------------------ fort (blue; rotation gives red)
    'wall': {'x': (86, 91), 'y': (204, 308), 'walk_z': 47, 'gate_y': (252, 260), 'gate_h': 4,
             'casemates': [(214, 222), (238, 248), (264, 274), (290, 298)],      # y ranges (rooms in the wall)
             'stairs': [(234, -1), (278, 1)]},                                     # (first step y, direction)
    'corner_bastions': [(96, 204), (96, 308)],
    'corner_bastion': {'r': 10, 'wall': 2, 'floors': (53, 47), 'terrace': 39, 'steps_per_turn': 22},
    'gate_bastions': [(150, 226), (150, 286)],
    'gate_bastion': {'r': 6, 'wall': 2, 'floors': (), 'terrace': 45, 'steps_per_turn': 9},
    'watch_towers': [(220, 203), (190, 314)],
    'watch_tower': {'r': 8, 'wall': 2, 'floors': (49,), 'terrace': 41, 'steps_per_turn': 14, 'mast_top': 24,
                    'yard_wall': (12.0, 13.2, 3, 0.55)},    # low laterite yard wall: r0, r1, height, gap half-angle
                                                             # (rad) centred on the door
    'tower_platform_clearance': 28,                     # 3D distance from any tower voxel to the platform footprint

    # ------------------------------------------------------------------ islet buildings
    'shrine': {'x': (66, 74), 'y': (208, 216), 'door': 'S'},           # one-room domed shrine on islet N
    'hut': {'x': (64, 71), 'y': (297, 304), 'door': 'E', 'porch': 4},   # fisher hut with a porch on islet S

    # ------------------------------------------------------------------ props (low, real, chunky)
    'front_props': [
        # (kind, x, y, arg) on the blue front x 139-199, y 236-276: <= 10 tall, every 8-col section >= 50 % free
        ('garden_wall', 141, 236, 18), ('garden_wall', 141, 275, 18), ('kegs', 140, 262, None),
        ('cannon', 156, 241, 'E'), ('cannon', 156, 267, 'E'),
        ('guard_hut', 168, 260, None), ('cart', 178, 243, None),
        ('kegs', 177, 262, None), ('shrub', 192, 250, 3), ('crates', 147, 251, 8),
    ],
    'strip_props': [
        # west half of the under-platform strip (x 218-247), rotation gives the east half
        ('rack_shelter', 219, 241, None), ('crates', 231, 263, 8), ('cannon', 236, 244, 'N'),
        ('net_rack', 219, 257, None), ('shrub', 244, 268, 3), ('boat', 228, 256, None),
    ],
    'baoli': {'c': (256, 256), 'half': 8, 'top': 57, 'pool_half': 3},   # 17 x 17 stepped well; pool floor z 62
                                                                       # (r <= 3, painted water in stage 2)
    'island_props': [('boat_shed', 158, 186, None), ('boat', 152, 326, None),
                     ('field_wall', 154, 217, (204, 220)), ('field_wall', 162, 293, (212, 290))],
    'cover_props': [('shrub', 146, 232, 3), ('shrub', 146, 280, 3)],  # plaza corners beside the lane (spawn cover)

    # ------------------------------------------------------------------ vegetation (OS seed per build)
    'banyan_groves': [((144, 206), 1, 6.5), ((176, 199), 2, 7), ((200, 190), 1, 6), ((162, 306), 2, 6.5),
                      ((222, 316), 1, 6), ((236, 304), 1, 6), ((55, 220), 1, 5.5), ((55, 292), 1, 5.5)],
                                                                               # (centre, count, radius)
    'palm_groves': [((140, 190), 2), ((200, 186), 2), ((160, 330), 2), ((222, 330), 1),
                    ((52, 208), 2), ((54, 304), 2), ((64, 250), 2), ((66, 264), 1)],

    # ------------------------------------------------------------------ one-off (after rotation)
    'dhow': {'bar': (232, 280, 326, 344), 'x': (238, 272), 'y_c': 335, 'beam_half': 5, 'keel_z': 62,
             'deck_z': 56, 'mast': ((250, 335), 36)},

    # ------------------------------------------------------------------ art (stage 2)
    'heavens_color': (124, 116, 146, 255),
    'tide_rose': (400, 386, 26),                    # (cx, cy, r) painted on the sea, SE quadrant, clear of the dhow
    'lamps': {'brazier_y': (220, 244, 268, 292)},   # merlon tops on the curtain wall that carry braziers
    'tag': {'text': 'JANJIRA SOUND', 'corner': 'NW', 'margin': 24, 'scale': 2, 'rgb': (206, 198, 170),
            'shadow': (40, 74, 86)},

    'waivers': {},
    'deviations': [],
}
