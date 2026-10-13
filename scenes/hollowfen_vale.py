"""HOLLOWFEN VALE - one haunted village in the middle of rolling hills. Babel + CTF (stock piqueserver 1.4.2).

Variant of Hollowfen requested 2026-10-13: a single central village (it may spread beyond the middle), blue and red
spawns on hills either side, NO authored buildings/props inside the tower build zones (the Babel corridors between
each spawn and the platform), rolling hills.

Layout rules
  * tower build zones: x 139-212 (and mirror 300-373), y 228-284 - open meadow only (checked);
  * near the platform (within ~28 voxels of its footprint, outside the zones) only low props (<= 6 tall), so the
    village does not hand out free scaffolding; the church sits far enough north that its belfry is no shortcut;
  * spawn squares (stock Babel bases 118/394, +-20) on hilltops, clear of everything; CTF spawns + tents there too;
  * CTF intel on each side's pumpkin farm behind its spawn hill.
West half authored and mirrored (x' = 512 - x); central landmarks (church, mausoleum) are symmetric about x = 256
and the church is pasted after mirroring (its spiral stair is not symmetric, but it is equidistant from both sides).

Run: python scenes/hollowfen_vale.py out/hollowfen_vale
"""
import json
import os
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aosmap.scene import Scene                                               # noqa: E402
from aosmap import art                                                       # noqa: E402
from scenes import hollowfen as HF                                           # noqa: E402
from scenes import hollowfen_props as P                                      # noqa: E402
from scenes.hollowfen_art import materials, place_house, church_full, plant_forest   # noqa: E402

SEED = 1031 + 7
G = 57
FOG = (118, 92, 124)

SPEC = {
    'mode': 'babel + ctf (stock piqueserver 1.4.2)',
    'script_constants': HF.SPEC['script_constants'],
    'ground_z': G,
    'spawn_square': {'x': (98, 138), 'y': (236, 276)},
    'spawn_hill': {'center': (118, 256), 'top_z': 47, 'radius': 42},
    'tower_zone': {'x': (139, 212), 'y': (228, 284)},           # mirrored: x 300..373
    'low_zone_margin': 28,
    'green': {'x': (220, 255), 'y': (214, 298)},
    'church': {'x': (238, 274), 'y': (146, 196)},               # pasted whole after mirroring (centred on x 256)
    'churchyard': {'x': (222, 255), 'y': (112, 208)},
    'cemetery': {'x': (222, 255), 'y': (316, 392), 'z': G - 1, 'mausoleum_y': (346, 362)},
    'farm': {'x': (26, 78), 'y': (238, 274), 'intel': (52, 256)},
    'ctf': {'blue_flag': (52, 256), 'blue_base': (118, 256)},
    'ponds': [{'center': (64, 168), 'r': (18, 11)}, {'center': (64, 344), 'r': (18, 11)}],
    'witch_huts': [(36, 106), (36, 406)],
    'lanes': {
        'main': ([(216, 100), (216, 412)], 5, 'cobble'),
        'n1': ([(142, 205), (216, 205)], 5, 'cobble'),
        'n2': ([(150, 172), (216, 172)], 4, 'cobble'),
        'n3': ([(160, 138), (216, 138)], 4, 'dirt'),
        's1': ([(142, 307), (216, 307)], 5, 'cobble'),
        's2': ([(150, 340), (216, 340)], 4, 'cobble'),
        's3': ([(160, 374), (216, 374)], 4, 'dirt'),
        'spawn_n': ([(118, 234), (120, 216), (142, 205)], 4, 'dirt'),
        'spawn_s': ([(118, 278), (120, 296), (142, 307)], 4, 'dirt'),
        'farm': ([(28, 256), (97, 256)], 5, 'dirt'),
        'church_walk': ([(216, 142), (255, 142)], 4, 'cobble'),
        'cem_walk': ([(216, 330), (230, 330)], 4, 'cobble'),
        'outer_n': ([(120, 216), (94, 186), (84, 140), (108, 100), (160, 88), (216, 100)], 3, 'dirt'),
        'outer_s': ([(120, 296), (94, 326), (84, 372), (108, 412), (160, 424), (216, 412)], 3, 'dirt'),
    },
    'witches': [(70, 70, 18), (196, 52, 16), (448, 76, 21), (80, 446, 17), (318, 466, 15), (452, 414, 19)],
    'fog': FOG,
}


