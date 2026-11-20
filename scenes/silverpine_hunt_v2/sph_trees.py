"""Vegetation for Silverpine Hunt: spruces, Scots ('silver') pines, dead snags, saplings, birches.

Every tree gets its own height, girth, tier rhythm, edge jag and a two-palette blend (FOL0..7, neighbours in the
list are similar hues so the blend is smooth), plus three distinct random details from DETAILS.
All parts are face-connected to the trunk.
"""
from __future__ import annotations

import math

import numpy as np

from sph_props import (AIR, BARK, BARK_DK, BIRCH, BONE, CANDLE, CLAW_BARK, CONE, CROW, DEADWOOD, FOLS, FROST,
                       ICICLE, IRON_DK, LANTERN, MOSS, RAG_RED, ROPE, RUST, SCOTS_BARK, SNOWCAP, STRAW, hsh)

DETAILS = ('snowcap', 'icicles', 'lantern', 'ribbon', 'claws', 'nest', 'deadbranch', 'charm', 'moss', 'snowcap',
           'icicles')


def pick_details(rng, allow=DETAILS, n=3):
    idx = rng.choice(len(allow), size=min(n, len(allow)), replace=False)
    return {allow[i] for i in idx}


def _jag(rng):
    ph = rng.random(4) * 6.283
    k1, k2 = int(rng.integers(4, 7)), int(rng.integers(8, 12))
    a1, a2 = 0.12 + 0.1 * rng.random(), 0.06 + 0.08 * rng.random()
    return lambda th: 1 + a1 * np.sin(k1 * th + ph[0]) + a2 * np.sin(k2 * th + ph[1])


def _trunk(V, x, y, g, h, w, mat, claws=False, rng=None):
    for k in range(h):
        for dx in range(w):
            for dy in range(w):
                m = mat
                if claws and 3 <= k <= 8 and dx == 0 and (k + dy) % 3 == 0:
                    m = CLAW_BARK
                V.put(x + dx, y + dy, g - 1 - k, m)
    # root flare
    if w >= 2:
        for (dx, dy) in ((-1, 0), (w, 1), (0, w), (1, -1), (-1, w - 1), (w, 0)):
            if rng is None or rng.random() < 0.6:
                V.put(x + dx, y + dy, g - 1, BARK_DK)


def spruce(V, x, y, g, rng, h=None, pal=None, clear=None, details=None):
    """Layered conical spruce. clear = height of the lowest branches (>= 4: walk under)."""
    h = h or int(rng.integers(13, 30))
    pal = int(rng.integers(0, 8)) if pal is None else pal
    pal2 = (pal + (1 if rng.random() < 0.5 else -1)) % 8
    fa, fb = FOLS[pal], FOLS[pal2]
    clear = clear if clear is not None else int(rng.choice([2, 3, 4, 4, 5]))
    details = details if details is not None else pick_details(rng)
    w = 2 if h >= 20 else 1
    R0 = 0.2 * h + 1.4 + rng.random() * 1.0
    period = int(rng.integers(2, 4))
    jag = _jag(rng)
    cx, cy = x + (w - 1) / 2.0, y + (w - 1) / 2.0
    _trunk(V, x, y, g, h - 1, w, BARK, claws='claws' in details, rng=rng)
    tips = []
    tier_tops = []
    span = h - clear
    for k in range(clear, h + 1):
        f = (k - clear) / max(span, 1)
        phase = ((k - clear) % period) / period
        r = R0 * (1 - f) ** 1.05 * (1 - 0.32 * phase) + 0.45
        z = g - 1 - k
        if V.get(x, y, z) == AIR:
            V.put(x, y, z, fb)
        ri = int(math.ceil(r + 1))
        for dx in range(-ri, ri + w):
            for dy in range(-ri, ri + w):
                px, py = x + dx, y + dy
                ddx, ddy = px - cx, py - cy
                d = math.hypot(ddx, ddy)
                th = math.atan2(ddy, ddx)
                lim = r * jag(th) + (hsh(px, py, z) - 0.5) * 0.5
                if d <= lim:
                    outer = d > lim - 1.2
                    mat = fb if (f > 0.55 or (outer and hsh(px, py, z, 3) < 0.6)) else fa
                    if V.get(px, py, z) == AIR:
                        V.put(px, py, z, mat)
                    if outer and phase == 0:
                        tips.append((px, py, z))
                    if phase == period - 1 or k == h:
                        tier_tops.append((px, py, z, d / max(lim, 0.1)))
    V.put(x, y, g - 2 - h, fb)
    V.put(x, y, g - 3 - h, fb)
    _decorate(V, x, y, g, h, rng, details, tips, tier_tops, w)
    return {'r': R0, 'h': h, 'clear': clear}


