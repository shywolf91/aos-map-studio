"""Death Swamp layout: island footprints, ground heights, spawn pads, control points, bridgeheads.

Push (piqueserver 1.4.2 game_modes/push.py): each team spawns with the ENEMY intel at its own spawn and carries
it to its OWN control point; water_damage is forced to 100, so the swamp is lethal and every island gap must be
bridged. Layout: two mirrored lanes running north. Blue = west lane (x < 256), Red = east lane (mirror).
Spawn islands in the south, four bridged gaps per lane, both control points on the shared North Isle
("the Leviathan's Rest") either side of the beast skull.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from ds_core import MX, MY, fbm2, mirror_x

# --------------------------------------------------------------------------------------------- SPEC
# Every number the generator and the checks use. West half only; the east half is the x' = 511 - x mirror.
SPEC = {
    'name': 'Death Swamp',
    'islands': {          # name -> (plateau z, [(cx, cy, rx, ry), ...] blobs)
        'S':  (55, [(172, 456, 44, 40), (146, 478, 22, 17), (204, 440, 22, 22), (186, 484, 24, 14)]),
        'I2': (54, [(196, 366, 34, 34), (218, 348, 16, 17), (172, 378, 18, 13)]),
        'I3': (56, [(176, 280, 36, 40), (150, 266, 15, 16), (204, 302, 17, 13)]),
        'I4': (55, [(194, 194, 34, 36), (214, 180, 16, 14), (170, 210, 16, 13)]),
        'N':  (53, [(186, 100, 60, 43), (232, 84, 36, 46), (150, 72, 28, 24), (222, 124, 34, 20),
                    (256, 64, 30, 36)]),
    },
    'order': ['S', 'I2', 'I3', 'I4', 'N'],        # push direction for each team
    'gap_target': (12, 17),                         # shortest island-to-island water gap per crossing
    'channel_min': 40,                              # water between the two lanes (x 236..275)
    'spawn': (170, 462),                            # blue spawn pad centre (push_spawn_range 5)
    'spawn_range': 5,
    'cp': (184, 96),                                # blue control point (tent) centre
    'cp_protect': 8,                                # push default_cp_protect_range
    'skull': (255.5, 68),                           # beast skull centre (on the mirror axis)
    'ribs_y': (208, 240, 274, 310, 348, 388),       # rib pairs of the drowned leviathan (central channel)
    'build_area_blue': (96, 150, 240, 508),         # push_blue_build_area (x1, y1, x2, y2), enemy can't build
}


def island_masks():
    """Return {name: 2D bool mask over the full map} (mirrored), plus combined land mask."""
    n = fbm2((MX, MY), 32, 3, 'coastwarp')
    n2 = fbm2((MX, MY), 12, 2, 'coastfine')
    X, Y = np.indices((MX, MY)).astype(np.float32)
    masks = {}
    for name, (_, blobs) in SPEC['islands'].items():
        f = np.full((MX, MY), -9.0, np.float32)
        for (cx, cy, rx, ry) in blobs:
            f = np.maximum(f, 1.0 - ((X - cx) / rx) ** 2 - ((Y - cy) / ry) ** 2)
        f += (n - 0.5) * 0.55 + (n2 - 0.5) * 0.18
        m = f > 0
        m[256:] = False
        m = mirror_x(m)
        # keep the largest component per half (drop noise specks)
        lab, k = ndi.label(m)
        if k > 2:
            sizes = np.bincount(lab.ravel()); sizes[0] = 0
            keep = np.argsort(sizes)[-2:] if name != 'N' else np.argsort(sizes)[-1:]
            m = np.isin(lab, keep)
        masks[name] = m
    return masks


def ground_height(masks):
    """Top z of terrain per column (63 = water) and the island id map.

    Banks step down to the water in 1-voxel terraces (z = 61 - ceil(d), d = inland distance) until they meet the
    plateau (gentle +-1 terraced undulation), so every bank is walkable and the edge sits 1-3 above the water."""
    top = np.full((MX, MY), 63, np.int16)
    ident = np.full((MX, MY), -1, np.int8)
    und = fbm2((MX, MY), 40, 3, 'undulate')
    und = mirror_x(und)
    for i, name in enumerate(SPEC['order']):
        m = masks[name]
        pz = SPEC['islands'][name][0]
        d = ndi.distance_transform_edt(m)
        plateau = pz + np.rint((und - 0.5) * 3.2).astype(np.int16)          # pz-1 .. pz+1, terraced
        bank = 61 - np.ceil(d).astype(np.int16)                             # 1-voxel steps up from the water
        z = np.maximum(bank, plateau)
        top = np.where(m, np.minimum(top, z), top)
        ident = np.where(m, i, ident)
    return top, ident


def gaps(masks):
    """Shortest water gap between consecutive islands of the blue lane (+ lane-to-lane channel)."""
    out = {}
    west = np.zeros((MX, MY), bool); west[:256] = True
    order = SPEC['order']
    for a, b in zip(order, order[1:]):
        A = masks[a] & west
        B = masks[b] & west
        dB = ndi.distance_transform_edt(~B)
        k = np.argmin(np.where(A, dB, 1e9))
        ax, ay = np.unravel_index(k, A.shape)
        dA = ndi.distance_transform_edt(~A)
        k2 = np.argmin(np.where(B, dA, 1e9))
        bx, by = np.unravel_index(k2, B.shape)
        out[f'{a}->{b}'] = {'gap_water_voxels': float(dB[ax, ay]) - 1.0, 'from': (int(ax), int(ay)),
                            'to': (int(bx), int(by))}
    lanes = np.zeros((MX, MY), bool)
    for n in order[:-1]:
        lanes |= masks[n]
    xs = np.nonzero(lanes[:256].any(axis=1))[0]
    out['channel'] = {'blue_lane_max_x': int(xs.max()), 'water_width': int(2 * (255 - xs.max()))}
    return out


if __name__ == '__main__':
    import json
    m = island_masks()
    print(json.dumps(gaps(m), indent=1))
