"""Non-deterministic vegetation: bloom trees, bushes, flower patches, giant mushrooms, bloom lanterns.
Positions are chosen on the west half and mirrored; each mirrored partner is a *different* random plant of the same size class."""
import math
import numpy as np
from geo import shade, mix, clamp8
import builds as B

GREENS = [(104, 176, 70), (146, 198, 74), (74, 146, 74), (78, 160, 122), (124, 186, 96)]
BLOSSOM = [(238, 152, 178), (246, 184, 124), (190, 154, 222), (242, 228, 208), (236, 124, 110)]
BARK = [(132, 90, 58), (112, 80, 56), (150, 108, 70), (124, 96, 82)]


def can_place(W, x, y, r, keep_mask, slope=2):
    if x - r < 2 or x + r > 509 or y - r < 2 or y + r > 509:
        return False
    if keep_mask[x - r:x + r + 1, y - r:y + r + 1].any():
        return False
    h = W.H[x - r:x + r + 1, y - r:y + r + 1]
    if (h >= 61).any():
        return False
    if int(h.max()) - int(h.min()) > slope:
        return False
    # no overhead structure
    if W.column_top(x, y, 0) < int(W.H[x, y]):
        return False
    return True


def bloom_tree(W, x, y, rng, size, glow_ok=True):
    g = int(W.H[x, y])
    blossom = rng.random() < 0.3
    base = (BLOSSOM if blossom else GREENS)[rng.integers(5)]
    base = clamp8(np.array(base) * rng.uniform(0.92, 1.06))
    alt = (GREENS if not blossom else BLOSSOM)[rng.integers(5)]
    bark = BARK[rng.integers(len(BARK))]
    th = int(size * rng.uniform(0.45, 0.6))
    cr = size * rng.uniform(0.32, 0.42)
    cr = max(cr, 3.0)
    lean = rng.uniform(-0.15, 0.15, 2)
    tr = 1.0 if size < 14 else 1.6
    top = g - th
    for z in range(top - int(cr * 0.5), g):
        t = g - z
        cx = x + lean[0] * t; cy = y + lean[1] * t
        r = tr * (1.5 if z >= g - 2 else 1.0)
        B.cyl(W, cx, cy, r, z, z, bark if (z % 3) else shade(bark, 0.88))
    ccx = x + lean[0] * th; ccy = y + lean[1] * th
    ccz = top - cr * 0.55
    seed = int(rng.integers(1 << 30))
    details = list(rng.choice(['fruit', 'flowers', 'vines', 'roots', 'band', 'shrooms', 'nest', 'sublobe',
                               'glowbulb', 'litter', 'twotone'], 3, replace=False))
    if not glow_ok and 'glowbulb' in details:
        details[details.index('glowbulb')] = 'litter'
    two = 'twotone' in details

    def lobe(cx, cy, cz, rx, rz, tint):
        ztop_l = cz - rz

        def cf(xs, ys, zs, d):
            t = np.clip((zs - ztop_l) / (2 * rz), 0, 1)[:, None]
            c = np.array(tint, float)[None, :]
            lt = np.minimum(c * 1.12, 255); dk = c * 0.78
            out = lt * (1 - t) + dk * t
            if 'fruit' in details or 'flowers' in details:
                hs = np.array([B.h32(a, b, cc, seed) for a, b, cc in zip(xs, ys, zs)])
                outer = d > 0.6
                if 'fruit' in details:
                    m = (hs % 13 == 0) & outer
                    out[m] = (226, 72, 64) if not blossom else (250, 210, 90)
                if 'flowers' in details:
                    m = (hs % 11 == 1) & outer
                    out[m] = (250, 240, 226)
            return np.clip(out, 0, 255).astype(np.uint8)
        W.ellipsoid(cx, cy, cz, rx, rx, rz, cf)

    lobe(ccx, ccy, ccz, cr, cr * 0.8, base)
    nl = int(rng.integers(2, 4))
    for k in range(nl):
        a = rng.uniform(0, 2 * math.pi)
        rr = cr * rng.uniform(0.5, 0.72)
        off = cr * rng.uniform(0.55, 0.8)
        tint = mix(base, alt, 0.35) if two and k % 2 == 0 else clamp8(np.array(base) * rng.uniform(0.94, 1.05))
        lobe(ccx + off * math.cos(a), ccy + off * math.sin(a), ccz + rng.uniform(-0.3, 0.5) * cr * 0.6, rr, rr * 0.82, tint)
    if 'sublobe' in details:
        a = rng.uniform(0, 2 * math.pi)
        bx, by = ccx + cr * 0.9 * math.cos(a), ccy + cr * 0.9 * math.sin(a)
        bz = top + 1
        # branch from trunk to sublobe
        n = 6
        for i in range(n + 1):
            t = i / n
            B.cyl(W, x + lean[0] * (g - bz) * (1 - t) + (bx - x) * t * 0.8, y + lean[1] * (g - bz) * (1 - t) + (by - y) * t * 0.8,
                  0.8, int(bz - t * 2), int(bz - t * 2), bark)
        lobe(x + (bx - x) * 0.85, y + (by - y) * 0.85, bz - 4, cr * 0.45, cr * 0.4, clamp8(np.array(base) * 0.95))
    if 'vines' in details:
        for k in range(int(rng.integers(4, 8))):
            a = rng.uniform(0, 2 * math.pi); r = cr * rng.uniform(0.5, 0.85)
            vx, vy = int(round(ccx + r * math.cos(a))), int(round(ccy + r * math.sin(a)))
            col = W.S[vx, vy, :]
            zs = np.nonzero(col[:g])[0]
            if len(zs) == 0:
                continue
            zb = zs.max()  # lowest canopy voxel in this column
            if zb >= g - 4:
                continue
            ln = int(rng.integers(2, 5))
            for z in range(zb + 1, min(zb + 1 + ln, g - 3)):
                W.set(vx, vy, z, (92, 150, 70))
            if rng.random() < 0.5:
                W.set(vx, vy, min(zb + ln, g - 4), (238, 170, 196))
    if 'roots' in details:
        for a in range(0, 360, 90):
            ra = math.radians(a + rng.uniform(-20, 20))
            for i in range(1, 4):
                rx_, ry_ = int(round(x + (tr + i) * math.cos(ra))), int(round(y + (tr + i) * math.sin(ra)))
                W.set(rx_, ry_, g - 1, bark)
                if i == 1:
                    W.set(rx_, ry_, g - 2, bark)
    if 'band' in details:
        zb = g - int(th * 0.4)
        B.cyl(W, x + lean[0] * (g - zb), y + lean[1] * (g - zb), tr + 0.6, zb, zb, (196, 176, 120))
    if 'shrooms' in details:
        for k in range(3):
            a = rng.uniform(0, 6.28); r = tr + rng.uniform(1.5, 3)
            sx, sy = int(round(x + r * math.cos(a))), int(round(y + r * math.sin(a)))
            W.set(sx, sy, g - 1, (236, 226, 200)); W.set(sx, sy, g - 2, (214, 96, 76))
    if 'nest' in details:
        nz = int(ccz + cr * 0.2)
        a = rng.uniform(0, 6.28)
        nx, ny = int(round(ccx + (cr - 0.5) * math.cos(a))), int(round(ccy + (cr - 0.5) * math.sin(a)))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                W.set(nx + dx, ny + dy, nz, (150, 112, 70))
        W.set(nx, ny, nz - 1, (200, 224, 236))
    if 'glowbulb' in details:
        a = rng.uniform(0, 6.28)
        r = cr * 0.6
        vx, vy = int(round(ccx + r * math.cos(a))), int(round(ccy + r * math.sin(a)))
        zs = np.nonzero(W.S[vx, vy, :g])[0]
        if len(zs) and zs.max() < g - 4:
            zb = zs.max()
            W.set(vx, vy, zb + 1, (92, 150, 70))
            W.set(vx, vy, zb + 2, B.GLOW_YEL); W.glow.append((vx, vy, zb + 2, B.GLOW_YEL))
    if 'litter' in details:
        for dx in range(-int(cr), int(cr) + 1):
            for dy in range(-int(cr), int(cr) + 1):
                if dx * dx + dy * dy <= cr * cr and B.h32(x + dx, y + dy, seed) % 3 == 0:
                    gx, gy = x + dx, y + dy
                    if 0 <= gx < 512 and 0 <= gy < 512:
                        gz = int(W.H[gx, gy])
                        if W.S[gx, gy, gz] and not W.S[gx, gy, gz - 1] and gz < 61:
                            W.C[gx, gy, gz] = clamp8(mix(W.C[gx, gy, gz], shade(base, 0.9), 0.5))
    return True


