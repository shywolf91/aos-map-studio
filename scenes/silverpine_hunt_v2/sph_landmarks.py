"""Hero landmarks for Silverpine Hunt: the werewolf, the wolf-skull gate, the den caverns, the trophy tree and the
frozen waterfall with its ice cave. All are authored symmetric about x = 256 (they sit on the mirror axis).
"""
from __future__ import annotations

import math

import numpy as np

from sph_props import *            # noqa: F401,F403
from sph_props import AIR, hsh
from sph_terrain import PZ


# ================================================================== werewolf

def werewolf(V, cx, cy, g, s=0.9):
    """Rearing werewolf, arms raised out to the sides with claws spread, snarling up toward the platform (+y)."""
    def P(dx, dy, up):
        return (cx + dx * s, cy + dy * s, g - up * s)

    def cap(a, b, r0, r1, mat, squash=(1, 1, 1)):
        V.capsule(P(*a), P(*b), r0 * s, r1 * s, mat, squash=squash)

    def ell(c, r, mat):
        V.ellipsoid(P(*c), (r[0] * s, r[1] * s, r[2] * s), mat)

    for sd in (-1, 1):
        ell((6.5 * sd, 3, 1.1), (2.4, 3.8, 1.5), FUR_DK)                        # paws
        cap((6.5 * sd, 2, 1.5), (7 * sd, -3, 7), 1.6, 2.0, FUR_DK)              # metatarsus
        cap((7 * sd, -3, 7), (6.8 * sd, 2.5, 12), 2.1, 2.9, FUR_DK)             # shin
        cap((6.8 * sd, 2.5, 12), (4.2 * sd, -1, 16), 3.1, 3.8, FUR_DK)          # thigh
    ell((0, -1, 16), (6.0, 4.4, 3.6), FUR_DK)                                   # pelvis
    cap((0, -1, 16.5), (0, 1.5, 25.5), 4.4, 6.6, FUR_DK, squash=(1.3, 0.9, 1))  # V-shaped torso
    for sd in (-1, 1):
        ell((8 * sd, 1, 25.5), (3.6, 3.4, 3.4), FUR_DK)                          # shoulders
        cap((8.5 * sd, 1, 25.5), (14 * sd, 3, 22), 2.7, 2.2, FUR_DK)             # upper arm out
        cap((14 * sd, 3, 22), (16.5 * sd, 7, 26.5), 2.2, 1.8, FUR_DK)            # forearm raised
        ell((17 * sd, 8, 28), (2.0, 2.1, 2.4), FUR)                              # hand
    cap((0, 1.5, 26), (0, 2.2, 30), 4.0, 3.5, FUR_DK)                            # neck
    ell((0, 2.2, 31.5), (3.6, 4.2, 3.5), FUR_DK)                                # head
    cap((0, 4.2, 32.6), (0, 9.6, 35.2), 2.4, 1.4, FUR)                           # upper jaw (snarl, raised)
    cap((0, 4.2, 30.6), (0, 9.0, 31.4), 1.7, 1.0, FUR)                           # lower jaw (dropped)
    cap((0, 5.0, 31.6), (0, 8.8, 33.0), 1.1, 0.7, MAW)                           # open mouth
    for sd in (-1, 1):
        cap((2.6 * sd, 0.2, 34.2), (3.9 * sd, -1.2, 39.5), 1.5, 0.4, FUR_DK)      # ears
        cap((2.7 * sd, 0.9, 35.2), (3.4 * sd, 0.1, 38), 0.6, 0.3, EAR_IN)
    cap((0, -4, 14), (0, -9, 8), 2.4, 2.0, FUR_DK)                               # tail to the ground (support)
    cap((0, -9, 8), (0, -11.5, 2.5), 2.0, 1.7, FUR)
    cap((0, -11.5, 2.5), (0, -8, 0.4), 1.7, 1.3, FUR_TIP)

    def recolor(c, r, src, dst):
        x0, y0, z0 = P(*c)
        R = (r[0] * s, r[1] * s, r[2] * s)
        for x in range(int(x0 - R[0]) - 1, int(x0 + R[0]) + 2):
            for y in range(int(y0 - R[1]) - 1, int(y0 + R[1]) + 2):
                for z in range(int(z0 - R[2]) - 1, int(z0 + R[2]) + 2):
                    if ((x - x0) / R[0]) ** 2 + ((y - y0) / R[1]) ** 2 + ((z - z0) / R[2]) ** 2 <= 1 and \
                            V.get(x, y, z) in src:
                        V.put(x, y, z, dst)
    recolor((0, 5.5, 21.5), (3.4, 3.0, 6.0), (FUR_DK,), FUR_LT)                 # chest blaze
    recolor((0, 8.0, 33.0), (1.6, 2.6, 2.2), (FUR,), FUR_LT)                    # muzzle
    for sd in (-1, 1):
        recolor((8 * sd, -1, 27), (4, 3, 2.5), (FUR_DK,), FUR)                   # lighter shoulder hump
    # claws (hands up-out, feet forward), fangs, nose, eyes
    for sd in (-1, 1):
        for f in (-1.5, -0.5, 0.5, 1.5):
            V.line4(P(17 * sd + f * 0.8, 9.2, 29.5), P(18.5 * sd + f * 1.3, 11.0, 33.0), CLAW)
        for t in (-1, 0, 1):
            V.line4(P(6.5 * sd + t * 1.1, 6.4, 1.2), P(6.5 * sd + t * 1.3, 7.8, 0.3), CLAW)
        V.line4(P(1.1 * sd, 8.6, 33.6), P(1.1 * sd, 8.6, 32.2), FANG)            # upper canines
        V.line4(P(0.9 * sd, 8.4, 31.4), P(0.9 * sd, 8.4, 32.4), FANG)            # lower canines
        V.line4(P(1.4 * sd, 6.4, 33.0), P(1.4 * sd, 6.4, 32.4), FANG)
        for du in (34.0, 34.6):
            V.put(*[int(round(v)) for v in P(1.9 * sd, 5.4, du)], EYE)
        V.put(*[int(round(v)) for v in P(1.0 * sd, 5.8, 35.4)], FUR_DK)        # brow
    V.ellipsoid(P(0, 9.8, 35.6), (0.9, 0.9, 0.9), NOSE)
    # mane spikes up the back of the neck and across the shoulders, spine ridge
    for i in range(16):
        t = i / 15
        a = (-1.0 + 2.0 * t)
        bx, by, bu = 6.0 * math.sin(a), -1.0 - 1.5 * math.cos(a), 27.5 + 3.0 * math.cos(a)
        V.line4(P(bx, by, bu), P(bx * 1.3, by - 2.6, bu + 2.4 + (i % 3) * 0.5), FUR_TIP)
    for i in range(6):
        t = i / 5
        V.line4(P(0, -2.6, 28 + 4 * t), P(0, -5.0 - 0.5 * (i % 2), 29.5 + 4 * t), FUR_TIP)
    for up in range(16, 26, 2):
        V.line4(P(0, -5.0 + (up - 16) * 0.3, up), P(0, -6.8 + (up - 16) * 0.3, up + 1.5), FUR_TIP)
    for sd in (-1, 1):                                                           # elbow + forearm tufts
        V.line4(P(14 * sd, 2, 21.5), P(15.5 * sd, 0, 20), FUR_TIP)
        V.line4(P(15.5 * sd, 4.5, 24), P(17.5 * sd, 3.5, 23), FUR_TIP)


