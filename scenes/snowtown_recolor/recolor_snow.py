"""SnowTown snow - artistic repaint. Only voxels that are exactly RGB(221,221,221) change colour;
no voxel is added or removed. Every output channel is <= 221 (OpenSpades glare limit).

The snow is "lit" by baked geometry: sun shading from the terrain relief, ambient-occlusion
shadows in hollows and against walls/props, wind-sculpted ripples (sastrugi), flowing
contour ribbons that follow the coastline (like carved ice), drifting colour zones
(pearl / blush / lavender / mint / glacier cyan), frost sparkle and cold shadow tones.

usage: python recolor_snow.py <in.vxl> <out.vxl>      deterministic (fixed seed)
"""
import sys
sys.path.insert(0, __file__.rsplit('scenes', 1)[0])
import numpy as np
from scipy import ndimage as ndi
from aosmap import vxl

CAP = 221
rng = np.random.default_rng(7511)


def noise(sigma, shape=(512, 512)):
    n = ndi.gaussian_filter(rng.standard_normal(shape), sigma, mode='wrap')
    return (n - n.mean()) / n.std()


def ramp(t, stops):
    """piecewise-linear colour ramp; t in [0,1]; stops = [(pos,(r,g,b)),...]"""
    pos = np.array([p for p, _ in stops])
    cols = np.array([c for _, c in stops], float)
    return np.stack([np.interp(t, pos, cols[:, i]) for i in range(3)], -1)


