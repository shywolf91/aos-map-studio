"""Detail pass: ice caves, boulder fields, frozen ponds, penguin colonies, flag lines, crystal clusters.
Keeps the tower corridor (|y-256| < 40 between the bases) and the spawn squares free of anything but 1-high litter."""
from __future__ import annotations

import numpy as np

from fb_core import MAT


def detail_blocked(x, y, pad=0):
    """Whale and ship ground (the centre-line pieces are built first and own their pads)."""
    return (226 - pad < x < 286 + pad and 36 - pad < y < 192 + pad) or (232 - pad < x < 280 + pad and 300 - pad < y < 440 + pad)


def keep_out(x, y, pad=0):
    if detail_blocked(x, y, pad):
        return True
    if 140 < x < 372:                                      # tower corridor (+ a margin): litter only
        return abs(y - 256) < 30 + pad
    return abs(y - 256) < 40 + pad and 84 < x < 428        # spawn grounds


def boulder(W, H, cx, cy, r, h, top='snow', body='ice'):
    for x in range(cx - r, cx + r + 1):
        for y in range(cy - r, cy + r + 1):
            dd = np.hypot(x - cx, y - cy) / r
            if dd > 1 or not (0 <= x < 512 and 0 <= y < 512):
                continue
            g = int(H[x, y])
            if g >= 62:
                continue
            t = g - int(round(h * np.sqrt(1 - dd * dd)))
            if t < g:
                W.m[x, y, t:g] = MAT[body]
                W.m[x, y, t:t + 2] = MAT[top]


def boulder_fields(W, H, calm, d, n=26, minsep=12):
    rng = W.lrng
    placed = []
    tries = 0
    while len(placed) < n and tries < 4000:
        tries += 1
        x = int(rng.integers(100, 246)); y = int(rng.integers(120, 400))
        r = int(rng.integers(3, 6)); h = int(rng.integers(3, 6))
        if keep_out(x, y, 6) or calm[x, y] > 0.08 or d[x, y] < 10 or H[x, y] > 60:
            continue
        if any(np.hypot(x - a, y - b) < minsep + r + c for a, b, c in placed):
            continue
        placed.append((x, y, r))
        boulder(W, H, x, y, r, h)
        for k in range(int(rng.integers(1, 3))):          # companions in a loose grove
            ox, oy = int(rng.integers(-9, 10)), int(rng.integers(-9, 10))
            rr = int(rng.integers(2, 4))
            if not keep_out(x + ox, y + oy, 4) and H[x + ox, y + oy] <= 60 and x + ox < 250:
                boulder(W, H, x + ox, y + oy, rr, 2)
    return placed


def pond(W, H, cx, cy, rx, ry):
    for x in range(cx - rx - 1, cx + rx + 2):
        for y in range(cy - ry - 1, cy + ry + 2):
            dd = np.hypot((x - cx) / rx, (y - cy) / ry)
            if dd <= 1.0 and H[x, y] < 62:
                g = int(H[x, y])
                W.m[x, y, g:g + 3] = MAT['blueice']
            elif dd <= 1.15 and H[x, y] < 62:
                g = int(H[x, y])
                W.m[x, y, g] = MAT['ice']


def penguin(W, H, x, y, face=0):
    g = int(H[x, y])
    if g >= 61 or not (2 <= x < 510):
        return
    W.box(x, x + 1, y, y + 1, g - 3, g - 1, 'rubber')
    W.box(x, x + 1, y, y + 1, g - 4, g - 4, 'rubber')
    dx, dy = ((2, 0), (-1, 0), (0, 2), (0, -1))[face % 4]
    for t in ((0, 0), (1, 0), (0, 1), (1, 1)):
        px, py = x + t[0], y + t[1]
        # white belly on the face side
    if face % 4 == 0:
        W.box(x + 1, x + 1, y, y + 1, g - 3, g - 1, 'white'); W.pt(x + 2, y, g - 3, 'orange')
    elif face % 4 == 1:
        W.box(x, x, y, y + 1, g - 3, g - 1, 'white'); W.pt(x - 1, y, g - 3, 'orange')
    elif face % 4 == 2:
        W.box(x, x + 1, y + 1, y + 1, g - 3, g - 1, 'white'); W.pt(x, y + 2, g - 3, 'orange')
    else:
        W.box(x, x + 1, y, y, g - 3, g - 1, 'white'); W.pt(x, y - 1, g - 3, 'orange')