def bush(W, x, y, rng):
    g = int(W.H[x, y])
    base = GREENS[rng.integers(5)]
    berry = rng.random() < 0.4
    bc = [(226, 80, 90), (244, 200, 90), (190, 150, 230)][rng.integers(3)]
    seed = int(rng.integers(1 << 30))
    n = int(rng.integers(2, 4))
    for k in range(n):
        r = rng.uniform(1.8, 3.2)
        ox = (k - (n - 1) / 2) * r * 1.1
        a = rng.uniform(-0.6, 0.6)
        cx, cy = x + ox * math.cos(a), y + ox * math.sin(a)

        def cf(xs, ys, zs, d, r=r):
            t = np.clip((zs - (g - 2 * r)) / (2 * r), 0, 1)[:, None]
            c = np.array(base, float)[None, :]
            out = c * 1.1 * (1 - t) + c * 0.8 * t
            if berry:
                hs = np.array([B.h32(a, b, cc, seed) for a, b, cc in zip(xs, ys, zs)])
                out[(hs % 9 == 0) & (d > 0.5)] = bc
            return np.clip(out, 0, 255).astype(np.uint8)
        W.ellipsoid(cx, cy, g - r * 0.7, r, r, r * 0.85, cf)


def flower_patch(W, x, y, rng, r):
    pal = [(244, 120, 120), (250, 214, 96), (246, 240, 228), (196, 150, 230), (250, 160, 90)]
    c1 = pal[rng.integers(5)]; c2 = pal[rng.integers(5)]
    for k in range(int(r * r * 0.5)):
        a = rng.uniform(0, 6.28); d = r * math.sqrt(rng.random())
        fx, fy = int(round(x + d * math.cos(a))), int(round(y + d * math.sin(a)))
        if not (2 <= fx < 510 and 2 <= fy < 510):
            continue
        if W.keep[fx, fy] & 2:
            continue
        g = int(W.H[fx, fy])
        if g >= 60 or W.S[fx, fy, g - 1] or W.column_top(fx, fy, 0) < g:
            continue
        W.set(fx, fy, g - 1, (96, 160, 66))
        W.set(fx, fy, g - 2, c1 if rng.random() < 0.65 else c2)


