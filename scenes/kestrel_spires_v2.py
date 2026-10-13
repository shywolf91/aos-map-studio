"""KESTREL SPIRES art v2 features (called from scenes/kestrel_spires_art.py with version=2).

All functions author the WEST half only (x <= 255); the caller mirrors afterwards.
Rules every feature follows:
  * never touch the walk keep-out (`keep`) or the 2D route margin (`near_walk`);
  * stay grounded (everything is built up from the canyon floor / cliff / alcove floor);
  * no new standable perch more than 3 voxels above the canyon floor (z 56) in the canyon;
  * rises the player meets are either 1 voxel (walkable) or >= 3 (a wall), never a 2-voxel trap.
"""
import numpy as np
from scipy import ndimage

from aosmap import art
from aosmap.art import SurfaceShader, StrataShader
from aosmap.scene import Material

FLOOR = 56

# dry-wash centre lines (west half). North wash skirts the mesa terraces and bends into the inner canyon
# toward the river; the south wash mirrors the idea with a different meander (both teams get both).
WASHES = [
    [(30, 184), (58, 179), (86, 183), (112, 180), (138, 184), (160, 190), (176, 200), (189, 213),
     (199, 225), (209, 233), (214, 236)],
    [(30, 330), (62, 334), (94, 329), (122, 332), (148, 326), (168, 316), (184, 303), (196, 291),
     (207, 282), (214, 279)],
]


def materials(s):
    A = lambda name, shader: s.material(Material(name, (128, 128, 128), shader=shader))   # noqa: E731
    return {
        'bed': A('wash_bed', SurfaceShader(top=['#8c8472', '#9a917c', '#827a68'], side=['#736b5b'],
                                           noise_scale=7, noise_w=0.7, height_w=0, occ_dark=0.35)),
        'pebble': A('pebble', SurfaceShader(top=['#b5a991', '#aa9e86'], side=['#978b75'], noise_scale=2,
                                            noise_w=0.6, height_w=0, occ_dark=0.1)),
        'slick': A('slickrock', StrataShader(['#c98a66', '#b8754f', '#d39a74', '#a9663f'], pattern=(1, 1, 1, 1),
                                             warp=0.6, crust='#d7a382', crust_mix=0.45, salt=7)),
        'buttress': A('buttress', StrataShader(['#c9a27d', '#b9855f', '#a96d4f', '#c4936c', '#94593f', '#d2ad87'],
                                               pattern=(4, 2, 5, 3, 2, 6), salt=2, crust=None)),
        'varnish': A('desert_pavement', SurfaceShader(top=['#b8987a', '#c4a585', '#ad8d6f'],
                                                      side=['#9c7d61'], noise_scale=8, noise_w=0.8,
                                                      height_w=0, occ_dark=0.45)),
        'shadow': A('alcove_shadow', SurfaceShader(top=['#7d4e39'], side=['#6c412f', '#764834'],
                                                   noise_scale=3, noise_w=0.5, height_w=0, occ_dark=0.2)),
        'cotton': A('cottonwood', SurfaceShader(top=['#a7b25a', '#bcbf62', '#94a24f'], side=['#7d8a43', '#8c9849'],
                                                z_range=(56, 44), noise_scale=4, noise_w=0.7, height_w=0.3,
                                                occ_dark=0.5)),
    }


def _polyline_distance(points, X, Y, step=0.5):
    pts = []
    for (x0, y0), (x1, y1) in zip(points[:-1], points[1:]):
        n = max(2, int(np.hypot(x1 - x0, y1 - y0) / step))
        t = np.linspace(0, 1, n, endpoint=False)
        pts.append(np.stack([x0 + (x1 - x0) * t, y0 + (y1 - y0) * t], 1))
    pts.append(np.array([points[-1]], float))
    P = np.concatenate(pts)
    from scipy.spatial import cKDTree
    d, _ = cKDTree(P).query(np.stack([X.ravel(), Y.ravel()], 1))
    return d.reshape(X.shape)


