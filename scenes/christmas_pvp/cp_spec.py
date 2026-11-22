"""Christmas PVP v2 - every number of the rework in one dict (single source of truth).

Community map: 'Christmas PVP' by GTR-CODE (Minecraft export, planetminecraft 'mapa-boxpvp-free').
Rework tier M (owner 2026-11-22): light rework, ~90 % same geometry. Recolour to a cozy Christmas evening, glow
blocks, light strings on the arena walls and coaster rails, light walk-through spawn cover. Stock Babel, labelled
"Babel with assist structures" because the two giant centre trees (kept unchanged) reach to z 3 under the platform.

Rationale for the numbers the guru is likely to question
* mirror axis 'x512' (x' = 512 - x): measured on the original, 2 690 mismatched columns with x512 against 23 068
  with x511; arena x 91-421 is symmetric about 256 (91 + 421 = 512).
* cover trees at x 145 (trunk 145-146), y 244 / 256 / 268, 18 tall, crown radius 6 from 4 above the floor:
  sightline sweep (calibrated model) on the original west spawn gave 75 / 441 hidden spots (17 %) against 18 (4 %)
  before; x 147 or 16-tall trees fell below 15 %. The crown keeps x >= 139 (outside the stock +/-20 square) and starts
  4 above the floor, so players walk under it (walk-through cover, the paths under them stay open).
* garland hook height z 13 and sag 5 (z 13-18): hangs on the plain wall above the coaster terraces and floating decor
  (most tops z ~15-30), 44-49 above the arena floor (z 62), so it reads from spawn and front as a festive ring.
* bulb spacing 8 along garlands, 12 along coaster rails (r2: halved for speckle and .txt size): dots, never a 1-voxel stripe (anti-flicker rule).
* fog: violet-rose dusk, not used by the graded palette, low chroma so it leans to neither team.
"""

SPEC = {
    'name': 'Christmas PVP',
    'file': 'ChristmasPVP',
    'version': '2.0',
    'slug': 'christmas_pvp',
    'source': r'D:/Ace of Spades/Aloha.pk_Map/maps/ChristmasPVP.vxl',
    'source_sha256': None,                 # filled at build time (recorded in build.json)
    'layout_seed': 20261122,
    'axis': 'x512',
    'arena': {'x': (91, 421), 'y': (132, 381), 'floor_z': 62},
    'perimeter': {'x': (91, 421), 'y': (132, 381)},           # 1-voxel wall core rising to z 0
    'spawn': {'bases': ((118, 256), (394, 256)), 'half': 20},
    'platform': {'x': (206, 305), 'y': (240, 271), 'z': 1},

    # ---------------------------------------------------------------- additions (west side, mirrored x' = 512 - x)
    'cover': {
        'trees': [  # trunk corner (2x2 trunk), height above floor, crown radius, crown starts this far above floor
            {'name': 'lit fir N', 'x': 145, 'y': 244, 'h': 18, 'r': 6.0, 'clear': 4},
            {'name': 'lit fir C', 'x': 145, 'y': 256, 'h': 18, 'r': 6.0, 'clear': 4},
            {'name': 'lit fir S', 'x': 145, 'y': 268, 'h': 18, 'r': 6.0, 'clear': 4},
        ],
        'min_x': 139,                       # nothing of the cover inside the stock spawn square (x <= 138)
        'drifts': [  # low snow drifts (walkable, 1-2 high) hugging the tree feet: centre x, y, radii, height
            {'x': 149, 'y': 250, 'rx': 4, 'ry': 3, 'h': 1},
            {'x': 150, 'y': 263, 'rx': 4, 'ry': 3, 'h': 2},
            {'x': 143, 'y': 274, 'rx': 3, 'ry': 2, 'h': 1},
        ],
        'gifts': [  # gift pile beside the centre fir: boxes x0, x1, y0, y1, height (stacked from the floor)
            {'x': (150, 152), 'y': (254, 256), 'h': 3},
            {'x': (151, 152), 'y': (257, 258), 'h': 2},
            {'x': (149, 150), 'y': (258, 259), 'h': 1},
        ],
        'sleigh': {'x': (154, 162), 'y': (269, 273), 'h': 4},   # parked sleigh, open seat (walk-in), runners
    },

    # ---------------------------------------------------------------- lights
    'garland': {'hook_z': 13, 'sag': 5, 'period': 24, 'thick': 2, 'bulb_every': 8,
                'max_face_depth': 2},       # paint only the plain wall core (first solid within 2 of the perimeter)
    'rail': {'bulb_every': 12, 'max_from_wall': 26},
    'tree_lights': {'every': 22},            # spiral string on the cover firs and the giant centre trees
    'glow_palette': {                       # knowledge base 11.4: only these colours are glow sources
        'white': (255, 255, 255), 'red': (255, 95, 95), 'yellow': (255, 255, 95),
        'cyan': (95, 255, 255), 'amber': (255, 175, 95), 'green': (95, 255, 95)},
    'bulb_cycle': ('amber', 'red', 'amber', 'yellow'),      # warm strings only (r2: no cyan/green glitter)
    'glow': {'radius': 6.5, 'strength': 0.32},

    # ---------------------------------------------------------------- grade (OKLab / RGB anchors)
    'grade': {
        'general': {'L_mult': 0.80, 'L_add': 0.035, 'chroma': 0.90, 'tint_hue': 272, 'tint_amount': 0.022},
        'snow_ramp': [(0.00, (70, 82, 128)), (0.30, (104, 116, 160)), (0.62, (136, 148, 186)),
                      (0.85, (160, 170, 202)), (1.00, (178, 184, 210))],
        'wall_ramp': [(0.00, (74, 84, 132)), (0.45, (110, 116, 164)), (0.80, (150, 142, 184)),
                      (1.00, (176, 156, 188))],                    # floor -> top: dusk sky glow near the rim
        'ice_ramp': [(0.00, (84, 124, 168)), (0.50, (118, 160, 196)), (1.00, (150, 186, 210))],
        'frozen_ramp': [(0.00, (62, 98, 136)), (0.50, (86, 128, 164)), (1.00, (124, 164, 192))],
        'frost_crack': (156, 186, 206),
        'garland_greens': [(36, 84, 58), (48, 104, 66), (60, 116, 72)],
        'window_warm': [(176, 112, 58), (214, 150, 80), (236, 184, 112)],
    },
    'fog': (188, 170, 198),
    'heavens_color': None,                 # not used: fog carries the dusk; no owner request
    'corner_tag': None,                    # every arena corner is occupied by coaster terraces (see build.json)
    'assist_trees': {'blue giant tree': (209, 238, 236, 270), 'red giant tree': (274, 303, 236, 270)},
}
