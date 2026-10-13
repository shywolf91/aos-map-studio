"""Preview renderers (numpy + Pillow). Purely visual QA - colours are file RGB, no game lighting.

top_down(vm)            overhead colour map with hillshade (z = 0 is top, so height = 63 - z)
isometric(vm, ...)      2:1 isometric cubes, painter's order resolved with a depth buffer;
                        view=0..3 rotates the map 90 deg so all four sides can be inspected.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from .vxl import VoxelMap, surface_mask


def _rgb(c):
    c = c.astype(np.uint32)
    return np.stack([(c >> 16) & 255, (c >> 8) & 255, c & 255], -1).astype(np.float32)


def top_down(vm: VoxelMap, crop=None, scale=1) -> Image.Image:
    solid = vm.solid
    top = np.argmax(solid, axis=2)                          # first solid z from top
    xs, ys = np.indices(top.shape)
    col = _rgb(vm.color[xs, ys, top])
    h = (63 - top).astype(np.float32)
    # simple hillshade from NW light: compare with neighbour heights
    gx = np.zeros_like(h); gy = np.zeros_like(h)
    gx[1:, :] = h[1:, :] - h[:-1, :]
    gy[:, 1:] = h[:, 1:] - h[:, :-1]
    shade = np.clip(1.0 + 0.10 * (gx + gy), 0.55, 1.25)
    img = np.clip(col * shade[..., None], 0, 255).astype(np.uint8).transpose(1, 0, 2)  # rows = y
    im = Image.fromarray(img, 'RGB')
    if crop:
        x0, y0, x1, y1 = crop
        im = im.crop((x0, y0, x1 + 1, y1 + 1))
    if scale != 1:
        im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    return im


def _sprite(s):
    """Pixel offsets for top / +y (left) / +x (right) faces of an iso cube of size s."""
    faces = {'top': [], 'left': [], 'right': []}
    for v in range(2 * s):
        for u in range(2 * s):
            cu, cv = u + 0.5, v + 0.5
            d = abs(cu - s)
            if cv < s / 2 - d / 2 or cv > 1.5 * s + (s - d) / 2:
                continue
            if cv <= s / 2 + (s - d) / 2:
                faces['top'].append((u, v))
            elif cu < s:
                faces['left'].append((u, v))
            else:
                faces['right'].append((u, v))
    return {k: np.array(v, np.int32) for k, v in faces.items()}


def isometric(vm: VoxelMap, crop=None, view=0, s=2, bg=(24, 26, 30), zmin_draw=0) -> Image.Image:
    solid, color = vm.solid, vm.color
    if crop:
        x0, y0, x1, y1 = crop
        solid = solid[x0:x1 + 1, y0:y1 + 1]
        color = color[x0:x1 + 1, y0:y1 + 1]
    solid = np.rot90(solid, view, axes=(0, 1))
    color = np.rot90(color, view, axes=(0, 1))
    X, Y, Z = solid.shape
    surf = surface_mask_any(solid)
    air_up = np.ones_like(solid); air_up[:, :, 1:] = ~solid[:, :, :-1]
    air_px = np.ones_like(solid); air_px[:-1] = ~solid[1:]
    air_py = np.ones_like(solid); air_py[:, :-1] = ~solid[:, 1:]
    vis = surf & (air_up | air_px | air_py)
    vis[:, :, :zmin_draw] = False
    x, y, z = np.nonzero(vis)
    h = (63 - z)
    sx = (x - y + Y) * s
    sy = ((x + y) * s) // 2 + (63 - h) * s
    depth = (x + y + h).astype(np.int32)
    rgb = _rgb(color[x, y, z])
    W = (X + Y + 2) * s
    H = ((X + Y) * s) // 2 + 64 * s + 2 * s
    sp = _sprite(s)
    pid, dep, cols = [], [], []
    for face, mul in (('top', 1.0), ('left', 0.80), ('right', 0.64)):
        offs = sp[face]
        px = (sx[:, None] + offs[None, :, 0]).ravel()
        py = (sy[:, None] + offs[None, :, 1]).ravel()
        pid.append(py.astype(np.int64) * W + px)
        dep.append(np.repeat(depth, len(offs)))
        cols.append(np.repeat(np.clip(rgb * mul, 0, 255).astype(np.uint8), len(offs), axis=0))
    pid = np.concatenate(pid); dep = np.concatenate(dep); cols = np.concatenate(cols)
    order = np.lexsort((dep, pid))
    pid, cols = pid[order], cols[order]
    last = np.ones(len(pid), bool)
    last[:-1] = pid[1:] != pid[:-1]
    img = np.empty((H * W, 3), np.uint8)
    img[:] = bg
    img[pid[last]] = cols[last]
    return Image.fromarray(img.reshape(H, W, 3), 'RGB')


def surface_mask_any(solid):
    """Surface test for display: like the file rule but map/crop edges count as AIR so cut faces show."""
    air = ~solid
    e = np.zeros_like(solid)
    e[:, :, 0] = True
    e[:, :, 1:] |= air[:, :, :-1]; e[:, :, :-1] |= air[:, :, 1:]
    e[1:] |= air[:-1]; e[:-1] |= air[1:]
    e[:, 1:] |= air[:, :-1]; e[:, :-1] |= air[:, 1:]
    e[0] = e[-1] = True
    e[:, 0] = e[:, -1] = True
    return solid & e


def contact_sheet(images, labels=None, pad=8, bg=(24, 26, 30)) -> Image.Image:
    from PIL import ImageDraw
    w = max(i.width for i in images); h = sum(i.height for i in images) + pad * (len(images) + 1) + 14 * len(images)
    sheet = Image.new('RGB', (w + 2 * pad, h), bg)
    d = ImageDraw.Draw(sheet)
    yy = pad
    for k, im in enumerate(images):
        if labels:
            d.text((pad, yy), labels[k], fill=(220, 220, 220))
            yy += 14
        sheet.paste(im, (pad, yy))
        yy += im.height + pad
    return sheet
