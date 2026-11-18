"""Validation for Tradeoff Christmas v2: python tc2_check.py MAP.vxl ORIG.vxl BUILD.json OUT.json  (run with the 3.11 venv for pyspades)"""
import io, json, os, sys
import numpy as np
from scipy import ndimage
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from aosmap.vxl import read_vxl, write_vxl, surface_mask
from aosmap.validate import floating_components

path, orig, bj, outp = sys.argv[1:5]
raw = open(path, 'rb').read()
vm, rep = read_vxl(raw)
o, _ = read_vxl(open(orig, 'rb').read())
info = json.load(open(bj))
S, O = vm.solid, o.solid
res = {'reader_issues': len(rep.issues), 'reencode_identical': write_vxl(vm) == raw, 'z63_all_solid': bool(S[:, :, 63].all())}
try:
    from pyspades.vxl import VXLData
    P = VXLData(io.BytesIO(raw)).generate()
    res['pyspades_generate_identical'] = P == raw
except ImportError:
    res['pyspades_generate_identical'] = 'pyspades not importable here'
diff = S != O
res['changed_voxels_total'] = int(diff.sum())
top = np.where(O.any(2), O.argmax(2), 64)
foot = ndimage.binary_dilation(top < 60, iterations=2)
allowed = np.zeros_like(diff)
allowed[:, :, 1] = True                                            # roof bulbs
for (x, y) in info['strand_tip_baubles']:                          # hanging baubles at the web tips
    allowed[max(0, x - 5):x + 6, max(0, y - 5):y + 6, 8:22] = True
res['footprint_changes_outside_allowed'] = int((diff & foot[:, :, None] & ~allowed).sum())
res['removed_original_voxels_in_footprint'] = int((~S & O & foot[:, :, None]).sum())
pf = np.zeros_like(diff); pf[196:316, 230:282, 0:4] = True        # babel platform volume + margin (z 0-3)
res['new_solid_in_platform_volume'] = int((diff & S & pf).sum())
res['original_solid_in_platform_volume'] = int((O & pf).sum())
sx = np.zeros_like(diff)
for (x0, y0, x1, y1) in [(108, 246, 128, 266), (384, 246, 404, 266)]:
    sx[x0 - 3:x1 + 4, y0 - 3:y1 + 4, :] = True
res['new_solid_in_spawn_rects'] = int((diff & S & sx).sum())
fl = floating_components(S)
exp = info['floaters']
def inbox(c, f):
    (x0, x1), (y0, y1), (z0, z1) = c['bbox']; b = f['bbox']
    return x0 >= b[0] - 6 and x1 <= b[3] + 6 and y0 >= b[1] - 6 and y1 <= b[4] + 6 and z0 >= b[2] - 16 and z1 <= b[5] + 16
orig_fl = floating_components(O)
res['original_floating_components'] = len(orig_fl)
unexp = [c for c in fl if not any(inbox(c, f) for f in exp)]
res['floating_total'] = len(fl); res['expected_sky_pieces'] = len(exp)
res['floating_unexpected'] = [(c['voxels'], c['bbox']) for c in unexp][:10]
res['floating_unexpected_count'] = len(unexp)
# outer water untouched: no solid above the water floor outside tower footprint except the island and sky pieces
low = S[:, :, :63] & ~O[:, :, :63]
outside = ~foot
island = np.zeros((512, 512), bool); island[256 - 31:256 + 32, 256 - 31:256 + 32] = True
res['props_on_water_outside_island_z>=50'] = int((low[:, :, 50:] & outside[:, :, None] & ~island[:, :, None]).sum())
# tree/stairs: dry footing and build gaps
t = info['tree']
res['tree'] = t
res['gap_stair_top_to_platform_underside'] = t['stair_top_stand_z'] - 2
res['gap_star_to_platform_underside'] = t['star_z'] - 2
# staircase walkability: BFS over standable cells (feet cell + 2 air above, floor solid) from island edge to landing, step <= 1
cx, cy = 256, 256
reg = (slice(cx - 30, cx + 31), slice(cy - 30, cy + 31))
Sub = S[reg]
def standable(x, y, z): return (not Sub[x, y, z]) and (not Sub[x, y, z - 1]) and (not Sub[x, y, z - 2]) and Sub[x, y, z + 1]
from collections import deque
start = None
for x in range(0, 61):
    for y in range(0, 61):
        d = ((x - 30) ** 2 + (y - 30) ** 2) ** .5
        if 22.5 < d < 24 and standable(x, y, 60):
            start = (x, y, 60); break
    if start: break
seen = {start}; q = deque([start]); best = 63
while q:
    x, y, z = q.popleft(); best = min(best, z)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nx, ny = x + dx, y + dy
        if not (0 <= nx < 61 and 0 <= ny < 61): continue
        for nz in (z - 2, z - 1, z, z + 1):
            if 3 <= nz < 62 and (nx, ny, nz) not in seen and standable(nx, ny, nz) and abs(nz - z) <= 1:
                seen.add((nx, ny, nz)); q.append((nx, ny, nz))
res['walk_from_island_edge_highest_feet_z_reached'] = int(best)
res['stair_reaches_landing'] = bool(best <= t['stair_top_stand_z'] + 1)
sf = surface_mask(S)
c = vm.color[:, :, 63][sf[:, :, 63]].astype(np.int64)
lum = 0.3 * ((c >> 16) & 255) + 0.59 * ((c >> 8) & 255) + 0.11 * (c & 255)
res['water_luma_min_median'] = [float(lum.min()), float(np.median(lum))]
res['file_bytes'] = len(raw)
json.dump(res, open(outp, 'w'), indent=1, default=int)
print(json.dumps(res, indent=1, default=int))
