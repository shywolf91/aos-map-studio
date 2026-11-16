"""Yulehaven Isles: the single source of truth for every number in the generator (docs/yulehaven_isles_spec.md).

Christmas Eve in a Nordic fishing archipelago. Stock Babel (piqueserver 1.4.2 babel_script), island Babel,
no assist structures. Owner answers 2026-11-14: roofed wading sea passage links the caves, lighthouse at the
Blue end of the north chain / chapel at the Red end of the south chain, water_damage 1.

Coordinates are the WEST (blue) half and the centre axis; the east half is the mirror x' = 512 - x ('x512',
column 255 copied into 256). Centre-axis objects (cargo ship, islet stair) are built after mirroring and are
self-symmetric. One-off landmarks (lighthouse, Yule goat, chapel, ice camp, post office / sauna dressing, spruce,
iceberg + tag, sky decor) are placed after mirroring and listed as cosmetic boxes.
z = 0 is the sky top, z = 63 the bottom; a "floor z" is the solid voxel a player stands on. Boxes are inclusive.
"""

SPEC = {
    'name': 'Yulehaven Isles', 'file': 'yulehaven_isles', 'version': '1.0',
    'layout_seed': 20261114, 'axis': 'x512',
    'fog': (172, 174, 192),                     # cool lilac-grey: absent from the granite/timber/red/sea palette
    'heavens_color': (46, 74, 112, 255),        # polar-twilight teal-violet (one RGBA; the key takes one colour)
    'water_damage': 1,

    # ---------------------------------------------------------------- elevations (floor z)
    'z': {
        'water': 63, 'beach': 61, 'spawn': 48, 'anchor': 52, 'plateau': 48,
        'ice': 62,                              # ice shelves flush with the water (z 62 solid): every hole steps out
        'pier': 60, 'cave_floor': 60, 'cave_air': (54, 59), 'islet_cave_floor': 61,
    },

    # ---------------------------------------------------------------- Babel (stock 1.4.2, see params.BABEL_DEFAULT)
    'spawn': {'base': (118, 256), 'half': 20, 'margin': 4},          # square 98-138 / 236-276
    'front': {'x': (139, 199), 'y': (236, 276)},
    'anchor': {'x': (200, 212), 'y': (236, 276), 'z': 52},   # 212 so the mirror gives red x 300 (platform end 300-305)
    'front_crest': {'x0': 143, 'crest': (148, 153), 'z': 45},  # gentle rise 3 above the spawn floor, then down to the anchor
    'zone_blend': 12,                                                # spawn/front/anchor blend into the terrain

    # ---------------------------------------------------------------- spawn island (west; east is the mirror)
    'island': {
        'ellipses': [(122, 256, 86, 106), (176, 194, 34, 44), (176, 318, 34, 44), (70, 200, 40, 40),
                     (70, 312, 40, 40)],
        'x_max': 207, 'edge_noise': 0.16, 'beach_w': 6, 'rise_w': 22,
        'relief_amp': 5.0, 'relief_cell': 26,
        'cliff_headland': (112, 352, 16),        # forced granite headland on the south coast (sea-cave mouth)
    },
    # ---------------------------------------------------------------- central islet (self-symmetric)
    'islet': {
        'c': (256, 256), 'rx': 29.5, 'ry': 78, 'x': (226, 286), 'edge_noise': 0.10,
        'rim_z': 57, 'outcrop': (256, 192, 15, 42), 'plateau': (256, 316, 22, 53),
        'south_lobe': (256, 314, 26, 30),
        'lagoon': (256, 256, 19.5, 42),          # frozen lagoon (ice at z 61) holding the cargo ship
    },
    # rock hops across the channel (north) and the wading lane (painted shallows) - west half, mirrored
    'hops': [(203, 219, 1), (207, 218, 1), (211, 220, 1), (215, 219, 1), (219, 221, 1), (223, 220, 1), (227, 219, 1)],   # (x, y, half size): 3x3 rocks, 1 water column apart
    'shallows': [((196, 200), (230, 204)), ((196, 314), (232, 316))],                      # painted lanes (still water)

    # ---------------------------------------------------------------- flank skerries (north; south = y-mirror)
    # (cx, cy, r, peak_z); 'M' sits on the axis (self-symmetric)
    'skerries': {
        'S1': (128, 108, 13, 52), 'S2': (176, 88, 10, 53), 'S3': (218, 78, 9, 55), 'M': (256, 86, 14, 51),
        'L': (90, 72, 14, 50),
    },
    'links': [
        # (kind, polyline of axis-aligned or straight points, width); ends meet the terrain
        ('pier', [(127, 150), (127, 118)], 3),               # island north shore -> S1 beach
        ('rope', [(134, 101), (171, 89)], 3),                # S1 top -> S2 top
        ('broken', [(184, 84), (212, 84)], 3),               # S2 shore -> S3 shore (one sagging, broken stretch)
        ('rope', [(224, 80), (247, 85)], 3),                 # S3 top -> M top
        ('pier', [(118, 100), (102, 100)], 3),               # S1 -> lighthouse / goat skerry L
        ('pier', [(102, 100), (102, 80)], 3),
    ],

    # ---------------------------------------------------------------- underground (west, mirrored)
    'cave': {
        'chamber': (106, 318, 15, 11),           # (cx, cy, rx, ry) smugglers' chamber under the south village
        'mouth': ((106, 329), (110, 362)),       # tunnel to the sea-cave mouth in the south headland
        'shed_stair_x': (112, 125), 'shed_y': (300, 303),     # stair from the smugglers' shed down to the chamber
        'tunnel': [(118, 316), (160, 316), (186, 318)],       # chamber -> under the inner south shore spine
        'passage': ((186, 318), (242, 318)),     # roofed wading passage over the channel (water air z 59-62)
        'spine': ((170, 211), 318, 53),          # granite spine over the tunnel on the shore (x range, y, crest z)
        'islet_chamber': (256, 318, 16, 6),      # shared chamber under the islet's south plateau (floor 61)
    },

    # ---------------------------------------------------------------- structures (west half; mirrored)
    'cabins': [
        # (name, x0, x1, y0, y1, storeys, ridge, door, wall, stilt_floor or None)
        ('north cabin 1', 96, 109, 204, 215, 2, 'x', 'S', 'red', None),
        ('north cabin 2', 116, 127, 196, 207, 1, 'y', 'S', 'ochre', None),
        ('north cabin 3', 140, 153, 221, 232, 2, 'x', 'N', 'red', None),
        ('south cabin 1', 96, 109, 297, 308, 2, 'x', 'N', 'ochre', None),
        ('smugglers shed', 110, 127, 296, 307, 1, 'x', 'N', 'red', None),
        ('south cabin 3', 140, 153, 280, 291, 2, 'x', 'S', 'red', None),
        ('west net loft', 52, 67, 240, 255, 2, 'y', 'E', 'ochre', None),
        ('west cabin', 54, 65, 266, 277, 1, 'y', 'E', 'red', None),
        ('shore cabin N', 62, 73, 170, 181, 1, 'x', 'S', 'ochre', 54),
        ('shore cabin S', 62, 73, 331, 342, 1, 'x', 'N', 'red', 54),
    ],
    'boathouse': (178, 194, 140, 156),            # inner north shore, sea door facing north
    'trawler_dock': {'pier_x': (193, 196), 'pier_y': (164, 206), 'boat_x': (199, 206), 'boat_y': (170, 196)},
    'post_office': (168, 183, 336, 347),          # inner south shore (red side: sauna, same shell)
    'post_pier': {'x': (174, 177), 'y': (348, 372)},
    'racks': [(160, 182, 0), (160, 190, 0), (168, 226, 1)],       # stockfish racks (x, y, along-y?)
    'pots': [(160, 210), (186, 214), (188, 300), (158, 328)],      # lobster pot stacks (x, y)
    'front_props': [
        # (kind, x, y) low dressing on the front (<= 10 tall): two walk-through fish sheds on the crest, an upturned
        # boat on trestles, fish-crate stacks, a firewood stack, a net reel, a kicksled - every N-S section >= 50 % free
        ('shed', 147, 238), ('shed', 147, 268), ('boat_trestle', 160, 251), ('crates', 170, 264),
        ('woodpile', 178, 244), ('net_reel', 188, 258), ('sled', 164, 241), ('crates', 192, 270),
    ],
    'spawn_cover': [
        # granite boulders on the enemy-facing corners of the spawn square (outside it and outside the front band)
        (158, 226, 4), (158, 286, 4),
    ],
    # vegetation groves (art pass, OS seed): spawn-side corners, rear backdrop, villages, outer coasts
    'groves': [(150, 212, 9), (150, 300, 9), (70, 224, 13), (70, 290, 13), (84, 256, 10), (100, 180, 11),
               (100, 336, 11), (44, 250, 11), (160, 176, 10), (160, 340, 10), (44, 200, 10), (44, 312, 10),
               (128, 168, 9), (128, 344, 9), (134, 108, 6), (134, 403, 6), (176, 88, 5), (176, 423, 5)],

    # ---------------------------------------------------------------- centre (self-symmetric / one-offs)
    'ship': {'y': (220, 291), 'x_c': 256, 'beam_half': 8, 'keel_z': 62, 'deck_z': 50, 'hold_floor': 61,
             'breach_y': (246, 251), 'forecastle_y': (220, 231), 'deckhouse_y': (272, 289), 'mast_top': 28},
    'bonfire': (256, 322, 11),                   # (cx, cy, ring radius) on the south plateau
    'spruce': (256, 192, 42, 18),                # (x, y, ground z, height) on the north outcrop
    'ice_camp': (90, 439),                       # south chain, Blue end (skerry L, y-mirror)
    'lighthouse': (90, 70),                      # north chain, Blue end (skerry L)
    'goat': (422, 72),                           # north chain, Red end (skerry L mirrored)
    'chapel': (422, 439),                        # south chain, Red end (skerry L, y-mirror + x-mirror)
    'iceberg': (46, 476),                        # SW corner, under the sky-level tag
    'tag': {'text': 'YULEHAVEN ISLES', 'x0': 10, 'y0': 492, 'z': 8},

    # declared waivers (babel_checks summary row key -> reason)
    'waivers': {'spawn_exposure_blue': 'owner 2026-11-15: accept the open-front trade-off',
                'spawn_exposure_red': 'owner 2026-11-15: accept the open-front trade-off'},

    'deviations': [],
}
