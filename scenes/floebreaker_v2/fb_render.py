"""Previews from the exported .vxl (numpy renders, not client captures).  python fb_render.py OUTDIR PREVIEWDIR"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from aosmap.vxl import load
from aosmap import render
out, pv = sys.argv[1], sys.argv[2]
os.makedirs(pv, exist_ok=True)
for v in ('day', 'night'):
    vm, rep = load(os.path.join(out, f'floebreaker_{v}.vxl'))
    assert rep.ok, rep.issues[:3]
    render.top_down(vm).save(f'{pv}/{v}_top.png')
    render.isometric(vm, s=1, view=0).save(f'{pv}/{v}_iso0.png')
    render.isometric(vm, s=1, view=2).save(f'{pv}/{v}_iso2.png')
    render.isometric(vm, crop=(196, 40, 316, 190), s=4, view=0).save(f'{pv}/{v}_ship.png')
    render.isometric(vm, crop=(70, 190, 200, 330), s=4, view=0).save(f'{pv}/{v}_spawn_blue.png')
print('ok')
