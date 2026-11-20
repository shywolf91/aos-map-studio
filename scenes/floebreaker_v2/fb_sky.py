"""Floating sky decor (opt-in by owner, both versions). Pieces are expected-floating and recorded in W.floating.

Rules: >= 60 voxels from the Babel platform, nothing over a spawn square, >= 10 voxels clear air below (ground z >= 40
under every piece, pieces live in z 3..15), >= 14 from the ship mast, wingspans/curtains big enough to read (>= 13).
Placement uses the decor RNG (non-deterministic; seed saved in build.json).
"""
from __future__ import annotations

import numpy as np

from fb_core import MAT

PLAT = (206, 305, 240, 271)


def far_enough(x, y, rx, ry):
    px0, px1, py0, py1 = PLAT
    dx = max(px0 - (x + rx), (x - rx) - px1, 0); dy = max(py0 - (y + ry), (y - ry) - py1, 0)
    if np.hypot(dx, dy) < 64:
        return False
    for bx in (118, 394):
        if abs(x - bx) < 40 + rx and abs(y - 256) < 40 + ry:
            return False
    if abs(x - 255.5) < 22 + rx and 44 < y < 184:               # ship + mast
        return False
    return True


def _record(W, name, x0, x1, y0, y1, z0, z1):
    sub = W.m[x0:x1 + 1, y0:y1 + 1, z0:z1 + 1]
    W.floating.append({'name': name, 'x': (x0, x1), 'y': (y0, y1), 'z': (z0, z1), 'voxels': int((sub > 0).sum())})


def cloud(W, cx, cy, cz, rx, ry, rz, rng):
    x0, x1, y0, y1 = int(cx - rx - 2), int(cx + rx + 2), int(cy - ry - 2), int(cy + ry + 2)
    xs, ys, zs = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1), np.arange(cz - rz - 1, cz + rz + 2),
                             indexing='ij')
    sol = np.zeros(xs.shape, bool)
    for k in range(int(rng.integers(4, 7))):
        ox, oy = rng.uniform(-rx * .55, rx * .55), rng.uniform(-ry * .5, ry * .5)
        r = rng.uniform(.45, .7)
        sol |= (((xs - cx - ox) / (rx * r)) ** 2 + ((ys - cy - oy) / (ry * r)) ** 2 + ((zs - cz) / (rz * 0.9)) ** 2) <= 1
    sub = W.m[x0:x1 + 1, y0:y1 + 1, cz - rz - 1:cz + rz + 2]
    sub[sol] = MAT['cloud']
    _record(W, 'cloud', x0, x1, y0, y1, cz - rz - 1, cz + rz + 1)