def scots_pine(V, x, y, g, rng, h=None, pal=None, details=None):
    """Tall 'silver pine': bare curving trunk, orange upper bark, flat cloud-like crown clumps up high."""
    h = h or int(rng.integers(22, 34))
    pal = int(rng.integers(0, 8)) if pal is None else pal
    fa, fb = FOLS[pal], FOLS[(pal + 1) % 8]
    details = details if details is not None else pick_details(
        rng, allow=('lantern', 'ribbon', 'claws', 'nest', 'deadbranch', 'charm', 'moss'))
    w = 2 if h >= 24 else 1
    # curving trunk: offset drifts by up to 2 over the height
    ox = oy = 0.0
    vx, vy = (rng.random() - 0.5) * 0.12, (rng.random() - 0.5) * 0.12
    pos = []
    for k in range(h):
        if k > h * 0.3:
            ox += vx; oy += vy
        tx, ty = x + int(round(ox)), y + int(round(oy))
        mat = SCOTS_BARK if k > h * 0.45 else BARK
        if 'claws' in details and 3 <= k <= 8:
            mat = CLAW_BARK if k % 2 else BARK
        for dx in range(w):
            for dy in range(w):
                V.put(tx + dx, ty + dy, g - 1 - k, mat)
        if pos and (tx, ty) != pos[-1][:2]:              # keep face contact when the trunk shifts
            px_, py_, _ = pos[-1]
            V.put(px_, py_, g - 1 - k, mat)
            V.put(tx, py_, g - 1 - k, mat)
        pos.append((tx, ty, g - 1 - k))
    for (dx, dy) in ((-1, 0), (w, 1), (0, w), (1, -1)):
        if rng.random() < 0.6:
            V.put(x + dx, y + dy, g - 1, BARK_DK)
    n = int(rng.integers(3, 7))
    tips, tops = [], []
    for i in range(n):
        f = 0.62 + 0.38 * (i / max(n - 1, 1)) + (rng.random() - 0.5) * 0.08
        k = min(h - 1, int(f * h))
        tx, ty, tz = pos[k]
        ang = rng.random() * 6.283
        reach = (1 - f) * 10 + 1.5 + rng.random() * 2.5
        ex, ey = tx + reach * math.cos(ang), ty + reach * math.sin(ang)
        ez = tz - 1 - int(rng.integers(0, 3))
        V.line4((tx, ty, tz), (ex, ey, ez), BARK if f < 0.8 else SCOTS_BARK)
        rx = 2.5 + rng.random() * 3.5 * (1.2 - f) + 1.2
        rz = 1.3 + rng.random() * 0.8
        mat = fa if i % 2 == 0 else fb
        jag = _jag(rng)
        for dx in range(-int(rx) - 2, int(rx) + 3):
            for dy in range(-int(rx) - 2, int(rx) + 3):
                for dz in range(-2, 3):
                    px, py, pz = int(round(ex)) + dx, int(round(ey)) + dy, ez + dz
                    d = math.sqrt((dx / (rx * jag(math.atan2(dy, dx)))) ** 2 + (dy / (rx * 0.85)) ** 2 +
                                  ((dz + 0.6) / rz) ** 2)
                    if d <= 1.0 + (hsh(px, py, pz) - 0.5) * 0.25 and V.get(px, py, pz) == AIR:
                        V.put(px, py, pz, fb if dz < 0 and hsh(px, py, pz, 2) < 0.6 else mat)
                        if d > 0.75 and dz >= 0:
                            tips.append((px, py, pz))
                        if dz <= -1:
                            tops.append((px, py, pz, d))
    top = pos[-1]
    V.put(top[0], top[1], top[2] - 1, fb)
    _decorate(V, x, y, g, h, rng, details, tips, tops, w)
    return {'h': h}


