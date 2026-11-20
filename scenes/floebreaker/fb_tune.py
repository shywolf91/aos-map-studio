"""Experiment harness: python fb_tune.py '[[cx,cy,rx,ry,h],...]'  -> exposure + zone rules for the blue side (no sky)."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..')); sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import fb_detail, fb_build
from aosmap.kit import babel_checks, zones
from aosmap.kit.params import BABEL_DEFAULT
fb_detail.RIDGES[:] = [tuple(r) for r in json.loads(sys.argv[1])] if len(sys.argv) > 1 else []
W = fb_build.build(decor_seed=1)
solid = W.m > 0; solid[:, :, 63] = True
ex = {b: babel_checks.spawn_exposure(solid, bs)['hidden_pct'] for b, bs in (('blue', (118, 256)), ('red', (394, 256)))}
e = babel_checks.spawn_exposure(solid, (118, 256))
print('exposure blue', e)
zr = zones.zone_rules(solid, BABEL_DEFAULT, terrain_H=W.H)
for k, v in zr.items():
    if isinstance(v, dict) and 'status' in v:
        print(k, v['status'], v.get('why', '')[:230])
