"""Frostbell Hollow vegetation art: real trees on the graybox stand-ins (same trunk column, canopy >= 4 above the
ground, inside the stand-in's height budget so nothing rises above z 7), the giant village spruce, holly bushes.

Owner rules: non-deterministic look (every species / size / palette / detail choice comes from the build's OS seed
`veg_seed`, saved in build.json), varied colours with smooth base->tip gradients, THREE random details per plant,
groves (each grove takes its palette from a slow field), every voxel face-connected (kit veg._connected prunes).
Placement is fixed by the graybox stand-ins so gameplay geometry stays checked; see fh_checks.collision_diff.
"""
from __future__ import annotations

import math

import numpy as np

from aosmap.kit import noise
from aosmap.kit.color import clamp8, mix, shade
from aosmap.kit.veg import _connected, palette_family

SNOW = (196, 200, 210)
SNOW_SHADE = (172, 180, 198)
WINTER_DETAILS = ('icicles', 'baubles', 'robin', 'pinecones', 'lantern', 'ribbon', 'frost tips', 'nest',
                  'mistletoe', 'birdhouse', 'squirrel', 'star')
# conifer greens: 8 close families from deep teal-green to olive (calm, never confetti)
CONIFER_FAMILIES = [
    palette_family([(34, 66, 52), (52, 92, 66), (78, 116, 78)], 6),
    palette_family([(30, 58, 58), (44, 82, 72), (66, 104, 86)], 6),
    palette_family([(40, 70, 46), (62, 96, 56), (92, 120, 66)], 6),
    palette_family([(36, 60, 64), (54, 86, 80), (82, 110, 92)], 6),
]
NATURAL_DETAILS = ('icicles', 'robin', 'pinecones', 'frost tips', 'nest', 'mistletoe', 'birdhouse', 'squirrel')
BIRCH_BARK = [(196, 192, 184), (206, 200, 188), (186, 182, 176)]
BARK = [(84, 62, 48), (92, 70, 52), (76, 58, 46), (100, 76, 58)]


def pick(rng, allow=WINTER_DETAILS, n=3):
    idx = rng.choice(len(allow), size=n, replace=False)
    return tuple(sorted(allow[i] for i in idx))


def _snowy(c, amt):
    return clamp8(mix(c, SNOW, amt))


