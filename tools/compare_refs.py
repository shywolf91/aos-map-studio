"""Validate aosmap.vxl against real maps and pyspades 1.4.2, and collect art statistics.

Per map:
  1. decode with our reader (strict issue report)
  2. pyspades VXLData(file).generate()                -> bytes P   (independent C++ loader + writer)
  3. our write_vxl(our decode, missing='default')     -> bytes O
     O == P  => our reader+writer agree with pyspades' loader+writer on every voxel AND colour
  4. decode P with our reader, compare occupancy/colours with step 1 (redundant reader check)
  5. O == original file?  (is the source file already in canonical pyspades form?)
  6. statistics: land/water, heights, palette, shade byte, floating (ungrounded) components
Usage: python tools/compare_refs.py <dir-with-vxl> <out.json>
"""
import io, json, os, sys, time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from aosmap.vxl import read_vxl, write_vxl, surface_mask  # noqa: E402

FACE6 = ndimage.generate_binary_structure(3, 1)


def analyse(path):
    from pyspades.vxl import VXLData
    t0 = time.time()
    raw = open(path, 'rb').read()
    name = os.path.basename(path).split('-', 1)[-1].rsplit('.', 1)[0]
    res = {'name': name, 'file': os.path.basename(path), 'bytes': len(raw)}
    try:
        m, rep = read_vxl(raw)
    except Exception as e:                       # noqa: BLE001
        res['read_error'] = repr(e)
        return res
    res['reader_ok'] = rep.ok
    res['reader_issues'] = Counter(i[0] for i in rep.issues)
    res['empty_top_runs'] = rep.empty_top_runs
    res['void_columns'] = rep.void_columns
    res['spans'] = rep.spans

    P = VXLData(io.BytesIO(raw)).generate()
    O = write_vxl(m, missing='default', force_bottom=False)
    res['ours_eq_pyspades_bytes'] = (O == P)
    res['original_is_canonical'] = (O == raw)
    m2, rep2 = read_vxl(P)
    res['pyspades_roundtrip_occupancy_equal'] = bool(np.array_equal(m.solid, m2.solid))
    surf = surface_mask(m2.solid)
    c1 = np.where(m.colored, m.color, 0xFF674028)
    res['pyspades_roundtrip_surface_colours_equal'] = bool(np.array_equal(c1[surf], m2.color[surf]))

    # ---- statistics
    solid = m.solid
    surf0 = surface_mask(solid)
    res['surface_voxels'] = int(surf0.sum())
    res['surface_missing_colour'] = int((surf0 & ~m.colored).sum())
    res['colours_on_hidden_voxels'] = int((m.colored & ~surf0).sum())
    land = solid[:, :, 62]
    res['land_fraction_z62'] = round(float(land.mean()), 4)
    top = np.argmax(solid, axis=2)                       # first solid z from top
    res['top_z_min'] = int(top.min())
    res['top_z_median_land'] = int(np.median(top[land])) if land.any() else None
    res['top_z_hist'] = {int(k): int(v) for k, v in zip(*np.unique(top, return_counts=True))}
    cols = m.color[surf0] & 0xFFFFFF
    res['unique_colours'] = int(np.unique(cols).size)
    shade = (m.color[surf0] >> 24) & 0xFF
    sh_vals, sh_counts = np.unique(shade, return_counts=True)
    res['shade_byte_top'] = {int(k): int(v) for k, v in sorted(zip(sh_vals, sh_counts), key=lambda t: -t[1])[:6]}
    vals, counts = np.unique(cols, return_counts=True)
    order = np.argsort(-counts)[:24]
    res['palette_top24'] = [(f'#{int(vals[i]):06x}', int(counts[i])) for i in order]
    # exposed top colours (what the overhead view sees)
    xs, ys = np.indices(top.shape)
    topc = m.color[xs, ys, top] & 0xFFFFFF
    res['top_unique_colours'] = int(np.unique(topc).size)
    # floating components (6-connected, grounded iff touching z >= 62) - excludes the z>=62 layers
    lab, n = ndimage.label(solid, structure=FACE6)
    grounded = np.unique(lab[:, :, 62:][solid[:, :, 62:]])
    sizes = np.bincount(lab.ravel())
    floating = [i for i in range(1, n + 1) if i not in set(grounded.tolist())]
    res['components'] = int(n)
    res['floating_components'] = len(floating)
    res['floating_voxels'] = int(sizes[floating].sum()) if floating else 0
    res['largest_floating'] = int(sizes[floating].max()) if floating else 0
    res['seconds'] = round(time.time() - t0, 1)
    return res


_B = None


def _bottom():
    global _B
    if _B is None:
        _B = np.zeros((512, 512, 64), bool)
        _B[:, :, 63] = True
    return _B


if __name__ == '__main__':
    src, out = sys.argv[1], sys.argv[2]
    files = sorted(os.path.join(src, f) for f in os.listdir(src) if f.lower().endswith('.vxl'))
    with ProcessPoolExecutor(max_workers=int(os.environ.get('JOBS', '4'))) as ex:
        results = list(ex.map(analyse, files))
    json.dump(results, open(out, 'w'), indent=1, default=str)
    for r in results:
        print(f"{r['name']:24s} ok={r.get('reader_ok')} eq_pys={r.get('ours_eq_pyspades_bytes')} "
              f"canon={r.get('original_is_canonical')} occ={r.get('pyspades_roundtrip_occupancy_equal')} "
              f"col={r.get('pyspades_roundtrip_surface_colours_equal')} float={r.get('floating_components')}"
              f"/{r.get('floating_voxels')} miss={r.get('surface_missing_colour')} {r.get('read_error','')}")
