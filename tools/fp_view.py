"""First-person preview renderer (numpy ray marcher) - approximates what a 0.75 client shows: file colours, simple
face shading (top brightest, then x faces, y faces, undersides), linear fog to the map's fog colour at the client
render distance (~128 voxels), the stock Babel platform drawn in. Not a client capture: no models, no lighting,
no client-side ambient occlusion. Coordinates: AoS x, y, z with z = 0 the sky; eye z = floor z - 2.4.

Usage: python tools/fp_view.py <map.vxl> <out.png> eye_x eye_y eye_z look_x look_y look_z [--fog r g b] [--babel]
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aosmap.vxl import load                                                    # noqa: E402

SHADE = {'top': 1.0, 'x': 0.84, 'y': 0.72, 'under': 0.55}


def render(vm, eye, look, size=(960, 540), fov=75.0, fog=(152, 174, 168), dist=128.0, step=0.12, babel=False):
    solid = vm.solid.copy()
    color = vm.color.copy()
    if babel:
        solid[206:306, 240:272, 1] = True
        color[206:306, 240:272, 1] = (0x80 << 24) | (0 << 16) | (255 << 8) | 255
    W, H = size
    eye = np.array(eye, float); look = np.array(look, float)
    fwd = look - eye; fwd /= np.linalg.norm(fwd)
    up_world = np.array([0.0, 0.0, -1.0])                                          # z down
    right = np.cross(fwd, up_world); right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    t = np.tan(np.radians(fov) / 2)
    u = (np.arange(W) + 0.5) / W * 2 - 1
    v = (np.arange(H) + 0.5) / H * 2 - 1
    U, V = np.meshgrid(u * t, -v * t * H / W)
    d = fwd[None, None] + U[..., None] * right[None, None] + V[..., None] * up[None, None]
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    d = d.reshape(-1, 3)
    n = len(d)
    out = np.empty((n, 3), np.float32); out[:] = fog
    alive = np.ones(n, bool)
    prev = np.floor(np.repeat(eye[None], n, 0)).astype(int)
    fogc = np.array(fog, np.float32)
    for k in range(1, int(dist / step) + 1):
        idx = np.nonzero(alive)[0]
        if not len(idx):
            break
        s = k * step
        p = eye[None] + d[idx] * s
        c = np.floor(p).astype(int)
        x, y, z = c[:, 0], c[:, 1], c[:, 2]
        sky = z < 0
        oob = (x < 0) | (x > 511) | (y < 0) | (y > 511)
        zc = np.clip(z, 0, 63)
        hit = ~sky & ~oob & solid[np.clip(x, 0, 511), np.clip(y, 0, 511), zc]
        hit |= ~oob & (z >= 63)
        if hit.any():
            hi = idx[hit]
            cx, cy, cz = np.clip(x[hit], 0, 511), np.clip(y[hit], 0, 511), np.clip(z[hit], 0, 63)
            col = color[cx, cy, cz].astype(np.uint32)
            rgb = np.stack([(col >> 16) & 255, (col >> 8) & 255, col & 255], -1).astype(np.float32)
            pv = prev[hi]
            dz = cz - pv[:, 2]; dx = cx - pv[:, 0]
            sh = np.where(dz > 0, SHADE['top'], np.where(dz < 0, SHADE['under'], np.where(dx != 0, SHADE['x'], SHADE['y'])))
            f = np.full(len(hi), np.clip(s / dist, 0, 1) ** 1.2)
            out[hi] = rgb * sh[:, None] * (1 - f[:, None]) + fogc * f[:, None]
            alive[hi] = False
        prev[idx] = c
    return Image.fromarray(np.clip(out.reshape(H, W, 3), 0, 255).astype(np.uint8), 'RGB')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('vxl'); ap.add_argument('out')
    ap.add_argument('coords', nargs=6, type=float)
    ap.add_argument('--fog', nargs=3, type=int, default=(152, 174, 168))
    ap.add_argument('--babel', action='store_true')
    a = ap.parse_args()
    vm, _ = load(a.vxl)
    render(vm, a.coords[:3], a.coords[3:], fog=tuple(a.fog), babel=a.babel).save(a.out)
