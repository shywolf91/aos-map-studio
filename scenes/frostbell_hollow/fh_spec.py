"""Frostbell Hollow: the single source of truth for every number in the generator (docs/frostbell_hollow_spec.md).

Graybox v2 (2026-11-10): same gameplay frame as v1, organic shapes (noisy mountain ring, tapered ridge spur,
meandering creek, irregular plaza with lanes, clustered stalls, L/T houses with gables, terrain relief, groves,
outcrops and art-pass feature pads).

Coordinates are the WEST (blue) half and the centre axis; the east half is the mirror x' = 512 - x ('x512',
column 255 copied into 256). Axis objects are written as their west half (x <= 255) and come out self-symmetric.
z = 0 is the sky top, z = 63 the bottom; a "floor z" is the solid voxel a player stands on. Boxes are inclusive
(x0, x1, y0, y1). Deviations from the spec doc are listed in SPEC['deviations'].
"""

SPEC = {
    'name': 'Frostbell Hollow', 'file': 'frostbell_hollow', 'version': '1.0-graybox2',
    'layout_seed': 20261110, 'axis': 'x512',
    'fog': (166, 160, 188),
    'heavens_color': (52, 44, 104, 255),          # art pass (not written into the graybox .txt)

    # ---------------------------------------------------------------- elevations (floor z)
    'z': {
        'valley': 50, 'village': 49, 'village_mound': 48, 'rail': 49, 'underground_floor': 59,
        'tunnel_air': (55, 58),                   # 4 air: step-up rule needs z-4 clear over the source
        'chamber_air': (54, 58),                  # 3 solid between the chamber roof (53) and the surface (50)
        'water': 63, 'ice_shelf': 62, 'bank_low': 61,
        'ring_peak': (9, 14), 'ring_foot': 48, 'min_solid_z': 7,   # nothing solid at z <= 6
    },
    # terrain relief outside the flat gameplay zones: knolls up to 3 above, hollows down to 2 below the valley
    'relief': {'cells': (22, 9), 'amp': (7.0, 2.5), 'clip': (-2, 3), 'over_tunnels_max_z': 51, 'front_clip': 1},

    # ---------------------------------------------------------------- Babel (stock 1.4.2, see params.BABEL_DEFAULT)
    'spawn': {'base': (118, 256), 'half': 20, 'margin': 4},          # square 98-138 / 236-276, no-prop 94-142 / 232-280
    'anchor': {'x': (200, 211), 'y': (236, 275), 'z': 50},
    'under_platform': {'x': (212, 255), 'y': (236, 276), 'max_prop_h': 2},
    'platform_clear': {'x': (200, 311), 'y': (234, 277), 'z_max': 2},

    # ---------------------------------------------------------------- terrain zones
    # ring: depth W varies 28-60 along the edge (noise); profile in u = d / W: peaks, rock face (terraces,
    # outcrop noise), foothill shoulder. Near protected gameplay zones it may only rise at approach_slope per voxel.
    'ring': {'w': (28, 60), 'w_cell': 56, 'peak_u': 0.14, 'face_u': 0.72, 'face_top': 42, 'approach_slope': 0.7,
             'terrace_step': 5, 'rugged': 4.0},
    'village': {'x': (44, 145), 'y': (176, 334)},
    'front': {'x': (152, 199), 'y': (232, 280), 'max_prop_h': 5, 'lantern_h': 6, 'min_free': 0.70},
    'railway': {'x': (40, 255), 'embankment_y': (79, 89), 'shoulder': 2, 'rails_y': (82, 86), 'rail_z': 48,
                'station_apron': (228, 255, 56, 92)},
    # tapered ridge spur out of the north range: centre line, half width and crest vary along y
    'spur': {'y': (14, 104), 'xc': 162, 'wiggle': 3.0, 'hw': 12.0, 'hw_amp': 3.0, 'crest': (24, 36),
             'tip_from': 92, 'tunnel_x': (140, 186), 'tunnel_y': (82, 86), 'tunnel_air': (44, 48)},
    # meandering creek: centre 430 +- 9, water half width 3.5-6.5 (7-13 wide), irregular ice shelves, gravel islands
    'creek': {'y_c': 430, 'amp': 9.0, 'period': 75.0, 'axis_flat': 22.0, 'wh': (5.0, 1.5, 1.0), 'wh_clamp': (3.5, 6.5),
              'shelf': 2.0, 'shelf_noise': 2.0, 'bank_w': 24,
              'islands': [(118, 7.0, 1.6), (196, 6.0, 1.4)]},          # (x, half length, half width)
    'sled_hill': {'x': (244, 255), 'y': (462, 500), 'z_top': 30, 'z_bottom': 52},

    # ---------------------------------------------------------------- plaza (organic market) and lanes
    'plaza': {
        'ellipses': [(256, 190, 54, 44), (256, 146, 36, 26), (256, 322, 52, 46), (256, 368, 36, 22),
                     (198, 180, 26, 22), (198, 332, 26, 22), (214, 218, 30, 14), (214, 296, 30, 14)],
        'rects': [(200, 255, 226, 286)],         # anchors + under-platform strip (always cobbled and flat)
        'edge_noise': 0.22,
    },
    'lanes': [  # (points, width): cobbled lanes radiating to the gatehouses and both flanks
        ([(214, 224), (184, 224), (153, 224)], 7),
        ([(214, 288), (184, 288), (153, 288)], 7),
        ([(250, 166), (250, 120), (250, 92)], 7),
        ([(206, 158), (194, 140), (182, 122)], 6),
        ([(250, 378), (250, 398)], 7),
        ([(212, 372), (196, 384), (182, 394)], 6),
    ],

    # ---------------------------------------------------------------- village (west)
    'chapel': {'nave': (69, 90, 248, 264), 'tower': (58, 69, 250, 262), 'nave_roof_z': 38,
               'tower_storeys': 4, 'tower_storey_h': 6},                  # tower roof z 25
    'post_office': {'box': (96, 122, 196, 222), 'partition_x': 106, 'mailbox': (114, 115, 225, 226),
                    'wing': (104, 114, 186, 196)},                         # T: rear wing on the north side
    # village buildings: parts share a wall; 'link' = doorway (x0, x1, y0, y1) carved through the shared wall
    'houses': [
        {'name': 'house NW', 'parts': [((64, 82, 186, 204), 2, 5, ('S', 'E'), 'x'),
                                       ((70, 80, 178, 186), 1, 5, ('N',), 'y')], 'link': (74, 75, 186, 186)},
        {'name': 'house NE', 'parts': [((131, 145, 184, 206), 3, 5, ('S', 'W'), 'y')]},
        {'name': 'cellar house SW', 'parts': [((62, 82, 292, 310), 2, 5, ('N', 'E'), 'x'),
                                              ((52, 62, 300, 310), 1, 5, ('S',), 'y')],
         'link': (62, 62, 305, 306), 'cellar': True},
        {'name': 'house SE', 'parts': [((120, 142, 296, 316), 2, 5, ('N', 'W'), 'x'),
                                       ((126, 136, 316, 324), 1, 5, ('S',), 'x')], 'link': (130, 131, 316, 316)},
        {'name': 'barn', 'parts': [((91, 105, 290, 304), 1, 7, ('N', 'S'), 'y')], 'door_w': 5},
        {'name': 'shed NW', 'parts': [((46, 54, 184, 192), 1, 5, ('E',), 'x')]},
        {'name': 'shed S', 'parts': [((100, 108, 322, 330), 1, 5, ('N',), 'y')]},
        {'name': 'woodshed', 'parts': [((82, 90, 232, 239), 1, 5, ('S',), 'x')]},
    ],
    'fences': [(64, 74, 214, 214), (58, 66, 244, 244), (58, 66, 268, 268), (62, 72, 318, 318),
               (112, 112, 288, 296), (124, 130, 226, 226)],               # <= 2 tall, open segments
    'well': (86, 88, 270, 272),
    'woodpiles': [(66, 69, 210, 211), (106, 109, 308, 309), (56, 59, 196, 197)],
    'gatehouse': {'x': (146, 151), 'y': (220, 292), 'tower_y': (220, 231), 'floor_z': 50,
                  'passage_air': (41, 49), 'gallery_floor': 40, 'gallery_air': (30, 39), 'roof': (28, 29),
                  'piers': [(240, 243), (254, 258), (269, 272)], 'statue_y': (213, 216),
                  # experiment switch (fh_main.py --gate NAME): full (release) | band | arch | twin | low | none
                  'variant': 'full', 'flank_cover': False},
    'front_huts': [{'box': (166, 174, 232, 239), 'open': 'S'}, {'box': (181, 189, 273, 280), 'open': 'N'}],
    # scattered low front props (x, y, kind): never in rows; heights <= 5 (lanterns 6)
    'front_props': [(157, 263, 'sled'), (191, 249, 'sled'), (161, 271, 'firewood'), (177, 245, 'hay'),
                    (193, 265, 'hay'), (170, 255, 'cart'), (183, 240, 'rock'), (196, 271, 'rock'),
                    (159, 243, 'bush'), (186, 259, 'bush'), (163, 252, 'bench'), (178, 267, 'bench'),
                    (154, 236, 'lantern'), (155, 277, 'lantern'), (168, 274, 'rock'), (189, 233, 'firewood')],

    # ---------------------------------------------------------------- market stalls (west half), clusters and arcs
    # (x0, x1, y0, y1, front, kind) kind: plain | awning | L
    'stalls': [
        (224, 231, 165, 171, 'E', 'plain'), (217, 223, 185, 194, 'E', 'awning'), (224, 232, 211, 217, 'E', 'L'),
        (165, 174, 198, 205, 'S', 'L'), (186, 193, 206, 212, 'S', 'plain'), (203, 209, 194, 202, 'W', 'awning'),
        (216, 223, 141, 148, 'E', 'plain'), (186, 194, 145, 151, 'S', 'awning'), (169, 175, 154, 161, 'E', 'plain'),
        (224, 231, 293, 299, 'E', 'awning'), (219, 225, 317, 326, 'E', 'plain'), (220, 228, 343, 349, 'E', 'awning'),
        (168, 176, 297, 303, 'N', 'plain'), (189, 195, 302, 310, 'N', 'L'), (203, 209, 326, 333, 'W', 'plain'),
        (170, 177, 348, 355, 'E', 'awning'), (196, 204, 359, 365, 'N', 'plain'),
    ],
    'hatch_stalls': {'north': (184, 195, 172, 186), 'south': (184, 195, 326, 340)},
    'sculptures': [(230, 313, 3, 4), (234, 324, 2, 5), (230, 334, 3, 3), (235, 343, 2, 4), (212, 309, 2, 4)],

    # ---------------------------------------------------------------- centre-axis one-offs (west half x <= 255)
    'station': {'box': (242, 269, 62, 73), 'canopy_y': (74, 78), 'floor': 49},
    'train': {'box': (226, 285, 82, 86), 'chassis_z': 47},         # added AFTER the mirror (asymmetric)
    'nativity': {'box': (249, 263, 111, 120)},
    'tavern': {'box': (240, 271, 136, 159), 'floor': 50, 'cellar': (242, 255, 140, 157)},
    'spruce': {'c': (256, 190), 'r': 13, 'cone_base_z': 40, 'tip_z': 12, 'trunk_r': 2.5},
    'carousel': {'c': (256, 292), 'r': 8, 'canopy_z': 42},
    'rink': {'box': (239, 272, 315, 336)},
    'workshop': {'box': (241, 270, 356, 375), 'storey_h': 9},
    'bridge': {'x': (248, 264), 'y': (414, 450), 'deck_z': 52, 'roof_z': 43},
    'mill': {'x': (142, 158), 'depth': 12, 'gap_to_water': 9, 'wheel_r': 6},   # placed from the creek centre line

    # ---------------------------------------------------------------- underground (west half; floor z 59)
    'tunnels': [
        ('trunk W', (48, 50, 166, 344)),
        ('north lateral', (48, 236, 166, 168)),
        ('tavern link N-S', (234, 236, 147, 168)),
        ('tavern link W-E', (234, 241, 147, 149)),
        ('south lateral', (48, 196, 342, 344)),
        ('cellar link', (48, 64, 300, 302)),
        ('adit foot', (48, 51, 208, 210)),
    ],
    'chambers': [('elf mine north', (96, 112, 159, 175)), ('elf mine south', (112, 130, 336, 350))],
    'house_cellar': (64, 80, 294, 308),
    'adit': {'x0': 52, 'y': (208, 210)},                      # stair rising +x from the trunk to the surface
    'hatch_n': {'x': (188, 190), 'y0': 169},                   # stair rising +y into the north hatch stall
    'hatch_s': {'x': (188, 190), 'y0': 341},                   # stair rising -y into the south hatch stall
    'tunnel_exclusion': {'x': (150, 215), 'y': (232, 280)},

    # ---------------------------------------------------------------- scatter (deterministic from the layout seed)
    # stand-in pines are material 'veg' (replaced in the art pass, which draws its own OS seed)
    'scatter': {'field_spacing': 22, 'field_jitter': 7, 'plaza_spacing': 15, 'plaza_jitter': 4,
                'village_spacing': 17, 'village_jitter': 5, 'grove_radius': 12, 'grove_n': (3, 6)},

    # ---------------------------------------------------------------- checks
    'flank_bands': {'north': (46, 126), 'south': (386, 466), 'restrict_x': (152, 360), 'max_diff': 0.10},
    'front_check': {'x': (152, 199), 'y': (232, 280)},
    'gatehouse_check': {'y': (232, 280), 'min_open': 0.60, 'max_pier': 5},
    # corner tag strip (NE quadrant, on the valley floor; the graybox keeps it flat and clear on both halves)
    'tag': {'x0': 358, 'y0': 107, 'strip': (354, 456, 104, 117)},
    'featureless': {'max_side': 24, 'exempt': [(94, 142, 232, 280), (370, 418, 232, 280), (200, 311, 236, 276)]},

    'deviations': [
        'post office x 96-122 (spec 100-126): keeps an 8-wide lane to the NE house and the gatehouse statue',
        'gatehouse y 220-292 (spec 222-290): end towers 12 long so a 2-flight stair (floor 50 -> gallery 40) fits',
        'gallery floor z 40, passages z 41-49 air, roof slab z 28-29 (as spec); stairs only inside the end towers',
        'bridge abutments: earth ramps at z 52 from the bank to the deck (y 398-413, 451-461) so the deck at z 52 '
        'joins the banks; the sledding hill ends on the south abutment (run y 462-500 from z 30 to 52)',
        'creek banks 24 wide (spec ~28) so the meandering valley stays inside the south flank zone',
        'water mill placed from the creek centre line (x 142-158, 9 voxels north of the water), floor = local bank '
        'height so its north door opens onto level ground',
        'village: 4 houses (3 with L/T wings), barn, 3 sheds; market: 17 stalls + hatch stall per side in arcs '
        'and clusters (spec: 4 per side)',
        'station box x 242-270 after the mirror (written as 242-269 so its recorded interior stays at x 255), '
        'train x 226-285 on rails z 48, chassis z 47',
        'railway rails stay straight (no end bends); the embankment has noisy shoulders instead',
    ],
}
