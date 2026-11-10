"""Numpy preview renders: label every output as a numpy preview, NOT a client capture.

Merged from hc/wkh/sph_render.py (topdown with relief shading, point-splat perspective `view` with optional fog)
and Bloomhop render.py. For isometric sheets and contact sheets use aosmap.render.

    python -m aosmap.kit.preview maps/<map>_v1 [--out renders_dir]
"""
from __future__ import annotations

import argparse
import glob
import os

import numpy as np
from PIL import Image, ImageDraw

from .codec import as_packed, surface_mask, unpack_rgb

LABEL = 'numpy preview - not a client capture'


def _label(im):
    d = ImageDraw.Draw(im)
    d.text((6, im.height - 14), LABEL, fill=(255, 255, 255))
    return im


def topdown(solid, color, scale=2, shade=True, crop=None, label=True):
    color = as_packed(color)
    top = np.argmax(solid, axis=2)
    xs, ys = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    rgb = unpack_rgb(color[xs, ys, top]).astype(float)
    if shade:
        h = 63 - top.astype(float)
        dx = h - np.roll(h, 1, 0)
        dy = h - np.roll(h, 1, 1)
        rgb *= (1 + np.clip((dx + dy) * 0.06, -0.35, 0.35))[..., None]
        rgb *= (0.86 + 0.14 * (h / 63.0))[..., None]
    im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8).transpose(1, 0, 2))
    if crop:
        im = im.crop(crop)
    if scale != 1:
        im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    return _label(im) if label else im


def _surface_points(solid, color, region=None):
    surf = surface_mask(solid)
    if region is not None:
        (x0, x1), (y0, y1) = region
        m = np.zeros_like(surf)
        m[x0:x1, y0:y1] = True
        surf &= m
    xs, ys, zs = np.nonzero(surf)
    rgb = unpack_rgb(color[xs, ys, zs]).astype(float)
    up = np.ones(len(xs), bool)
    up[zs > 0] = ~solid[xs[zs > 0], ys[zs > 0], zs[zs > 0] - 1]
    light = np.where(up, 1.0, 0.78)
    e = np.zeros(len(xs), bool)
    ok = xs < 511
    e[ok] = ~solid[xs[ok] + 1, ys[ok], zs[ok]]
    s = np.zeros(len(xs), bool)
    ok = ys < 511
    s[ok] = ~solid[xs[ok], ys[ok] + 1, zs[ok]]
    light = np.where(~up & e, 0.72, light)
    light = np.where(~up & s & ~e, 0.84, light)
    return xs, ys, zs, rgb * light[:, None]


def view(solid, color, cam, look, fov=60, size=(1280, 720), ortho=None, region=None, bg=(34, 30, 44), fog=None,
         fog_dist=(60, 200), label=True):
    """Camera cam=(x, y, h) looking at look=(x, y, h), h = 63 - z (height above the bottom)."""
    color = as_packed(color)
    W, H = size
    xs, ys, zs, rgb = _surface_points(solid, color, region)
    P = np.stack([xs + 0.5, ys + 0.5, 63 - zs + 0.5], 1).astype(float)
    cam = np.array(cam, float)
    look = np.array(look, float)
    f = look - cam
    f /= np.linalg.norm(f)
    r = np.cross([0, 0, 1.0], f)
    r /= np.linalg.norm(r)
    u = np.cross(f, r)
    d = P - cam
    zc, xc, yc = d @ f, d @ r, d @ u
    keep = zc > 0.5
    xc, yc, zc, rgb = xc[keep], yc[keep], zc[keep], rgb[keep]
    if ortho:
        k = (H / 2) / ortho
        sx, sy = W / 2 + xc * k, H / 2 - yc * k
        size_px = np.full(len(zc), max(1, int(np.ceil(k * 1.15))))
    else:
        fpx = (H / 2) / np.tan(np.radians(fov) / 2)
        sx, sy = W / 2 + xc / zc * fpx, H / 2 - yc / zc * fpx
        size_px = np.ceil(fpx * 1.25 / zc).astype(int)
    if fog is not None:
        t = np.clip((zc - fog_dist[0]) / (fog_dist[1] - fog_dist[0]), 0, 1)[:, None]
        rgb = rgb * (1 - t) + np.array(fog, float) * t
    size_px = np.clip(size_px, 1, 40)
    inb = (sx > -40) & (sx < W + 40) & (sy > -40) & (sy < H + 40)
    sx, sy, zc, rgb, size_px = sx[inb], sy[inb], zc[inb], rgb[inb], size_px[inb]
    img = np.zeros((H, W, 3))
    img[:] = bg
    zbuf = np.full((H, W), np.inf)
    for k in np.unique(size_px):
        m = size_px == k
        bx = np.floor(sx[m] - k / 2).astype(int)
        by = np.floor(sy[m] - k / 2).astype(int)
        zz, cc = zc[m], rgb[m]
        for dx in range(k):
            for dy in range(k):
                px, py = bx + dx, by + dy
                ok = (px >= 0) & (px < W) & (py >= 0) & (py < H)
                px2, py2, z2, c2 = px[ok], py[ok], zz[ok], cc[ok]
                o = np.argsort(-z2, kind='stable')
                px2, py2, z2, c2 = px2[o], py2[o], z2[o], c2[o]
                closer = z2 < zbuf[py2, px2]
                px2, py2, z2, c2 = px2[closer], py2[closer], z2[closer], c2[closer]
                zbuf[py2, px2] = z2
                img[py2, px2] = c2
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    return _label(im) if label else im


STANDARD_SHOTS = [
    ('overview_sw', dict(cam=(-60, 600, 190), look=(256, 256, 10), fov=46, size=(1600, 1000))),
    ('overview_ne', dict(cam=(580, -80, 190), look=(256, 256, 10), fov=46, size=(1600, 1000))),
    ('blue_spawn_from_platform_edge', dict(cam=(206, 256, 64), look=(118, 256, 18), fov=66, size=(1400, 800))),
    ('red_spawn_from_platform_edge', dict(cam=(305, 256, 64), look=(394, 256, 18), fov=66, size=(1400, 800))),
    ('blue_front_eye_level', dict(cam=(120, 256, 22), look=(256, 256, 30), fov=66, size=(1400, 800))),
]


def render_dir(map_dir, out=None, shots=STANDARD_SHOTS, fog=None):
    from .codec import decode
    vx = sorted(glob.glob(os.path.join(map_dir, '*.vxl')))[0]
    solid, color, _ = decode(open(vx, 'rb').read())
    out = out or os.path.join(map_dir, 'renders')
    os.makedirs(out, exist_ok=True)
    topdown(solid, color).save(os.path.join(out, '01_top_down.png'))
    for name, kw in shots:
        view(solid, color, fog=fog, **kw).save(os.path.join(out, name + '.png'))
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('mapdir')
    ap.add_argument('--out')
    a = ap.parse_args()
    print('numpy previews in', render_dir(a.mapdir, a.out))
