# Haunted Fairground v1.3 — Tower of Babel, built on the Ruins.vxl layout
# Terrain silhouette/heights are derived from Ruins.vxl (smoothed, props stripped).
# Every prop and building is new. The Babel platform is NOT in the VXL: babel_script.py
# paints it at load time. Deterministic: SEED below.
import numpy as np, math, sys, os
from scipy import ndimage as nd
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import vxlio
from load import load as load_vxl

SEED = 1031
W = H = 512; D = 64; WATER = 63
S = np.zeros((W, H, D), bool); C = np.zeros((W, H, D), np.uint32)

def rgb(r, g, b): return (int(r) << 16) | (int(g) << 8) | int(b)
# Darker, spookier autumn palette (v1.1). Lights stay bright so they read as glow.
P = dict(
    water=rgb(30, 46, 56), sand=rgb(118, 104, 86), sand2=rgb(104, 92, 78),
    grass=rgb(46, 56, 42), grass2=rgb(54, 62, 44), litter_r=rgb(112, 56, 32), litter_g=rgb(138, 94, 40),
    litter_b=rgb(82, 60, 44), dirt=rgb(92, 76, 62), dirt2=rgb(80, 66, 54), subsoil=rgb(70, 54, 42),
    rock=rgb(66, 62, 70), rock2=rgb(56, 54, 62), mist=rgb(88, 82, 102),
    rust=rgb(116, 52, 36), rust2=rgb(92, 42, 32), red=rgb(128, 34, 34), bone=rgb(206, 196, 170),
    bone2=rgb(172, 164, 144), amber=rgb(255, 180, 60), amber2=rgb(222, 128, 36),
    wood=rgb(92, 68, 50), wood2=rgb(74, 56, 42), wood3=rgb(58, 44, 34),
    stone=rgb(98, 96, 104), stone2=rgb(82, 80, 90), slate=rgb(48, 50, 62), iron=rgb(38, 40, 48),
    pump=rgb(214, 100, 26), pump2=rgb(176, 76, 22), stem=rgb(58, 76, 36),
    purple=rgb(88, 52, 112), purple2=rgb(64, 40, 86), teal=rgb(44, 86, 88),
    orange=rgb(190, 96, 34), orange2=rgb(150, 72, 28),
    bark=rgb(52, 42, 38), bark2=rgb(40, 34, 32),
    leaf1=rgb(136, 54, 26), leaf2=rgb(166, 98, 34), leaf3=rgb(96, 42, 30),
    black=rgb(22, 20, 26), wallA=rgb(60, 48, 66), wallA2=rgb(52, 42, 58),
    plaster=rgb(78, 72, 82), mirror=rgb(150, 160, 172), tar=rgb(40, 40, 50))

def put(x, y, z, c):
    if 0 <= x < W and 0 <= y < H and 0 <= z < D: S[x, y, z] = True; C[x, y, z] = c
def box(x0, y0, z0, x1, y1, z1, c):
    x0, x1 = sorted((x0, x1)); y0, y1 = sorted((y0, y1)); z0, z1 = sorted((z0, z1))
    S[x0:x1+1, y0:y1+1, z0:z1+1] = True; C[x0:x1+1, y0:y1+1, z0:z1+1] = c
def clear(x0, y0, z0, x1, y1, z1):
    x0, x1 = sorted((x0, x1)); y0, y1 = sorted((y0, y1)); z0, z1 = sorted((z0, z1))
    S[x0:x1+1, y0:y1+1, z0:z1+1] = False
def fline(a, b, c, w=1):
    """face-connected 3D voxel line (one axis step at a time); w>1 thickens along x."""
    pts = [tuple(int(round(v)) for v in a)]
    n = max(abs(int(round(b[i])) - pts[0][i]) for i in range(3)); n = max(n, 1)
    for t in range(1, n+1):
        tgt = tuple(int(round(a[i] + (b[i]-a[i])*t/n)) for i in range(3))
        for axis in range(3):
            cur = list(pts[-1])
            if cur[axis] != tgt[axis]: cur[axis] = tgt[axis]; pts.append(tuple(cur))
    for (px, py, pz) in pts:
        for dx in range(w): put(px+dx, py, pz, c)
def shade(c, f):
    r, g_, b_ = (c >> 16) & 255, (c >> 8) & 255, c & 255
    return rgb(min(255, r * f), min(255, g_ * f), min(255, b_ * f))
def mix(c1, c2, t):
    a = [(c1 >> s) & 255 for s in (16, 8, 0)]; b = [(c2 >> s) & 255 for s in (16, 8, 0)]
    return rgb(*[a[i] * (1 - t) + b[i] * t for i in range(3)])

# ------------------------------------------------------------------ terrain from Ruins
RUINS = os.environ.get('RUINS_VXL', os.path.join(HERE, 'Ruins.vxl'))
RS, _ = load_vxl(RUINS)
rtop = np.argmax(RS, axis=2); rh = 63 - rtop
base = nd.median_filter(rh, size=11)
base = np.minimum(base, 13)
base = np.where(nd.binary_erosion(rh > 0, iterations=1) | (base > 0), base, 0)
base = np.round(nd.gaussian_filter(base.astype(float), 1.2)).astype(int)
base[rh == 0] = np.minimum(base[rh == 0], 0)
base = np.minimum(base, base[::-1, :])
TZ = 63 - np.clip(base, 0, 62)