def gull(W, cx, cy, cz, span, rng):
    """A V of two swept wings (>= 13 wide) with a body, 2 thick so it reads."""
    for side in (-1, 1):
        for t in range(0, span // 2 + 1):
            x = int(cx + side * t); y = int(cy + t * 0.55 + (0 if t < 3 else 0.5)); z = int(cz - (0.28 * t if t < 5 else 1.4 - 0.1 * (t - 5)))
            for dz in (0, 1):
                W.pt(x, y, z + dz, 'bird'); W.pt(x, y + 1, z + dz, 'bird')
    W.box(cx - 1, cx + 1, cy - 2, cy + 2, cz, cz + 1, 'bird')
    _record(W, 'gull', cx - span // 2 - 1, cx + span // 2 + 1, cy - 3, cy + int(span * .3) + 3, cz - 3, cz + 3)


def snowflake(W, cx, cy, cz, r):
    """Hexagonal ice crystal, 1-2 thick, with spokes and a bright centre."""
    for k in range(6):
        a = k * np.pi / 3
        for t in range(0, r + 1):
            x = int(round(cx + t * np.cos(a))); y = int(round(cy + t * np.sin(a)))
            W.pt(x, y, cz, 'cloud'); W.pt(x + 1, y, cz, 'cloud'); W.pt(x, y + 1, cz, 'cloud')
            if t in (r // 2, r - 1):
                for s in (-2, 2):
                    bx = int(round(x + s * np.cos(a + np.pi / 2))); by = int(round(y + s * np.sin(a + np.pi / 2)))
                    W.pt(bx, by, cz, 'cloud_s')
    W.box(cx - 1, cx + 1, cy - 1, cy + 1, cz, cz + 1, 'cloud')
    _record(W, 'crystal', cx - r - 2, cx + r + 2, cy - r - 2, cy + r + 2, cz, cz + 1)


def aurora(W, x0, y0, ang, length, zc, h, rng, phase=0.0):
    """Curtain ribbon: wavy 2-thick wall, colours drift green -> teal -> violet along its length."""
    pts = []
    for t in range(length):
        a = ang + 0.35 * np.sin(t / 11.0 + phase)
        x = x0 + t * np.cos(ang) + 5 * np.sin(t / 13.0 + phase) * np.sin(ang)
        y = y0 + t * np.sin(ang) - 5 * np.sin(t / 13.0 + phase) * np.cos(ang)
        pts.append((x, y))
    # skip the ribbon if it would touch any existing piece (each sky piece must stay its own component)
    for t, (x, y) in enumerate(pts[::3]):
        xi, yi = int(x), int(y)
        if 0 <= xi < 512 and 0 <= yi < 512 and (W.m[max(xi - 2, 0):xi + 4, max(yi - 2, 0):yi + 4, 1:17].any()
                                                 or W.keep[max(xi - 6, 0):xi + 7, max(yi - 6, 0):yi + 7].any()):
            return
    xs0 = ys0 = 999; xs1 = ys1 = -1; zlo, zhi = 99, 0
    for t, (x, y) in enumerate(pts):
        hh = int(h * (0.55 + 0.45 * np.clip(np.sin(np.pi * t / (length - 1)), 0, 1) ** 0.8))
        zt = int(zc - hh // 2 - 1 + 2 * np.sin(t / 7.0 + phase))
        c = 'aur_a' if t < length * 0.45 else ('aur_b' if t < length * 0.75 else 'aur_c')
        for dz in range(hh):
            z = zt + dz
            if z < 3:
                continue
            for ox, oy in ((0, 0), (1, 0), (0, 1)):
                xi, yi = int(x) + ox, int(y) + oy
                if 0 <= xi < 512 and 0 <= yi < 512:
                    W.m[xi, yi, z] = MAT[c]
                    xs0, xs1, ys0, ys1 = min(xs0, xi), max(xs1, xi), min(ys0, yi), max(ys1, yi)
                    zlo, zhi = min(zlo, z), max(zhi, z)
    _record(W, 'aurora', xs0, xs1, ys0, ys1, zlo, zhi)


def star(W, x, y, z):
    for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (2, 0), (-2, 0), (0, 2), (0, -2)):
        W.pt(x + dx, y + dy, z, 'star')
        W.pt(x + dx, y + dy, z + 1, 'star')
    _record(W, 'star', x - 2, x + 2, y - 2, y + 2, z, z + 1)


def moon(W, cx, cy, cz, r):
    for x in range(cx - r, cx + r + 1):
        for z in range(cz - r, cz + r + 1):
            if (x - cx) ** 2 + (z - cz) ** 2 <= r * r:
                for y in (cy, cy + 1):
                    W.m[x, y, z] = MAT['moon']
    _record(W, 'moon', cx - r, cx + r, cy, cy + 1, cz - r, cz + r)


def build_sky(W, variant):
    rng = W.drng
    placed = []
    def spot(rx, ry, tries=400):
        for _ in range(tries):
            x = int(rng.integers(30, 482)); y = int(rng.integers(30, 482))
            if far_enough(x, y, rx, ry) and not W.m[max(x - rx - 3, 0):x + rx + 4, max(y - ry - 3, 0):y + ry + 4, 1:18].any() and not W.keep[max(x - rx - 30, 0):x + rx + 31, max(y - ry - 30, 0):y + ry + 31].any() and all(np.hypot(x - a, y - b) > (rx + ry) * 0.9 + ra for a, b, ra in placed):
                placed.append((x, y, max(rx, ry)))
                return x, y
        return None
    if variant == 'day':
        for _ in range(11):
            s = spot(12, 8)
            if s:
                cloud(W, s[0], s[1], int(rng.integers(6, 10)), int(rng.integers(9, 13)), int(rng.integers(6, 9)), 3, rng)
        for _ in range(8):
            s = spot(10, 6)
            if s:
                gull(W, s[0], s[1], int(rng.integers(6, 11)), int(rng.integers(14, 20)), rng)
        for _ in range(7):
            s = spot(9, 9)
            if s:
                snowflake(W, s[0], s[1], int(rng.integers(5, 12)), int(rng.integers(6, 8)))
    else:
        for mx, my in ((60, 70),):
            moon(W, mx, my, 9, 6)
            placed.append((mx, my, 14))
        for i in range(9):
            s = spot(30, 18)
            if s:
                aurora(W, s[0] - 25, s[1], float(rng.uniform(-0.5, 0.5)), int(rng.integers(50, 80)),
                       int(rng.integers(8, 11)), int(rng.integers(8, 11)), rng, phase=float(rng.uniform(0, 6)))
        for _ in range(26):
            s = spot(4, 4)
            if s:
                star(W, s[0], s[1], int(rng.integers(3, 14)))

