"""The Wicker King's Harvest — Halloween Tower of Babel island (AoS 0.75 / piqueserver 1.4.2 babel).

Layout, landmarks and props. Run wkh_main.py to build, colour and export; wkh_check.py to validate.
Everything gameplay-relevant is authored on the west half and mirrored (x' = 512 - x); only the curling stem
in the north notch is placed after mirroring (cosmetic, recorded as cosmetic_asymmetric_bbox).
"""
from __future__ import annotations

import math
import sys

import numpy as np
from scipy import ndimage as ndi

from wkh_core import fbm2, fold_x, hash3, pack_rgb, value_noise2
from wkh_props import *          # noqa: F401,F403  (materials + props)
import wkh_props as P
from wkh_terrain import PZ, SPEC, SEED, terrain

NAME = "The Wicker King's Harvest"
FILE = 'wicker_kings_harvest'
VERSION = '1.0'


# ----------------------------------------------------------------------------------------------- paths

def poly_mask(polys, width_fn=None):
    """2D mask of thick polylines. polys: list of (points, width)."""
    m = np.zeros((512, 512), bool)
    for pts, w in polys:
        for (p, q) in zip(pts[:-1], pts[1:]):
            n = int(max(abs(q[0] - p[0]), abs(q[1] - p[1])) * 2) + 1
            for k in range(n + 1):
                x = p[0] + (q[0] - p[0]) * k / n
                y = p[1] + (q[1] - p[1]) * k / n
                r = w / 2
                x0, x1 = int(math.floor(x - r)), int(math.ceil(x + r))
                y0, y1 = int(math.floor(y - r)), int(math.ceil(y + r))
                for xx in range(max(x0, 0), min(x1, 511) + 1):
                    for yy in range(max(y0, 0), min(y1, 511) + 1):
                        if (xx + 0.5 - x) ** 2 + (yy + 0.5 - y) ** 2 <= r * r:
                            m[xx, yy] = True
    return m


PATHS = [   # left half (mirrored)
    ([(141, 256), (175, 256), (206, 256)], 7),                                       # front: spawn -> clearing
    ([(118, 234), (124, 224), (131, 210), (136, 188), (146, 160), (160, 132), (176, 108), (204, 100),
      (232, 108)], 4),                                                                 # north route
    ([(118, 280), (122, 296), (134, 318), (150, 350), (176, 384), (208, 408), (240, 418), (256, 419)], 4),
    ([(124, 282), (138, 292), (170, 297), (214, 298), (238, 302)], 4),               # upper-lip path
    ([(256, 130), (256, 160), (255, 206)], 5),                                         # between the eyes
    ([(96, 256), (70, 252), (58, 248)], 3),                                            # out to the west dock
    ([(208, 108), (214, 140), (226, 186), (238, 214)], 3),                             # King -> clearing NW
    ([(150, 350), (134, 380), (126, 404)], 3),                                         # SW lobe track
]

SPAWN_WALL = {'x': (95, 141), 'y': (233, 279)}


def gate_gaps():
    return {'N': (112, 124), 'S': (112, 124), 'E': (245, 267), 'W': (250, 262)}


# ----------------------------------------------------------------------------------------------- terrain fill

def fill_terrain(F):
    H = F['H'].copy()
    land = H < 63
    rho = F['rho']
    # rocky shore shelf just inside the coastline
    n_shore = fold_x(fbm2((512, 512), 10, 2, 'shore', SEED))
    shelf = land & (rho > 0.965)
    zs = np.rint(56 + (rho - 0.965) / 0.035 * 5 + (n_shore - 0.5) * 5).astype(int)
    zs = np.clip(zs, 54, 61)
    H = np.where(shelf, np.maximum(H, zs), H)
    F['shelf'] = shelf
    F['H'] = H
    return F


def pads(F, rects):
    """Flatten building pads to the plateau level (cut into lobes; the cut faces show skin/rock)."""
    H = F['H']
    for (x0, x1, y0, y1, z) in rects:
        H[x0:x1 + 1, y0:y1 + 1] = z
    F['H'] = H


def stair_cut(F, pts, width, z_from, z_to):
    """Set the terrain to an exact stair (1-voxel risers) along a polyline (cuts and fills)."""
    H = F['H']
    st = F.setdefault('stairs', np.zeros((512, 512), bool))
    pts = np.array(pts, float)
    seg = np.diff(pts, axis=0); L = np.hypot(seg[:, 0], seg[:, 1]); tot = L.sum(); cum = 0
    for p, s, l in zip(pts[:-1], seg, L):
        n = int(np.ceil(l * 2))
        for k in range(n + 1):
            q = p + s * k / n
            z = int(round(z_from + (z_to - z_from) * (cum + l * k / n) / tot))
            x0, y0 = int(round(q[0] - width / 2)), int(round(q[1] - width / 2))
            H[x0:x0 + width, y0:y0 + width] = z
            st[x0:x0 + width, y0:y0 + width] = True
        cum += l


