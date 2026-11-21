"""Frozen Icebreaker: SPEC (single source of truth) and the night palette.

Polar-night ground/island Babel on stock piqueserver 1.4.2 babel_script. Inspired by (not copied from)
arctic_icebreaker.vxl: an icebreaker beset in pack ice north of the platform, a drift research station south of it,
expedition camps at the spawns, blue-ice tunnels from the north flanks into the ship's hold.

Coordinates: x, y 0..511 (y grows south), z 0..63 with z = 0 the sky top. The west half (x <= 255) is authored and
mirrored x' = 512 - x; the ship (asymmetric) is drawn after the mirror inside a declared cosmetic box.
"""

SPEC = {
    'name': 'Frozen Icebreaker',
    'file': 'frozen_icebreaker',
    'version': '1.0',
    'layout_seed': 20261120,
    'axis': 'x512',
    # ---------------------------------------------------------------- terrain
    'ice_z': 54,                 # field top (standing floor); sea is the z 63 layer; 9 above the water
    'sea_z': 63,
    'island': {'cx': 256, 'cy': 256, 'rx': 232, 'ry': 214, 'warp': 26},   # superellipse, fbm-warped coast
    'shore_band': 8,             # coastal slope 54 -> 62 over this many columns (cliff stretches where noise says)
    # ---------------------------------------------------------------- Babel (stock constants, kit BABEL_DEFAULT)
    'platform': {'x': (206, 305), 'y': (240, 271), 'z': 1},
    'spawn': {'base': (118, 256), 'half': 20},
    'anchor_x': (196, 211),      # flat, prop-free ground under the platform end (+ 10 columns of tower apron)
    'front': {'x': (139, 211), 'y': (236, 276)},
    'strip': {'x': (212, 300), 'y': (240, 271)},
    # ---------------------------------------------------------------- landmarks
    'ship': {'x': (182, 330), 'y': (156, 196), 'deck_z': 44, 'tween_z': 53, 'hold_z': 61},
    'ship_cosmetic_box': [160, 352, 146, 206],      # symmetric about x 256 (bow-wave floes included)
    'station': {'lab_x': 186, 'lab_y': 300, 'derrick_y': 300},
    'lodge': {'x': 58, 'y': 238},                 # expedition lodge behind the blue spawn (rear backdrop)
    'schooner': {'y': (80, 136)},                  # old expedition schooner frozen in, keel on x = 256 (north flank)
    'plane': {'y': (378, 420)},                    # crashed ski-plane, fuselage on x = 256 (south flank)
    'tunnel': {'mouth': (92, 132), 'run_y': 140, 'end_x': 236, 'floor_z': 61, 'air': (56, 60)},
    # ---------------------------------------------------------------- look
    'fog': (164, 186, 160),      # pale aurora green: hue absent from the palette, neutral between blue and red
    'heavens': (34, 52, 86, 255),
    'tag_corner': 'SE',
}

