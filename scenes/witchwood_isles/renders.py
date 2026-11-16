"""usage: python renders.py OUTDIR  (reads OUTDIR/volume.npz and the .vxl colours via ww_gen.shade)"""
import os, sys
import numpy as np
import ww_gen
from ww_render import top_down, oblique, stamp_platform

out = sys.argv[1]
v = np.load(os.path.join(out, 'volume.npz'))
solid, mat = v['solid'], v['mat']
colors = v['colors'] if 'colors' in v.files else ww_gen.shade(solid, mat)
top_down(solid, colors, os.path.join(out, 'top_down.png'))
s, c = stamp_platform(solid, colors)
oblique(s, c, os.path.join(out, 'overview_south.png'), elev_deg=38, scale=1.6,
        crop=(0, 511, 90, 422), title='Overview from the south (preview render; cyan = script platform)')
oblique(s, c, os.path.join(out, 'blue_side_oblique.png'), elev_deg=34, yaw_deg=-28, scale=2.6,
        crop=(20, 262, 120, 392), title='Blue island and anchor mound, from the south-west')
oblique(s, c, os.path.join(out, 'centre_gap_closeup.png'), elev_deg=28, yaw_deg=-20, scale=4.0,
        crop=(150, 262, 214, 300), title='West water gap: boardwalk, pilings, mound + stairs under the platform end')
print('ok')
