"""KESTREL SPIRES - art pass v1 on top of the verified graybox (same layout, same route numbers).

Order: graybox (west half, unmirrored) -> keep-out mask of every walkable route surface ->
material remap (strata sandstone, crust, paving, trails, caprock) -> silhouette shaping (rimrock lip,
cliff flutes, tapered spire + kestrel relief, curved arch underside, hoodoo fingers, cliff dwellings)
-> vegetation/props -> mirror -> painted river / haze bottom plane.

Run: python scenes/kestrel_spires_art.py out/kestrel_spires_art
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aosmap.scene import Material                                  # noqa: E402
from aosmap import art                                             # noqa: E402
from aosmap.art import StrataShader, SurfaceShader, PatternShader  # noqa: E402
from scenes.kestrel_spires import build_graybox, mirror, SPEC, SEED, metadata_txt   # noqa: E402

SAND_BANDS = ['#e2c39a', '#d4a77a', '#c78a5c', '#b8714b', '#cf9670', '#a95f41', '#dcb48a', '#9b5639']
WALL_BANDS = ['#c9a27d', '#b9855f', '#a96d4f', '#c4936c', '#94593f', '#d2ad87']

KESTREL = [  # original 15 x 11 pictogram, wings spread; 1 = body, 2 = dark accent (eye, wing bars)
    "......1.1......",
    ".......1.......",
    "......121......",
    "11....111....11",
    "211..11111..112",
    ".2111111111112.",
    "..21111111112..",
    "....1111111....",
    ".....12121.....",
    "......111......",
    ".....1.1.1.....",
]


def build():
    s = build_graybox(mirror_output=False)
    ids = dict(s._ids)
    gm = s.mat.copy()                                      # graybox materials (west half)
    X, Y = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    zz = np.arange(64)
    west = X <= 255

    # ---------------------------------------------------------------- keep-out (walk surfaces)
    walk_ids = [ids[k] for k in ('spawn', 'route', 'bridgehead', 'flank')]
    walk = np.isin(gm, walk_ids)
    keep = np.zeros_like(walk)                             # voxels that must stay AIR
    for k in range(1, 5):
        keep[:, :, :-k] |= walk[:, :, k:]                  # 4 voxels above each walk voxel
    walk_cols = walk.any(axis=2)
    from scipy import ndimage
    near_walk = ndimage.binary_dilation(walk_cols, iterations=3)   # 2D margin for props

    # ---------------------------------------------------------------- art materials
    A = lambda name, shader: s.material(Material(name, (128, 128, 128), shader=shader))   # noqa: E731
    m_sand = A('sandstone', StrataShader(SAND_BANDS, salt=1))
    m_wall = A('wall_sandstone', StrataShader(WALL_BANDS, pattern=(4, 2, 5, 3, 2, 6), salt=2, crust='#cdb08c'))
    m_cap = A('caprock', StrataShader(['#7a4a33', '#6b3f2c', '#86533a'], pattern=(1, 1, 1), warp=1.0,
                                      crust='#8c5c42', crust_mix=0.4, salt=3))
    m_crust = A('deck_crust', SurfaceShader(top=['#d9bc90', '#e3c9a0', '#cfa97f'], side=['#b98a62'],
                                           noise_scale=16, noise_w=0.8, height_w=0, occ_dark=0.3))
    m_trail = A('trail', SurfaceShader(top=['#ead7b4', '#dfc59c'], side=['#c49e78'], noise_scale=5,
                                      noise_w=0.6, height_w=0, occ_dark=0.2))
    cx, cy = SPEC['script_constants']['bases'][0]

    def paving(x, y, z):                                    # concentric square courses around the base
        r = np.maximum(np.abs(x - cx), np.abs(y - cy))
        ring = (r // 3) % 2
        inlay = ((np.abs(x - cx) == np.abs(y - cy)) & (r % 3 == 0)).astype(int) * 2
        return np.where(r <= 1, 3, ring + inlay)
    m_pave = A('paving', PatternShader(['#e6cfa6', '#d3a983', '#b77356', '#8f4f3a'], paving))
    m_gravel = A('gravel', SurfaceShader(top=['#c9ad86', '#d8bf98', '#bf9b74', '#d1b48c'],
                                        side=['#a8835f', '#b8936d'], noise_scale=9, noise_w=0.9,
                                        height_w=0.1, occ_dark=0.45))
    m_wet = A('wet_sand', SurfaceShader(top=['#a88a68', '#bfa37f', '#d0b690'], side=['#8a6f52'],
                                       z_range=(61, 56), height_w=0.8, noise_w=0.2, noise_scale=6))
    m_adobe = A('adobe', SurfaceShader(top=['#ead2b8', '#e2c6a8'], side=['#dcbfa0', '#cfae8c'],
                                      noise_scale=4, noise_w=0.5, height_w=0, occ_dark=0.35))
    m_viga = A('viga', SurfaceShader(top=['#6b5240'], side=['#4f3b2e', '#5b4636'], noise_scale=2, height_w=0))
    m_bird = A('kestrel_inlay', SurfaceShader(top=['#f0e2c2'], side=['#eadbb8', '#f2e6c8'], noise_scale=3,
                                             height_w=0, occ_dark=0.1))
    m_bird2 = A('kestrel_dark', SurfaceShader(top=['#4b3226'], side=['#3f2a20'], noise_scale=3, height_w=0))
    m_jun = A('juniper', SurfaceShader(top=['#4f6b4e', '#5f7d58', '#6f8c62'], side=['#3a523e', '#46604a'],
                                      z_range=(60, 40), noise_scale=4, noise_w=0.7, height_w=0.3, occ_dark=0.5))
    m_wood = A('deadwood', SurfaceShader(top=['#8b7a66'], side=['#6c5c4c', '#7b6a58'], noise_scale=2, height_w=0))
    m_pool = A('rain_pool', SurfaceShader(top=['#3f8f92', '#5aa9a2'], side=['#2f6f73'], noise_scale=3,
                                         noise_w=0.5, height_w=0, occ_dark=0))
    m_niche = A('niche', SurfaceShader(top=['#5a3426'], side=['#4a2b20', '#55321f'], noise_scale=2, height_w=0,
                                      occ_dark=0.1))
    m_sage = A('sage', SurfaceShader(top=['#9aa284', '#8b957a', '#a7ad8f'], side=['#7c856c'], noise_scale=3,
                                    noise_w=0.8, height_w=0))

    # ---------------------------------------------------------------- material remap
    def remap(old, new, where=None):
        sel = gm == ids[old]
        if where is not None:
            sel &= where
        s.mat[sel] = new
    for k in ('cliff', 'terrace', 'deck'):
        remap(k, m_sand)
    remap('wall', m_wall)
    remap('canyon', m_gravel)
    remap('bank', m_wet)
    remap('route', m_trail)
    remap('spawn', m_pave)
    remap('bridgehead', m_cap)
    remap('flank', m_cap)
    solid = s.mat > 0
    top_open = np.zeros_like(solid); top_open[:, :, 1:] = solid[:, :, 1:] & ~solid[:, :, :-1]
    s.mat[top_open & (s.mat == m_sand) & ~walk] = m_crust          # dusty crust on exposed rock tops

    deck = s.markers['deck_mask']
    dz = SPEC['mesa']['deck_z']

    # ---------------------------------------------------------------- rimrock lip (caprock overhang)
    rim = ndimage.binary_dilation(deck, iterations=1) & ~deck & west
    for z in (dz, dz + 1):
        cand = rim & (s.mat[:, :, z] == 0) & ~keep[:, :, z] & ~near_walk
        s.mat[cand, z] = m_cap
    s.mat[deck & (s.mat[:, :, dz + 1] == m_sand), dz + 1] = m_cap              # cap band under the deck edge

    # ---------------------------------------------------------------- cliff flutes (vertical erosion grooves)
    ang = np.arctan2(Y - 256, X - SPEC['mesa']['center'][0])
    flute = (np.sin(ang * 46 + art.fbm(X, Y, None, scale=12, octaves=2, seed=SEED + 5) * 4) > 0.55)
    for z in range(16, 54):
        sl = s.mat[:, :, z]
        outer = (sl > 0) & ~ndimage.binary_erosion(sl > 0, iterations=1) & flute & west & ~near_walk
        outer &= np.isin(sl, [m_sand, m_wall])
        s.mat[:, :, z][outer & ~keep[:, :, z]] = 0

    # ---------------------------------------------------------------- spire: tapered base + kestrel relief
    sc = SPEC['spire']; (sx, sy) = sc['center']
    r_xy = np.sqrt((X - sx) ** 2 + (Y - sy) ** 2)
    for z in range(sc['top_z'] + 6, 63):
        r = sc['r'] + 2.8 * np.clip((z - 30) / 26.0, 0, 1) ** 1.5
        add = (r_xy < r) & (s.mat[:, :, z] == 0) & ~keep[:, :, z]
        s.mat[add, z] = m_sand
    rows = len(KESTREL)
    for v in range(-1, rows + 1):
        z = 21 + v
        for u in range(-1, len(KESTREL[0]) + 1):
            ch = KESTREL[v][u] if 0 <= v < rows and 0 <= u < len(KESTREL[0]) else '.'
            y = sy - 7 + u
            xs = np.nonzero(s.mat[:, y, z] > 0)[0]
            xs = xs[(xs >= sx) & (xs <= sx + 10)]
            if xs.size < 2:
                continue
            xo = xs.max()                                 # outermost voxel facing the platform (+x)
            if ch == '.':
                s.mat[xo, y, z] = 0                       # carve the background one voxel deep
                s.mat[xo - 1, y, z] = m_niche
            else:
                s.mat[xo, y, z] = m_bird if ch == '1' else m_bird2
    # (no protruding frame ledge: a ledge here became a landing that opened a descent route)

    # ---------------------------------------------------------------- arch: curved underside
    ax0, ax1 = SPEC['arch']['x']; ay0, ay1 = SPEC['arch']['y']
    for x in range(ax0, ax1 + 1):
        under = np.nonzero(s.mat[x, ay0, :] > 0)[0]
        if under.size == 0:
            continue
        ztop = under[0]
        e = min(x - ax0, ax1 - x)
        extra = int(max(0, 7 - 1.6 * e))
        for y in range(ay0 + 1, ay1):
            for z in range(ztop + 3, min(ztop + 3 + extra, 62)):
                if s.mat[x, y, z] == 0:
                    s.mat[x, y, z] = m_sand

    # ---------------------------------------------------------------- hoodoo fingers
    for f in SPEC['fingers']:
        fx, fy = f['center']; rr = np.sqrt((X - fx) ** 2 + (Y - fy) ** 2)
        y0, y1 = f['ramp_y']
        ramp_band = (np.abs(Y - (y0 + y1) / 2) <= (y1 - y0) / 2 + 0.5) & (X < fx)
        for z in range(f['top_z'] + 3, 63):
            if z <= f['top_z'] + 12:
                r = 2.7
            else:
                r = 2.7 + 3.0 * np.clip((z - f['top_z'] - 12) / 30.0, 0, 1)
            pillar = rr < f['r'] + 0.5
            s.mat[pillar & (rr >= r) & ~ramp_band & ~keep[:, :, z], z] = 0     # neck carve
            s.mat[(rr < r) & (s.mat[:, :, z] == 0), z] = m_sand
        cap = rr < f['r'] + 0.6
        for z in (f['top_z'] + 1, f['top_z'] + 2):
            s.mat[cap & (s.mat[:, :, z] == 0) & ~keep[:, :, z], z] = m_cap

    # ---------------------------------------------------------------- finger ramps -> rock bridges
    for f in SPEC['fingers']:
        fx, fy = f['center']; y0, y1 = f['ramp_y']
        xe = int(np.max(np.nonzero(deck[:, (y0 + y1) // 2])[0]))
        span = range(xe + 2, fx - 4)
        for x in span:
            band = s.mat[x, y0:y1 + 1, :]
            tops = [int(np.argmax(band[j] > 0)) for j in range(band.shape[0]) if band[j].any()]
            if not tops:
                continue
            zt = min(tops)
            e = min(x - span.start, span.stop - 1 - x)
            keep_th = 3 + int(max(0, 6 - 1.5 * e))          # thicker toward both ends: arched underside
            s.mat[x, y0:y1 + 1, zt + keep_th:63] = 0

    # ---------------------------------------------------------------- cliff dwellings (inner face)
    def dwelling(y0, y1, ztop=24, zfloor=35, depth=8):
        face = []
        for y in range(y0, y1 + 1):
            xs = np.nonzero(s.mat[:200, y, 30] > 0)[0]
            face.append(xs.max() if xs.size else None)
        if None in face:
            return
        xf = min(face)
        s.mat[xf - depth:xf + 4, y0:y1 + 1, ztop:zfloor] = 0                  # alcove
        s.mat[xf - depth:xf + 4, y0:y1 + 1, zfloor] = np.where(
            s.mat[xf - depth:xf + 4, y0:y1 + 1, zfloor] > 0, m_crust, 0)
        rooms = [(xf - depth + 1, xf - 3, y0 + 1, y0 + (y1 - y0) // 2 - 1, zfloor - 6),
                 (xf - depth + 1, xf - 1, y0 + (y1 - y0) // 2 + 1, y1 - 1, zfloor - 4)]
        for (a0, a1, b0, b1, rz) in rooms:
            s.mat[a0:a1 + 1, b0:b1 + 1, rz:zfloor] = m_adobe
            s.mat[a0 + 1:a1, b0 + 1:b1, rz + 1:zfloor] = 0                     # hollow
            dyc = (b0 + b1) // 2
            s.mat[a1, dyc, zfloor - 3:zfloor] = 0                              # door (T-shape top)
            s.mat[a1, dyc - 1:dyc + 2, zfloor - 3] = 0
            s.mat[a1, b0 + 1, zfloor - 4] = 0; s.mat[a1, b1 - 1, zfloor - 4] = 0   # windows
            for vy in range(b0 + 1, b1, 2):                                     # vigas through the roof line
                if s.mat[a1, vy, rz + 1] > 0 and s.mat[a1 + 1, vy, rz + 1] == 0:   # only where the wall survived
                    s.mat[a1 + 1, vy, rz + 1] = m_viga
            s.mat[a0:a1 + 1, b0:b1 + 1, rz] = m_adobe                           # flat roof
        # ladder poles from the alcove lip up the cliff (decorative, against rock)
        lx = xf + 1
        for z in range(ztop - 6, zfloor):
            if s.mat[lx, y1 - 1, z] == 0 and s.mat[lx - 1, y1 - 1, z] > 0:
                s.mat[lx, y1 - 1, z] = m_viga
    dwelling(234, 247)
    dwelling(265, 278)

    # ---------------------------------------------------------------- vegetation and props
    rng = np.random.default_rng(SEED + 40)
    topz = np.argmax(s.mat > 0, axis=2)
    spawn_sq = (np.abs(X - cx) <= 22) & (np.abs(Y - cy) <= 22)
    river_band = (X >= SPEC['bank_x_west'][0] - 3)
    ok2d = west & ~near_walk & ~spawn_sq & ~river_band & (X > 24)
    used = np.zeros((512, 512), bool)

    def surface_mat(x, y):
        return s.mat[x, y, topz[x, y]]
    # juniper groves: canyon floor and back terraces
    grove = art.fbm(X, Y, None, scale=38, octaves=2, seed=SEED + 41)
    cand = np.argwhere(ok2d & (grove > 0.58) & (topz < 62))
    rng.shuffle(cand)
    n_trees = 0
    for x, y in cand:
        if n_trees >= 70:
            break
        if used[max(x - 4, 0):x + 5, max(y - 4, 0):y + 5].any():
            continue
        if surface_mat(x, y) not in (m_gravel, m_crust, m_sand):
            continue
        win = topz[x - 1:x + 2, y - 1:y + 2]
        if win.max() != win.min():
            continue
        pf = art.tree(SEED + 500 + n_trees, m_wood, m_jun, height=int(rng.integers(3, 6)),
                      crown_r=float(rng.uniform(2.4, 3.4)), crown_h=3, lean=float(rng.uniform(-1.2, 1.2)))
        fz = int(topz[x, y])
        ok = True
        h = pf.a.shape[2]
        ox, oy = pf.origin
        xx0, yy0 = x - ox, y - oy
        reg = (slice(max(xx0, 0), xx0 + pf.a.shape[0]), slice(max(yy0, 0), yy0 + pf.a.shape[1]),
               slice(max(fz - h, 0), fz))
        if keep[reg].any() or (s.mat[reg] > 0).sum() > 0:
            ok = False
        if ok:
            art.stamp(s, pf, int(x), int(y), fz, replace_air_only=True)
            used[x - 3:x + 4, y - 3:y + 4] = True
            n_trees += 1
    # sage tufts (1-2 voxels) scattered on gravel and crust, denser near groves
    cand = np.argwhere(ok2d & (topz < 62) & (topz > 2))
    rng.shuffle(cand)
    n_sage = 0
    for x, y in cand[:9000]:
        if n_sage >= 300 or used[x, y]:
            continue
        if surface_mat(x, y) not in (m_gravel, m_crust):
            continue
        if grove[x, y] < 0.5 or rng.random() > 1.6 * (grove[x, y] - 0.45):
            continue                                       # clumps follow the grove noise, not uniform speckle
        z = int(topz[x, y]) - 1
        if keep[x, y, z]:
            continue
        s.mat[x, y, z] = m_sage
        for (ddx, ddy) in ((1, 0), (0, 1), (-1, 0), (0, -1)):
            if rng.random() < 0.5 and s.mat[x + ddx, y + ddy, z] == 0 and s.mat[x + ddx, y + ddy, z + 1] > 0 \
                    and not keep[x + ddx, y + ddy, z]:
                s.mat[x + ddx, y + ddy, z] = m_sage
        if rng.random() < 0.3 and not keep[x, y, z - 1]:
            s.mat[x, y, z - 1] = m_sage
        used[x, y] = True
        n_sage += 1
    # talus boulders at the foot of the mesa cliffs
    foot = ndimage.binary_dilation(deck, iterations=14) & ~ndimage.binary_dilation(deck, iterations=8) & ok2d
    cand = np.argwhere(foot & (topz >= 55))
    rng.shuffle(cand)
    n_b = 0
    for x, y in cand:
        if n_b >= 26:
            break
        if used[max(x - 3, 0):x + 4, max(y - 3, 0):y + 4].any():
            continue
        pf = art.boulder(SEED + 800 + n_b, m_sand, r=float(rng.uniform(1.8, 3.4)))
        art.stamp(s, pf, int(x), int(y), int(topz[x, y]), replace_air_only=True)
        used[x - 3:x + 4, y - 3:y + 4] = True
        n_b += 1

    # deck outcrops: small caprock-topped rock stacks for cover on the open mesa top
    deck_ok = deck & ~near_walk & ~spawn_sq & ~ndimage.binary_dilation(~deck, iterations=4)
    cand = np.argwhere(deck_ok)
    rng.shuffle(cand)
    n_out = 0
    for x, y in cand:
        if n_out >= 7:
            break
        if used[max(x - 7, 0):x + 8, max(y - 7, 0):y + 8].any():
            continue
        h = int(rng.integers(3, 6)); r0 = float(rng.uniform(2.0, 3.2))
        rr = np.sqrt((X[x - 5:x + 6, y - 5:y + 6] - x) ** 2 + (Y[x - 5:x + 6, y - 5:y + 6] - y) ** 2)
        wob = art.value_noise(X[x - 5:x + 6, y - 5:y + 6], Y[x - 5:x + 6, y - 5:y + 6], None, scale=2.0,
                              seed=SEED + 900 + n_out) * 1.2
        for k in range(h):
            z = dz - 1 - k
            r = r0 + 0.6 - 0.5 * k / max(h - 1, 1) + (0.8 if k == h - 1 else 0)   # flared cap
            sel = (rr + wob < r)
            s.mat[x - 5:x + 6, y - 5:y + 6, z][sel] = m_cap if k == h - 1 else m_sand
        used[x - 7:x + 8, y - 7:y + 8] = True
        n_out += 1
    # rain basins: shallow 1-voxel pools in the deck rock (visual only; standable)
    n_pool = 0
    for x, y in cand[::-1]:
        if n_pool >= 4:
            break
        if used[max(x - 5, 0):x + 6, max(y - 5, 0):y + 6].any():
            continue
        rr = np.sqrt((X[x - 4:x + 5, y - 4:y + 5] - x) ** 2 + ((Y[x - 4:x + 5, y - 4:y + 5] - y) * 1.4) ** 2)
        s.mat[x - 4:x + 5, y - 4:y + 5, dz][rr < 3.2] = 0
        s.mat[x - 4:x + 5, y - 4:y + 5, dz + 1][rr < 3.2] = m_pool
        s.mat[x - 4:x + 5, y - 4:y + 5, dz + 1][(rr >= 3.2) & (rr < 4.0) & (s.mat[x - 4:x + 5, y - 4:y + 5, dz] == 0)] = m_crust
        used[x - 5:x + 6, y - 5:y + 6] = True
        n_pool += 1
    s.markers.update({'outcrops': n_out, 'pools': n_pool})

    mirror(s)

    # ---------------------------------------------------------------- painted bottom: river + desert haze
    rx = np.abs(X - 256)
    haze = np.stack([np.full((512, 512), 198), np.full((512, 512), 168), np.full((512, 512), 138)], -1).astype(float)
    hn = art.fbm(X, Y, None, scale=60, octaves=3, seed=SEED + 70)[..., None]
    haze = haze * (0.9 + 0.2 * hn)
    t = np.clip(rx / 30.0, 0, 1)[..., None]
    deep, shallow = np.array([28, 120, 128]), np.array([96, 178, 166])
    ripple = art.fbm(X, Y * 0.4, None, scale=9, octaves=2, seed=SEED + 71)[..., None]
    water = deep * (1 - t) + shallow * t
    water = water * (0.92 + 0.16 * ripple)
    in_canyon = (Y >= SPEC['play_space']['y'][0]) & (Y <= SPEC['play_space']['y'][1])
    bottom = np.where((in_canyon & (rx <= 30))[..., None], water, haze)
    s.paint_bottom(np.clip(bottom, 0, 255).astype(np.uint8))
    s.markers.update({'trees': n_trees, 'sage': n_sage, 'boulders': n_b})
    return s


if __name__ == '__main__':
    from aosmap.vxl import write_vxl
    out = sys.argv[1] if len(sys.argv) > 1 else 'out/kestrel_spires_art'
    os.makedirs(out, exist_ok=True)
    s = build()
    vm = s.to_voxelmap()
    data = write_vxl(vm)
    open(os.path.join(out, 'kestrel_spires.vxl'), 'wb').write(data)
    txt = metadata_txt().replace('graybox v1', 'art v1').replace(' Graybox - layout only.', '')
    open(os.path.join(out, 'kestrel_spires.txt'), 'w').write(txt)
    json.dump(SPEC, open(os.path.join(out, 'spec.json'), 'w'), indent=1, default=list)
    print('written', len(data), 'bytes', {k: v for k, v in s.markers.items() if k in ('trees', 'sage', 'boulders', 'outcrops', 'pools')})