def snag(V, x, y, g, rng, h=None, details=None):
    """Dead, broken pine: grey trunk, stub branches, jagged top."""
    h = h or int(rng.integers(9, 22))
    w = 2 if h >= 16 else 1
    details = details if details is not None else pick_details(
        rng, allow=('claws', 'ribbon', 'charm', 'lantern', 'rust', 'moss', 'snowcap', 'nest'))
    for k in range(h):
        for dx in range(w):
            for dy in range(w):
                if k >= h - 2 and hsh(x + dx, y + dy, k) < 0.5:
                    continue
                mat = DEADWOOD if hsh(x + dx, y + dy, k, 4) < 0.85 else BARK_DK
                if 'claws' in details and 2 <= k <= 7 and dx == 0 and (k + dy) % 3 == 0:
                    mat = CLAW_BARK
                V.put(x + dx, y + dy, g - 1 - k, mat)
    k = 4 + int(rng.integers(0, 3))
    while k < h - 2:
        ang = rng.random() * 6.283
        L = int(rng.integers(2, 6))
        V.line4((x, y, g - 1 - k), (x + L * math.cos(ang), y + L * math.sin(ang), g - 1 - k - int(rng.integers(0, 3))),
                DEADWOOD)
        k += int(rng.integers(2, 5))
    if 'rust' in details:
        for _ in range(6):
            px, py = x + int(rng.integers(-2, 3)), y + int(rng.integers(-2, 3))
            pz = g - 1 - int(rng.integers(h // 2, h))
            if V.get(px, py, pz) == AIR and any(V.get(px + a, py + b, pz + c) not in (AIR, 255)
                                                for a, b, c in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0),
                                                                (0, 0, 1))):
                V.put(px, py, pz, RUST)
    _decorate(V, x, y, g, h, rng, details - {'rust'}, [], [], w, dead=True)
    return {'h': h}


def sapling(V, x, y, g, rng, h=None, pal=None):
    h = h or int(rng.integers(4, 8))
    pal = int(rng.integers(0, 8)) if pal is None else pal
    V.box(x, x, y, y, g - h, g - 1, BARK)
    for k in range(1, h + 1):
        r = (h - k) * 0.45 + 0.6
        z = g - 1 - k
        ri = int(math.ceil(r))
        for dx in range(-ri, ri + 1):
            for dy in range(-ri, ri + 1):
                if dx * dx + dy * dy <= r * r + 0.3 and V.get(x + dx, y + dy, z) == AIR:
                    V.put(x + dx, y + dy, z, FOLS[pal] if k < h - 1 else FOLS[(pal + 1) % 8])
    V.put(x, y, g - 2 - h, FOLS[(pal + 1) % 8])
    if rng.random() < 0.4:
        V.put_air(x, y, g - 3 - h, SNOWCAP)


