"""The two colossal skeletal hands, placed after mirroring (cosmetic asymmetry, both centred on x = 256 so
neither team is closer). Built from capsule sweeps (radius >= 0.9, face-connected), rooted inside the terrain.

* North: a hand reaching for the sky from the burial mound, palm toward the cathedral, ring finger snapped.
* South: a hand clawing out of the crater, palm down, fingers dug into the crater's north lip, with the crown
  of its skull breaking the soil behind it.
"""
from __future__ import annotations

import math

import numpy as np

from gf_core import hash3
from gf_props import BONE, BONE_DK, SOCKET, EARTH_DK, CRACK_GLOW, SOIL, DIRT, GRAVE, GRAVE_DK, STONE_DK, MUD
from gf_terrain import SPEC


def _chain(V, base, dirs, lengths, radii, mat=BONE, joint=BONE_DK, stop=None):
    """Phalanx chain from base along successive direction vectors. Returns the joint points."""
    p = np.array(base, float)
    pts = [p.copy()]
    for i, (d, L) in enumerate(zip(dirs, lengths)):
        if stop is not None and i >= stop:
            break
        d = np.array(d, float); d /= np.linalg.norm(d)
        q = p + d * L
        V.sweep([p, q], [radii[i], radii[i + 1]], mat)
        V.ball(q, radii[i + 1] + 0.35, joint)
        pts.append(q.copy())
        p = q
    return pts


def _bbox_of_change(before, after):
    diff = np.nonzero(before != after)
    return [int(diff[0].min()), int(diff[0].max()), int(diff[1].min()), int(diff[1].max()),
            int(diff[2].min()), int(diff[2].max())]


def hand_reaching(V):
    cx, cy = SPEC['hand_up']
    g = V.ground(cx, cy)                         # mound top (~34)
    # ground dressing first (so nothing lands on the bones)
    # the snapped fragment lies on the mound to the south-west
    fx, fy = cx - 14, cy + 16
    gf = V.ground(fx, fy)
    V.sweep([(fx, fy, gf - 0.6), (fx + 4.5, fy + 1.5, gf - 0.6), (fx + 7.5, fy + 0.5, gf - 0.4)],
            [1.25, 1.1, 0.95], BONE)
    V.ball((fx + 4.5, fy + 1.5, gf - 0.6), 1.5, BONE_DK)
    # disturbed earth and ghost-lit cracks around the base
    for x in range(cx - 13, cx + 14):
        for y in range(cy - 13, cy + 14):
            d = math.hypot(x - cx, y - cy - 1)
            gz = V.ground(x, y)
            if d < 11 and V.m[x, y, gz] in (SOIL, DIRT, MUD):
                V.m[x, y, gz] = EARTH_DK
    for a in range(0, 360, 40):
        r0 = 6
        for r in range(r0, 16):
            ang = math.radians(a + 9 * math.sin(r * 0.9 + a))
            x = int(round(cx + math.cos(ang) * r)); y = int(round(cy + 1 + math.sin(ang) * r))
            gz = V.ground(x, y)
            if V.m[x, y, gz] in (SOIL, DIRT, EARTH_DK, MUD):
                V.m[x, y, gz] = CRACK_GLOW
    # gravestones knocked flat by the eruption
    for (dx, dy, along) in ((-16, -6, True), (12, -10, False), (15, 9, True), (-10, 12, False), (2, -16, True)):
        x, y = cx + dx, cy + dy
        gz = V.ground(x, y)
        if along:
            V.box(x, x + 3, y, y + 2, gz - 1, gz - 1, GRAVE)
        else:
            V.box(x, x + 2, y, y + 3, gz - 1, gz - 1, GRAVE_DK)
    wz = float(max(g - 15, 22))                  # fingertips must stay below the sky top (z >= 1)
    wrist = np.array([cx + 0.5, cy + 5.5, wz])
    # radius and ulna, rooted deep in the mound, twisting slightly as they rise
    mid = (g + wz) / 2
    V.sweep([(cx - 3.5, cy - 2.0, g + 9), (cx - 3.0, cy + 1.5, mid + 1), (cx - 2.0, cy + 4.0, wz + 2)],
            [2.7, 2.4, 2.1], BONE)
    V.sweep([(cx + 4.0, cy - 1.0, g + 9), (cx + 3.5, cy + 2.0, mid), (cx + 2.5, cy + 4.5, wz + 2)],
            [2.5, 2.2, 1.9], BONE)
    V.ball((cx - 3.0, cy + 1.5, g - 1), 3.0, BONE_DK)     # where the bones break the soil
    V.ball((cx + 3.5, cy + 2.0, g - 1), 2.8, BONE_DK)
    # carpals
    for (dx, dy, dz, r) in ((-2.5, 0, 0, 1.9), (0, 0.5, -0.5, 2.0), (2.5, 0, 0, 1.9), (-1.2, 1.2, -2.2, 1.7),
                            (1.4, 1.0, -2.2, 1.7), (0, -0.8, 1.5, 1.8)):
        V.ball(wrist + (dx, dy, dz), r, BONE)
    # metacarpals fanning to the knuckles (palm cups toward +y, i.e. toward the cathedral)
    fingers = [  # knuckle offset from wrist, phalanx dirs, lengths
        ((-9.0, 2.0, -6.5), [(-0.45, 0.25, -1), (-0.25, 0.7, -1), (0.0, 1.0, -0.6)], [4.5, 3.5, 2.6]),   # little
        ((-4.5, 3.0, -8.5), [(-0.25, 0.2, -1), (-0.1, 0.6, -1), (0.1, 1.0, -0.5)], [5.5, 4.0, 3.0]),    # ring
        ((0.5, 3.5, -9.5), [(0.0, 0.15, -1), (0.05, 0.55, -1), (0.0, 1.0, -0.4)], [6.0, 4.5, 3.0]),     # middle
        ((5.5, 3.0, -8.5), [(0.3, 0.1, -1), (0.35, 0.5, -1), (0.2, 1.0, -0.5)], [5.5, 4.0, 2.8]),      # index
    ]
    snapped = None
    for i, (off, dirs, lens) in enumerate(fingers):
        k = wrist + off
        V.sweep([wrist + (off[0] * 0.25, 0, -1.5), k], [1.5, 1.35], BONE)
        V.ball(k, 1.8, BONE_DK)
        stop = 1 if i == 1 else None                      # the ring finger is snapped after its first phalanx
        pts = _chain(V, k, dirs, lens, [1.35, 1.2, 1.05, 0.95], stop=stop)
        if i == 1:
            snapped = (pts[-1], dirs, lens)
    # thumb: out to the side and up
    tb = wrist + (6.0, 0.0, -1.0)
    V.sweep([wrist + (2.0, 0, 0), tb], [1.6, 1.45], BONE)
    V.ball(tb, 1.8, BONE_DK)
    _chain(V, tb, [(1, 0.4, -0.9), (0.4, 0.8, -1)], [4.5, 3.5], [1.4, 1.2, 1.0])
    return snapped