# Night-graded base colours (before kit lighting/AO). Snow follows docs/colour_palette_guide.md §4: field is the
# lightest broad band at luma ~135, crests short and broken, troughs along tracks; nothing near the 212 cap.
PAL = {
    # snow / ice field
    'snow': [(122, 134, 151), (126, 138, 155), (119, 131, 148), (124, 137, 152)],
    'snow_crest': [(150, 160, 173), (156, 165, 177)],
    'snow_trough': [(100, 112, 130), (96, 108, 127), (104, 116, 133)],
    'track': [(108, 112, 122), (102, 107, 118), (112, 116, 124)],
    'lead': [(62, 80, 104), (58, 76, 100), (68, 86, 108)],
    'ice': [(92, 136, 166), (104, 148, 176), (86, 128, 160), (98, 142, 170)],
    'ice_deep': [(60, 98, 132), (66, 106, 138), (56, 92, 126)],
    'ice_cap': [(138, 152, 168), (144, 156, 170)],
    'cave': [(70, 116, 150), (78, 126, 158), (64, 108, 144)],
    'sea': [(28, 54, 90), (30, 58, 94), (26, 51, 86)],
    'shallow': [(40, 74, 108), (44, 80, 112)],
    'seabed': [(44, 64, 88), (40, 60, 84)],
    # timber / stone / metal
    'plank': [(140, 108, 74), (130, 100, 68), (146, 114, 78)],
    'beam': [(88, 68, 54), (82, 64, 50)],
    'dwood': [(104, 80, 60), (96, 74, 56)],
    'log': [(124, 92, 64), (116, 86, 60), (130, 98, 68)],
    'stone': [(108, 110, 116), (98, 100, 108), (114, 116, 120)],
    'concrete': [(116, 118, 122), (108, 110, 114)],
    'steel': [(120, 126, 134), (112, 118, 126)],
    'dsteel': [(72, 76, 84), (66, 70, 78)],
    'rust': [(124, 82, 58), (114, 76, 54)],
    # buildings
    'clad_ochre': [(178, 142, 68), (168, 134, 62)],
    'clad_teal': [(84, 120, 124), (78, 112, 116)],
    'clad_log': [(126, 94, 66), (116, 86, 60)],
    'clad_grey': [(132, 136, 140), (124, 128, 132)],
    'clad_moss': [(104, 120, 92), (96, 112, 86)],
    'trim': [(186, 180, 162)],
    'roof': [(74, 80, 94), (82, 88, 102)],
    'roof_wood': [(92, 76, 68), (100, 82, 72)],
    'ridge': [(56, 60, 72)],
    'snow_roof': [(146, 156, 170), (140, 150, 165)],
    'floor': [(128, 100, 72), (120, 94, 68)],
    'furn': [(96, 74, 56)],
    'canvas_o': [(196, 122, 58), (186, 114, 54)],
    'canvas_k': [(150, 136, 98), (142, 128, 92)],
    'canvas_g': [(98, 118, 84), (92, 110, 80)],
    # ship
    'hull': [(48, 52, 62), (44, 48, 58), (52, 56, 66)],
    'hull_band': [(204, 112, 46), (194, 106, 42)],
    'sheer': [(180, 176, 166)],
    'deck': [(98, 110, 102), (92, 104, 96), (104, 114, 106)],
    'super': [(184, 178, 164), (176, 170, 156), (190, 184, 170)],
    'funnel': [(206, 116, 48), (198, 110, 44)],
    'funnel_top': [(46, 48, 54)],
    'lifeboat': [(212, 124, 44), (204, 118, 40)],
    'heli': [(206, 132, 52), (190, 120, 48)],
    'yellow': [(206, 168, 60), (196, 160, 56)],
    'container_g': [(78, 118, 92), (72, 110, 86)],
    'container_y': [(190, 150, 62), (182, 142, 58)],
    'container_s': [(126, 120, 112), (118, 112, 104)],
    'glass': [(60, 74, 92)],
    # props
    'drum_y': [(196, 160, 56)],
    'drum_g': [(80, 110, 80)],
    'drum_s': [(130, 132, 136)],
    'flag_pole': [(150, 152, 156)],
    'fur': [(176, 168, 140), (168, 160, 132), (182, 174, 148)],
    'fur_dark': [(90, 86, 82)],
    'seal': [(84, 86, 94), (92, 94, 100), (78, 80, 88)],
    'walrus': [(132, 98, 78), (124, 92, 72), (140, 104, 82)],
    'tusk': [(196, 186, 156)],
    'bone': [(178, 168, 140)],
    'black': [(40, 40, 46)],
    'team': [(60, 80, 200)],             # recoloured per half by kit color.team_recolor
}

GLOW = {
    'amber': (255, 196, 112),
    'warm': (255, 214, 150),
    'flood': (250, 238, 196),
    'aurora': (130, 238, 186),
    'aurora_b': (150, 214, 238),
    'nav_g': (90, 236, 120),
    'nav_w': (240, 240, 232),
}
