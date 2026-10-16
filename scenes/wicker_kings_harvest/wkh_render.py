"""Preview renders (numpy point-splat; NOT a game client)."""
from __future__ import annotations

import numpy as np
from PIL import Image

from wkh_core import surface_mask, unpack_rgb


def topdown(solid, color, scale=2, shade=True, crop=None):
    top = np.argmax(solid, axis=2)
    xs, ys = np.meshgrid(np.arange(512), np.arange(512), indexing='ij')
    rgb = unpack_rgb(color[xs, ys, top]).astype(float)
    if shade:
        h = 63 - top.astype(float)
        dx = h - np.roll(h, 1, 0); dy = h - np.roll(h, 1, 1)
        light = 1 + np.clip((dx + dy) * 0.06, -0.35, 0.35)
        rgb *= light[..., None]
        rgb *= (0.86 + 0.14 * (h / 63.0))[..., None]
    img = np.clip(rgb, 0, 255).astype(np.uint8).transpose(1, 0, 2)  # rows = y
    im = Image.fromarray(img)
    if crop:
        im = im.crop(crop)
    if scale != 1:
        im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    return im


def _surface_points(solid, color, region=None):
    surf = surface_mask(solid)
    if region is not None:
        (x0, x1), (y0, y1) = region
        m = np.zeros_like(surf); m[x0:x1, y0:y1] = True; surf &= m
    xs, ys, zs = np.nonzero(surf)
    rgb = unpack_rgb(color[xs, ys, zs]).astype(float)
    # face lighting: top exposure brightens, west/north faces mid, others darker
    up = np.ones(len(xs), bool); up[zs > 0] = ~solid[xs[zs > 0], ys[zs > 0], zs[zs > 0] - 1]
    light = np.where(up, 1.0, 0.78)
    e = np.zeros(len(xs), bool)
    ok = xs < 511; e[ok] = ~solid[xs[ok] + 1, ys[ok], zs[ok]]
    s = np.zeros(len(xs), bool)
    ok = ys < 511; s[ok] = ~solid[xs[ok], ys[ok] + 1, zs[ok]]
    light = np.where(~up & e, 0.72, light)
    light = np.where(~up & s & ~e, 0.84, light)
    return xs, ys, zs, rgb * light[:, None]


def view(solid, color, cam, look, fov=60, size=(1280, 720), ortho=None, region=None, bg=(34, 30, 44),
         fog=None, fog_dist=(60, 200)):
    """Render from camera position cam=(x,y,z_up) looking at look=(x,y,z_up) where z_up = 63 - z.
    ortho: if given, orthographic half-height in voxels."""
    W, H = size
    xs, ys, zs, rgb = _surface_points(solid, color, region)
    P = np.stack([xs + 0.5, ys + 0.5, 63 - zs + 0.5], 1).astype(float)
    cam = np.array(cam, float); look = np.array(look, float)
    f = look - cam; f /= np.linalg.norm(f)
    r = np.cross([0, 0, 1.0], f); r /= np.linalg.norm(r)   # map axes are left-handed (y points south)
    u = np.cross(f, r)
    d = P - cam
    zc = d @ f; xc = d @ r; yc = d @ u
    keep = zc > 0.5
    xc, yc, zc, rgb = xc[keep], yc[keep], zc[keep], rgb[keep]
    if ortho:
        k = (H / 2) / ortho
        sx = W / 2 + xc * k; sy = H / 2 - yc * k
        size_px = np.full(len(zc), max(1, int(np.ceil(k * 1.15))))
    else:
        fpx = (H / 2) / np.tan(np.radians(fov) / 2)
        sx = W / 2 + xc / zc * fpx; sy = H / 2 - yc / zc * fpx
        size_px = np.ceil(fpx * 1.25 / zc).astype(int)
    if fog is not None:
        t = np.clip((zc - fog_dist[0]) / (fog_dist[1] - fog_dist[0]), 0, 1)[:, None]
        rgb = rgb * (1 - t) + np.array(fog, float) * t
    size_px = np.clip(size_px, 1, 40)
    inb = (sx > -40) & (sx < W + 40) & (sy > -40) & (sy < H + 40)
    sx, sy, zc, rgb, size_px = sx[inb], sy[inb], zc[inb], rgb[inb], size_px[inb]
    img = np.zeros((H, W, 3)); img[:] = bg
    zbuf = np.full((H, W), np.inf)
    order = np.argsort(-zc)
    sx, sy, zc, rgb, size_px = sx[order], sy[order], zc[order], rgb[order], size_px[order]
    for k in np.unique(size_px):
        m = size_px == k
        bx = np.floor(sx[m] - k / 2).astype(int); by = np.floor(sy[m] - k / 2).astype(int)
        zz = zc[m]; cc = rgb[m]
        for dx in range(k):
            for dy in range(k):
                px = bx + dx; py = by + dy
                ok = (px >= 0) & (px < W) & (py >= 0) & (py < H)
                px2, py2, z2, c2 = px[ok], py[ok], zz[ok], cc[ok]
                # nearest wins: sort by depth descending so nearest written last
                o = np.argsort(-z2, kind='stable')
                px2, py2, z2, c2 = px2[o], py2[o], z2[o], c2[o]
                closer = z2 < zbuf[py2, px2]
                px2, py2, z2, c2 = px2[closer], py2[closer], z2[closer], c2[closer]
                zbuf[py2, px2] = z2  # last write (nearest) wins for duplicates
                img[py2, px2] = c2
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


SHOTS = [   # name, camera kwargs (cam / look are (x, y, height) with height = 63 - z)
    ('02_overview_sw', dict(cam=(-60, 560, 170), look=(256, 256, 10), fov=48, size=(1600, 1000))),
    ('03_overview_ne', dict(cam=(600, -40, 170), look=(256, 270, 10), fov=48, size=(1600, 1000))),
    ('04_clearing_to_wicker_king', dict(cam=(256, 250, 30), look=(250, 100, 22), fov=55, size=(1280, 720))),
    ('05_tower_zone_to_blue_gate', dict(cam=(200, 256, 28), look=(118, 256, 22), fov=60, size=(1280, 720))),
    ('06_blue_barn', dict(cam=(135, 250, 34), look=(98, 203, 24), fov=60, size=(1280, 720))),
    ('07_grin_bridges', dict(cam=(256, 300, 44), look=(256, 380, 14), fov=65, size=(1280, 720))),
    ('08_west_pier_cliffs', dict(cam=(20, 330, 16), look=(48, 300, 6), fov=60, size=(1280, 720))),
    ('09_eye_walkway', dict(cam=(150, 214, 30), look=(196, 160, 12), fov=65, size=(1280, 720))),
    ('10_stem_from_sea', dict(cam=(150, 20, 40), look=(235, 90, 25), fov=60, size=(1280, 720))),
]


if __name__ == '__main__':
    import os
    import sys
    from wkh_core import read_vxl
    out = sys.argv[1]
    rd = os.path.join(out, 'renders')
    os.makedirs(rd, exist_ok=True)
    s, c, _ = read_vxl(open(os.path.join(out, 'wicker_kings_harvest.vxl'), 'rb').read())
    topdown(s, c, scale=2).save(os.path.join(rd, '01_top_down.png'))
    for name, kw in SHOTS:
        view(s, c, **kw).save(os.path.join(rd, name + '.png'))
    print('renders in', rd)
