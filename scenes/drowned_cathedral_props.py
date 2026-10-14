"""Original voxel prefabs for Drowned Cathedral (2026-10-14).

Local axes: a[i, j, k] with k = 0 the LOWEST layer; art.stamp puts k = 0 directly on the floor voxel.
Every prefab is pruned to the single face-connected component that touches k = 0, so nothing floats
when it is stamped on solid ground (or on the z = 63 water plane for fen trees).
Material ids come in a dict `m` built by drowned_cathedral.materials().
"""
import numpy as np
from scipy import ndimage

from aosmap import art
from aosmap.art import Prefab

FACE6 = ndimage.generate_binary_structure(3, 1)


def keep_base(a):
    lab, _ = ndimage.label(a > 0, structure=FACE6)
    base = np.unique(lab[:, :, 0][lab[:, :, 0] > 0])
    a[~np.isin(lab, base)] = 0
    return a


def trim_k(a):
    k = np.nonzero(a.any(axis=(0, 1)))[0]
    return a[:, :, :k.max() + 1]


# ---------------------------------------------------------------------------------------------- vegetation
def cypress(seed, m, height=16, crown_r=5.0, pads=3, moss=0.22, knees=True):
    """Swamp cypress: flared buttress base with root fins, straight trunk, flat layered crown pads on
    crooked arms, grey-green moss hanging in short strands from pad undersides, knees around the base."""
    rng = np.random.default_rng(seed)
    R = int(np.ceil(crown_r)) + 4
    H = height + 4
    a = np.zeros((2 * R + 1, 2 * R + 1, H), np.uint8)
    c = R
    ii, jj = np.meshgrid(np.arange(2 * R + 1), np.arange(2 * R + 1), indexing='ij')
    # buttress flare
    for k, r in enumerate((2.6, 2.0, 1.5, 1.1)):
        a[:, :, k][np.hypot(ii - c, jj - c) <= r] = m['bark']
    for ang in rng.uniform(0, 2 * np.pi, int(rng.integers(3, 6))):          # root fins
        for s in range(2, 5):
            x, y = c + int(round(np.cos(ang) * s)), c + int(round(np.sin(ang) * s))
            a[x, y, 0] = m['bark']
            if s == 2:
                a[x, y, 1] = m['bark']
    # trunk
    tx, ty = float(c), float(c)
    lean = rng.uniform(-0.12, 0.12, 2)
    prev = (c, c)
    for k in range(4, height):
        x, y = int(round(tx)), int(round(ty))
        w = 2 if k < height * 0.55 else 1
        a[x:x + w, y:y + w, k] = m['bark']
        if (x, y) != prev:
            a[prev[0], prev[1], k] = m['bark']
        prev = (x, y)
        tx += lean[0]; ty += lean[1]
    top = (prev[0], prev[1], height - 1)
    # crown pads: arms from the upper trunk, each ending in a flat irregular pad
    pad_cells = np.zeros(a.shape, bool)
    levels = sorted(rng.choice(np.arange(int(height * 0.62), height), size=min(pads, height // 3), replace=False))
    for n, k0 in enumerate(levels):
        ang = rng.uniform(0, 2 * np.pi)
        L = int(rng.integers(1, 4)) if n < len(levels) - 1 else 0
        bx, by, bk = top[0], top[1], k0
        for s in range(L):
            nx = int(np.clip(round(bx + np.cos(ang)), 1, 2 * R - 1)); ny = int(np.clip(round(by + np.sin(ang)), 1, 2 * R - 1))
            a[nx, by, bk] = m['bark']; a[nx, ny, bk] = m['bark']
            if rng.random() < 0.5 and bk + 1 < H:
                bk += 1; a[nx, ny, bk] = m['bark']
            bx, by = nx, ny
        r = crown_r * rng.uniform(0.55, 0.95) * (0.75 if n == len(levels) - 1 else 1.0)
        nse = art.value_noise(ii, jj, None, scale=2.2, seed=seed + 31 * n) - 0.5
        disk = np.hypot((ii - bx) * 1.0, (jj - by) * 1.15) + nse * 2.4 < r
        for dk, shrink in ((0, 1.0), (1, 0.72)):
            kk = bk + dk
            if kk < H:
                sub = disk & (np.hypot(ii - bx, jj - by) < r * shrink + 0.3)
                pad_cells[:, :, kk] |= sub
        a[bx, by, bk] = m['bark']
    a[pad_cells & (a == 0)] = m['leaf']
    a = keep_base(a)
    # moss strands under pads (only where the pad voxel is kept)
    leaf = a == m['leaf']
    under = leaf.copy(); under[:, :, 1:] &= ~(a[:, :, :-1] > 0); under[:, :, 0] = False
    for (x, y, k) in np.argwhere(under):
        if rng.random() < moss:
            L = int(rng.integers(2, 5))
            for d in range(1, L + 1):
                if k - d < 1 or a[x, y, k - d]:
                    break
                a[x, y, k - d] = m['moss']
    if knees:                                                                  # knees poke up around the base
        for _ in range(int(rng.integers(2, 6))):
            ang = rng.uniform(0, 2 * np.pi); dd = rng.uniform(3.5, 5.5)
            x, y = c + int(round(np.cos(ang) * dd)), c + int(round(np.sin(ang) * dd))
            if 0 <= x < a.shape[0] and 0 <= y < a.shape[1] and not a[x, y, 0]:
                a[x, y, 0:int(rng.integers(1, 3))] = m['bark']
    return Prefab(trim_k(a), origin=(c, c), name='cypress')
    # NB knees are separate base components: stamp() grounds each on its floor voxel.


def snag(seed, m, height=10, spread=4):
    """Dead, bark-stripped tree: crooked trunk and a few bare forked branches (face-connected L-steps)."""
    rng = np.random.default_rng(seed)
    R = spread + 3
    a = np.zeros((2 * R + 1, 2 * R + 1, height + spread + 3), np.uint8)
    x, y = R, R
    for k in range(height):
        a[x, y, k] = m['snag']
        if k < 2:
            a[x + 1, y, k] = m['snag']; a[x, y + 1, k] = m['snag']; a[x - 1, y, k] = m['snag']
        if k > 2 and rng.random() < 0.3:
            nx = int(np.clip(x + rng.integers(-1, 2), 2, 2 * R - 2)); ny = int(np.clip(y + rng.integers(-1, 2), 2, 2 * R - 2))
            a[nx, y, k] = m['snag']; a[nx, ny, k] = m['snag']; x, y = nx, ny
    for b in range(int(rng.integers(3, 6))):
        k = int(rng.integers(height // 2, height)); ang = rng.uniform(0, 2 * np.pi)
        bx, by, bk = x, y, k
        for _ in range(int(rng.integers(2, spread + 1))):
            nx = int(np.clip(round(bx + np.cos(ang)), 0, 2 * R)); ny = int(np.clip(round(by + np.sin(ang)), 0, 2 * R))
            nk = min(bk + (1 if rng.random() < 0.65 else 0), a.shape[2] - 1)
            a[nx, by, bk] = m['snag']; a[nx, ny, bk] = m['snag']; a[nx, ny, nk] = m['snag']
            bx, by, bk = nx, ny, nk; ang += rng.uniform(-0.7, 0.7)
    return Prefab(trim_k(keep_base(a)), origin=(R, R), name='snag')


def reeds(seed, m, n=7, r=2):
    rng = np.random.default_rng(seed)
    a = np.zeros((2 * r + 1, 2 * r + 1, 5), np.uint8)
    for _ in range(n):
        x, y = rng.integers(0, 2 * r + 1, 2)
        h = int(rng.integers(2, 5))
        a[x, y, 0:h] = m['reed']
        if rng.random() < 0.35:
            a[x, y, h - 1] = m['reed_head']
    return Prefab(a, origin=(r, r), name='reeds')


def lily_patch(seed, m, r=3.0):
    """Lily pads one voxel above the water plane (grounded on z = 63), with a few pale flowers."""
    rng = np.random.default_rng(seed)
    R = int(np.ceil(r)) + 1
    ii, jj = np.meshgrid(np.arange(2 * R + 1), np.arange(2 * R + 1), indexing='ij')
    n = art.value_noise(ii, jj, None, scale=1.6, seed=seed) - 0.5
    a = np.zeros((2 * R + 1, 2 * R + 1, 1), np.uint8)
    pad = (np.hypot(ii - R, jj - R) + n * 2.0 < r) & (art.value_noise(ii, jj, None, scale=1.1, seed=seed + 1) > 0.42)
    a[pad, 0] = m['lily']
    fl = pad & (rng.random(pad.shape) < 0.08)
    a[fl, 0] = m['flower']
    return Prefab(a, origin=(R, R), name='lilies')


def bush(seed, m, r=1.8):
    R = int(np.ceil(r)) + 1
    ii, jj, kk = np.meshgrid(np.arange(2 * R + 1), np.arange(2 * R + 1), np.arange(R + 1), indexing='ij')
    n = art.value_noise(ii, jj, kk, scale=1.7, seed=seed) - 0.5
    a = np.where(np.sqrt((ii - R) ** 2 + (jj - R) ** 2 + (kk * 1.5) ** 2) + n < r, m['shrub'], 0).astype(np.uint8)
    a[R, R, 0] = m['shrub']
    return Prefab(keep_base(a), origin=(R, R), name='bush')


def boulder(seed, m, r=2.4, squash=0.65):
    R = int(np.ceil(r)) + 2
    ii, jj, kk = np.meshgrid(np.arange(2 * R + 1), np.arange(2 * R + 1), np.arange(2 * R + 1), indexing='ij')
    d = np.sqrt((ii - R) ** 2 + (jj - R) ** 2 + ((kk - 0.6) / squash) ** 2)
    n = art.value_noise(ii, jj, kk, scale=2.0, seed=seed) - 0.5
    a = np.where(d + n * 1.8 < r, m['rubble'], 0).astype(np.uint8)
    a[R - 1:R + 2, R - 1:R + 2, 0] = m['rubble']
    return Prefab(trim_k(keep_base(a)), origin=(R, R), name='boulder')


# ---------------------------------------------------------------------------------------------- props
def lantern_post(m, h=4, arm=False):
    """Iron post with a caged amber lantern; arm=True hangs it from a short bracket instead."""
    a = np.zeros((5, 3, h + 4), np.uint8)
    a[2, 1, 0:h + 2] = m['iron']
    a[1:4, 0:3, 0] = m['iron']
    if arm:
        a[2:5, 1, h + 1] = m['iron']
        a[4, 1, h] = m['iron']
        a[4, 1, h - 1] = m['glow']; a[4, 1, h - 2] = m['iron']
    else:
        a[1:4, 0:3, h + 2] = m['iron']
        a[2, 1, h + 2] = m['glow']
        a[2, 1, h + 3] = m['iron']
    return Prefab(keep_base(a), origin=(2, 1), name='lantern')


def pumpkin(seed, m, size=2, lit=True, face=(-1, 0)):
    """Jack-o'-lantern, size 1..3, carved face pointing to `face` (di, dj)."""
    s = size
    a = np.zeros((s + 2, s + 2, s + 1), np.uint8)
    a[1:s + 1, 1:s + 1, 0:s] = m['pumpkin']
    if s >= 2:
        for (x, y) in ((1, 1), (s, 1), (1, s), (s, s)):
            a[x, y, s - 1] = 0
        for i in range(1, s + 1, 2):
            sl = a[i, 1:s + 1, 0:s]
            a[i, 1:s + 1, 0:s] = np.where(sl > 0, m['pumpkin_dark'], 0)
    a[1 + s // 2, 1 + s // 2, s] = m['stem']
    a[1 + s // 2, 1 + s // 2, s - 1] = m['pumpkin']
    if lit and s >= 2:
        di, dj = face
        if di:
            i = 1 if di < 0 else s
            a[i, 1:s + 1, 0:s - 1] = m['glow']
        else:
            j = 1 if dj < 0 else s
            a[1:s + 1, j, 0:s - 1] = m['glow']
    return Prefab(keep_base(a), origin=(1, 1), name='pumpkin')


def candles(seed, m, n=5, r=1):
    rng = np.random.default_rng(seed)
    a = np.zeros((2 * r + 1, 2 * r + 1, 4), np.uint8)
    for _ in range(n):
        x, y = rng.integers(0, 2 * r + 1, 2)
        h = int(rng.integers(1, 4))
        a[x, y, 0:h] = m['wax']
        a[x, y, h] = m['glow']
    return Prefab(keep_base(a), origin=(r, r), name='candles')


def gibbet(seed, m, h=12, arm=5):
    """Gallows post with an iron cage on a chain; a few bones inside. Faces +i."""
    a = np.zeros((arm + 4, 7, h + 2), np.uint8)
    px, py = 1, 3
    a[px:px + 2, py:py + 2, 0:h + 1] = m['timber']
    a[px - 1:px + 3, py - 1:py + 3, 0] = m['timber']
    a[px:px + arm + 2, py, h] = m['timber']                 # arm
    for d in range(1, 4):                                   # brace
        a[px + 1 + d, py, h - 4 + d] = m['timber']; a[px + 1 + d, py, h - 3 + d] = m['timber']
    cx = px + arm
    a[cx, py, h - 3:h] = m['iron']                          # chain
    k1, k0 = h - 4, h - 8                                   # cage spans k0..k1
    a[cx - 1:cx + 2, py - 1:py + 2, k1] = m['iron']
    a[cx - 1:cx + 2, py - 1:py + 2, k0] = m['iron']
    for (x, y) in ((cx - 1, py - 1), (cx + 1, py - 1), (cx - 1, py + 1), (cx + 1, py + 1), (cx, py - 1), (cx, py + 1)):
        a[x, y, k0:k1 + 1] = m['iron']
    a[cx, py, k0 + 1] = m['bone']; a[cx, py, k0 + 2] = m['bone']; a[cx, py, k0 + 3] = m['skull']
    return Prefab(keep_base(a), origin=(px, py), name='gibbet')


def skull_pile(seed, m, r=2):
    rng = np.random.default_rng(seed)
    a = np.zeros((2 * r + 1, 2 * r + 1, r + 1), np.uint8)
    ii, jj, kk = np.meshgrid(np.arange(2 * r + 1), np.arange(2 * r + 1), np.arange(r + 1), indexing='ij')
    pile = np.sqrt((ii - r) ** 2 + (jj - r) ** 2 + (kk * 1.6) ** 2) < r + 0.3
    a[pile] = m['bone']
    sk = pile & (rng.random(pile.shape) < 0.45)
    a[sk] = m['skull']
    return Prefab(keep_base(a), origin=(r, r), name='skulls')


def rowboat(m, length=9):
    """Upturned / beached wooden boat lying along i (hull 3 wide, pointed ends)."""
    a = np.zeros((length, 5, 3), np.uint8)
    for i in range(length):
        t = min(i, length - 1 - i)
        w = 0 if t == 0 else (1 if t == 1 else 2)
        a[i, 2 - w:3 + w, 0] = m['timber']
        if t >= 1:
            a[i, 2 - w, 1] = m['timber']; a[i, 2 + w, 1] = m['timber']
        if t >= 2:
            a[i, 2 - w, 2] = m['boat']; a[i, 2 + w, 2] = m['boat']
    a[length // 2, 1:4, 1] = m['timber']                    # thwart
    return Prefab(keep_base(a), origin=(length // 2, 2), name='boat')


def gargoyle(m):
    """Crouching gargoyle facing +i, to be stamped on a wall top or corbel (k = 0 sits on the stone)."""
    a = np.zeros((5, 3, 4), np.uint8)
    g = m['gargoyle']
    a[0:3, 0:3, 0] = g                                      # haunches / plinth
    a[1:4, 1, 1] = g                                        # body leaning out
    a[0, 0, 1] = g; a[0, 2, 1] = g                          # folded wings
    a[0, 0, 2] = g; a[0, 2, 2] = g
    a[3:5, 1, 2] = g                                        # neck + head
    a[4, 0, 2] = m['glow_dim']; a[4, 2, 2] = m['glow_dim']  # eyes (side voxels touching the head)
    a[4, 1, 3] = g                                          # brow / horns
    a[1, 1, 2] = g
    return Prefab(keep_base(a), origin=(0, 1), name='gargoyle')


def hanging_tree(seed, m, height=15, spread=8, lanterns=4):
    """Landmark: a huge dead oak with a 3x3 flared trunk, long crooked limbs and lanterns hung on chains."""
    rng = np.random.default_rng(seed)
    R = spread + 4
    H = height + spread + 2
    a = np.zeros((2 * R + 1, 2 * R + 1, H), np.uint8)
    c = R
    for k in range(height):
        w = 3 if k < height * 0.6 else 2
        o = -1 if w == 3 else 0
        a[c + o:c + o + w, c + o:c + o + w, k] = m['snag']
    for ang in np.linspace(0, 2 * np.pi, 7)[:-1] + rng.uniform(0, 0.5):     # root flare
        for s_ in range(2, 5):
            a[c + int(round(np.cos(ang) * s_)), c + int(round(np.sin(ang) * s_)), 0] = m['snag']
        a[c + int(round(np.cos(ang) * 2)), c + int(round(np.sin(ang) * 2)), 1] = m['snag']
    tips = []
    for b in range(6):
        ang = b * np.pi / 3 + rng.uniform(-0.4, 0.4)
        k0 = int(height * rng.uniform(0.5, 0.95))
        bx, by, bk = c, c, k0
        for s_ in range(int(rng.integers(spread - 2, spread + 1))):
            nx = int(np.clip(round(bx + np.cos(ang)), 0, 2 * R)); ny = int(np.clip(round(by + np.sin(ang)), 0, 2 * R))
            nk = min(bk + (1 if rng.random() < 0.45 else 0), H - 1)
            a[nx, by, bk] = m['snag']; a[nx, ny, bk] = m['snag']; a[nx, ny, nk] = m['snag']
            if s_ < 2:
                a[nx, ny, bk - 1] = m['snag']
            bx, by, bk = nx, ny, nk
            ang += rng.uniform(-0.35, 0.35)
        tips.append((bx, by, bk))
        for _ in range(2):                                             # twigs
            tx, ty = bx + int(rng.integers(-1, 2)), by + int(rng.integers(-1, 2))
            if 0 <= tx <= 2 * R and 0 <= ty <= 2 * R and bk + 1 < H:
                a[tx, by, bk] = m['snag']; a[tx, ty, bk] = m['snag']; a[tx, ty, bk + 1] = m['snag']
    a = keep_base(a)
    for (bx, by, bk) in tips[:lanterns]:                              # chain + lantern under each limb end
        if bk - 4 > 1 and a[bx, by, bk]:
            a[bx, by, bk - 2:bk] = m['iron']
            a[bx, by, bk - 3] = m['glow']
            a[bx, by, bk - 4] = m['iron']
    return Prefab(trim_k(a), origin=(c, c), name='hanging_tree')


def calvary(m, h=9):
    """Wayside stone cross on a stepped plinth."""
    a = np.zeros((5, 5, h + 3), np.uint8)
    a[0:5, 0:5, 0] = m['stone_dk']
    a[1:4, 1:4, 1] = m['stone']
    a[2, 2, 2:h + 2] = m['trim']
    a[0:5, 2, h - 1] = m['trim']
    a[2, 2, h + 2] = m['trim']
    return Prefab(keep_base(a), origin=(2, 2), name='calvary')


def well(m):
    a = np.zeros((5, 5, 7), np.uint8)
    a[:, :, 0:2] = m['stone_dk']
    a[1:4, 1:4, 0:2] = 0
    a[1:4, 1:4, 0] = m['iron']                                        # dark water surface stand-in
    a[0, 2, 2:6] = m['timber']; a[4, 2, 2:6] = m['timber']
    a[0:5, 2, 6] = m['timber']
    a[2, 2, 5] = m['iron']; a[2, 2, 4] = m['timber']                   # rope + bucket
    a[0:5, 1:4, 6] = np.where(a[0:5, 1:4, 6] == 0, m['slate'], a[0:5, 1:4, 6])
    return Prefab(keep_base(a), origin=(2, 2), name='well')