def voxelize_terrain(V, F):
    H = F['H']
    m = V.m
    zz = np.arange(64)[None, None, :]
    solid = zz >= H[:, :, None]
    land = (H < 63)
    rho = F['rho']
    rim = (rho >= F['rim0'] - 0.01) & land
    pit = F['pit']
    # default deep material: dark rock inside the face, skin (upper) + rock (lower) on the rim/coast
    deep = np.where(rim[:, :, None], np.where(zz >= 51, ROCK, SKIN), PIT_ROCK)
    m[:] = np.where(solid, deep, 0).astype(np.uint8)
    m[:, :, 63] = np.where(land, ROCK, SEA)
    # soil skin: 2 voxels of earth over the face rock, skin on the rim
    top = H
    xs, ys = np.nonzero(land)
    tz = top[xs, ys]
    for d in (0, 1):
        z = np.clip(tz + d, 0, 63)
        is_rim = rim[xs, ys]
        is_pit = pit[xs, ys]
        is_shelf = F['shelf'][xs, ys]
        mat = np.where(is_shelf, SHORE_ROCK, np.where(is_rim, SKIN, np.where(is_pit, ASH if d == 0 else PIT_ROCK,
                                                                             SOIL if d == 0 else DIRT)))
        m[xs, ys, z] = mat.astype(np.uint8)


# ----------------------------------------------------------------------------------------------- landmarks

