"""HOLLOWFEN - haunted fen village at dusk. Babel + CTF (stock piqueserver 1.4.2). LAYOUT / GRAYBOX.

Two mirrored villages (x' = 512 - x), each around its spawn square at the stock Babel base, with a church whose
bell tower faces the sky platform (Babel bridgehead, stair inside to the belfry), a walled cemetery with a
mausoleum in the middle under the platform (neutral ground / CTF midfield), two haunted bogs north and south
crossed by boardwalks (flank routes), forest everywhere else, and a pumpkin farm behind each village that holds
that team's intel in CTF. Terrain is solid down to z 62 and destructible (classic play, no protection script).

The layout (plots, lanes, church, cemetery...) is computed here once and shared by the art pass
(scenes/hollowfen_art.py), so the graybox and the final map have identical gameplay geometry.

Run: python scenes/hollowfen.py out/hollowfen_graybox
"""
import json
import os
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aosmap.scene import Scene, Material          # noqa: E402
from aosmap import art                            # noqa: E402

SEED = 1031
G = 57                     # village / cemetery ground: top voxel z (players stand on z 57, eye ~54.6)

SPEC = {
    'mode': 'babel + ctf (stock piqueserver 1.4.2)',
    'script_constants': {'platform_x': (206, 305), 'platform_y': (240, 271), 'platform_z': 1,
                         'intel': (256, 256), 'bases': ((118, 256), (394, 256)), 'spawn_half': 20},
    'ground_z': G,
    'square': {'x': (98, 138), 'y': (236, 276)},                 # = Babel spawn square, also CTF spawns
    'church': {'nave_x': (150, 182), 'nave_y': (248, 264), 'nave_wall_top_z': 45,
               'tower_x': (183, 193), 'tower_y': (251, 261), 'belfry_floor_z': 32},
    'cemetery': {'x': (210, 255), 'y': (198, 314), 'z': G - 1,
                 'mausoleum_x': (246, 255), 'mausoleum_y': (248, 264), 'gates_y': [(230, 236), (276, 282), (252, 260)]},
    'bogs': [{'center': (256, 132), 'r': (38, 22)}, {'center': (256, 380), 'r': (38, 22)}],
    'boardwalk_y': [(130, 133), (379, 382)],
    'farm': {'x': (26, 86), 'y': (238, 274), 'intel': (56, 256)},
    'ctf': {'blue_flag': (56, 256), 'blue_base': (118, 256)},    # mirrored for green
    'lanes': {   # (polyline, width, surface)
        'lane_n': ([(66, 233), (210, 233)], 5, 'cobble'),
        'lane_s': ([(66, 279), (210, 279)], 5, 'cobble'),
        'lane_w': ([(30, 256), (98, 256)], 5, 'dirt'),
        'lane_nn': ([(66, 205), (206, 205)], 4, 'dirt'),
        'lane_ss': ([(66, 307), (206, 307)], 4, 'dirt'),
        'lane_x': ([(66, 205), (66, 307)], 4, 'dirt'),
        'road_n': ([(118, 231), (118, 204), (126, 178), (150, 154), (186, 138), (220, 131)], 4, 'dirt'),
        'road_s': ([(118, 281), (118, 308), (126, 334), (150, 358), (186, 374), (220, 381)], 4, 'dirt'),
        'path_farm_n': ([(66, 205), (60, 186), (78, 168), (110, 164), (126, 178)], 3, 'dirt'),
        'path_farm_s': ([(66, 307), (60, 326), (78, 344), (110, 348), (126, 334)], 3, 'dirt'),
    },
    'witches': [(70, 92, 18), (196, 56, 16), (448, 84, 21), (86, 438, 17), (318, 462, 15), (452, 404, 19)],  # z = below the broom
    'fog': (118, 92, 124),
}

