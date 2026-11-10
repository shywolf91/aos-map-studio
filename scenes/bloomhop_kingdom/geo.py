"""World container + primitives. Arrays are indexed [x, y, z]; z = 0 is the sky top, z = 63 the bottom."""
import numpy as np

X, Y, Z = 512, 512, 64


def clamp8(c):
    return tuple(int(max(0, min(255, round(v)))) for v in c)


def mix(a, b, t):
    return tuple(float(a[i]) + (float(b[i]) - float(a[i])) * t for i in range(3))


def shade(c, f):
    return clamp8((c[0] * f, c[1] * f, c[2] * f))


class World:
    def __init__(self):
        self.S = np.zeros((X, Y, Z), bool)
        self.C = np.zeros((X, Y, Z, 3), np.uint8)
        self.H = np.full((X, Y), 63, np.int16)  # terrain top (filled to 63)
        self.keep = np.zeros((X, Y), np.uint8)  # vegetation keep-out flags
        self.glow = []  # (x, y, z, rgb) glow sources
        self.expect_floating = []  # bounding boxes of intended floating pieces
        self.nolight = np.zeros((X, Y, Z), bool)  # voxels excluded from lighting pass (glow sources)

    # ---- basic setters --------------------------------------------------
    def set(self, x, y, z, c):
        if 0 <= x < X and 0 <= y < Y and 0 <= z < Z:
            self.S[x, y, z] = True
            self.C[x, y, z] = c

    def clear(self, x, y, z):
        if 0 <= x < X and 0 <= y < Y and 0 <= z < Z:
            self.S[x, y, z] = False

    def box(self, x0, x1, y0, y1, z0, z1, c=None, air=False):
        """Inclusive box. c may be a colour tuple or a function (xs, ys, zs) -> (n,3) array."""
        x0, x1 = max(0, min(x0, x1)), min(X - 1, max(x0, x1))
        y0, y1 = max(0, min(y0, y1)), min(Y - 1, max(y0, y1))
        z0, z1 = max(0, min(z0, z1)), min(Z - 1, max(z0, z1))
        if x0 > x1 or y0 > y1 or z0 > z1:
            return
        sl = (slice(x0, x1 + 1), slice(y0, y1 + 1), slice(z0, z1 + 1))
        if air:
            self.S[sl] = False
            return
        self.S[sl] = True
        if callable(c):
            xs, ys, zs = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1), np.arange(z0, z1 + 1), indexing='ij')
            self.C[sl] = c(xs, ys, zs)
        else:
            self.C[sl] = c

    def mask_fill(self, m, c):
        """m: bool [X,Y,Z] mask; c: tuple or array broadcastable to m.sum()x3."""
        self.S[m] = True
        self.C[m] = c

    def column_top(self, x, y, zmin=0):
        """Topmost solid z at or below zmin."""
        col = self.S[x, y, zmin:]
        idx = np.argmax(col)
        return zmin + idx if col[idx] else 64

    def ellipsoid(self, cx, cy, cz, rx, ry, rz, colfn, hollow=0.0):
        x0, x1 = int(np.floor(cx - rx)), int(np.ceil(cx + rx))
        y0, y1 = int(np.floor(cy - ry)), int(np.ceil(cy + ry))
        z0, z1 = int(np.floor(cz - rz)), int(np.ceil(cz + rz))
        x0, y0, z0 = max(x0, 0), max(y0, 0), max(z0, 0)
        x1, y1, z1 = min(x1, X - 1), min(y1, Y - 1), min(z1, Z - 1)
        if x0 > x1 or y0 > y1 or z0 > z1:
            return None
        xs, ys, zs = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1), np.arange(z0, z1 + 1), indexing='ij')
        d = ((xs - cx) / max(rx, .5)) ** 2 + ((ys - cy) / max(ry, .5)) ** 2 + ((zs - cz) / max(rz, .5)) ** 2
        m = d <= 1.0
        if hollow > 0:
            m &= d >= hollow
        sl = (slice(x0, x1 + 1), slice(y0, y1 + 1), slice(z0, z1 + 1))
        sub = self.S[sl]
        sub[m] = True
        cs = self.C[sl]
        cs[m] = colfn(xs[m], ys[m], zs[m], d[m])
        return (x0, y0, z0, m)
