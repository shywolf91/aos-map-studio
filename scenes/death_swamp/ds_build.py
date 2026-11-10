"""Death Swamp geometry: terrain, paths, spawn pads, control-point daises, boulder mounds, dead trees,
mooring lanterns, the leviathan skull and ribs, outer islets.

Everything is authored for the west half (x <= 255) and mirrored (x' = 511 - x). Geometry is stored as
material ids (uint8) in M[x, y, z]; colours are applied in ds_color.py.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from ds_core import MX, MY, MZ, fbm2, hash3, line_voxels, mirror_x, rng
from ds_layout import SPEC, gaps, ground_height, island_masks

# ------------------------------------------------------------------------------------------- materials
(AIR, PEAT, SOIL, BANK, ROCK, BARK, TWIG, HANGMOSS, BONE, SOCKET, FLAG, STONE, PATH, POST, LANTERN,
 GLOWCAP, TUFT, REED, CATTAIL, RUNE, ROOT, LANTERN_CAP, ISLET_ROCK) = range(23)
NAMES = {v: k for k, v in dict(PEAT=PEAT, SOIL=SOIL, BANK=BANK, ROCK=ROCK, BARK=BARK, TWIG=TWIG,
                                HANGMOSS=HANGMOSS, BONE=BONE, SOCKET=SOCKET, FLAG=FLAG, STONE=STONE,
                                PATH=PATH, POST=POST, LANTERN=LANTERN, GLOWCAP=GLOWCAP, TUFT=TUFT, REED=REED,
                                CATTAIL=CATTAIL, RUNE=RUNE, ROOT=ROOT, LANTERN_CAP=LANTERN_CAP,
                                ISLET_ROCK=ISLET_ROCK).items()}

WEST = np.zeros((MX, MY), bool)
WEST[:256] = True


class World:
    def __init__(self):
        self.M = np.zeros((MX, MY, MZ), np.uint8)
        self.masks = island_masks()
        self.top, self.ident = ground_height(self.masks)
        self.land = self.top < 63
        self.inland = ndi.distance_transform_edt(self.land)
        self.noprop = np.zeros((MX, MY), bool)        # columns kept clear of props (paths, pads, landings)
        self.pathmask = np.zeros((MX, MY), bool)
        self.protect = np.zeros((MX, MY), bool)       # spawn pad / CP dais: open sky required
        self.markers = {}

    # -- helpers --------------------------------------------------------------------------------------
    def put(self, x, y, z, mid, only_air=False):
        x = np.asarray(x); y = np.asarray(y); z = np.asarray(z)
        ok = (x >= 0) & (x < 256) & (y >= 0) & (y < MY) & (z >= 0) & (z < 63)
        x, y, z = x[ok], y[ok], z[ok]
        if only_air:
            free = self.M[x, y, z] == AIR
            x, y, z = x[free], y[free], z[free]
        self.M[x, y, z] = mid

    def surface_z(self, x, y):
        """z of the topmost solid voxel in column (x, y) (63 = water plane)."""
        col = self.M[x, y, :63] > 0
        return int(np.argmax(col)) if col.any() else 63


# ------------------------------------------------------------------------------------------- terrain

def build_terrain(w: World):
    top = w.top
    zz = np.arange(MZ)[None, None, :]
    solid = (zz >= top[:, :, None]) & (top[:, :, None] < 63)
    w.M[solid] = SOIL
    xs, ys = np.nonzero(w.land)
    zs = top[xs, ys]
    bank = w.inland[xs, ys] < 4.5
    w.M[xs, ys, zs] = np.where(bank, BANK, PEAT)
    w.M[:, :, 63] = 0          # z = 63 is forced solid at export (water plane / seabed)


def flatten_disc(w: World, cx, cy, r, z, mid, square=False):
    X, Y = np.indices((MX, MY))
    if square:
        m = (np.abs(X - cx) <= r) & (np.abs(Y - cy) <= r)
    else:
        m = (X - cx) ** 2 + (Y - cy) ** 2 <= r * r
    m &= WEST
    xs, ys = np.nonzero(m)
    w.M[xs, ys, :63] = AIR
    for zz in range(z, 63):
        w.M[xs, ys, zz] = SOIL
    w.M[xs, ys, z] = mid
    w.top[xs, ys] = z
    return m


def build_paths(w: World, g):
    """Worn trails linking landings (bridgeheads) across each island; flush with the ground."""
    order = SPEC['order']
    land_pts = {n: [] for n in order}
    for a, b in zip(order, order[1:]):
        land_pts[a].append(g[f'{a}->{b}']['from'])
        land_pts[b].append(g[f'{a}->{b}']['to'])
    land_pts['S'].insert(0, SPEC['spawn'])
    land_pts['N'].append(SPEC['cp'])
    w.markers['landings'] = {k: v for k, v in land_pts.items()}
    r = rng('paths')
    X, Y = np.indices((MX, MY))
    for name, pts in land_pts.items():
        for p, q in zip(pts, pts[1:]):
            p = np.array(p, float); q = np.array(q, float)
            mid = (p + q) / 2 + np.array([r.uniform(-9, 9), r.uniform(-4, 4)])
            poly = [p, mid, q]
            for s, t in zip(poly, poly[1:]):
                n = int(np.linalg.norm(t - s)) + 1
                for k in range(n + 1):
                    c = s + (t - s) * k / n
                    m = (X - c[0]) ** 2 + (Y - c[1]) ** 2 <= 2.6 ** 2
                    w.pathmask |= m
    w.pathmask &= w.land & WEST
    xs, ys = np.nonzero(w.pathmask & (w.inland > 3.5))
    w.M[xs, ys, w.top[xs, ys]] = PATH
    w.noprop |= ndi.binary_dilation(w.pathmask, iterations=3)
    # landings: keep a clear 9-radius apron at every bridgehead
    for pts in land_pts.values():
        for (lx, ly) in pts:
            w.noprop |= (X - lx) ** 2 + (Y - ly) ** 2 <= 10 ** 2


def build_spawn_pad(w: World):
    sx, sy = SPEC['spawn']
    z = SPEC['islands']['S'][0]
    rr = SPEC['spawn_range']
    pad = flatten_disc(w, sx, sy, rr + 2, z, FLAG, square=True)
    # mossy cracks: rune ring of darker stones marking the pad edge
    X, Y = np.indices((MX, MY))
    ring = (np.maximum(np.abs(X - sx), np.abs(Y - sy)) == rr + 2) & pad
    xs, ys = np.nonzero(ring)
    w.M[xs, ys, z] = RUNE
    w.noprop |= (np.abs(X - sx) <= rr + 6) & (np.abs(Y - sy) <= rr + 6)
    w.protect |= (np.abs(X - sx) <= rr + 2) & (np.abs(Y - sy) <= rr + 2)
    w.markers['spawn_z'] = z


def build_cp_dais(w: World):
    cx, cy = SPEC['cp']
    z = SPEC['islands']['N'][0]
    flatten_disc(w, cx, cy, 11, z, FLAG)
    X, Y = np.indices((MX, MY))
    d = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    ring = (d >= 5.5) & (d < 6.6) & WEST
    xs, ys = np.nonzero(ring)
    w.M[xs, ys, z] = RUNE
    ring2 = (d >= 10.2) & (d < 11.3) & WEST
    xs, ys = np.nonzero(ring2)
    w.M[xs, ys, z] = RUNE
    # standing stones at radius 14, gaps on the approach (south) and toward the skull (east)
    r = rng('stones')
    for k in range(9):
        a = 2 * np.pi * k / 9 + 0.17
        if abs(np.sin(a) - 1) < 0.25 or abs(np.cos(a) - 1) < 0.2:     # leave entrances
            continue
        px = int(round(cx + 14.5 * np.cos(a))); py = int(round(cy + 14.5 * np.sin(a)))
        h = int(r.integers(5, 9))
        gz = w.top[px, py]
        for dx in (0, 1):
            for dy in (0, 1):
                gz2 = w.top[px + dx, py + dy]
                w.put([px + dx] * (h + 63 - gz2), [py + dy] * (h + 63 - gz2),
                      list(range(gz2 - h, 63)), STONE)
        # weathered cap: one voxel lean on the top
        w.put([px + int(r.integers(0, 2))], [py + int(r.integers(0, 2))], [gz - h - 1], STONE)
    w.noprop |= d <= 17
    w.protect |= (d <= 12) & WEST
    w.markers['cp_z'] = z


# ------------------------------------------------------------------------------------------- props

def _smooth3(x, y, z, salt):
    """Cheap smooth 3D noise (sum of random-phase sines), in roughly [-1, 1]."""
    r = rng(f'sines{salt}')
    v = np.zeros(np.broadcast(x, y, z).shape, np.float32)
    for _ in range(4):
        k = r.normal(0, 0.28, 3)
        v += np.sin(k[0] * x + k[1] * y + k[2] * z + r.uniform(0, 6.28))
    return v / 2.0


def boulder_mound(w: World, cx, cy, R, salt, lumps=None, height=1.0, mid=ROCK):
    """Cluster of squashed, noise-warped ellipsoids sunk into the ground (or rising from the water).
    Columns over water get a rock skirt to the seabed so the mound stands on the water plane (grounded)."""
    r = rng(f'mound{salt}')
    lumps = lumps or int(r.integers(3, 7))
    gz = int(w.top[int(cx), int(cy)]) if w.land[int(cx), int(cy)] else 60
    x0, x1 = int(max(cx - R - 4, 0)), int(min(cx + R + 4, 255))
    y0, y1 = int(max(cy - R - 4, 0)), int(min(cy + R + 4, MY - 1))
    X, Y, Z = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1), np.arange(0, 63), indexing='ij')
    occ = np.zeros(X.shape, bool)
    for i in range(lumps):
        a = r.uniform(0, 2 * np.pi)
        dist = r.uniform(0, R * 0.55) if i else 0
        lx, ly = cx + np.cos(a) * dist, cy + np.sin(a) * dist
        lr = R * r.uniform(0.5, 0.78) if i else R * 0.72
        rz = lr * r.uniform(0.62, 0.85) * height
        lz = gz + lr * 0.22
        f = ((X - lx) / lr) ** 2 + ((Y - ly) / lr) ** 2 + ((Z - lz) / rz) ** 2
        occ |= f <= 1.0 + 0.16 * _smooth3(X, Y, Z, f'{salt}/{i}')
    xs, ys, zs = np.nonzero(occ)
    xs += x0; ys += y0
    w.put(xs, ys, zs, mid)
    # skirt: columns over water filled from the lowest mound voxel down to z 62
    cols = {}
    for x, y, z in zip(xs.tolist(), ys.tolist(), zs.tolist()):
        cols[(x, y)] = max(cols.get((x, y), -1), z)
    for (x, y), zb in cols.items():
        if zb < 62:
            w.M[x, y, zb:63][w.M[x, y, zb:63] == AIR] = mid
    return occ


def dead_tree(w: World, x, y, salt, height=None, in_water=False, big=False):
    """Bare swamp tree: root flares, leaning trunk, radiating spiky branches, hanging moss, shelf fungi.
    All parts are face-connected to the trunk; the trunk stands on ground (or on the water plane)."""
    r = rng(f'tree{salt}')
    gz = 63 if in_water else int(w.top[x, y])
    base = gz - 1
    h = height or int(r.integers(13, 22))
    lean = r.normal(0, 0.18, 2)
    pts = []
    # trunk
    top = np.array([x + lean[0] * h, y + lean[1] * h, base - h], float)
    spine = line_voxels((x, y, base), top)
    thick = 2 if big else 1
    for (px, py, pz) in spine:
        frac = (base - pz) / h
        t = thick if frac < 0.55 else 1
        for dx in range(t):
            for dy in range(t):
                pts.append((px + dx, py + dy, pz, BARK))
    # trunk down into ground/water (anchor)
    for zz in range(base, 63):
        for dx in range(thick):
            for dy in range(thick):
                pts.append((x + dx, y + dy, zz, BARK))
    # root flares / cypress knees
    for k in range(int(r.integers(4, 7))):
        a = r.uniform(0, 2 * np.pi)
        L = r.uniform(3, 5.5) if not in_water else r.uniform(2.5, 4)
        tip = (x + np.cos(a) * L, y + np.sin(a) * L, base + (1 if in_water else 0))
        for (px, py, pz) in line_voxels((x, y, base - 2), tip):
            pts.append((px, py, min(pz, 62), ROOT))
            # roots hug the ground: fill under them
            for zz in range(min(pz, 62) + 1, 63):
                pts.append((px, py, zz, ROOT))
    # branches
    nb = int(r.integers(7, 11)) + (3 if big else 0)
    for k in range(nb):
        f = r.uniform(0.38, 1.0)
        i = min(int(f * (len(spine) - 1)), len(spine) - 1)
        sx, sy, sz = spine[i]
        a = 2 * np.pi * k / nb + r.uniform(-0.4, 0.4)
        L = r.uniform(5.5, 11) * (1.35 if big else 1.0) * (1.2 - 0.5 * f)
        rise = r.uniform(0.25, 0.95)
        tip = (sx + np.cos(a) * L, sy + np.sin(a) * L, sz - L * rise)
        bv = line_voxels((sx, sy, sz), tip)
        for j, (px, py, pz) in enumerate(bv):
            pts.append((px, py, pz, TWIG if j > len(bv) * 0.55 else BARK))
        # sub-twigs
        for q in range(int(r.integers(1, 3))):
            j = int(r.integers(len(bv) // 2, len(bv)))
            px, py, pz = bv[j]
            a2 = a + r.uniform(-1.1, 1.1)
            L2 = r.uniform(2, 4)
            for (qx, qy, qz) in line_voxels((px, py, pz), (px + np.cos(a2) * L2, py + np.sin(a2) * L2,
                                                          pz - L2 * r.uniform(0.3, 1.2))):
                pts.append((qx, qy, qz, TWIG))
        # hanging moss under the branch
        if r.random() < 0.55:
            j = int(r.integers(1, max(2, len(bv) - 1)))
            px, py, pz = bv[j]
            for d in range(1, int(r.integers(2, 5))):
                pts.append((px, py, pz + d, HANGMOSS))
    # crown spikes
    for k in range(3):
        a = r.uniform(0, 2 * np.pi)
        tx, ty, tz = spine[-1]
        for (px, py, pz) in line_voxels((tx, ty, tz), (tx + np.cos(a) * 2, ty + np.sin(a) * 2, tz - 3)):
            pts.append((px, py, pz, TWIG))
    # shelf fungi on the trunk (amber glowcaps)
    for k in range(int(r.integers(0, 3))):
        i = int(r.integers(1, max(2, len(spine) // 2)))
        px, py, pz = spine[i]
        d = [(1, 0), (-1, 0), (0, 1), (0, -1)][int(r.integers(0, 4))]
        pts.append((px + d[0] * thick if d[0] > 0 else px + d[0], py + (d[1] * thick if d[1] > 0 else d[1]),
                    pz, GLOWCAP))
    arr = np.array([p[:3] for p in pts]); mids = np.array([p[3] for p in pts], np.uint8)
    ok = (arr[:, 0] >= 0) & (arr[:, 0] < 256) & (arr[:, 1] >= 0) & (arr[:, 1] < MY) & (arr[:, 2] >= 2) & (arr[:, 2] < 63)
    arr, mids = arr[ok], mids[ok]
    # order: bark/roots win over twigs/moss
    for prio in (HANGMOSS, GLOWCAP, TWIG, ROOT, BARK):
        s = mids == prio
        cur = w.M[arr[s, 0], arr[s, 1], arr[s, 2]]
        keep = np.isin(cur, (AIR, TWIG, HANGMOSS, GLOWCAP, ROOT, PEAT, BANK, SOIL)) if prio in (BARK, ROOT) else cur == AIR
        w.M[arr[s, 0][keep], arr[s, 1][keep], arr[s, 2][keep]] = prio


def mooring_post(w: World, x, y):
    """Old rotten mooring post with an amber lantern; marks a bridgehead."""
    gz = int(w.top[x, y])
    for zz in range(gz - 6, 63):
        if w.M[x, y, zz] in (AIR, PEAT, BANK, PATH):
            w.M[x, y, zz] = POST if zz < gz else w.M[x, y, zz]
    w.M[x, y, gz - 7] = LANTERN
    w.M[x, y, gz - 8] = LANTERN_CAP


# ------------------------------------------------------------------------------------------- landmark

def build_skull(w: World):
    """The leviathan skull on the North Isle, facing south, centred on the mirror axis.
    Built for x <= 255 with dx = x - 255.5 so the mirror completes it exactly."""
    cx, cy = SPEC['skull']
    X, Y, Z = np.meshgrid(np.arange(200, 256), np.arange(10, 150), np.arange(0, 63), indexing='ij')
    dx = X - cx
    bone = np.zeros(X.shape, bool)
    n = 0.10 * _smooth3(X, Y, Z, 'skull')
    # cranium
    bone |= (dx / 22) ** 2 + ((Y - (cy - 2)) / 26) ** 2 + ((Z - 45) / 16) ** 2 <= 1 + n
    # sagittal crest along the top of the cranium
    bone |= (dx / 3.5) ** 2 + ((Y - (cy - 6)) / 20) ** 2 + ((Z - 31) / 4) ** 2 <= 1 + n
    # brow ridges
    for s in (-1,):
        bone |= ((dx - s * 10) / 8) ** 2 + ((Y - (cy + 14)) / 8) ** 2 + ((Z - 33) / 5) ** 2 <= 1 + n
    # cheekbones
    bone |= ((dx + 19) / 7) ** 2 + ((Y - (cy + 12)) / 11) ** 2 + ((Z - 46) / 6) ** 2 <= 1 + n
    # snout (upper jaw), tapering to the south
    sy0, sy1 = cy + 14, cy + 62
    t = np.clip((Y - sy0) / (sy1 - sy0), 0, 1)
    rx = 12.5 - 4.5 * t
    rz = 7.5 - 2.0 * t
    in_len = (Y >= sy0) & (Y <= sy1)
    bone |= in_len & ((dx / rx) ** 2 + ((Z - 43) / rz) ** 2 <= 1 + n)
    # rounded snout tip
    bone |= (dx / 8) ** 2 + ((Y - sy1) / 5) ** 2 + ((Z - 44) / 5.5) ** 2 <= 1 + n
    # lower jaw resting on the ground
    jy1 = sy1 - 2
    tj = np.clip((Y - (cy + 4)) / (jy1 - cy - 4), 0, 1)
    bone |= (Y >= cy + 4) & (Y <= jy1) & ((dx / (11.5 - 3.5 * tj)) ** 2 + ((Z - 52) / 4) ** 2 <= 1 + n)
    # horns: curve back, out and up
    for k in range(60):
        u = k / 59
        hx = cx - (17 + 15 * u)
        hy = cy - 10 - 26 * u + 6 * u * u
        hz = 33 - 18 * u + 2 * u * u
        hr = 4.6 - 3.3 * u
        bone |= ((X - hx) ** 2 + (Y - hy) ** 2 + (Z - hz) ** 2) <= hr * hr
    bone &= Z < 63
    xs, ys, zs = np.nonzero(bone)
    w.M[xs + 200, ys + 10, zs] = BONE
    # eye sockets: carve dark hollows into the brow face
    sock = (((X - (cx - 10)) / 5.5) ** 2 + ((Y - (cy + 21)) / 6) ** 2 + ((Z - 39) / 5) ** 2) <= 1
    xs, ys, zs = np.nonzero(sock & bone)
    w.M[xs + 200, ys + 10, zs] = AIR
    shell = ndi.binary_dilation(sock, iterations=2) & ~sock & bone
    xs, ys, zs = np.nonzero(shell)
    w.M[xs + 200, ys + 10, zs] = SOCKET
    # nostrils
    nos = (((X - (cx - 4)) / 2.2) ** 2 + ((Y - (sy1 - 1)) / 3) ** 2 + ((Z - 39.5) / 2) ** 2) <= 1
    xs, ys, zs = np.nonzero(nos & bone)
    w.M[xs + 200, ys + 10, zs] = AIR
    shell = ndi.binary_dilation(nos, iterations=1) & ~nos & bone
    xs, ys, zs = np.nonzero(shell)
    w.M[xs + 200, ys + 10, zs] = SOCKET
    # teeth along the jaw line, overlapping both jaws
    for ty in range(int(sy0) + 4, int(sy1) - 1, 4):
        tt = (ty - sy0) / (sy1 - sy0)
        txo = 12.5 - 4.5 * tt
        tx = int(round(cx - txo + 0.2))
        for zz in range(45, 52):
            wdt = 2 if zz < 49 else 1
            for k in range(wdt):
                w.put([tx - 1 + k], [ty], [zz], BONE)
                w.put([tx - 1 + k], [ty + 1], [zz], BONE)
    w.noprop |= (np.abs(np.indices((MX, MY))[0] - cx) < 40) & (np.abs(np.indices((MX, MY))[1] - cy) < 64)


def build_ribs(w: World):
    """Drowned leviathan ribs rising from the central channel (no-man's water between the lanes).
    Each rib is isolated: its foot stands in the water >= 8 from any island, apex gap 4 at the axis."""
    for k, ry in enumerate(SPEC['ribs_y']):
        Hr = 26 - 2.4 * k
        pts = set()
        for t in np.linspace(0, np.pi / 2, 120):
            px = 255.5 - 2.5 - 10.5 * np.cos(t)
            pz = 62 - Hr * np.sin(t)
            for ox in (0, 1):
                for oz in (0, 1):
                    for oy in (0, 1):
                        pts.add((int(np.floor(px)) - ox, ry + oy, int(round(pz)) - oz))
        # foot knuckle
        fx = int(np.floor(255.5 - 13))
        for ox in range(-1, 2):
            for oy in range(-1, 3):
                for zz in range(58, 63):
                    pts.add((fx + ox, ry + oy, zz))
        for (x, y, z) in pts:
            if 0 <= z < 63 and x <= 255:
                w.M[x, y, z] = BONE


# ------------------------------------------------------------------------------------------- scatter

def poisson(mask, n, rmin, tag, weight=None):
    r = rng(tag)
    xs, ys = np.nonzero(mask)
    if len(xs) == 0:
        return []
    p = None
    if weight is not None:
        p = weight[xs, ys].astype(float); p /= p.sum()
    out = []
    tries = 0
    while len(out) < n and tries < n * 400:
        tries += 1
        i = r.choice(len(xs), p=p)
        x, y = int(xs[i]), int(ys[i])
        if all((x - a) ** 2 + (y - b) ** 2 >= rmin * rmin for a, b in out):
            out.append((x, y))
    return out


def build_mounds(w: World):
    """Boulder mounds: ringed along island banks (the screenshot's boulder clusters), kept off paths,
    pads, landings and the CP dais; a few big ones inland for cover."""
    placed = []
    keep_out = ndi.binary_dilation(w.noprop, iterations=4)
    for name in SPEC['order']:
        m = w.masks[name] & WEST & ~keep_out
        if name == 'N':
            m &= ~((np.abs(np.indices((MX, MY))[0] - 255.5) < 44))
        d = w.inland
        weight = np.exp(-((d - 4) / 5.0) ** 2) + 0.15
        count = {'S': 8, 'I2': 7, 'I3': 7, 'I4': 7, 'N': 10}[name]
        pts = poisson(m, count, 15, f'mounds{name}', weight=weight)
        r = rng(f'mr{name}')
        for i, (x, y) in enumerate(pts):
            R = float(r.uniform(6.5, 11.5)) if i % 3 else float(r.uniform(10, 14))
            boulder_mound(w, x, y, R, f'{name}{i}', height=float(r.uniform(0.9, 1.25)))
            placed.append((x, y, R, name))
    # spawn cover: a low boulder ridge between the spawn pad and the central channel
    sx, sy = SPEC['spawn']
    for k, (ox, oy, R) in enumerate([(19, -6, 7.5), (21, 4, 8.5), (18, 13, 7)]):
        boulder_mound(w, sx + ox, sy + oy, R, f'spawncover{k}', height=1.15)
        placed.append((sx + ox, sy + oy, R, 'S'))
    w.markers['mounds'] = placed
    return placed


def carve_hollows(w: World, mounds):
    """The screenshot's 'hole in the boulder': a dark socket sunk into the top of a few big mounds."""
    r = rng('hollows')
    big = [m for m in mounds if m[2] >= 10]
    for (x, y, R, name) in big[::3]:
        z = w.surface_z(x, y)
        if z > 50:
            continue
        rr = 2.5
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                if dx * dx + dy * dy <= rr * rr:
                    depth = 4 if dx * dx + dy * dy < 2 else 3
                    for zz in range(z, z + depth):
                        if w.M[x + dx, y + dy, zz] == ROCK:
                            w.M[x + dx, y + dy, zz] = AIR
                    zb = z + depth
                    if w.M[x + dx, y + dy, zb] == ROCK:
                        w.M[x + dx, y + dy, zb] = SOCKET


def build_trees(w: World, mounds):
    trees = []
    # island trees: inland, off paths/pads, away from mound centres
    blocked = ndi.binary_dilation(w.noprop, iterations=2) | (ndi.distance_transform_edt(~w.protect) < 15)
    m = w.land & WEST & (w.inland >= 6) & ~blocked
    for (x, y, R, _) in mounds:
        X, Y = np.indices((MX, MY))
        m &= (X - x) ** 2 + (Y - y) ** 2 > (R + 2) ** 2
    pts = poisson(m, 34, 13, 'treesland')
    r = rng('treesland2')
    for i, (x, y) in enumerate(pts):
        if w.M[x, y, w.top[x, y] - 1] != AIR:
            continue
        dead_tree(w, x, y, f'L{i}', big=(i % 5 == 0), height=int(r.integers(14, 24)))
        trees.append((x, y, 'land'))
    # water trees: outer swamp only, >= 12 from any land, never in the lane gaps or the central channel
    far = ndi.distance_transform_edt(~w.land) >= 12
    lanes = np.zeros((MX, MY), bool)
    lanes[118:256, 150:500] = True
    wm = far & WEST & ~lanes
    wm[:12] = False; wm[:, :12] = False; wm[:, 500:] = False
    wm[0:90, 455:512] = False         # leave the SW corner for the name tag
    grove = mirror_x(fbm2((MX, MY), 40, 2, 'groves')) > 0.52
    pts = poisson(wm & grove, 30, 12, 'treeswater')
    for i, (x, y) in enumerate(pts):
        dead_tree(w, x, y, f'W{i}', in_water=True, big=(i % 4 == 0), height=int(r.integers(12, 22)))
        trees.append((x, y, 'water'))
    w.markers['trees'] = trees


def build_islets(w: World):
    """Small unreachable boulder islets in the outer swamp (decor, >= 30 from the lanes)."""
    r = rng('islets')
    spots = [(66, 150, 12), (54, 322, 15), (84, 430, 10), (104, 36, 13), (36, 236, 9), (40, 70, 10)]
    for i, (x, y, R) in enumerate(spots):
        boulder_mound(w, x, y, R, f'islet{i}', height=float(r.uniform(0.9, 1.3)), mid=ISLET_ROCK)
        # a drowned tree beside some
        if i % 2 == 0:
            dead_tree(w, x + int(R) + 4, y - 3, f'IT{i}', in_water=True, height=int(r.integers(14, 20)))


def scatter_small(w: World):
    """Grass tufts (clustered, low), reeds and cattails on the banks, glowcaps near water on rocks."""
    r = rng('scatter')
    clump = fbm2((MX, MY), 14, 2, 'clumps')
    xs, ys = np.nonzero(w.land & WEST & ~w.noprop)
    for x, y in zip(xs.tolist(), ys.tolist()):
        z = w.surface_z(x, y)
        if z >= 63 or w.M[x, y, z] not in (PEAT, BANK, ROCK):
            continue
        hv = hash3(x, y, 7)
        d = w.inland[x, y]
        if w.M[x, y, z] == BANK and d < 3.5 and clump[x, y] > 0.56 and hv < 0.22:
            h = 2 + int(hash3(x, y, 9) * 3)
            for k in range(1, h + 1):
                w.M[x, y, z - k] = REED
            if hash3(x, y, 11) < 0.25:
                w.M[x, y, z - h - 1] = CATTAIL
        elif w.M[x, y, z] == PEAT and clump[x, y] > 0.66 and hv < 0.05:
            w.M[x, y, z - 1] = TUFT
        elif w.M[x, y, z] == ROCK and z > 52 and hv < 0.012:
            w.M[x, y, z - 1] = GLOWCAP


# ------------------------------------------------------------------------------------------- build

def remove_debris(w: World, max_voxels=40):
    """Delete small floating fragments left by carving (eye sockets, hollows). Larger floating pieces are
    NOT removed - the export check reports them as errors so they get fixed at the source."""
    solid = w.M > 0
    solid[:, :, 63] = True
    lab, n = ndi.label(solid, structure=ndi.generate_binary_structure(3, 1))
    grounded = set(np.unique(lab[:, :, 62:][solid[:, :, 62:]]).tolist())
    sizes = np.bincount(lab.ravel())
    small = [i for i in range(1, n + 1) if i not in grounded and sizes[i] <= max_voxels]
    if small:
        w.M[np.isin(lab, small)] = AIR
    return {'components': len(small), 'voxels': int(sum(sizes[i] for i in small))}


def build(graybox=False):
    w = World()
    g = gaps(w.masks)
    w.markers['gaps'] = g
    build_terrain(w)
    build_paths(w, g)
    build_spawn_pad(w)
    build_cp_dais(w)
    if not graybox:
        mounds = build_mounds(w)
        carve_hollows(w, mounds)
        build_trees(w, mounds)
        build_islets(w)
        scatter_small(w)
        # bridgehead lanterns: two posts flanking each landing
        for pts in w.markers['landings'].values():
            for (lx, ly) in pts:
                if (lx, ly) in (tuple(SPEC['spawn']), tuple(SPEC['cp'])):
                    continue
                for off in (-4, 4):
                    px, py = lx + off, ly
                    if w.land[px, py] and px <= 255:
                        # step inland until the post sits at least 2 from the water
                        mooring_post(w, px, py)
    build_skull(w)
    build_ribs(w)
    # open sky over the spawn pad and CP dais (intel/tent settle on the topmost voxel)
    xs, ys = np.nonzero(w.protect)
    for x, y in zip(xs.tolist(), ys.tolist()):
        w.M[x, y, :w.top[x, y]] = AIR
    w.markers['debris_removed'] = remove_debris(w)
    w.M = mirror_x(w.M)
    w.noprop = mirror_x(w.noprop)
    w.pathmask = mirror_x(w.pathmask)
    w.top = np.where(w.land, w.top, 63)
    return w
