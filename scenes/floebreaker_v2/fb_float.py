"""List floating components that are NOT sky decor.  python fb_float.py OUTDIR variant"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
import numpy as np
from scipy import ndimage as ndi
from aosmap.vxl import load
out, v = sys.argv[1], sys.argv[2]
vm, _ = load(f'{out}/floebreaker_{v}.vxl'); s = vm.solid
lab, n = ndi.label(s, structure=ndi.generate_binary_structure(3, 1))
gr = set(np.unique(lab[:, :, 62:][s[:, :, 62:]]).tolist())
objs = ndi.find_objects(lab); sizes = ndi.sum(s, lab, range(1, n + 1))
bad = [(int(sizes[i]), [(a.start, a.stop - 1) for a in objs[i]]) for i in range(n) if (i + 1) not in gr and objs[i][2].start > 16]
sky = [(int(sizes[i])) for i in range(n) if (i + 1) not in gr and objs[i][2].start <= 16]
print(v, 'non-sky floating:', len(bad), 'voxels', sum(b[0] for b in bad), '| sky components:', len(sky), 'voxels', sum(sky))
for b in bad[:15]: print(b)