def canyon(s, c, M, seed):
    """Dry washes, pebble beds, desert-pavement patches, slickrock benches and bank fins."""
    X, Y, keep, near_walk = c['X'], c['Y'], c['keep'], c['near_walk']
    west = X <= 255
    topz = np.argmax(s.mat > 0, axis=2)
    floor = west & (topz == FLOOR) & (s.mat[:, :, FLOOR] == c['m_gravel'])
    rng = np.random.default_rng(seed + 140)

    # desert pavement: large dark patches on the open floor (coherent, not speckle)
    pav = art.fbm(X, Y, None, scale=26, octaves=3, seed=seed + 141)
    s.mat[:, :, FLOOR][floor & (pav > 0.6)] = M['varnish']

    # dry washes: terraced profile (depth 1/2/3), so every edge is a 1-voxel step - never a trap
    wash_d = np.full(X.shape, 1e9)
    for line in WASHES:
        wash_d = np.minimum(wash_d, _polyline_distance(line, X, Y))
    wob = (art.fbm(X, Y, None, scale=7, octaves=2, seed=seed + 142) - 0.5) * 0.9
    dd = wash_d + wob
    depth = np.where(dd < 2.2, 3, np.where(dd < 3.4, 2, np.where(dd < 4.6, 1, 0)))
    can = floor | (west & (topz == FLOOR))                       # incl. pavement just painted
    can &= ~near_walk & (X < 214)
    depth = np.where(can, depth, 0)
    bed_cols = []
    for k in (1, 2, 3):
        sel = depth == k
        for dz in range(k):
            s.mat[:, :, FLOOR + dz][sel] = 0
        s.mat[:, :, FLOOR + k][sel] = M['bed'] if k == 3 else M['slick']   # cut banks show pink rock
        if k == 3:
            bed_cols = np.argwhere(sel)
    # pebbles: 1-voxel pale stones on the bed (step-over height)
    n_peb = 0
    for x, y in bed_cols[rng.permutation(len(bed_cols))[:max(1, len(bed_cols) // 30)]]:
        if not keep[x, y, FLOOR + 2]:
            s.mat[x, y, FLOOR + 2] = M['pebble']; n_peb += 1

    # slickrock benches in the inner canyon: 3 tiers of 1 voxel (walkable steps), top at z 53
    topz = np.argmax(s.mat > 0, axis=2)
    occupied = ndimage.binary_dilation((topz < FLOOR) & west, iterations=5)   # spire, fingers, talus, cliff
    zone = west & (X >= 170) & (X <= 206) & (Y >= 182) & (Y <= 330) & (topz == FLOOR) & ~occupied
    zone &= ~near_walk & (wash_d > 6)
    used = np.zeros(X.shape, bool)
    benches = []
    cand = np.argwhere(zone)
    rng.shuffle(cand)
    for x, y in cand:
        if len(benches) >= 5:
            break
        if used[max(x - 12, 0):x + 13, max(y - 12, 0):y + 13].any():
            continue
        a, b = rng.uniform(4.5, 6.5), rng.uniform(3.0, 4.5)
        th = rng.uniform(0, np.pi)
        dx, dy = X - x, Y - y
        u = (dx * np.cos(th) + dy * np.sin(th)) / a
        v = (-dx * np.sin(th) + dy * np.cos(th)) / b
        n = (art.value_noise(X, Y, None, scale=2.5, seed=seed + 150 + len(benches)) - 0.5) * 0.35
        r = np.sqrt(u * u + v * v) + n
        t1 = (r < 1.0) & zone
        t2 = (r < 0.68) & zone
        t3 = (r < 0.38) & zone
        if t1.sum() < 25:
            continue
        s.mat[:, :, FLOOR - 1][t1] = M['slick']
        s.mat[:, :, FLOOR - 2][t2] = M['slick']
        s.mat[:, :, FLOOR - 3][t3] = M['slick']
        used |= ndimage.binary_dilation(t1, iterations=3)
        benches.append((int(x), int(y)))

    # bank fins: sandstone blades by the river (line-of-sight breaks). 3 thick, 7-9 high, sheer sides,
    # crown narrows to 1 - the top is not reachable on foot (nearest standable surface is the floor).
    fins = []
    for (fx, fy, L, H) in ((203, 244, 6, 9), (204, 269, 5, 8)):
        if near_walk[fx - 2:fx + 3, fy - L - 1:fy + L + 2].any():
            continue
        nz = art.value_noise(np.arange(-L, L + 1), np.zeros(2 * L + 1), None, scale=2.0, seed=seed + 181 + fx)
        for j in range(-L, L + 1):
            e = 1 - abs(j) / (L + 1)
            h = int(round(H * (0.4 + 0.6 * e ** 0.5) + (nz[j + L] - 0.5) * 4))
            for i in (-1, 0, 1):
                hh = h - (2 if i != 0 else 0)
                if hh < 3 or s.mat[fx + i, fy + j, FLOOR] == 0 or s.mat[fx + i, fy + j, FLOOR - 1] != 0:
                    continue
                s.mat[fx + i, fy + j, FLOOR - hh:FLOOR] = c['m_sand']
                s.mat[fx + i, fy + j, FLOOR - hh] = c['m_cap']
        fins.append((fx, fy))
    return {'wash_d': wash_d, 'pebbles': n_peb, 'benches': benches, 'fins': fins}


def walls(s, c, M, seed):
    """Buttresses and slot recesses that break the long outer canyon walls (scenery, not climbable)."""
    X, Y, near_walk = c['X'], c['Y'], c['near_walk']
    rng = np.random.default_rng(seed + 160)
    out = {'buttresses': 0, 'slots': 0}
    m_wall, m_gravel = c['m_wall'], c['m_gravel']
    for face_y, sgn in ((171, 1), (341, -1)):           # sgn: direction from the wall into the canyon
        xs = [34, 66, 104, 142, 178, 206]
        for bx in xs:
            bx += int(rng.integers(-5, 6))
            w = rng.uniform(3.0, 4.5); p0 = rng.uniform(4.0, 6.0)
            col_top = np.argmax(s.mat[bx, face_y - 6 * sgn] > 0)        # wall top z behind the face
            if near_walk[bx - 6:bx + 7, min(face_y, face_y + 8 * sgn):max(face_y, face_y + 8 * sgn) + 1].any():
                continue
            for z in range(col_top + 2, FLOOR):
                f = 1.0 if z >= FLOOR - 6 else 0.35 + 0.65 * ((z - col_top) / (FLOOR - 6 - col_top)) ** 1.3
                p, ww = p0 * f, w * (0.7 + 0.3 * f)
                sel = (((X - bx) / ww) ** 2 + ((Y - face_y) / max(p, 0.6)) ** 2 < 1.0) & ((Y - face_y) * sgn > 0)
                sel &= s.mat[:, :, z] == 0
                s.mat[:, :, z][sel] = M['buttress']
            out['buttresses'] += 1
        # slot recesses between buttresses (walk-in, dark interior)
        for sx in (50 + int(rng.integers(-4, 5)), 160 + int(rng.integers(-4, 5))):
            depth = int(rng.integers(6, 9)); half = int(rng.integers(2, 3))
            if near_walk[sx - half - 2:sx + half + 3, min(face_y, face_y - depth * sgn):max(face_y, face_y - depth * sgn) + 1].any():
                continue
            carved = np.zeros(s.mat.shape, bool)
            for dxs in range(-half, half + 1):
                ztop = 26 + 3 * abs(dxs)                       # rounded head of the slot
                for k in range(depth):
                    y = face_y - k * sgn
                    zt = ztop + 2 * k                           # roof steps down going in
                    carved[sx + dxs, y, zt:FLOOR] = s.mat[sx + dxs, y, zt:FLOOR] > 0
                    s.mat[sx + dxs, y, zt:FLOOR] = 0
                    s.mat[sx + dxs, y, FLOOR] = m_gravel
            lining = ndimage.binary_dilation(carved, iterations=1) & np.isin(s.mat, [m_wall, M['buttress']])
            s.mat[lining] = M['shadow']
            out['slots'] += 1
    return out


def dwelling(s, c, M, y0, y1, flip, ztop=23, zfloor=35, depth=9):
    """Cliff dwelling v2: arched alcove with a shadowed back wall, a two-storey tower, a terraced room
    block and a low parapet court. Scenery only (the alcove floor is 21 voxels above the canyon floor)."""
    m_adobe, m_viga, m_crust = c['m_adobe'], c['m_viga'], c['m_crust']
    face = []
    for y in range(y0, y1 + 1):
        xs = np.nonzero(s.mat[:200, y, 30] > 0)[0]
        face.append(xs.max() if xs.size else None)
    if None in face:
        return False
    xf = min(face)
    xa = xf - depth
    carved = np.zeros(s.mat.shape, bool)
    for y in range(y0, y1 + 1):                                  # arched mouth: higher in the middle
        e = min(y - y0, y1 - y)
        zc = ztop + max(0, 3 - e)
        carved[xa:xf + 4, y, zc:zfloor] = s.mat[xa:xf + 4, y, zc:zfloor] > 0
        s.mat[xa:xf + 4, y, zc:zfloor] = 0
    fl = s.mat[xa:xf + 4, y0:y1 + 1, zfloor]
    s.mat[xa:xf + 4, y0:y1 + 1, zfloor] = np.where(fl > 0, m_crust, 0)
    # shadow lining: back wall, sides and ceiling of the alcove (only faces of the carved hollow)
    lining = ndimage.binary_dilation(carved, iterations=1) & (s.mat > 0) & (s.mat != m_crust)
    s.mat[lining] = M['shadow']
    # room blocks along y (optionally flipped so the two dwellings differ)
    W = y1 - y0 - 1
    parts = [('tower', 4, 8, 4), ('rooms', 5, 5, 2), ('court', W - 9, 2, 1)]
    if flip:
        parts = parts[::-1]
    yc = y0 + 1
    for kind, wy, h, setback in parts:
        b0, b1 = yc, yc + wy - 1
        yc = b1 + 1
        a0, a1 = xa + 1, xf - setback
        rz = zfloor - h
        if kind == 'court':                                     # low parapet wall around a small court
            s.mat[a0:a1 + 1, b0:b1 + 1, rz:zfloor] = m_adobe
            s.mat[a0 + 1:a1, b0 + 1:b1, rz:zfloor] = 0
            continue
        s.mat[a0:a1 + 1, b0:b1 + 1, rz:zfloor] = m_adobe
        s.mat[a0 + 1:a1, b0 + 1:b1, rz + 1:zfloor] = 0                 # hollow
        dyc = (b0 + b1) // 2
        s.mat[a1, dyc, zfloor - 3:zfloor] = 0                          # T-door
        s.mat[a1, dyc - 1:dyc + 2, zfloor - 3] = 0
        if kind == 'tower':                                            # upper storey steps back 3 over a terrace
            s.mat[a1 - 2:a1 + 1, b0:b1 + 1, rz:rz + 2] = 0
            s.mat[a1 - 2:a1 + 1, b0:b1 + 1, rz + 2] = m_adobe          # terrace roof
            s.mat[a1 - 3, b0:b1 + 1, rz:rz + 2] = m_adobe              # upper-storey front wall
            s.mat[a1 - 3, dyc, rz + 1] = 0                             # its window
        else:
            s.mat[a1, b0 + 1, zfloor - 4] = 0; s.mat[a1, b1 - 1, zfloor - 4] = 0
        for vy in range(b0 + 1, b1, 2):                                # vigas only where the wall survived
            zv = rz + 1 if kind != 'tower' else rz + 3
            if s.mat[a1, vy, zv] > 0 and s.mat[a1 + 1, vy, zv] == 0:
                s.mat[a1 + 1, vy, zv] = m_viga
    lx = xf + 1                                                        # ladder pole
    ly = y1 - 1 if not flip else y0 + 1
    for z in range(ztop - 6, zfloor):
        if s.mat[lx, ly, z] == 0 and s.mat[lx - 1, ly, z] > 0:
            s.mat[lx, ly, z] = m_viga
    return True


def mini_mesa(s, c, x, y, rng, seed):
    """Deck outcrop v2: a low, wide, three-tier mini mesa (1-voxel tiers, so it can be climbed)."""
    X, Y = c['X'], c['Y']
    dz = c['deck_z']
    sl = (slice(x - 7, x + 8), slice(y - 7, y + 8))
    rx, ry = rng.uniform(4.0, 5.5), rng.uniform(3.2, 4.5)
    th = rng.uniform(0, np.pi)
    dx, dy = X[sl] - x, Y[sl] - y
    u = (dx * np.cos(th) + dy * np.sin(th)) / rx
    v = (-dx * np.sin(th) + dy * np.cos(th)) / ry
    n = (art.value_noise(X[sl], Y[sl], None, scale=2.0, seed=seed) - 0.5) * 0.4
    r = np.sqrt(u * u + v * v) + n
    for k, (rad, mid) in enumerate(((1.0, c['m_sand']), (0.68, c['m_sand']), (0.42, c['m_cap']))):
        z = dz - 1 - k
        sel = (r < rad) & (s.mat[sl][:, :, z] == 0) & ~c['keep'][sl][:, :, z]
        s.mat[sl][:, :, z][sel] = mid


def cottonwoods(s, c, M, wash_d, used, seed, limit=8):
    """Riparian cottonwoods along the wash banks and the river side of the canyon."""
    X, Y, keep, near_walk = c['X'], c['Y'], c['keep'], c['near_walk']
    rng = np.random.default_rng(seed + 170)
    topz = np.argmax(s.mat > 0, axis=2)
    zone = (X <= 255) & (topz == FLOOR) & ~near_walk & (((wash_d > 4.5) & (wash_d < 7)) | ((X >= 196) & (X < 212)))
    zone &= (X > 30)
    cand = np.argwhere(zone)
    rng.shuffle(cand)
    n = 0
    for x, y in cand:
        if n >= limit:
            break
        if used[max(x - 6, 0):x + 7, max(y - 6, 0):y + 7].any():
            continue
        win = topz[x - 1:x + 2, y - 1:y + 2]
        if win.max() != win.min():
            continue
        pf = art.tree(seed + 700 + n, c['m_wood'], M['cotton'], height=int(rng.integers(6, 9)),
                      crown_r=float(rng.uniform(3.4, 4.4)), crown_h=4, lean=float(rng.uniform(-0.8, 0.8)))
        ox, oy = pf.origin
        h = pf.a.shape[2]
        reg = (slice(max(x - ox, 0), x - ox + pf.a.shape[0]), slice(max(y - oy, 0), y - oy + pf.a.shape[1]),
               slice(max(FLOOR - h, 0), FLOOR))
        if keep[reg].any() or (s.mat[reg] > 0).any():
            continue
        art.stamp(s, pf, int(x), int(y), FLOOR, replace_air_only=True)
        used[x - 5:x + 6, y - 5:y + 6] = True
        n += 1
    return n
