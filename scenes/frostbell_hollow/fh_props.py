"""Frostbell Hollow one-off props on the graybox feature pads (built after the mirror, per side, so every snowman and
sculpture is unique; each pad box is recorded as a cosmetic box). Everything stays inside its pad's x/y box and
stands on the pad (face contact), so gameplay changes are limited to the reserved pads (fh_checks.collision_diff).
All choices come from the build's OS seed (owner rule: decoration is non-deterministic, seed saved)."""
from __future__ import annotations

import math

import numpy as np

from aosmap.kit.color import clamp8, mix, shade

SNOWBODY = [(198, 202, 210), (192, 198, 208), (204, 206, 212)]
SCARVES = [(168, 46, 48), (52, 112, 72), (196, 150, 60), (90, 70, 140), (40, 120, 140), (200, 110, 50),
           (140, 40, 90), (70, 96, 150), (150, 150, 160), (120, 80, 50)]
HATS = ['top hat', 'beanie', 'bucket', 'holly crown', 'earmuffs', 'bowler', 'tricorn', 'flowerpot']
ACCESSORIES = ['broom', 'lantern', 'pipe', 'buttons', 'mittens', 'book', 'shovel', 'bird']
ICE_SHAPES = ['swan', 'stag', 'angel', 'bell', 'star', 'harp']
ICE_A, ICE_B = (150, 198, 214), (192, 212, 220)


