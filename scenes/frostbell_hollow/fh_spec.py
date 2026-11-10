"""Frostbell Hollow: the single source of truth for every number in the generator (docs/frostbell_hollow_spec.md).

Coordinates are the WEST (blue) half and the centre axis; the east half is the mirror x' = 512 - x ('x512',
column 255 copied into 256). Axis objects are written as their west half (x <= 255) and come out self-symmetric.
z = 0 is the sky top, z = 63 the bottom; a "floor z" is the solid voxel a player stands on. Boxes are inclusive
(x0, x1, y0, y1). Deviations from the spec doc are marked DEV and listed in SPEC['deviations'].
"""

SPEC = {
    'name': 'Frostbell Hollow', 'file': 'frostbell_hollow', 'version': '1.0-graybox',
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

    # ---------------------------------------------------------------- Babel (stock 1.4.2, see params.BABEL_DEFAULT)
    'spawn': {'base': (118, 256), 'half': 20, 'margin': 4},          # square 98-138 / 236-276, no-prop 94-142 / 232-280
    'anchor': {'x': (200, 211), 'y': (236, 275), 'z': 50},
    'under_platform': {'x': (212, 255), 'y': (236, 276), 'max_prop_h': 2},
    'platform_clear': {'x': (200, 311), 'y': (234, 277), 'z_max': 2},

    # ---------------------------------------------------------------- terrain zones
    'ring': {'width': 40, 'foot': 44, 'peak_band': 6, 'rock_to': 34},   # d = min(x, y, 511 - y) on the west half
    'village': {'x': (44, 145), 'y': (176, 334)},
    'market_cobble': {'x': (154, 255), 'y': (128, 388)},
    'front': {'x': (152, 199), 'y': (232, 280), 'max_prop_h': 5, 'lantern_h': 6, 'min_free': 0.70},
    'railway': {'x': (40, 255), 'y_strip': (58, 90), 'embankment_y': (79, 89), 'rails_y': (82, 86), 'rail_z': 48},
    'spur': {'x': (150, 176), 'y': (36, 104), 'core_half': 9, 'top_z': 30, 'tip_from': 96,
             'tunnel_y': (82, 86), 'tunnel_air': (44, 48)},                # 5 x 5 tunnel, walk-around y 105-126
    'creek': {'y_c': 430, 'wiggle': 4, 'water_half': 5, 'shelf_half': 8, 'bank_from': 9, 'bank_w': 26},
    'sled_hill': {'x': (244, 255), 'y': (462, 500), 'z_top': 30, 'z_bottom': 52},

    # ---------------------------------------------------------------- village (west)
    'chapel': {'nave': (69, 90, 248, 264), 'tower': (58, 69, 250, 262), 'nave_roof_z': 38,
               'tower_storeys': 4, 'tower_storey_h': 6},                  # tower roof z 25
    'post_office': {'box': (96, 122, 196, 222), 'partition_x': 106, 'mailbox': (114, 115, 225, 226)},
    'houses': [
        {'name': 'house NW', 'box': (64, 82, 186, 204), 'doors': ('S', 'E')},
        {'name': 'house NE', 'box': (131, 145, 184, 206), 'doors': ('S', 'W')},
        {'name': 'cellar house SW', 'box': (62, 82, 292, 310), 'doors': ('N', 'E'), 'cellar': True},
        {'name': 'house SE', 'box': (120, 142, 296, 316), 'doors': ('N', 'W')},
    ],
    'gatehouse': {'x': (146, 151), 'y': (220, 292), 'tower_y': (220, 231), 'floor_z': 50,
                  'passage_air': (41, 49), 'gallery_floor': 40, 'gallery_air': (30, 39), 'roof': (28, 29),
                  'piers': [(240, 243), (254, 258), (269, 272)], 'statue_y': (213, 216)},
    'front_huts': [{'box': (166, 174, 232, 239), 'open': 'S'}, {'box': (181, 189, 273, 280), 'open': 'N'}],

    # ---------------------------------------------------------------- market (west half)
    'stalls_north': [(166, 175, 208, 216), (184, 193, 208, 216), (202, 211, 208, 216),
                     (166, 175, 150, 158), (202, 211, 150, 158), (166, 175, 180, 188), (220, 229, 210, 218)],
    'stalls_south': [(166, 175, 296, 304), (184, 193, 296, 304), (202, 211, 296, 304),
                     (166, 175, 352, 360), (202, 211, 352, 360), (166, 175, 324, 332), (202, 211, 324, 332)],
    'hatch_stalls': {'north': (184, 195, 172, 186), 'south': (184, 195, 326, 340)},

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
    'mill': {'box': (142, 158, 400, 412), 'floor': 52, 'wheel_c': (150, 56), 'wheel_r': 6, 'wheel_y': (413, 415)},

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

    # ---------------------------------------------------------------- stand-in vegetation (material 'veg')
    'pines': [  # (x, y, r, height) west half; cones on the ground, replaced in the art pass
        (60, 60, 4, 14), (84, 54, 3, 12), (110, 50, 4, 15), (196, 50, 3, 12), (226, 52, 4, 14),
        (58, 132, 3, 12), (92, 118, 4, 14), (130, 140, 3, 12),
        (52, 230, 3, 12), (54, 282, 3, 13), (90, 176, 3, 12), (138, 224, 3, 13), (138, 288, 3, 13),
        (60, 360, 4, 14), (96, 372, 3, 12), (140, 366, 4, 14), (70, 404, 3, 12), (100, 396, 4, 14),
        (186, 400, 3, 13), (214, 396, 4, 14), (82, 462, 3, 12), (120, 456, 3, 13), (176, 456, 3, 13),
        (212, 456, 3, 13), (228, 398, 3, 12),
    ],

    # ---------------------------------------------------------------- checks
    'flank_bands': {'north': (46, 126), 'south': (386, 466), 'restrict_x': (152, 360), 'max_diff': 0.10},
    'front_check': {'x': (152, 199), 'y': (232, 280)},
    'gatehouse_check': {'y': (232, 280), 'min_open': 0.60, 'max_pier': 5},

    'deviations': [
        'post office x 96-122 (spec 100-126): keeps an 8-wide lane to the NE house and the gatehouse statue',
        'gatehouse y 220-292 (spec 222-290): end towers 12 long so a 2-flight stair (floor 50 -> gallery 40) fits',
        'gallery floor z 40, passages z 41-49 air, roof slab z 28-29 (as spec); stairs only inside the end towers',
        'bridge abutments: earth ramps at z 52 from the bank to the deck (y 398-413, 451-461) so the deck at z 52 '
        'joins the banks; the sledding hill ends on the south abutment (run y 462-500 from z 30 to 52)',
        'creek banks 26 wide (spec ~28) so the valley (y ~395-465) stays inside the south flank zone',
        '4 village houses (NW, NE, SW cellar house, SE); stall counts 7 + hatch stall per market quadrant',
        'station box x 242-270 after the mirror (written as 242-269 so its recorded interior stays at x 255), train x 226-285 on rails z 48, chassis z 47',
    ],
}
