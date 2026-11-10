"""Death Swamp colour pass. Palette taken from the owner's swamp screenshot: teal water with dark ink halos
around every island, olive/khaki boulders with yellow-green moss caps, near-black dead trees, amber specks.

Variation is structured (coherent fbm, height ramps, crevice occlusion, face orientation); per-voxel jitter is
small. Noise is sampled on x folded about the mirror axis so both lanes match.
Push safety: every channel is clamped to 6..249 so no authored colour reaches HLS saturation 255, i.e. none can
match a team colour's hue+saturation (push.py compare_hs) - checked again by validate.check_push.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

import ds_build as B
from ds_core import MX, MY, MZ, fbm2, fold_x, hash3, mirror_x, pack_rgb
from aosmap.pixelfont import text_mask

C = np.array


def lerp(a, b, t):
    t = np.asarray(t, np.float32)[..., None]
    return np.asarray(a, np.float32) * (1 - t) + np.asarray(b, np.float32) * t


def ramp3(lo, mid, hi, t):
    t = np.clip(np.asarray(t, np.float32), 0, 1)
    return np.where((t < 0.5)[..., None], lerp(lo, mid, t * 2), lerp(mid, hi, (t - 0.5) * 2))


# ------------------------------------------------------------------------------------------ palette
ROCK_LO, ROCK_MID, ROCK_HI = (72, 72, 58), (118, 116, 90), (160, 156, 122)
MOSS_LO, MOSS_MID, MOSS_HI = (92, 100, 48), (124, 128, 58), (160, 154, 70)
PEAT_LO, PEAT_MID, PEAT_HI = (70, 72, 46), (92, 98, 54), (116, 118, 64)
BANK_WET, BANK_DRY = (64, 72, 62), (98, 92, 66)
SOIL = (80, 68, 50)
PATH_LO, PATH_HI = (104, 94, 70), (136, 124, 92)
FLAG_A, FLAG_B, FLAG_JOINT = (142, 140, 120), (126, 126, 108), (92, 94, 80)
RUNE = (92, 156, 146)
STONE_SIDE, STONE_TOP = (118, 118, 106), (140, 142, 92)
BARK_LO, BARK_HI = (52, 48, 44), (78, 70, 60)
TWIG = (98, 88, 74)
ROOT = (68, 62, 52)
HANGMOSS = (126, 132, 82)
BONE_TOP, BONE_SIDE, BONE_STAIN, BONE_CRACK = (214, 206, 174), (184, 174, 144), (134, 142, 100), (126, 118, 96)
SOCKET = (60, 58, 54)
POST = (90, 76, 58)
LANTERN, LANTERN_CAP = (246, 178, 70), (64, 58, 52)
GLOWCAP_A, GLOWCAP_B = (238, 170, 66), (212, 136, 52)
TUFT = (140, 140, 64)
REED = (116, 124, 64)
CATTAIL = (88, 70, 50)

WATER_DEEP, WATER_MIST, WATER_INK = (58, 126, 130), (98, 164, 158), (30, 62, 72)
ALGAE, LILY, FIREFLY = (136, 198, 180), (92, 140, 88), (238, 188, 92)
TAG_RGB, TAG_OUT = (206, 196, 160), (34, 58, 64)


def colorize(M):
    solid = M > 0
    solid[:, :, 63] = True
    surf = B_surface(solid)
    sky_open = np.zeros_like(solid)
    sky_open[:, :, 0] = solid[:, :, 0]
    sky_open[:, :, 1:] = solid[:, :, 1:] & ~solid[:, :, :-1]
    under = np.zeros_like(solid)
    under[:, :, :-1] = solid[:, :, :-1] & ~solid[:, :, 1:]
    occ = ndi.uniform_filter(solid.astype(np.float32), size=3, mode='constant', cval=1.0)
    color = np.zeros(solid.shape, np.uint32)

    big = mirror_x(fbm2((MX, MY), 24, 3, 'col_big'))
    fine = mirror_x(fbm2((MX, MY), 6, 2, 'col_fine'))
    mossn = mirror_x(fbm2((MX, MY), 10, 3, 'col_moss'))

    x, y, z = np.nonzero(surf & (M > 0))
    mid = M[x, y, z]
    so = sky_open[x, y, z]; un = under[x, y, z]; oc = occ[x, y, z]
    fx = fold_x(x)
    bn = big[x, y]; fn = fine[x, y]; mn = mossn[x, y]
    h = (63 - z).astype(np.float32)
    jit = (hash3(fx, y, z, 3) - 0.5) * 6                                 # +-3 value jitter
    crev = np.clip((oc - 0.55) * 1.6, 0, 0.45)                          # enclosed -> darker
    rgb = np.zeros((len(x), 3), np.float32)

    def sel(m):
        return mid == m

    # rock (boulders, islets): khaki body, moss caps on top faces, darker sides/undersides, crevices
    s = sel(B.ROCK) | sel(B.ISLET_ROCK)
    t = 0.30 + 0.45 * bn[s] + 0.25 * np.clip((h[s] - 4) / 22, 0, 1) + 0.12 * (fn[s] - 0.5)
    body = ramp3(ROCK_LO, ROCK_MID, ROCK_HI, t)
    moss = ramp3(MOSS_LO, MOSS_MID, MOSS_HI, 0.25 + 0.6 * mn[s] + 0.15 * fn[s])
    is_moss = so[s] & ((mn[s] + 0.3 * fn[s] + 0.012 * (h[s] - 10)) > 0.62)
    side_f = np.where(so[s], 1.0, np.where(un[s], 0.62, 0.84))
    c = np.where(is_moss[:, None], moss, body * side_f[:, None])
    # mossy drip on the upper sides just below a moss cap
    drip = (~so[s]) & (mn[s] > 0.62) & (hash3(fx[s], y[s], z[s], 5) < 0.35)
    c = np.where(drip[:, None], lerp(c, MOSS_LO, 0.55), c)
    rgb[s] = c * (1 - crev[s])[:, None]

    s = sel(B.PEAT)
    c = ramp3(PEAT_LO, PEAT_MID, PEAT_HI, 0.2 + 0.55 * bn[s] + 0.25 * fn[s])
    bog = (mn[s] < 0.34)                                     # wet black-green bog hollows
    c = np.where(bog[:, None], lerp(c, (58, 66, 50), 0.7), c)
    rgb[s] = c * (1 - crev[s] * 0.6)[:, None]
    s = sel(B.BANK)
    wet = np.clip((z[s] - 56) / 4.0, 0, 1)
    c = lerp(BANK_DRY, BANK_WET, wet)
    rgb[s] = np.where(so[s][:, None], c, c * 0.8)
    s = sel(B.SOIL)
    rgb[s] = lerp(SOIL, (60, 54, 42), np.clip((z[s] - 54) / 8, 0, 1)) * (0.92 + 0.1 * fn[s])[:, None]
    s = sel(B.PATH)
    rgb[s] = lerp(PATH_LO, PATH_HI, 0.3 + 0.5 * fn[s] + 0.2 * bn[s])
    # flagstones: 3x3 slabs with darker joints, two alternating tones
    s = sel(B.FLAG)
    joint = ((fx[s] % 4) == 0) | ((y[s] % 4) == 0)
    alt = ((fx[s] // 4 + y[s] // 4) % 2) == 0
    c = np.where(alt[:, None], C(FLAG_A, np.float32), C(FLAG_B, np.float32)) + 0 * rgb[s]
    c = np.where(joint[:, None], C(FLAG_JOINT, np.float32), c)
    mossy = (mn[s] > 0.62) & joint
    c = np.where(mossy[:, None], C(MOSS_LO, np.float32), c)
    rgb[s] = np.where(so[s][:, None], c, c * 0.78)
    s = sel(B.RUNE)
    rgb[s] = np.where(so[s][:, None], C(RUNE, np.float32), C(RUNE, np.float32) * 0.7)
    s = sel(B.STONE)
    c = lerp(STONE_SIDE, (96, 98, 88), np.clip((z[s] - 46) / 8, 0, 1))
    rgb[s] = np.where(so[s][:, None], C(STONE_TOP, np.float32), c * (1 - crev[s])[:, None])
    s = sel(B.BARK)
    rgb[s] = lerp(BARK_LO, BARK_HI, np.clip(0.2 + (h[s] - 8) / 30 + 0.3 * (fn[s] - 0.5), 0, 1))
    rgb[sel(B.TWIG)] = TWIG
    rgb[sel(B.ROOT)] = ROOT
    rgb[sel(B.HANGMOSS)] = HANGMOSS
    # bone: pale tops, warm sides, green algae stain toward the waterline, darker cracks
    s = sel(B.BONE)
    c = np.where(so[s][:, None], C(BONE_TOP, np.float32), C(BONE_SIDE, np.float32))
    stain = np.clip((z[s] - 46) / 14, 0, 1) * (0.55 + 0.45 * mn[s])
    c = lerp(c, BONE_STAIN, stain * 0.85)
    crack = hash3(fx[s] // 2, y[s] // 3, z[s] // 2, 8) < 0.06
    c = np.where(crack[:, None], C(BONE_CRACK, np.float32), c)
    mtop = so[s] & (mn[s] + 0.4 * (fn[s] - 0.5) > 0.66)
    c = np.where(mtop[:, None], lerp(MOSS_MID, MOSS_LO, fn[s]), c)
    rgb[s] = c * (1 - 0.7 * crev[s])[:, None] * np.where(un[s], 0.7, 1.0)[:, None]
    rgb[sel(B.SOCKET)] = SOCKET
    rgb[sel(B.POST)] = POST
    rgb[sel(B.LANTERN)] = LANTERN
    rgb[sel(B.LANTERN_CAP)] = LANTERN_CAP
    s = sel(B.GLOWCAP)
    rgb[s] = np.where((hash3(fx[s], y[s], z[s], 2) < 0.5)[:, None], C(GLOWCAP_A, np.float32), C(GLOWCAP_B, np.float32))
    rgb[sel(B.TUFT)] = TUFT
    rgb[sel(B.REED)] = REED
    rgb[sel(B.CATTAIL)] = CATTAIL

    unshaded = np.isin(mid, (B.LANTERN, B.GLOWCAP, B.RUNE, B.SOCKET))
    rgb = np.where(unshaded[:, None], rgb, rgb + jit[:, None])
    color[x, y, z] = pack_rgb(np.clip(rgb, 6, 249))

    # ---- painted water plane (z = 63)
    color[:, :, 63] = pack_rgb(paint_water(M))
    return color


def B_surface(solid):
    air = ~solid
    e = np.zeros_like(solid)
    e[:, :, 0] = True
    e[:, :, 1:] |= air[:, :, :-1]; e[:, :, :-1] |= air[:, :, 1:]
    e[1:] |= air[:-1]; e[:-1] |= air[1:]
    e[:, 1:] |= air[:, :-1]; e[:, :-1] |= air[:, 1:]
    return solid & e


def paint_water(M):
    """Teal swamp water with ink halos around every land column, mist, ripple rings, algae, lilies,
    firefly glints, a soft edge vignette and the corner name tag."""
    land = M[:, :, 62] > 0
    dw = ndi.distance_transform_edt(~land)
    mist = mirror_x(fbm2((MX, MY), 48, 4, 'mist'))
    fine = mirror_x(fbm2((MX, MY), 8, 2, 'wfine'))
    X, Y = np.indices((MX, MY))
    fx = fold_x(X)
    c = lerp(WATER_DEEP, WATER_MIST, np.clip((mist - 0.35) * 1.8, 0, 1) * 0.85)
    halo = np.exp(-dw / 10.0)
    c = lerp(c, WATER_INK, np.clip(0.82 * halo + 0.1 * (fine - 0.5), 0, 0.86))
    ripple = (dw > 2) & (dw < 16) & (np.sin(dw * 1.05 + mist * 3) > 0.92)
    c = np.where(ripple[..., None], c * 0.9, c)
    algae_cl = mirror_x(fbm2((MX, MY), 9, 2, 'algae'))
    h = hash3(fx, Y, 0, 41)
    algae = (algae_cl > 0.6) & (h < 0.3) & (dw > 3)
    c = np.where(algae[..., None], lerp(c, ALGAE, 0.75), c)
    lily = (algae_cl > 0.66) & (hash3(fx // 2, Y // 2, 0, 43) < 0.10) & (dw > 4)
    c = np.where(lily[..., None], C(LILY, np.float32), c)
    ff = (hash3(fx, Y, 0, 47) < 0.0016 + 0.004 * halo) & (dw > 1)
    c = np.where(ff[..., None], C(FIREFLY, np.float32), c)
    edge = np.minimum(np.minimum(X, 511 - X), np.minimum(Y, 511 - Y))
    vig = np.clip((edge - 4) / 60.0, 0, 1)
    c = lerp(lerp(c, (36, 70, 78), 0.5), c, vig)
    # corner tag: map name only, painted on the water in the SW corner
    tm = text_mask(['DEATH', 'SWAMP'], spacing=1)
    tm = np.kron(tm, np.ones((2, 2), bool))
    x0, y0 = 14, 512 - 14 - tm.shape[1]
    assert not land[x0 - 2:x0 + tm.shape[0] + 2, y0 - 2:y0 + tm.shape[1] + 2].any(), 'tag over land'
    tag = np.zeros((MX, MY), bool)
    tag[x0:x0 + tm.shape[0], y0:y0 + tm.shape[1]] = tm
    out = ndi.binary_dilation(tag, iterations=1) & ~tag
    c = np.where(out[..., None], C(TAG_OUT, np.float32), c)
    c = np.where(tag[..., None], C(TAG_RGB, np.float32), c)
    return np.clip(c, 6, 249)
