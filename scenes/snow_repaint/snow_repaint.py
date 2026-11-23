"""Shared artistic snow repaint for classic AoS maps. Only the colour of the selected "snow" voxels
changes; no voxel is added or removed, every other colour (and the shade byte) is untouched.

Per voxel: baked sun light from terrain relief, ambient occlusion against props/walls, wind
ripples, flowing contour ribbons, Yukon-style terrace rims and foot shadows, drifting colour zones
(cyan / periwinkle / lilac / mint), frost sparkle, and a cyan glow where snow meets other ground.
Brightness is limited by luma (luma_max), not by channel, so it stays free of glare.

usage: python snow_repaint.py <map-key> <in.vxl> <out.vxl>      (keys: see MAPS)   deterministic
"""
import sys
sys.path.insert(0, __file__.rsplit('scenes', 1)[0])
import numpy as np
from scipy import ndimage as ndi
from aosmap import vxl

LUMA_W = np.array([0.299, 0.587, 0.114])

PALETTES = {
    # Yukon-sampled saturated cyan/periwinkle
    'yukon': dict(
        cool=[(0, (66, 96, 168)), (.18, (100, 140, 205)), (.38, (128, 184, 244)), (.6, (160, 208, 255)), (.8, (188, 226, 255)), (1, (208, 232, 255))],
        blush=[(0, (96, 84, 168)), (.25, (140, 128, 218)), (.5, (184, 172, 250)), (.75, (212, 196, 255)), (1, (228, 214, 250))],
        mint=[(0, (54, 112, 170)), (.25, (88, 160, 214)), (.5, (126, 208, 246)), (.75, (170, 234, 255)), (1, (204, 242, 252))],
        lav=[(0, (82, 84, 186)), (.25, (128, 132, 232)), (.55, (182, 185, 255)), (.8, (205, 208, 255)), (1, (224, 224, 255))],
        ice=[(0, (40, 100, 180)), (.4, (84, 168, 240)), (.75, (140, 214, 255)), (1, (190, 238, 255))]),
    # paler, whiter snow with a cyan rim (Icecraft-like), still clearly snow on green/brown ground
    'pale': dict(
        cool=[(0, (92, 122, 190)), (.2, (128, 166, 224)), (.42, (166, 205, 246)), (.66, (200, 226, 252)), (.85, (220, 236, 252)), (1, (232, 242, 252))],
        blush=[(0, (112, 100, 180)), (.25, (152, 142, 222)), (.5, (192, 184, 248)), (.75, (216, 206, 252)), (1, (232, 224, 250))],
        mint=[(0, (78, 130, 186)), (.25, (110, 170, 220)), (.5, (150, 212, 244)), (.75, (190, 236, 252)), (1, (218, 246, 252))],
        lav=[(0, (100, 102, 196)), (.25, (140, 146, 236)), (.55, (188, 192, 255)), (.8, (210, 214, 255)), (1, (228, 230, 255))],
        ice=[(0, (56, 118, 196)), (.4, (100, 178, 244)), (.75, (160, 222, 255)), (1, (208, 242, 255))]),
    # moonlit: deep indigo shadows, silver-blue highlights
    'night': dict(
        cool=[(0, (34, 46, 112)), (.22, (62, 86, 156)), (.45, (100, 134, 204)), (.7, (144, 176, 232)), (1, (188, 212, 250))],
        blush=[(0, (62, 52, 124)), (.25, (100, 88, 170)), (.5, (142, 132, 214)), (.75, (178, 168, 242)), (1, (206, 198, 250))],
        mint=[(0, (30, 74, 124)), (.25, (58, 114, 176)), (.5, (96, 160, 220)), (.75, (136, 202, 240)), (1, (176, 228, 250))],
        lav=[(0, (44, 44, 126)), (.25, (84, 86, 178)), (.55, (130, 136, 226)), (.8, (168, 174, 246)), (1, (198, 204, 255))],
        ice=[(0, (26, 70, 150)), (.4, (60, 128, 214)), (.75, (110, 186, 248)), (1, (160, 218, 255))]),
}


def ramp(t, stops):
    pos = np.array([p for p, _ in stops])
    cols = np.array([c for _, c in stops], float)
    return np.stack([np.interp(t, pos, cols[:, i]) for i in range(3)], -1)


