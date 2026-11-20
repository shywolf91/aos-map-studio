"""Witchwood Isles graybox pipeline: build -> export -> round trips -> Babel checks.

usage: python build.py OUTDIR [--no-checks]
"""
import hashlib
import json
import os
import sys
import time

import numpy as np

import ww_gen
from ww_core import write_vxl, read_vxl, surface_mask

NAME = 'witchwood_isles'


def pyspades_roundtrip(data, solid, colors):
    try:
        from pyspades.vxl import VXLData
    except ImportError:
        return {'skipped': 'pyspades not installed'}
    import io
    m = VXLData(fp=io.BytesIO(data))
    regen = bytes(m.generate())
    rng = np.random.RandomState(1)
    pts = rng.randint(0, 512, size=(20000, 2))
    zs = rng.randint(0, 64, size=20000)
    surf = surface_mask(solid)
    sol_mm = col_mm = 0
    for (x, y), z in zip(pts, zs):
        s = bool(m.get_solid(int(x), int(y), int(z)))
        if s != bool(solid[x, y, z]):
            sol_mm += 1
        if surf[x, y, z]:
            c = m.get_point(int(x), int(y), int(z))[1]
            if tuple(c[:3]) != tuple(int(v) for v in colors[x, y, z]):
                col_mm += 1
    return {'regenerate_identical': regen == data, 'solid_mismatch_of_20000': sol_mm,
            'colour_mismatch_of_20000': col_mm}


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    art = '--art' in sys.argv
    if art:
        import ww_art
        A = ww_art.Art()
        solid, mat, colors = A.build()
        MATS = ww_art.MATS
    else:
        solid, mat, H = ww_gen.build()
        colors = ww_gen.shade(solid, mat)
        MATS = ww_gen.MATS
    vxl_path = os.path.join(out, NAME + '.vxl')
    data = write_vxl(vxl_path, solid, colors)
    ww_gen.map_txt(os.path.join(out, NAME + '.txt'), version='1.0' if art else '0.1-graybox')
    np.savez_compressed(os.path.join(out, 'volume.npz'), solid=solid, mat=mat, colors=colors)
    sha = hashlib.sha256(data).hexdigest()
    print('exported', len(data), 'bytes sha256', sha[:16], round(time.time() - t0, 1), 's')
    if '--no-checks' in sys.argv:
        return

    R = {'map': NAME, 'seed': ww_gen.SEED, 'sha256': sha, 'bytes': len(data)}
    s2, c2, stored = read_vxl(data)
    surf = surface_mask(solid)
    R['own_reader'] = {'solid_identical': bool((s2 == solid).all()),
                       'stored_equals_surface': bool((stored == surf).all()),
                       'colours_identical_on_surface': bool((c2[surf] == colors[surf]).all())}
    print('own reader', R['own_reader'])
    R['pyspades_1_4_2'] = pyspades_roundtrip(data, solid, colors)
    print('pyspades', R['pyspades_1_4_2'])
    import ww_validate
    R.update(ww_validate.run(solid, mat, ww_gen.SPEC, MATS))
    R['elapsed_s'] = round(time.time() - t0, 1)
    with open(os.path.join(out, 'validation.json'), 'w') as f:
        json.dump(R, f, indent=1, default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o))
    print(json.dumps({k: v for k, v in R.items() if k not in ('own_reader', 'pyspades_1_4_2')}, indent=1,
                     default=str)[:6000])


if __name__ == '__main__':
    main()
