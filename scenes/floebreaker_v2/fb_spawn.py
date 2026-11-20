"""Floebreaker v2 spawn compounds (docs/craft_standard.md §3, AGENTS.md §4 Babel spawn rules).

Blue side only; the build mirrors it. Inside the stock +-20 square (x 98-138, y 236-276) nothing stands taller than
the terrain mounds. Around it:
  * a broken cut-block snow wall, sled racks, crate and drum stacks within 1-7 voxels of the square on the N, S and W
    sides, gaps >= 6 at least every 12 voxels (exits on all four sides; cover within 8 for the spawn spots);
  * the expedition lodge behind the square (backdrop 20-40 behind it, door facing the spawn);
  * a glacier arch over the front (x 140-150): legs outside the tower corridor, a lintel whose underside stays
    >= 10 above the ground (players walk and build under it), thick enough to cut the platform's sightlines.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from fb_core import MAT
import fb_struct as S

SQ = (98, 138, 236, 276)


def arch_gate(W, H, xa=139, xb=151, ya=220, yb=292, leg=11, clear=10, seed=5):
    """Sculpted glacier arch: rounded cross-section (narrower at the crown and the underside), noise-warped faces with
    bites, snow lying on top and draping 1-2 voxels down the faces, broken crest, icicles where the opening is tall.
    The underside stays >= `clear` above the ground across the whole opening."""
    rng = np.random.default_rng(seed)
    n = yb - ya + 1
    wob_l = ndi.gaussian_filter(rng.standard_normal(n), 3.0) * 1.8
    wob_r = ndi.gaussian_filter(rng.standard_normal(n), 3.0) * 1.8
    xc0 = (xa + xb) / 2.0
    hw0 = (xb - xa) / 2.0
    bites = [(int(rng.integers(xa - 1, xb + 2)), int(rng.integers(ya, yb + 1)), int(rng.integers(30, 56)),
              float(rng.uniform(1.5, 3.4))) for _ in range(70)]
    for i, y in enumerate(range(ya, yb + 1)):
        tt = (i - leg) / max(n - 2 * leg - 1, 1)
        in_open = leg <= i <= n - 1 - leg
        s_ = np.sin(np.pi * np.clip(tt, 0, 1))
        g = int(H[int(xc0), y])
        if in_open:
            bottom = g - clear - int(round(3 * s_))
            top = bottom - (8 + int(round(5 * (1 - s_))))
        else:
            dleg = min(i, n - 1 - i)
            bottom = g
            top = g - clear - 12 - int(round(3 * (leg - dleg) / leg))
        xcen = xc0 + (wob_r[i] - wob_l[i]) / 2
        hw = hw0 + (wob_l[i] + wob_r[i]) / 2
        for z in range(top, bottom + 1 if in_open else g):
            # round the cross-section: narrower near the crown and (in the opening) near the underside
            u = (z - top) / max((bottom - top) if in_open else (g - top), 1)
            shrink = 2.2 * (1 - np.sin(np.pi * np.clip(u, 0, 1)) ** 0.6) if in_open else 2.2 * max(0.0, 1 - u * 4)
            half = hw - shrink
            for x in range(max(int(xcen - hw - 1), 139), int(xcen + hw + 2)):        # never over the spawn square
                if abs(x - xcen) <= half:
                    W.m[x, y, z] = MAT['blueice']
        if in_open:
            for x in range(int(xcen - hw - 2), int(xcen + hw + 3)):
                gx = int(H[x, y])
                W.m[x, y, bottom + 1:gx] = 0
    for bx, by, bz, br in bites:                                      # weathering bites on the faces
        for x in range(int(bx - br) - 1, int(bx + br) + 2):
            for y in range(int(by - br) - 1, int(by + br) + 2):
                for z in range(int(bz - br) - 1, int(bz + br) + 2):
                    if (x - bx) ** 2 + (y - by) ** 2 + (z - bz) ** 2 <= br * br and 0 <= z < 62:
                        if W.m[x, y, z] == MAT['blueice'] and z < int(H[x, y]) - clear:
                            W.m[x, y, z] = 0
    # snow on top, draping down the faces; crest on lips; icicles under the outer lintel edges
    for x in range(xa - 4, xb + 5):
        for y in range(ya, yb + 1):
            col = W.m[x, y, :62]
            if not (col == MAT['blueice']).any():
                continue
            zt = int(np.argmax(col == MAT['blueice']))
            if W.m[x, y, zt - 1] == 0 if zt > 0 else True:
                W.m[x, y, zt] = MAT['crest'] if (x * 7 + y * 3) % 11 == 0 else MAT['snow']
                if (x + y) % 3:
                    if W.m[x, y, zt + 1] == MAT['blueice']:
                        W.m[x, y, zt + 1] = MAT['snow']
            g = int(H[x, y])
            under = [z for z in range(zt, g) if W.m[x, y, z] == MAT['blueice'] and W.m[x, y, z + 1] == 0]
            for z in under[:1]:
                if g - z - 1 >= 12 and (x + 2 * y) % 3 == 0:
                    W.m[x, y, z + 1:z + 1 + int(1 + (x + y) % 3)] = MAT['berg_c']
    W.keep[xa - 6:xb + 7, ya - 2:yb + 3] = True
    W.structures.append({'name': 'arch_gate_blue', 'box': [xa - 3, xb + 3, ya, yb], 'role': 'ruin'})
    return (xa - 3, xb + 3, ya, yb)


def camp_ring(W, H):
    x0, x1, y0, y1 = SQ
    # north and south windbreak walls with exits, 2-6 voxels outside the square
    for yy in (y0 - 4, y1 + 3):
        x = x0 + 2
        segs = [(x0 + 2, x0 + 9), (x0 + 16, x0 + 24), (x0 + 31, x0 + 38)]
        for a, b in segs:
            S.snow_wall(W, H, a, yy, b, yy, h=3)
    # west windbreak with two exits toward the lodge
    for a, b in ((y0 + 2, y0 + 10), (y0 + 17, y0 + 24), (y0 + 31, y0 + 38)):
        S.snow_wall(W, H, x0 - 5, a, x0 - 5, b, h=3)
    # gear: sled racks, crate and drum stacks at the corners and along the sides
    S.sled_rack(W, H, x0 + 10, y0 - 8)
    S.sled_rack(W, H, x0 + 22, y1 + 7)
    S.crate_stack(W, H, x0 - 8, y0 - 7, 5)
    S.drum_stack(W, H, x0 - 8, y1 + 5)
    S.crate_stack(W, H, x1 - 4, y0 - 9, 4)
    S.drum_stack(W, H, x1 - 3, y1 + 6)
    S.woodpile(W, H, x0 - 9, y0 + 12, 6, 'y')
    S.woodpile(W, H, x0 - 9, y0 + 26, 6, 'y')
    S.flagpole(W, H, x0 - 3, y0 - 6, 14, 'flag_b')


def spawn_compound(W, H):
    camp_ring(W, H)
    S.lodge(W, H, 66, 232, name='lodge_blue')
    return arch_gate(W, H)
