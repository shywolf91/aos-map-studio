"""SnowTown snow recolour: change ONLY the colour of voxels that are exactly RGB(221,221,221).
No voxel is added or removed. Every output channel is <= 221 (OpenSpades glare limit).

usage: python recolor_snow.py <in.vxl> <out.vxl>
Deterministic (fixed seed).
"""
import sys
sys.path.insert(0, __file__.rsplit('scenes', 1)[0])
import numpy as np
from scipy import ndimage as ndi
from aosmap import vxl

SNOW = (221, 221, 221)
CAP = 221
rng = np.random.default_rng(7511)


def smooth_noise(shape2d, sigma):
    n = ndi.gaussian_filter(rng.standard_normal(shape2d), sigma, mode='wrap')
    return (n - n.mean()) / n.std()


def main(src, dst):
    m, rep = vxl.load(src)
    assert rep.ok
    c = m.color
    r, g, b = (c >> 16) & 255, (c >> 8) & 255, c & 255
    snow = m.colored & (r == SNOW[0]) & (g == SNOW[1]) & (b == SNOW[2])
    xs, ys, zs = np.nonzero(snow)

    # footprint of the snow island (top-view) -> distance to its coast, smoothed
    foot = snow.any(axis=2)
    dist = ndi.distance_transform_edt(foot)
    edge = np.clip(1 - dist / 22.0, 0, 1) ** 1.5          # 1 at coast, 0 inland
    edge = ndi.gaussian_filter(edge, 3)

    big = smooth_noise((512, 512), 38)                      # large drifts
    mid = smooth_noise((512, 512), 11)                      # medium swells
    drift = np.clip(0.5 + 0.30 * big + 0.15 * mid, 0, 1)    # 0 = cool, 1 = warm white

    # exposure: slightly deeper tone on voxels that only show side faces (gives relief)
    top_open = np.zeros_like(snow)
    top_open[:, :, 1:] = ~m.solid[:, :, :-1]
    top_open[:, :, 0] = True

    warm = np.array([221, 219, 213], float)    # soft warm white
    cool = np.array([203, 214, 221], float)    # pale blue-grey
    ice = np.array([170, 203, 221], float)     # glacier blue, echoes the surrounding ice

    d = drift[xs, ys][:, None]
    e = edge[xs, ys][:, None]
    col = cool + (warm - cool) * d
    col = col + (ice - col) * (0.85 * e)
    # height: lower snow a touch cooler/denser, higher snow lighter
    h = ((62 - zs) / 10.0).clip(0, 1)[:, None]
    col = col - (1 - h) * np.array([4, 2, 0.0])
    side = (~top_open[xs, ys, zs])[:, None]
    col = col - side * np.array([9, 7, 4.0])
    col = col + rng.normal(0, 1.4, (len(xs), 1))            # fine, low-contrast grain
    col = np.clip(np.rint(col), 0, CAP).astype(np.uint32)

    old = c[snow]
    c[xs, ys, zs] = (old & 0xFF000000) | (col[:, 0] << 16) | (col[:, 1] << 8) | col[:, 2]
    vxl.save(m, dst, force_bottom=False)
    print('recoloured', len(xs), 'voxels ->', dst)


if __name__ == '__main__':
    main(*sys.argv[1:3])