GRAY = {'grass': (110, 120, 90), 'forest': (80, 96, 70), 'soil': (120, 100, 80), 'rock': (110, 108, 112),
        'cobble': (150, 150, 150), 'dirt': (150, 120, 90), 'square': (110, 140, 190), 'house': (190, 170, 140),
        'roof': (90, 70, 80), 'church': (160, 160, 170), 'stair': (225, 205, 120), 'belfry': (200, 90, 70),
        'cem': (90, 110, 80), 'cemwall': (130, 130, 140), 'mausoleum': (170, 165, 175), 'farm': (170, 130, 70),
        'barn': (150, 70, 60), 'boardwalk': (140, 110, 80), 'bank': (100, 90, 70), 'witch': (200, 60, 200)}


# ---------------------------------------------------------------------------------------- helpers
def poly_dist(points, X, Y, step=0.5):
    pts = []
    for (x0, y0), (x1, y1) in zip(points[:-1], points[1:]):
        n = max(2, int(np.hypot(x1 - x0, y1 - y0) / step))
        t = np.linspace(0, 1, n, endpoint=False)
        pts.append(np.stack([x0 + (x1 - x0) * t, y0 + (y1 - y0) * t], 1))
    pts.append(np.array([points[-1]], float))
    from scipy.spatial import cKDTree
    d, _ = cKDTree(np.concatenate(pts)).query(np.stack([X.ravel(), Y.ravel()], 1))
    return d.reshape(X.shape)


def mirror(s):
    s.mat[257:512] = s.mat[1:256][::-1]
    s.mat[256] = s.mat[255]


