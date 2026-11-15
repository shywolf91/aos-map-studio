"""Mirror, floating components, orphan cleanup, trap fill.

Merged from gf_build.mirror_west_to_east, ds_core.mirror_x / the cores' fold_x (mirror), Bloomhop
main.remove_orphans + wkh/sph_build.cleanup + ds_build.remove_debris (orphans) and the hc/wkh/sph/gf_check
floating() reports.

Mirror axes used in this project (state which one a map uses in its SPEC):
  'x512'  x' = 512 - x   (column 0 and 256 are on the axis; 256 must be copied from 255) - most Babel maps
  'x511'  x' = 511 - x   (no shared column) - Bloomhop, Under the Tree
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

_FACE = ndi.generate_binary_structure(3, 1)


def mirror_index(x, axis='x512'):
    return (512 - x) % 512 if axis == 'x512' else 511 - x


def mirror_west_to_east(*arrays, axis='x512'):
    """Copy the west half onto the east half in place, for every [x, ...] array given."""
    for a in arrays:
        if axis == 'x512':
            a[257:] = a[255:0:-1]
            a[256] = a[255]          # lesson: the axis column is otherwise left empty
        else:
            a[256:] = a[255::-1]
    return arrays


def mirror_canvas(cv, axis='x512'):
    mirror_west_to_east(cv.solid, cv.rgb, cv.mat, cv.H, cv.keep, cv.nolight, axis=axis)
    east = []
    for (x, y, z, c) in cv.glow:
        if x < 256:
            east.append((mirror_index(x, axis), y, z, c))
    cv.glow = [g for g in cv.glow if g[0] < 256] + east
    ints = []
    for (nm, x, y, z) in cv.interiors:
        if x < 256:
            ints.append([f'{nm} (W)', x, y, z])
            ints.append([f'{nm} (E)', mirror_index(x, axis), y, z])
    if ints:
        cv.interiors = ints
    return cv


def mirror_mismatch(solid, mat=None, axis='x512', exclude=None):
    """Voxels that differ from their mirror. exclude: list of (x0, x1, y0, y1) boxes (west or east) left out."""
    excl = np.zeros((512, 512), bool)
    for (x0, x1, y0, y1) in exclude or []:
        excl[x0:x1 + 1, y0:y1 + 1] = True
        a, b = sorted((mirror_index(x0, axis), mirror_index(x1, axis)))
        excl[a:b + 1, y0:y1 + 1] = True
    if axis == 'x512':
        west, east, keep = slice(1, 256), slice(511, 256, -1), ~excl[1:256, :, None]
    else:
        west, east, keep = slice(0, 256), slice(511, 255, -1), ~excl[0:256, :, None]
    out = {'solid': int(((solid[west] != solid[east]) & keep).sum())}
    if mat is not None:
        out['material'] = int(((mat[west] != mat[east]) & keep).sum())
    return out


def _bbox_inside(f, box):
    return (box['x'][0] <= f['x'][0] and f['x'][1] <= box['x'][1] and box['y'][0] <= f['y'][0] and
            f['y'][1] <= box['y'][1] and box['z'][0] <= f['z'][0] and f['z'][1] <= box['z'][1])


def floating_components(solid, mat=None, mat_names=None):
    """Components (6-connected) not touching z >= 62. Grounded = face-connected to the indestructible layer."""
    lab, n = ndi.label(solid, structure=_FACE)
    grounded = set(np.unique(lab[:, :, 62:][solid[:, :, 62:]]).tolist())
    objs = ndi.find_objects(lab)
    out = []
    for i, sl in enumerate(objs, start=1):
        if sl is None or i in grounded:
            continue
        sub = lab[sl] == i
        f = {'voxels': int(sub.sum()), 'x': [sl[0].start, sl[0].stop - 1], 'y': [sl[1].start, sl[1].stop - 1],
             'z': [sl[2].start, sl[2].stop - 1]}
        if mat is not None:
            vals, cnt = np.unique(mat[sl][sub], return_counts=True)
            v = int(vals[np.argmax(cnt)])
            f['mat'] = (mat_names or {}).get(v, v)
        out.append(f)
    return out


def split_expected(floating, expected_boxes):
    """-> (unexpected, expected) using intentional-floating boxes ({'x':[a,b],'y':..,'z':..} or 6-tuples)."""
    boxes = []
    for b in expected_boxes or []:
        if isinstance(b, dict):
            boxes.append(b)
        else:
            x0, x1, y0, y1, z0, z1 = b
            boxes.append({'x': [x0, x1], 'y': [y0, y1], 'z': [z0, z1]})
    exp = [f for f in floating if any(_bbox_inside(f, b) for b in boxes)]
    return [f for f in floating if f not in exp], exp


def remove_orphans(cv, keep_expected=True, min_expected=20):
    """Delete floating fragments (lesson: diagonal-only contact floats and collapses). Keeps intentional pieces.
    Returns a report for build.json."""
    fl = floating_components(cv.solid)
    unexpected, expected = split_expected(fl, cv.expect_floating) if keep_expected else (fl, [])
    removed = removed_vox = 0
    kept = []
    for f in expected:
        if f['voxels'] > min_expected:
            kept.append(f)
        else:
            unexpected.append(f)
    if unexpected:
        lab, n = ndi.label(cv.solid, structure=_FACE)
        drop = np.ones(n + 1, bool)
        drop[0] = False
        drop[np.unique(lab[:, :, 62:][cv.solid[:, :, 62:]])] = False      # grounded
        for f in kept:                                                    # intentional pieces stay
            sl = (slice(f['x'][0], f['x'][1] + 1), slice(f['y'][0], f['y'][1] + 1), slice(f['z'][0], f['z'][1] + 1))
            drop[np.unique(lab[sl])] = False
        m = drop[lab]
        cv.solid[m] = False
        cv.mat[m] = 0
        removed = len(unexpected)
        removed_vox = int(m.sum())
    return {'removed_components': removed, 'removed_voxels': removed_vox, 'kept_floating': kept}


def standable(solid):
    """Floor voxels with 3 air voxels above (z-1..z-3)."""
    st = np.zeros_like(solid)
    st[:, :, 3:] = solid[:, :, 3:] & ~solid[:, :, 2:-1] & ~solid[:, :, 1:-2] & ~solid[:, :, 0:-3]
    return st


def fill_pits(cv, max_depth=3, region=None):
    """Raise 1-column pits deeper than 1 that a player could fall into and not step out of (graph-free version of
    wkh_terrain.fix_pockets): a column whose top is > 1 below all 4 neighbours gets raised to (min neighbour + 1)."""
    top = cv.tops().astype(int)
    raised = 0
    nb = np.stack([np.roll(top, 1, 0), np.roll(top, -1, 0), np.roll(top, 1, 1), np.roll(top, -1, 1)])
    lo = nb.min(0)
    pit = (top - lo > 1) & (top - lo <= max_depth)
    if region is not None:
        x0, x1, y0, y1 = region
        r = np.zeros_like(pit)
        r[x0:x1 + 1, y0:y1 + 1] = True
        pit &= r
    for x, y in zip(*np.nonzero(pit)):
        z_new = lo[x, y] + 1
        c = cv.rgb[x, y, top[x, y]].copy()
        cv.solid[x, y, z_new:top[x, y]] = True
        cv.rgb[x, y, z_new:top[x, y]] = c
        raised += 1
    return raised