def main(src, dst):
    m, rep = vxl.load(src)
    assert rep.ok
    c = m.color
    r, g, b = (c >> 16) & 255, (c >> 8) & 255, c & 255
    snow = m.colored & (r == 221) & (g == 221) & (b == 221)
    xs, ys, zs = np.nonzero(snow)

    # ---- terrain relief (height of the highest solid voxel per column) ----
    H = (63 - np.argmax(m.solid, axis=2)).astype(float)
    Hs = ndi.gaussian_filter(H, 1.2)
    gx, gy = np.gradient(Hs)
    sun = np.array([-0.55, -0.55])                         # light from the north-west
    lam = -(gx * sun[0] + gy * sun[1])                     # >0 faces the sun
    lam = np.tanh(lam * 2.2)
    hollow = ndi.gaussian_filter(H, 7) - H                  # >0 in pits
    hollow = np.tanh(hollow / 2.0)
    # props / walls: distance from non-snow solid (rises above the snow) -> contact shadow
    foot = snow.any(axis=2)
    prop = (H > ndi.maximum_filter(np.where(foot, H, 0), 5) + 0.5) & ~foot | \
           ((~foot) & (H > 0) & (ndi.binary_dilation(foot, iterations=3)) & (H > 55))
    dprop = ndi.distance_transform_edt(~prop)
    contact = np.exp(-dprop / 3.5)

    # ---- coastline: ribbons + blend to glacier ----
    dist = ndi.distance_transform_edt(foot)
    warp = noise(14) * 4.0 + noise(5) * 1.2
    ribbon = 0.5 + 0.5 * np.sin((dist + warp) * 0.62)       # flowing carved-ice contours
    ribbon *= np.clip(dist / 8, 0, 1)                       # calm at the very centre
    coast = ndi.gaussian_filter(np.clip(1 - dist / 26.0, 0, 1) ** 1.3, 2)

    # ---- wind sculpting: elongated ripples across the whole island ----
    wz = ndi.gaussian_filter(rng.standard_normal((512, 512)), (2.2, 9.0), mode='wrap')
    wz = (wz - wz.mean()) / wz.std()
    wz2 = ndi.gaussian_filter(rng.standard_normal((512, 512)), (4.5, 20.0), mode='wrap')
    wz2 = (wz2 - wz2.mean()) / wz2.std()
    ripple = np.tanh(wz * 0.9 + wz2 * 0.6)

    # ---- colour zones ----
    zA, zB, zC = noise(46), noise(30), noise(16)
    z1, z2 = noise(60), noise(60)

    # ---- per-voxel exposure ----
    solid = m.solid
    def nb(dx, dy, dz):
        o = np.zeros_like(solid)
        sx = slice(max(dx, 0), 512 + min(dx, 0)); tx = slice(max(-dx, 0), 512 + min(-dx, 0))
        sy = slice(max(dy, 0), 512 + min(dy, 0)); ty = slice(max(-dy, 0), 512 + min(-dy, 0))
        sz = slice(max(dz, 0), 64 + min(dz, 0)); tz = slice(max(-dz, 0), 64 + min(-dz, 0))
        o[tx, ty, tz] = solid[sx, sy, sz]
        return o
    top_open = ~nb(0, 0, -1)
    top_open[:, :, 0] = True
    faceN = ~nb(0, -1, 0); faceW = ~nb(-1, 0, 0)            # faces lit by the NW sun
    faceS = ~nb(0, 1, 0);  faceE = ~nb(1, 0, 0)

    X, Y, Z = xs, ys, zs
    L = 0.0 * X.astype(float)
    L += 0.55 * lam[X, Y]
    L -= 0.55 * hollow[X, Y]
    L -= 0.75 * contact[X, Y]
    L += 0.30 * ripple[X, Y]
    L -= 0.35 * ribbon[X, Y] * (0.4 + coast[X, Y])
    L += 0.12 * np.clip((Z - 56) / 6.0, -1, 1)
    L += 0.18 * (faceN[X, Y, Z] | faceW[X, Y, Z]) * ~top_open[X, Y, Z]
    L -= 0.45 * (faceS[X, Y, Z] | faceE[X, Y, Z]) * ~top_open[X, Y, Z]
    L += rng.normal(0, 0.06, len(X))
    t = np.clip(0.62 + 0.52 * L, 0, 1)

    # hue zones: choose which "family" the lit/shadow ramps lean toward
    h_blush = np.clip(z1[X, Y] * 0.9 + zC[X, Y] * 0.3, 0, 1)        # warm pink pearl
    h_mint = np.clip(z2[X, Y] * 0.9 + zB[X, Y] * 0.3, 0, 1)         # aqua mint
    h_lav = np.clip(-z1[X, Y] * 0.7 + zA[X, Y] * 0.5, 0, 1)         # lavender

    cool = ramp(t, [(0.00, (78, 104, 176)), (0.18, (112, 143, 205)), (0.38, (150, 182, 221)),
                    (0.60, (190, 214, 221)), (0.80, (212, 221, 221)), (1.00, (221, 221, 214))])
    blush = ramp(t, [(0.00, (118, 98, 170)), (0.25, (158, 140, 205)), (0.50, (200, 188, 221)),
                     (0.75, (221, 208, 221)), (1.00, (221, 218, 205))])
    mint = ramp(t, [(0.00, (60, 120, 168)), (0.25, (96, 160, 200)), (0.50, (150, 205, 221)),
                    (0.75, (190, 221, 221)), (1.00, (214, 221, 216))])
    lav = ramp(t, [(0.00, (92, 92, 178)), (0.25, (128, 128, 210)), (0.55, (176, 178, 221)),
                   (0.80, (205, 208, 221)), (1.00, (221, 219, 221))])
    col = cool
    for w, fam in ((0.75 * h_blush, blush), (0.7 * h_mint, mint), (0.8 * h_lav, lav)):
        col = col + (fam - col) * w[:, None]

    # coast: deep glacier cyan so the island melts into the surrounding ice
    ice = ramp(t, [(0.0, (40, 100, 176)), (0.4, (80, 160, 215)), (0.75, (140, 205, 221)), (1.0, (196, 221, 221))])
    col = col + (ice - col) * (0.8 * coast[X, Y])[:, None]

    # frost sparkle: sparse bright crystals, and a few cold cracks
    u = rng.random(len(X))
    sp = (u > 0.985) & top_open[X, Y, Z]
    col[sp] = col[sp] * 0.35 + np.array([221, 221, 221]) * 0.65
    cr = (u < 0.012) & top_open[X, Y, Z]
    col[cr] = col[cr] * 0.78 + np.array([70, 110, 190]) * 0.22
    col += rng.normal(0, 1.8, (len(X), 1))

    col = np.clip(np.rint(col), 0, CAP).astype(np.uint32)
    old = c[snow]
    c[xs, ys, zs] = (old & 0xFF000000) | (col[:, 0] << 16) | (col[:, 1] << 8) | col[:, 2]
    vxl.save(m, dst, force_bottom=False)
    print('recoloured', len(xs), 'voxels ->', dst)


if __name__ == '__main__':
    main(*sys.argv[1:3])