# ================================================================== wolf-skull gate

def wolf_skull(V, cx, ycr, g):
    """Giant wolf skull facing +y. Cranium centre y = ycr; mouth opens at ground level as the den doorway."""
    yb = ycr
    V.ellipsoid((cx, yb, g - 9.5), (12.5, 13, 9.5), BONE)                       # cranium (long, low)
    V.capsule((cx, yb - 10, g - 15), (cx, yb + 6, g - 19.2), 1.4, 1.0, BONE_DK)  # sagittal crest
    V.capsule((cx, yb + 6, g - 9), (cx, yb + 28, g - 7), 7.5, 4.2, BONE)        # snout
    V.capsule((cx, yb + 10, g - 15.5), (cx, yb + 27, g - 11), 1.6, 1.1, BONE)   # nasal bridge
    for sd in (-1, 1):
        V.ellipsoid((cx + 6 * sd, yb + 10, g - 15), (5, 3, 2.2), BONE_DK)       # brow ridges
        V.capsule((cx + 12 * sd, yb + 2, g - 8), (cx + 8 * sd, yb + 14, g - 8), 1.8, 1.4, BONE)   # cheekbones
    # hollow the cranium + snout (inner chamber)
    V.ellipsoid((cx, yb, g - 10), (10.6, 9.6, 7.8), AIR)
    V.capsule((cx, yb + 6, g - 8), (cx, yb + 27, g - 6.5), 5.0, 2.4, AIR)
    # mouth: open from the ground up to 5 high across the snout
    V.box(cx - 6, cx + 6, yb + 4, yb + 31, g - 5, g - 1, AIR)
    # eye sockets (through the shell) with ember eyes deep inside
    for sd in (-1, 1):
        V.ellipsoid((cx + 6 * sd, yb + 11, g - 12), (2.8, 3.2, 2.8), AIR)
        V.put(cx + 6 * sd, yb + 8, g - 12, EYE); V.put(cx + 6 * sd, yb + 8, g - 13, EYE)
        V.put(cx + 6 * sd, yb + 7, g - 12, BONE_DK); V.put(cx + 6 * sd, yb + 7, g - 13, BONE_DK)
        V.put(cx + 6 * sd, yb + 8, g - 11, BONE_DK)
    V.ellipsoid((cx, yb + 27, g - 9.5), (2.0, 2.0, 1.5), AIR)                   # nasal opening
    # lower jaw lying on the ground: rami + low chin bar (1 high, step over)
    for sd in (-1, 1):
        V.capsule((cx + 11 * sd, yb - 4, g - 2), (cx + 6 * sd, yb + 29, g - 1), 1.9, 1.3, BONE)
    V.box(cx - 6, cx + 6, yb + 30, yb + 31, g - 1, g - 1, BONE)
    # teeth: upper row hanging from the snout edge, long canines at the mouth corners, lower row up
    for y in range(yb + 10, yb + 30, 2):
        for sd in (-1, 1):
            V.put(cx + 6 * sd, y, g - 5, FANG); V.put(cx + 6 * sd, y, g - 4, FANG if y % 4 == 0 else AIR)
            V.put(cx + 6 * sd, y + 1, g - 2, FANG)
    for sd in (-1, 1):
        V.box(cx + 6 * sd, cx + 6 * sd, yb + 28, yb + 29, g - 6, g - 2, FANG)
        V.box(cx + 5 * sd, cx + 5 * sd, yb + 29, yb + 29, g - 4, g - 3, FANG)
        V.put(cx + 6 * sd, yb + 29, g - 2, BLOOD)
        V.put(cx + 5 * sd, yb + 29, g - 3, BLOOD)
    # sutures + snow patches on top of the cranium
    for x in range(cx - 10, cx + 11):
        y = yb + int(round(1.5 * math.sin(x * 0.7)))
        z = V.ground(x, y)
        if V.get(x, y, z) == BONE:
            V.put(x, y, z, BONE_DK)
    for x in range(cx - 11, cx + 12):
        for y in range(yb - 10, yb + 26):
            z = V.ground(x, y)
            if V.get(x, y, z) == BONE and z < g - 12 and hsh(x // 2, y // 2, 33) < 0.35:
                V.put_air(x, y, z - 1, SNOWCAP)
    # weathering: darker stained bone toward the ground and in the sockets, moss at the base
    for x in range(cx - 14, cx + 15):
        for y in range(yb - 14, yb + 36):
            for z in range(g - 22, g):
                v = V.get(x, y, z)
                if v == BONE and (z > g - 4 or hsh(x // 2, y // 3, z // 2, 61) < 0.18):
                    V.put(x, y, z, BONE_DK)
                elif v == BONE_DK and z > g - 2 and hsh(x, y, 62) < 0.35:
                    V.put(x, y, z, MOSS)
    # candles + bones at the doorway
    for sd in (-1, 1):
        V.put(cx + 9 * sd, yb + 31, g - 1, CANDLE)
        V.put(cx + 10 * sd, yb + 33, g - 1, BONE); V.put(cx + 10 * sd, yb + 34, g - 1, BONE)
    V.reserve(cx - 16, cx + 16, yb - 14, yb + 36)


# ================================================================== den caverns

def carve_den(V, F):
    """Cave-and-ruin den under the platform: nest hall, open nest pit with a twin stair, north passage under the
    crag, south passage up into the skull, side alcoves. Floors are CAVE_FLOOR, walls CAVE_ROCK."""
    cx, cy = 256, 256
    fz = PZ + 10                       # nest floor top z
    air = np.zeros((512, 512, 64), bool)
    X, Y = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    # nest hall
    d = np.hypot((X - cx) / 32.0, (Y - cy) / 21.0)
    for z in range(PZ + 3, fz):
        k = d < 1.0 - 0.22 * np.clip((PZ + 6 - z) / 3.0, 0, 1)          # domed ceiling
        air[:, :, z] |= k
    # side alcoves
    for sx in (-1, 1):
        dd = np.hypot((X - (cx + 34 * sx)) / 9.0, (Y - cy) / 6.5)
        for z in range(PZ + 6, fz):
            air[:, :, z] |= dd < 1
    # north passage: floor rises from fz at y 236 to PZ at y 200, flat to the crag's north face
    for y in range(176, 240):
        if y >= 236:
            f = fz
        elif y > 200:
            f = PZ + int(round((y - 200) / 36 * 10))
        else:
            f = PZ
        w = 4 if y > 200 else 5
        for x in range(cx - w, cx + w + 1):
            air[x, y, f - 4:f] = True
    # south passage: flat to y 300, then rising to PZ inside the skull at y 334
    for y in range(272, 336):
        if y <= 300:
            f = fz
        else:
            f = fz - int(round((y - 300) / 34 * 10))
        for x in range(cx - 5, cx + 6):
            air[x, y, f - 4:f] = True
    # nest pit open to the sky, r 7
    dp = np.hypot(X - cx, Y - cy)
    for z in range(PZ - 2, fz):
        air[:, :, z] |= dp < 7.2
    # carve, then dress
    sol = V.m > 0
    newair = air & sol
    V.m[newair] = AIR
    # floors / walls
    below = np.zeros_like(air); below[:, :, :-1] = air[:, :, :-1] & (V.m[:, :, 1:] > 0)
    xs, ys, zs = np.nonzero(below)
    V.m[xs, ys, zs + 1] = CAVE_FLOOR
    nb = np.zeros_like(air)
    for ax in (0, 1, 2):
        for sh in (1, -1):
            nb |= np.roll(air, sh, axis=ax)
    wall = nb & (V.m > 0) & (V.m != CAVE_FLOOR) & ~below
    xs, ys, zs = np.nonzero(wall)
    keep = zs > PZ                                       # leave the surface skin (snow / earth) as it is
    V.m[xs[keep], ys[keep], zs[keep]] = CAVE_ROCK
    # twin stair in the pit: two flights from the north rim descend around west / east to the south landing
    for sd in (-1, 1):
        for k in range(1, 11):
            a = -math.pi / 2 + sd * math.pi * k / 10.5
            for rr in (5.4, 6.2, 7.0):
                x = int(round(cx + rr * math.cos(a)))
                y = int(round(cy + rr * math.sin(a)))
                for z in (PZ + k, PZ + k + 1):
                    if z < fz:
                        V.put(x, y, z, STONE_DK)
    # nest: straw / pelts / bones ring on the hall floor north of the pit
    rng = np.random.default_rng(77)
    for a in range(0, 360, 5):
        t = math.radians(a)
        for rr in (4, 5, 6):
            x = int(round(cx + rr * math.cos(t))); y = int(round(cy - 13 + rr * 0.7 * math.sin(t)))
            if V.get(x, y, fz - 1) == AIR and V.get(x, y, fz) == CAVE_FLOOR:
                V.put(x, y, fz - 1, [STRAW, PELT, STRAW, PELT_GREY, BONE][int(hsh(x, y, 1) * 5)])
                if rr == 6 and hsh(x, y, 2) < 0.3:
                    V.put(x, y, fz - 2, STRAW)
    for (x, y) in ((cx - 2, cy - 13), (cx + 1, cy - 12), (cx - 1, cy - 14)):
        V.put(x, y, fz, PELT_RED)
    bones(V, cx - 14, cy, lambda a, b: fz, rng, n=10, r=5)
    bones(V, cx - 6, cy + 14, lambda a, b: fz, rng, n=8, r=4)
    animal_skull(V, cx - 18, cy - 6, fz, face=(1, 0), antler=True)
    animal_skull(V, cx - 9, cy + 15, fz, face=(0, -1))
    # gnawed hunter: skull, ribs, rifle, dropped lantern
    V.put(cx - 22, cy + 6, fz - 1, BONE); V.put(cx - 22, cy + 7, fz - 1, BONE_DK)
    V.box(cx - 24, cx - 23, cy + 5, cy + 8, fz - 1, fz - 1, COAT)
    V.line4((cx - 26, cy + 2, fz - 1), (cx - 26, cy + 9, fz - 1), IRON_DK)
    V.put(cx - 20, cy + 9, fz - 1, LANTERN)
    # eyes in the alcoves + claw marks on the hall walls
    for (ex, ey, ez) in ((cx - 40, cy - 2, fz - 3), (cx - 40, cy + 2, fz - 4), (cx - 31, cy - 18, fz - 3)):
        if V.get(ex, ey, ez) == CAVE_ROCK:
            V.put(ex, ey, ez, EYE)
            V.put(ex, ey + 1, ez, EYE) if V.get(ex, ey + 1, ez) == CAVE_ROCK else None
    for x in range(cx - 33, cx - 2):
        for y in range(cy - 22, cy + 23):
            for z in range(PZ + 4, fz - 1):
                if V.get(x, y, z) == CAVE_ROCK and hsh(x, y + z, 41) < 0.05 and (y + x + z) % 3 == 0:
                    V.put(x, y, z, BLOOD)
    # candles + skull niches along the south passage
    for y in range(280, 300, 6):
        for sd in (-1,):
            x = cx + 6 * sd
            V.put(x, y, fz - 2, AIR); V.put(x, y, fz - 3, AIR)
            V.put(x, y, fz - 1, BONE); V.put(x, y, fz - 2, CANDLE)
    return {'floor_z': fz}


# ================================================================== trophy tree

def trophy_tree(V, x, y, g, rng):
    """Giant dead oak hung with the werewolf's trophies: cages, coats and hats, lanterns, antler skulls, pelts."""
    V.reserve(x - 16, x + 16, y - 14, y + 14)
    H = 22
    for k in range(H):
        r = 2.4 - 1.1 * (k / H)
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                if dx * dx + dy * dy <= r * r + 0.4 + 0.6 * hsh(dx, dy, k // 3):
                    V.put(x + dx, y + dy, g - 1 - k, DEADWOOD if hsh(x + dx, y + dy, k) < 0.8 else BARK_DK)
    for a in range(0, 360, 45):                                              # root flare
        t = math.radians(a + 11)
        V.line4((x + 2 * math.cos(t), y + 2 * math.sin(t), g - 2), (x + 6 * math.cos(t), y + 6 * math.sin(t), g - 1),
                BARK_DK)
    hangs = []
    limbs = [(-60, 12, 13, 4), (-150, 14, 12, 5), (150, 13, 12, 3), (60, 15, 11, 5), (-110, 18, 9, 6),
             (110, 17, 10, 6), (-30, 19, 8, 7), (30, 20, 8, 7)]                # (angle deg, height, reach, rise)
    for (ad, hh, reach, rise) in limbs:
        t = math.radians(ad + 90)                                            # 0 deg = +y (south)
        ex, ey = x + reach * math.cos(t), y + reach * math.sin(t)
        p = V.line4((x, y, g - 1 - hh), (ex, ey, g - 1 - hh - rise), DEADWOOD, thick=0)
        V.line4((x, y, g - 2 - hh), ((x + ex) / 2, (y + ey) / 2, g - 2 - hh - rise // 2), DEADWOOD)
        # twigs at the tip
        tx, ty, tz = p[-1]
        for j in range(3):
            aa = t + (j - 1) * 0.7
            V.line4((tx, ty, tz), (tx + 3 * math.cos(aa), ty + 3 * math.sin(aa), tz - 2 - j % 2), BARK_DK)
        for i in range(len(p) * 2 // 5, len(p), 4):
            hangs.append(p[i])
    kinds = ['cage', 'coat', 'lantern', 'skull', 'pelt', 'coat', 'cage', 'lantern', 'bones', 'skull', 'pelt',
             'lantern', 'coat', 'bones']
    used = set()
    for i, (hx, hy, hz) in enumerate(hangs):
        key = (hx // 3, hy // 3)
        if key in used:
            continue
        used.add(key)
        kind = kinds[i % len(kinds)]
        drop = 2 + int(hsh(hx, hy, 3) * 3)
        for k in range(1, drop + 1):
            V.put_air(hx, hy, hz + k, ROPE if kind != 'cage' else IRON_DK)
        zb = hz + drop + 1
        if g - zb < 5:                                                        # keep head room under hangings
            continue
        if kind == 'cage':
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx or dy:
                        if (dx + dy) % 2 or (dx and dy):
                            V.box(hx + dx, hx + dx, hy + dy, hy + dy, zb, zb + 3, IRON_DK)
            V.box(hx - 1, hx + 1, hy - 1, hy + 1, zb, zb, IRON_DK)
            V.box(hx - 1, hx + 1, hy - 1, hy + 1, zb + 3, zb + 3, IRON_DK)
            V.put(hx, hy, zb + 2, BONE); V.put(hx, hy, zb + 1, BONE_DK)
        elif kind == 'coat':
            V.box(hx - 1, hx + 1, hy, hy, zb + 1, zb + 3, COAT)
            V.put(hx, hy, zb, BONE)
            V.box(hx - 1, hx + 1, hy, hy, zb - 1, zb - 1, COAT); V.put(hx, hy, zb - 2, COAT)   # hat
            V.put(hx, hy, zb + 4, COAT) if hsh(hx, hy) < 0.5 else None
        elif kind == 'lantern':
            V.put(hx, hy, zb, LANTERN)
        elif kind == 'skull':
            V.box(hx - 1, hx + 1, hy, hy, zb, zb + 1, BONE)
            V.put(hx - 1, hy, zb, MAW); V.put(hx + 1, hy, zb, MAW)
            antlers(V, hx, hy, zb - 1, along_x=True, size=2)
        elif kind == 'pelt':
            pelt_patch(V, hx, hy, zb, 2, 4, along_x=True, mat=[PELT, PELT_GREY, PELT_RED][i % 3])
        else:
            V.put(hx, hy, zb, BONE); V.put(hx, hy, zb + 1, BONE_DK); V.put(hx, hy, zb + 2, BONE)
    # crows on the limb tips, rags, a bone heap + candles at the foot
    for (ad, hh, reach, rise) in limbs[::2]:
        t = math.radians(ad + 90)
        V.put_air(int(round(x + (reach - 2) * math.cos(t))), int(round(y + (reach - 2) * math.sin(t))),
                  g - 2 - hh - rise + 1, CROW)
    bones(V, x, y + 5, lambda a, b: V.ground(a, b), rng, n=14, r=6)
    for a in range(0, 360, 40):
        t = math.radians(a)
        V.put_air(int(round(x + 7 * math.cos(t))), int(round(y + 7 * math.sin(t))),
                  V.ground(int(round(x + 7 * math.cos(t))), int(round(y + 7 * math.sin(t)))) - 1, CANDLE)


# ================================================================== frozen waterfall + ice cave

def frozen_falls(V, x0, x1, ice_z, rng):
    """Ice cascade draped on the cliff north of the lake, a plunge mound, icicle fringe, and an ice cave behind."""
    cxm = (x0 + x1) / 2
    cols = [(cxm + o, w) for o, w in ((-15, 3.5), (-9, 4.5), (-3, 3.0), (3, 3.0), (9, 4.5), (15, 3.5))]
    faces = {}
    for x in range(x0 - 2, x1 + 3):
        prof = sum(math.exp(-((x - c) / w) ** 2) for c, w in cols)
        edge = min(x - x0, x1 - x) / 4.0
        for z in range(10, ice_z):
            # cliff face: first air cell scanning south from deep inside the cliff
            yf = None
            if V.get(x, 20, z) != AIR:
                for y in range(20, 90):
                    if V.get(x, y, z) == AIR:
                        yf = y
                        break
            if yf is None:
                continue
            faces[(x, z)] = yf
            if V.get(x, yf - 1, z - 1) == AIR and z > 12:
                pass
            wob = 0.65 + 0.35 * math.sin(z * 0.37 + x * 0.9) + 0.15 * math.sin(z * 1.3 + x * 0.4)
            t = 1 + int(round(5.0 * prof * wob * min(1, max(edge, 0.25))))
            t += int(max(0, (z - (ice_z - 9))) * 0.7)                       # spreading at the foot
            if z < 14:                                                       # frozen brow at the lip
                t += 2
            for k in range(t):
                front = k >= t - 1
                mat = (ICE_LT if prof > 0.55 else ICE) if front else (ICE if prof > 0.35 else ICE_DK)
                if prof < 0.25:
                    mat = ICE_DK
                V.put(x, yf + k, z, mat)
            if z < 15 and hsh(x, z, 9) < 0.5:                               # icicles off the brow
                for k in range(1 + int(hsh(x, z, 10) * 4)):
                    V.put_air(x, yf + t, z + k, ICICLE)
    # plunge mound on the lake
    yb = int(np.median([faces[(x, ice_z - 1)] for x in range(x0, x1) if (x, ice_z - 1) in faces]) or 56)
    V.ellipsoid(((x0 + x1) / 2, yb + 3, ice_z), (22, 8, 3.6), ICE)
    V.ellipsoid(((x0 + x1) / 2, yb + 2, ice_z - 1), (14, 5, 2.4), ICE_LT)
    # ice cave behind the falls: entrance at the west foot, a domed chamber inside the cliff
    cz = ice_z
    V.ellipsoid((cxm, 34, cz - 5.5), (15, 9, 5.0), AIR)
    for y in range(34, yb + 4):
        for x in range(x0 - 8, x0 - 2):
            for z in range(cz - 4, cz):
                V.put(x, y, z, AIR)
    for x in range(x0 - 8, int(cxm)):
        for y in range(36, 42):
            for z in range(cz - 4, cz):
                V.put(x, y, z, AIR)
    # floor + crystals + silver veins + a frozen hunter
    for x in range(x0 - 10, x1 + 10):
        for y in range(20, yb + 6):
            for z in range(cz - 12, cz + 1):
                if V.get(x, y, z) != AIR and V.get(x, y, z - 1) == AIR and z == cz and \
                        V.get(x, y, z) not in (ICE, ICE_LT, ICE_DK):
                    V.put(x, y, z, ICE_DK)
    for (dx, dy, h) in ((-9, -3, 4), (-6, 4, 3), (5, -5, 5), (9, 3, 3), (0, -7, 6), (-12, 1, 2), (12, -1, 2)):
        px, py = int(cxm + dx), 34 + dy
        for k in range(h):
            V.put(px, py, cz - 1 - k, MOONGLOW if k < h - 1 else ICE_LT)
        V.put(px + 1, py, cz - 1, ICE_LT)
    for x in range(int(cxm) - 16, int(cxm) + 17):
        for y in range(24, 46):
            for z in range(cz - 11, cz):
                if V.get(x, y, z) not in (AIR, 255) and V.get(x, y, z) not in (MOONGLOW, ICE_LT) and \
                        hsh(x, y, z, 51) < 0.07:
                    nb_air = any(V.get(x + a, y + b, z + c) == AIR for a, b, c in
                                 ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)))
                    if nb_air:
                        V.put(x, y, z, ORE)
    hx, hy = int(cxm) - 3, 30
    V.box(hx, hx + 1, hy, hy + 3, cz - 1, cz - 1, COAT)
    V.put(hx, hy - 1, cz - 1, BONE)
    V.put(hx + 3, hy + 1, cz - 1, LANTERN)
    V.line4((hx - 2, hy + 4, cz - 1), (hx + 3, hy + 5, cz - 1), IRON_DK)
    return {'yb': yb}