def mirror(s):
    s.mat[257:512] = s.mat[1:256][::-1]
    s.mat[256] = s.mat[255]


class Layout:
    def __init__(self):
        X, Y = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
        self.X, self.Y = X, Y
        west = X <= 255
        self.west = west
        rng = np.random.default_rng(SEED)
        box = lambda b: (X >= b['x'][0]) & (X <= b['x'][1]) & (Y >= b['y'][0]) & (Y <= b['y'][1])  # noqa: E731
        self.lane = {n: (HF.poly_dist(p, X, Y) <= w / 2.0) & west for n, (p, w, s_) in SPEC['lanes'].items()}
        self.cobble = np.zeros(X.shape, bool); self.dirt = np.zeros(X.shape, bool)
        for n, (p, w, surf) in SPEC['lanes'].items():
            (self.cobble if surf == 'cobble' else self.dirt)[...] |= self.lane[n]
        self.roads = self.cobble | self.dirt
        self.square = box(SPEC['spawn_square'])
        z = SPEC['tower_zone']
        self.zone = box(z)
        self.zone_both = self.zone | ((512 - X >= z['x'][0]) & (512 - X <= z['x'][1]) & (Y >= z['y'][0]) & (Y <= z['y'][1]))
        sc = SPEC['script_constants']
        dx = np.maximum(0, np.maximum(sc['platform_x'][0] - X, X - sc['platform_x'][1]))
        dy = np.maximum(0, np.maximum(sc['platform_y'][0] - Y, Y - sc['platform_y'][1]))
        self.low = (np.hypot(dx, dy) <= SPEC['low_zone_margin']) & west & ~self.zone
        self.green = box(SPEC['green'])
        self.church = box(SPEC['church'])
        self.churchyard = box(SPEC['churchyard']) & ~self.church
        self.cem = box(SPEC['cemetery'])
        self.farm = box(SPEC['farm'])
        self.pond_d = np.full(X.shape, 9.0)
        for p in SPEC['ponds']:
            (cx, cy), (rx, ry) = p['center'], p['r']
            n = (art.fbm(X, Y, None, scale=9, octaves=2, seed=SEED + cy) - 0.5) * 0.3
            self.pond_d = np.minimum(self.pond_d, np.sqrt(((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2) + n)
        self.pond = (self.pond_d < 1.0) & west
        self.village = west & (X >= 140) & (X <= 255) & (Y >= 100) & (Y <= 412) & ~self.zone
        self.plots = self._plots(rng)
        pm = np.zeros(X.shape, bool)
        for p in self.plots:
            pm[p['x'][0]:p['x'][1] + 1, p['y'][0]:p['y'][1] + 1] = True
        self.plot_mask = pm

    def _plots(self, rng):
        X, Y = self.X, self.Y
        blocked = (ndimage.binary_dilation(self.roads, iterations=1) | ndimage.binary_dilation(self.zone, iterations=3)
                   | self.low | self.green | ndimage.binary_dilation(self.church | self.churchyard | self.cem, iterations=2)
                   | ndimage.binary_dilation(self.square, iterations=4) | self.farm | (X > 212) | (X < 140)
                   | ndimage.binary_dilation(self.pond, iterations=3))
        rows = []
        for n in ('n1', 'n2', 'n3', 's1', 's2', 's3'):
            (poly, w, _) = SPEC['lanes'][n]
            ly = poly[0][1]
            half = w // 2
            rows += [((142, 210), ly - half - 3, -1), ((142, 210), ly + half + 3, +1)]
        plots = []
        for (xa, xb), edge, side in rows:
            x = xa + int(rng.integers(0, 4))
            while x < xb:
                w = int(rng.integers(9, 14)); d = int(rng.integers(7, 10))
                if rng.random() < 0.12:
                    x += w; continue
                y0, y1 = (edge - d + 1, edge) if side < 0 else (edge, edge + d - 1)
                x0, x1 = x, x + w - 1
                if x1 <= xb and not blocked[x0 - 1:x1 + 2, y0 - 1:y1 + 2].any():
                    plots.append({'x': (x0, x1), 'y': (y0, y1), 'front': 'n' if side > 0 else 's',
                                  'storeys': int(rng.choice([2, 2, 2, 3])), 'seed': int(rng.integers(1 << 30))})
                    blocked[x0 - 2:x1 + 3, y0 - 2:y1 + 3] = True
                x += w + int(rng.integers(3, 7))
        # hillside cottages beyond the village (on flattened pads)
        for (cx, cy) in ((96, 206), (150, 112), (96, 306), (150, 400), (190, 104), (190, 408)):
            w, d = int(rng.integers(9, 12)), int(rng.integers(7, 9))
            x0, y0 = cx - w // 2, cy - d // 2
            if not blocked[x0 - 1:x0 + w + 1, y0 - 1:y0 + d + 1].any() or (cx < 140):
                if self.zone[x0 - 3:x0 + w + 3, y0 - 3:y0 + d + 3].any() or self.square[x0 - 4:x0 + w + 4, y0 - 4:y0 + d + 4].any():
                    continue
                if self.roads[x0 - 1:x0 + w + 1, y0 - 1:y0 + d + 1].any():
                    continue
                plots.append({'x': (x0, x0 + w - 1), 'y': (y0, y0 + d - 1), 'front': 'n' if cy > 256 else 's',
                              'storeys': 2, 'seed': int(rng.integers(1 << 30)), 'cottage': True})
                blocked[x0 - 2:x0 + w + 2, y0 - 2:y0 + d + 2] = True
        return plots


def terrain(L):
    """Rolling hills + spawn hill + flattened village / farm / pads; zones are a smooth meadow ramp."""
    X, Y = L.X, L.Y
    hills = 57 - 11 * art.fbm(X, Y, None, scale=120, octaves=4, seed=SEED + 1)
    edge = np.minimum.reduce([X, Y, 511 - Y]).astype(float)
    hills -= np.clip((30 - edge) / 30.0, 0, 1) ** 1.5 * 12
    sh = SPEC['spawn_hill']; (hx, hy) = sh['center']
    d = np.hypot(X - hx, Y - hy)
    dome = sh['top_z'] + 11 * (d / sh['radius']) ** 2
    H = np.where(d < sh['radius'], np.minimum(hills, dome), hills)
    # flats: (mask, z) blended outward over 16 voxels
    flats = []
    vill = L.village | L.green | L.church | L.churchyard | L.cem | ndimage.binary_dilation(L.plot_mask, iterations=4)
    vill |= ndimage.binary_dilation(L.roads & (X >= 140), iterations=2)
    flats.append((vill & ~L.zone, G))
    fz = int(round(float(H[SPEC['farm']['intel']])))
    flats.append((L.farm | ndimage.binary_dilation(L.lane['farm'] & (X < 98), iterations=2), fz))
    for p in L.plots:
        if p.get('cottage'):
            (x0, x1), (y0, y1) = p['x'], p['y']
            m = np.zeros(X.shape, bool); m[x0 - 2:x1 + 3, y0 - 2:y1 + 3] = True
            flats.append((m, int(round(float(H[(x0 + x1) // 2, (y0 + y1) // 2])))))
    out = H.copy()
    for m, z in flats:
        dist = ndimage.distance_transform_edt(~m)
        t = np.clip(dist / 16.0, 0, 1); t = t * t * (3 - 2 * t)
        out = np.where(dist < 16, z + (out - z) * t, out)
    # tower zone: smooth ramp from the spawn hill down to the village level (no noise, mirrored)
    z0 = float(dome[SPEC['tower_zone']['x'][0], hy])
    zx = SPEC['tower_zone']['x']
    ramp = z0 + (G - z0) * np.clip((X - zx[0]) / 31.0, 0, 1)                      # meadow rises to the hill
    zone_soft = ndimage.distance_transform_edt(~L.zone)
    t = np.clip(zone_soft / 8.0, 0, 1)
    out = np.where(zone_soft < 8, ramp + (out - ramp) * t, out)
    cm = SPEC['cemetery']
    out = np.where(L.cem, cm['z'], out)
    return np.clip(np.rint(out), 24, 62).astype(int)


def ground(s, L, m, H):
    X, Y = L.X, L.Y
    west = L.west
    top_mat = np.where(L.village | L.green | L.zone | L.farm | L.square, m['grass'], m['forest'])
    top_mat = np.where(L.cem, m['cem'], top_mat)
    for z in range(24, 63):
        sel = west & (z >= H)
        s.mat[:, :, z][sel] = np.where(z == H, top_mat, np.where(z < H + 4, m['soil'], m['rock']))[sel]
    for msk, mat in ((L.cobble, m['cobble']), (L.dirt, m['dirt'])):
        d = np.where(msk & west & ~L.zone)
        s.mat[d[0], d[1], H[d]] = mat
    from aosmap.art import PatternShader
    from scenes.hollowfen_art import _h

    def green_fn(x, y, z):
        r = np.maximum(np.abs(x - 256), np.abs(y - 256) * 0.6)
        return np.where((r.astype(int) % 9 == 0), 3, _h(x // 3, y // 3, 3))
    from aosmap.scene import Material
    m_green = s.material(Material('green_flags', (128, 128, 128),
                                  shader=PatternShader(['#706c78', '#7b7682', '#65616d', '#5a3d32'], green_fn, occ_dark=0.3)))
    d = np.where(L.green & west)
    s.mat[d[0], d[1], H[d]] = m_green
    d = np.where(L.farm & west)
    s.mat[d[0], d[1], H[d]] = m['farm']
    # ponds: stepped mud banks to open water (z 62 air)
    depth = np.clip(np.rint((1.0 - L.pond_d) * 12), 0, 6).astype(int)
    for x, y in zip(*np.nonzero(L.pond & (depth > 0))):
        h = min(int(H[x, y]) + int(depth[x, y]), 62)
        s.mat[x, y, :h] = 0
        s.mat[x, y, h] = m['bank']
    water = L.pond & (depth >= 6)
    s.mat[water, :63] = 0
    return water


def build(stage='art'):
    L = Layout()
    s = Scene('hollowfen_vale', seed=SEED)
    m = materials(s)
    X, Y = L.X, L.Y
    west = L.west
    rng = np.random.default_rng(SEED + 100)
    H = terrain(L)
    ground(s, L, m, H)
    counts = {}

    # ---------------------------------------------------------------- houses
    for p in L.plots:
        (x0, x1), (y0, y1) = p['x'], p['y']
        fz = int(H[(x0 + x1) // 2, (y0 + y1) // 2])
        place_house(s, m, p, floor_z=fz)
    counts['houses_west'] = len(L.plots)

    # ---------------------------------------------------------------- churchyard + cemetery (west half, mirrored)
    cm = SPEC['cemetery']; cz = cm['z']
    cem_ring = L.cem & ~ndimage.binary_erosion(L.cem | (X > 255), iterations=1)
    cem_ring &= ~((X == cm['x'][0]) & (np.abs(Y - 330) <= 2))                       # west gate (cem_walk)
    cem_ring &= ~((X >= 250) & (Y == cm['y'][0]))                                    # north gate (from the green)
    s.mat[cem_ring, cz - 2:cz] = m['cemwall']
    for (gx, gy) in ((cm['x'][0], 327), (cm['x'][0], 333), (249, cm['y'][0])):       # gate piers + lanterns
        s.mat[gx, gy, cz - 3:cz] = m['cemwall']; s.mat[gx, gy, cz - 4] = m['glow']
    my0, my1 = cm['mausoleum_y']; mx0 = 246
    s.box(mx0, 255, my0, my1, cz - 7, cz - 1, m['marble'])
    s.carve(mx0 + 1, 255, my0 + 1, my1 - 1, cz - 6, cz - 1)
    s.box(mx0 - 1, 255, my0 - 1, my1 + 1, cz - 8, cz - 8, m['marble_dark'])
    for k in range(4):
        s.box(mx0 + k, 255, my0 + k, my1 - k, cz - 9 - k, cz - 9 - k, m['marble_dark'] if k % 2 else m['marble'])
    s.box(254, 255, (my0 + my1) // 2 - 1, (my0 + my1) // 2 + 1, cz - 17, cz - 13, m['marble_dark'])
    s.mat[255, (my0 + my1) // 2, cz - 19:cz - 17] = m['marble_dark']
    yc = (my0 + my1) // 2
    s.box(mx0 - 3, mx0 - 1, yc - 5, yc + 5, cz - 1, cz - 1, m['marble'])
    for py in (yc - 5, yc - 2, yc + 2, yc + 5):
        s.mat[mx0 - 3, py, cz - 7:cz - 1] = m['marble']
    s.box(mx0 - 3, mx0 - 1, yc - 6, yc + 6, cz - 8, cz - 8, m['marble_dark'])
    for k in range(3):
        s.box(mx0 - 3, mx0 - 3, yc - 5 + 2 * k, yc + 5 - 2 * k, cz - 9 - k, cz - 9 - k, m['marble'])
    s.carve(mx0, mx0, yc - 2, yc + 2, cz - 5, cz - 1)
    s.mat[mx0, yc - 2:yc + 3, cz - 6] = m['iron']
    paths = L.cem & west & ((np.abs(Y - 330) <= 1) | (X >= 252))
    paths &= ~((X >= mx0 - 3) & (Y >= my0 - 1) & (Y <= my1 + 1))
    s.mat[paths & (s.mat[:, :, cz] == m['cem']), cz] = m['gravel']
    used = ndimage.binary_dilation(paths, iterations=1) | ((X >= mx0 - 5) & (Y >= my0 - 3) & (Y <= my1 + 3))
    used |= L.cem & ~ndimage.binary_erosion(L.cem | (X > 255), iterations=2)
    used |= L.churchyard & ~ndimage.binary_erosion(L.churchyard | (X > 255), iterations=2)
    for (tx, ty) in ((228, 324), (232, 384), (244, 338), (226, 120), (230, 200)):
        art.stamp(s, P.dead_tree(int(rng.integers(1 << 30)), m['deadwood'], height=int(rng.integers(8, 12))), tx, ty,
                  int(np.argmax(s.mat[tx, ty] > 0)), replace_air_only=True)
        used[tx - 4:tx + 5, ty - 4:ty + 5] = True
    kinds = ['slab', 'slab', 'slab', 'cross', 'cross', 'obelisk', 'tomb', 'celtic']
    n_g = 0

    def graves_in(mask, zf, x_range, y_range, density=0.92, step=7):
        nonlocal n_g
        for gx in range(*x_range, step):
            for gy in range(*y_range, 5):
                jx = gx + int(rng.integers(-1, 2))
                if not mask[jx - 1:jx + 5, gy - 2:gy + 3].all() or used[jx - 1:jx + 5, gy - 2:gy + 3].any() \
                        or rng.random() > density:
                    continue
                kind = kinds[int(rng.integers(0, len(kinds)))]
                art.stamp(s, P.headstone(int(rng.integers(1 << 30)), m, kind), jx, gy, zf, replace_air_only=True)
                if kind != 'tomb':
                    sub = s.mat[jx + 1:jx + 5, gy - 1:gy + 2, zf - 1]
                    s.mat[jx + 1:jx + 5, gy - 1:gy + 2, zf - 1] = np.where(sub == 0, m['mound'], sub)
                used[jx:jx + 5, gy - 2:gy + 3] = True
                n_g += 1
    graves_in(L.cem & west, cz, (cm['x'][0] + 3, 252), (cm['y'][0] + 4, cm['y'][1] - 2))
    # churchyard graves (west of the church, north of the green) - G level
    cy_ok = L.churchyard & ~ndimage.binary_dilation(L.roads, iterations=2) & ~ndimage.binary_dilation(L.church, iterations=2)
    graves_in(cy_ok, G, (224, 238), (114, 206), density=0.8)
    graves_in(cy_ok, G, (238, 254), (114, 142), density=0.8)          # north of the church walk
    graves_in(cy_ok, G, (238, 254), (199, 208), density=0.8)          # between tower and green
    counts['graves_west'] = n_g

    # ---------------------------------------------------------------- the green (under the platform): low props only
    # market stalls with striped awnings, pumpkin piles, hay, lamp posts, a giant jack-o'-lantern at the centre
    def stall(x, y, cloth):
        s.box(x, x + 5, y, y + 3, G - 2, G - 2, m['timber'])                     # counter
        for (px, py) in ((x, y), (x + 5, y), (x, y + 3), (x + 5, y + 3)):
            s.mat[px, py, G - 5:G] = m['timber']
        for i in range(6):
            s.mat[x + i, y - 1:y + 5, G - 6] = cloth if i % 2 == 0 else m['barn_trim']   # awning
        for i in range(1, 5):
            art.stamp(s, P.pumpkin(int(rng.integers(1 << 30)), m, 1), x + i, y + 1, G - 2, replace_air_only=True)
    for (sx_, sy_, c) in ((224, 220, m['barn']), (224, 288, m['roofs'][1]), (236, 222, m['roofs'][3]),
                          (236, 286, m['barn'])):
        stall(sx_, sy_, c)
    for (hx, hy) in ((230, 240), (230, 270), (246, 232), (246, 280)):
        s.box(hx, hx + 1, hy, hy + 2, G - 2, G - 1, m['hay'])
        art.stamp(s, P.pumpkin(int(rng.integers(1 << 30)), m, 2, lantern=True), hx + 2, hy, G, replace_air_only=True)
    lamp = P.lamp_post(m)
    lamp_pts = [(219, 214), (219, 298), (219, 240), (219, 272)]
    for y in range(110, 410, 18):
        if not (226 <= y <= 286):
            lamp_pts.append((213, y))
    for (lx, ly) in lamp_pts:
        tz = int(np.argmax(s.mat[lx, ly] > 0))
        if s.mat[lx, ly, tz - 6:tz].max() == 0 and not L.zone[lx, ly]:
            art.stamp(s, lamp, lx, ly, tz, replace_air_only=True)

    # ---------------------------------------------------------------- spawn camps: team banners outside the squares
    from aosmap.scene import Material
    m_blue = s.material(Material('banner_blue', (47, 79, 168), top=(57, 92, 186)))
    m_red = s.material(Material('banner_red', (168, 47, 47), top=(186, 60, 57)))
    m_gold = s.material(Material('banner_gold', (190, 150, 60)))
    s.markers['banner_mats'] = (m_blue, m_red)
    for (bx, by) in ((96, 232), (96, 280), (136, 232), (136, 280), (84, 246), (84, 266)):
        tz = int(np.argmax(s.mat[bx, by] > 0))
        s.mat[bx, by, tz - 9:tz] = m['iron']
        s.mat[bx - 1:bx + 2, by, tz - 9] = m['iron']
        s.mat[bx - 1:bx + 2, by, tz - 8:tz - 4] = m_blue
        s.mat[bx, by, tz - 10] = m_gold

    # ---------------------------------------------------------------- farm (CTF intel) behind the spawn hill
    f = SPEC['farm']; fz = int(H[f['intel']])
    s.box(30, 48, 262, 272, fz - 7, fz - 1, m['barn']); s.carve(31, 47, 263, 271, fz - 6, fz - 1)
    for k in range(7):
        y_lo, y_hi = 261 + (k if k < 3 else 3 + (k - 3) * 2), 273 - (k if k < 3 else 3 + (k - 3) * 2)
        if y_lo > y_hi:
            break
        z = fz - 8 - k
        s.box(29, 49, y_lo, y_lo + 1, z, z, m['roofs'][3]); s.box(29, 49, y_hi - 1, y_hi, z, z, m['roofs'][3])
        if y_lo + 2 <= y_hi - 2:
            s.box(30, 30, y_lo + 2, y_hi - 2, z, z, m['barn']); s.box(48, 48, y_lo + 2, y_hi - 2, z, z, m['barn'])
    s.carve(36, 42, 262, 262, fz - 5, fz - 1)
    s.box(35, 43, 262, 262, fz - 6, fz - 6, m['barn_trim'])
    s.mat[35, 262, fz - 6:fz] = m['barn_trim']; s.mat[43, 262, fz - 6:fz] = m['barn_trim']
    fh = P.house(SEED + 7, 13, 10, 2, m, m['plasters'][0], m['roofs'][0], ridge='x')
    art.stamp(s, P.Prefab(fh.a[:, ::-1, :], origin=(fh.origin[0], fh.a.shape[1] - 1 - fh.origin[1])), 30, 250, fz,
              replace_air_only=True)
    fx, fy = f['intel']
    n_p = 0
    for px in range(50, 78, 3):
        for py in list(range(240, 251, 3)) + list(range(262, 273, 3)):
            if abs(px - fx) <= 3 and abs(py - fy) <= 3:
                continue
            if rng.random() < 0.55:
                sz = int(rng.choice([1, 1, 2, 2, 3]))
                art.stamp(s, P.pumpkin(int(rng.integers(1 << 30)), m, size=sz, lantern=(sz >= 2 and rng.random() < 0.3)),
                          px, py, fz, replace_air_only=True)
                n_p += 1
    for (sx_, sy_) in ((60, 244), (72, 268)):
        art.stamp(s, P.scarecrow(0, m), sx_, sy_, fz, replace_air_only=True)
    counts['field_pumpkins_west'] = n_p

    # ---------------------------------------------------------------- witch's huts (easter egg) in forest clearings
    for (hx0, hy0) in SPEC['witch_huts']:
        hz = int(np.median(H[hx0 - 6:hx0 + 7, hy0 - 6:hy0 + 7]))
        for x in range(hx0 - 8, hx0 + 9):
            for y in range(hy0 - 8, hy0 + 9):
                if (x - hx0) ** 2 + (y - hy0) ** 2 <= 64:
                    s.mat[x, y, :hz] = 0
                    s.mat[x, y, hz:63] = np.where(s.mat[x, y, hz:63] == 0, m['soil'], s.mat[x, y, hz:63])
                    s.mat[x, y, hz] = m['forest']
        hut = P.house(SEED + 13 + hy0, 9, 7, 1, m, m['plasters'][4], m['roofs'][2], ridge='y', lit=1.0)
        art.stamp(s, hut, hx0 - 4, hy0 + 3, hz, replace_air_only=True)
        art.stamp(s, P.cauldron(m), hx0, hy0 + 7, hz, replace_air_only=True)

    # ---------------------------------------------------------------- forest + scattered village trees
    notree = (ndimage.binary_dilation(L.roads, iterations=2) | ndimage.binary_dilation(L.plot_mask, iterations=3)
              | L.zone | ndimage.binary_dilation(L.zone, iterations=2) | L.low | L.green | L.church | L.churchyard
              | L.cem | L.farm | ndimage.binary_dilation(L.square, iterations=6) | ndimage.binary_dilation(L.pond, iterations=1)
              | (X > 255) | (X < 1))
    for (hx0, hy0) in SPEC['witch_huts']:
        notree |= (X - hx0) ** 2 + (Y - hy0) ** 2 <= 100
    # the village itself gets sparse orchard trees only: thin the candidates there
    village_thin = L.village & (art.value_noise(X, Y, None, scale=3, seed=SEED + 5) < 0.75)
    notree |= village_thin
    counts['trees_west'] = plant_forest(s, m, rng, notree, L.pond_d, X, Y)
    shore = west & (L.pond_d > 0.75) & (L.pond_d < 1.0)
    for x, y in np.argwhere(shore)[::3]:
        if rng.random() < 0.35:
            tz = int(np.argmax(s.mat[x, y] > 0))
            if tz < 63 and s.mat[x, y, tz] == m['bank'] and s.mat[x, y, tz - 3:tz].max() == 0:
                s.mat[x, y, tz - int(rng.integers(2, 4)):tz] = m['reed']

    mirror(s)
    # east banners are red (cosmetic only: same geometry)
    east = X > 256
    sub = s.mat[257:, :, :]
    sub[sub == m_blue] = m_red

    # ---------------------------------------------------------------- church: pasted whole, centred on x = 256
    tmp = Scene('tmp_church', seed=SEED)
    mt = materials(tmp)
    assert mt['church'] == m['church']
    church_full(tmp, mt)
    c1 = HF.SPEC['church']
    lx0, lx1 = c1['nave_x'][0] - 3, c1['tower_x'][1] + 3
    ly0, ly1 = c1['nave_y'][0] - 4, c1['nave_y'][1] + 4
    block = tmp.mat[lx0:lx1 + 1, ly0:ly1 + 1, :].transpose(1, 0, 2)                  # (y_local -> x, x_local -> y)
    wx0, wy0 = ly0, lx0                                                               # world x = local y, world y = local x
    region = s.mat[wx0:wx0 + block.shape[0], wy0:wy0 + block.shape[1], :]
    region[block > 0] = block[block > 0]
    # clear the church interior / doorway volumes of anything the terrain left (floor is G everywhere there)
    s.markers['church_tower'] = (c1['nave_y'][0], c1['nave_y'][1], c1['tower_x'][0], c1['tower_x'][1])
    # giant jack-o'-lantern at the centre of the green (placed after mirroring, symmetric)
    big = np.zeros((7, 7, 6), np.uint8)                                              # giant jack-o'-lantern
    ii, jj, kk = np.meshgrid(np.arange(7), np.arange(7), np.arange(6), indexing='ij')
    body = ((ii - 3) ** 2 / 10.0 + (jj - 3) ** 2 / 10.0 + (kk - 2.4) ** 2 / 7.5) <= 1.0
    big[body] = m['pumpkin']
    big[body & (ii % 2 == 1)] = m['pumpkin_dark']
    big[3, 3, 5] = m['stem']
    big[0, 2:5, 3] = m['glow']; big[0, 1, 3] = m['glow']; big[0, 5, 3] = m['glow']      # eyes / mouth on -i face
    big[0, 2:5, 1] = m['glow']
    big[6] = np.where(big[0] == m['glow'], m['glow'], big[6])           # same face on +i
    big[0:2, :, 0] = np.where(big[0:2, :, 0] > 0, big[0:2, :, 0], 0)
    big[1:6, 1:6, 0] = m['pumpkin']
    from scipy import ndimage as _nd
    lab, _n = _nd.label(big > 0, structure=_nd.generate_binary_structure(3, 1))
    big[lab != lab[3, 3, 0]] = 0
    art.stamp(s, P.Prefab(big, origin=(3, 3)), 256, 256, G, replace_air_only=True)
    # ---------------------------------------------------------------- witches (requested floating scenery)
    for n, (wx, wy, wz) in enumerate(SPEC['witches']):
        pf = P.witch(SEED + 900 + n, m)
        a = np.rot90(pf.a, n % 4, axes=(0, 1))
        art.stamp(s, P.Prefab(a, origin=(a.shape[0] // 2, a.shape[1] // 2)), wx, wy, wz, replace_air_only=True)
    # painted bottom: dark pond water
    bot = np.zeros((512, 512, 3), float); bot[:] = (34, 46, 38)
    bot = bot * (0.8 + 0.4 * art.fbm(X, Y, None, scale=10, octaves=2, seed=SEED + 70)[..., None])
    bot[art.value_noise(X, Y, None, scale=3.0, seed=SEED + 71) > 0.78] = (58, 92, 44)
    s.paint_bottom(np.clip(bot, 0, 255).astype(np.uint8))
    s.markers['counts'] = counts
    s.markers['H'] = H
    return s, L


def metadata_txt(author='aosmap (vale art v1)'):
    from aosmap.meta import map_txt
    sq = SPEC['spawn_square']
    H = terrain(Layout())
    pts = [(x, y, int(H[x, y])) for x in range(sq['x'][0] + 4, sq['x'][1] - 3, 8) for y in range(sq['y'][0] + 4, sq['y'][1] - 3, 8)]
    spawns = {0: pts, 1: [(512 - x, y, z) for (x, y, z) in pts]}
    fx, fy = SPEC['ctf']['blue_flag']; bx, by = SPEC['ctf']['blue_base']
    ents = {0: (fx, fy, int(H[fx, fy])), 1: (512 - fx, fy, int(H[fx, fy])), 2: (bx, by, int(H[bx, by])),
            3: (512 - bx, by, int(H[bx, by]))}
    return map_txt(
        name='Hollowfen Vale', author=author, version='0.1',
        description='Haunted village in a valley of rolling hills at dusk. Babel or CTF; hilltop spawns, open tower meadows.',
        header='Generated by scenes/hollowfen_vale.py (seed %d). CTF: spawns + tents on the hilltop squares, intel on\n'
               "each side's pumpkin farm. Babel mode replaces these hooks with its own." % SEED,
        fog=FOG, extensions={'babel': True, 'water_damage': 0}, spawns=spawns, entities=ents)


if __name__ == '__main__':
    from aosmap.vxl import write_vxl
    out = sys.argv[1] if len(sys.argv) > 1 else 'out/hollowfen_vale'
    os.makedirs(out, exist_ok=True)
    s, L = build()
    data = write_vxl(s.to_voxelmap())
    open(os.path.join(out, 'hollowfen_vale.vxl'), 'wb').write(data)
    open(os.path.join(out, 'hollowfen_vale.txt'), 'w').write(metadata_txt())
    spec = dict(SPEC); spec['plots'] = L.plots
    json.dump(spec, open(os.path.join(out, 'spec.json'), 'w'), indent=1, default=list)
    print('written', len(data), 'bytes', s.markers['counts'], 'plots', len(L.plots))
