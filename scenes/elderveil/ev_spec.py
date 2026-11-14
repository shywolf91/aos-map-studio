"""Elderveil: the single source of truth for every number in the generator (docs/elderveil_spec.md).

Graybox v1 (2026-11-13): gameplay geometry only, organic shapes from the start (noisy cliff ring with spurs and
coves, irregular outpost wall, sunken plaza and amphitheatre outlines from noisy ellipses, meandering stream,
ruins with broken tops), flat function colours per material.

Coordinates are the WEST (blue) half and the centre axis; the east half is the mirror x' = 512 - x ('x512',
column 255 copied into 256). Axis objects are written symmetric about x = 256 and come out self-symmetric.
z = 0 is the sky top, z = 63 the bottom; a "floor z" is the solid voxel a player stands on. Boxes are inclusive
(x0, x1, y0, y1). Deviations from the spec doc are listed in SPEC['deviations'].
"""

SPEC = {
    'name': 'Elderveil', 'file': 'elderveil', 'version': '1.0-graybox1',
    'layout_seed': 20261113, 'axis': 'x512',
    'fog': (176, 172, 190),

    # ---------------------------------------------------------------- elevations (floor z)
    'z': {
        'valley': 50, 'outpost': 49, 'outpost_mound': 48, 'plaza': 53, 'arena': 53, 'aqueduct_ground': 49,
        'deck': 39, 'water': 63, 'shelf': 62, 'bank_low': 61,
        'ring_peak': (10, 16), 'ring_foot': 48, 'min_solid_z': 7,          # nothing solid at z <= 6
    },
    # terrain relief in the open fields (knolls up to 3 above, hollows 1 below); +-1 on the front band
    'relief': {'cells': (24, 9), 'amp': (7.0, 2.5), 'clip': (-1, 3), 'front_clip': 1, 'fade': 8.0},

    # ---------------------------------------------------------------- Babel (stock 1.4.2, params.BABEL_DEFAULT)
    'spawn': {'base': (118, 256), 'half': 20, 'margin': 4},         # square 98-138 / 236-276, no-prop 94-142 / 232-280
    'anchor': {'x': (200, 211), 'y': (236, 275), 'z': 50},
    'under_platform': {'x': (212, 255), 'y': (236, 276), 'clear_x': (200, 217)},
    'platform_clear': {'x': (200, 311), 'y': (234, 277), 'z_max': 3},
    'front': {'x': (139, 199), 'y': (236, 276), 'max_prop_h': 5, 'min_free': 0.70},

    # ---------------------------------------------------------------- cliff ring
    # depth W 30-60 along the edge (noise) plus spurs / coves (gaussian bumps along the edge); profile in u = d / W:
    # crest (z 10-16), rock face with terraces, foothill shoulder down to 48
    'ring': {'w': (26, 60), 'w_cell': 38, 'peak_u': 0.16, 'face_u': 0.70, 'face_top': 42, 'approach_slope': 0.7,
             'terrace_step': 5, 'rugged': 4.0,
             # (edge, along-edge centre, half width, extra depth): N/S edges run along x, W edge along y
             'bumps': [('N', 118, 14, 24), ('N', 40, 14, -8), ('W', 150, 12, 26), ('W', 360, 16, 18),
                       ('S', 150, 14, 14), ('S', 70, 12, -8), ('S', 256, 26, 14), ('N', 220, 16, -8),
                       ('N', 180, 8, 14), ('W', 205, 10, -8), ('W', 420, 12, -6), ('S', 205, 9, 10)],
             'crest_wall': {'band_u': (0.05, 0.14), 'h': (2, 4), 'cell': 9, 'keep': 0.50}},

    # ---------------------------------------------------------------- ruined outpost (spawn camp), west half
    'outpost': {
        # outline polygon (clockwise), the floor zone and the curtain-wall line
        'poly': [(56, 196), (84, 186), (118, 190), (144, 200), (154, 214), (156, 232), (156, 280), (154, 298),
                 (144, 312), (116, 324), (82, 326), (58, 316), (48, 290), (46, 256), (48, 222)],
        'wall_t': 3, 'wall_h': (6, 11),
        # breaches: wall segments skipped (polygon edge index, t0, t1 along the edge 0..1); east edge 5 is the
        # front breach (whole edge open)
        'breaches': [(5, 0.0, 1.0), (1, 0.30, 0.62), (9, 0.36, 0.70), (13, 0.30, 0.66), (11, 0.25, 0.60)],
        'mound_share': 0.40,
    },
    # gate tower at the north end of the front breach (enterable, 3 storeys, right beside the band: spawn cover);
    # south end: the stump of a collapsed bastion (broken ring wall 6-9 tall, filled with rubble 4-6 tall)
    'gate_tower': {'box': (143, 156, 222, 235), 'storeys': 3, 'storey_h': 6},
    'bastion': {'box': (143, 156, 277, 290), 'h': (6, 9), 'fill_h': (4, 6)},
    'hall': {'main': (60, 81, 236, 270), 'wing': (66, 77, 222, 236), 'storeys': 2, 'storey_h': 6},
    'tents': [(62, 72, 200, 207, 'S'), (102, 112, 198, 205, 'S'), (124, 133, 205, 215, 'W'),
              (64, 74, 300, 307, 'N'), (98, 108, 304, 311, 'N'), (124, 133, 295, 305, 'W')],
    'racks': [(86, 92, 210, 210), (86, 92, 302, 302), (140, 140, 300, 306)],
    'cart': (82, 87, 286, 289),
    'campfires': [(88, 218), (90, 292)],
    # rear backdrop: trees pinned to the layout seed (x, y, canopy r, height)
    'rear_trees': [(64, 216, 5, 12), (56, 284, 5, 12), (84, 232, 4, 11), (86, 276, 4, 11)],
    # enemy-side spawn cover outside the front band and the spawn margin (pinned)
    'cover_trees': [(150, 302, 5, 11), (147, 210, 4, 10)],
    # sunken plaza extras: a fallen arcade column on the west floor and a tree grown through the paving (pinned)
    'plaza_drums': [(217, 166, 'y', 11, 2.2)],
    'plaza_trees': [(224, 146, 4, 12)],

    # ---------------------------------------------------------------- front (x 139-199, y 236-276): low ruins
    # (kind, x, y, params) - scattered, never in rows, <= 5 tall, each >= 25 cells, >= 7 apart, every column of
    # the band keeps >= 70 % of its rows free
    'front_pieces': [
        ('drum_x', 144, 266, {'len': 10, 'r': 2.4}),            # fallen column drum lying along x (5 tall)
        ('lintel', 147, 239, {'w': 8, 'd': 6, 'h': 5}),         # fallen carved lintel block (5 tall)
        ('torso', 169, 252, {}),                                # toppled statue torso (+ broken arm, neck)
        ('mound', 181, 270, {'rx': 5, 'ry': 4, 'h': 3}),        # moss mound
        ('sled', 190, 251, {}),                                 # hunter's sled-cart
        ('drum_x', 186, 238, {'len': 9, 'r': 2.2}),             # second drum
        ('ferns', 158, 262, {'rx': 3, 'ry': 3.5}),              # fern clump (veg stand-in, 2 tall)
        ('shrine', 164, 226, {}),                               # roofless one-room shrine (x 164-173, y 226-234)
    ],

    # ---------------------------------------------------------------- under the platform (x 218-255, y 240-271)
    'under': {
        'head': {'c': (256, 256), 'r': 7.5, 'h': 3},             # fallen elder head: 3-tall steep base + features
        'stubs': [(224, 245), (224, 266), (238, 255)],          # 7x7 plinths (2 tall) + column stub; >= 7 apart
        'mosaic': (218, 255, 240, 271),
    },

    # ---------------------------------------------------------------- assist spire (west; east is the mirror)
    'spire': {'c': (190.5, 218.5), 'r_wall': (4.5, 6.5), 'r_stair': 9.5, 'ground': 50, 'top': 12,
              'rises_per_turn': 24, 'start_deg': 90.0,              # stair foot faces south (+y)
              'mid_rise': 19, 'fill_rises': 5, 'tread_t': 2,
              'doors_deg': [200.0, 300.0, 40.0], 'box': (180, 201, 208, 229),
              'collapse_deg': (200.0, 340.0),                    # mid floor missing over this arc
              'crumble': [(40.0, 75.0), (160.0, 200.0), (300.0, 330.0)],   # outer tread ring missing (r > 8.5)
              'parapet': {'h': (2, 4), 'gap_deg': [(300.0, 360.0), (20.0, 45.0), (150.0, 180.0)]}},

    # ---------------------------------------------------------------- sunken plaza (north centre)
    'plaza': {'c': (256, 176), 'r': (64, 36), 'edge_noise': 0.12, 'steps': (2.5, 5.0),     # z 51 / 52 / 53
              'moonwell': {'c': (256, 170), 'r': 7.5, 'rim_h': 2, 'gaps_deg': [0, 90, 180, 270], 'pillar_h': 8},
              'statue_r': 20, 'statue_deg': [150, 210, 270],
              # arcades: (centre angle deg, half arc deg, radius along the plaza ellipse factor)
              'arcades': [(180, 16, 0.84), (232, 10, 0.84)]},
    # fallen elder-queen statue lying N-S across the plaza's south edge (axis object)
    'queen': {'x': (249, 263), 'head_c': (256, 192), 'head_r': 5.5, 'torso_y': (197, 214), 'torso_z': (44, 46),
              'hips_y': (215, 223), 'legs_y': (226, 233), 'ramp_x': (241, 248), 'ramp_y': (216, 219)},

    # ---------------------------------------------------------------- elder library (north, axis)
    'library': {'box': (238, 274, 106, 132), 'storeys': 2, 'storey_h': 6, 'wing': (226, 238, 110, 126)},

    # ---------------------------------------------------------------- root amphitheatre + heart-tree (south centre)
    'amphi': {'c': (256, 340), 'r': (44, 32), 'levels': [(0.36, 53), (0.52, 52), (0.70, 51)], 'edge_noise': 0.08,
              'tree': {'trunk_r': 5.0, 'trunk_top': 20, 'canopy': (17, 15, 8), 'canopy_z': 20},
              'roots': [(200, 30), (235, 33), (160, 31), (125, 29)],    # (direction deg, reach); west half
              'root_z0': 36},

    # ---------------------------------------------------------------- north flank: aqueduct
    'aqueduct': {'y': (85, 91), 'x0': 44, 'deck_z': 39, 'deck_t': 2, 'soffit': 41, 'pier_w': 3, 'pier_dx': 16,
                 'pier_x0': 52, 'parapet_h': 2,
                 'collapses': [(98, 124), (178, 204)]},           # gaps in the deck (rubble ramps inside)

    # ---------------------------------------------------------------- south flank: stream, pool, bridge, mushrooms
    'stream': {'y_c': 428, 'amp': 7.0, 'period': 70.0, 'axis_flat': 24.0, 'wh': (4.5, 1.2, 0.8),
               'wh_clamp': (3.5, 6.0), 'shelf': 2.0, 'shelf_noise': 1.5, 'bank_w': 16,
               'pool': {'c': (256, 436), 'wh': 9.0, 'L': 20.0}},
    'bridge': {'x': (253, 259), 'deck_z': 50, 'parapet_x': (253, 259)},
    'waterfall': {'x': (252, 260)},
    'rune_circle': {'c': (256, 398), 'r': 8.0, 'stones_deg': [150, 190, 230, 110], 'stone_h': (5, 7)},
    'mushrooms': [(84, 404, 6, 18), (118, 466, 5, 14), (152, 400, 7, 20), (190, 470, 5, 13), (214, 402, 6, 16),
                  (66, 458, 5, 15)],                                # (x, y, cap r, height)

    # ---------------------------------------------------------------- scatter (layout seed) + veg (veg seed)
    'scatter': {'field_spacing': 22, 'field_jitter': 7, 'forest_cell': 30, 'grove_density': (0.53, 0.9),
                'grove_spacing': 7, 'grove_jitter': 2, 'lone_p': 0.06},

    # ---------------------------------------------------------------- checks
    'flank_bands': {'north': (46, 126), 'south': (386, 466), 'restrict_x': (152, 360), 'max_diff': 0.10},
    'featureless': {'max_side': 24, 'exempt': [(94, 142, 232, 280), (370, 418, 232, 280), (200, 311, 236, 276)]},
    # composite pieces counted as one structure in the gap check (parts deliberately 2-3 apart: the queen's legs
    # broken off at the knees, the moonwell rim arcs round the pillar plinth)
    'central_gap': {'min': 7, 'composites': [(248, 264, 161, 180), (240, 272, 184, 236)]},

    'deviations': [
        'spire footprint x 180-201, y 208-229 (spec about 178-200 / 206-228): centre (190.5, 218.5), stair radius 9.5',
        'gate tower y 222-235 and the bastion y 277-290 sit right beside the front band (spawn-cover rule); the '
        'bastion is a collapsed rubble-filled stump (ruin mound, no room) rather than an enterable tower',
        'front: a fallen lintel block (5 tall) added inside the band for spawn cover; the shrine sits just north of '
        'the band (y 226-234) so every band column keeps >= 70 % free rows and pieces stay >= 7 apart; one fern '
        'clump (spec: ferns); the sled-cart is the hunters sled',
        'under the platform: no root humps (they broke the 7-voxel gap rule); the head is r 7.5 and there are three '
        '7x7 plinths with column stubs; the broken mosaic floor is paint only (region 6)',
        'rune circle centre y 398 (spec 410): the footbridge abutment needs y 405-412; the circle opens onto the '
        'bridge',
        'footbridge spans the pool where the bank is below z 50 (about y 410-462, centre ~436; spec 440)',
        'waterfall: graybox paint only (cliff face + bank behind the pool); the cascade is art-pass geometry',
        'library y 106-132 (centre 119) with a west wing (east by mirror); plaza ellipse centre (256, 176) r 64 x 36 '
        '(x 192-320, y 140-212)',
        'heart-tree roots end in steep knees (top >= 6 above the ground) so they cannot be walked onto',
        'crest walls are removed within 3 of any trap cell they create (logged in build.json)',
        'not in the graybox (art pass): corner tag at sky level, sky islets and crows, glow blocks, vegetation art',
    ],
}