class Layout:
    """Everything the graybox and the art pass share (west half, x <= 255)."""

    def __init__(self):
        X, Y = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
        self.X, self.Y = X, Y
        west = X <= 255
        rng = np.random.default_rng(SEED)
        # lanes
        self.lane = {}
        for name, (poly, w, surf) in SPEC['lanes'].items():
            self.lane[name] = (poly_dist(poly, X, Y) <= w / 2.0) & west
        self.cobble = np.zeros(X.shape, bool); self.dirt = np.zeros(X.shape, bool)
        for name, (poly, w, surf) in SPEC['lanes'].items():
            (self.cobble if surf == 'cobble' else self.dirt)[...] |= self.lane[name]
        self.roads = self.cobble | self.dirt
        sq = SPEC['square']; self.square = (X >= sq['x'][0]) & (X <= sq['x'][1]) & (Y >= sq['y'][0]) & (Y <= sq['y'][1])
        c = SPEC['church']
        self.nave = (X >= c['nave_x'][0]) & (X <= c['nave_x'][1]) & (Y >= c['nave_y'][0]) & (Y <= c['nave_y'][1])
        self.tower = (X >= c['tower_x'][0]) & (X <= c['tower_x'][1]) & (Y >= c['tower_y'][0]) & (Y <= c['tower_y'][1])
        cm = SPEC['cemetery']
        self.cem = (X >= cm['x'][0]) & (X <= 255) & (Y >= cm['y'][0]) & (Y <= cm['y'][1])
        f = SPEC['farm']
        self.farm = (X >= f['x'][0]) & (X <= f['x'][1]) & (Y >= f['y'][0]) & (Y <= f['y'][1])
        self.bog_d = np.full(X.shape, 9.0)
        for b in SPEC['bogs']:
            (cx, cy), (rx, ry) = b['center'], b['r']
            n = (art.fbm(X, Y, None, scale=14, octaves=2, seed=SEED + cy) - 0.5) * 0.35
            self.bog_d = np.minimum(self.bog_d, np.sqrt(((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2) + n)
        self.bog = (self.bog_d < 1.0) & west
        # churchyard: the strip between nave/tower and the cemetery wall, and beside the nave
        self.churchyard = west & (X >= 146) & (X <= 209) & (Y >= 238) & (Y <= 274) & ~self.nave & ~self.tower
        # village area: flat ground at G
        self.village = west & (X >= 58) & (X <= 209) & (Y >= 188) & (Y <= 324)
        self.flat = self.village | self.cem | self.farm | ndimage.binary_dilation(self.roads, iterations=2)
        # house plots (ground under every plot is flattened to G)
        self.plots = self._plots(rng)
        pm = np.zeros(X.shape, bool)
        for p in self.plots:
            pm[p['x'][0]:p['x'][1] + 1, p['y'][0]:p['y'][1] + 1] = True
        self.plot_mask = pm
        self.flat |= ndimage.binary_dilation(pm, iterations=4)

    def _plots(self, rng):
        X, Y = self.X, self.Y
        blocked = (ndimage.binary_dilation(self.roads, iterations=1) | ndimage.binary_dilation(self.square, iterations=2)
                   | ndimage.binary_dilation(self.nave | self.tower, iterations=3) | self.churchyard
                   | ndimage.binary_dilation(self.cem, iterations=3) | self.farm | (X > 255))
        plots = []
        rows = [  # (x range, lane edge y, side): houses whose front faces the lane
            ((70, 204), 228, -1), ((88, 146), 238, +1),    # lane_n: north side, south side (west of church)
            ((70, 204), 284, +1), ((88, 146), 274, -1),    # lane_s: south side, north side
            ((70, 204), 200, -1),                          # lane_nn: north side (back row, gardens behind)
            ((70, 204), 312, +1),                          # lane_ss: south side
        ]
        for (xa, xb), edge, side in rows:
            x = xa + int(rng.integers(0, 4))
            while x < xb:
                w = int(rng.integers(9, 14)); d = int(rng.integers(7, 10))
                if rng.random() < 0.15:                    # garden gap
                    x += w; continue
                if side < 0:
                    y0, y1 = edge - d + 1, edge
                else:
                    y0, y1 = edge, edge + d - 1
                x0, x1 = x, x + w - 1
                if x1 <= xb and not blocked[x0 - 1:x1 + 2, y0 - 1:y1 + 2].any():
                    plots.append({'x': (x0, x1), 'y': (y0, y1), 'front': 'n' if side > 0 else 's',
                                  'storeys': int(rng.choice([2, 2, 2, 3])), 'seed': int(rng.integers(1 << 30))})
                    blocked[x0 - 2:x1 + 3, y0 - 2:y1 + 3] = True
                x += w + int(rng.integers(3, 7))
        # outskirts along the forest roads (a few lonely cottages)
        for (cx, cy) in ((100, 196), (146, 170), (100, 316), (146, 342), (196, 150), (196, 362)):
            w, d = int(rng.integers(9, 12)), int(rng.integers(7, 9))
            x0, y0 = cx - w // 2, cy - d // 2
            if not blocked[x0 - 1:x0 + w + 1, y0 - 1:y0 + d + 1].any() and not self.bog[x0:x0 + w, y0:y0 + d].any():
                plots.append({'x': (x0, x0 + w - 1), 'y': (y0, y0 + d - 1), 'front': 'n' if cy > 256 else 's',
                              'storeys': 2, 'seed': int(rng.integers(1 << 30)), 'cottage': True})
                blocked[x0 - 2:x0 + w + 2, y0 - 2:y0 + d + 2] = True
        return plots


def terrain_heights(L):
    """Top-surface z for every column (west half; caller mirrors)."""
    X, Y = L.X, L.Y
    hills = 57 - 8 * art.fbm(X, Y, None, scale=90, octaves=4, seed=SEED + 1)          # forest: z 49..57
    edge = np.minimum.reduce([X, Y, 511 - Y]).astype(float)
    hills -= np.clip((34 - edge) / 34.0, 0, 1) ** 1.5 * 16                            # forested rim ridge
    d_flat = ndimage.distance_transform_edt(~L.flat)
    t = np.clip(d_flat / 18.0, 0, 1); t = t * t * (3 - 2 * t)
    H = G + (hills - G) * t
    H = np.where(L.cem, SPEC['cemetery']['z'], H)                                     # cemetery terrace (+1)
    return np.clip(np.rint(H), 20, 62).astype(int)


def ground(s, L, M):
    """Terrain solid to z 62 + surfaces (lanes, square, farm, cemetery terrace). Returns H."""
    X, Y = L.X, L.Y
    west = X <= 255
    H = terrain_heights(L)
    top_mat = np.where(L.flat, M['grass'], M['forest'])
    for z in range(20, 63):
        sel = west & (z >= H)
        s.mat[:, :, z][sel] = np.where(z == H, top_mat, np.where(z < H + 4, M['soil'], M['rock']))[sel]
    s.mat[L.cobble & west, G] = M['cobble']
    d = np.where(L.dirt & west)
    s.mat[d[0], d[1], H[d]] = M['dirt']
    s.mat[L.square, G] = M['square']
    s.mat[L.farm & west, G] = M['farm']
    s.mat[L.cem, SPEC['cemetery']['z']] = M['cem']
    return H


def bogs(s, L, M):
    """Bogs: stepped banks down to open water (air to z 62), boardwalks on posts to the bog floor."""
    X, Y = L.X, L.Y
    west = X <= 255
    depth = np.clip(np.rint((1.0 - L.bog_d) * 14), 0, 6).astype(int)              # 0..6 below G
    inbog = L.bog & (depth > 0)
    for x, y in zip(*np.nonzero(inbog)):
        h = min(G + int(depth[x, y]), 62)
        s.mat[x, y, :h] = 0
        s.mat[x, y, h] = M['bank']
    water = L.bog & (depth >= 6)
    s.mat[water, :63] = 0                                                         # open water: z 62 air
    for (wy0, wy1) in SPEC['boardwalk_y']:
        bw = west & (Y >= wy0) & (Y <= wy1) & (X >= 200) & L.bog
        s.mat[bw, G] = M['boardwalk']
        posts = bw & ((X % 6) == 0) & ((Y == wy0) | (Y == wy1))
        for x, y in zip(*np.nonzero(posts)):
            s.mat[x, y, G:63] = M['boardwalk']
        s.mat[bw, :G] = 0
    return water


def cemetery_wall(s, L, M):
    X, Y = L.X, L.Y
    cm = SPEC['cemetery']; cz = cm['z']
    ring = L.cem & ~ndimage.binary_erosion(L.cem | (X > 255), iterations=1)
    for (g0, g1) in cm['gates_y']:
        ring &= ~((Y >= g0) & (Y <= g1) & (X == cm['x'][0]))
    ring &= ~((X >= 248) & ((Y == cm['y'][0]) | (Y == cm['y'][1])))                 # north / south gates
    s.mat[ring, cz - 2:cz] = M['cemwall']
    return ring


def build_graybox(mirror_output=True, L=None):
    L = L or Layout()
    s = Scene('hollowfen', seed=SEED)
    M = {k: s.material(Material(k, v)) for k, v in GRAY.items()}
    H = ground(s, L, M)
    bogs(s, L, M)
    cemetery_wall(s, L, M)
    cm = SPEC['cemetery']; cz = cm['z']
    mx, my = cm['mausoleum_x'], cm['mausoleum_y']
    s.box(mx[0], 255, my[0], my[1], cz - 8, cz - 1, M['mausoleum'])
    s.carve(mx[0] + 1, 255, my[0] + 1, my[1] - 1, cz - 7, cz - 1)
    s.box(mx[0] - 1, 255, my[0] - 1, my[1] + 1, cz - 9, cz - 9, M['mausoleum'])      # roof slab overhang
    s.carve(mx[0], mx[0], 254, 258, cz - 4, cz - 1)                                   # door
    for p in L.plots:                                     # houses: hollow boxes, door on the lane side
        (x0, x1), (y0, y1) = p['x'], p['y']
        wh = 4 * p['storeys'] + 1
        s.box(x0, x1, y0, y1, G - wh, G - 1, M['house'])
        s.carve(x0 + 1, x1 - 1, y0 + 1, y1 - 1, G - wh + 1, G - 1)
        s.box(x0 - 1, x1 + 1, y0 - 1, y1 + 1, G - wh - 1, G - wh - 1, M['roof'])
        dx = (x0 + x1) // 2; dy = y0 if p['front'] == 'n' else y1
        s.carve(dx, dx + 1, dy, dy, G - 3, G - 1)
    s.box(30, 50, 262, 273, G - 10, G - 1, M['barn']); s.carve(31, 49, 263, 272, G - 9, G - 1)
    s.carve(39, 41, 262, 262, G - 5, G - 1)
    s.box(32, 46, 239, 250, G - 9, G - 1, M['house']); s.carve(33, 45, 240, 249, G - 8, G - 1)
    s.carve(38, 39, 250, 250, G - 3, G - 1)
    church(s, M['church'], M['stair'], M['belfry'], M['roof'])
    s.markers['H'] = H
    if mirror_output:
        mirror(s)
        # witches (requested floating scenery) go in AFTER mirroring: they are placed freely, not mirrored
        for (wx, wy, wz) in SPEC['witches']:
            s.box(wx - 5, wx + 5, wy - 1, wy + 1, wz, wz + 1, M['witch'])
    return s, L


def church(s, m_wall, m_stair, m_belfry, m_roof, m_floor=None, detail=None):
    """Church massing shared by graybox and art (art passes its own materials and adds detail).
    Nave: walls G-12..G-1, hollow, doors west + north/south, pitched roof. Tower: hollow, 2-wide spiral stair from
    the floor to the belfry deck (z 32), belfry arches z 25..31, spire of 1-in-3 steps (not walkable)."""
    c = SPEC['church']
    (nx0, nx1), (ny0, ny1) = c['nave_x'], c['nave_y']
    (tx0, tx1), (ty0, ty1) = c['tower_x'], c['tower_y']
    top = c['nave_wall_top_z']
    s.box(nx0, nx1, ny0, ny1, top, G - 1, m_wall)
    s.carve(nx0 + 1, nx1, ny0 + 1, ny1 - 1, top + 1, G - 1)                        # open into the tower base
    yc = (ny0 + ny1) // 2
    s.carve(nx0, nx0, yc - 1, yc + 1, G - 5, G - 1)                                # west door
    for yy in (ny0, ny1):
        s.carve(nx0 + 6, nx0 + 7, yy, yy, G - 4, G - 1)                            # side doors
    s.box(nx0 - 1, nx1, ny0 - 1, ny0 - 1, top, top, m_roof)                       # eaves, attached to the wall top
    s.box(nx0 - 1, nx1, ny1 + 1, ny1 + 1, top, top, m_roof)
    k = 0
    while ny0 + k <= ny1 - k:                                                      # pitched roof along x
        z = top - 1 - k
        s.box(nx0 - 1, nx1, ny0 + k, ny0 + k, z, z, m_roof)
        s.box(nx0 - 1, nx1, ny1 - k, ny1 - k, z, z, m_roof)
        if ny0 + k + 1 <= ny1 - k - 1:
            s.box(nx0, nx0, ny0 + k + 1, ny1 - k - 1, z, z, m_wall)               # west gable
        k += 1
    # tower
    bz = c['belfry_floor_z']
    s.box(tx0, tx1, ty0, ty1, bz, G - 1, m_wall)
    s.carve(tx0 + 1, tx1 - 1, ty0 + 1, ty1 - 1, bz + 1, G - 1)
    s.carve(tx0, tx0, ty0 + 3, ty1 - 3, G - 4, G - 1)                              # opening from the nave
    # spiral stair: 2-wide ring inside the walls, one voxel up per cell, thin treads attached to the wall
    ring = []
    a0, a1, b0, b1 = tx0 + 1, tx1 - 1, ty0 + 1, ty1 - 1
    for x in range(a0, a1 + 1): ring.append((x, b0))
    for y in range(b0 + 1, b1 + 1): ring.append((a1, y))
    for x in range(a1 - 1, a0 - 1, -1): ring.append((x, b1))
    for y in range(b1 - 1, b0, -1): ring.append((a0, y))
    inner = {(a0, b0): (a0 + 1, b0 + 1)}
    start = ring.index((a0 + 2, b0))
    z = G - 1                                                                       # first tread one above floor
    k = start
    steps = []
    while z > bz:
        x, y = ring[k % len(ring)]
        ix = x + (1 if x == a0 else -1 if x == a1 else 0)
        iy = y + (1 if y == b0 else -1 if y == b1 else 0)
        for (px, py) in ((x, y), (ix, iy)):
            s.mat[px, py, z] = m_stair
            s.mat[px, py, max(z - 4, 0):z] = 0                                     # headroom
        steps.append((x, y, z))
        z -= 1; k += 1
    # belfry deck with the stair arriving through a hole
    s.box(tx0, tx1, ty0, ty1, bz, bz, m_belfry)
    for (x, y, zst) in steps[-5:]:
        ix = x + (1 if x == a0 else -1 if x == a1 else 0)
        iy = y + (1 if y == b0 else -1 if y == b1 else 0)
        s.mat[x, y, bz] = 0; s.mat[ix, iy, bz] = 0
    x, y, _ = steps[-1]
    s.mat[x, y, bz + 1] = m_stair                                                  # last tread = deck level step
    # belfry: corner piers + arches, then the spire
    for z in range(bz - 7, bz):
        for (x, y) in ((tx0, ty0), (tx1, ty0), (tx0, ty1), (tx1, ty1), (tx0 + 1, ty0), (tx0, ty0 + 1),
                       (tx1 - 1, ty0), (tx1, ty0 + 1), (tx0 + 1, ty1), (tx0, ty1 - 1), (tx1 - 1, ty1), (tx1, ty1 - 1)):
            s.mat[x, y, z] = m_wall
    s.box(tx0, tx1, ty0, ty1, bz - 8, bz - 8, m_wall)                              # belfry ceiling / cornice
    z = bz - 9                                                                     # spire: 1 in 3 (not walkable)
    lo = 1
    while (tx1 - lo) - (tx0 + lo) >= 2:
        for _ in range(3):
            s.box(tx0 + lo, tx1 - lo, ty0 + lo, ty1 - lo, z, z, m_roof)
            z -= 1
        lo += 1
    cx, cy = (tx0 + tx1) // 2, (ty0 + ty1) // 2
    s.mat[cx, cy, z - 1:z + 1] = m_roof                                            # finial
    s.markers['church_steps'] = steps
    s.markers['spire_tip_z'] = z + 1


def metadata_txt(fog=None, author='aosmap (graybox v1)'):
    from aosmap.meta import map_txt
    sq = SPEC['square']
    pts = [(x, y, G) for x in range(sq['x'][0] + 4, sq['x'][1] - 3, 8) for y in range(sq['y'][0] + 4, sq['y'][1] - 3, 8)]
    spawns = {0: pts, 1: [(512 - x, y, z) for (x, y, z) in pts]}
    fx, fy = SPEC['ctf']['blue_flag']; bx, by = SPEC['ctf']['blue_base']
    ents = {0: (fx, fy, G), 1: (512 - fx, fy, G), 2: (bx, by, G), 3: (512 - bx, by, G)}
    return map_txt(
        name='Hollowfen', author=author, version='0.1',
        description='Haunted fen village at dusk. Babel or CTF: two villages, two churches, a cemetery between.',
        header='Generated by scenes/hollowfen.py (seed %d). CTF: spawns on the village squares, intel at each\n'
               "village's pumpkin farm, tents on the squares. Babel mode replaces these hooks with its own." % SEED,
        fog=fog or SPEC['fog'], extensions={'babel': True, 'water_damage': 0},
        spawns=spawns, entities=ents)


if __name__ == '__main__':
    from aosmap.vxl import write_vxl
    out = sys.argv[1] if len(sys.argv) > 1 else 'out/hollowfen_graybox'
    os.makedirs(out, exist_ok=True)
    s, L = build_graybox()
    data = write_vxl(s.to_voxelmap())
    open(os.path.join(out, 'hollowfen.vxl'), 'wb').write(data)
    open(os.path.join(out, 'hollowfen.txt'), 'w').write(metadata_txt())
    spec = dict(SPEC); spec['plots'] = L.plots; spec['spire_tip_z'] = s.markers['spire_tip_z']
    json.dump(spec, open(os.path.join(out, 'spec.json'), 'w'), indent=1, default=list)
    print('written', len(data), 'bytes; plots', len(L.plots), 'spire tip z', s.markers['spire_tip_z'],
          'stair steps', len(s.markers['church_steps']))
