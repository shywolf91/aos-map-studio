"""Preview renders (numpy raycaster; not client captures)."""
import sys, os, math, numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(__file__))
import vxlcore

def topdown(S, C, path, scale=2):
    has = S.any(axis=2)
    ztop = np.argmax(S, axis=2)
    col = C[np.arange(512)[:, None], np.arange(512)[None, :], ztop].astype(float)
    water = ~S[:, :, 62]
    col[water] = col[water] * 0.55 + np.array([60, 150, 190]) * 0.45
    # hillshade from height
    h = -ztop.astype(float)
    gx = np.gradient(h, axis=0); gy = np.gradient(h, axis=1)
    sh = np.clip(1 + 0.08 * (-gx - gy), 0.7, 1.25)
    col = np.clip(col * sh[..., None], 0, 255).astype(np.uint8)
    im = Image.fromarray(col.transpose(1, 0, 2)).resize((512 * scale, 512 * scale), Image.NEAREST)
    im.save(path)

def persp(S, C, eye, look, path, w=960, h=540, fov=70, fog=(196, 204, 214), maxd=160, sky=(128, 184, 238)):
    eye = np.array(eye, float); look = np.array(look, float)
    fwd = look - eye; fwd /= np.linalg.norm(fwd)
    up = np.array([0, 0, -1.0])
    right = np.cross(fwd, up); right /= np.linalg.norm(right)
    up2 = np.cross(right, fwd)
    t = math.tan(math.radians(fov / 2))
    xs = (np.arange(w) - w / 2 + 0.5) / (w / 2) * t
    ys = (np.arange(h) - h / 2 + 0.5) / (w / 2) * t
    X, Y = np.meshgrid(xs, ys)
    d = fwd[None, None, :] + X[..., None] * right[None, None, :] - Y[..., None] * up2[None, None, :]
    d /= np.linalg.norm(d, axis=2, keepdims=True)
    d = d.reshape(-1, 3)
    out = np.zeros((d.shape[0], 3)); done = np.zeros(d.shape[0], bool); dist = np.full(d.shape[0], maxd, float)
    step = 0.25
    for i in range(int(maxd / step)):
        s = i * step
        idx = np.nonzero(~done)[0]
        if len(idx) == 0:
            break
        p = eye[None, :] + d[idx] * s
        px = np.floor(p[:, 0]).astype(int); py = np.floor(p[:, 1]).astype(int); pz = np.floor(p[:, 2]).astype(int)
        inb = (px >= 0) & (px < 512) & (py >= 0) & (py < 512) & (pz >= 0) & (pz < 64)
        hit = np.zeros(len(idx), bool)
        hit[inb] = S[px[inb], py[inb], pz[inb]]
        hit |= (pz >= 63) & (px >= 0) & (px < 512) & (py >= 0) & (py < 512)
        hi = idx[hit]
        if len(hi):
            qx, qy, qz = np.clip(px[hit], 0, 511), np.clip(py[hit], 0, 511), np.clip(pz[hit], 0, 63)
            c = C[qx, qy, qz].astype(float)
            wat = (qz >= 62) & ~S[qx, qy, np.minimum(qz, 62)]
            c[wat] = c[wat] * 0.6 + np.array([70, 160, 200]) * 0.4
            out[hi] = c; dist[hi] = s; done[hi] = True
    f = np.clip(dist / maxd, 0, 1) ** 1.3
    out[~done] = sky
    out[done] = out[done] * (1 - f[done, None]) + np.array(fog) * f[done, None]
    img = np.clip(out.reshape(h, w, 3), 0, 255).astype(np.uint8)
    Image.fromarray(img).save(path)

if __name__ == '__main__':
    d = sys.argv[1]
    data = open(os.path.join(d, 'bloomhop_kingdom.vxl'), 'rb').read()
    S, C = vxlcore.decode(data)
    os.makedirs(os.path.join(d, 'renders'), exist_ok=True)
    topdown(S, C, os.path.join(d, 'renders', 'top.png'))
    views = {
        'overview_from_platform': ((256, 256, -2), (130, 256, 46)),
        'overview_high_south': ((256, 470, 4), (256, 300, 50)),
        'overview_diag': ((60, 60, 2), (200, 200, 52)),
        'keep_inside': ((60, 262, 43), (48, 250, 42)),
        'lookout': ((180, 150, 44), (202, 136, 36)),
        'spawn_blue': ((112, 256, 42), (220, 256, 40)),
        'keep_front': ((112, 256, 40), (50, 256, 34)),
        'toy_hill': ((200, 230, 48), (256, 256, 48)),
        'north_centre': ((150, 190, 46), (256, 168, 52)),
        'south_centre': ((150, 330, 46), (250, 330, 52)),
        'north_flank': ((60, 96, 46), (200, 96, 46)),
        'ridge_fort': ((180, 380, 40), (256, 424, 40)),
        'tunnel': ((140, 415, 55.5), (230, 416, 55.5)),
        'grotto': ((242, 410, 53), (256, 424, 55)),
        'cottage': ((178, 220, 48), (178, 192, 44)),
        'red_side': ((392, 270, 40), (300, 250, 50)),
        'gate': ((176, 256, 44), (120, 256, 40)),
    }
    which = sys.argv[2:] or list(views)
    for k in which:
        e, l = views[k]
        persp(S, C, e, l, os.path.join(d, 'renders', k + '.png'))
        print('rendered', k)
