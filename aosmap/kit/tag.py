"""Corner tag: the map name only, painted on the ground in a free corner (owner rule; no credit line).

Merged from gf/hc_color.paint_tag, wkh/sph_main.paint_tag, Bloomhop main.corner_tag, Haunted Fairground
corner_tag and ww_font, on top of the shared 5x7 font in aosmap.pixelfont.
"""
from __future__ import annotations

import numpy as np

from ..pixelfont import text_mask

CORNERS = ('SW', 'SE', 'NW', 'NE')


def tag_rect(text, corner='SW', margin=8, scale=1):
    m = text_mask([text.upper()])
    w, h = m.shape[0] * scale, m.shape[1] * scale
    x0 = margin if corner in ('SW', 'NW') else 512 - margin - w
    y0 = margin if corner in ('NW', 'NE') else 512 - margin - h
    return x0, x0 + w - 1, y0, y0 + h - 1


def paint_tag(cv, text, corner='SW', margin=8, scale=1, rgb=(222, 206, 160), shadow=(70, 60, 52), raised=False,
              level=True):
    """Paint `text` on the ground. level=True flattens only the strip under the tag (owner: clear only the area
    under the tag). raised=True puts the letters 1 voxel above the ground instead of painting the top.
    Returns (x0, x1, y0, y1, z) for build.json ('tag_rect') and the mirror-check exclusion."""
    m = text_mask([text.upper()])
    if scale > 1:
        m = np.kron(m, np.ones((scale, scale), bool))
    x0, x1, y0, y1 = tag_rect(text, corner, margin, scale)
    pad = 2
    bx0, bx1, by0, by1 = max(0, x0 - pad), min(511, x1 + pad), max(0, y0 - pad), min(511, y1 + pad)
    tops = np.argmax(cv.solid[bx0:bx1 + 1, by0:by1 + 1], axis=2)
    z = int(np.median(tops))
    if level:
        under = cv.rgb[bx0:bx1 + 1, by0:by1 + 1, :].copy()
        col = tuple(int(v) for v in np.median(under[np.arange(tops.shape[0])[:, None],
                                                     np.arange(tops.shape[1])[None, :], tops], axis=(0, 1)))
        cv.carve(bx0, bx1, by0, by1, 0, z - 1)
        cv.box(bx0, bx1, by0, by1, z, 63, None)
        sub = cv.rgb[bx0:bx1 + 1, by0:by1 + 1, z]
        need = (tops > z)
        sub[need] = col
    for (i, j) in zip(*np.nonzero(m)):
        x, y = x0 + i, y0 + j
        if raised:
            cv.set(x, y, z - 1, rgb, 'tag')
        else:
            cv.rgb[x, y, z] = rgb
            if shadow is not None and x + 1 <= 511 and y + 1 <= 511 and not m[min(i + 1, m.shape[0] - 1),
                                                                               min(j + 1, m.shape[1] - 1)]:
                cv.rgb[x + 1, y + 1, z] = shadow
    return (bx0, bx1, by0, by1, z)