def repaint(m, snow, palette='yukon', luma_max=224.0, coast_w=24.0, ribbon=0.35, seed=7511,
            zone_scale=1.0, wind=0.30, bias=0.62, soft=0.0, foot_mode='any'):
    rng = np.random.default_rng(seed)

    def noise(sigma):
        n = ndi.gaussian_filter(rng.standard_normal((512, 512)), sigma, mode='wrap')
        return (n - n.mean()) / n.std()

    P = PALETTES[palette]
    X, Y, Z = np.nonzero(snow)
    solid = m.solid

    # ---- relief ----
    top_z = np.argmax(solid, axis=2)
    H = (63 - top_z).astype(float)
    Hsn = np.where(snow.any(axis=2), 63 - np.argmax(snow, axis=2), np.nan)
    lim = np.nanpercentile(Hsn, 97) + 3
    Hc = np.minimum(H, lim)                       # ignore tall props/walls in the relief maths
    Hs = ndi.gaussian_filter(Hc, 1.2)
    gx, gy = np.gradient(Hs)
    lam = np.tanh(-(gx * -0.55 + gy * -0.55) * 2.2)          # sun from the north-west
    hollow = np.tanh((ndi.gaussian_filter(Hc, 7) - Hc) / 2.0)

    # ---- ambient occlusion against non-snow solids (props, walls, trees) ----
    ns = (solid & ~snow).astype(np.float32)
    occ = ndi.uniform_filter(ns, size=(5, 5, 5))
    ao = np.clip(occ[X, Y, Z] * 3.0, 0, 1)
    del ns, occ

    # ---- snow footprint: edge glow + ribbons ----
    if foot_mode == 'top':      # snow covers the whole ground: measure distance to trees/buildings
        foot = np.take_along_axis(snow, top_z[:, :, None], 2)[:, :, 0]
    else:
        foot = snow.any(axis=2)
    dist = ndi.distance_transform_edt(np.pad(foot, 1, constant_values=True))[1:-1, 1:-1]
    warp = noise(14) * 4.0 + noise(5) * 1.2
    rib = (0.5 + 0.5 * np.sin((dist + warp) * 0.62)) * np.clip(dist / 8, 0, 1)
    coast = ndi.gaussian_filter(np.clip(1 - dist / coast_w, 0, 1) ** 1.3, 2)

    # ---- wind ripples ----
    wz = ndi.gaussian_filter(rng.standard_normal((512, 512)), (2.2, 9.0), mode='wrap')
    wz = (wz - wz.mean()) / wz.std()
    wz2 = ndi.gaussian_filter(rng.standard_normal((512, 512)), (4.5, 20.0), mode='wrap')
    wz2 = (wz2 - wz2.mean()) / wz2.std()
    ripple = np.tanh(wz * 0.9 + wz2 * 0.6)

    zA, zB, zC = noise(46 * zone_scale), noise(30 * zone_scale), noise(16 * zone_scale)
    z1, z2 = noise(60 * zone_scale), noise(60 * zone_scale)

    def nb(dx, dy, dz):
        o = np.zeros_like(solid)
        sx = slice(max(dx, 0), 512 + min(dx, 0)); tx = slice(max(-dx, 0), 512 + min(-dx, 0))
        sy = slice(max(dy, 0), 512 + min(dy, 0)); ty = slice(max(-dy, 0), 512 + min(-dy, 0))
        sz = slice(max(dz, 0), 64 + min(dz, 0)); tz = slice(max(-dz, 0), 64 + min(-dz, 0))
        o[tx, ty, tz] = solid[sx, sy, sz]
        return o
    top_open = ~nb(0, 0, -1)
    top_open[:, :, 0] = True
    fNW = (~nb(0, -1, 0)) | (~nb(-1, 0, 0))
    fSE = (~nb(0, 1, 0)) | (~nb(1, 0, 0))
    topo = top_open[X, Y, Z]
    side = ~topo

    def sh(a, dx, dy):
        return np.roll(np.roll(a, dx, 0), dy, 1)
    rim = np.clip(Hc - sh(Hc, 1, 1), 0, 3) / 3 + 0.5 * np.clip(Hc - sh(Hc, 2, 2), 0, 3) / 3
    foot_ = np.clip(sh(Hc, -1, -1) - Hc, 0, 3) / 3 + 0.5 * np.clip(sh(Hc, -2, -2) - Hc, 0, 3) / 3
    atop = (Z == top_z[X, Y])

    L = 0.55 * lam[X, Y] - 0.55 * hollow[X, Y] - 0.75 * ao + wind * ripple[X, Y]
    L -= ribbon * rib[X, Y] * (0.4 + coast[X, Y])
    L += 0.55 * rim[X, Y] * atop - 0.50 * foot_[X, Y] * atop
    L += 0.18 * (fNW[X, Y, Z] & side) - 0.45 * (fSE[X, Y, Z] & side)
    L += rng.normal(0, 0.06, len(X))
    t = np.clip(bias + 0.52 * L, 0, 1)

    hb = np.clip(z1[X, Y] * 0.9 + zC[X, Y] * 0.3, 0, 1)
    hm = np.clip(z2[X, Y] * 0.9 + zB[X, Y] * 0.3, 0, 1)
    hl = np.clip(-z1[X, Y] * 0.7 + zA[X, Y] * 0.5, 0, 1)
    col = ramp(t, P['cool'])
    for w, key in ((0.65 * hb, 'blush'), (0.6 * hm, 'mint'), (0.85 * hl, 'lav')):
        col = col + (ramp(t, P[key]) - col) * w[:, None]
    col = col + (ramp(t, P['ice']) - col) * (0.8 * coast[X, Y])[:, None]

    u = rng.random(len(X))
    sp = (u > 0.985) & topo
    col[sp] = col[sp] * 0.35 + np.array([232, 240, 255]) * 0.65
    cr = (u < 0.012) & topo
    col[cr] = col[cr] * 0.78 + np.array([70, 110, 190]) * 0.22
    col += rng.normal(0, 1.8, (len(X), 1))

    col = np.clip(col, 0, 255)
    luma = col @ LUMA_W
    if soft:                                   # pull toward a cool near-neutral of the same brightness
        neutral = luma[:, None] * np.array([0.96, 1.0, 1.06])
        col = col * (1 - soft) + neutral * soft
        luma = col @ LUMA_W
    col = col * np.minimum(1.0, luma_max / np.maximum(luma, 1))[:, None]
    col = np.clip(np.rint(col), 0, 255).astype(np.uint32)
    old = m.color[snow]
    m.color[X, Y, Z] = (old & 0xFF000000) | (col[:, 0] << 16) | (col[:, 1] << 8) | col[:, 2]
    return len(X)


