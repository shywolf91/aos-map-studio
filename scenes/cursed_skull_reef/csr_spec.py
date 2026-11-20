"""Cursed Skull Reef: the single source of truth for every number in the generator (docs/cursed_skull_reef_spec.md).

A bright moonlit storm night over a cursed pirate reef. Babel with assist structures (AGENTS.md §4 custom variant,
knowledge base §8.8), island Babel in the CURRENT (dense, authored) style. Owner answers 2026-11-15: mixture of
"Skull Cove Archipelago" (two mirrored spawn isles joined by a shoal neck, a skull-shaped crag with a sea cave at
the centre, a cannon fort, a ruined pirate town, moored brigs on the flanks) and "Shipwreck Graveyard" (wrecked
galleons and broken masts in a central lagoon that act as assist structures, a maelstrom painted on the sea,
driftwood-and-rope harbour spawns). Mood: moonlit night + cursed stormy sea. water_damage 1. Extras: glow blocks
and floating sky decor. No underground layer. Original designs only (no film names, logos, characters, landmarks).

Coordinates are the WEST (blue) half and the centre axis; the east half is the mirror x' = 512 - x ('x512', column
255 copied into 256). Axis objects (skull crag, half-sunk galleon, cannon fort, bridge ruin, ribs) are built as
their west half + axis column before the mirror and come out symmetric. One-offs (ruined tavern, rum-barrel dock,
lighthouse stump, gallows, heeled-over brig, corner tag, sky decor) are placed after the mirror and listed as
cosmetic boxes. z = 0 is the sky top, z = 63 the bottom; a "floor z" is the solid voxel a player stands on.
"""