def birch(V, x, y, g, rng, h=None):
    """Bare winter birch (sparse use: pale bark with dark marks, thin twiggy crown in rust tones)."""
    h = h or int(rng.integers(10, 17))
    for k in range(h):
        V.put(x, y, g - 1 - k, BIRCH if hsh(x, y, k) > 0.22 else BARK_DK)
    k = h // 2
    while k < h:
        ang = rng.random() * 6.283
        L = int(rng.integers(2, 5))
        p = V.line4((x, y, g - 1 - k), (x + L * math.cos(ang), y + L * math.sin(ang), g - 2 - k - L // 2), BARK_DK)
        ex, ey, ez = p[-1]
        if rng.random() < 0.6:
            V.put_air(ex, ey, ez - 1, RUST)
        k += int(rng.integers(1, 3))


# ------------------------------------------------------------------ shared decoration

def _decorate(V, x, y, g, h, rng, details, tips, tops, w, dead=False):
    if 'snowcap' in details and tops:
        for (px, py, pz, dn) in tops:                    # coherent caps: whole angular sectors of a tier
            sector = int((math.atan2(py - y, px - x) + math.pi) / (2 * math.pi) * 5) % 5
            if 0.2 < dn < 0.92 and hsh(x, y, pz // 2, sector) < 0.55:
                V.put_air(px, py, pz - 1, SNOWCAP)
    if 'frost' in details and tips:
        for (px, py, pz) in tips:
            if hsh(px, py, pz, 11) < 0.35 and pz < g - h * 0.35:
                V.put(px, py, pz, FROST)
    if 'icicles' in details and tips:
        for (px, py, pz) in tips:
            if hsh(px, py, pz, 12) < 0.16 and V.get(px, py, pz + 1) == AIR:
                V.put(px, py, pz + 1, ICICLE)
                if hsh(px, py, pz, 13) < 0.4:
                    V.put_air(px, py, pz + 2, ICICLE)
    if 'rust' in details and tips:
        for (px, py, pz) in tips:
            if hsh(px, py, pz, 14) < 0.07:
                V.put(px, py, pz, RUST)
    if 'cones' in details and tips:
        for (px, py, pz) in tips:
            if hsh(px, py, pz, 15) < 0.03:
                V.put_air(px, py, pz + 1, CONE)
    low = [t for t in tips if g - 1 - t[2] >= 5] if tips else []
    if 'lantern' in details:
        if low:
            px, py, pz = low[int(rng.integers(0, len(low)))]
            if V.get(px, py, pz + 1) == AIR and V.get(px, py, pz + 2) == AIR:
                V.put(px, py, pz + 1, IRON_DK); V.put(px, py, pz + 2, LANTERN)
        else:                                               # nail a lantern to the trunk
            z = g - 4
            V.put(x - 1, y, z, IRON_DK); V.put(x - 1, y, z + 1, LANTERN)
    if 'charm' in details:
        src = low if low else [(x - 1, y, g - 6)]
        px, py, pz = src[int(rng.integers(0, len(src)))]
        if not low:
            V.put(px, py, pz, DEADWOOD)
        drop = int(rng.integers(1, 3))
        for k in range(1, drop + 1):
            V.put_air(px, py, pz + k, ROPE)
        V.put_air(px, py, pz + drop + 1, BONE)
        V.put_air(px, py, pz + drop + 2, BONE if rng.random() < 0.5 else CANDLE)
    if 'ribbon' in details:
        z = g - 3 - int(rng.integers(0, 2))
        side = int(rng.integers(0, 4))
        ox, oy = ((-1, 0), (w, 0), (0, -1), (0, w))[side]
        V.put(x + ox, y + oy, z, RAG_RED)
        V.put(x + ox, y + oy, z + 1, RAG_RED)
    if 'nest' in details:
        z = g - 1 - int(h * (0.6 if not dead else 0.8))
        for (dx, dy) in ((-1, 0), (w, 0), (0, -1), (0, w), (-1, -1), (w, w)):
            V.put_air(x + dx, y + dy, z, STRAW)
        if rng.random() < 0.6:
            V.put_air(x - 1, y, z - 1, CROW)
    if 'deadbranch' in details:
        z = g - 2 - int(rng.integers(1, 3)) if dead else g - 1 - max(2, int(h * 0.2))
        ang = rng.random() * 6.283
        V.line4((x, y, z), (x + 4 * math.cos(ang), y + 4 * math.sin(ang), z - 2), DEADWOOD)
    if 'moss' in details:
        for k in range(3):
            for (dx, dy) in ((0, -1), (-1, 0)):
                if hsh(x + dx, y + dy, k, 16) < 0.7:
                    V.put_air(x + dx, y + dy, g - 1 - k, MOSS) if k == 0 else V.put(x, y, g - 1 - k, MOSS)
    if 'claws' in details and w == 1:
        for k in (3, 5, 6):
            V.put(x, y, g - 1 - k, CLAW_BARK)
