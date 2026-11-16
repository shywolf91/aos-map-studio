"""Northgale Freighter art pass: COLOUR ONLY (the solid array is asserted unchanged).

Hull paint bands (white sheer strake, oxblood topsides, dark boot-top), rust streaks, deck markings, the ship's
name on both bows/quarters, islet colour cover, the painted z 63 sea (lit shallows inside the boundary, a soft
buoy-line edge, dark deep sea outside), night grade, baked light + glow bake, brightness rules, the corner tag
painted on the deep sea.

art(cv, rep, S) -> (stored glow colours, report)
"""
from __future__ import annotations

import hashlib

import numpy as np
from scipy import ndimage as ndi

from aosmap.kit import color, noise, tag
from aosmap.kit.codec import surface_mask
from aosmap.pixelfont import text_mask

GLOW_PALETTE = {(255, 255, 255), (255, 95, 95), (255, 255, 95), (95, 255, 255), (255, 175, 95), (95, 255, 95)}
NIGHT = np.array((0.80, 0.83, 0.94))

SEA_IN = [(0, (126, 150, 160)), (2, (108, 138, 150)), (8, (86, 118, 136)), (22, (70, 100, 124)),
          (50, (60, 88, 114)), (120, (54, 80, 108))]
SEA_DEEP = (40, 56, 84)


def _mix(a, b, t):
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    t = np.asarray(t, float)[..., None] if np.ndim(t) else t
    return a + (b - a) * t


