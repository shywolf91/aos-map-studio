"""Validation for Tradeoff Christmas: python tc_check.py MAP.vxl ORIG.vxl BUILD.json OUT.json"""
import json, os, sys
import numpy as np
from scipy import ndimage
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from aosmap.vxl import read_vxl, write_vxl, surface_mask
from aosmap.validate import floating_components

path, orig, bj, outp = sys.argv[1:5]
raw = open(path, 'rb').read()
vm, rep = read_vxl(raw)
res = {'reader_ok': bool(rep.ok) if not callable(rep.ok) else bool(rep.ok()), 'issues': rep.issues[:5]}
res['reencode_identical'] = write_vxl(vm) == raw
res['z63_all_solid'] = bool(vm.solid[:, :, 63].all())
S = vm.solid
# geometry preserved: tower/slab region unchanged vs original
o, _ = read_vxl(open(orig, 'rb').read())
top = np.where(o.solid.any(2), o.solid.argmax(2), 64)
slab = ndimage.binary_dilation(top < 60, iterations=2)
diff = (S != o.solid)
res['tower_geometry_changed_voxels_in_slab_footprint'] = int(diff[slab].sum())
# the only allowed changes inside the footprint are the roof-edge bulbs at z=1 (+ nothing else)
d2 = diff & slab[:, :, None]
res['slab_changes_not_z1'] = int((d2 & (np.arange(64)[None, None, :] != 1)).sum())
info = json.load(open(bj))
fl = floating_components(S)
exp = info['floaters']
def inbox(c, f):
    (x0, x1), (y0, y1), (z0, z1) = c['bbox']
    bx0, by0, bz0, bx1, by1, bz1 = f['bbox']
    return x0 >= bx0 - 6 and x1 <= bx1 + 6 and y0 >= by0 - 6 and y1 <= by1 + 6 and z0 >= bz0 - 16 and z1 <= bz1 + 16
unexp = [c for c in fl if not any(inbox(c, f) for f in exp)]
res['floating_components_total'] = len(fl)
res['floating_expected_pieces'] = len(exp)
res['floating_unexpected'] = [(c['voxels'], c['bbox']) for c in unexp][:20]
res['floating_unexpected_count'] = len(unexp)
per = []
for f in exp:
    n = [c for c in fl if inbox(c, f)]
    per.append((f['name'], len(n), sum(c['voxels'] for c in n)))
res['floating_components_per_expected_piece'] = per
# interior reachability: air inside each house/igloo connects to outside
air = ~S
def reach(x0, x1, y0, y1, zlo, seed):
    sub = air[x0:x1, y0:y1, zlo:63]
    lab, _ = ndimage.label(sub)
    l = lab[seed[0] - x0, seed[1] - y0, seed[2] - zlo]
    if l == 0: return 'seed is solid'
    border = np.unique(np.concatenate([lab[0].ravel(), lab[-1].ravel(), lab[:, 0].ravel(), lab[:, -1].ravel()]))
    return bool(l in border)
r = {}
for (x, y) in info['oneoffs'].get('gingerbread', []):
    r[f'gingerbread@{x},{y}'] = reach(x - 4, x + 20, y - 4, y + 16, 40, (x + 7, y + 5, 62))
for (x, y) in info['oneoffs'].get('igloo', []):
    r[f'igloo@{x},{y}'] = reach(x - 4, x + 18, y - 4, y + 18, 40, (x + 7, y + 7, 61))
res['interiors_connect_to_outside'] = r
# colour metrics (top surface of floor / roofs)
sf = surface_mask(S)
C = vm.color
def lum(ix):
    c = C[ix].astype(np.int64); r_, g_, b_ = (c >> 16) & 255, (c >> 8) & 255, c & 255
    return 0.3 * r_ + 0.59 * g_ + 0.11 * b_, np.maximum(np.maximum(r_, g_), b_)
f = sf[:, :, 63]
l, m = lum((np.nonzero(f)[0], np.nonzero(f)[1], np.full(f.sum(), 63)))
res['floor_luma_min_median'] = [float(l.min()), float(np.median(l))]
res['floor_max_channel_max'] = int(m.max())
ro = sf[:, :, 2] & slab
ix = np.nonzero(ro); l2, m2 = lum((ix[0], ix[1], np.full(len(ix[0]), 2)))
res['roof_luma_median'] = float(np.median(l2)); res['roof_max_channel_p99'] = float(np.percentile(m2, 99))
sv = sf & (np.arange(64)[None, None, :] < 63)
ix = np.nonzero(sv); l3, _ = lum(ix)
res['surface_luma_min_p1'] = [float(l3.min()), float(np.percentile(l3, 1))]
res['file_bytes'] = len(raw)
json.dump(res, open(outp, 'w'), indent=1, default=int)
print(json.dumps(res, indent=1, default=int))
