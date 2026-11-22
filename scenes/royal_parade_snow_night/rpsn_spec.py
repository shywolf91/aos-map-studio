"""Royal Parade Snow Night v2: every number of the rework in one dict (single source of truth).

Tier M community-map rework (~90 % same geometry) of 'Royal Parade Night' (RoyalParadeSnowNight.vxl, Bradley & Mile,
courtesy of Sauerkraut). Owner answers 2026-11-22: light rework, moonlit snow night, glow blocks, Babel (stock
babel_script 1.4.2), festive vehicles, bunting & lights (no spans over the boulevard), snow details, keep name + v2,
light spawn cover outside the +-20 squares.

Coordinates: x, y columns 0..511, z 0 = sky top, 63 = bottom; boxes inclusive [x0, x1, y0, y1].
Rationale for the numbers the guru is likely to question: see RATIONALE at the bottom.
"""
from __future__ import annotations

from aosmap.kit.params import BABEL_DEFAULT

SPEC = {
    'name': 'Royal Parade Snow Night', 'file': 'RoyalParadeSnowNight', 'version': '2.0', 'slug': 'royal_parade_snow_night',
    'out_version_dir': 'maps/royal_parade_snow_night_v2',
    'source': {'vxl': r'D:/Ace of Spades/Aloha.pk_Map/maps/RoyalParadeSnowNight.vxl',
               'txt': r'D:/Ace of Spades/Aloha.pk_Map/maps/RoyalParadeSnowNight.txt',
               'sha256': '2c022e0b0d49928b9eec3b8ef55c40d2877ae6542b21d94f1a33a6f8e5319d3e',
               'name': 'Royal Parade Night', 'authors': 'Bradley & Mile', 'courtesy': 'Sauerkraut'},
    'layout_seed': 20261122,               # fixed: cover shapes, lamp layout, grade noise
    'babel': dict(BABEL_DEFAULT),          # platform x 206-305, y 240-271, z 1; bases (118,256)/(394,256) +-20
    # ---------------------------------------------------------------- measured map facts (original, [RUN])
    'street_z': 56, 'water_z': 63, 'land_y': (159, 347),
    'boulevard_y': (236, 280), 'median_y': (254, 258),
    'spawn_squares': {'blue': (98, 138, 236, 276), 'red': (374, 414, 236, 276)},
    'anchor_cols': {'blue': (206, 211, 240, 271), 'red': (300, 305, 240, 271)},
    'no_new_geometry': [(98, 138, 236, 276), (374, 414, 236, 276),            # spawn squares stay as built
                        (200, 312, 234, 277)],                                # under the platform + 6 margin
    # ---------------------------------------------------------------- festive vehicles (original bboxes)
    # identified by their exact bounding box in a 6-connected label of the original solid above z 56
    'vehicles': {
        'gift_truck_w': [142, 164, 240, 246], 'gift_truck_e': [357, 375, 240, 245],
        'tree_float_w': [125, 143, 267, 272], 'tree_float_e': [358, 377, 267, 272],
        'sleigh_w': [62, 73, 245, 248], 'sleigh_e': [445, 453, 264, 267],
        # repainted in parade liveries (colour only)
        'bus_c1': [198, 216, 240, 245], 'bus_c2': [304, 326, 240, 245], 'decker_c': [201, 221, 266, 272],
        'coach_c': [287, 305, 267, 272], 'car_1': [106, 114, 244, 247], 'car_2': [281, 289, 250, 253],
        'car_3': [165, 173, 259, 262], 'limo_e': [400, 411, 258, 261], 'van_1': [233, 240, 244, 247],
        'van_2': [28, 31, 294, 301], 'van_3': [296, 303, 301, 304], 'van_4': [296, 303, 306, 309],
        'car_4': [191, 194, 302, 310], 'car_5': [201, 204, 301, 309], 'car_6': [311, 319, 203, 206],
        'car_7': [311, 319, 219, 222], 'car_8': [476, 479, 295, 303], 'car_9': [493, 496, 199, 207],
        'truck_n': [461, 466, 202, 220],
    },
    'gift_stack': {'gift_truck_w': {'x': (142, 149), 'top_z': 42}, 'gift_truck_e': {'x': (363, 370), 'top_z': 42}},
    'tree_float': {'tree_float_w': {'c': (142.0, 269.5), 'r': 4.0, 'h': 22},
                   'tree_float_e': {'c': (370.0, 269.5), 'r': 4.0, 'h': 22}},
    'clear_width_max_loss': 1,             # owner: clear street width beside a festive vehicle shrinks by <= 1
    # ---------------------------------------------------------------- spawn cover (platform side, outside squares)
    # walk-through pieces; 'x' / 'y' inclusive ranges, h above the street; mirrored x' = 512 - x by intent and
    # adjusted to each side's own vehicles (the base map is hand-built, not mirrored)
    'cover': {
        'blue': [
            {'kind': 'great_tree', 'c': (144.0, 256.0), 'r': 5.5, 'h': 24, 'name': 'blue great tree (median)'},
            {'kind': 'sleigh', 'x': (139, 141), 'y': (240, 246), 'h': 7, 'name': 'blue parked sleigh (by the truck)'},
            {'kind': 'drift', 'x': (139, 141), 'y': (264, 266), 'h': 4, 'name': 'blue snowman drift',
             'snowman': (140, 265)},
            {'kind': 'drift', 'x': (139, 140), 'y': (247, 248), 'h': 7, 'name': 'blue lane-edge drift'},
        ],
        'red': [
            {'kind': 'great_tree', 'c': (368.0, 256.0), 'r': 5.5, 'h': 24, 'name': 'red great tree (median)'},
            {'kind': 'sleigh', 'x': (371, 373), 'y': (240, 246), 'h': 7, 'name': 'red parked sleigh (by the truck)'},
            {'kind': 'drift', 'x': (371, 373), 'y': (264, 266), 'h': 4, 'name': 'red snowman drift',
             'snowman': (372, 265)},
            {'kind': 'drift', 'x': (372, 373), 'y': (247, 248), 'h': 7, 'name': 'red lane-edge drift'},
        ],
    },
    'front_lanes_min': {'lanes_3wide': 3, 'clearance_z': (51, 54)},   # >= 3 lanes >= 3 wide at every front x
    'exposure_targets': {'viewers_max_mean': 10.0, 'hidden_min_pct': 15.0},
    # ---------------------------------------------------------------- street lamps (new, fixed layout)
    'lamps': {'rows_y': (234, 277), 'x_step': 24, 'x_range': (14, 498), 'post_h': 7, 'pool_r': 7.5},
    # ---------------------------------------------------------------- snow details (OS-seeded placement)
    'snowmen': {'count': 12, 'min_spacing': 26, 'clear_r': 3},
    'kerb_drift': {'cell': 7, 'thresh_1': 0.42, 'thresh_2': 0.68},
    'icicles': {'spacing_p': 0.22, 'max_len': 3, 'min_height': 6},
    'quay_ice': {'band': (1, 9), 'cell': 9},           # painted ice on the water (no geometry, water stays water)
    # ---------------------------------------------------------------- art
    'palette': {
        # moonlit snow (cool blue, OKLCH hue ~262, max channel ~170) kept out of the fog's lilac hue bin (295)
        'snow_mid': (114, 131, 166), 'snow_light_hue': 235, 'snow_shadow_hue': 262,
        'slush': (80, 94, 122), 'ice': (104, 122, 156), 'ice_crack': (78, 94, 130),
        'water_deep': (38, 52, 100), 'water_near': (48, 68, 116),
        'brick': (92, 66, 58), 'stone': (82, 94, 112), 'stone_dark': (58, 66, 84), 'interior': (46, 44, 66),
        'evergreen': (34, 66, 58), 'iron': (54, 52, 64),
        'credit_title': (206, 170, 98), 'credit_by': (176, 186, 206),
        'window_dim': (96, 76, 66), 'window_dark': (52, 60, 92),
    },
    'glow': {'window_lit_share': 0.42, 'bulb_spacing': 4, 'strength': 0.32, 'radius': 6.5},
    'fog': (168, 160, 196),                 # bright lilac (owner), hue absent from the palette, neutral blue/red
    'heavens_color': (78, 74, 128, 255),    # deep moonlit indigo sky (optional key, owner's setup)
    'water_damage': 2,                      # kept from the original .txt
    'top_luma_target': 104,                 # night grade scalar target for the top-surface median (glow excluded)
}