SPEC = {
    'name': 'Cursed Skull Reef', 'file': 'cursed_skull_reef', 'version': '1.0',
    'layout_seed': 20261115, 'axis': 'x512',
    # pale ghost-jade: green is neutral between Blue and Red; the palette keeps to sand, timber, bone, olive palms,
    # blue-teal sea and warm lantern light, so the fog hue is free. Bright (min channel 156) per owner rule.
    'fog': (156, 184, 170),
    'water_damage': 1,

    # ---------------------------------------------------------------- elevations (floor z)
    'z': {'water': 63, 'spawn': 48, 'anchor': 52, 'neck': 61, 'plateau': 48, 'reef': 61},

    # ---------------------------------------------------------------- Babel (stock 1.4.2, params.BABEL_DEFAULT)
    'spawn': {'base': (118, 256), 'half': 20, 'margin': 4},           # square 98-138 / 236-276
    'front': {'x': (139, 199), 'y': (236, 276)},
    'anchor': {'x': (200, 212), 'y': (236, 276), 'z': 52},             # mirror -> red x 300-312 (end 300-305)
    'front_crest': {'x0': 143, 'crest': (148, 153), 'z': 45},          # 3 above the spawn floor, then down
    'zone_blend': 12,

    # ---------------------------------------------------------------- spawn isle (west; east is the mirror)
    'island': {
        'ellipses': [(112, 256, 80, 94), (164, 204, 40, 34), (164, 308, 40, 34), (62, 178, 34, 36),
                     (62, 334, 34, 36), (190, 256, 30, 52)],
        'x_max': 204, 'x_max_shoulder': 214, 'shoulder_y': [(218, 235), (277, 294)],
        'edge_noise': 0.14, 'beach_w': 6, 'rise_w': 20, 'relief_amp': 4.0, 'relief_cell': 24,
        # rear ridge (spawn backdrop): rises up to `h` above the plateau, centred x, half-length in y
        'rear_ridge': {'x': (50, 84), 'y': (196, 316), 'h': 7},
    },

    # ---------------------------------------------------------------- centre (axis / west halves)
    'neck': {'x': (213, 255), 'y': (238, 274), 'z': 61,
             'shoulders': [((213, 234), (226, 237)), ((213, 234), (275, 286))]},
    'fort_islet': {'c': (256, 140), 'rx': 44, 'ry': 28, 'z': 52, 'edge_noise': 0.08},
    'skull_islet': {'c': (256, 352), 'rx': 46, 'ry': 38, 'z': 54, 'edge_noise': 0.08},
    'stern_reef': {'x': (247, 255), 'y': (214, 237)},                 # reef bar under the galleon stern -> neck
    'maelstrom': {'c': (256, 296), 'r': 19},                          # painted on the z 63 sea (south lagoon)

    # half-sunk galleon on the axis, bow north (sunk at the fort islet), stern south (raised on the stern reef)
    'galleon': {'y': (158, 226), 'x_c': 256, 'beam_half': 10, 'deck_stern': 46, 'deck_bow': 61, 'depth': 13,
                'quarter_y': (206, 226), 'poop_y': (216, 226), 'masts_y': (176, 196), 'mast_top': 22},

    # assist wreck (west; mirror = east): broken-off stern of a galleon beached on the neck shoulder,
    # mizzen mast wrapped in a spiral rope-and-plank stair up to a crow's-nest ring next to the platform
    'assist': {'x_c': 221, 'beam_half': 7, 'y': (204, 236), 'keel': 62, 'decks': (60, 55, 50),
               'quarter_y': (222, 236), 'quarter_z': 45, 'mast': (221, 229), 'nest_z': 8, 'nest_r': 6.5,
               'stair_r': 4},

    # cannon fort on the fort islet (axis): curtain walls, south gate, bastion towers, barracks, magazine
    'fort': {'x': (230, 282), 'y': (122, 156), 'floor': 52, 'wall_top': 42, 'wall_t': 2,
             'tower': (230, 240, 146, 156), 'barracks': (238, 255, 124, 134), 'magazine': (232, 241, 124, 134)},

    # skull crag (axis): cranium, cheekbones, jaw over the sea cave, eye-socket rooms, inner stair
    'skull': {'cranium': (256, 348, 34, 30, 28, 24), 'maxilla': (256, 332, 45, 25, 15, 10),
              'eye': (244, 320, 31, 6.0, 9.0, 5.5), 'eye_room': (237, 251, 316, 328, 25, 31),
              'nose': (256, 322, 42), 'mouth': (236, 255, 318, 342, 50, 62), 'pool_x': 248, 'ledge_z': 60,
              'stair_x': (238, 240), 'stair_y0': 360, 'chest': (256, 342)},

    # skull bridge ruin across the maelstrom (axis): neck south beach -> skull jaw ledge
    'bridge_ruin': {'x': (254, 255), 'y': (275, 339), 'z': 61, 'broken': (290, 300)},

    # ---------------------------------------------------------------- flank chains (north; south = y-mirror)
    'skerries': {'N1': (124, 112, 15, 52), 'N2': (176, 90, 11, 54), 'N3': (220, 82, 10, 55), 'M': (256, 78, 15, 51)},
    'links': [
        ('pier', [(124, 172), (124, 126)], 3),               # isle north shore -> N1
        ('rope', [(134, 104), (170, 93)], 3),                # N1 -> N2
        ('broken', [(186, 86), (212, 86)], 3),               # N2 -> N3 (sagging, broken stretch)
        ('rope', [(226, 80), (244, 79)], 3),                 # N3 -> M
    ],
    'centre_links': [
        ('rope', [(184, 178), (224, 150)], 3),               # isle NE lobe -> fort islet
        ('rope', [(186, 336), (220, 344)], 3),               # isle SE lobe -> skull islet
    ],
    'axis_piers': [((255, 92), (255, 116)), ((255, 384), (255, 420))],   # M -> fort islet, skull islet -> S-M

    # ---------------------------------------------------------------- spawn isle structures (west; mirrored)
    'houses': [
        # (name, x0, x1, y0, y1, storeys, ridge, door, ruin) - ruined pirate town; ruin: 'roof' / 'corner' / None
        ('chandlery', 88, 101, 198, 209, 2, 'x', 'S', None),
        ('cooperage', 108, 119, 190, 201, 1, 'y', 'S', 'roof'),
        ('powder house', 140, 153, 220, 231, 2, 'x', 'S', 'corner'),
        ('net loft', 88, 101, 303, 314, 2, 'x', 'N', 'roof'),
        ('sail maker', 108, 120, 311, 322, 1, 'y', 'N', None),
        ('harbour master', 140, 153, 281, 292, 2, 'x', 'N', None),
        ('smithy', 54, 67, 228, 241, 1, 'y', 'E', 'corner'),
        ('rope store', 54, 65, 272, 283, 1, 'y', 'E', None),
        ('lookout cabin', 62, 73, 250, 261, 2, 'y', 'E', None),
    ],
    'harbour': {'pier_y': (240, 272), 'pier_x': (26, 40)},               # west harbour behind the spawn
    'brig': {'x': (92, 130), 'y': (66, 78), 'deck': 56, 'pier': ((118, 79), (118, 102))},   # moored brig at N1
    'alcoves': [(54, 214, 'W'), (54, 298, 'W')],                        # treasure-chest alcoves in the coast rock
    'front_props': [
        # (kind, x, y): low dressing (<= 10 tall), every N-S section >= 50 % free
        ('hut', 147, 238), ('hut', 147, 268), ('rowboat', 160, 250), ('crates', 171, 264), ('barrels', 178, 242),
        ('cannon', 188, 256), ('logs', 165, 240), ('anchor', 194, 268), ('pots', 186, 272),
    ],
    'spawn_cover': [(158, 226, 4), (158, 286, 4)],                      # boulders on the enemy-facing corners
    'strip_props': [
        # (kind, x, y) on the neck under the platform (west half; ribs and chest pile are axis pieces)
        ('mast_log', 214, 243), ('longboat', 216, 252), ('anchor_big', 233, 258), ('coral', 222, 266),
        ('coral', 236, 250), ('barrels', 228, 264), ('cannon', 240, 268),
    ],
    'ribs': {'x': (241, 255), 'y': (247, 265), 'h': 9, 'every': 3},
    # vegetation groves (art pass, OS seed): (x, y, radius, kind) kind: palm / dead / mangrove / mix
    'groves': [(150, 212, 8, 'palm'), (150, 300, 8, 'palm'), (66, 214, 12, 'mix'), (66, 298, 12, 'mix'),
               (84, 256, 9, 'palm'), (100, 176, 10, 'palm'), (100, 336, 10, 'palm'), (40, 250, 10, 'mix'),
               (160, 178, 9, 'mangrove'), (162, 334, 9, 'mangrove'), (36, 196, 9, 'dead'), (36, 316, 9, 'dead'),
               (128, 168, 8, 'palm'), (128, 344, 8, 'palm'), (124, 112, 6, 'palm'),
               (176, 90, 5, 'dead'), (176, 421, 5, 'palm'), (232, 140, 6, 'palm'), (226, 360, 7, 'dead'),
               (236, 382, 6, 'mangrove')],

    # ---------------------------------------------------------------- one-offs (after the mirror)
    'tavern': (40, 156),          # ruined tavern on stilts (Blue NW shore)
    'lighthouse': (472, 156),     # lighthouse stump (Red NE shore)
    'rum_dock': (124, 399),       # rum-barrel dock (Blue south chain S1)
    'gallows': (388, 399),        # gallows (Red south chain S1)
    'heeled_brig': (256, 58),     # heeled-over brig beside the north chain middle islet
    'tag': {'text': 'CURSED SKULL REEF', 'corner': 'SW', 'bar': (4, 116, 486, 508)},

    # assist structures for the kit report (west box; east = mirror)
    'assist_box': (212, 230, 204, 236),

    'waivers': {},
    'deviations': [],
}