def _rgb(m):
    c = m.color
    return ((c >> 16) & 255).astype(int), ((c >> 8) & 255).astype(int), (c & 255).astype(int)


def snow_battlefarm(m):
    r, g, b = _rgb(m)
    return m.colored & (r == 220) & (g == 220) & (b == 220)


def snow_royal(m):
    r, g, b = _rgb(m)       # the night recolour jitters the snow around (203,213,233)
    return m.colored & (r >= 195) & (r <= 210) & (g >= 205) & (g <= 220) & (b >= 225) & (b <= 240)


def snow_pvp(m):
    r, g, b = _rgb(m)
    s = m.colored & (r == 190) & (g == 203) & (b == 210)
    X, Y, Z = np.indices(s.shape)
    ring = (X <= 96) | (X >= 416) | (Y <= 137) | (Y >= 376)
    return s & ~(ring & (Z <= 52))          # leave the sky-box walls alone, only ground snow


def snow_battlefarm_snow(m):
    r, g, b = _rgb(m)
    return m.colored & (r == 221) & (g == 221) & (b == 221)


MAPS = {
    'battlefarm_snow': (snow_battlefarm_snow, dict(palette='pale', luma_max=222, coast_w=8, ribbon=0.3, zone_scale=1.0,
                                                   bias=0.68, soft=0.3, wind=0.4, foot_mode='top')),
    'battlefarm_winter': (snow_battlefarm, dict(palette='pale', luma_max=226, coast_w=9, ribbon=0.25, zone_scale=0.7, bias=0.68, soft=0.3)),
    'RoyalParadeSnowNight': (snow_royal, dict(palette='night', luma_max=214, coast_w=7, ribbon=0.2, zone_scale=1.4, bias=0.74, soft=0.25)),
    'ChristmasPVP': (snow_pvp, dict(palette='pale', luma_max=224, coast_w=8, ribbon=0.3, zone_scale=0.6, bias=0.74, soft=0.5)),
}

if __name__ == '__main__':
    key, src, dst = sys.argv[1:4]
    m, rep = vxl.load(src)
    assert rep.ok
    sel, kw = MAPS[key]
    n = repaint(m, sel(m), **kw)
    vxl.save(m, dst, force_bottom=False)
    print(key, 'repainted', n, 'voxels ->', dst)
