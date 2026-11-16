"""Northgale Freighter art pass: COLOUR ONLY (the solid array is asserted unchanged).

Hull paint bands (white sheer strake, oxblood topsides, dark boot-top), rust streaks, deck markings, the ship's
name on both bows/quarters, islet colour cover, the painted z 63 sea (lit shallows inside the boundary, a soft
buoy-line edge, dark deep sea outside), night grade, baked light + glow bake, brightness rules, the corner tag
painted on the deep sea.

art(cv, rep, S) -> (stored glow colours, report)
"""
from __future__ import annotations

import hashlib
import math

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
    # v1.2: plate seams (soft), a pale belting line, anchors in their hawse pockets, forecastle portholes
    hx, hy, hz = np.nonzero(sel('hull'))
    c = cv.rgb[hx, hy, hz].astype(float)
    seam = (np.abs(hx - 256) % 14 == 0) | (hz == 50)
    c[seam] *= 0.9
    c[hz == 47] = _mix(c[hz == 47], (196, 176, 120), 0.6)
    cv.rgb[hx, hy, hz] = np.clip(c, 0, 255).astype(np.uint8)

    def hull_face(x, z, north):
        rng_ = range(180, 256) if north else range(332, 256, -1)
        for y in rng_:
            if solid[x, y, z]:
                return y
        return None
    anchor = [(0, -1), (0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (-2, 0), (-1, 0), (1, 0), (2, 0),
              (-3, 5), (-2, 6), (-1, 6), (0, 6), (1, 6), (2, 6), (3, 5), (-3, 4), (3, 4)]
    for north in (True, False):
        ax, az = S['detail']['anchor_x'], deck + 3
        for (ox, oz) in [(o, -1) for o in (-1, 0, 1)] + [(o, -2) for o in (-1, 0, 1)]:
            y = hull_face(ax + ox, az + oz, north)
            if y is not None:
                cv.rgb[ax + ox, y, az + oz] = (34, 34, 38)                   # hawse pipe
        for (ox, oz) in anchor:
            y = hull_face(ax + ox, az + oz, north)
            if y is not None:
                cv.rgb[ax + ox, y, az + oz] = (70, 72, 78)
        for x in range(24, 62, 6):                                         # forecastle portholes
            for z in (Z['forecastle'] + 2,):
                y = hull_face(x, z, north)
                if y is not None and cv.mat[x, y, z] == M['hull']:
                    cv.rgb[x, y, z] = (214, 196, 120)
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
    # ------------------------------------------------------------------ deck (v1.2): tiled steel grid, lanes, hazards
    dx_, dy_, dz_ = np.nonzero(sel('deck'))
    g = cv.rgb[dx_, dy_, dz_].astype(float)
    f = noise.fbm2((512, 512), 6, 3, 'deckwear', seed)[dx_, dy_]
    g *= (0.93 + 0.12 * f)[:, None]
    tile = ((np.abs(dx_ - 256) % 8) == 0) | ((np.abs(dy_ - 256) % 8) == 4)
    g[tile] *= 0.86                                                         # plate seams (soft, 1 in 8)
    g = _mix(g, (124, 92, 66), 0.32 * np.clip((f - 0.72) / 0.14, 0, 1))  # rust patches
    lane = (np.abs(dy_ - (ya + 11)) <= 0) | (np.abs(dy_ - (yb - 11)) <= 0) | \
        (np.abs(dy_ - (ya + 1)) == 0) | (np.abs(dy_ - (yb - 1)) == 0)
    g[lane] = (196, 166, 64)                                               # yellow walkway lane edges
    # hazard stripes (2-wide diagonal yellow / dark) round crane pedestals, deckhouses, stair heads, the deck hatch
    near = np.zeros((512, 512), bool)
    for nm in ('crane', 'deckhouse', 'coaming', 'stair'):
        if nm in M:
            m2 = (cv.mat == M[nm]).any(axis=2)
            near |= ndi.binary_dilation(m2, iterations=2) & ~m2
    hz_ = near[dx_, dy_] & (dz_ == deck)
    stripe = ((dx_ + dy_) // 2) % 2 == 0
    g[hz_ & stripe] = (206, 170, 52)
    g[hz_ & ~stripe] = (76, 76, 80)
    cv.rgb[dx_, dy_, dz_] = np.clip(g, 0, 255).astype(np.uint8)
    # hatch panels: green with white borders (panel edges) and big numbers 01..06
    hx_, hy_, hz2 = np.nonzero(sel('hatch'))
    hid = M['hatch']
    edge = np.zeros(len(hx_), bool)
    for (ox, oy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        edge |= cv.mat[np.clip(hx_ + ox, 0, 511), np.clip(hy_ + oy, 0, 511), hz2] != hid
    c = cv.rgb[hx_, hy_, hz2].astype(float)
    c[edge] = (176, 180, 170)
    cv.rgb[hx_, hy_, hz2] = np.clip(c, 0, 255).astype(np.uint8)
    for k, (bx0, bx1) in enumerate(S['hatch_bays']):
        for (xx, num) in ((bx0 + 3, f'0{k + 1}'), (512 - bx1 + 3, f'0{6 - k}')):
            mm = np.kron(text_mask([num]), np.ones((2, 2), bool))
            for i in range(mm.shape[0]):
                for j in range(mm.shape[1]):
                    if mm[i, j]:
                        X_, Y_ = xx + i, S['hatch_y'][0] + 3 + j
                        if solid[X_, Y_, Z['hatch']] and cv.mat[X_, Y_, Z['hatch']] == hid:
                            cv.rgb[X_, Y_, Z['hatch']] = (206, 202, 192)
    # ------------------------------------------------------------------ bridge (v1.2): floor bands, helideck markings
    Bd = S['bridge']
    bx0, bx1 = Bd['x']
    by0, by1 = Bd['y']
    roof = deck - Bd['storeys'] * Bd['storey_h']
    sid = M.get('superstructure')
    for k in range(Bd['storeys'] + 1):
        z = deck - k * Bd['storey_h']
        col = (56, 74, 122) if k < Bd['storeys'] else (214, 112, 40)
        for x in range(bx0, bx1 + 1):
            for y in (by0, by1):
                if solid[x, y, z] and cv.mat[x, y, z] == sid:
                    cv.rgb[x, y, z] = col
        for y in range(by0, by1 + 1):
            for x in (bx0, bx1):
                if solid[x, y, z] and cv.mat[x, y, z] == sid:
                    cv.rgb[x, y, z] = col
    hc, hr = S['helideck']['c'], S['helideck']['r']
    for x in range(hc[0] - hr - 1, hc[0] + hr + 2):
        for y in range(hc[1] - hr - 1, hc[1] + hr + 2):
            if not (solid[x, y, roof] and cv.mat[x, y, roof] == sid) or solid[x, y, roof - 1]:
                continue
            r = math.hypot(x - hc[0], y - hc[1])
            if r > hr + 0.5:
                continue
            col = (64, 76, 74)
            if hr - 0.6 <= r <= hr + 0.5:
                col = (200, 198, 188)                                      # perimeter line
            elif hr * 0.62 <= r <= hr * 0.62 + 1.6:
                col = (214, 176, 48)                                       # touchdown circle
            u, v = x - hc[0], y - hc[1]
            if (abs(v) <= 5 and 2 <= abs(u) <= 3) or (abs(u) <= 3 and abs(v) <= 0):
                col = (206, 204, 196)                                      # the H
            cv.rgb[x, y, roof] = col
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