def plant_all(W, rng, spec):
    keep = (W.keep != 0)
    # gameplay keep-outs: spawn squares, tower zones, path lanes, platform underside handled by caps
    k = keep.copy()
    sx0, sx1, sy0, sy1 = spec['spawn_square']
    for (a, b) in ((sx0, sx1), (511 - sx1, 511 - sx0)):
        k[a - 3:b + 4, sy0 - 3:sy1 + 4] = True
    tx0, tx1, ty0, ty1 = spec['tower_zone']
    for (a, b) in ((tx0, tx1), (511 - tx1, 511 - tx0)):
        k[a:b + 1, ty0 - 4:ty1 + 5] = True
    k[(W.H >= 61)] = True
    occupied = np.zeros((512, 512), bool)

    def try_place(x, y, r, slope=2):
        mx = 511 - x
        if not (can_place(W, x, y, r, k | occupied, slope) and can_place(W, mx, y, r, k | occupied, slope)):
            return False
        return True

    def occupy(x, y, r):
        occupied[max(0, x - r):x + r + 1, max(0, y - r):y + r + 1] = True
        mx = 511 - x
        occupied[max(0, mx - r):mx + r + 1, max(0, y - r):y + r + 1] = True

    counts = {'trees': 0, 'mushrooms': 0, 'bushes': 0, 'lanterns': 0, 'flower_patches': 0}
    # grove density field
    from noise import fbm
    dens = 0.5 + 0.5 * fbm((256, 512), 34, int(rng.integers(1 << 20)))

    # 1. under-platform mushroom grove (cap tops kept at z >= 40 under the platform footprint)
    tries = 0
    while counts['mushrooms'] < 7 and tries < 600:
        tries += 1
        x = int(rng.integers(214, 236)); y = int(rng.integers(206, 306))
        if 230 <= y <= 281 and x >= 228:
            continue
        r = 7
        if not try_place(x, y, 3, slope=1):
            continue
        under = 236 <= y <= 276
        for xx in (x, 511 - x):
            B.giant_mushroom(W, xx, y, int(rng.integers(12, 19)), float(rng.uniform(5, 8)), rng,
                             cap_top_min=40 if under else 30, glow=rng.random() < 0.3)
        occupy(x, y, r)
        counts['mushrooms'] += 2
    # 2. giant mushroom clusters around the centre and flanks
    tries = 0
    target = 30
    placed = 0
    while placed < target and tries < 4000:
        tries += 1
        x = int(rng.integers(20, 250)); y = int(rng.integers(30, 482))
        if rng.random() > dens[x, y] ** 2:
            continue
        r = 8
        if not try_place(x, y, 4, slope=1):
            continue
        for xx in (x, 511 - x):
            B.giant_mushroom(W, xx, y, int(rng.integers(10, 25)), float(rng.uniform(5, 10)), rng,
                             cap_top_min=8, glow=rng.random() < 0.25)
        occupy(x, y, r)
        placed += 1
    counts['mushrooms'] += 2 * placed
    # 3. bloom trees in groves
    tries = 0; placed = 0
    while placed < 112 and tries < 20000:
        tries += 1
        x = int(rng.integers(8, 252)); y = int(rng.integers(20, 492))
        if rng.random() > max(0.0, dens[x, y] - 0.18) ** 1.4 * 1.5:
            continue
        size = float(rng.uniform(10, 22))
        r = int(size * 0.32)
        if not try_place(x, y, 2, slope=2):
            continue
        if occupied[max(0, x - r):x + r + 1, max(0, y - r):y + r + 1].any():
            continue
        # keep canopies out of the platform volume: only allow near the platform if small
        if 196 <= x and 228 <= y <= 284:
            continue
        glow_ok = rng.random() < 0.5
        for xx in (x, 511 - x):
            bloom_tree(W, xx, y, rng, size * rng.uniform(0.9, 1.1), glow_ok)
        occupy(x, y, max(3, r))
        placed += 1
    counts['trees'] = 2 * placed
    # 4. spawn-cover trees on the plateau rim (front kept open: gaps >= 10)
    for (x, y) in ((140, 206), (128, 214), (140, 306), (128, 298)):
        for xx in (x, 511 - x):
            bloom_tree(W, xx, y, rng, float(rng.uniform(22, 26)))
    counts['trees'] += 8
    # 5. bushes
    tries = 0; placed = 0
    while placed < 120 and tries < 12000:
        tries += 1
        x = int(rng.integers(8, 252)); y = int(rng.integers(20, 492))
        if not try_place(x, y, 3, slope=2):
            continue
        for xx in (x, 511 - x):
            bush(W, xx, y, rng)
        occupy(x, y, 2)
        placed += 1
    counts['bushes'] = 2 * placed
    # 6. bloom lanterns along path edges (glow)
    pm = (W.keep & 2) != 0
    tries = 0; placed = 0
    while placed < 34 and tries < 8000:
        tries += 1
        x = int(rng.integers(30, 250)); y = int(rng.integers(40, 470))
        if pm[x, y] or not pm[max(0, x - 3):x + 4, max(0, y - 3):y + 4].any():
            continue
        if not try_place(x, y, 1, slope=1):
            continue
        for xx in (x, 511 - x):
            B.bloom_lantern(W, xx, y, rng)
        occupy(x, y, 4)
        placed += 1
    counts['lanterns'] = 2 * placed
    # 7. flower patches (not mirrored exactly — tiny, cosmetic)
    for i in range(70):
        x = int(rng.integers(10, 502)); y = int(rng.integers(24, 488))
        if keep[x, y] or k[x, y]:
            continue
        flower_patch(W, x, y, rng, float(rng.uniform(3, 6)))
        counts['flower_patches'] += 1
    return counts
