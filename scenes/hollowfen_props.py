"""Original voxel prefabs for Hollowfen. Local axes: a[i, j, k] with k = 0 the LOWEST layer (art.stamp puts
k = 0 directly on the floor voxel). Every prefab is a single face-connected component unless noted
(witches are floating by request). Material ids are passed in a dict `m`."""
import numpy as np
from scipy import ndimage

from aosmap import art
from aosmap.art import Prefab


def _keep_connected_to_base(a):
    lab, _ = ndimage.label(a > 0, structure=ndimage.generate_binary_structure(3, 1))
    base = np.unique(lab[:, :, 0][lab[:, :, 0] > 0])
    a[~np.isin(lab, base)] = 0
    return a


# ------------------------------------------------------------------------------------------------ houses
def house(seed, w, d, storeys, m, plaster, roof, ridge='x', jetty=False, lit=0.45):
    """Timber-framed house, front (door) at j = 0. w along i, d along j.
    k0 stone plinth/floor; ground storey k1-4; floor beam k5; upper storeys 4 tall each; steep 1:1 gable roof
    (2-voxel-thick rows so every roof row touches the one below); chimney; lit/dark windows."""
    rng = np.random.default_rng(seed)
    jf = 1 if jetty else 0                       # upper storeys overhang the front by one voxel
    H = 1 + 4 * storeys + storeys + max(w, d) // 2 + 6
    a = np.zeros((w + 2, d + 2 + jf, H), np.uint8)
    o = 1 + jf                                   # array j index of the ground-storey front wall
    i0, i1 = 1, w                                # inclusive i range of walls
    j0, j1 = o, o + d - 1
    win = lambda: m['win_lit'] if rng.random() < lit else m['win_dark']  # noqa: E731
    a[i0:i1 + 1, j0:j1 + 1, 0] = m['stone']
    kt = 0
    for st in range(storeys):
        kb = 1 + st * 5                          # storey wall layers kb..kb+3, beam at kb+4
        fj0 = j0 - (jf if st > 0 else 0)         # jetty: upper storeys start one voxel further out
        for k in range(kb, kb + 4):
            a[i0:i1 + 1, fj0:j1 + 1, k] = plaster
            a[i0 + 1:i1, fj0 + 1:j1, k] = 0
            for (ii, jj) in ((i0, fj0), (i1, fj0), (i0, j1), (i1, j1)):
                a[ii, jj, k] = m['timber']
            for ii in range(i0 + 3, i1 - 1, 3):                 # studs on long walls
                a[ii, fj0, k] = m['timber']; a[ii, j1, k] = m['timber']
            for jj in range(fj0 + 3, j1 - 1, 3):
                a[i0, jj, k] = m['timber']; a[i1, jj, k] = m['timber']
        # diagonal braces at the front corners of upper storeys
        if st > 0:
            for t in range(3):
                if i0 + 1 + t < i1:
                    a[i0 + 1 + t, fj0, kb + t] = m['timber']
                if i1 - 1 - t > i0:
                    a[i1 - 1 - t, fj0, kb + t] = m['timber']
        # beam / floor at kb+4 (full slab: the ceiling of this storey)
        a[i0:i1 + 1, fj0:j1 + 1, kb + 4] = m['timber']
        if st + 1 < storeys and jf:
            a[i0:i1 + 1, fj0 - 1, kb + 4] = m['timber']          # jetty joists carry the next storey
        # windows: 2 wide x 2 tall, between studs
        for ii in range(i0 + 1, i1 - 1, 3):
            for jj in (fj0, j1):
                if st == 0 and jj == fj0 and abs(ii - (i0 + i1) // 2) <= 1:
                    continue                                    # door bay
                if rng.random() < 0.8:
                    c = win()
                    a[ii:ii + 2, jj, kb + 1:kb + 3] = c
        for jj in range(fj0 + 1, j1 - 1, 3):
            for ii in (i0, i1):
                if rng.random() < 0.5:
                    a[ii, jj:jj + 2, kb + 1:kb + 3] = win()
        kt = kb + 4
    # door: 2 wide, 3 tall, timber lintel
    dc = (i0 + i1) // 2
    a[dc:dc + 2, j0, 1:4] = 0
    a[dc - 1:dc + 3, j0, 4] = m['timber']
    # roof
    if ridge == 'x':
        jl, jh = j0 - jf - 1, j1 + 1                            # eave rows (outside the walls)
        s = 0
        while jl + s <= jh - s:
            k = kt + 1 + s
            for jj in (jl + s, jl + s + 1, jh - s - 1, jh - s):
                if jl <= jj <= jh:
                    a[0:w + 2, jj, k] = roof
            if jl + s + 2 <= jh - s - 2:
                a[i0, jl + s + 2:jh - s - 1, k] = plaster       # gable ends
                a[i1, jl + s + 2:jh - s - 1, k] = plaster
            s += 1
        ridge_k = kt + s
        a[0:w + 2, (jl + jh) // 2, ridge_k] = m['ridge']
        if s > 4:                                               # attic window in each gable
            a[i0, (jl + jh) // 2, kt + 3] = win(); a[i1, (jl + jh) // 2, kt + 3] = win()
    else:                                                        # gable faces the street
        il, ih = 0, w + 1
        s = 0
        while il + s <= ih - s:
            k = kt + 1 + s
            for ii in (il + s, il + s + 1, ih - s - 1, ih - s):
                if il <= ii <= ih:
                    a[ii, j0 - jf - 1:j1 + 2, k] = roof
            if il + s + 2 <= ih - s - 2:
                a[il + s + 2:ih - s - 1, j0 - jf, k] = plaster  # front gable
                a[il + s + 2:ih - s - 1, j1, k] = plaster
            s += 1
        ridge_k = kt + s
        a[(il + ih) // 2, j0 - jf - 1:j1 + 2, ridge_k] = m['ridge']
        if s > 4:
            a[(il + ih) // 2, j0 - jf, kt + 3] = win()
    # chimney: 2x2 stone stack against the back wall, through the roof
    ci = i0 + 1 if rng.random() < 0.5 else i1 - 2
    top_k = min(ridge_k + 2, a.shape[2] - 1)
    a[ci:ci + 2, j1 - 2:j1, 1:top_k + 1] = m['stone']
    a[ci:ci + 2, j1 - 2:j1, top_k] = m['chimney_top']
    k_used = np.nonzero(a.any(axis=(0, 1)))[0]
    a = a[:, :, :k_used.max() + 1]
    return Prefab(_keep_connected_to_base(a), origin=(1, o), name='house')


# ------------------------------------------------------------------------------------------------ nature
def pine(seed, m, height=12, r0=3.6):
    rng = np.random.default_rng(seed)
    R = int(np.ceil(r0)) + 1
    a = np.zeros((2 * R + 1, 2 * R + 1, height + 2), np.uint8)
    a[R, R, 0:height] = m['trunk_dark']
    ii, jj = np.meshgrid(np.arange(2 * R + 1), np.arange(2 * R + 1), indexing='ij')
    d = np.hypot(ii - R, jj - R)
    k0 = 2 + int(rng.integers(0, 2))
    for k in range(k0, height + 1):
        t = (k - k0) / max(height - k0, 1)
        r = r0 * (1 - t) * (0.75 + 0.25 * ((k - k0) % 3 == 0)) + 0.6       # tiered skirts
        a[:, :, k][(d <= r) & (a[:, :, k] == 0)] = m['pine']
    a[R, R, height + 1] = m['pine']
    return Prefab(_keep_connected_to_base(a), origin=(R, R), name='pine')


def dead_tree(seed, wood, height=9, spread=4):
    """Gnarled leafless tree: leaning trunk + 3-5 crooked branches built from face-connected L-steps."""
    rng = np.random.default_rng(seed)
    R = spread + 3
    a = np.zeros((2 * R + 1, 2 * R + 1, height + spread + 3), np.uint8)
    x, y = R, R
    for k in range(height):
        a[x, y, k] = wood
        if k < 2:
            a[x + 1, y, k] = wood; a[x, y + 1, k] = wood                 # root flare
        if rng.random() < 0.25 and k > 2:
            nx, ny = x + int(rng.integers(-1, 2)), y + int(rng.integers(-1, 2))
            nx, ny = int(np.clip(nx, 2, 2 * R - 2)), int(np.clip(ny, 2, 2 * R - 2))
            a[nx, y, k] = wood; a[nx, ny, k] = wood
            x, y = nx, ny
    tips = []
    for b in range(int(rng.integers(3, 6))):
        k = int(rng.integers(height // 2, height))
        ang = rng.uniform(0, 2 * np.pi)
        bx, by, bk = x, y, k
        for step in range(int(rng.integers(2, spread + 1))):
            nx = int(np.clip(round(bx + np.cos(ang)), 0, 2 * R)); ny = int(np.clip(round(by + np.sin(ang)), 0, 2 * R))
            nk = min(bk + (1 if rng.random() < 0.6 else 0), a.shape[2] - 1)
            a[nx, by, bk] = wood; a[nx, ny, bk] = wood; a[nx, ny, nk] = wood
            bx, by, bk = nx, ny, nk
            ang += rng.uniform(-0.6, 0.6)
        tips.append((bx, by, bk))
    for (bx, by, bk) in tips:                                           # twig forks
        if bk + 1 < a.shape[2]:
            a[bx, by, bk + 1] = wood
    k_used = np.nonzero(a.any(axis=(0, 1)))[0]
    return Prefab(_keep_connected_to_base(a[:, :, :k_used.max() + 1]), origin=(R, R), name='dead_tree')


def bush(seed, leaf, r=1.6):
    R = int(np.ceil(r)) + 1
    ii, jj, kk = np.meshgrid(np.arange(2 * R + 1), np.arange(2 * R + 1), np.arange(R + 1), indexing='ij')
    n = art.value_noise(ii, jj, kk, scale=1.7, seed=seed) - 0.5
    a = np.where(np.sqrt((ii - R) ** 2 + (jj - R) ** 2 + (kk * 1.5) ** 2) + n < r, leaf, 0).astype(np.uint8)
    a[R, R, 0] = leaf
    return Prefab(_keep_connected_to_base(a), origin=(R, R), name='bush')


# ------------------------------------------------------------------------------------------------ halloween props
def pumpkin(seed, m, size=2, lantern=False, face='-j'):
    """size 1..3 pumpkin with a stem; lantern=True carves a glowing face on one side."""
    s = size
    a = np.zeros((s + 2, s + 2, s + 1), np.uint8)
    a[1:s + 1, 1:s + 1, 0:s] = m['pumpkin']
    if s >= 2:
        a[1, 1, s - 1] = 0; a[s, 1, s - 1] = 0; a[1, s, s - 1] = 0; a[s, s, s - 1] = 0   # rounded top corners
        for ii in range(1, s + 1, 2):
            a[ii, 1:s + 1, 0:s] = np.where(a[ii, 1:s + 1, 0:s] > 0, m['pumpkin_dark'], 0)   # ribs
    a[1 + s // 2, 1 + s // 2, s] = m['stem']
    if a[1 + s // 2, 1 + s // 2, s - 1] == 0:
        a[1 + s // 2, 1 + s // 2, s - 1] = m['pumpkin']
    if lantern and s >= 2:
        if face == '-j':
            a[1:s + 1, 1, 0:s - 1] = m['glow']
        else:
            a[1, 1:s + 1, 0:s - 1] = m['glow']
    return Prefab(_keep_connected_to_base(a), origin=(1, 1), name='pumpkin')


def lamp_post(m, h=4):
    a = np.zeros((3, 3, h + 3), np.uint8)
    a[1, 1, 0:h] = m['iron']
    a[0:3, 0:3, h] = m['iron']
    a[1, 1, h] = m['glow']
    a[0:3, 1, h + 1] = m['glow']; a[1, 0:3, h + 1] = m['glow']
    a[1, 1, h + 2] = m['iron']
    a[1, 1, h + 1] = m['glow']
    return Prefab(_keep_connected_to_base(a), origin=(1, 1), name='lamp')


def scarecrow(seed, m):
    a = np.zeros((5, 3, 9), np.uint8)
    a[2, 1, 0:6] = m['timber']                       # post
    a[0:5, 1, 4] = m['timber']                       # cross bar
    a[1:4, 1, 3:6] = m['rag']                        # ragged coat
    a[1:4, 0:3, 6:8] = m['pumpkin']                  # pumpkin head
    a[1:4, 0, 6] = m['glow']                         # carved face (front)
    a[2, 1, 6] = m['pumpkin']
    a[0:5, 0:3, 8] = m['hat']                        # hat brim
    a[2, 1, 8] = m['hat']
    a[0, 1, 3] = m['straw']; a[4, 1, 3] = m['straw']  # straw hands
    return Prefab(_keep_connected_to_base(a), origin=(2, 1), name='scarecrow')


def headstone(seed, m, kind):
    """Grave marker facing -i (west). kind: slab, cross, obelisk, tomb, celtic."""
    rng = np.random.default_rng(seed)
    st = m['grave'][int(rng.integers(0, len(m['grave'])))]
    if kind == 'slab':
        a = np.zeros((1, 3, 4), np.uint8)
        a[0, :, 0:3] = st
        a[0, 1, 3] = st
        if rng.random() < 0.3:
            a[0, 2, 2] = 0                           # chipped corner
    elif kind == 'cross':
        a = np.zeros((1, 3, 5), np.uint8)
        a[0, 1, 0:5] = st
        a[0, :, 3] = st
    elif kind == 'obelisk':
        a = np.zeros((2, 2, 6), np.uint8)
        a[:, :, 0:2] = st
        a[0, 0, 2:6] = st
    elif kind == 'celtic':
        a = np.zeros((1, 5, 8), np.uint8)
        a[0, 2, 0:8] = st
        a[0, 0:5, 5] = st
        a[0, 1, 4] = st; a[0, 3, 4] = st; a[0, 1, 6] = st; a[0, 3, 6] = st   # ring
    else:  # tomb chest
        a = np.zeros((5, 3, 2), np.uint8)
        a[:, :, :] = m['marble']
        a[0, :, 1] = m['marble_dark']; a[4, :, 1] = m['marble_dark']
    return Prefab(a, origin=(0, a.shape[1] // 2), name='grave')


def witch(seed, m):
    """Flying witch on a broom, broom along +i (flies toward +i). Floating scenery, ~16 x 5 x 14."""
    a = np.zeros((16, 5, 14), np.uint8)
    a[0:15, 2, 2] = m['broom']                                       # stick
    for i in range(0, 4):                                            # bristles fan
        r = 1 + (3 - i) // 2
        a[i, 2 - r:2 + r + 1, 1:4] = m['bristle']
    a[4, 1:4, 1:4] = m['iron']                                       # binding
    a[6:9, 1:4, 0:7] = m['robe']                                     # body + dress draped over the stick
    a[4:6, 1:4, 4:7] = m['robe']                                     # cape streaming back
    a[3, 2, 5:7] = m['robe']
    a[9:11, 1:4, 3:5] = m['robe']                                    # arms forward
    a[11, 1, 3] = m['skin']; a[11, 3, 3] = m['skin']                 # hands on the stick
    a[11, 1, 2] = m['skin']; a[11, 3, 2] = m['skin']
    a[7:9, 1:4, 7:9] = m['skin']                                     # head
    a[9, 2, 8] = m['skin']                                           # nose
    a[6, 1:4, 6:9] = m['hair']                                       # hair
    a[5:10, 0:5, 9] = m['hat']                                       # brim
    a[6:9, 1:4, 10] = m['band']
    a[7:9, 1:4, 11] = m['hat']
    a[7, 2, 12] = m['hat']; a[6, 2, 12] = m['hat']; a[6, 2, 13] = m['hat']   # bent tip
    # black cat riding on the bristles
    a[1:3, 2, 4] = m['cat']; a[2, 2, 5] = m['cat']
    a[2, 1, 5] = m['cat_eye']; a[2, 3, 5] = m['cat_eye']
    a[2, 1, 6] = m['cat']; a[2, 3, 6] = m['cat']
    a[0, 2, 4:7] = m['cat']
    lab, n = ndimage.label(a > 0, structure=ndimage.generate_binary_structure(3, 1))
    assert n == 1, 'witch must be one connected piece'
    return Prefab(a, origin=(8, 2), name='witch')


def cauldron(m):
    a = np.zeros((5, 5, 4), np.uint8)
    a[0:5, 0:5, 0:3] = m['iron']
    a[1:4, 1:4, 1:3] = 0
    a[1:4, 1:4, 2] = m['brew']
    a[2, 2, 3] = m['brew']
    a[0, 0, 0] = 0; a[4, 0, 0] = 0; a[0, 4, 0] = 0; a[4, 4, 0] = 0
    a[1:4, 1:4, 0] = m['iron']
    return Prefab(_keep_connected_to_base(a), origin=(2, 2), name='cauldron')