def art(cv, rep, S):
    before = hashlib.sha256(np.packbits(cv.solid).tobytes()).hexdigest()
    seed = S['layout_seed']
    out = {}
    solid = cv.solid
    surf = surface_mask(solid)
    M = cv.materials
    Z = S['z']
    deck = Z['deck']

    def sel(*names):
        ids = [M[n] for n in names if n in M]
        return np.isin(cv.mat, ids) & solid

    # ------------------------------------------------------------------ hull bands + rust streaks
    hx, hy, hz = np.nonzero(sel('hull'))
    streak = noise.fbm2((512, 512), 3, 2, 'rust', seed)
    rust = np.clip((streak[hx, hy] - 0.58) / 0.12, 0, 1) * np.clip((hz - deck - 2) / 10, 0, 1)
    band = np.where(hz <= deck + 1, 0, np.where(hz >= 56, 2, 1))
    base = np.array([(196, 192, 182), (122, 36, 40), (64, 40, 42)], float)[band]
    base = np.where((hz == deck + 2)[:, None], np.array((200, 196, 186), float), base)   # thin white line
    base = _mix(base, (128, 74, 48), 0.55 * rust)
    base *= (0.95 + 0.08 * noise.hash3(hx, hy, hz, 61))[:, None]
    cv.rgb[hx, hy, hz] = np.clip(base, 0, 255).astype(np.uint8)
    # draught marks near bow and stern (white ticks on the boot-top)
    for x in (80, 432):
        for y in (S['hull']['y'][0], S['hull']['y'][1]):
            for z in range(48, 62, 3):
                if solid[x, y, z]:
                    cv.rgb[x, y, z] = (190, 186, 176)
    # ship's name on both sides near the bow (west) and on the quarters (east)
    name = 'NORTHGALE'
    m = text_mask([name])                       # (w, h) bool, x along the text
    w, h = m.shape
    z0 = deck + 4
    ya, yb = S['hull']['y']
    # read from outside: on the north face the text runs toward -x, on the south face toward +x
    for (x_first, y_face, step) in ((150, ya, -1), (150 - w + 1, yb, 1), (362 + w - 1, ya, -1), (362, yb, 1)):
        for i in range(w):
            for j in range(h):
                if m[i, j]:
                    X = x_first + step * i
                    if solid[X, y_face, z0 + j]:
                        cv.rgb[X, y_face, z0 + j] = (206, 202, 192)
    # ------------------------------------------------------------------ deck: walkway lines, hatch numbers, rust
    dx_, dy_, dz_ = np.nonzero(sel('deck'))
    g = cv.rgb[dx_, dy_, dz_].astype(float)
    f = noise.fbm2((512, 512), 6, 3, 'deckwear', seed)[dx_, dy_]
    g *= (0.92 + 0.14 * f)[:, None]
    g = _mix(g, (118, 96, 70), 0.30 * np.clip((f - 0.7) / 0.15, 0, 1))
    walk = (np.abs(dy_ - (ya + 11)) == 0) | (np.abs(dy_ - (yb - 11)) == 0)
    g[walk] = (176, 168, 112)                                              # yellow walkway lines
    cv.rgb[dx_, dy_, dz_] = np.clip(g, 0, 255).astype(np.uint8)
    # hatch numbers 01..06 painted on the panels next to the gangway edge
    for k, (bx0, bx1) in enumerate(S['hatch_bays']):
        for (xx, num) in ((bx0 + 2, f'0{k + 1}'), (512 - bx1 + 2, f'0{6 - k}')):
            mm = text_mask([num])
            for i in range(mm.shape[0]):
                for j in range(mm.shape[1]):
                    if mm[i, j]:
                        X, Y = xx + i, S['hatch_y'][0] + 2 + j
                        if solid[X, Y, Z['hatch']]:
                            cv.rgb[X, Y, Z['hatch']] = (200, 196, 186)
    # ------------------------------------------------------------------ islets: rock / moss / sand cover
    X, Y = np.indices((512, 512))
    rx, ry, rz = np.nonzero(sel('rock'))
    lich = noise.fbm2((512, 512), 4, 2, 'lichen', seed)
    c = cv.rgb[rx, ry, rz].astype(float)
    c = _mix(c, (118, 122, 96), 0.35 * np.clip((lich[rx, ry] - 0.55) / 0.2, 0, 1))
    c *= (1 - 0.18 * np.clip((rz - 56) / 7, 0, 1))[:, None]                # darker, wet at the foot
    cv.rgb[rx, ry, rz] = np.clip(c, 0, 255).astype(np.uint8)
    gx, gy, gz = np.nonzero(sel('ground'))
    heath = noise.fbm2((512, 512), 7, 3, 'heath', seed)
    c = cv.rgb[gx, gy, gz].astype(float)
    c = _mix(c, (112, 84, 96), 0.45 * np.clip((heath[gx, gy] - 0.6) / 0.15, 0, 1))   # heather patches
    c = _mix(c, (122, 118, 88), 0.30 * np.clip((0.35 - heath[gx, gy]) / 0.15, 0, 1))  # dry grass
    cv.rgb[gx, gy, gz] = np.clip(c, 0, 255).astype(np.uint8)
    # ------------------------------------------------------------------ painted sea (z 63)
    water = ~solid[:, :, 62]
    dland = ndi.distance_transform_edt(water)
    B = S['boundary']
    inside = (X >= B['left']) & (X <= B['right']) & (Y >= B['top']) & (Y <= B['bottom'])
    dedge = np.minimum.reduce([X - B['left'], B['right'] - X, Y - B['top'], B['bottom'] - Y]).astype(float)
    sx, sy = np.nonzero(water)
    d = dland[sx, sy]
    g = color.ramp(SEA_IN, d)
    wave = noise.fbm2((512, 512), 11, 3, 'swell', seed)[sx, sy]
    g *= (0.94 + 0.10 * wave)[:, None]
    # wake / foam along the hull and the beaches
    foam = (d <= 2.5) * np.clip((noise.fbm2((512, 512), 3, 2, 'foam', seed)[sx, sy] - 0.45) / 0.2, 0, 1)
    g = _mix(g, (164, 178, 186), 0.45 * foam)
    # deep sea outside the boundary: darker, with a soft 6-voxel edge just outside the buoy line
    de = dedge[sx, sy]
    deep = np.clip((-de) / 6.0, 0, 1)
    g = _mix(g, np.array(SEA_DEEP) * (0.94 + 0.1 * wave[:, None]), deep)
    # moonlight glitter path (soft streak, north-east to south-west, away from the ship)
    u = (sx - 256) * 0.6 + (sy - 256) * 0.8
    v = -(sx - 256) * 0.8 + (sy - 256) * 0.6
    glit = np.exp(-(v / 26.0) ** 2) * (u < -90) * np.clip((noise.fbm2((512, 512), 2, 2, 'glit', seed)[sx, sy] - 0.5)
                                                          / 0.25, 0, 1)
    g = _mix(g, (176, 182, 200), 0.35 * glit)
    cv.rgb[sx, sy, np.full(len(sx), 63)] = np.clip(np.rint(g), 0, 255).astype(np.uint8)
    out['sea_columns'] = int(len(sx))
    out['water_pct'] = round(100 * float(water.mean()), 2)
    # ------------------------------------------------------------------ night grade (glow sources excluded)
    m = solid & ~cv.nolight
    cv.rgb[m] = np.clip(cv.rgb[m].astype(float) * NIGHT[None, :], 0, 255).astype(np.uint8)
    # ------------------------------------------------------------------ light, glow, brightness, tag
    for (x, y, z, c_) in cv.glow:
        cv.rgb[x, y, z] = c_
    color.lighting(cv, side_f=0.86)
    stored, nsrc = color.bake_glow(cv, surf, radius=6.5, strength=0.32)
    out['brightness'] = color.enforce_brightness(cv)
    src = {(x, y, z) for (x, y, z, _) in cv.glow}
    pal = np.array(sorted(GLOW_PALETTE))
    sxs, sys_, szs = np.nonzero(surf)
    rgb = cv.rgb[sxs, sys_, szs].astype(int)
    hit = (rgb[:, None, :] == pal[None, :, :]).all(-1).any(-1)
    nudged = 0
    for i in np.nonzero(hit)[0]:
        k = (int(sxs[i]), int(sys_[i]), int(szs[i]))
        if k not in src:
            cv.rgb[k][1] = max(0, int(cv.rgb[k][1]) - 1)
            nudged += 1
    for (x, y, z, c_) in cv.glow:
        cv.rgb[x, y, z] = c_
    out['glow'] = {'sources': nsrc, 'stored_entries': len(stored), 'nudged_off_palette': nudged}
    T = S['tag']
    rect = tag.paint_tag(cv, T['text'], corner=T['corner'], margin=T['margin'], scale=T['scale'], rgb=T['rgb'],
                         shadow=T['shadow'], level=False)
    out['tag_rect'] = list(rect)
    after = hashlib.sha256(np.packbits(cv.solid).tobytes()).hexdigest()
    assert before == after, 'art pass changed solid geometry'
    out['solid_unchanged'] = True
    out['colour_stats'] = color.colour_stats(cv.solid, cv.rgb)
    return stored, out
