"""Run the repo's Babel rules checker (aosmap.kit.babel_checks) on each variant.  Use the venv python (pyspades).
   python fb_rules.py OUTDIR [variant ...]   -> OUTDIR/rules_<variant>.json and a pass/fail printout"""
import json, os, shutil, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from aosmap.kit import babel_checks
out = sys.argv[1]
variants = [a for a in sys.argv[2:]] or ['day', 'night']
for v in variants:
    tmp = tempfile.mkdtemp(prefix=f'fb_rules_{v}_')
    for src, dst in ((f'floebreaker_{v}.vxl', f'floebreaker_{v}.vxl'), (f'floebreaker_{v}_build.json', 'build.json'),
                     (f'floebreaker_{v}_mat.npy', 'mat.npy'), (f'floebreaker_{v}_terrain_H.npy', 'terrain_H.npy')):
        p = os.path.join(out, src)
        if os.path.exists(p):
            shutil.copy(p, os.path.join(tmp, dst))
    print('=====', v)
    R = babel_checks.main([tmp, '--out', os.path.join(out, f'rules_{v}.json')])
    shutil.rmtree(tmp, ignore_errors=True)
