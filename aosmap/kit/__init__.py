"""aosmap.kit: the shared map-making kit (2026-11-10).

It merges the helpers that every per-map generator in scenes/ used to copy:

    codec       VXL encode/decode on plain arrays + pyspades cross-check      (*_core.py, vxlcore.py, vxlio.py)
    noise       crc32-seeded value noise / fbm / hash                         (*_core.py, noise.py)
    canvas      Canvas: solid + rgb + material arrays, primitives, masks      (geo.World, *_build.poly_mask, ...)
    structures  stairs, spiral stairs, doors, windows, enterable buildings    (hc_build, bloomhop builds, generate.py)
    symmetry    mirror, floating components, orphan cleanup, trap fill        (gf_build, ds_core, bloomhop main, ...)
    color       mix/shade/ramp, baked light + AO, glow bake, team recolour    (bloomhop main, *_color.py)
    veg         trees with three random details, groves, saved OS seed        (sph_trees, bloomhop veg)
    tag         corner name tag on the ground                                 (paint_tag / corner_tag copies)
    sky         opt-in floating sky decor with the placement rules           (wkh_sky, sph_sky, bloomhop sky_decor)
    babel_checks the full Babel validation suite -> validation.json          (hc/wkh/sph/gf_check, bloomhop check)
    probe       live piqueserver probe in a temp config dir                  (server_test/*/scripts/*_probe.py)
    build       build.json, .txt writer, export + determinism helpers        (*_main.py, meta.py)
    preview     numpy previews (NOT client captures)                          (hc/wkh/sph_render.py)

Arrays are indexed [x, y, z]; x, y 0..511; z 0..63 with z = 0 the sky top and z = 63 the bottom.
Older generators in scenes/ are left as they were; new maps should import from here.
"""
from .codec import decode, encode, pack_rgb, unpack_rgb, surface_mask, pyspades_crosscheck  # noqa: F401
from .canvas import Canvas  # noqa: F401
from .params import BABEL_DEFAULT  # noqa: F401