def wicker_king(V, cx, cy, g):
    """Giant woven effigy on a stepped stone plinth, arms outstretched, facing south toward the clearing."""
    steps = [(18, 13), (14, 9)]
    for i, (hx, hy) in enumerate(steps):
        z = g - 1 - i
        V.box(cx - hx, cx + hx - 1, cy - hy, cy + hy - 1, z, z, STONE)
        if i == 0:
            for xx in range(cx - hx, cx + hx):
                for yy in range(cy - hy, cy + hy):
                    V.column_to_ground(xx, yy, z + 1, STONE)
    V.box(cx - 4, cx + 3, cy + 9, cy + 12, g - 1, g - 1, STONE)
    base = g - 2                                         # plinth top surface z
    for (bx, by) in ((cx - 13, cy - 6), (cx + 12, cy - 6), (cx - 13, cy + 5), (cx + 12, cy + 5)):
        V.box(bx, bx, by, by, base - 2, base - 1, IRON)
        V.put(bx, by, base - 3, GLOW)

    def weave_layer(zc, rx, ry, ring, ox=0, band=0):
        for dx in range(-int(rx) - 2, int(rx) + 3):
            for dy in range(-int(ry) - 2, int(ry) + 3):
                d = math.hypot(dx / max(rx, 0.5), dy / max(ry, 0.5))
                if 1 - 1.7 / max(min(rx, ry), 1) <= d <= 1.0 + 0.45 / max(rx, ry, 1):
                    a = math.atan2(dy, dx)
                    stave = int(math.floor((a / (2 * math.pi)) * 24 + band)) % 3 == 0
                    if ring or stave:
                        V.put(cx + ox + dx, cy + dy, zc, WICKER if (ring or (dx + dy + zc) % 3) else WICKER_DK)

    leg_h = 10
    for side in (-1, 1):
        lx = cx + side * 6
        for k in range(leg_h):
            z = base - 1 - k
            r = 2.9 - 0.05 * k
            off = -side * (k // 5)
            for dx in range(-4, 5):
                for dy in range(-4, 5):
                    d = math.hypot(dx, dy)
                    if d <= r and (d >= r - 1.4 or k % 3 == 0):
                        V.put(lx + off + dx, cy + dy, z, WICKER if (k + dx + dy) % 4 else WICKER_DK)
            V.put(lx + off, cy, z, WICKER_DK)            # inner pole
        V.box(lx - 3, lx + 3, cy - 3, cy + 3, base - 1, base - 1, WICKER_DK)
    zh = base - 1 - leg_h
    V.box(cx - 8, cx + 7, cy - 2, cy + 2, zh, zh, WICKER_DK)
    torso_h = 12
    for k in range(torso_h):
        z = zh - 1 - k
        f = k / (torso_h - 1)
        rx = 5.0 + 5.0 * f ** 1.3
        ry = 3.6 + 1.8 * f
        ring = (k % 3 == 0) or k == torso_h - 1
        weave_layer(z, rx, ry, ring=ring, band=k // 3)
        if ring:                                      # cross braces tie each ring to the spine
            V.box(cx - int(rx), cx + int(rx) - 1, cy, cy, z, z, WICKER_DK)
    V.box(cx - 1, cx, cy, cy, zh - torso_h, zh, WICKER_DK)
    zs = zh - torso_h
    V.box(cx - 11, cx + 10, cy - 1, cy + 1, zs, zs, WICKER_DK)
    for side in (-1, 1):
        x_start = cx + (11 if side > 0 else -12)
        L = 20
        prev = None
        for i in range(L):
            x = x_start + side * i
            z = zs + (i // 7)
            V.box(x, x, cy - 1, cy + 1, z, z + 1, WICKER if (i + z) % 3 else WICKER_DK)
            if prev is not None and prev != z:
                V.box(x, x, cy - 1, cy + 1, min(prev, z), max(prev, z) + 1, WICKER)
            prev = z
            if i % 6 == 3:
                V.put(x, cy, z + 2, ROPE); V.put(x, cy, z + 3, ROPE); V.put(x, cy, z + 4, IRON); V.put(x, cy, z + 5, GLOW)
        xe = x_start + side * (L - 1)
        ze = zs + (L - 1) // 7
        for j, (ddx, ddy, ddz) in enumerate(((4, -1, -3), (5, 0, -1), (4, 1, 1), (3, 0, 3), (2, -1, 4))):
            V.line4((xe, cy + ddy, ze), (xe + side * ddx, cy + ddy, ze + ddz), WICKER_DK)
    # neck, head (woven sphere), ember eyes + mouth, twig crown
    V.box(cx - 1, cx, cy - 1, cy, zs - 2, zs - 1, WICKER_DK)
    hr = 4.6
    zc = zs - 2 - 5
    for dx in range(-6, 7):
        for dy in range(-6, 7):
            for dz in range(-6, 7):
                d = math.sqrt(dx * dx + (dy * 1.12) ** 2 + dz * dz)
                if hr - 1.5 <= d <= hr + 0.3:
                    lat = (dz + 12) % 3 == 0
                    lon = int(math.floor((math.atan2(dy, dx) / (2 * math.pi)) * 14)) % 2 == 0
                    if lat or lon:
                        V.put(cx + dx, cy + dy, zc + dz, WICKER if (dx + dz) % 3 else WICKER_DK)
    V.box(cx - 1, cx, cy - 1, cy, zc - 4, zs - 2, WICKER_DK)
    for ex in (cx - 3, cx + 2):
        V.box(ex, ex + 1, cy + 3, cy + 4, zc - 1, zc - 1, GLOW)
    V.box(cx - 2, cx + 1, cy + 4, cy + 4, zc + 2, zc + 2, GLOW)
    ztop = zc - 4
    V.box(cx - 3, cx + 2, cy - 3, cy + 2, ztop + 1, ztop + 1, WICKER_DK)
    for i in range(11):
        a = i * 2 * math.pi / 11
        sx = cx + int(round(math.cos(a) * 3)); sy = cy + int(round(math.sin(a) * 3))
        V.put(sx, sy, ztop + 1, WICKER_DK)
        V.line4((sx, sy, ztop + 1), (sx + int(round(math.cos(a) * 2)), sy + int(round(math.sin(a) * 2)),
                                        ztop - 2 - (i % 3)), WICKER_DK)
    for (ox, oy) in ((-12, 11), (10, 12), (-6, 14), (5, 15), (-16, 2), (15, 3)):
        xg, yg = cx + ox, cy + oy
        hay_bale(V, xg, yg, V.ground(xg, yg), along_x=(ox % 2 == 0))


def stem(V, cx, cy, g, rng):
    """Thick ribbed pumpkin stem: rises from the north notch, then hooks over to the west like a crook."""
    path = []
    N1 = 60
    top = (cx - 4.0, cy - 5.0, 31.0)
    for i in range(N1):
        t = i / (N1 - 1)
        e = math.sin(t * math.pi / 2)
        path.append((cx + (top[0] - cx) * t, cy + (top[1] - cy) * e, top[2] * e, 8.6 - 3.0 * t))
    R = 7.0
    ccx, ccz = top[0] - R, top[2]
    N2 = 50
    for i in range(1, N2):
        a = math.radians(220 * i / (N2 - 1))
        path.append((ccx + R * math.cos(a), top[1] - 2 * i / N2, ccz + R * math.sin(a), 5.6 - 2.2 * i / N2))
    for i, (x, y, h, r) in enumerate(path):
        z = g - h
        ri = int(r) + 2
        for dx in range(-ri, ri + 1):
            for dy in range(-ri, ri + 1):
                for dz in range(-2, 3):
                    if dx * dx + dy * dy + dz * dz * 1.5 <= r * r:
                        a = math.atan2(dy, dx) + i * 0.07
                        rib = int(math.floor(a / (2 * math.pi) * 10)) % 2 == 0
                        V.put(int(round(x + dx)), int(round(y + dy)), int(round(z + dz)), STALK if rib else STALK_DK)
    # cut, dried tip
    x, y, h, r = path[-1]
    V.box(int(x) - 1, int(x) + 1, int(y) - 1, int(y) + 1, int(g - h) + 1, int(g - h) + 2, STRAW)
    # root flare, tendrils and vines
    for k in range(9):
        a = k * 2 * math.pi / 9 + 0.2
        V.line4((cx, cy, g - 2), (cx + math.cos(a) * 14, cy + math.sin(a) * 11, g - 1), STALK_DK)
    for k in range(8):
        vine_run(V, cx + int(rng.integers(-14, 14)), cy + int(rng.integers(4, 18)),
                 lambda a, b: V.ground(a, b), rng, length=30, pumpkins=True)
    # a curling tendril off the stem
    pts = [(cx + 6, cy, g - 14)]
    for k in range(1, 14):
        a = k * 0.6
        pts.append((cx + 6 + k * 0.6 + math.cos(a) * 2, cy + math.sin(a) * 2, g - 14 - k * 0.5))
    for p, q in zip(pts[:-1], pts[1:]):
        V.line4(p, q, VINE)


def pier(V, F, k, rng, length=24, boat_side=1):
    """Wooden pier in the coastal notch of rim groove k, with a stair cut up to the plateau and a boat."""
    cx, cy = SPEC['center']
    th = -math.pi / 2 + k * 2 * math.pi / SPEC['lobes']
    ux, uy = math.cos(th), math.sin(th)
    H = F['H']
    # find the coast along the ray
    r = 120.0
    while r < 260:
        x, y = int(cx + ux * r), int(cy + uy * r)
        if H[x, y] >= 63:
            break
        r += 0.5
    coast = r
    # stair: from the shelf edge (z 61) inward up to the plateau level
    p_out = (cx + ux * (coast - 1), cy + uy * (coast - 1))
    p_in = (cx + ux * (coast - 30), cy + uy * (coast - 30))
    zin = int(H[int(p_in[0]), int(p_in[1])])
    stair_cut(F, [p_out, p_in], 4, 61, zin)
    return dict(th=th, coast=coast, u=(ux, uy), zin=zin)


def pier_deck(V, info, rng, length=22, boat_side=1):
    cx, cy = SPEC['center']
    ux, uy = info['u']
    vx, vy = -uy, ux
    base = info['coast'] - 2
    for i in range(length):
        for j in range(-2, 2):
            x = int(round(cx + ux * (base + i) + vx * j)); y = int(round(cy + uy * (base + i) + vy * j))
            if V.m[x, y, 61] == 0 and V.m[x, y, 60] == 0:
                V.put(x, y, 61, PLANK)
                if i % 4 == 0 and j in (-2, 1):
                    V.put(x, y, 62, TIMBER)                      # post standing on the water plane
                    V.put(x, y, 60, TIMBER); V.put(x, y, 59, TIMBER)
                    if i % 8 == 0:
                        V.put(x, y, 58, GLOW)
                elif j in (-2, 1) and i % 4 == 2:
                    V.put(x, y, 60, ROPE)
    # landing step at the end
    for j in range(-2, 2):
        x = int(round(cx + ux * (base + length) + vx * j)); y = int(round(cy + uy * (base + length) + vy * j))
        V.put(x, y, 62, PLANK)
    # rowboat moored alongside
    bx = cx + ux * (base + length * 0.55) + vx * 5 * boat_side
    by = cy + uy * (base + length * 0.55) + vy * 5 * boat_side
    for i in range(-4, 5):
        w = 1 if abs(i) >= 3 else 2
        for j in range(-w, w + 1):
            x = int(round(bx + ux * i + vx * j)); y = int(round(by + uy * i + vy * j))
            if V.m[x, y, 62] == 0:
                V.put(x, y, 62, HULL)
                edge = abs(j) == w or abs(i) == 4
                if edge:
                    V.put(x, y, 61, HULL)
    V.put(int(round(bx)), int(round(by)), 61, PLANK)


def offshore_rock(V, x, y, rng, r=5, h=6):
    for dx in range(-r - 1, r + 2):
        for dy in range(-r - 1, r + 2):
            d = math.hypot(dx, dy * 1.2)
            if d <= r:
                top = 62 - int(round(h * (1 - (d / r) ** 1.6) + rng.random() * 1.2))
                V.box(x + dx, x + dx, y + dy, y + dy, max(top, 40), 62, SHORE_ROCK)


# ----------------------------------------------------------------------------------------------- pits

def pit_furnish(V, F, rng):
    H = F['H']
    gz = lambda x, y: int(H[x, y])
    # eye walkway (broken), y 178..180, deck z 48 over the pit
    y0 = 178
    for x in range(150, 214):
        if 177 <= x <= 181:
            continue                                   # broken gap
        for y in range(y0, y0 + 3):
            if F['eye_mask'][x, y] and H[x, y] > 48:
                V.put(x, y, 48, PLANK)
                if x % 6 == 0 and y in (y0, y0 + 2):
                    V.box(x, x, y, y, 49, H[x, y] - 1, TIMBER)
        if x % 6 == 0 and F['eye_mask'][x, y0] and H[x, y0] > 48:
            V.box(x, x, y0 - 1, y0 - 1, 46, 48, TIMBER)        # rail post
    # make sure each walkway piece has a post at both ends
    for x in (152, 176, 182, 208):
        for y in (y0, y0 + 2):
            if F['eye_mask'][x, y] and H[x, y] > 48:
                V.box(x, x, y, y, 48, H[x, y] - 1, TIMBER)
    # lookout scaffold in the eye floor
    lx, ly = 190, 192
    if F['eye_mask'][lx, ly]:
        g = gz(lx, ly)
        for (px, py) in ((lx, ly), (lx + 4, ly), (lx, ly + 3), (lx + 4, ly + 3)):
            V.box(px, px, py, py, g - 4, g - 1, TIMBER)
        V.box(lx, lx + 4, ly, ly + 3, g - 4, g - 4, PLANK)
    # lanterns on the eye floor
    for (x, y) in ((170, 160), (186, 140), (200, 196), (160, 196)):
        if F['eye_mask'][x, y]:
            lantern_post(V, x, y, gz(x, y), h=4)
    # nose bridge E-W at deck z 44 with posts
    for x in range(236, 257):
        for y in (301, 302, 303):
            if F['nose_mask'][x, y]:
                V.put(x, y, 44, PLANK)
                if x % 5 == 0 and y != 302:
                    V.box(x, x, y, y, 45, H[x, y] - 1, TIMBER)
    V.box(256, 256, 301, 303, 45, int(H[256, 302]) - 1, TIMBER)
    # grin bridges
    g = SPEC['grin']
    for off, kind in SPEC['grin_bridges']:
        bx = 256 + off
        ys = [y for y in range(280, 440) if F['grin_mask'][bx, y]]
        if not ys:
            continue
        for x in (bx - 1, bx, bx + 1):
            for y in range(min(ys), max(ys) + 1):
                if H[x, y] > 44:
                    V.put(x, y, 44, PLANK)
                    if (y - min(ys)) % 5 == 2 and x != bx:
                        V.box(x, x, y, y, 45, H[x, y] - 1, TIMBER)
                    if (y - min(ys)) % 4 == 0 and x != bx:
                        V.put(x, y, 43, TIMBER)                 # low rail stub
        for y in (min(ys), max(ys)):
            V.box(bx - 1, bx + 1, y, y, 45, int(H[bx, y]) - 1, TIMBER)
    # trench boardwalk along the floor centre + lanterns
    for x in range(140, 257):
        t = (x - 256) / g['half_w']
        q = max(0.0, 1 - t * t)
        ymid = int(round(g['corner_y'] + (g['upper_sag'] * q + g['lower_sag'] * q ** 0.85) / 2))
        for y in (ymid - 1, ymid, ymid + 1):
            if F['grin_mask'][x, y] and not F['ramps'][x, y]:
                F['floor_plank'][x, y] = True
        if x % 22 == 4 and F['grin_mask'][x, ymid + 3]:
            lantern_post(V, x, ymid + 3, int(H[x, ymid + 3]), h=4, arm=(0, -1))


def scatter(V, F, gz, n_try=1800):
    """Clustered small props on open plateau/lobes: pumpkin clusters, hay, tufts. Avoids routes and objectives."""
    H = F['H']
    rng = np.random.default_rng(SEED + 77)
    keep = np.zeros((512, 512), bool)
    keep[:257] = True
    bad = F['pit'] | F['path_mask'] | F['stairs'] | F['shelf']
    bad = ndi.binary_dilation(bad, iterations=2)
    X, Y = F['X'], F['Y']
    bad |= (X > 90) & (X < 222) & (Y > 226) & (Y < 288)          # spawn yard + front corridor
    (ccx, ccy), cr = SPEC['clearing']
    bad |= np.hypot(X - ccx, Y - ccy) < cr + 4
    for (x0, x1, y0, y1) in FIELDS:
        bad |= (X > x0 - 2) & (X < x1 + 2) & (Y > y0 - 2) & (Y < y1 + 2)
    cl = fold_x(fbm2((512, 512), 40, 2, 'scatter', SEED))
    placed = 0
    for _ in range(n_try):
        x = int(rng.integers(40, 256)); y = int(rng.integers(40, 472))
        if not keep[x, y] or bad[x, y] or H[x, y] >= 52 or cl[x, y] < 0.46:
            continue
        g = gz(x, y)
        if g != H[x, y]:
            continue                                                # something already here
        if (V.m[x - 3:x + 4, y - 3:y + 4, max(g - 4, 0):g] != 0).any():
            continue
        r = rng.random()
        if r < 0.55:
            for k in range(int(rng.integers(2, 5))):
                px, py = x + int(rng.integers(-3, 4)), y + int(rng.integers(-3, 4))
                if not bad[px, py]:
                    pumpkin(V, px, py, gz(px, py), size=int(rng.integers(0, 2)))
            V.put(x, y, g - 1, VINE)
        elif r < 0.75:
            hay_bale(V, x, y, g, along_x=bool(rng.integers(0, 2)))
        else:
            for k in range(int(rng.integers(4, 9))):
                px, py = x + int(rng.integers(-3, 4)), y + int(rng.integers(-3, 4))
                gg = gz(px, py)
                if not bad[px, py] and V.get(px, py, gg) in (SOIL, SKIN):
                    V.put(px, py, gg - 1, GRASS)
        placed += 1
    F['scatter_count'] = placed


def shoring(V, F):
    """Mine-style timber posts against the pit walls, some carrying amber lamps (left half; mirrored)."""
    H = F['H']
    pit = F['pit']
    for x in range(120, 257):
        for y in range(100, 440):
            if not pit[x, y] or F['ramps'][x, y]:
                continue
            h = H[x, y]
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                hn = H[x + dx, y + dy]
                if hn <= h - 3 and ((x * 7 + y * 13) % 17 == 0):
                    if V.m[x, y, h - 1] != 0:
                        continue
                    V.box(x, x, y, y, hn, h - 1, TIMBER)
                    if (x + 2 * y) % 4 == 0:
                        V.put(x, y, hn + 1, GLOW)
                    break


def ember_cracks(F):
    """Fissure network on pit floors and up the terrace walls (colour only)."""
    n = fold_x(fbm2((512, 512), 14, 3, 'cracks', SEED))
    ridge = np.abs(n - 0.5) < 0.0045
    floor = F['H'] >= PZ + 5
    return ridge & F['pit'] & floor


# ----------------------------------------------------------------------------------------------- ground paint

FIELDS = [(100, 130, 146, 184), (96, 128, 322, 352), (214, 246, 142, 172), (174, 232, 410, 432),
          (196, 232, 306, 326)]


def paint_ground(V, F):
    """Top-surface materials: paths, clearing, farmyard, fields, stairs, ember cracks (left half; mirrored)."""
    H = F['H']; m = V.m
    land = H < 63
    X, Y = F['X'], F['Y']
    def setm(mask, mat):
        xs, ys = np.nonzero(mask & land)
        m[xs, ys, H[xs, ys]] = mat
    (ccx, ccy), cr = SPEC['clearing']
    dc = np.hypot(X - ccx, Y - ccy)
    flat_face = ~F['pit'] & (H == PZ)
    setm((dc < cr) & flat_face, CLEARING)
    yard = (X > 96) & (X < 140) & (Y > 234) & (Y < 278)
    setm(yard & flat_face, CLEARING)
    pm = fold_x(poly_mask(PATHS))
    F['path_mask'] = pm
    setm(pm & ~F['pit'] & ~F['stairs'] & ~F['shelf'], PATH)
    for (x0, x1, y0, y1) in FIELDS:
        fm = (X > x0 + 1) & (X < x1 - 1) & (Y > y0 + 1) & (Y < y1 - 1) & ~F['pit']
        rows = (np.floor(Y) - y0) % 3 == 0
        setm(fm & rows, FURROW); setm(fm & ~rows, FIELD)
    setm(F['stairs'], STAIR)
    nf = fold_x(fbm2((512, 512), 4, 2, 'yardstraw', SEED))
    setm(yard & flat_face & (nf > 0.70), HAY_LITTER)
    rut = yard & flat_face & ((np.abs(Y - 251.5) < 0.6) | (np.abs(Y - 261.5) < 0.6)) & (nf < 0.7)
    setm(rut, EARTH_DK)
    setm(ember_cracks(F) & ~F['ramps'], EMBER)
    F['crack_mask'] = ember_cracks(F)


# ----------------------------------------------------------------------------------------------- build

def build(graybox=False, sky=False):
    rng = np.random.default_rng(SEED)
    F = terrain()
    F = fill_terrain(F)
    # building pads (left half; mirrored later by folding H)
    PADS = [(83, 117, 191, 217, PZ), (82, 103, 286, 304, PZ), (84, 94, 306, 316, PZ), (155, 164, 210, 219, PZ),
            (104, 114, 288, 298, PZ)]
    pads(F, PADS)
    # piers + stairs (grooves 8, 10, 12 on the left; 7 = south axis)
    piers = []
    for k in (8, 10, 12, 7):
        piers.append(pier(None, F, k, rng))
    F['H'] = fold_x(F['H'])
    F['stairs'] = fold_x(F['stairs'])
    H = F['H']
    F['floor_plank'] = np.zeros((512, 512), bool)

    V = Vox(H)
    voxelize_terrain(V, F)
    if graybox:
        return V, F, piers

    gz = lambda x, y: int(V.ground(x, y))
    Hg = lambda x, y: int(H[int(x), int(y)])
    paint_ground(V, F)

    # ---------------- blue hamlet (west); everything here is mirrored to the east
    barn(V, 84, 114, 192, 214, PZ, door_side='S')
    farmhouse(V, 84, 98, 288, 302, PZ, porch='E')
    shed(V, 156, 163, 211, 218, PZ, door=(0, 1))
    silo(V, 150, 227, PZ, r=4, h=15)
    silo(V, 150, 285, PZ, r=4, h=15)
    # gate oaks: broad autumn canopies over the yard's east gate (sightline cover from the platform; you
    # walk underneath - trunks stand on the wall line, canopies start 9 above the ground)
    for (x, y, lean) in ((148, 241, (-1, 1)), (148, 271, (-1, -1))):
        big_tree(V, x, y, PZ, np.random.default_rng(SEED + x + 3 * y), trunk_h=9, cr=8, ch=4, lean=lean)
    shed(V, 85, 92, 308, 314, PZ, door=(1, 0))
    windpump(V, 106, 290, PZ, h=17)
    # spawn yard wall with four gates (outside the stock +-20 spawn square)
    sw = SPAWN_WALL
    gg = gate_gaps()
    wr = np.random.default_rng(SEED + 5)
    drystone_wall(V, [(sw['x'][0], sw['y'][0]), (gg['N'][0], sw['y'][0])], Hg, wr)
    drystone_wall(V, [(gg['N'][1], sw['y'][0]), (sw['x'][1], sw['y'][0])], Hg, wr)
    drystone_wall(V, [(sw['x'][0], sw['y'][1]), (gg['S'][0], sw['y'][1])], Hg, wr)
    drystone_wall(V, [(gg['S'][1], sw['y'][1]), (sw['x'][1], sw['y'][1])], Hg, wr)
    drystone_wall(V, [(sw['x'][1], sw['y'][0]), (sw['x'][1], gg['E'][0])], Hg, wr)
    drystone_wall(V, [(sw['x'][1], gg['E'][1]), (sw['x'][1], sw['y'][1])], Hg, wr)
    drystone_wall(V, [(sw['x'][0], sw['y'][0]), (sw['x'][0], gg['W'][0])], Hg, wr)
    drystone_wall(V, [(sw['x'][0], gg['W'][1]), (sw['x'][0], sw['y'][1])], Hg, wr)
    for (x, y) in ((141, gg['E'][0] - 2), (141, gg['E'][1] + 2)):
        banner(V, x, y, PZ, h=10, dirx=1)
    for (x, y) in ((gg['N'][0] - 1, 233), (gg['N'][1] + 1, 233), (gg['S'][0] - 1, 279), (gg['S'][1] + 1, 279)):
        lantern_post(V, x, y, PZ, h=4, arm=(0, 1 if y == 233 else -1))
    banner(V, 84, 190, PZ, h=12, dirx=-1)
    # spawn yard: only low cover (<= 2) inside the square
    hay_bale(V, 103, 241, PZ, True); hay_bale(V, 128, 270, PZ, False); hay_bale(V, 131, 241, PZ, True)
    V.box(108, 112, 268, 269, PZ - 1, PZ - 1, STONE)          # trough
    V.box(109, 111, 268, 269, PZ - 1, PZ - 1, SEA)            # water in the trough (coloured as water)
    # hay yard + cart by the barn
    hay_stack(V, 118, 197, PZ, wr); hay_stack(V, 118, 204, PZ, wr)
    cart(V, 126, 222, PZ, along_x=True)
    cart(V, 102, 282, PZ, along_x=True, load=PUMPKIN)
    # fields: NW (rows E-W), SW pumpkin patch, north-centre patch
    fields = FIELDS
    F['fields'] = fields
    for i, (x0, x1, y0, y1) in enumerate(fields):
        fr = np.random.default_rng(SEED + 100 + i)
        fence(V, [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0 + 6)], Hg, fr)
        for y in range(y0 + 2, y1 - 1, 3):
            for x in range(x0 + 2, x1 - 1):
                if fr.random() < 0.05:
                    pumpkin(V, x, y, Hg(x, y), size=int(fr.integers(0, 3)) if i != 3 else int(fr.integers(0, 2)))
                elif fr.random() < 0.22:
                    V.put(x, y, Hg(x, y) - 1, VINE)
        sx, sy = (x0 + x1) // 2, (y0 + y1) // 2
        scarecrow(V, sx, sy, Hg(sx, sy), fr, facing=(0, 1))
    # groves: dead orchards (rows) and autumn trees on the lobes and around the hamlet
    GROVES = [  # (x, y, kind)  kind: d = dead, a = autumn
        (62, 236, 'd'), (56, 254, 'd'), (64, 272, 'd'), (70, 222, 'a'), (72, 290, 'd'), (60, 300, 'a'),
        (66, 318, 'd'), (76, 334, 'a'), (52, 284, 'a'), (50, 240, 'a'),
        (138, 372, 'd'), (150, 396, 'd'), (166, 414, 'd'), (182, 430, 'a'), (204, 444, 'd'), (226, 448, 'a'),
        (120, 392, 'a'), (104, 372, 'd'),
        (112, 122, 'd'), (98, 140, 'a'), (128, 102, 'a'), (150, 88, 'd'), (176, 78, 'a'), (198, 96, 'd'),
        (218, 92, 'a'), (86, 168, 'a'), (80, 186, 'd'),
        (232, 96, 'd'), (196, 132, 'a'),
    ]
    for (x, y, kind) in GROVES:
        tr = np.random.default_rng(SEED + 7 * x + y)
        g = gz(x, y)
        if g > 50 or F['stairs'][x, y] or F['pit'][x, y]:
            continue
        leaves = None if kind == 'd' else [LEAF_RUST, LEAF_ORANGE, LEAF_BROWN, LEAF_RUST]
        dead_tree(V, x, y, g, int(tr.integers(10, 16)) if kind == 'd' else int(tr.integers(12, 17)), tr,
                  girth=2, leaves=leaves)
        if kind == 'a':
            leaf_litter(V, x, y, gz, tr, r=7)
    # vines + pumpkins on the rim lobes
    vr = np.random.default_rng(SEED + 9)
    for (x, y) in ((60, 200), (52, 320), (90, 360), (120, 400), (170, 446), (210, 456), (100, 110),
                   (140, 86), (190, 80), (56, 230)):
        vine_run(V, x, y, lambda a, b: gz(a, b), vr, length=30)
    # lanterns along routes
    for (x, y) in ((146, 162), (162, 128), (204, 104), (132, 318), (176, 382), (226, 414), (174, 290),
                   (214, 294)):
        lantern_post(V, x, y, gz(x, y), h=4, arm=(1, 0))

    # farmland walls (broken dry-stone parcel boundaries)
    for pts in ([(70, 150), (100, 140)], [(140, 362), (166, 394)], [(84, 360), (110, 362), (128, 380)],
                [(186, 120), (200, 150)], [(196, 400), (228, 404)]):
        drystone_wall(V, pts, Hg, np.random.default_rng(SEED + pts[0][0]), h=2, gap_p=0.12)
    scatter(V, F, gz)

    # ---------------- centre (authored whole on the axis; mirror keeps it symmetric)
    (ccx, ccy), cr = SPEC['clearing']
    standing_ring(V, ccx, ccy, SPEC['stone_ring_r'], 12, Hg, rng, skip=(0.0, math.pi))
    # fire pit
    for a in range(16):
        x = int(round(ccx - 0.5 + 3.5 * math.cos(a * math.pi / 8))); y = int(round(ccy - 0.5 + 3.5 * math.sin(a * math.pi / 8)))
        V.put(x, y, PZ - 1, STONE_DARK)
    V.box(ccx - 2, ccx + 1, ccy - 2, ccy + 1, PZ, PZ, EMBER)
    V.box(ccx - 1, ccx, ccy - 1, ccy, PZ - 1, PZ - 1, DEADWOOD)
    for (x, y) in ((236, 226), (228, 288), (232, 236)):
        pumpkin(V, x, y, PZ, size=1)
    hay_bale(V, 222, 282, PZ, True); hay_bale(V, 240, 222, PZ, False)
    for (x, y) in ((228, 246), (230, 268)):
        V.box(x, x, y, y, PZ - 4, PZ - 1, TIMBER)              # ritual stakes
        V.put(x, y, PZ - 5, STRAW)
    # vine-tunnel trellis arches over the centre path between the eyes
    for y in range(176, 204, 6):
        for x in (251, 261):
            V.box(x, x, y, y, PZ - 6, PZ - 1, TIMBER)
        V.box(251, 261, y, y, PZ - 6, PZ - 6, TIMBER)
        for x in range(251, 262):
            if (x + y) % 3:
                V.put(x, y, PZ - 7, VINE)
        V.put(251, y, PZ - 3, VINE); V.put(261, y, PZ - 4, VINE)
    for y in range(176, 203):
        if y % 6:
            V.put(251, y, PZ - 6, VINE); V.put(261, y, PZ - 6, VINE)

    # north: Wicker King on its plinth + standing stones (the stem is added after mirroring)
    kx, ky = SPEC['king']
    kg = int(np.median(H[kx - 16:kx + 16, ky - 12:ky + 12]))
    wicker_king(V, kx, ky, kg)
    standing_ring(V, kx, ky - 2, 26, 14, gz, rng, skip=(math.pi / 2,))
    # south: giant carved pumpkins + scarecrow in the south patch
    pumpkin(V, 248, 424, gz(248, 424), size=3, carved=True, face_dir=(0, -1))
    pumpkin(V, 222, 400, gz(222, 400), size=2, carved=True, face_dir=(0, -1))

    # pits
    pit_furnish(V, F, rng)
    shoring(V, F)
    for pts in ([(97, 146), (97, 186)], [(93, 322), (93, 352)], [(102, 188), (130, 188)], [(176, 404), (176, 432)],
                [(194, 306), (194, 326)], [(84, 322), (84, 354)]):
        hedge(V, pts, Hg, np.random.default_rng(SEED + pts[0][1] * 3 + pts[0][0]))
    fp = fold_x(F['floor_plank'])
    xs, ys = np.nonzero(fp)
    V.m[xs, ys, H[xs, ys]] = PLANK

    # piers
    for i, info in enumerate(piers):
        pier_deck(V, info, rng, boat_side=1 if i % 2 else -1)

    # offshore rocks (west half; mirrored)
    for (x, y, r, h, deco) in ((34, 146, 6, 8, True), (45, 136, 3, 4, False), (28, 160, 3, 3, False),
                               (26, 322, 5, 6, True), (36, 336, 3, 3, False), (94, 448, 6, 9, True),
                               (107, 455, 3, 4, False), (166, 52, 5, 7, True), (178, 44, 3, 3, False)):
        orr = np.random.default_rng(SEED + x * 3 + y)
        offshore_rock(V, x, y, orr, r, h)
        if deco:
            pumpkin(V, x - 1, y, V.ground(x - 1, y), size=1)
            lantern_post(V, x + 2, y - 2, V.ground(x + 2, y - 2), h=3)

    # ---------------- mirror the left half onto the right (x' = 512 - x)
    V.m[257:] = V.m[255:0:-1]
    # asymmetric cosmetic landmark placed after mirroring: the curling stem in the north notch
    before = V.m.copy()
    sx, sy = SPEC['stem']
    stem(V, sx, sy, gz(sx, sy), np.random.default_rng(SEED + 3))
    diff = np.nonzero((V.m != before).any(axis=2))
    F['cosmetic_bbox'] = [int(diff[0].min()), int(diff[0].max()), int(diff[1].min()), int(diff[1].max())]
    F['cleanup'] = cleanup(V, F['cosmetic_bbox'])
    if sky:                                   # optional floating sky layer (placed last; see wkh_sky.py)
        from wkh_sky import add_sky
        add_sky(V, F)
    return V, F, piers


def cleanup(V, cbox=None, max_small=8, iters=4):
    """Drop tiny floating decoration (stray leaves/twigs) and raise terrain cells that would trap a player."""
    from wkh_check import Nav
    from scipy.sparse.csgraph import dijkstra
    st = ndi.generate_binary_structure(3, 1)
    solid = V.m > 0
    solid[:, :, 63] = True
    lab, n = ndi.label(solid, structure=st)
    grounded = set(np.unique(lab[:, :, 62:][solid[:, :, 62:]]).tolist())
    sizes = ndi.sum(solid, lab, index=np.arange(1, n + 1))
    removed = 0
    for i in range(1, n + 1):
        if i not in grounded and sizes[i - 1] <= max_small:
            V.m[lab == i] = 0
            removed += int(sizes[i - 1])
    terrain_mats = {SOIL, ASH, PIT_ROCK, SHORE_ROCK, STAIR, SKIN, ROCK, PATH, EMBER, CLEARING, DIRT, PLANK}
    raised = 0
    for it in range(iters):
        solid = V.m > 0
        solid[:, :, 63] = True
        nav = Nav(solid)
        pl = nav.nodes_in(0, 511, 0, 511, PZ, PZ)
        db = dijkstra(nav.G.T.tocsr(), directed=True, unweighted=True, indices=pl[::5], min_only=True)
        p = nav.xyz
        trap = (p[:, 2] < 62) & (p[:, 2] >= PZ) & ~np.isfinite(db)
        fixed = 0
        for x, y, z in p[trap]:
            in_cos = cbox is not None and cbox[0] <= x <= cbox[1] and cbox[2] <= y <= cbox[3]
            sym = in_cos or (V.m[512 - x if x > 0 else 0, y, z] == V.m[x, y, z])
            if V.m[x, y, z] in terrain_mats and V.m[x, y, z - 1] == 0 and sym:
                V.m[x, y, z - 1] = V.m[x, y, z]
                fixed += 1
        raised += fixed
        if not fixed:
            break
    return {'tiny_floating_removed_voxels': removed, 'trap_cells_raised': raised}


if __name__ == '__main__':
    import time
    t = time.time()
    V, F, piers = build(graybox='--graybox' in sys.argv)
    print('built', time.time() - t)