def penguin_colony(W, H, cx, cy, n=9):
    rng = W.drng
    for i in range(n):
        ox, oy = int(rng.normal(0, 5)), int(rng.normal(0, 5))
        penguin(W, H, cx + ox, cy + oy, int(rng.integers(0, 4)))


def flag_line(W, H, pts, step=12):
    for (ax, ay), (bx, by) in zip(pts[:-1], pts[1:]):
        n = int(np.hypot(bx - ax, by - ay))
        for t in range(0, n, step):
            x = int(ax + (bx - ax) * t / max(n, 1)); y = int(ay + (by - ay) * t / max(n, 1))
            g = int(H[x, y])
            if g >= 61 or keep_out(x, y):
                continue
            W.box(x, x, y, y, g - 6, g - 1, 'dwood')
            W.box(x + 1, x + 2, y, y, g - 6, g - 5, 'orange' if (t // step) % 2 == 0 else 'canvas_b')


def crystal_spikes(W, H, cx, cy, n=5, hmax=6, mat='lamp_c'):
    """Glow crystal cluster growing from the ice: 1-voxel spikes on a 2x2 root (all face-connected)."""
    rng = W.lrng
    g = int(H[cx, cy])
    W.box(cx, cx + 1, cy, cy + 1, g - 2, g - 1, 'blueice')
    for i in range(n):
        ox, oy = int(rng.integers(0, 2)), int(rng.integers(0, 2))
        hh = int(rng.integers(3, hmax + 1))
        W.box(cx + ox, cx + ox, cy + oy, cy + oy, g - hh, g - 3, 'berg_c')
        W.pt(cx + ox, cy + oy, g - hh - 1, mat)


def ice_cave(W, H, x0, x1, cy, hw=3, floor=59, roof_min=50, gallery_at=None, gallery_len=14):
    """Tunnel through a hill along x at row cy (width 2*hw+1, up to 8 high), with a side gallery crossing it."""
    def carve_row(x, y0, y1):
        g = int(H[x, cy if True else 0])
        for y in range(y0, y1 + 1):
            gy = int(H[x, y])
            zc = min(max(gy + 2, roof_min), 55)
            if zc < floor:
                W.m[x, y, zc:floor] = 0
    for x in range(x0, x1 + 1):
        carve_row(x, cy - hw, cy + hw)
    # floor of the tunnel: make sure the surface under the carve is ice at z = floor
    if gallery_at is not None:
        gx = gallery_at
        for y in range(cy - gallery_len, cy + gallery_len + 1):
            for x in range(gx - 2, gx + 3):
                gy = int(H[x, y])
                zc = min(max(gy + 2, roof_min), 55)
                if zc < floor:
                    W.m[x, y, zc:floor] = 0
    # glow crystals on the ceiling, every 7 voxels along both walls
    for x in range(x0 + 3, x1 - 2, 7):
        for y in (cy - hw, cy + hw):
            gy = int(H[x, y]); zc = min(max(gy + 2, roof_min), 55)
            if zc < floor - 2 and W.m[x, y, zc - 1] != 0:
                W.pt(x, y, zc, 'lamp_c')
                W.pt(x, y, zc + 1, 'lamp_c')


def mound(W, H, cx, cy, rx, ry, h, body='ice', top='snow'):
    """Elongated ice mound (dome), every column grounded."""
    for x in range(int(cx - rx), int(cx + rx) + 1):
        for y in range(int(cy - ry), int(cy + ry) + 1):
            dd = np.hypot((x - cx) / rx, (y - cy) / ry)
            if dd > 1 or not (0 <= x < 512 and 0 <= y < 512):
                continue
            g = int(H[x, y])
            if g >= 62:
                continue
            t = g - int(round(h * np.sqrt(1 - dd * dd)))
            if t < g:
                W.m[x, y, t:g] = MAT[body]
                W.m[x, y, t:t + 2] = MAT[top]
                H[x, y] = t


def cone(W, H, cx, cy, rx, ry, h, body='blueice', top='snow'):
    """Walkable cone ridge (slope <= ~1 per voxel when h <= min(rx, ry)*0.9), every column grounded."""
    for x in range(int(cx - rx), int(cx + rx) + 1):
        for y in range(int(cy - ry), int(cy + ry) + 1):
            dd = np.hypot((x - cx) / rx, (y - cy) / ry)
            if dd >= 1 or not (0 <= x < 512 and 0 <= y < 512):
                continue
            g = int(H[x, y])
            if g >= 62:
                continue
            t = g - int(round(h * (1 - dd)))
            if t < g:
                W.m[x, y, t:g] = MAT[body]
                W.m[x, y, t] = MAT[top] if dd < 0.5 else MAT[body]
                H[x, y] = t


RIDGES = []          # (cx, cy, rx, ry, h) optional cone ridges (tuning harness only)
FINS = [(142, 206, 262, 5, 29, 8), (152, 250, 308, 5, 29, -8)]   # (cx, y0, y1, thick, crest z, lean)


def skiff(W, H, x0, y0, length=10, width=5):
    """Stranded wooden skiff lying on the ice (hollow, open top), ~3 tall, with a lantern on the bow post."""
    zf = int(H[x0:x0 + width, y0:y0 + length].max())
    for y in range(y0, y0 + length):
        t = (y - y0) / (length - 1)
        hw = max(1, int(round((width / 2.0) * (1 - (2 * t - 1) ** 4))))
        cx = x0 + width // 2
        for x in range(cx - hw, cx + hw + 1):
            g = int(H[x, y])
            W.m[x, y, zf - 3:g] = MAT['dwood']
            edge = abs(x - cx) == hw or y in (y0, y0 + length - 1)
            if not edge:
                W.m[x, y, zf - 2:zf] = 0
                W.m[x, y, zf - 1] = 0
                W.m[x, y, zf] = MAT['plank']
    W.box(x0 + width // 2, x0 + width // 2, y0 + length - 1, y0 + length - 1, zf - 6, zf - 3, 'dwood')
    W.pt(x0 + width // 2, y0 + length - 1, zf - 7, 'lamp')


def ice_blocks(W, H, x0, y0, seed=0):
    """Tumbled ice blocks (cut for a camp), 3-5 stacked cubes, <= 7 tall."""
    rng = np.random.default_rng(seed)
    for i in range(5):
        ox, oy = int(rng.integers(0, 6)), int(rng.integers(0, 6))
        s = int(rng.integers(2, 4)); n = int(rng.integers(1, 3))
        g = int(H[x0 + ox:x0 + ox + s, y0 + oy:y0 + oy + s].max())
        W.box(x0 + ox, x0 + ox + s - 1, y0 + oy, y0 + oy + s - 1, g - s * n, g, 'blueice')
        W.box(x0 + ox, x0 + ox + s - 1, y0 + oy, y0 + oy + s - 1, g - s * n, g - s * n, 'snow')


def cache(W, H, x0, y0):
    """Supply cache: crate stack, drums and a canvas tarp lean-to (1 storey)."""
    g = int(H[x0:x0 + 8, y0:y0 + 6].max())
    W.box(x0, x0 + 2, y0, y0 + 2, g - 3, g, 'plank')
    W.box(x0 + 1, x0 + 2, y0 + 1, y0 + 2, g - 5, g - 4, 'dwood')
    W.box(x0 + 4, x0 + 5, y0, y0 + 1, g - 3, g, 'drum_r'); W.box(x0 + 4, x0 + 5, y0 + 3, y0 + 4, g - 3, g, 'drum_b')
    for k in range(4):
        W.box(x0 + 6 + (k // 2), x0 + 6 + (k // 2), y0 + 5 - k, y0 + 5 - k, g - 3 + (k // 2), g, 'canvas_o')
    W.pt(x0 + 1, y0 + 1, g - 6, 'lamp')


def front_dress(W, H):
    """Blue-side (x < 256) dressing of the spawn -> tower front and the strip under the platform, plus the rear
    backdrop. Low objects (<= 10 tall), gaps >= 8, nothing seals a route. Mirrored later by array copy."""
    # --- spawn cover: two staggered glacier fins (declared as a front exemption in build.json; see spec). The only
    #     tall objects in the front; everything else below is low dressing.
    import fb_props as P
    for i, (cx, y0, y1, th, zt, ln) in enumerate(FINS):
        P.fin_wall(W, H, cx, y0, y1, th, zt, ln, seed=100 + i)
    # --- front dressing (x >= 160): low boulders, ice blocks, skiff, cache
    for cx, cy, r, h in ((164, 244, 4, 7), (168, 270, 4, 8), (177, 250, 3, 5), (181, 273, 3, 6), (172, 258, 3, 4)):
        boulder(W, H, cx, cy, r, h)
    mound(W, H, 163, 247, 5, 3, 4)
    ice_blocks(W, H, 190, 240, 1)
    skiff(W, H, 183, 257, 10, 5)
    cache(W, H, 196, 264)
    mound(W, H, 163, 247, 5, 3, 4)
    # --- rear backdrop 20-40 behind the spawn square (x 58-78): broken ridge with exits
    for cy, ry, h in ((205, 9, 6), (224, 8, 7), (246, 7, 6), (268, 7, 7), (288, 8, 6), (309, 9, 7), (186, 8, 6),
                      (327, 8, 6)):
        mound(W, H, 68, cy, 9, ry, h)
    # --- strip under the platform (x 212-255): low boulders, ice blocks, a cache; ends x 206-211 stay prop-free
    for cx, cy, r, h in ((222, 247, 4, 6), (225, 266, 4, 7), (235, 254, 5, 8), (238, 266, 3, 5), (246, 245, 4, 6),
                         (250, 268, 4, 5), (230, 243, 3, 4), (243, 257, 3, 4), (216, 257, 3, 4)):
        boulder(W, H, cx, cy, r, h)
    ice_blocks(W, H, 226, 256, 7)
    cache(W, H, 240, 246)
    skiff(W, H, 214, 261, 9, 5)


def detail_pass(W, H, calm, d):
    rng = W.lrng
    boulder_fields(W, H, calm, d)
    # frozen ponds
    for px, py, rx, ry in ((112, 190, 12, 8), (112, 322, 12, 8), (206, 140, 10, 9), (206, 372, 10, 9)):
        pond(W, H, px, py, rx, ry)
    # ice caves through the rim glaciers + side gallery (two exits each side => cannot be sealed by one block line)
    for (cx, cy, hwid) in ((52, 150, 3), (66, 352, 3)):
        for xa, xb, gal in ((cx - 30, cx + 30, cx),):
            ice_cave(W, H, max(xa, 8), xb, cy, hwid, gallery_at=gal)
    # flag lines guiding from each camp to the tower corridor and along the flanks
    for pts in ([(150, 196), (150, 226)], [(150, 316), (150, 286)], [(100, 120), (150, 112), (200, 118)],
                [(100, 396), (150, 404), (200, 396)]):
        flag_line(W, H, pts)
    # glow crystal clusters at crevasse heads, among seracs and on the headlands
    for _ in range(40):
        x = int(rng.integers(40, 240)); y = int(rng.integers(60, 452))
        if keep_out(x, y, 4) or calm[x, y] > 0.05 or d[x, y] < 8 or H[x, y] > 60 or (x > 235 and 40 < y < 190):
            continue
        crystal_spikes(W, H, x, y, 5)


PENGUIN_SITES = ((92, 100), (70, 410), (170, 450), (190, 66))


def penguin_pass(W, H):
    """Penguin colonies (decor RNG: non-deterministic). Run after mirroring; boxes go to cosmetic_asymmetric_boxes."""
    boxes = []
    for cx, cy in PENGUIN_SITES:
        for xx in (cx, 512 - cx):
            if H[xx, cy] < 61:
                penguin_colony(W, H, xx, cy, 9)
                boxes.append((xx - 14, xx + 14, cy - 14, cy + 14))
    return boxes
