"""Preview renders (numpy, not a game client): annotated top-down and oblique views.

The Babel platform is drawn as the server stamps it (x 206-305, y 240-271, z 1, cyan).
"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ww_core import W, D, surface_mask, top_z

PLAT = (206, 305, 240, 271, 1)


def stamp_platform(solid, colors):
    s = solid.copy()
    c = colors.copy()
    x0, x1, y0, y1, z = PLAT
    s[x0:x1 + 1, y0:y1 + 1, z] = True
    c[x0:x1 + 1, y0:y1 + 1, z] = (0, 235, 235)
    return s, c


def font(sz):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/dejavu/DejaVuSans.ttf'):
        try:
            return ImageFont.truetype(p, sz)
        except OSError:
            pass
    return ImageFont.load_default()


def top_down(solid, colors, path, scale=2, annotate=True):
    tz = top_z(solid)
    xs = np.arange(W)[:, None]
    ys = np.arange(W)[None, :]
    img = colors[xs, ys, tz].astype(np.float32)
    h = (63 - tz).astype(np.float32)
    gx = np.gradient(h, axis=0)
    gy = np.gradient(h, axis=1)
    sh = np.clip(1 + (-gx - gy) * 0.07, 0.65, 1.3)
    img *= sh[..., None]
    img = img.clip(0, 255).astype(np.uint8).transpose(1, 0, 2)
    im = Image.fromarray(img).resize((W * scale, W * scale), Image.NEAREST)
    if annotate:
        d = ImageDraw.Draw(im)
        f = font(13)
        s = scale
        d.rectangle([206 * s, 240 * s, 306 * s - 1, 272 * s - 1], outline=(0, 255, 255), width=2)
        for (bx, lab) in ((118, 'blue spawn'), (394, 'red spawn')):
            d.rectangle([(bx - 20) * s, 236 * s, (bx + 21) * s - 1, 277 * s - 1], outline=(255, 250, 200), width=1)
            d.text(((bx - 20) * s, 278 * s + 2), lab, fill=(255, 250, 220), font=f)
        d.rectangle([128 * s, 240 * s, 212 * s - 1, 273 * s - 1], outline=(110, 160, 255), width=1)
        d.rectangle([301 * s, 240 * s, 385 * s - 1, 273 * s - 1], outline=(255, 120, 120), width=1)
        d.text((206 * s, 226 * s), 'script platform (z 1)', fill=(0, 255, 255), font=f)
        d.text((8, 8), 'Witchwood Isles - top-down (preview render, not a game client)', fill=(235, 235, 235), font=f)
        d.text((8, 26), 'blue/red outline: tower build-ban corridors; white: stock +-20 spawn squares', fill=(200, 200, 200), font=f)
    im.save(path)
    return im


def oblique(solid, colors, path, elev_deg=42, yaw_deg=0, crop=None, scale=2.0, zscale=1.0, bg=(28, 34, 44),
            title=None):
    """Painter's-algorithm voxel splat. View from +y (south) rotated by yaw about the map centre."""
    surf = surface_mask(solid)
    if crop:
        x0, x1, y0, y1 = crop
        m = np.zeros_like(surf)
        m[x0:x1 + 1, y0:y1 + 1] = True
        surf &= m
    P = np.argwhere(surf)
    col = colors[P[:, 0], P[:, 1], P[:, 2]].astype(np.float32)
    # face lighting: top faces (air above) bright, else side
    above_air = np.ones(len(P), bool)
    zz = P[:, 2]
    k = zz > 0
    above_air[k] = ~solid[P[k, 0], P[k, 1], zz[k] - 1]
    col[~above_air] *= 0.72
    e = np.radians(elev_deg)
    a = np.radians(yaw_deg)
    cx = cy = 256.0
    X = P[:, 0] + 0.5 - cx
    Y = P[:, 1] + 0.5 - cy
    Z = (P[:, 2] + 0.5) * zscale
    Xr = X * np.cos(a) - Y * np.sin(a)
    Yr = X * np.sin(a) + Y * np.cos(a)
    u = Xr
    v = Yr * np.sin(e) + Z * np.cos(e)
    depth = Yr * np.cos(e) - Z * np.sin(e)
    # distance fog toward bg for depth cue
    dn = (depth - depth.min()) / max(1e-6, depth.max() - depth.min())
    col = col * (0.55 + 0.45 * dn[:, None]) + np.array(bg, np.float32) * (0.45 - 0.45 * dn[:, None])
    umin, umax = u.min(), u.max()
    vmin, vmax = v.min(), v.max()
    Wp = int((umax - umin + 3) * scale)
    Hp = int((vmax - vmin + 3) * scale)
    img = np.zeros((Hp, Wp, 3), np.uint8)
    img[:] = bg
    zbuf = np.full(Hp * Wp, -1e9, np.float32)
    cbuf = np.zeros((Hp * Wp, 3), np.uint8)
    pu = (u - umin + 1) * scale
    pv = (v - vmin + 1) * scale
    foot = int(np.ceil(scale * 1.15)) + 1
    vfoot = int(np.ceil(scale * (np.sin(e) + np.cos(e) * zscale) * 1.05)) + 1
    c8 = col.clip(0, 255).astype(np.uint8)
    for du in range(foot):
        for dv in range(vfoot):
            iu = (pu - scale / 2 + du).astype(np.int64)
            iv = (pv - scale / 2 + dv).astype(np.int64)
            ok = (iu >= 0) & (iu < Wp) & (iv >= 0) & (iv < Hp)
            lin = iv[ok] * Wp + iu[ok]
            dp = depth[ok].astype(np.float32)
            order = np.lexsort((dp, lin))
            lin_s = lin[order]
            last = np.r_[lin_s[1:] != lin_s[:-1], True]
            li = lin_s[last]
            di = dp[order][last]
            ci = c8[ok][order][last]
            better = di > zbuf[li]
            zbuf[li[better]] = di[better]
            cbuf[li[better]] = ci[better]
    m = zbuf > -1e9
    img.reshape(-1, 3)[m] = cbuf[m]
    im = Image.fromarray(img)
    if title:
        d = ImageDraw.Draw(im)
        d.text((10, 8), title, fill=(235, 235, 235), font=font(14))
    im.save(path)
    return im