def vnoise(scale, seed):
    r = np.random.default_rng(seed); g_ = r.random((W // scale + 3, H // scale + 3))
    xs, ys = np.meshgrid(np.arange(W) / scale, np.arange(H) / scale, indexing='ij')
    ix, iy = xs.astype(int), ys.astype(int); fx, fy = xs - ix, ys - iy
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy)
    a = g_[ix, iy] * (1 - fx) + g_[ix + 1, iy] * fx; b = g_[ix, iy + 1] * (1 - fx) + g_[ix + 1, iy + 1] * fx
    return a * (1 - fy) + b * fy
n1 = vnoise(14, SEED) * 0.7 + vnoise(5, SEED + 1) * 0.3
n2 = vnoise(9, SEED + 2)
slope = np.maximum.reduce([abs(np.roll(TZ, 1, 0) - TZ), abs(np.roll(TZ, -1, 0) - TZ),
                           abs(np.roll(TZ, 1, 1) - TZ), abs(np.roll(TZ, -1, 1) - TZ)])
paths = [[(92, 256), (130, 256), (168, 254), (200, 256), (250, 256)],
         [(100, 226), (132, 214), (160, 212), (180, 200), (210, 192), (256, 192)],
         [(100, 288), (136, 296), (170, 312), (210, 320), (256, 322)]]
pathmask = np.zeros((W, H), bool)
xs, ys = np.meshgrid(np.arange(W), np.arange(H), indexing='ij')
for pl in paths:
    for (ax, ay), (bx, by) in zip(pl, pl[1:]):
        L = max(abs(bx - ax), abs(by - ay))
        for t in range(L + 1):
            px = ax + (bx - ax) * t / L; py = ay + (by - ay) * t / L
            x0, y0 = int(px), int(py)
            pathmask[x0-3:x0+4, y0-3:y0+4] |= ((xs[x0-3:x0+4, y0-3:y0+4] - px) ** 2 + (ys[x0-3:x0+4, y0-3:y0+4] - py) ** 2) < (3.2 + 0.8 * n2[x0, y0]) ** 2
pathmask |= pathmask[::-1, :]
land = TZ < WATER
near_water = nd.binary_dilation(~land, iterations=2) & land
path_edge = nd.binary_dilation(pathmask, iterations=1) & ~pathmask
moss_rim = nd.binary_dilation(slope >= 2, iterations=1) & (slope < 2)
low = nd.gaussian_filter(((63 - TZ) <= 7).astype(float) * land, 3.0)      # ground mist in hollows

S[:, :, WATER] = True; C[:, :, WATER] = P['water']
for x in range(W):
    for y in range(H):
        t = TZ[x, y]
        if t >= WATER: continue
        S[x, y, t:WATER] = True
        h = 63 - t
        f = 0.86 + 0.02 * h + 0.06 * (n2[x, y] - 0.5)
        if h <= 1:
            top = shade(P['sand2'], 0.82) if near_water[x, y] else (P['sand'] if n2[x, y] > 0.4 else P['sand2'])
        elif slope[x, y] >= 2: top = P['rock'] if n1[x, y] > 0.5 else P['rock2']
        elif pathmask[x, y]: top = shade(P['dirt'] if n2[x, y] > 0.45 else P['dirt2'], f)
        elif path_edge[x, y]: top = shade(P['litter_b'], f)
        else:
            v = n1[x, y]
            top = (P['litter_r'] if v > 0.70 else P['litter_g'] if v > 0.65 else P['litter_b'] if v > 0.58
                   else P['grass2'] if n2[x, y] > 0.55 else P['grass'])
            if moss_rim[x, y] and v <= 0.58: top = shade(P['grass2'], 1.06)
            top = shade(top, f)
            if low[x, y] > 0.25: top = mix(top, P['mist'], min(0.45, (low[x, y] - 0.25) * 0.9))
        C[x, y, t] = top
        if h <= 2: C[x, y, t+1:WATER] = P['sand2']
        else:
            C[x, y, t+1] = P['subsoil']
            for z in range(t + 2, WATER):
                C[x, y, z] = [P['rock2'], P['rock'], shade(P['rock2'], 0.85)][(z // 2) % 3] if z < 61 else P['sand2']

def g(x, y): return int(TZ[x, y])
def gmin(x0, y0, x1, y1): return int(TZ[x0:x1+1, y0:y1+1].min())
def gmax(x0, y0, x1, y1): return int(TZ[x0:x1+1, y0:y1+1].max())
def footing(x0, y0, x1, y1, ztop, c):
    for x in range(x0, x1+1):
        for y in range(y0, y1+1):
            box(x, y, ztop, x, y, max(ztop, TZ[x, y]), c)
def footing_mask(mask, ztop, c, clear_above=False):
    for x, y in zip(*np.nonzero(mask)):
        if clear_above: S[x, y, :ztop] = False                  # terrain must not intrude into the floor
        box(x, y, ztop, x, y, max(ztop, TZ[x, y]), c)
def footing_clear(x0, y0, x1, y1, ztop, c):
    m = np.zeros((W, H), bool); m[x0:x1+1, y0:y1+1] = True; footing_mask(m, ztop, c, clear_above=True)

# ------------------------------------------------------------------ generic building kit
def perim(mask):
    return mask & ~nd.binary_erosion(mask, border_value=0)

def stair_flight(s, lane, F, Cz, rising=+1, col=None, axis='x'):
    """One flight of 1-voxel steps from floor F up to floor Cz (F > Cz), 2 wide.
    axis='x': steps march along x from s (rising=+1) or from s+n-1 back to s (rising=-1),
    occupying rows lane, lane+1. Clears the slab at Cz above the run. Landing is the
    slab cell just past the last step."""
    n = F - Cz - 1
    col = col or P['wood2']
    for j in range(1, n + 1):
        a = s + j - 1 if rising > 0 else s + n - j
        for r in (lane, lane + 1):
            x, y = (a, r) if axis == 'x' else (r, a)
            box(x, y, F - j, x, y, F - 1, col if j % 2 else P['wood'])
            clear(x, y, F - j - 3, x, y, F - j - 1)              # headroom inside the storey
    for k in range(n):
        a = s + k
        for r in (lane, lane + 1):
            x, y = (a, r) if axis == 'x' else (r, a)
            S[x, y, Cz] = False                                  # opening in the floor above

def stair_stack(s, yA, yB, levels, axis='x'):
    """switchback stairs through every storey: even storeys use lane A rising +,
    odd storeys lane B rising -. Shaft spans s-1..s+n along the axis."""
    for i, (F, Cz) in enumerate(zip(levels[:-1], levels[1:])):
        if i % 2 == 0: stair_flight(s, yA, F, Cz, +1, axis=axis)
        else: stair_flight(s, yB, F, Cz, -1, axis=axis)

def door(x0, y0, x1, y1, F, h=3):
    clear(x0, y0, F - h, x1, y1, F - 1)

def windows_on(mask, F, Cz, skip=lambda x, y, z: False, every=6, lit=0.0):
    """2-wide, 2-tall window openings on exterior walls of a storey; bone sills/lintels."""
    pm = perim(mask)
    for x, y in zip(*np.nonzero(pm)):
        out_x = not mask[x-1, y] or not mask[x+1, y]
        out_y = not mask[x, y-1] or not mask[x, y+1]
        if out_x and out_y: continue                              # corners stay solid
        coord = y if out_x else x
        if coord % every in (2, 3):
            for z in (F - 2, F - 3):
                if not skip(x, y, z): S[x, y, z] = False
            if not skip(x, y, F - 4) and S[x, y, F - 4]: C[x, y, F - 4] = P['bone2']
            if S[x, y, F - 1]: C[x, y, F - 1] = P['bone2']

def cobweb(x, y, z, dx, dy):
    """small ceiling-corner web attached to wall/ceiling at (x,y,z)."""
    put(x, y, z, P['bone2']); put(x + dx, y, z, P['bone2']); put(x, y + dy, z, P['bone2'])

# ------------------------------------------------------------------ small assets
def pumpkin(x, y, z, big=False):
    if big:
        box(x, y, z-2, x+2, y+2, z-1, P['pump']); box(x+1, y, z-2, x+1, y+2, z-1, P['pump2'])
        put(x+1, y+1, z-3, P['stem'])
    else:
        box(x, y, z-1, x+1, y, z-1, P['pump']); put(x, y, z-2, P['stem'])

def jack_small(x, y, face=1):
    """3x3x2 carved pumpkin with a glowing face on the +y (face=1) or -y side."""
    z = g(x, y)
    box(x, y, z-2, x+2, y+2, z-1, P['pump']); box(x+1, y, z-2, x+1, y+2, z-1, P['pump2'])
    put(x+1, y+1, z-3, P['stem'])
    fy = y + 2 if face == 1 else y
    put(x, fy, z-2, P['amber']); put(x+2, fy, z-2, P['amber']); put(x+1, fy, z-1, P['amber'])

def dead_tree(x, y, seed, leaves=True):
    r = np.random.default_rng(seed); z0 = g(x, y); th = 10 + int(r.integers(0, 4))
    for dx, dy in ((-1, 0), (2, 0), (0, -1), (0, 2)): put(x+dx, y+dy, z0-1, P['bark2'])
    box(x, y, z0-th//2, x+1, y+1, z0-1, P['bark'])
    box(x, y, z0-th, x, y, z0-th//2, P['bark2'])
    tips = [(x, y, z0-th)]
    for k in range(5 if not leaves else 4):
        ang = k * 2 * math.pi / (5 if not leaves else 4) + r.uniform(-0.5, 0.5); L = 3 + int(r.integers(0, 3)) + (0 if leaves else 1)
        cx, cy, cz = x, y, z0 - th//2 - 1 - k
        for s_ in range(L):
            nx = x + round(math.cos(ang) * (s_+1)); ny = y + round(math.sin(ang) * (s_+1))
            if nx != cx: cx = nx; put(cx, cy, cz, P['bark2'])
            if ny != cy: cy = ny; put(cx, cy, cz, P['bark2'])
            if s_ % 2 == 1: cz -= 1; put(cx, cy, cz, P['bark2'])
        tips.append((cx, cy, cz))
    if leaves:
        for (tx, ty, tz) in tips:
            rr = 2 if r.random() < 0.55 else 1
            for dx in range(-rr, rr+1):
                for dy in range(-rr, rr+1):
                    for dz in range(-rr, 1):
                        if dx*dx + dy*dy + dz*dz <= rr*rr + 1:
                            put(tx+dx, ty+dy, tz+dz-1, P['leaf2'] if dz < -1 else (P['leaf1'] if (tx+ty) % 2 else P['leaf3']))
    else:
        for (tx, ty, tz) in tips[1:]:                         # gnarled twig ends + a crow
            put(tx, ty, tz-1, P['bark2'])
        tx, ty, tz = tips[1]; put(tx, ty, tz-2, P['black']); put(tx, ty, tz-3, P['black'])

def lamp(x, y, face=1):
    z0 = g(x, y)
    box(x, y, z0-7, x, y, z0-1, P['iron'])
    put(x, y+face, z0-7, P['iron']); put(x, y+face, z0-6, P['amber']); put(x, y, z0-8, P['amber2'])
    return (x, y, z0-7)

def lamp_on(x, y, zd):
    box(x, y, zd-7, x, y, zd-1, P['iron']); put(x, y, zd-8, P['amber2'])
    put(x, y-1, zd-7, P['iron']); put(x, y-1, zd-6, P['amber'])
    return (x, y, zd-7)

def bunting(a, b):
    (ax, ay, az), (bx, by, bz) = a, b
    n = max(abs(bx-ax), abs(by-ay)); px, py, pz = ax, ay, az
    for t in range(1, n):
        x = round(ax + (bx-ax)*t/n); y = round(ay + (by-ay)*t/n)
        z = round(az + (bz-az)*t/n + 2.5*math.sin(math.pi*t/n))
        while pz != z: pz += 1 if z > pz else -1; put(px, py, pz, P['iron'])
        if x != px and y != py: put(x, py, pz, P['iron'])
        put(x, y, z, P['iron']); px, py, pz = x, y, z
        if t % 4 in (1, 2):
            col = [P['red'], P['bone2'], P['amber2'], P['purple']][(t // 4) % 4]
            put(x, y, z+1, col)
            if t % 4 == 1: put(x, y, z+2, col)

def stall(x, y, kind, team, facing=1):
    z0 = gmax(x, y, x+6, y+4); footing(x, y, x+6, y+4, z0, P['wood3'])
    fy, by = (y+4, y) if facing == 1 else (y, y+4)
    box(x, by, z0-6, x+6, by, z0-1, P['wood2'])
    for xx in (x, x+6): box(xx, y, z0-6, xx, y+4, z0-1, P['wood'])
    box(x+1, fy, z0-2, x+5, fy, z0-1, P['wood']); box(x+1, fy, z0-2, x+5, fy, z0-2, P['bone2'])
    acc = P['purple'] if team == 0 else P['orange']
    stripe = [P['red'], P['bone2']] if kind != 'ticket' else [acc, P['bone2']]
    for i in range(7):
        for d in range(6):
            yy = (y + d) if facing == 1 else (y + 4 - d)
            put(x+i, yy, z0-7+(d >= 3) + (d >= 5), stripe[(i // 2) % 2])
        if i % 2 == 0: put(x+i, fy + facing, z0-5, stripe[(i // 2) % 2])
    sh = by + facing
    box(x+1, sh, z0-4, x+5, sh, z0-4, P['wood3'])
    for i in (1, 3, 5): put(x+i, sh, z0-5, [P['red'], P['pump'], P['amber2']][i // 2])
    put(x+3, y+2, z0-6, P['amber'])
    box(x+2, by, z0-9, x+4, by, z0-8, P['bone2'])
    put(x+3, by, z0-9, P['red'] if kind == 'apple' else P['pump'] if kind == 'pumpkin' else acc)
    if kind == 'pumpkin':
        for i in (1, 3, 5): put(x+i, fy, z0-3, P['pump'])
        put(x+3, fy, z0-4, P['stem'])
    elif kind == 'apple':
        for i in (1, 2, 4, 5): put(x+i, fy, z0-3, P['wood3']); put(x+i, fy, z0-4, P['red'])
    else:
        box(x+2, by+facing, z0-4, x+4, by+facing, z0-3, P['amber'])

def hay(x, y, along_x=True):
    z0 = g(x, y); x1, y1 = (x+2, y+1) if along_x else (x+1, y+2)
    footing(x, y, x1, y1, z0, P['litter_g'])
    box(x, y, z0-2, x1, y1, z0-1, P['litter_g'])
    if along_x: box(x+1, y, z0-2, x+1, y1, z0-1, P['sand2'])
    else: box(x, y+1, z0-2, x1, y+1, z0-1, P['sand2'])

def crate(x, y, tall=False, z0=None):
    if z0 is None: z0 = gmax(x, y, x+1, y+1); footing(x, y, x+1, y+1, z0, P['wood3'])
    hgt = 4 if tall else 2
    box(x, y, z0-hgt, x+1, y+1, z0-1, P['wood']); box(x, y, z0-hgt, x+1, y+1, z0-hgt, P['wood3'])
    if tall: box(x, y, z0-2, x+1, y+1, z0-2, P['wood3'])

def barrel(x, y, z0=None):
    if z0 is None: z0 = gmax(x, y, x+1, y+1); footing(x, y, x+1, y+1, z0, P['wood3'])
    box(x, y, z0-3, x+1, y+1, z0-1, P['wood2']); box(x, y, z0-2, x+1, y+1, z0-2, P['iron'])

def coffin(x, y, z0, along_y=True):
    x1, y1 = (x, y+3) if along_y else (x+3, y)
    box(x, y, z0-1, x1, y1, z0-1, P['wood3']); put(x, y, z0-2, P['wood2']) if False else None
    if along_y: box(x, y+1, z0-2, x, y+2, z0-2, P['wood2'])
    else: box(x+1, y, z0-2, x+2, y, z0-2, P['wood2'])

def tombstone(x, y, tall=3, z0=None):
    z0 = g(x, y) if z0 is None else z0
    box(x, y, z0-tall, x+1, y, z0-1, P['stone']); put(x, y, z0-tall-1, P['stone2'])
    put(x+1, y, z0-2, P['stone2'])

def graveyard(x0, y0, x1, y1, seed):
    r = np.random.default_rng(seed)
    for x in range(x0, x1+1):                                     # broken picket fence
        for y in (y0, y1):
            if TZ[x, y] < 62 and (x * 3 + y) % 7 != 0:
                put(x, y, g(x, y)-1, P['bone2'] if x % 2 else P['wood2'])
                if x % 2 == 0: put(x, y, g(x, y)-2, P['bone2'])
    for y in range(y0, y1+1):
        for x in (x0, x1):
            if TZ[x, y] < 62 and (y * 3 + x) % 7 != 0:
                put(x, y, g(x, y)-1, P['bone2'] if y % 2 else P['wood2'])
                if y % 2 == 0: put(x, y, g(x, y)-2, P['bone2'])
    for x in range(x0 + 2, x1 - 1, 4):
        for y in range(y0 + 2, y1 - 1, 4):
            if TZ[x, y] < 62 and TZ[x+1, y] == TZ[x, y]:
                tombstone(x, y, 2 + int(r.integers(0, 3)))
                C[x, y-1, TZ[x, y-1]] = P['dirt2']; C[x+1, y-1, TZ[x+1, y-1]] = P['dirt2']

def pumpkin_patch(x0, y0, x1, y1):
    for x in range(x0, x1+1):
        for y in range(y0, y1+1):
            if TZ[x, y] >= 62: continue
            if (y - y0) % 4 == 0: C[x, y, TZ[x, y]] = P['dirt2']
            elif (y - y0) % 4 == 2 and (x + y) % 3 == 0: C[x, y, TZ[x, y]] = P['stem']
    for x in range(x0 + 1, x1, 3):
        for y in range(y0 + 1, y1, 4):
            if TZ[x, y] < 62 and TZ[x+1, y] == TZ[x, y]: pumpkin(x, y, g(x, y), big=((x * 7 + y) % 5 == 0))

def scarecrow(x, y, team):
    acc = P['purple'] if team == 0 else P['orange']; z0 = g(x, y)
    box(x, y, z0-9, x, y, z0-1, P['wood'])
    box(x, y-3, z0-7, x, y+3, z0-7, P['wood'])
    put(x, y-4, z0-7, P['litter_g']); put(x, y+4, z0-7, P['litter_g'])
    box(x, y-1, z0-7, x, y+1, z0-4, acc); box(x+1, y-1, z0-7, x+1, y+1, z0-5, acc)
    box(x-1, y-1, z0-12, x+1, y+1, z0-10, P['sand'])
    put(x+1, y-1, z0-11, P['black']); put(x+1, y+1, z0-11, P['black']); put(x+1, y, z0-10, P['red'])
    box(x-2, y-2, z0-13, x+2, y+2, z0-13, P['bark2']); box(x-1, y-1, z0-15, x+1, y+1, z0-14, P['bark'])
    put(x, y+3, z0-8, P['black'])                                  # crow on the crossbar

def gate_arch(x, y0, y1, team):
    acc = P['purple'] if team == 0 else P['orange']
    zt = min(g(x, y0), g(x, y1)) - 10
    for yy in (y0, y1):
        zb_ = max(g(x, yy), g(x+1, yy), g(x, yy+1), g(x+1, yy+1))
        box(x, yy, zt, x+1, yy+1, zb_, P['wood2']); box(x, yy, zt+2, x+1, yy+1, zt+2, acc)
        put(x+2, yy, zt+3, P['amber'])
    box(x, y0, zt-1, x+1, y1+1, zt, P['wood'])
    ym = (y0 + y1) // 2
    box(x+2, ym-3, zt-2, x+2, ym+4, zt+1, P['bone2']); box(x+2, ym-3, zt+1, x+2, ym+4, zt+1, P['red'])
    for yy in range(ym-2, ym+4, 2): put(x+3, yy, zt-1, acc)
    for yy in range(y0, y1+2, 3): put(x, yy, zt-2, P['red']); put(x+1, yy, zt-2, P['bone2'])

def bumper_pen(x0, y0, x1, y1, team):
    z0 = gmax(x0, y0, x1, y1); footing(x0, y0, x1, y1, z0, P['stone2'])
    for x in range(x0, x1+1):
        for y in range(y0, y1+1): C[x, y, z0] = P['slate'] if (x + y) % 2 else P['stone2']
    for x in range(x0, x1+1): put(x, y0, z0-1, P['bone2']); put(x, y1, z0-1, P['bone2'])
    for y in range(y0, y1+1): put(x0, y, z0-1, P['bone2']); put(x1, y, z0-1, P['bone2'])
    for x in (x0, x1):
        for y in (y0, y1): box(x, y, z0-7, x, y, z0-1, P['rust'])
    box(x0, y0, z0-7, x1, y0, z0-7, P['rust']); box(x0, y1, z0-7, x1, y1, z0-7, P['rust'])
    cars = [(x0+3, y0+3, P['red']), (x0+10, y0+6, P['purple'] if team == 0 else P['orange']),
            (x0+5, y1-4, P['amber2']), (x1-6, y1-3, P['teal'])]
    for cx, cy, c in cars:
        box(cx, cy, z0-1, cx+2, cy+1, z0-1, c); put(cx+1, cy, z0-2, P['bone2']); box(cx+1, cy, z0-4, cx+1, cy, z0-3, P['iron'])

def boardwalk_bridge(x0, x1, y0, y1, z):
    for x in range(x0, x1+1):
        for y in range(y0, y1+1):
            if TZ[x, y] > z: put(x, y, z, P['wood'] if (x // 2) % 2 else P['wood2'])
        for y in (y0, y1):
            if TZ[x, y] > z: put(x, y, z-1, P['wood3'])
        if x % 5 == 0:
            for y in (y0, y1):
                if TZ[x, y] > z: box(x, y, z+1, x, y, max(z+1, TZ[x, y]-1), P['wood3']); put(x, y, z-2, P['wood3'])

def stairs_out(x, y0, y1, w=4):
    za, zb = g(x+1, y0), g(x+1, y1); n = abs(y1 - y0)
    for i in range(n + 1):
        z = round(za + (zb - za) * i / n)
        for xx in range(x, x+w): box(xx, y0+i, z, xx, y0+i, TZ[xx, y0+i], P['stone'] if i % 2 else P['stone2'])

# ------------------------------------------------------------------ enterable small buildings
def caravan(x, y, team):
    """fortune-teller wagon, 7 x 13, hollow cabin (5 wide x 11 long x 5 tall), door + steps at the y end."""
    z0 = gmax(x, y, x+6, y+12); acc = P['purple'] if team == 0 else P['orange']
    acc2 = P['purple2'] if team == 0 else P['orange2']
    box(x+1, y+2, z0-2, x+5, y+10, z0-1, P['wood3']); footing(x+1, y+2, x+5, y+10, z0-1, P['wood3'])
    for wy in (y+2, y+9):
        for xx in (x, x+6):
            box(xx, wy, z0-3, xx, wy+2, z0-1, P['iron']); put(xx, wy+1, z0-2, P['amber2'])
    box(x, y, z0-8, x+6, y+12, z0-3, acc)                                  # shell
    clear(x+1, y+1, z0-8, x+5, y+11, z0-4)                                  # cabin
    for xx in range(x+1, x+6):
        for yy in range(y+1, y+12): C[xx, yy, z0-3] = P['wood'] if yy % 2 else P['wood2']   # floor
    box(x, y, z0-9, x+6, y+12, z0-9, P['rust'])                             # roof
    box(x+1, y, z0-10, x+5, y+12, z0-10, P['rust2']); box(x+2, y, z0-11, x+4, y+12, z0-11, P['rust'])
    clear(x+2, y+1, z0-10, x+4, y+11, z0-9)                                 # vaulted ceiling
    for wy in (y+3, y+7):                                                   # side windows (openings)
        for xx in (x, x+6):
            clear(xx, wy, z0-6, xx, wy+1, z0-5); box(xx, wy-1, z0-7, xx, wy+2, z0-7, P['bone2'])
    clear(x+2, y, z0-6, x+3, y, z0-4)                                       # door 2x3
    box(x+1, y, z0-7, x+4, y, z0-7, P['bone2'])
    box(x+2, y-1, z0-2, x+3, y-1, z0-1, P['wood']); box(x+2, y-2, z0-1, x+3, y-2, z0-1, P['wood'])  # steps
    box(x+2, y+10, z0-4, x+4, y+11, z0-4, P['wood3'])                       # table
    put(x+3, y+10, z0-5, P['amber']); put(x+1, y+6, z0-4, P['purple2'] if team == 0 else P['orange2'])
    put(x+3, y+6, z0-10, P['amber'])                                        # hanging lamp (from the vault)
    cobweb(x+1, y+11, z0-8, 1, -1)

def tent(cx, cy, team, R=5, Ht=9):
    """striped fortune-teller tent: 4-high cylindrical wall, stepped cone roof, doorway on +y,
    table and crystal ball inside."""
    z0 = gmax(cx-R, cy-R, cx+R, cy+R); acc = P['purple'] if team == 0 else P['orange']
    footing_clear(cx-R, cy-R, cx+R, cy+R, z0, P['wood3'])
    for x in range(cx-R, cx+R+1):
        for y in range(cy-R, cy+R+1): C[x, y, z0] = P['wood2'] if (x + y) % 2 else P['wood3']
    stripe = lambda x, y: acc if int((math.atan2(y-cy, x-cx)+math.pi)/(math.pi/4)) % 2 else P['bone2']
    for x in range(cx-R, cx+R+1):
        for y in range(cy-R, cy+R+1):
            d = math.hypot(x-cx, y-cy)
            if R - 1.1 < d <= R + 0.3:
                for dz in range(4): put(x, y, z0-1-dz, stripe(x, y))
    nroof = Ht - 4
    for k in range(nroof + 1):
        r = (R + 0.3) * (1 - k / (nroof + 1))
        for x in range(cx-R, cx+R+1):
            for y in range(cy-R, cy+R+1):
                d = math.hypot(x-cx, y-cy)
                if (r - 1.6 < d <= r) or (r < 2.2 and d <= r + 0.5): put(x, y, z0-5-k, stripe(x, y))
    box(cx, cy, z0-Ht-4, cx, cy, z0-Ht-1, P['iron']); put(cx, cy+1, z0-Ht-4, acc); put(cx, cy+1, z0-Ht-3, acc)
    clear(cx, cy+R-1, z0-3, cx+1, cy+R+1, z0-1)                              # doorway 2 wide x 3 tall
    put(cx, cy-1, z0-1, P['wood3']); put(cx, cy-1, z0-2, P['amber'])         # crystal-ball table
    kf = next(k for k in range(nroof + 1) if (R + 0.3) * (1 - k / (nroof + 1)) < 2.2)
    for z in range(z0-4-kf, z0-5): put(cx, cy, z, P['iron'])                  # chain from the peak
    put(cx, cy, z0-5, P['amber'])                                            # lantern

def jack_o_lantern(cx, cy, rx=6.5, rz=6.0, face=1):
    """giant carved pumpkin: hollow 2-voxel shell lit amber inside, carved face on +x,
    walk-in door on the north (-y) side."""
    z0 = gmax(int(cx)-3, int(cy)-3, int(cx)+3, int(cy)+3); zc = z0 - rz
    footing_clear(int(cx-5), int(cy-5), int(cx+5), int(cy+5), z0, P['pump2'])
    for x in range(int(cx-rx)-1, int(cx+rx)+2):
        for y in range(int(cy-rx)-1, int(cy+rx)+2):
            for z in range(int(zc-rz)-1, z0):
                d = ((x-cx)/rx)**2 + ((y-cy)/rx)**2 + ((z-zc)/rz)**2
                if d <= 1.0:
                    a = math.atan2(y-cy, x-cx); rib = int((a+math.pi)/(2*math.pi)*14) % 2
                    inner = ((x-cx)/(rx-2))**2 + ((y-cy)/(rx-2))**2 + ((z-zc)/(rz-2))**2
                    if inner < 1.0: S[x, y, z] = False
                    else: put(x, y, z, P['amber2'] if inner < 1.25 else (P['pump'] if rib else P['pump2']))
    for x in range(int(cx-rx), int(cx+rx)+1):                                # flat inside floor
        for y in range(int(cy-rx), int(cy+rx)+1):
            dd = math.hypot(x-cx, y-cy)
            if dd < rx - 3:
                S[x, y, int(zc):z0] = False; put(x, y, z0, P['wood3'])
            elif dd < rx - 1.5:
                for z in range(int(zc), z0):                                   # supporting drum wall
                    if not S[x, y, z]: put(x, y, z, P['pump2'])
    eyes = [(dy, dz) for dy in range(-4, -1) for dz in range(-3, 0) if dz >= -3 + abs(dy + 2.5)] + \
           [(dy, dz) for dy in range(2, 5) for dz in range(-3, 0) if dz >= -3 + abs(dy - 2.5)]
    nose = [(0, 0), (0, 1), (-1, 1), (1, 1)]
    mouth = [(dy, dz) for dy in range(-4, 5) for dz in (3, 4) if not (dz == 3 and dy in (-2, 2)) and not (dz == 4 and dy in (-3, 0, 3))]
    for dy, dz in eyes + nose + mouth:                                      # cut clean through the shell
        y = int(round(cy + dy)); z = int(round(zc + dz))
        for x in range(int(cx), int(cx+rx)+2): S[x, y, z] = False if S[x, y, z] and C[x, y, z] != P['wood3'] else S[x, y, z]
    door(int(cx)-1, int(cy-rx)-1, int(cx)+1, int(cy-rx)+4, z0, h=3)          # walk-in door (north)
    box(int(cx), int(cy), int(zc-rz)-3, int(cx)+1, int(cy)+1, int(zc-rz)+1, P['stem'])
    put(int(cx)+2, int(cy), int(zc-rz)-3, P['stem']); put(int(cx)+3, int(cy), int(zc-rz)-3, P['stem']); put(int(cx)+3, int(cy), int(zc-rz)-2, P['stem'])
    put(int(cx), int(cy), int(zc), P['amber']) if False else None

def ghost_train(x0, y0, x1, y1):
    """two-storey ride building: tunnel mouth (south) into a dark maze with coffins on the
    ground floor, a stair to an upper gallery with 'eye' windows, hollow gabled attic."""
    z0 = int(np.median(TZ[x0:x1+1, y0:y1+1])); L = [z0, z0 - 6, z0 - 12]
    footing_clear(x0, y0, x1, y1, z0, P['stone2'])
    m = np.zeros((W, H), bool); m[x0:x1+1, y0:y1+1] = True
    pm = perim(m)
    for F, Cz in zip(L[:-1], L[1:]):
        for x, y in zip(*np.nonzero(pm)): box(x, y, Cz+1, x, y, F-1, P['slate'] if (x + y) % 3 else P['iron'])
        box(x0, y0, Cz, x1, y1, Cz, P['wood3'])
    for x in range(x0+1, x1):
        for y in range(y0+1, y1):
            C[x, y, z0] = P['black'] if (x in (x0+3, x1-3) or y in (y0+3, y1-3)) and 0 else (P['wood3'] if (x+y) % 2 else P['slate'])
    for x in range(x0+3, x1-2):                                                # rail loop on the floor
        C[x, y0+3, z0] = P['iron']; C[x, y1-3, z0] = P['iron']
    for y in range(y0+3, y1-2): C[x0+3, y, z0] = P['iron']; C[x1-3, y, z0] = P['iron']
    for x, y in zip(*np.nonzero(pm)): C[x, y, L[1]] = P['bone2']                # stringcourse
    # ground floor maze walls + doors
    box(x0+7, y0+1, L[1]+1, x0+7, y1-6, z0-1, P['plaster']); door(x0+7, y0+8, x0+7, y0+9, z0)
    box(x0+8, y1-6, L[1]+1, x1-1, y1-6, z0-1, P['plaster']); door(x1-6, y1-6, x1-5, y1-6, z0)
    mid = (x0 + x1) // 2
    clear(mid-3, y1, z0-5, mid+3, y1, z0-1)                                    # tunnel mouth (south)
    box(mid-4, y1, z0-6, mid+4, y1, z0-6, P['bone2']); put(mid-4, y1, z0-5, P['bone2']); put(mid+4, y1, z0-5, P['bone2'])
    door(x1, y0+6, x1, y0+7, z0)                                               # exit door (east)
    for yy in range(y1+1, y1+6):
        for xx in (mid-2, mid+2):
            if TZ[xx, yy] < 60: put(xx, yy, g(xx, yy)-1, P['iron'])
    for k in (1, 2, 3):                                                         # steps up to the east exit
        for yy in (y0+6, y0+7):
            z = z0 + k
            if TZ[x1+k, yy] > z: box(x1+k, yy, z, x1+k, yy, TZ[x1+k, yy], P['stone2'])
    for (cx_, cy_) in [(x0+2, y0+2), (x0+10, y0+2), (x0+4, y1-4)]: coffin(cx_, cy_, z0, along_y=False)
    put(x0+8, y0+4, z0-1, P['bone']); put(x0+8, y0+4, z0-2, P['bone']); put(x0+8, y0+4, z0-3, P['bone2'])   # skeleton prop
    # stair to the gallery (west side), flight along x
    stair_flight(x0+9, y0+12, L[0], L[1], +1)
    # gallery: eye windows south + north, cobwebs
    for xx in (x0+4, x0+5, x1-5, x1-4):
        for yy in (y0, y1): clear(xx, yy, L[1]-3, xx, yy, L[1]-2)
    for yy in (y0, y1):
        box(x0+3, yy, L[1]-4, x0+6, yy, L[1]-4, P['amber2']); box(x1-6, yy, L[1]-4, x1-3, yy, L[1]-4, P['amber2'])
    cobweb(x0+1, y0+1, L[2]+1, 1, 1); cobweb(x1-1, y0+1, L[2]+1, -1, 1)
    for k, (xx, yy) in enumerate([(x0+2, y0+6), (x1-3, y0+9)]): coffin(xx, yy, L[1], along_y=True)
    # hollow gabled roof: two sloped 2-thick skins + gable end walls
    half = (x1 - x0) // 2; ztop = L[2]
    for k in range(half + 1):
        z = ztop - 1 - k // 2
        for xx in (x0 + k, x1 - k):
            box(xx, y0, z, xx, y1, z + 1 if k else z, P['rust'] if (k // 2) % 2 else P['rust2'])
        for yy in (y0, y1): box(x0 + k, yy, z, x1 - k, yy, ztop - 1, P['slate'])
    box(mid, y1, ztop - 4, mid + 1, y1, ztop - 3, P['amber'])                  # attic eye
    put(mid, y0 + 3, ztop - 1 - half // 2 - 1, P['black'])                     # crow on the ridge

# ------------------------------------------------------------------ THE PAVILION (contested centre building)
def pavilion():
    """'The Midnight Pavilion': same footprint and storey heights as Ruins' central
    building (x219..292, y262..308, roof z15). Six storeys of rooms, two switchback
    stairwells per half, an atrium lobby, a north loggia under the platform, roof deck."""
    LV = [51, 45, 39, 33, 27, 21, 15]
    low = np.zeros((W, H), bool)
    low[240:272, 268:301] = True                     # central tower x240..271, y268..300
    low[219:241, 286:309] = True                     # west wing x219..240, y286..308
    low[271:293, 286:309] = True                     # east wing (mirror)
    for x in range(219, 224):                        # chamfered outer wing corners
        for y in range(286, 309):
            if (x - 219) + (y - 286) < 4 or (x - 219) + (308 - y) < 4: low[x, y] = False; low[511 - x, y] = False
    for x in range(240, 243):
        for y in range(268, 271):
            if (x - 240) + (y - 268) < 2: low[x, y] = False; low[511 - x, y] = False
    top = low.copy(); top[242:270, 262:268] = True    # north overhang on the top storey
    masks = [low, low, low, low, low, top]
    footing_mask(low, LV[0], P['stone2'], clear_above=True)
    # slabs (floors) with plank tops, exterior edge trim
    for k, z in enumerate(LV):
        m = top if k >= 5 else low
        for x, y in zip(*np.nonzero(m)):
            put(x, y, z, (P['wood'] if y % 2 else P['wood2']) if 0 < k < 6 else P['stone'] if k == 0 else (P['slate'] if (x + y) % 5 else P['tar']))
        for x, y in zip(*np.nonzero(perim(m))): C[x, y, z] = P['rust2'] if k else P['stone2']
    # exterior walls
    for i in range(6):
        F, Cz = LV[i], LV[i + 1]; m = masks[i]; pm = perim(m)
        for x, y in zip(*np.nonzero(pm)):
            for z in range(Cz + 1, F):
                if i == 0: c = P['stone'] if ((z // 2) + (x + y) // 3) % 2 else P['stone2']
                else: c = P['wallA2'] if (x + y) % 3 == 0 else P['wallA']
                coord = y if (not m[x-1, y] or not m[x+1, y]) else x
                if i > 0 and coord % 6 == 0: c = P['bone2']                     # pilasters
                if z == Cz + 1: c = P['rust']                                   # cornice band
                put(x, y, z, c)
    # interior partitions (left half; mirrored later)
    parts = [(251, 269, 251, 299), (241, 279, 250, 279), (241, 290, 250, 290),
             (240, 287, 240, 299), (229, 287, 229, 307), (220, 297, 239, 297)]
    for i in range(6):
        F, Cz = LV[i], LV[i + 1]
        for (a, b, c_, d) in parts:
            box(a, b, Cz + 1, c_, d, F - 1, P['plaster'])
            box(a, b, F - 1, c_, d, F - 1, P['wood3'])                           # wainscot
        if i == 5: box(251, 263, Cz + 1, 251, 268, F - 1, P['plaster'])
        if i == 2:                                                               # hall of mirrors floor
            box(251, 269, Cz + 2, 251, 299, F - 2, P['mirror']); box(240, 287, Cz + 2, 240, 299, F - 2, P['mirror'])
        # interior doors (2 wide x 3 tall)
        for (a, b, c_, d) in [(251, 272, 251, 273), (251, 284, 251, 285), (251, 294, 251, 295),
                              (249, 279, 250, 279), (249, 290, 250, 290), (240, 292, 240, 293),
                              (229, 291, 229, 292), (229, 305, 229, 306), (223, 297, 224, 297), (238, 297, 239, 297)]:
            door(a, b, c_, d, F)
        if i == 5: door(251, 265, 251, 266, F)
        # windows on every storey except where the clock is painted
        clock = lambda x, y, z: (y == 268 and 247 <= x <= 264 and 26 <= z <= 40)
        windows_on(masks[i], F, Cz, skip=clock)
    # ground-floor arcade doors (4 tall) + stoops
    gdoors = [(247, 268, 249, 268, 0, -1), (254, 268, 257, 268, 0, -1), (240, 274, 240, 276, -1, 0),
              (219, 296, 219, 298, -1, 0), (225, 286, 227, 286, 0, -1), (233, 286, 235, 286, 0, -1),
              (223, 308, 225, 308, 0, 1), (233, 308, 235, 308, 0, 1), (254, 300, 257, 300, 0, 1),
              (246, 300, 248, 300, 0, 1), (240, 303, 240, 305, 1, 0)]
    for (a, b, c_, d, ox, oy) in gdoors:
        door(a, b, c_, d, LV[0], h=4)
        box(a, b, LV[0] - 5, c_, d, LV[0] - 5, P['bone2'])                       # lintel
        for x in range(a, c_ + 1):
            for y in range(b, d + 1):
                sx, sy = x + ox, y + oy
                if TZ[sx, sy] > LV[0] + 1: box(sx, sy, LV[0] + 1, sx, sy, TZ[sx, sy], P['stone2'])   # stoop
    # north loggia on the top storey (open arches looking at the platform)
    for x in range(243, 269):
        if x % 4 in (0, 1): clear(x, 262, LV[5] - 3, x, 262, LV[5] - 1)
    for x in (244, 249, 253):                                                    # overhang brackets
        box(x, 267, LV[5] + 1, x, 267, LV[5] + 3, P['bone2']); box(x, 266, LV[5] + 1, x, 266, LV[5] + 2, P['bone2']); put(x, 265, LV[5] + 1, P['bone2'])
    # stairs: tower (s=243, lanes y282/285) and wing (s=232, lanes y300/303), all storeys to the roof
    stair_stack(243, 282, 285, LV); stair_stack(232, 300, 303, LV)
    # atrium: double-height lobby (opening in the first-floor slab) with a broken rail
    clear(253, 281, LV[1], 258, 286, LV[1])
    for x in range(252, 260):
        for y in (280, 287):
            if x not in (255, 256): put(x, y, LV[1] - 1, P['iron'])
    for y in range(281, 287): put(252, y, LV[1] - 1, P['iron'])
    # roof deck: crenellated parapet, hatches already cut by the stairs, crows
    for x, y in zip(*np.nonzero(perim(top))):
        if (x + y) % 3 != 2: put(x, y, LV[6] - 1, P['bone2'] if (x + y) % 2 else P['stone2'])
    for (x, y) in [(219, 296), (233, 286), (245, 262), (236, 308)]:
        if S[x, y, LV[6] - 1]: put(x, y, LV[6] - 2, P['black'])
    # clock face on the tower's north wall (painted, below the overhang)
    ccx, ccz = 255.5, 33
    for x in range(247, 265):
        for z in range(26, 41):
            d = math.hypot(x - ccx, (z - ccz) * 1.0)
            if d <= 6.5 and S[x, 268, z]:
                C[x, 268, z] = P['rust'] if d > 5.6 else P['bone']
    for z in range(29, 34): C[255, 268, z] = P['black']; C[256, 268, z] = P['black']      # hands
    for x in range(256, 260): C[x, 268, 33] = P['black']
    for (x, z) in [(255, 28), (256, 28), (261, 33), (250, 33), (255, 38), (256, 38)]: C[x, 268, z] = P['amber2']
    # team banners on the wing south faces (mirrored to orange)
    for x in (229, 230):
        for z in range(23, 40):
            if S[x, 308, z]: C[x, 308, z] = P['purple']
    # interior dressing: corridor lanterns, room corners, coffins upstairs, cobwebs
    for i in range(6):
        F, Cz = LV[i], LV[i + 1]
        for y in range(271, 300, 6):
            if S[254, y, Cz]: put(254, y, Cz + 1, P['amber'])                    # corridor lanterns
        rooms = [(241, 269, 250, 278), (241, 291, 250, 299), (220, 287, 228, 296), (220, 298, 228, 307), (230, 287, 239, 296)]
        for k, (a, b, c_, d) in enumerate(rooms):
            if (i + k) % 3 == 0: crate(a + 1, b + 1, tall=(i % 2 == 0), z0=F)
            elif (i + k) % 3 == 1: barrel(c_ - 2, d - 2, z0=F)
            elif i >= 3: coffin(a + 2, b + 2, F, along_y=True)
            cobweb(a, b, Cz + 1, 1, 1)
        put(221, 300, F - 1, P['wood3']); put(221, 300, F - 2, P['amber2']) if i % 2 else None
    return LV

# ------------------------------------------------------------------ Ferris wheel + operator station (secondary point)
def ferris_wheel():
    wx, wy, R, hubz = 255.5, 182, 23, 28
    zb = gmax(236, 176, 275, 188)
    footing(230, 177, 281, 187, zb, P['stone2'])
    for x in range(230, 282):
        for y in range(177, 188): C[x, y, zb] = P['stone'] if (x // 3 + y // 3) % 2 else P['stone2']
    for side in (-1, 1):
        foot = wx + side * (zb - hubz) * 0.45
        for yy in (wy - 4, wy + 4):
            fline((foot - 0.5, yy, zb - 1), (wx - 0.5 + side * 1.5, yy, hubz), P['rust2'], w=2)
            for frac in (0.35, 0.7):
                z = zb - 1 - (zb - hubz) * frac; xx = wx + side * (zb - hubz) * 0.45 * (1 - frac)
                fline((xx, yy, z), (wx, yy, z), P['rust2'])
        fline((foot, wy - 4, zb - 8), (foot, wy + 4, zb - 8), P['rust2'])
    box(254, wy - 4, hubz - 1, 257, wy + 4, hubz + 1, P['iron'])
    ring = []
    for t in range(900):
        a = t * 2 * math.pi / 900
        p = (int(round(wx + R * math.cos(a))), int(round(hubz + R * math.sin(a))))
        if not ring or ring[-1] != p: ring.append(p)
    for yy in (wy - 2, wy + 2):
        for (x0_, z0_), (x1_, z1_) in zip(ring, ring[1:] + ring[:1]):
            fline((x0_, yy, z0_), (x1_, yy, z1_), P['rust'])
            fline((wx + (x0_ - wx) * (R - 1) / R, yy, hubz + (z0_ - hubz) * (R - 1) / R),
                  (wx + (x1_ - wx) * (R - 1) / R, yy, hubz + (z1_ - hubz) * (R - 1) / R), P['rust'])
        for k in range(12):
            a = k * math.pi / 6
            fline((wx, yy, hubz), (wx + R * math.cos(a), yy, hubz + R * math.sin(a)), P['rust2'])
    for k in range(12):                                   # open-top gondola buckets you can stand in
        a = k * math.pi / 6 + math.pi / 12
        gx = int(round(wx + R * math.cos(a))); gz = int(round(hubz + R * math.sin(a)))
        if gz + 6 >= zb: continue
        box(gx - 2, wy - 2, gz, gx + 2, wy + 2, gz, P['iron'])                    # roof plate rim-to-rim
        col = [P['amber2'], P['purple'], P['teal'], P['red']][k % 4]
        box(gx - 2, wy - 1, gz + 1, gx + 2, wy + 1, gz + 4, col)                   # bucket, open on y sides
        clear(gx - 1, wy - 1, gz + 1, gx + 1, wy + 1, gz + 3)
        box(gx - 1, wy - 1, gz + 4, gx + 1, wy + 1, gz + 4, P['bone2'])          # floor
    for t in range(1800):
        a = t * math.pi / 900
        if int(a * 12) % 2 == 0:
            x = int(round(wx + R * math.cos(a))); z = int(round(hubz + R * math.sin(a)))
            if S[x, wy - 2, z]: put(x, wy - 3, z, P['amber'])
    # operator station: 2 storeys with rooms, stair to roof, iron gantry ramps to the hub deck
    m = np.zeros((W, H), bool); m[240:272, 156:171] = True
    F0 = gmax(240, 156, 271, 170) - 1; LV = [F0, F0 - 6, F0 - 12]
    footing_mask(m, F0, P['stone2'], clear_above=True)
    for k, z in enumerate(LV):
        for x, y in zip(*np.nonzero(m)): put(x, y, z, (P['wood'] if y % 2 else P['wood2']) if k == 1 else P['stone'] if k == 0 else P['slate'])
        for x, y in zip(*np.nonzero(perim(m))): C[x, y, z] = P['rust2']
    for i in range(2):
        F, Cz = LV[i], LV[i + 1]
        for x, y in zip(*np.nonzero(perim(m))):
            for z in range(Cz + 1, F):
                c = P['rust'] if (x + y) % 4 else P['rust2']
                if (x % 8 == 0 and (y in (156, 170))) or (y % 8 == 0 and x in (240, 271)): c = P['bone2']
                if z == Cz + 1: c = P['bone2']
                put(x, y, z, c)
        box(251, 157, Cz + 1, 251, 169, F - 1, P['plaster']); door(251, 163, 251, 164, F)
        windows_on(m, F, Cz, every=5)
    for (a, b, c_, d) in [(254, 170, 257, 170), (244, 170, 246, 170), (254, 156, 257, 156), (240, 162, 240, 164)]:
        door(a, b, c_, d, LV[0], h=4); box(a, b, LV[0] - 5, c_, d, LV[0] - 5, P['bone2'])
    box(253, 168, LV[0] - 2, 258, 168, LV[0] - 1, P['wood3'])                    # ticket counter
    stair_stack(243, 158, 161, LV)
    for x, y in zip(*np.nonzero(perim(m))):
        if (x + y) % 3 != 2 and not (249 <= x <= 262 and y == 170): put(x, y, LV[2] - 1, P['bone2'])
    deck = hubz + 1
    for x in (249, 250, 251):                                                    # gantry ramp (one per side)
        for j in range(1, LV[2] - deck + 1):
            y = 159 + j
            box(x, y, LV[2] - j, x, y, LV[2] - j, P['iron'] if j % 2 else P['slate'])
            if y <= 170: box(x, y, LV[2] - j, x, y, LV[2] - 1, P['iron'])
            else: put(x, y, LV[2] - j + 1, P['iron'])
    box(249, 171, deck, 262, 177, deck, P['iron'])                               # hub deck
    for x in range(249, 263):
        if x not in (249, 250, 251, 260, 261, 262): put(x, 171, deck - 1, P['bone2'])
    for y in range(172, 178): put(249, y, deck - 1, P['bone2'])
    box(254, 177, deck - 1, 255, 177, deck - 1, P['iron'])                       # step up onto the axle
    for y in range(171, 177, 2): put(252, y, deck + 1, P['iron'])                # underside ribs to the ramps
    return hubz

# ------------------------------------------------------------------ carousel (open, centre)
def carousel(cx=255.5, cy=251.0, RD=15.5, RC=13.5, RH=10):
    """open carousel on the basin floor north of the pavilion: stone deck, plinth, pole,
    stepped striped canopy with a bulb fringe, 12 horses on poles."""
    zg = gmax(int(cx - RD), int(cy - RD), int(cx + RD), int(cy + RD))
    for x in range(int(cx - RD) - 1, int(cx + RD) + 2):
        for y in range(int(cy - RD) - 1, int(cy + RD) + 2):
            r = math.hypot(x - cx, y - cy)
            if r <= RD:
                box(x, y, zg-1, x, y, TZ[x, y], P['stone2'] if r > RD - 1.5 else P['stone'])
                if r > RD - 1: C[x, y, zg-1] = P['bone2']
    for x in range(int(cx) - 4, int(cx) + 5):
        for y in range(int(cy) - 4, int(cy) + 5):
            if math.hypot(x - cx, y - cy) <= 3.6: box(x, y, zg-4, x, y, zg-2, P['stone'])
    canz = zg - 18
    box(254, int(cy) - 1, canz, 257, int(cy), zg-5, P['rust'])
    for x in range(int(cx - RC) - 1, int(cx + RC) + 2):
        for y in range(int(cy - RC) - 1, int(cy + RC) + 2):
            r = math.hypot(x - cx, y - cy)
            if r <= RC:
                zz = canz + int(r / 4)
                a = math.atan2(y - cy, x - cx); seg = int((a + math.pi) / (math.pi / 8)) % 2
                box(x, y, canz + int(max(r - 1.5, 0) / 4), x, y, zz, P['red'] if seg else P['bone2'])
                if RC - 1 < r <= RC: put(x, y, zz + 1, P['amber'] if (int((a + math.pi) * 8)) % 2 else P['bone2'])
    box(254, int(cy) - 1, canz-4, 257, int(cy), canz-1, P['rust']); put(255, int(cy) - 1, canz-5, P['amber']); put(256, int(cy) - 1, canz-5, P['amber'])
    for k in range(12):
        a = (k + 0.5) * math.pi / 6; px = int(round(cx + RH * math.cos(a))); py = int(round(cy + RH * math.sin(a)))
        box(px, py, canz + 3, px, py, zg-2, P['bone2'] if k % 2 else P['amber2'])
        hz = zg - 6 - (k % 2) * 2
        horiz = abs(-math.sin(a)) > abs(math.cos(a))
        for dx in (-2, -1, 0, 1):
            hx, hy = (px + dx, py) if horiz else (px, py + dx)
            put(hx, hy, hz, P['bone']); put(hx, hy, hz+1, P['bone'])
        hx, hy = (px + 2, py) if horiz else (px, py + 2)
        put(hx, hy, hz-1, P['bone']); put(hx, hy, hz, P['bone'])
        for dx in (-2, 1):
            hx, hy = (px + dx, py) if horiz else (px, py + dx); put(hx, hy, hz+2, P['bone2'])
        hx, hy = (px - 1, py) if horiz else (px, py - 1); put(hx, hy, hz-1, P['red'])

# ================================================================== LAYOUT
team = 0
SPX0, SPX1, SPY0, SPY1 = 98, 138, 236, 276          # blue spawn square (babel_script: base 118,256 +-20)
for x in range(SPX0, SPX1 + 1):
    for y in range(SPY0, SPY1 + 1):
        if TZ[x, y] < 62 and slope[x, y] < 2 and (x // 4 + y // 4) % 2 == 0 and not pathmask[x, y]:
            C[x, y, TZ[x, y]] = shade(C[x, y, TZ[x, y]], 0.9)
caravan(70, 222, team); caravan(76, 270, team)
tent(84, 208, team, R=5, Ht=9); tent(82, 300, team, R=5, Ht=8)
jack_o_lantern(73, 256, face=1)
gate_arch(116, 214, 227, team); stall(103, 229, 'ticket', team, facing=-1)
gate_arch(118, 285, 298, team); stall(104, 279, 'ticket', team, facing=1)
for (px, py) in [(102, 218), (106, 296), (88, 244)]: pumpkin(px, py, g(px, py), big=True)
for (px, py, f) in [(110, 232, 1), (90, 267, 1), (92, 250, 1), (124, 230, 1), (126, 282, -1), (140, 300, -1)]: jack_small(px, py, f)
for (px, py) in [(99, 284), (88, 316), (70, 200)]: pumpkin(px, py, g(px, py))
pumpkin_patch(90, 194, 104, 204); scarecrow(97, 199, team)
pumpkin_patch(90, 304, 106, 314); scarecrow(98, 309, team)
graveyard(108, 302, 124, 314, SEED + 50)
for (hx, hy, ax) in [(80, 240, True), (82, 264, False), (64, 236, True), (64, 276, True), (100, 296, True)]: hay(hx, hy, ax)
for (cx_, cy_, t_) in [(88, 232, True), (124, 208, True)]: crate(cx_, cy_, t_)
for (bx_, by_) in [(91, 229), (88, 287)]: barrel(bx_, by_)
for i, (tx, ty) in enumerate([(98, 228), (96, 288), (137, 292), (147, 168), (174, 168),
                               (176, 313), (179, 197), (204, 174), (220, 317), (72, 210), (64, 296)]):
    if TZ[tx, ty] < 62 and not (SPX0 - 3 <= tx <= SPX1 + 3 and SPY0 - 3 <= ty <= SPY1 + 3):
        dead_tree(tx, ty, SEED + i, leaves=(i % 5 not in (1, 3)))
ghost_train(141, 177, 161, 190)          # on Ruins' north bastion (x~138-160, y~175-195)
for i, y in enumerate(range(196, 212)):  # timber pier from the bastion forecourt down to the neck (Ruins had a ladder here)
    z = 50 + round(2 * i / 15)
    for x in range(140, 144):
        if TZ[x, y] > z: put(x, y, z, P['wood'] if y % 2 else P['wood2'])
    for x in (140, 143):
        if TZ[x, y] > z: put(x, y, z - 1, P['wood3'])
        if y % 4 == 0 and TZ[x, y] > z: box(x, y, z + 1, x, y, TZ[x, y] - 1, P['wood3'])
for (tx, ty, th) in [(160, 198, 3), (165, 200, 2), (168, 197, 3)]:
    if TZ[tx, ty] < 60: tombstone(tx, ty, th)
kinds = ['apple', 'pumpkin', 'apple', 'pumpkin']
for i, sx in enumerate(range(176, 236, 15)): stall(sx, 172, kinds[i], team, facing=1)
lamps = [lamp(x, 197, face=-1) for x in range(174, 238, 12)]
for a, b in zip(lamps, lamps[1:]): bunting(a, b)
boardwalk_bridge(138, 172, 212, 218, 52)
for yy, face in ((236, 1), (276, -1)):
    row = [lamp(x, yy, face=face) for x in range(150, 204, 13) if TZ[x, yy] < 62]
    for a, b in zip(row, row[1:]): bunting(a, b)
bumper_pen(178, 300, 202, 314, team)
boardwalk_bridge(150, 214, 326, 330, 53)
bl = [lamp_on(x, 330, 53) for x in range(156, 214, 14) if S[x, 330, 53]]
for a, b in zip(bl, bl[1:]): bunting(a, b)
for (hx, hy) in [(206, 304), (174, 318)]: hay(hx, hy)

# centre structures (drawn across the centre; the left half is authoritative after mirroring)
carousel()
LV = pavilion()
HUBZ = ferris_wheel()

# ------------------------------------------------------------------ mirror L -> R (team accents swap)
Sl = S[:256].copy(); Cl = C[:256].copy()
Cr = Cl.copy()
for a_, b_ in {P['purple']: P['orange'], P['purple2']: P['orange2']}.items(): Cr[Cl == a_] = b_
S[256:] = Sl[::-1]; C[256:] = Cr[::-1]
S[:, :, WATER] = True

# ------------------------------------------------------------------ corner tag (map name only), painted on the sea floor
FONT = {
 'A': ['01110','10001','10001','11111','10001','10001','10001'],
 'D': ['11110','10001','10001','10001','10001','10001','11110'],
 'E': ['11111','10000','10000','11110','10000','10000','11111'],
 'F': ['11111','10000','10000','11110','10000','10000','10000'],
 'G': ['01111','10000','10000','10011','10001','10001','01111'],
 'H': ['10001','10001','10001','11111','10001','10001','10001'],
 'I': ['11111','00100','00100','00100','00100','00100','11111'],
 'L': ['10000','10000','10000','10000','10000','10000','11111'],
 'N': ['10001','11001','10101','10011','10001','10001','10001'],
 'O': ['01110','10001','10001','10001','10001','10001','01110'],
 'R': ['11110','10001','10001','11110','10100','10010','10001'],
 'S': ['01111','10000','10000','01110','00001','00001','11110'],
 'T': ['11111','00100','00100','00100','00100','00100','00100'],
 'U': ['10001','10001','10001','10001','10001','10001','01110'],
 ' ': ['00000'] * 7}
def corner_tag(text, x0, y0, scale=2, col=None, shadow=None):
    x = x0
    for ch in text:
        glyph = FONT[ch]
        for r, row in enumerate(glyph):
            for c, bit in enumerate(row):
                if bit == '1':
                    for dx in range(scale):
                        for dy in range(scale):
                            px, py = x + c * scale + dx, y0 + r * scale + dy
                            if shadow is not None and S[px + 1, py + 1, WATER] and not S[px + 1, py + 1, :WATER].any():
                                C[px + 1, py + 1, WATER] = shadow
                            C[px, py, WATER] = col
        x += (5 + 1) * scale
TAG_TEXT = 'HAUNTED FAIRGROUND'
assert not S[8:8 + len(TAG_TEXT) * 12 + 4, 482:502, :WATER].any()     # nothing above the tag area
corner_tag(TAG_TEXT, 10, 486, scale=2, col=P['amber'], shadow=P['black'])

out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'haunted_fairground.vxl')
vxlio.write(out, S, C)
if os.environ.get('HFI_DEBUG'): np.save('solid4.npy', S); np.save('tz4.npy', TZ); np.save('col4.npy', C)
print('written', out, 'solid', int(S.sum()), 'highest voxel z', int(np.argmax(S, axis=2)[S[:, :, :62].any(2)].min()))
