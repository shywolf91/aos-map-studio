"""Preview renders (numpy previews, NOT client inspection): python tc_render.py MAP.vxl OUTDIR"""
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from aosmap.vxl import read_vxl
from aosmap.render import top_down, isometric
vm, _ = read_vxl(open(sys.argv[1], 'rb').read())
out = sys.argv[2]
os.makedirs(out, exist_ok=True)
top_down(vm).save(os.path.join(out, 'top_down.png'))
top_down(vm, crop=(130, 180, 380, 340), scale=4).save(os.path.join(out, 'top_down_centre_x4.png'))
isometric(vm, s=1).save(os.path.join(out, 'iso_full.png'))
isometric(vm, crop=(150, 190, 380, 340), s=3).save(os.path.join(out, 'iso_centre_x3.png'))
import json
info = json.load(open(os.path.join(os.path.dirname(sys.argv[1]), 'build.json')))
gx, gy = info['oneoffs']['gingerbread'][0]
isometric(vm, crop=(gx - 30, gy - 30, gx + 50, gy + 40), s=6).save(os.path.join(out, 'iso_gingerbread_x6.png'))
isometric(vm, crop=(226, 226, 290, 290), s=8).save(os.path.join(out, 'iso_giant_tree_x8.png'))
isometric(vm, crop=(90, 30, 260, 110), s=5).save(os.path.join(out, 'iso_sky_sleigh_x5.png'))
