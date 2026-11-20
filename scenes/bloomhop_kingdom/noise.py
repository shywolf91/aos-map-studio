import numpy as np


def value_noise(shape, scale, seed):
    """Smooth 2D value noise in [-1,1] over an array of `shape`, feature size `scale` voxels."""
    rng = np.random.default_rng(seed)
    gx = int(np.ceil(shape[0] / scale)) + 3
    gy = int(np.ceil(shape[1] / scale)) + 3
    g = rng.uniform(-1, 1, (gx, gy))
    xs = np.arange(shape[0]) / scale
    ys = np.arange(shape[1]) / scale
    xi = xs.astype(int); yi = ys.astype(int)
    xf = xs - xi; yf = ys - yi
    xf = xf * xf * (3 - 2 * xf); yf = yf * yf * (3 - 2 * yf)
    a = g[xi][:, yi]; b = g[xi + 1][:, yi]; c = g[xi][:, yi + 1]; d = g[xi + 1][:, yi + 1]
    xf = xf[:, None]; yf = yf[None, :]
    return (a * (1 - xf) + b * xf) * (1 - yf) + (c * (1 - xf) + d * xf) * yf


def fbm(shape, scale, seed, octaves=4):
    out = np.zeros(shape); amp = 1.0; tot = 0
    for o in range(octaves):
        out += amp * value_noise(shape, scale / (2 ** o), seed + 101 * o)
        tot += amp; amp *= 0.5
    return out / tot