RATIONALE = [
    'Spawn cover: the calibrated exposure model needs tall pieces right at the square edge (a 10-tall piece only hides '
    'spots <= ~10 columns behind it; even a full 8-tall wall across the front only reaches 18.6 % hidden). Each side '
    'gets one 24-tall great tree on the median (the spawn landmark), the gift-truck stack and the tree float on the '
    'two vehicles that already flank the square, a sleigh parked in the dead pocket in front of the truck, a lane-edge '
    'drift and a snowman drift. Layouts that met 15 % with denser pieces closed the lanes (1-2 wide); this one keeps '
    '>= 3 lanes >= 3 wide at every front x (rpsn_check.front_lanes). Measured: blue 16.1 %, red 19.0 % hidden.',
    'Blue stays below red because the blue square holds more original car roofs (spawn spots on roofs are exposed); '
    'the geometry is mirrored by intent, the numbers are reported per side.',
    'Gift stack x 142-149 / 363-370 sits on the existing truck roofs (same footprint, taller).',
    'Tree floats stand on the outside end of the two vehicles that straddle the squares; no voxel enters x 98-138 / '
    '374-414, so no new spawn columns.',
    'Lamps on the planter lines y 234 / 277 are outside the squares (y 236-276) and outside the anchor columns.',
    'Quay ice is paint only: the z 63 water stays water (water_damage 2 still applies); a z 62 ice shelf would be '
    'indestructible land and a new flank walk.',
    'heavens_color (78,74,128): darker than the fog so the sky reads as night; fog (168,160,196) is the owner value.',
]
