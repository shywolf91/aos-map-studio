"""Close-up preview renders of the two skeletal hands (numpy splat, not a client)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'wicker_kings_harvest'))
from wkh_render import view
from gf_core import read_vxl
out = sys.argv[1]
s, c, _ = read_vxl(open(os.path.join(out, 'graveyard_of_the_forgotten.vxl'), 'rb').read())
sd = os.path.join(out, 'renders', '')
shots = {
 'hand_up_e': dict(cam=(320, 70, 32), look=(256, 66, 34), region=((210, 300), (20, 110))),
 'hand_up_s': dict(cam=(256, 130, 26), look=(256, 64, 36), region=((210, 300), (20, 110))),
 'hand_claw_e': dict(cam=(320, 430, 30), look=(256, 434, 20), region=((210, 300), (390, 480))),
 'hand_claw_n': dict(cam=(256, 370, 30), look=(256, 434, 20), region=((210, 300), (390, 480))),
}
for k, kw in shots.items():
    if len(sys.argv) > 2 and k not in sys.argv[2:]: continue
    view(s, c, fov=55, size=(960, 640), **kw).save(sd + k + '.png')