def _decorate(cv, rng, x, y, g, details, pts, glow):
    """Three winter details, all attached by a face to the crown or trunk. Glow sources go to `glow`."""
    if not pts:
        return
    by_z = sorted(pts, key=lambda p: p[2])
    lowest = [p for p in by_z[::-1] if not cv.get(p[0], p[1], p[2] + 1)][:30]
    outer = [p for p in pts if sum(not cv.get(p[0] + dx, p[1] + dy, p[2]) for dx, dy in
                                   ((1, 0), (-1, 0), (0, 1), (0, -1))) >= 2]
    outer = outer or pts
    sel = [outer[int(i)] for i in rng.choice(len(outer), size=min(12, len(outer)), replace=False)]
    if 'icicles' in details:
        for (px, py, pz) in lowest[:8:2]:
            if not cv.get(px, py, pz + 1):
                cv.set(px, py, pz + 1, (176, 206, 222), 'icicle')
    if 'baubles' in details:
        cols = [(176, 52, 48), (196, 160, 70), (70, 96, 150), (200, 200, 206)]
        for k, (px, py, pz) in enumerate(sel[:6]):
            cv.set(px, py, pz, cols[k % len(cols)], 'ornament')
    if 'robin' in details:
        px, py, pz = by_z[len(by_z) // 3]
        if not cv.get(px, py, pz - 1):
            cv.set(px, py, pz - 1, (96, 70, 52), 'robin')
            if not cv.get(px, py, pz - 2):
                cv.set(px, py, pz - 2, (186, 82, 52), 'robin')
    if 'pinecones' in details:
        for (px, py, pz) in lowest[1:7:2]:
            if not cv.get(px, py, pz + 1):
                cv.set(px, py, pz + 1, (110, 80, 54), 'cone')
    if 'lantern' in details and lowest:
        px, py, pz = lowest[len(lowest) // 2]
        if not cv.get(px, py, pz + 1):
            lit = rng.random() < 0.3
            cv.set(px, py, pz + 1, (60, 52, 44) if lit else (150, 110, 60), 'iron')
            if lit:
                glow.append((px, py, pz + 1, (255, 175, 95)))
    if 'ribbon' in details:
        for (px, py, pz) in sel[6:10]:
            cv.set(px, py, pz, (168, 46, 48), 'ribbon')
    if 'frost tips' in details:
        for (px, py, pz) in outer[::5]:
            cv.rgb[px, py, pz] = _snowy(tuple(int(v) for v in cv.rgb[px, py, pz]), 0.55)
    if 'nest' in details:
        px, py, pz = pts[len(pts) // 2]
        cv.rgb[px, py, pz] = (124, 96, 66)
    if 'mistletoe' in details:
        px, py, pz = sel[0]
        cv.rgb[px, py, pz] = (120, 150, 82)
        if not cv.get(px, py, pz + 1):
            cv.set(px, py, pz + 1, (214, 214, 196), 'berry')
    if 'birdhouse' in details:
        tx, ty = x + 1, y
        z = g - 5
        if not cv.get(tx, ty, z) and cv.get(x, y, z):
            cv.set(tx, ty, z, (150, 60, 50), 'birdhouse')
            if not cv.get(tx, ty, z - 1):
                cv.set(tx, ty, z - 1, (90, 60, 50), 'birdhouse')
    if 'squirrel' in details:
        z = g - 6
        if not cv.get(x, y - 1, z) and cv.get(x, y, z):
            cv.set(x, y - 1, z, (150, 84, 48), 'squirrel')
    if 'star' in details:
        px, py, pz = by_z[0]
        if not cv.get(px, py, pz - 1):
            cv.set(px, py, pz - 1, (214, 190, 110), 'ornament')


@_connected
def spruce(cv, rng, x, y, g, pal, h, clear, details, glow, snow=0.7, rmax=6.5):
    """Snow-laden spruce: drooping tiers, smooth base->tip gradient, snow on the tier tops in whole sectors."""
    fa, fb = pal[int(rng.integers(0, len(pal) - 1))], pal[-1 - int(rng.integers(0, 2))]
    bark = BARK[int(rng.integers(len(BARK)))]
    for k in range(h):
        cv.set(x, y, g - 1 - k, shade(bark, 0.9 + 0.1 * ((k // 3) % 2)), 'bark')
    R0 = min(0.24 * h + 1.6 + rng.random(), rmax)
    period = int(rng.integers(2, 4))
    ph = rng.random() * 6.283
    k1 = int(rng.integers(5, 8))
    snow_sect = rng.random(8) < snow
    pts = []
    for k in range(clear, h + 1):
        f = (k - clear) / max(h - clear, 1)
        phase = ((k - clear) % period) / period
        r = R0 * (1 - f) ** 1.0 * (1 - 0.35 * phase) + 0.5
        z = g - 1 - k
        ri = int(math.ceil(r + 1))
        for dx in range(-ri, ri + 1):
            for dy in range(-ri, ri + 1):
                d = math.hypot(dx, dy)
                th = math.atan2(dy, dx)
                if d <= r * (1 + 0.14 * math.sin(k1 * th + ph)) and not cv.get(x + dx, y + dy, z):
                    t = f + (d / max(r, 1)) * 0.15
                    c = clamp8(mix(fa, fb, min(1, max(0, t))))
                    c = shade(c, 0.84 + 0.2 * (d / max(r, 1)))
                    top_open = not cv.get(x + dx, y + dy, z - 1)
                    sect = int(((th + math.pi) / (2 * math.pi)) * 8) % 8
                    if top_open and snow_sect[sect] and phase == 0 and d > 0.6:
                        c = clamp8(mix(SNOW_SHADE, SNOW, 0.4 + 0.6 * (1 - f)))
                    cv.set(x + dx, y + dy, z, c, 'leaf')
                    pts.append((x + dx, y + dy, z))
    cv.set(x, y, g - 2 - h, fb, 'leaf')
    _decorate(cv, rng, x, y, g, details, pts, glow)
    return {'species': 'spruce', 'h': h, 'details': details}


@_connected
def fir(cv, rng, x, y, g, pal, h, clear, details, glow, rmax=4.5):
    """Slender fir: narrow column crown, upturned branch tips, blue-green gradient, snow on every second tier."""
    fa, fb = pal[int(rng.integers(0, 3))], pal[int(rng.integers(3, len(pal)))]
    bark = BARK[int(rng.integers(len(BARK)))]
    for k in range(h):
        cv.set(x, y, g - 1 - k, bark, 'bark')
    R0 = min(0.15 * h + 1.4 + 0.6 * rng.random(), rmax)
    pts = []
    for k in range(clear, h + 1):
        f = (k - clear) / max(h - clear, 1)
        r = R0 * (1 - f ** 1.6) + 0.4
        z = g - 1 - k
        ri = int(math.ceil(r + 1))
        for dx in range(-ri, ri + 1):
            for dy in range(-ri, ri + 1):
                d = math.hypot(dx, dy)
                if d <= r and not cv.get(x + dx, y + dy, z):
                    c = clamp8(mix(fa, fb, f))
                    if (k - clear) % 2 == 1 and not cv.get(x + dx, y + dy, z - 1) and d > r * 0.5:
                        c = _snowy(c, 0.75)
                    cv.set(x + dx, y + dy, z, shade(c, 0.88 + 0.16 * d / max(r, 1)), 'leaf')
                    pts.append((x + dx, y + dy, z))
    cv.set(x, y, g - 2 - h, fb, 'leaf')
    _decorate(cv, rng, x, y, g, details, pts, glow)
    return {'species': 'fir', 'h': h, 'details': details}


@_connected
def birch(cv, rng, x, y, g, pal, h, clear, details, glow, rmax=4.0):
    """Bare winter birch: pale trunk with dark lenticel bands, face-connected branches climbing outwards,
    a frosted twig cloud with a few clinging golden leaves."""
    bark = BIRCH_BARK[int(rng.integers(len(BIRCH_BARK)))]
    for k in range(h):
        c = (58, 54, 52) if rng.random() < 0.18 else shade(bark, 0.94 + 0.06 * rng.random())
        cv.set(x, y, g - 1 - k, c, 'bark')
    pts = []
    nb = int(rng.integers(3, 6))
    for b in range(nb):
        z0 = g - 1 - int(clear + (h - clear) * (0.15 + 0.7 * b / max(nb - 1, 1)))
        ang = rng.random() * 6.283
        L = int(rng.integers(2, max(3, int(rmax)) + 1)) - 1
        px, py, pz = x, y, z0
        for i in range(L):
            nx = x + int(round(math.cos(ang) * (i + 1)))
            ny = y + int(round(math.sin(ang) * (i + 1)))
            if (nx, ny) != (px, py):              # face-connected step: move in x/y first, then up
                if nx != px and ny != py:
                    if not cv.get(nx, py, pz):
                        cv.set(nx, py, pz, (150, 140, 130), 'bark')
                        pts.append((nx, py, pz))
                if not cv.get(nx, ny, pz):
                    cv.set(nx, ny, pz, (150, 140, 130), 'bark')
                    pts.append((nx, ny, pz))
                px, py = nx, ny
            if i % 2 == 1 and not cv.get(px, py, pz - 1):
                pz -= 1
                cv.set(px, py, pz, (160, 150, 140), 'bark')
                pts.append((px, py, pz))
        # twig cloud: frosted and sparse
        for (dx, dy, dz) in ((0, 0, -1), (1, 0, 0), (0, 1, 0), (-1, 0, 0), (0, -1, 0)):
            if rng.random() < 0.6 and not cv.get(px + dx, py + dy, pz + dz):
                c = (226, 200, 120) if rng.random() < 0.12 else (178, 182, 190)
                cv.set(px + dx, py + dy, pz + dz, c, 'twig')
                pts.append((px + dx, py + dy, pz + dz))
    top = g - 1 - h
    for k in range(2):
        cv.set(x, y, top - k, (170, 168, 166), 'twig')
    _decorate(cv, rng, x, y, g, details, pts, glow)
    return {'species': 'birch', 'h': h, 'details': details}


SPECIES = {'spruce': spruce, 'fir': fir, 'birch': birch}


def replace_stand_ins(cv, pines, rng, seed, glow, festive=None):
    """Remove every graybox 'veg' voxel above the terrain and plant a real tree on each recorded stand-in column."""
    vid = cv.materials.get('veg')
    report = {'trees': 0, 'by_species': {}, 'details': {}, 'pruned_voxels': 0}
    if vid is None:
        return report
    zz = np.arange(64)[None, None, :]
    above = zz < cv.H[:, :, None]
    m = (cv.mat == vid) & above & cv.solid
    m[256:] = False
    # ring pines (on the rock zone, ground z <= 46) keep their stand-in cone exactly and are painted as dark tiered
    # pines; valley trees are rebuilt (walk-under canopies were creating ledge pockets on the ring terraces)
    # The same applies to valley pines on a slope (the ground under the canopy rises > 1 above the trunk's ground):
    # a fixed walk-under clearance would sit too low uphill and close pockets.
    def keep_cone(x, y):
        g = int(cv.H[x, y])
        return g <= 46 or g - int(cv.H[max(0, x - 7):x + 8, max(0, y - 7):y + 8].min()) > 1

    ringkeep = np.zeros_like(m)
    for (x, y, r, h0) in pines:
        if keep_cone(x, y):
            ringkeep[x - r - 2:x + r + 3, y - r - 2:y + r + 3] = True
    ringkeep &= m
    rm = m & ~ringkeep
    cv.solid[rm] = False
    cv.mat[rm] = 0
    grove_field = noise.fbm2((512, 512), 48, 2, 'grove_palette', seed)
    report['ring_pines_painted'] = 0
    for (x, y, r, h0) in pines:
        g = int(cv.H[x, y])
        fam = CONIFER_FAMILIES[int(grove_field[x, y] * 3.999)]
        if keep_cone(x, y):
            paint_cone(cv, rng, x, y, r, g, fam, ringkeep)
            report['ring_pines_painted'] += 1
            continue
        hmax = min(h0 + 3, g - 11)                 # tip + top detail stay at z >= 7
        h = int(rng.integers(max(7, h0 - 3), max(8, hmax + 1)))
        h = min(h, hmax)
        if h < 6:
            continue
        t = rng.random()
        sp = 'spruce' if t < 0.6 else ('fir' if t < 0.85 else 'birch')
        # walk-under clearance >= 4 on the valley; on the ring's rock terraces the canopy stays low like the
        # stand-in cone (no walk-under pockets on ledges, which created trap cells)
        clear = int(rng.integers(4, 6)) if g > 46 else 0
        # on the ring the canopy reaches the ground like the stand-in did, so it keeps the stand-in's radius
        rmax = (r + 0.3) if g <= 46 else {'spruce': 6.5, 'fir': 4.5, 'birch': 4.0}[sp]
        if g <= 46 and sp == 'birch':
            sp = 'spruce'
        # festive details (baubles, ribbon, lantern, star) only near the village and the market; wild trees get
        # natural ones (icicles, cones, robin, nest, squirrel, mistletoe, frost, birdhouse)
        near = festive is not None and festive[x, y]
        allow = WINTER_DETAILS if near else NATURAL_DETAILS
        info = SPECIES[sp](cv, rng, x, y, g, fam, h, clear, pick(rng, allow), glow, rmax=rmax)
        report['trees'] += 1
        report['by_species'][sp] = report['by_species'].get(sp, 0) + 1
        report['pruned_voxels'] += info.get('pruned_voxels', 0)
        for d in info['details']:
            report['details'][d] = report['details'].get(d, 0) + 1
    return report


def paint_cone(cv, rng, x, y, r, g, pal, keep):
    """Paint a kept stand-in cone as a dark tiered pine: tier bands every 3, a smooth base->tip gradient, snow on the
    upward faces of each tier top, three random recolour details (frost tips, cones, a red ribbon, a bird...)."""
    x0, x1, y0, y1 = x - r - 2, x + r + 2, y - r - 2, y + r + 2
    sub = keep[x0:x1 + 1, y0:y1 + 1]
    xs, ys, zs = np.nonzero(sub)
    if not len(xs):
        return
    X, Y, Z = xs + x0, ys + y0, zs
    zt, zb = Z.min(), Z.max()
    fa, fb = pal[int(rng.integers(0, 2))], pal[int(rng.integers(3, len(pal)))]
    details = pick(rng, ('frost tips', 'pinecones', 'icicles', 'lichen', 'bare tip'))
    for (a, b, c) in zip(X, Y, Z):
        f = (zb - c) / max(zb - zt, 1)
        col = clamp8(mix(fa, fb, f))
        tier = (zb - c) % 3
        if tier == 2:
            col = shade(col, 0.82)
        if not cv.get(a, b, c - 1) and tier == 0:
            col = clamp8(mix(SNOW_SHADE, SNOW, 0.3 + 0.5 * f))
        h = noise.hash3(a, b, c, 17)
        if 'frost tips' in details and h < 0.08:
            col = _snowy(col, 0.6)
        if 'pinecones' in details and 0.08 <= h < 0.12:
            col = (110, 80, 54)
        if 'baubles' in details and 0.12 <= h < 0.14:
            col = (176, 52, 48)
        if 'lichen' in details and 0.14 <= h < 0.2 and c > zb - 3:
            col = (120, 130, 90)
        if 'icicles' in details and c == zb and h < 0.3:
            col = (176, 206, 222)
        cv.rgb[a, b, c] = col
        cv.mat[a, b, c] = cv.material('leaf')
    if 'bare tip' in details:
        cv.rgb[x, y, zt] = (96, 74, 56)


def holly_recolour(cv, rng, box_list):
    """Front / under-platform bushes keep their graybox voxels exactly; they become holly with berries."""
    vid = cv.materials.get('veg')
    n = 0
    for (x0, x1, y0, y1) in box_list:
        sub = cv.solid[x0:x1 + 1, y0:y1 + 1] & (cv.mat[x0:x1 + 1, y0:y1 + 1] == vid)
        for (i, j, k) in zip(*np.nonzero(sub)):
            x, y, z = x0 + i, y0 + j, k
            c = clamp8(mix((40, 74, 50), (70, 104, 60), rng.random()))
            if rng.random() < 0.12:
                c = (170, 40, 44)
            elif not cv.get(x, y, z - 1) and rng.random() < 0.5:
                c = _snowy(c, 0.65)
            cv.rgb[x, y, z] = c
            cv.mat[x, y, z] = cv.material('holly')
            n += 1
    return n


def giant_spruce(cv, rng, S, glow):
    """The village spruce one-off: the graybox cone envelope (r <= 12.5, z 12..40) rebuilt as drooping layered boughs
    with snow tips, a gold garland spiral, ornaments (warm / white glow, rare green) and a white star at z 8-11."""
    sp = S['spruce']
    cx, cy = sp['c'][0], sp['c'][1] + 0.5
    vid = cv.materials.get('veg')
    zb, zt = sp['cone_base_z'], sp['tip_z']
    R = sp['r'] - 0.5
    x0, x1, y0, y1 = int(cx - R - 2), 255, int(cy - R - 2), int(cy + R + 2)
    sub = (cv.mat[x0:x1 + 1, y0:y1 + 1, zt - 1:zb + 1] == vid)
    cv.solid[x0:x1 + 1, y0:y1 + 1, zt - 1:zb + 1][sub] = False
    cv.mat[x0:x1 + 1, y0:y1 + 1, zt - 1:zb + 1][sub] = 0
    pal = palette_family([(26, 56, 46), (40, 82, 60), (70, 110, 72)], 8)
    n_orn = 0
    h = zb - zt
    for z in range(zt, zb + 1):
        f = (z - zt) / h                                   # 0 at the tip, 1 at the base
        tier = (zb - z) % 4
        r = R * f * (1.0 - 0.34 * (tier / 3.0)) + 0.6
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                dx, dy = x + 0.5 - cx, y + 0.5 - cy
                d = math.hypot(dx, dy)
                th = math.atan2(dy, dx)
                rr = r * (1 + 0.08 * math.sin(7 * th + z * 0.7))
                if d > rr:
                    continue
                c = clamp8(mix(pal[1], pal[-1], 0.25 + 0.65 * (1 - f) * 0.6 + 0.35 * d / max(rr, 1)))
                c = shade(c, 0.8 + 0.25 * d / max(rr, 1))
                if tier == 0 and d > rr - 1.6 and math.cos(th * 3 + z * 0.9) > -0.2:
                    c = clamp8(mix(SNOW_SHADE, SNOW, 0.5 + 0.5 * math.cos(th * 3) ** 2))
                # garland: a gold helix on the outer skin
                hel = (th + (zb - z) * 0.32) % (2 * math.pi)
                if d > rr - 1.2 and hel < 0.28:
                    c = (204, 168, 86)
                cv.set(x, y, z, c, 'spruce')
    # trunk stays (graybox trunk material veg inside -> recolour)
    tm = (cv.mat[x0:x1 + 1, y0:y1 + 1, :] == vid)
    for (i, j, k) in zip(*np.nonzero(tm)):
        cv.rgb[x0 + i, y0 + j, k] = (90, 66, 50)
        cv.mat[x0 + i, y0 + j, k] = cv.material('bark')
    # ornaments on the outer skin
    orn_cols = [(255, 175, 95), (255, 255, 95), (255, 255, 255), (255, 175, 95), (95, 255, 95)]
    for z in range(zt + 4, zb, 3):
        f = (z - zt) / h
        r = R * f + 1.5
        k = max(2, int(r * 0.9))
        for a in range(k):
            th = (a + rng.random() * 0.6) * 2 * math.pi / k + z
            hit = None
            for rr in np.arange(r, 0, -0.5):             # walk inwards to the outer skin of the boughs
                x = int(math.floor(cx + rr * math.cos(th)))
                y = int(math.floor(cy + rr * math.sin(th)))
                if x <= 255 and cv.solid[x, y, z]:
                    hit = (x, y)
                    break
            if hit is None:
                continue
            x, y = hit
            if rng.random() < 0.4:
                c = orn_cols[int(rng.integers(len(orn_cols)))]
                if c == (95, 255, 95) and rng.random() < 0.7:
                    c = (255, 175, 95)
                glow.append((x, y, z, c))
                n_orn += 1
            else:
                cv.rgb[x, y, z] = [(168, 46, 48), (196, 160, 70), (180, 186, 200)][int(rng.integers(3))]
    # star: a 5-point star in the x-z plane (west half; the mirror completes it) above the tip, white glow core
    sx, sz = 255, zt - 2                                   # star z 7..11, resting on the tip (z 12)
    star = [(0, -3), (0, -2), (0, -1), (0, 0), (0, 1), (-1, -1), (-2, -1), (-1, 0), (-1, -2), (-1, 1)]
    for (dx, dz) in star:
        cv.set(sx + dx, int(cy), sz + dz, (230, 210, 140), 'star')
    glow.append((sx, int(cy), sz, (255, 255, 255)))
    glow.append((sx - 1, int(cy), sz, (255, 255, 95)))
    return {'ornament_lights': n_orn}