def _ball(cv, cx, cy, cz, r, cols, rng, mat='snowman'):
    pts = []
    R = int(math.ceil(r))
    for x in range(int(cx) - R - 1, int(cx) + R + 2):
        for y in range(int(cy) - R - 1, int(cy) + R + 2):
            for z in range(int(cz) - R - 1, int(cz) + R + 2):
                if (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 + ((z + 0.5 - cz) * 1.05) ** 2 <= r * r:
                    c = cols[int(rng.integers(len(cols)))]
                    c = shade(c, 1.0 - 0.06 * max(0, (z + 0.5 - cz) / max(r, 1)))
                    cv.set(x, y, z, c, mat)
                    pts.append((x, y, z))
    return pts


def snowman(cv, rng, x0, x1, y0, y1, pz, hat, acc, scarf, pose, scale=1.0, face=(1, 0)):
    """pz = pad top z. Three balls, coal eyes, carrot nose, scarf, hat type, accessory, pose (lean / wave / sit)."""
    cx, cy = (x0 + x1 + 1) / 2.0, (y0 + y1 + 1) / 2.0
    r1, r2, r3 = 2.4 * scale, 1.8 * scale, 1.35 * scale
    lean = 0.6 if pose == 'lean' else 0.0
    z1 = pz - r1 + 0.4
    z2 = z1 - r1 - r2 + 0.9
    z3 = z2 - r2 - r3 + 0.9
    _ball(cv, cx, cy, z1, r1, SNOWBODY, rng)
    _ball(cv, cx + lean * face[0], cy + lean * face[1], z2, r2, SNOWBODY, rng)
    hx, hy = cx + 2 * lean * face[0], cy + 2 * lean * face[1]
    _ball(cv, hx, hy, z3, r3, SNOWBODY, rng)
    fx, fy = face
    ix, iy, iz = int(math.floor(hx)), int(math.floor(hy)), int(math.floor(z3))
    # face: coal eyes and a carrot nose on the outermost head voxels facing `face`
    side = (-fy, fx)

    def outer(ax, ay, az):
        for k in range(4, -1, -1):
            if cv.get(ax + fx * k, ay + fy * k, az):
                return ax + fx * k, ay + fy * k
        return None
    for sgn in (-1, 1):
        e = outer(ix + side[0] * sgn, iy + side[1] * sgn, iz - 1)
        if e:
            cv.rgb[e[0], e[1], iz - 1] = (46, 44, 50)
    e = outer(ix, iy, iz) or (ix, iy)
    ex, ey = e
    cv.rgb[ex, ey, iz] = (214, 120, 52)
    nx, ny = ex + fx, ey + fy
    if x0 <= nx <= x1 and y0 <= ny <= y1:
        cv.set(nx, ny, iz, (204, 110, 46), 'snowman')
    # scarf: ring at the neck
    zn = int(math.floor(z3 + r3 - 0.3))
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            px, py = ix + dx, iy + dy
            if cv.get(px, py, zn) and cv.mat[px, py, zn] == cv.materials.get('snowman') and \
                    (abs(dx) == 1 or abs(dy) == 1 or abs(dx) == 2 or abs(dy) == 2):
                cv.rgb[px, py, zn] = scarf if (dx + dy) % 3 else shade(scarf, 0.75)
    tail = (ix - fx + side[0], iy - fy + side[1])
    for k in range(1, 3):
        if x0 <= tail[0] <= x1 and y0 <= tail[1] <= y1:
            cv.set(tail[0], tail[1], zn + k - 1, scarf, 'snowman')
    # hat
    zt = int(math.floor(z3 - r3 + 0.2))           # top voxel of the head
    hc = {'top hat': (44, 42, 50), 'beanie': scarf, 'bucket': (130, 132, 140), 'bowler': (60, 50, 44),
          'tricorn': (54, 48, 60), 'flowerpot': (176, 96, 64), 'holly crown': (40, 92, 56), 'earmuffs': scarf}[hat]
    if hat in ('top hat', 'bucket', 'flowerpot', 'bowler', 'tricorn'):
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if hat != 'bowler' or abs(dx) + abs(dy) < 2:
                    cv.set(ix + dx, iy + dy, zt - 1, shade(hc, 0.9), 'snowman')        # brim
        n = {'top hat': 3, 'bucket': 2, 'flowerpot': 2, 'bowler': 1, 'tricorn': 1}[hat]
        for k in range(n):
            cv.set(ix, iy, zt - 2 - k, hc, 'snowman')
            if hat in ('top hat', 'flowerpot') and k < n - 1:
                cv.set(ix + side[0], iy + side[1], zt - 2 - k, hc, 'snowman')
        if hat == 'top hat':
            cv.rgb[ix, iy, zt - 2] = (168, 46, 48)                                     # band
        if hat == 'tricorn':
            for (dx, dy) in ((fx, fy), (-fx + side[0], -fy + side[1]), (-fx - side[0], -fy - side[1])):
                cv.set(ix + dx, iy + dy, zt - 2, hc, 'snowman') if cv.get(ix + dx, iy + dy, zt - 1) else None
    elif hat == 'beanie':
        cv.set(ix, iy, zt - 1, hc, 'snowman')
        cv.set(ix, iy, zt - 2, (214, 206, 190), 'snowman')                             # pompom
    elif hat == 'holly crown':
        for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if cv.get(ix + dx, iy + dy, zt) or cv.get(ix, iy, zt):
                cv.set(ix + dx, iy + dy, zt - 1, hc, 'snowman')
        cv.set(ix, iy, zt - 1, (170, 40, 44), 'snowman')
    elif hat == 'earmuffs':
        for s in (-1, 1):
            px, py = ix + side[0] * (int(r3) + 1) * s, iy + side[1] * (int(r3) + 1) * s
            if x0 <= px <= x1 and y0 <= py <= y1:
                cv.set(px, py, iz, hc, 'snowman')
        cv.set(ix, iy, zt - 1, shade(hc, 0.8), 'snowman')
    # arms (twigs) from the body sides, pose-dependent; stay inside the pad box
    za = int(math.floor(z2))
    for s in (-1, 1):
        ax, ay = int(math.floor(cx)) + side[0] * s * (int(r2) + 1), int(math.floor(cy)) + side[1] * s * (int(r2) + 1)
        up = 1 if (pose == 'wave' and s == 1) else 0
        pts = [(ax, ay, za), (ax, ay, za - 1 if up else za)]
        if up:
            pts.append((ax, ay, za - 2))
        for (px, py, pz) in pts:
            if x0 <= px <= x1 and y0 <= py <= y1:
                cv.set(px, py, pz, (96, 72, 54), 'snowman')
        if acc == 'mittens' and x0 <= ax <= x1 and y0 <= ay <= y1:
            cv.rgb[ax, ay, pts[-1][2]] = scarf
    # accessory
    glow = []
    bx, by = int(math.floor(cx)) + side[0] * (int(r1) + 1), int(math.floor(cy)) + side[1] * (int(r1) + 1)
    inside = x0 <= bx <= x1 and y0 <= by <= y1
    if acc == 'broom' and inside:
        for k in range(0, 6):
            cv.set(bx, by, pz - 1 - k, (120, 90, 60), 'snowman')
        cv.set(bx, by, pz - 1, (190, 160, 90), 'snowman')
    elif acc == 'lantern' and inside:
        cv.set(bx, by, pz - 1, (60, 52, 44), 'snowman')
        cv.set(bx, by, pz - 2, (60, 52, 44), 'snowman')
        glow.append((bx, by, pz - 3, (255, 175, 95)))
        cv.set(bx, by, pz - 3, (255, 175, 95), 'snowman')
    elif acc == 'pipe':
        px, py = ex + side[0], ey + side[1]
        cv.set(px, py, iz + 1, (110, 76, 52), 'snowman')
    elif acc == 'buttons':
        bxx, byy = int(math.floor(cx)) + fx * int(math.ceil(r2 - 0.5)), int(math.floor(cy)) + fy * int(math.ceil(r2 - 0.5))
        for dz in (-1, 0, 1):
            if cv.get(bxx, byy, za + dz):
                cv.rgb[bxx, byy, za + dz] = (46, 44, 50)
    elif acc == 'book' and inside:
        cv.set(bx, by, pz - 1, (120, 50, 46), 'snowman')
    elif acc == 'shovel' and inside:
        for k in range(0, 4):
            cv.set(bx, by, pz - 1 - k, (110, 84, 60), 'snowman')
        cv.set(bx, by, pz - 1, (130, 132, 140), 'snowman')
    elif acc == 'bird':
        tz = cv.column_top(ix, iy, max(0, zt - 8))
        if tz > 7:
            cv.set(ix, iy, tz - 1, (186, 82, 52), 'snowman')
    return glow


def _ice(cv, x, y, z, t):
    cv.set(x, y, z, clamp8(mix(ICE_A, ICE_B, max(0.0, min(1.0, t)))), 'ice_art')


def ice_sculpture(cv, rng, x0, x1, y0, y1, pz, shape):
    """Original ice sculptures on a plinth (swan, stag, angel, bell, star, harp), cyan-tinted gradient, one cyan glow
    voxel inside the plinth. Shapes are drawn in the long axis of the pad; all face-connected via the plinth."""
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    long_x = (x1 - x0) >= (y1 - y0)
    for x in range(cx - 1, cx + 2):
        for y in range(cy - 1, cy + 2):
            _ice(cv, x, y, pz - 1, 0.2)
    base = pz - 2

    def P(u, v, h, t=None):        # u along the long axis, v across, h up from the plinth
        x, y = (cx + u, cy + v) if long_x else (cx + v, cy + u)
        if x0 <= x <= x1 and y0 <= y <= y1:
            _ice(cv, x, y, base - h, h / 9.0 if t is None else t)
    if shape == 'swan':
        for u in range(-2, 3):
            P(u, 0, 0)
            P(u, 0, 1)
        for u in (-1, 0, 1):
            P(u, -1, 1)
            P(u, 1, 1)
        for h in range(2, 6):
            P(2, 0, h)
        P(1, 0, 5)
        P(0, 0, 5)
        P(-2, 0, 2)
        P(-3, 0, 2) if True else None
    elif shape == 'stag':
        for u in range(-2, 3):
            P(u, 0, 2)
        for u in (-2, 2):
            P(u, 0, 0)
            P(u, 0, 1)
        for h in range(3, 6):
            P(2, 0, h)
        for (u, v, h) in ((2, -1, 5), (2, 1, 5), (2, -2, 6), (2, 2, 6), (1, -2, 6), (1, 2, 6), (2, -2, 7),
                          (2, 2, 7), (3, 0, 4)):
            P(u, v, h)
        P(2, -1, 6)
        P(2, 1, 6)
    elif shape == 'angel':
        for h in range(0, 6):
            P(0, 0, h)
        for h in range(0, 3):
            P(-1, 0, h)
            P(1, 0, h)
        for (v, h) in ((-1, 3), (-2, 4), (-2, 5), (-3, 5), (1, 3), (2, 4), (2, 5), (3, 5), (-1, 4), (1, 4)):
            P(0, v, h)
        P(0, 0, 7)
        P(0, 0, 6)
    elif shape == 'bell':
        for h in range(0, 6):
            w = [2, 2, 1, 1, 1, 0][h]
            for u in range(-w, w + 1):
                for v in range(-w, w + 1):
                    if abs(u) == w or abs(v) == w or h >= 4:
                        P(u, v, h)
        P(0, 0, 6)
        P(0, 0, 0, 0.1)
    elif shape == 'star':
        for h in range(0, 3):
            P(0, 0, h)
        for (u, h) in ((0, 3), (0, 4), (0, 5), (0, 6), (0, 7), (-1, 5), (-2, 5), (1, 5), (2, 5), (-1, 4), (1, 4),
                       (-1, 3), (1, 3)):
            P(u, 0, h)
    elif shape == 'harp':
        for h in range(0, 8):
            P(-2, 0, h)
        for u in range(-2, 3):
            P(u, 0, 0)
        for (u, h) in ((-1, 7), (0, 7), (0, 6), (1, 6), (1, 5), (2, 5), (2, 4), (2, 3), (2, 2), (2, 1)):
            P(u, 0, h)
        for h in range(1, 7):
            P(-1, 0, h, 0.95)
        for h in range(1, 5):
            P(1, 0, h, 0.95)
    return [(cx, cy, pz - 1, (95, 255, 255))]


def sled_stack(cv, rng, x0, x1, y0, y1, pz):
    cols = [(168, 46, 48), (52, 100, 70), (60, 84, 130), (180, 140, 60)]
    rng.shuffle(cols)
    long_x = (x1 - x0) >= (y1 - y0)
    for k in range(int(rng.integers(2, 4))):
        z = pz - 1 - k
        if long_x:
            cv.box(x0 + 1, x1 - 1, y0 + 1 + (k % 2), y0 + 2 + (k % 2), z, z, cols[k], 'sled')
        else:
            cv.box(x0 + 1 + (k % 2), x0 + 2 + (k % 2), y0 + 1, y1 - 1, z, z, cols[k], 'sled')
    return []


def snow_fort(cv, rng, x0, x1, y0, y1, pz):
    """A low U of snow blocks (2 tall, open on one side, never enclosing) with a snowball pile."""
    side = int(rng.integers(4))
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            edge = [y == y0, x == x1, y == y1, x == x0]
            if any(edge) and not edge[side]:
                h = 2 if (x + y) % 3 else 1
                for k in range(h):
                    cv.set(x, y, pz - 1 - k, shade((198, 202, 210), 0.95 - 0.04 * k), 'snowfort')
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    cv.set(cx, cy, pz - 1, (200, 204, 212), 'snowfort')
    cv.set(cx + 1, cy, pz - 1, (194, 198, 208), 'snowfort')
    cv.set(cx, cy, pz - 2, (204, 206, 212), 'snowfort')
    return []


def lantern_ring(cv, rng, x0, x1, y0, y1, pz):
    glow = []
    for (x, y) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        for k in range(3):
            cv.set(x, y, pz - 1 - k, (54, 50, 48), 'lantern')
        cv.set(x, y, pz - 4, (255, 175, 95), 'lantern')
        glow.append((x, y, pz - 4, (255, 175, 95)))
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    cv.box(cx - 1, cx + 1, cy, cy, pz - 1, pz - 1, (110, 84, 60), 'lantern')                  # bench
    return glow


def present_pile(cv, rng, x0, x1, y0, y1, pz):
    wraps = [((168, 46, 48), (204, 180, 96)), ((52, 100, 70), (200, 196, 186)), ((60, 84, 130), (204, 180, 96)),
             ((196, 170, 100), (150, 40, 44)), ((120, 60, 120), (200, 196, 186)), ((200, 196, 186), (52, 100, 70))]
    for k in range(int(rng.integers(3, 6))):
        w, d, h = int(rng.integers(1, 3)), int(rng.integers(1, 3)), int(rng.integers(1, 3))
        x = int(rng.integers(x0, max(x0 + 1, x1 - w)))
        y = int(rng.integers(y0, max(y0 + 1, y1 - d)))
        top = pz
        for xx in range(x, x + w + 1):
            for yy in range(y, y + d + 1):
                c = 0
                while cv.get(xx, yy, top - 1 - c) and c < 6:
                    c += 1
                top = min(top, pz - c)
        body, ribbon = wraps[int(rng.integers(len(wraps)))]
        for xx in range(x, min(x1, x + w) + 1):
            for yy in range(y, min(y1, y + d) + 1):
                for zz in range(top - h, top):
                    rib = (xx == x + w // 2) or (yy == y + d // 2)
                    cv.set(xx, yy, zz, ribbon if rib else body, 'present')
    return []


def snowman_family(cv, rng, x0, x1, y0, y1, pz, scarves):
    glow = []
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    long_x = (x1 - x0) >= (y1 - y0)
    for k, sc in enumerate((1.0 * 0.62, 0.48)):
        off = (-1.4 if k == 0 else 1.6)
        if long_x:
            bx0, bx1 = int(cx + off) - 1, int(cx + off) + 1
            glow += snowman(cv, rng, max(x0, bx0), min(x1, bx1), y0 + 1, y1 - 1, pz, ['beanie', 'earmuffs'][k],
                            'buttons', scarves[k], 'stand', scale=sc)
        else:
            by0, by1 = int(cy + off) - 1, int(cy + off) + 1
            glow += snowman(cv, rng, x0 + 1, x1 - 1, max(y0, by0), min(y1, by1), pz, ['beanie', 'earmuffs'][k],
                            'buttons', scarves[k], 'stand', scale=sc)
    return glow


def build_pads(cv, rng, pads):
    """Build every pad's one-off (pads given with their final box, both halves). Unique combos for snowmen and
    sculptures. Returns (glow sources, records)."""
    glow, recs = [], []
    hats = list(rng.permutation(HATS))
    accs = list(rng.permutation(ACCESSORIES))
    scarves = [SCARVES[i] for i in rng.permutation(len(SCARVES))]
    shapes = list(rng.permutation(ICE_SHAPES))
    poses = ['lean', 'wave', 'stand', 'wave', 'lean', 'stand']
    si = ii = 0
    for p in pads:
        x0, x1, y0, y1 = p['box']
        pz = int(cv.H[(x0 + x1) // 2, (y0 + y1) // 2]) - 1           # pad top (pads are 1 voxel on flat ground)
        before = cv.solid[x0 - 1:x1 + 2, y0 - 1:y1 + 2, :pz + 1].copy()
        kind = p['kind']
        face = (1, 0) if x0 < 256 else (-1, 0)
        if kind == 'snowman':
            hat, acc = hats[si % len(hats)], accs[si % len(accs)]
            sc = scarves[si % len(scarves)]
            g = snowman(cv, rng, x0, x1, y0, y1, pz, hat, acc, sc, poses[si % len(poses)],
                        scale=0.9 + 0.2 * rng.random(), face=face)
            recs.append({'pad': p['box'], 'kind': kind, 'hat': hat, 'accessory': acc, 'scarf': sc})
            si += 1
        elif kind == 'snowman family':
            g = snowman_family(cv, rng, x0, x1, y0, y1, pz, [scarves[(si + 3) % 10], scarves[(si + 5) % 10]])
            recs.append({'pad': p['box'], 'kind': kind})
            si += 1
        elif kind == 'ice sculpture':
            shape = shapes[ii % len(shapes)]
            g = ice_sculpture(cv, rng, x0, x1, y0, y1, pz, shape)
            recs.append({'pad': p['box'], 'kind': kind, 'shape': shape})
            ii += 1
        elif kind == 'sled stack':
            g = sled_stack(cv, rng, x0, x1, y0, y1, pz)
            recs.append({'pad': p['box'], 'kind': kind})
        elif kind == 'snow fort':
            g = snow_fort(cv, rng, x0, x1, y0, y1, pz)
            recs.append({'pad': p['box'], 'kind': kind})
        elif kind in ('lantern ring',):
            g = lantern_ring(cv, rng, x0, x1, y0, y1, pz)
            recs.append({'pad': p['box'], 'kind': kind})
        else:
            g = present_pile(cv, rng, x0, x1, y0, y1, pz)
            recs.append({'pad': p['box'], 'kind': kind})
        # keep only what is face-connected to the pad (no loose hat brims / birds)
        from scipy import ndimage as ndi
        sub = cv.solid[x0 - 1:x1 + 2, y0 - 1:y1 + 2, :pz + 1]
        lab, n = ndi.label(sub, structure=ndi.generate_binary_structure(3, 1))
        keep = np.unique(lab[:, :, pz][sub[:, :, pz]])
        drop = (lab > 0) & ~np.isin(lab, keep) & ~before
        if drop.any():
            sub[drop] = False
            cv.mat[x0 - 1:x1 + 2, y0 - 1:y1 + 2, :pz + 1][drop] = 0
            recs[-1]['pruned'] = int(drop.sum())
        g = [q for q in g if cv.solid[q[0], q[1], q[2]]]
        glow += g
    return glow, recs
