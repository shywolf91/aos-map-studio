"""Exporter / runtime diagnostic scene (NOT an art map).

Every object exists to test one rule. Coordinates: x, y 0..511, z 0..63, z = 0 is the sky.
Ground top surface is z = 58 (solid 58..62); outside the island z = 62 is air -> water.

Run:  python scenes/diagnostic.py out/diagnostic
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aosmap.scene import Scene, Material  # noqa: E402

SEED = 7501
GROUND = 58          # top surface z of the island
GATE_RGB = (201, 77, 211)


def build():
    s = Scene('aosmap_diagnostic', seed=SEED)
    soil = s.material(Material('soil', (124, 98, 68), jitter=3, top=(98, 138, 70), depth_ramp=0.04))
    rock = s.material(Material('rock', (108, 104, 98), jitter=3, depth_ramp=0.03))
    stone = s.material(Material('stone', (172, 166, 150), jitter=2))
    roof = s.material(Material('roof', (150, 72, 56), jitter=2))
    wood = s.material(Material('wood', (118, 84, 54), jitter=2))
    gate = s.material(Material('gate', GATE_RGB))                    # exact colour, no jitter!
    flt = s.material(Material('float_test', (255, 64, 160)))
    diag = s.material(Material('diag_test', (255, 200, 0)))
    swatches = [((200, 40, 40), 'red'), ((230, 140, 30), 'orange'), ((230, 210, 60), 'yellow'),
                ((60, 160, 90), 'leaf'), ((60, 170, 190), 'teal'), ((120, 80, 170), 'violet'),
                ((235, 235, 230), 'white'), ((0, 0, 120), 'pure_blue_TEAM1_HS')]
    sw_ids = [s.material(Material(f'swatch_{n}', c)) for c, n in swatches]

    # --- island: seabed-rooted ground (solid down to z = 62) -------------------------------
    s.box(160, 351, 192, 319, GROUND, 62, soil)
    s.box(160, 351, 192, 319, GROUND + 3, 62, rock)            # rock below 3 voxels of soil

    # --- terraces (3 heights: 58 / 52 / 46) + 1-voxel staircase --------------------------------
    s.box(168, 215, 200, 247, 52, 57, soil)
    s.box(168, 191, 200, 223, 46, 51, soil)
    for i in range(6):                                          # x = 221..216, tops z = 57..52
        s.box(221 - i, 221 - i, 230, 232, 57 - i, 57, stone)

    # --- pillar (5x5) + roof slab (9x9) overhang --------------------------------------------------
    s.box(254, 258, 252, 256, 48, 57, stone)
    s.box(252, 260, 250, 258, 46, 47, roof)

    # --- enclosed 7x7x5 room (interior 5x5x3 air, no openings) ------------------------------
    s.hollow_box(230, 236, 270, 276, 53, 57, wood)

    # --- floating 3x3x1 slab (EXPECTED floating) + diagonal-only contact (EXPECTED floating) ---
    s.box(270, 272, 230, 232, 44, 44, flt)
    s.point(288, 230, 57, stone)                               # 1-voxel post on the ground
    s.point(289, 230, 56, diag)                                # shares only an EDGE with the post

    # --- arena gate tests: A clean, B ornament leak, C 3-thick ------------------------------
    def arch(y0, y1):
        s.box(300, 301, y0, y1, 50, 57, stone)
        s.box(307, 308, y0, y1, 50, 57, stone)
        s.box(300, 308, y0, y1, 48, 49, stone)
    arch(270, 270); s.box(302, 306, 270, 270, 50, 57, gate)    # A: 5 x 8 = 40 voxels
    arch(280, 280); s.box(302, 306, 280, 280, 50, 57, gate)    # B: 40 + ornament
    s.point(304, 279, 57, gate)                                # B: same-colour pot touching gate
    arch(288, 290); s.box(302, 306, 288, 290, 50, 57, gate)    # C: 3 thick = 120 voxels

    # --- movement course: ledges of 1, 2, 3 voxels --------------------------------------------
    for k, x0 in enumerate((300, 308, 316)):
        h = k + 1
        s.box(x0, x0 + 4, 300, 306, GROUND - h, GROUND - 1, stone)

    # --- crouch tunnels: clearance 3 (y 210..214) and 2 (y 218..222), x 330..345 --------------
    for (y0, clear) in ((210, 3), (218, 2)):
        roof_lo = GROUND - clear - 1                           # first solid z above the air gap
        s.box(330, 345, y0, y0, roof_lo - 1, GROUND - 1, stone)          # wall
        s.box(330, 345, y0 + 4, y0 + 4, roof_lo - 1, GROUND - 1, stone)  # wall
        s.box(330, 345, y0, y0 + 4, roof_lo - 1, roof_lo, stone)         # 2-thick roof

    # --- drop towers: 10 (stairs along x) and 20 (stairs along y) -----------------------------
    for i in range(10):
        s.box(250 + i, 250 + i, 300, 302, 57 - i, 57, wood)
    s.box(260, 262, 300, 302, 48, 57, wood)                    # platform top z 48 -> 10 drop
    for i in range(20):
        s.box(330, 332, 240 + i, 240 + i, 57 - i, 57, wood)
    s.box(330, 332, 260, 262, 38, 57, wood)                    # platform top z 38 -> 20 drop

    # --- colour swatches (2x2x3 columns) ------------------------------------------------------
    for i, mid in enumerate(sw_ids):
        s.box(240 + 4 * i, 241 + 4 * i, 200, 201, 55, 57, mid)

    # --- sky spire reaching z = 0 (tests the z == 0 surface rule) ----------------------------
    s.box(340, 342, 300, 302, 0, 57, stone)

    # --- edge islet touching x = 0 (edge faces count as solid in the file rule) ---------------
    s.box(0, 3, 250, 253, 55, 62, rock)

    s.markers = {
        'expect_floating': {'float_slab': ((270, 272), (230, 232), (44, 44)),
                            'diagonal_contact': ((289, 289), (230, 230), (56, 56))},
        'gates': [
            {'name': 'gate_A_clean', 'seed': (304, 270, 53), 'expect_blocks': 40},
            {'name': 'gate_B_ornament_leak', 'seed': (304, 280, 53), 'expect_blocks': 41},
            {'name': 'gate_C_three_thick', 'seed': (304, 288, 53), 'expect_blocks': 40,
             'expect_failure': True},   # hidden middle layer stops the fill -> gate never opens
        ],
        'spawns_blue': [(x, y, GROUND) for x in (170, 173, 176) for y in (300, 303, 306)],
        'spawns_green': [(x, y, GROUND) for x in (340, 343, 346) for y in (270, 273, 276)],
        'entities': {0: (180, 212, 46),        # BLUE_FLAG on the top terrace
                     1: (261, 301, 48),        # GREEN_FLAG on the 10-drop tower platform
                     2: (178, 312, GROUND),    # BLUE_BASE
                     3: (344, 284, GROUND)},   # GREEN_BASE
        'crop': (150, 185, 360, 325),
        'gate_rgb': GATE_RGB,
        'gate_material': 'gate',
    }
    return s


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'out/diagnostic'
    from aosmap.pipeline import run_diagnostic   # noqa: E402
    run_diagnostic(build, out)