def hand_clawing(V):
    cx, cy = SPEC['hand_claw']
    g = V.ground(cx, cy)                          # crater floor
    wrist = np.array([cx + 0.5, cy - 6.0, g - 20.0])
    # forearm bursting steeply up out of the crater floor toward the north
    V.sweep([(cx - 3.5, cy + 12.0, g + 6), (cx - 3.0, cy + 4.0, g - 7), (cx - 2.0, cy - 4.0, g - 18)],
            [2.9, 2.6, 2.2], BONE)
    V.sweep([(cx + 4.0, cy + 13.0, g + 6), (cx + 3.5, cy + 5.0, g - 6), (cx + 2.5, cy - 3.5, g - 18)],
            [2.7, 2.4, 2.0], BONE)
    V.ball((cx - 3.0, cy + 8.5, g - 1), 3.3, BONE_DK)
    V.ball((cx + 3.5, cy + 9.5, g - 1), 3.1, BONE_DK)
    for (dx, dy, dz, r) in ((-2.5, 0, 0, 2.0), (0, -0.5, -0.8, 2.1), (2.5, 0, 0, 2.0), (-1.2, -2.0, -0.6, 1.8),
                            (1.4, -2.0, -0.6, 1.8)):
        V.ball(wrist + (dx, dy, dz), r, BONE)
    # palm down, knuckles arched high, long fingers reaching over the crater lip and digging into the ground
    fingers = [
        ((-8.5, -7.0, 0.5), [(-0.35, -1, -0.05), (-0.25, -1, 0.7), (-0.1, -0.4, 1)], [6.5, 7.0, 8.0]),
        ((-3.5, -9.0, -0.5), [(-0.12, -1, -0.1), (-0.1, -1, 0.65), (0.0, -0.35, 1)], [7.5, 7.5, 8.5]),
        ((2.0, -9.5, -0.5), [(0.08, -1, -0.12), (0.08, -1, 0.6), (0.05, -0.3, 1)], [8.0, 8.0, 9.0]),
        ((7.5, -7.5, 0.5), [(0.4, -1, -0.05), (0.3, -1, 0.7), (0.1, -0.4, 1)], [6.5, 7.0, 8.0]),
    ]
    for (off, dirs, lens) in fingers:
        k = wrist + off
        V.sweep([wrist + (off[0] * 0.3, -1.5, 0), k], [1.6, 1.45], BONE)
        V.ball(k, 1.95, BONE_DK)
        pts = _chain(V, k, dirs, lens, [1.45, 1.3, 1.15, 1.0])
        # drive the tip into the ground below it so the finger is rooted
        tip = pts[-1]
        gz = V.ground(int(tip[0]), int(tip[1]))
        V.sweep([tip, (tip[0], tip[1] - 0.5, gz + 2.0)], [1.0, 1.0], BONE)
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                x, y = int(tip[0]) + dx, int(tip[1]) + dy
                gg = V.ground(x, y)
                if V.m[x, y, gg] in (SOIL, DIRT, MUD):
                    V.m[x, y, gg] = EARTH_DK
                if abs(dx) + abs(dy) == 3 and V.m[x, y, gg - 1] == 0:
                    V.m[x, y, gg - 1] = EARTH_DK               # soil heaped by the claw
    # thumb hooked into the ground on the east side
    tb = wrist + (7.5, -2.0, 1.5)
    V.sweep([wrist + (2.0, -1.0, 0), tb], [1.7, 1.5], BONE)
    V.ball(tb, 1.9, BONE_DK)
    pts = _chain(V, tb, [(1, -0.4, 0.4), (0.3, -0.6, 1)], [6.0, 8.0], [1.45, 1.25, 1.05])
    tip = pts[-1]
    gz = V.ground(int(tip[0]), int(tip[1]))
    V.sweep([tip, (tip[0], tip[1], gz + 2.0)], [1.0, 1.0], BONE)
    # the crown of its skull breaking the crater floor behind the arm
    sx, sy = cx, cy + 17
    gs = V.ground(sx, sy)
    for x in range(sx - 12, sx + 13):
        for y in range(sy - 11, sy + 12):
            for k in range(-3, 9):
                d = ((x + 0.5 - sx) / 11.5) ** 2 + ((y + 0.5 - sy) / 10.5) ** 2 + ((k + 2.5) / 9.5) ** 2
                if d <= 1.0:
                    V.put(x, y, gs - k, BONE)
    # brow ridge and eye sockets just above the soil, facing north
    for side in (-1, 1):
        ex = sx + side * 5
        for x in range(ex - 2, ex + 3):
            for k in range(0, 3):
                if ((x - ex) / 2.4) ** 2 + ((k - 0.8) / 1.6) ** 2 <= 1:
                    for y in range(sy - 11, sy - 6):
                        if V.get(x, y, gs - k) == BONE:
                            V.put(x, y, gs - k, 0)
                    V.put(x, sy - 6, gs - k, SOCKET)
    # suture cracks on the crown
    for (a, b) in (((sx, sy - 8), (sx + 1, sy + 8)), ((sx - 9, sy + 1), (sx + 9, sy))):
        n = 40
        for i in range(n + 1):
            x = int(round(a[0] + (b[0] - a[0]) * i / n)); y = int(round(a[1] + (b[1] - a[1]) * i / n))
            z = V.ground(x, y)
            if V.m[x, y, z] == BONE:
                V.m[x, y, z] = BONE_DK
    # glowing fissures across the crater floor
    for a in range(10, 360, 30):
        for r in range(8, 22):
            ang = math.radians(a + 12 * math.sin(r * 0.7 + a * 0.1))
            x = int(round(cx + math.cos(ang) * r)); y = int(round(cy + math.sin(ang) * r))
            gz = V.ground(x, y)
            if V.m[x, y, gz] in (SOIL, DIRT, EARTH_DK, MUD):
                V.m[x, y, gz] = CRACK_GLOW


def hands(V):
    before = V.m.copy()
    hand_reaching(V)
    b1 = _bbox_of_change(before, V.m)
    mid = V.m.copy()
    hand_clawing(V)
    b2 = _bbox_of_change(mid, V.m)
    return [{'name': 'hand_reaching', 'bbox': b1}, {'name': 'hand_clawing', 'bbox': b2}]
