"""Load the original Royal Parade Night (snow) map read-only and classify every voxel into a material.

The input is third-party: it is only read (aosmap.kit.codec.decode, strict); its .txt is never executed.

Materials (Canvas.mat names):
  water, credit_title, credit_by           z 63 sea and the painted "Royal Parade / By Bradley" credit on it
  street, ground                           the z 56 street/pavement layer and the solid quay below it
  building, vehicle:<name>, vehicle, jet, guard, tree, figure, planter, median, prop
                                           6-connected components of the solid above the street (z <= 55)
"""
from __future__ import annotations

import hashlib

import numpy as np
from scipy import ndimage as ndi

from aosmap.kit import Canvas, codec

WATER_RGB = np.array((153, 217, 234), float)


def load(spec):
    data = open(spec['source']['vxl'], 'rb').read()
    sha = hashlib.sha256(data).hexdigest()
    if sha != spec['source']['sha256']:
        raise SystemExit(f'source map changed: sha256 {sha} != {spec["source"]["sha256"]}')
    solid, color, _ = codec.decode(data)
    rgb = codec.unpack_rgb(color).astype(np.uint8)
    return solid, rgb, sha


def components(solid, street_z=56):
    """6-connected components of the solid above the street (z < street_z)."""
    lab, n = ndi.label(solid[:, :, :street_z])
    objs = ndi.find_objects(lab)
    rows = []
    for i, sl in enumerate(objs, 1):
        if sl is None:
            continue
        rows.append({'id': i, 'box': [sl[0].start, sl[0].stop - 1, sl[1].start, sl[1].stop - 1],
                     'z': [sl[2].start, sl[2].stop - 1], 'sl': sl})
    return lab, rows


def _family(rgb):
    """Colour families of the original palette (used by the classifier and the art grade)."""
    r, g, b = (rgb[..., i].astype(int) for i in range(3))
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    fam = np.full(r.shape, 'other', dtype=object)
    fam[(mn >= 190) & (mx - mn <= 40)] = 'snow'
    fam[(mx <= 8)] = 'black'
    fam[(r > g) & (g > b) & (b < 20) & (r >= 40) & (r <= 130) & (r - b > 35)] = 'brick'
    fam[(g > r) & (b >= r) & (abs(g - b) <= 12) & (g >= 50) & (g <= 160) & (r >= 30)] = 'stone'
    fam[(g > r) & (g >= b) & (r <= 40) & (g <= 60) & (b <= 45) & (mx >= 25)] = 'glass'
    fam[(g > r) & (g > b) & (r <= 20) & (b <= 15) & (g >= 18) & (g <= 90)] = 'leaf'
    fam[(r > 230) & (g > 200) & (b < 60)] = 'yellow_light'
    return fam


def classify(spec, solid, rgb):
    """Return (Canvas with the original solid/rgb, info dict)."""
    cv = Canvas(spec['name'])
    cv.solid[:] = solid
    cv.rgb[:] = rgb
    zs = spec['street_z']
    top = np.argmax(solid, axis=2)
    land = solid[:, :, 50:63].any(axis=2)              # quay land (z 50-62 solid); the jets fly at z <= 33
    # terrain_H: the street level on land, the sea bottom elsewhere (object detection ground for the checks)
    cv.H[:] = np.where(land, np.maximum(np.minimum(top, zs), 0), 63).astype(np.int16)
    cv.H[land & (top > zs)] = top[land & (top > zs)]
    # sea + painted credit
    sea = np.zeros(solid.shape, bool)
    sea[:, :, 63] = ~land
    d = np.linalg.norm(rgb[:, :, 63].astype(float) - WATER_RGB, axis=-1)
    blueish = (rgb[:, :, 63, 2] > 200) & (rgb[:, :, 63, 0] < 130)
    whiteish = rgb[:, :, 63].min(-1) >= 200
    title = (~land) & (d > 25) & blueish
    by = (~land) & (d > 25) & whiteish & ~blueish
    m = cv.material
    cv.mat[sea] = m('water')
    cv.mat[:, :, 63][title] = m('credit_title')
    cv.mat[:, :, 63][by] = m('credit_by')
    # street layer and ground below it
    lz = np.zeros(solid.shape, bool)
    lz[:, :, zs] = land
    cv.mat[lz & solid] = m('street')
    below = np.zeros(solid.shape, bool)
    below[:, :, zs + 1:] = land[:, :, None]
    cv.mat[below & solid & (cv.mat == 0)] = m('ground')
    # objects above the street
    lab, rows = components(solid, zs)
    vb = {tuple(v): k for k, v in spec['vehicles'].items()}
    counts = np.bincount(lab.ravel())
    info = {'components': 0, 'by_kind': {}, 'vehicles_found': [], 'floating_original': []}
    fam = _family(rgb[:, :, :zs])
    sub_mat = cv.mat[:, :, :zs]
    for r in rows:
        i, (x0, x1, y0, y1), (z0, z1) = r['id'], r['box'], r['z']
        sl = r['sl']
        msk = lab[sl] == i
        fp = int(msk.any(2).sum())
        h = zs - z0
        touches = z1 == zs - 1
        n = int(counts[i])
        famc = fam[sl][msk]
        leaf = float((famc == 'leaf').mean()) if n else 0
        key = (x0, x1, y0, y1)
        if not touches:
            kind = 'jet'
            info['floating_original'].append({'box': [x0, x1, y0, y1], 'z': [z0, z1], 'voxels': n})
        elif key in vb:
            kind = 'vehicle:' + vb[key]
            info['vehicles_found'].append(vb[key])
        elif (x0, x1, y0, y1) == (393, 409, 209, 218):
            kind = 'guard'
        elif fp >= 150 or h >= 14:
            kind = 'building'
        elif y0 >= spec['median_y'][0] and y1 <= spec['median_y'][1] and x1 - x0 >= 15:
            kind = 'median'
        elif leaf >= 0.35 and h <= 5 and fp >= 12:
            kind = 'planter'
        elif leaf >= 0.25:
            kind = 'tree'
        elif fp <= 3 and 5 <= h <= 8:
            kind = 'figure'
        else:
            kind = 'prop'
        sub_mat[sl][msk] = m(kind)
        info['by_kind'][kind.split(':')[0]] = info['by_kind'].get(kind.split(':')[0], 0) + 1
        info['components'] += 1
    missing = sorted(set(spec['vehicles']) - set(info['vehicles_found']))
    if missing:
        raise SystemExit(f'vehicles not found in the source: {missing}')
    info['land_columns'] = int(land.sum())
    info['credit_voxels'] = {'title': int(title.sum()), 'by': int(by.sum())}
    return cv, info, lab


def colour_family(rgb):
    return _family(rgb)
