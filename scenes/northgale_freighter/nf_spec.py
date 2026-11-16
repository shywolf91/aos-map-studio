"""Northgale Freighter: the single source of truth for every number in the generator.

Classic island Babel (docs/classic_island_style.md) where the "island" is one huge cargo freighter on a cold
north sea at night (owner brief 2026-11-16: both spawns and the tower zone are on the ship, explorable areas under
the deck, the deck at a middle height, walkable shallows and islets, sky decor, glow / night mood, boundary
damage = deep sea). Stock Babel (piqueserver 1.4.2 babel_script).

Symmetry 'x512' (x -> 512 - x). The symmetric core x 73-439 is authored on the west half and mirrored. The ship's
ends are one-offs placed after the mirror (cosmetic boxes): the raked bow with the forecastle and foremast in the
west (behind blue), the bridge superstructure, funnel and poop deck in the east (behind red).
z = 0 is the sky top, z = 63 the bottom; a "floor z" is the solid voxel a player stands on. Boxes are inclusive.
"""

SPEC = {
    'name': 'Northgale Freighter', 'file': 'northgale_freighter', 'version': '1.2', 'stage': 'art',
    'layout_seed': 20261116, 'axis': 'x512',
    'fog': (112, 114, 134),                     # v1.2 owner: 'Storm dusk' slate fog (v1.0/1.1: (170, 164, 190))
    'heavens_color': (44, 48, 70, 255),         # v1.2: stormier sky
    'boundary': {'left': 8, 'right': 503, 'top': 72, 'bottom': 440, 'damage': 1},    # outside = deep sea
    'water_damage': 0,                          # inside the boundary the sea is walkable shallows

    # ------------------------------------------------------------------ elevations (floor z)
    'z': {'deck': 40, 'tween': 50, 'hold': 59, 'forecastle': 35, 'hatch': 39, 'bulwark_top': 38, 'sea': 63},

    # ------------------------------------------------------------------ hull
    'hull': {'y': (204, 308), 'wall': 3, 'mid_x': (70, 442),
             'bow': {'tip_x': 13, 'rake': 0.36, 'power': 1.8},          # west end, taper from x 70
             'stern': {'end_x': 494, 'rake': 0.22},                     # east end, rounded counter stern
             'core_x': (73, 439)},                                      # mirrored part of the ship
    # solid blocks below the deck: under both spawn squares and under the anchor ground (roof-free columns)
    'solid_below': [(96, 140, 234, 278), (200, 216, 236, 276)],
    'tween': {'x': (80, 256), 'y': (207, 305), 'air': (42, 49),
              'bulkheads': [116, 170], 'doors_y': [(223, 227), (253, 259), (285, 289)],
              'pillar_x': [88, 104, 130, 146, 158, 200, 238], 'pillar_y': [(231, 232), (280, 281)],
              'wells': [(226, 238, 247, 265)]},                         # tween-floor light wells over the hold
    'lower_hold': {'x': (176, 256), 'y': (210, 302), 'air': (52, 58),
                   'stairs': [(180, 212, 214), (180, 298, 300)]},       # (x0, y0, y1) rising +x, 59 -> 50
    'side_port': {'x': (250, 256), 'z_air': (55, 58)},                  # into the lower hold, both sides
    'deck_hatch': {'x': (244, 256), 'y': (246, 266)},                   # open hatch under the platform centre

    # ------------------------------------------------------------------ Babel (stock 1.4.2)
    'spawn': {'base': (118, 256), 'half': 20},
    'anchor': {'x': (200, 216)},                # plain flat deck (no hatch panels) across the anchor columns
    'hatch_bays': [(78, 124), (153, 198), (218, 256)],                 # raised 1-high hatch panels, y 216-296
    'hatch_y': (216, 296),

    # ------------------------------------------------------------------ access
    'companionways': [(122, 211, 1), (176, 211, 1)],                    # (x0, yc, dx) + y-mirrored twins
    'gangways': [(150, 200, 203)],                                      # accommodation ladder (x0, y0, y1) water->deck
    'cranes': [(195, 219)],                                             # pedestal centre (+ y-mirrored twin)
    'jib_rest_x': 160,

    # ------------------------------------------------------------------ props (west half; y-mirror where noted)
    # front x 139-199, y 236-276: <= 10 tall, every 8-col section >= 50 % free
    'front_props': [
        ('container', 139, 237, ('y', 9, 2, 'steel')), ('container', 139, 267, ('y', 9, 2, 'mustard')),
        ('container', 147, 250, ('y', 13, 2, 'grey')),
        ('container', 146, 237, ('x', 14, 1, 'rust')), ('tarp', 160, 250, (10, 7, 4)),
        ('crates', 160, 263, 2), ('container', 176, 270, ('x', 14, 1, 'teal')),
        ('tarp', 184, 240, (9, 6, 5)), ('drums', 194, 255, None), ('pallets', 168, 241, None),
        ('vents', 156, 270, None),
    ],
    # spawn cover beside the front (y-mirrored): container stacks x 140-158
    'cover_props': [('container', 140, 217, ('x', 19, 2, 'steel')), ('container', 140, 224, ('x', 19, 1, 'mustard')),
                    ('container', 74, 217, ('y', 14, 2, 'grey')), ('container', 81, 223, ('y', 10, 1, 'rust'))],
    'cover_props_s': [('container', 140, 291, ('x', 19, 2, 'teal')), ('container', 140, 284, ('x', 19, 1, 'grey')),
                      ('container', 74, 282, ('y', 14, 2, 'mustard')), ('container', 81, 280, ('y', 10, 1, 'steel'))],
    # under-platform strip, west half x 218-255 (mirror gives the east half)
    'strip_props': [('container', 219, 242, ('x', 18, 2, 'rust')), ('tarp', 222, 256, (14, 11, 7)),
                    ('crates', 240, 268, 2), ('drums', 238, 244, None)],
    # centre north / south bands (y-mirrored unless noted)
    'centre_props': [('container', 214, 222, ('x', 16, 1, 'steel')), ('tarp', 234, 213, (12, 7, 5)),
                     ('forklift', 206, 231, None)],
    # deck hold contents under the open hatch / tween deck
    'tween_props': [('container', 82, 246, ('y', 16, 1, 'rust', 'N')), ('container', 142, 268, ('x', 16, 1, 'teal', 'W')),
                    ('container', 182, 240, ('x', 20, 1, 'grey', 'E')), ('container', 244, 248, ('x', 12, 1, 'mustard')),
                    ('crates', 100, 214, 3), ('crates', 196, 290, 2), ('container', 214, 286, ('x', 14, 1, 'steel', 'E'))],

    # ------------------------------------------------------------------ sea, islets (west half + self-symmetric)
    'islets': [   # (cx, cy, r, peak height above sea, hut)
        (96, 116, 20, 9, False), (178, 100, 15, 7, True), (256, 124, 22, 10, False),
        (96, 396, 20, 9, False), (178, 412, 15, 7, True), (256, 388, 22, 10, False),
    ],
    'rocks': [(40, 160, 6, 4), (140, 168, 5, 3), (40, 352, 6, 4), (140, 344, 5, 3), (222, 166, 4, 3),
              (222, 346, 4, 3), (58, 424, 5, 4), (58, 88, 5, 4)],
    'piers': [(178, 114, 152, 'S'), (178, 398, 360, 'N'), (256, 145, 168, 'S'), (256, 367, 344, 'N')],
    'beacons': [(256, 118), (256, 394)],
    # v1.1 (owner 2026-11-16): bigger, enterable lighthouse with glow inside and around (after the mirror)
    'lighthouse': {'r_outer': 6.0, 'r_inner': 5.0, 'height': 26, 'band': 4, 'plinth_r': 7.5, 'gallery_r': 8.2,
                   'posts': 6, 'post_r': 11.5, 'clear_r': 13},
    'buoys': [(40, 80), (120, 80), (200, 80), (40, 432), (120, 432), (200, 432)],
    'groves': [(96, 116), (90, 396), (256, 124), (256, 388), (178, 96), (178, 416), (40, 160), (40, 352)],

    # ------------------------------------------------------------------ one-offs after the mirror
    'forecastle': {'x_break': 66, 'store': (24, 63), 'door_y': (253, 259), 'stairs_y': [(209, 212), (300, 303)]},
    'foremast': {'x': 34, 'y': 256, 'top': 6, 'rings': (24, 15)},
    'bridge': {'x': (446, 478), 'y': (220, 292), 'storeys': 5, 'storey_h': 6, 'wing_y': (207, 305)},
    'funnel': {'x': (481, 490), 'y': (247, 265), 'top': 3},           # v1.2: taller and wider
    'helideck': {'c': (462, 256), 'r': 15},                           # v1.2: on the bridge roof (z 10)
    'detail': {'pipe_y': (213, 214), 'mast_x': [96, 160, 226], 'fire_x': [110, 204], 'raft_x': [86, 236],
               'vent_x': [104, 150, 230], 'vent_y': 215, 'barrels': [(182, 226)],
               'bulb': (25.0, 60.0, 12.0, 5.0, 3.0), 'anchor_x': 46},                 # bulbous bow (cx, cz, rx, ry, rz)
    'lifeboats': [(452, 208), (452, 297)],
    'cosmetic_boxes': [(0, 72, 186, 326), (440, 511, 186, 326)],

    'sky': {'gulls': [(150, 150, 16, 0.4), (166, 158, 18, 0.6), (360, 360, 14, 2.8), (348, 372, 17, 2.6),
                      (440, 120, 20, 3.6)],
            'clouds': [(90, 40, 7, 34), (430, 470, 6, 30), (300, 24, 10, 26), (120, 486, 9, 28)]},

    'tag': {'text': 'NORTHGALE FREIGHTER', 'corner': 'SE', 'margin': 18, 'scale': 2, 'rgb': (196, 192, 170),
            'shadow': (30, 42, 60)},

    'waivers': {},
}
