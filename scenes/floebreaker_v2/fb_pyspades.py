"""pyspades cross-check + piqueserver Map() load.  Run with the venv python that has piqueserver 1.4.2:
   python fb_pyspades.py OUTDIR   (OUTDIR holds floebreaker_day/night .vxl + .txt, each loaded as its own map name)"""
import importlib.util, json, os, sys, shutil, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from pyspades.vxl import VXLData
from aosmap import pipeline
out = sys.argv[1]
res = {}
for v in ('day', 'night'):
    f = os.path.join(out, f'floebreaker_{v}.vxl')
    data = open(f, 'rb').read()
    import io
    m = VXLData(io.BytesIO(data))
    gen = m.generate()
    r = {'bytes': len(data), 'pyspades_parse_ok': True, 'generate_identical': bytes(gen) == data}
    r['get_z_platform_end_206_250'] = m.get_z(206, 250)
    r['map_load'] = pipeline.piqueserver_map_load(out, f'floebreaker_{v}')
    res[v] = r
print(json.dumps(res, indent=1, default=str))
json.dump(res, open(os.path.join(out, 'validation_pyspades.json'), 'w'), indent=1, default=str)
