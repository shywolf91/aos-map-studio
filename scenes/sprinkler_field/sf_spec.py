"""Sprinkler Field: the single source of truth for every number in the generator (docs/sprinkler_field_spec.md).

A lawn just after watering, seen by a person the size of an ant (inspired by the scale of the game Grounded; no
landmark, character or name is taken from it). Stock Babel (piqueserver 1.4.2 babel_script), ground Babel,
**Babel with assist structures** (knowledge base 8.8). Owner answers 2026-11-15: new map (not Backyard Babel v6),
assist structures, glow blocks, an underground layer (ant nest), floating sky decor; no heavens_color.

Coordinates are the WEST (blue) half and the centre axis; the east half is the mirror x' = 512 - x ('x512',
column 255 copied into 256). Centre-axis objects (sprinkler, feeder hose, trowel, queen chamber) are built after
mirroring and are self-symmetric. One-off landmarks are placed after mirroring and listed as cosmetic boxes.
z = 0 is the sky top, z = 63 the bottom; a "floor z" is the solid voxel a player stands on. Boxes are inclusive.
Scale: 1 voxel ~ 1.5 mm. A grass blade is 25-40 voxels tall, a pebble is a boulder, the hose is a walk-through pipe.
"""

SPEC = {
    'name': 'Sprinkler Field', 'file': 'sprinkler_field', 'version': '1.0',
    'layout_seed': 20261115, 'axis': 'x512',
    'fog': (206, 186, 216),                     # morning-haze lavender: absent from the green/soil/brass/hose palette
    'water_damage': 0,                          # no z 63 water anywhere; puddles are painted shallow dips

    # ---------------------------------------------------------------- elevations (floor z)
    'z': {
        'lawn': 52,                             # mean soil; rolls 50-54 everywhere, never flat outside built surfaces
        'spawn': 50, 'anchor': 52, 'front_crest': 47,
        'puddle': 54,                           # painted water, 1-2 deep dips, always a walk-out rim
        'tunnel_floor': 60, 'tunnel_air': (56, 59),   # ant nest: 4 air, >= 3 soil roof (so ground above is z <= 52)
        'bedrock': 62,
    },
    'relief': {'amp': 2.0, 'cell': 30, 'mound_amp': 3.0, 'mound_cell': 70},

    # ---------------------------------------------------------------- Babel (stock 1.4.2, see params.BABEL_DEFAULT)
    'spawn': {'base': (118, 256), 'half': 20, 'margin': 4},          # square 98-138 / 236-276: gentle mound, no props
    'front': {'x': (139, 199), 'y': (236, 276)},                     # open; low dressing only (<= 10 tall)
    'anchor': {'x': (200, 212), 'y': (236, 276), 'z': 52},           # flat, solid to the bottom, no objects, no tunnel
    'front_crest': {'x0': 143, 'crest': (148, 153), 'z': 47},        # soil rise 3 above the spawn floor (spawn cover)
    'zone_blend': 12,
    'no_tunnel_boxes': [(90, 146, 228, 284), (139, 216, 232, 280)],  # (x0, x1, y0, y1): spawn + margin, front + anchor

    # ---------------------------------------------------------------- assist structure 1: the tripod sprinkler
    # Self-symmetric on the axis, NORTH of the platform (the under-platform strip stays low: zone rule under_platform).
    # Climb: up a leg (stepped tube, 3 wide, 1-voxel steps, rails of rivets) -> collar deck -> spiral of nozzle
    # fittings round the riser -> head deck -> along the spray arm to the T-bar landing beside the platform north edge.
    'sprinkler': {
        'hub': (256, 210),
        'legs': {'W': (224, 204), 'N': (256, 174)},      # foot centres; E is the mirror of W. Feet are 7x7 pads
        'leg_w': 3, 'collar_z': 24, 'collar_r': 6,       # collar deck (standable ring) where the three legs meet
        'riser_r': 3, 'head_z': 9, 'head_r': 5,          # head deck floor z 9
        'arm': {'y': (215, 237), 'z': 6, 'w': 3},        # spray arm running south from the head, stepping 9 -> 6
        'tbar': {'x': (240, 272), 'y': (235, 237), 'z': 6},   # landing; platform is x 206-305, y 240-271, z 1
        'gap_target': (4, 6),                            # build gap from the landing to the platform, both teams equal
        'counter_arm': {'y': (190, 205), 'z': 9},        # impact-hammer arm + spring on the north side (cosmetic)
    },
    # ---------------------------------------------------------------- assist structure 2: the garden trowel
    # Self-symmetric on the axis, SOUTH of the platform. Blade half-buried in a soil heap, handle leaning north.
    # Longer build than the sprinkler (slower, safer route).
    'trowel': {
        'blade': {'x': (244, 268), 'y': (296, 330), 'tip_z': 54, 'shoulder_z': 40},   # scoop, walk up the centre rib
        'handle': {'from': (256, 296, 38), 'to': (256, 277, 12), 'r': 3},             # stepped, 1-voxel steps
        'cap': {'c': (256, 276), 'z': 11, 'r': 4},                                   # landing: handle end cap
        'gap_target': (8, 11),
        'heap': (256, 316, 20, 14, 46),                  # (cx, cy, rx, ry, peak floor z) loose soil the blade sits in
    },

    # ---------------------------------------------------------------- the garden hose (north flank route)
    # A pipe: outer radius 6, wall 2, bore radius 4 (walk through where it is split open). Centre line z 46 on the
    # ground (bottom at 52). Top is walkable (z 40); coupling rings give steps up at each end and at each arch.
    'hose': {
        'r_out': 6, 'r_in': 4,
        'path': [(0, 132), (60, 126), (120, 118), (180, 122), (230, 116), (256, 116)],   # west half; mirrored
        'arches': [((84, 104), 12), ((150, 172), 12)],   # (x range, lift): hose humps over pebbles - walk under it
        'split': (196, 222),                             # x range where the top third is torn off: walk inside
        'feeder': {'path': [(256, 116), (256, 150), (256, 172)], 'r_out': 4, 'r_in': 0},   # axis: Y-coupling -> N leg
        'crossings_min': 3,                              # per half: 2 arches + the split; plus both map edges
    },

    # ---------------------------------------------------------------- south flank route (brick edging + mud trail)
    'south_trail': {'y': (384, 396), 'x': (40, 256)},                # worn mud trail, ~135 from the centre
    'edging': {'y': (404, 412), 'x': (0, 256), 'brick_len': 34, 'gap': 9, 'top_z': 44},   # row of bricks, gaps between

    # ---------------------------------------------------------------- underground: the ant nest (west; mirrored)
    # Flank <-> mid-field, never under spawn/front/anchor. Tunnels 5 wide. Entrances are crater mounds with a
    # walkable spiral/ramp (drops <= 3). Fungus glow inside.
    'nest': {
        'entrances': {'A': (112, 168), 'B': (218, 172), 'C': (112, 344), 'D': (218, 338)},
        'chambers': {'north': (166, 170, 13, 9), 'south': (166, 342, 13, 9)},     # (cx, cy, rx, ry)
        'tunnels': [
            [(112, 168), (140, 172), (166, 170), (196, 168), (218, 172)],
            [(112, 344), (140, 340), (166, 342), (196, 344), (218, 338)],
            [(218, 172), (238, 158), (256, 150)],        # to the queen chamber on the axis (links both halves)
        ],
        'queen': (256, 150, 15, 11),                     # self-symmetric chamber under the feeder hose
        'w': 5,
    },

    # ---------------------------------------------------------------- centre objects (west half; mirrored)
    # Every feature is distinct, 7-10 voxel gaps between features, crossable on foot, median footprint >= 25 cells.
    # kinds: tussock = clump of 5-9 tapered curved blades (2-3 thick at the base, 25-40 tall), clover = stalked
    # trefoil canopy (12-18 tall, walk under), dandelion = hollow stalk + seed globe (30-36 tall), pebble = boulder
    # (4-9 tall, some climbable), mushroom = cap you can stand under (8-14 tall), acorn, twig (lying log, walk-over),
    # leaf (curled fallen leaf = lean-to shelter), cap (bottle cap bunker, rim 3 tall), pinecone (10 tall, climbable).
    'tussocks': [
        (70, 256, 16), (84, 222, 13), (84, 290, 13), (104, 210, 10), (104, 302, 10),       # spawn rear and sides
        (150, 200, 11), (150, 312, 11), (176, 184, 10), (176, 328, 10), (196, 214, 8), (196, 298, 8),
        (130, 150, 12), (130, 362, 12), (60, 180, 14), (60, 332, 14), (236, 190, 7), (236, 320, 7),
        (40, 90, 14), (40, 440, 14), (120, 70, 14), (120, 450, 14), (200, 60, 14), (200, 460, 14),
        (30, 256, 12), (170, 256 - 150, 10), (170, 256 + 150, 10),
    ],                                                                # (cx, cy, grove radius)
    'centre_props': [
        ('pebble', 160, 224, 7), ('pebble', 160, 288, 7), ('clover', 184, 228, 8), ('clover', 184, 284, 8),
        ('mushroom', 204, 190, 7), ('mushroom', 204, 322, 7), ('dandelion', 168, 206, 5), ('dandelion', 168, 306, 5),
        ('acorn', 222, 224, 5), ('acorn', 222, 288, 5), ('twig', 190, 150, 16), ('twig', 190, 362, 16),
        ('leaf', 140, 180, 10), ('leaf', 140, 332, 10), ('cap', 232, 150, 7), ('pinecone', 232, 362, 7),
        ('pebble', 110, 190, 8), ('pebble', 110, 322, 8), ('clover', 230, 300, 6),
    ],                                                                # (kind, cx, cy, radius)
    'front_props': [
        # 4-15 low objects (<= 10 tall) on 5-30 % of the front band; every 8-column N-S section >= 50 % free
        ('pebble_low', 158, 244), ('daisy', 166, 268), ('twiglet', 176, 250), ('seed', 184, 262),
        ('clover_low', 190, 242), ('pebble_low', 172, 272), ('dewdrop', 150, 258), ('sprout', 194, 256),
    ],
    'spawn_cover': [(146, 226, 5), (146, 286, 5)],     # pebble boulders on the enemy-facing corners, outside the front
    'under_platform': [
        # strip x 212-300, y 240-271: 15-45 % object columns, tops >= 25 below the platform (z >= 27); nothing on the
        # 6 anchor columns under each platform end
        ('puddle', 232, 256, 9), ('pebble', 246, 246, 5), ('clover_low', 244, 266, 5), ('cap', 256, 256, 6),
    ],
    'puddles': [(96, 150, 12), (96, 362, 12), (210, 256 - 118, 10), (62, 256, 8)],     # (cx, cy, r) painted, shallow

    # ---------------------------------------------------------------- one-offs (after the mirror; cosmetic boxes)
    'oneoffs': {
        'spigot': (14, 132),             # W end of the hose: brass tap on a concrete footing, dripping (glow dew)
        'hose_reel': (498, 132),         # E end of the hose: reel cart with a crank, enterable drum
        'flowerpot': (60, 420),          # SW: terracotta pot on its side, enterable, soil spill ramp to the rim
        'glove': (452, 420),             # SE: gardening glove, fingers are crawl tunnels, cuff is the door
        'snail_shell': (420, 60),        # NE: empty shell, spiral ramp inside to a lookout hole
        'footprint': (300, 440, 44, 20), # S: a giant sneaker print pressed 2 deep in the mud with puddles in the tread
        'plant_label': (76, 60),         # NW: plastic plant label stake leaning in the soil (blank face, no text)
        'sprinkler_key': (256, 470),     # S axis: dropped T-shaped valve key lying on the ground (bridge to walk on)
    },
    'tag': {'text': 'SPRINKLER FIELD', 'corner': 'SW', 'on_ground': True},

    # ---------------------------------------------------------------- art pass
    'glow': ['dew beads on blade tips and clover', 'fireflies resting on stalks (attached, never free-floating)',
             'tunnel fungi', 'spigot drip', 'sprinkler nozzle droplets'],
    'sky': {'dandelion_seeds': 6, 'dragonflies': 2, 'rules': '>= 60 from the platform, >= 8 air below, not over a '
            'spawn square, each >= 13 wide; listed as expected floating; collapse caveat in the spec'},
    'palette': {
        'grass': 'emerald / chartreuse / olive / teal families with smooth base-to-tip gradients',
        'soil': 'warm umber, luma >= 40; mud trail darker but >= 40', 'hose': 'garden green with a yellow stripe',
        'sprinkler': 'galvanised grey legs, brass head, orange plastic collar', 'trowel': 'steel blade, red-free '
        'wooden handle (ochre) - no team colours on any authored object',
    },

    'waivers': {},                       # filled only by the owner; report trade-offs instead of waiving silently
    'zone_rules_skip': {},
    'deviations': [],
}
