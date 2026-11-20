"""Validation for Floebreaker.  python fb_check.py OUTDIR [--exposure] [variant]  -> OUTDIR/validation.json"""
import json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
import numpy as np
from scipy import ndimage as ndi
from aosmap.vxl import load, write_vxl
from aosmap import nav, sightline, validate

out = sys.argv[1]
variant = next((a for a in sys.argv[2:] if a in ('day', 'night')), 'day')
t0 = time.time()
vm, rep = load(os.path.join(out, f'floebreaker_{variant}.vxl'))
s = vm.solid
res = {'variant': variant, 'reader_ok': bool(rep.ok), 'bytes': rep.bytes_total}
# roundtrip with our writer
res['roundtrip_identical'] = write_vxl(vm, missing='error') == open(os.path.join(out, f'floebreaker_{variant}.vxl'), 'rb').read()
# floating
bj = json.load(open(os.path.join(out, f'floebreaker_{variant}_build.json')))
lab, n = ndi.label(s, structure=ndi.generate_binary_structure(3, 1))
grounded = set(np.unique(lab[:, :, 62:][s[:, :, 62:]]).tolist())
fl = [i for i in range(1, n + 1) if i not in grounded]
sizes = ndi.sum(s, lab, fl) if fl else []
res['floating_components'] = len(fl); res['floating_voxels'] = int(sum(sizes))
res['expected_floating_pieces'] = len(bj['floating']); res['expected_floating_voxels'] = int(sum(p['voxels'] for p in bj['floating']))
res['unexpected_floating_voxels'] = max(0, res['floating_voxels'] - res['expected_floating_voxels'])
# babel platform + spawn zones
r = validate.check_babel(vm)
res['babel'] = [(f.severity, f.code, f.message) if hasattr(f, 'code') else str(f) for f in r.findings][:12] if hasattr(r, 'findings') else str(r)
# anchors: solid ground under both platform ends
for nm, (x0, x1) in (('west_end', (206, 211)), ('east_end', (300, 305))):
    col = s[x0:x1 + 1, 240:272, :62].any(axis=2)
    res[f'anchor_{nm}_land_pct'] = round(100 * float(col.mean()), 1)
top = np.argmax(s[:, :, :63], axis=2)
for nm, (bx, by) in (('blue', (118, 256)), ('red', (394, 256))):
    sq = top[bx - 20:bx + 21, by - 20:by + 21]
    res[f'spawn_{nm}'] = {'z_min': int(sq.min()), 'z_max': int(sq.max()), 'z_median': int(np.median(sq)),
                           'water_cols': int((sq >= 62).sum()), 'relief': int(sq.max() - sq.min())}
# routes + build gap (sea walkable: water_damage off, boundary damage ignored for the graph)
g = nav.build(s, water_damage=False)
rt = nav.babel_route_check(s, water_damage=False)
res['babel_routes'] = rt
# reachability of every spawn from the other
src = nav.zone_nodes(g, 118, 256, 20); d1 = nav.distances(g, src)
src2 = nav.zone_nodes(g, 394, 256, 20); d2 = nav.distances(g, src2)
res['blue_to_red_spawn_cost'] = round(float(np.nanmin(d1[nav.zone_nodes(g, 394, 256, 20)])), 1)
res['red_to_blue_spawn_cost'] = round(float(np.nanmin(d2[nav.zone_nodes(g, 118, 256, 20)])), 1)
reach = np.isfinite(d1)
xyz = g.node_xyz
land_nodes = (xyz[:, 2] < 62)
res['land_nodes'] = int(land_nodes.sum()); res['land_nodes_reachable_from_blue_pct'] = round(100 * float((reach & land_nodes).sum() / land_nodes.sum()), 1)
# ship interiors: nodes inside the hull volume at each floor reachable from spawn?
sx = (xyz[:, 0] >= 244) & (xyz[:, 0] <= 267) & (xyz[:, 1] >= 58) & (xyz[:, 1] <= 170)
ship = {}
for nm, zf in (('hold_floor', 59), ('main_deck', 49), ('level_B', 43), ('bridge_C', 37), ('roof', 31)):
    sel = sx & (xyz[:, 2] == zf)
    ship[nm] = {'nodes': int(sel.sum()), 'reachable_pct': round(100 * float(reach[sel].mean()), 1) if sel.any() else None}
res['ship_interiors'] = ship
# unreachable-from-blue land pockets (periphery passability)
res['periphery_ring_reach_pct'] = None
ring = land_nodes & (np.hypot(xyz[:, 0] - 256, xyz[:, 1] - 256) > 130)
res['periphery_nodes_reachable_pct'] = round(100 * float(reach[ring].mean()), 1) if ring.any() else None
# nearest authored voxel to platform (free-scaffolding): highest standable node within 60 of the platform
px0, px1, py0, py1 = 206, 305, 240, 271
near = (xyz[:, 0] >= px0 - 60) & (xyz[:, 0] <= px1 + 60) & (xyz[:, 1] >= py0 - 60) & (xyz[:, 1] <= py1 + 60)
res['highest_standable_z_within_60_of_platform'] = int(xyz[near & reach, 2].min())
if '--exposure' in sys.argv:
    res['spawn_exposure'] = sightline.babel_spawn_report(s)
res['elapsed_s'] = round(time.time() - t0, 1)
json.dump(res, open(os.path.join(out, f'validation_{variant}.json'), 'w'), indent=1, default=str)
print(json.dumps(res, indent=1, default=str))
