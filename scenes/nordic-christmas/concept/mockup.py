"""Concept mockups for nordic-christmas. Flat zones only. Run: python mockup.py
Each concept lists west-half shapes; mirror=True also draws x' = 512 - x.
Label on every image: concept mockup - not a map."""
import os
from PIL import Image, ImageDraw, ImageFont

S = 2
HERE = os.path.dirname(os.path.abspath(__file__))
try:
    F = ImageFont.truetype("arial.ttf", 15)
    FB = ImageFont.truetype("arialbd.ttf", 22)
except Exception:
    F = FB = ImageFont.load_default()


def sc(v):
    return int(round(v * S))


def mx(x0, x1):
    return 512 - x1, 512 - x0


def C(name):
    return name


def build(idx, title, bg, shapes, legend):
    W, H = 512 * S, 512 * S + 170
    img = Image.new("RGBA", (W, H), (30, 30, 36, 255))
    base = Image.new("RGBA", (512 * S, 512 * S), bg + (255,))
    img.paste(base, (0, 0))
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    labels = []

    def rect(x0, y0, x1, y1, col, a=255, lab=None, outline=None):
        d.rectangle([sc(x0), sc(y0), sc(x1), sc(y1)], fill=col + (a,),
                    outline=(outline + (255,)) if outline else None, width=2)
        if lab:
            labels.append((sc(x0) + 3, sc(y0) + 2, lab))

    def ell(cx, cy, rx, ry, col, a=255, lab=None, outline=None, dash=False):
        box = [sc(cx - rx), sc(cy - ry), sc(cx + rx), sc(cy + ry)]
        if dash:
            d.ellipse(box, outline=col + (255,), width=2)
        else:
            d.ellipse(box, fill=col + (a,), outline=(outline + (255,)) if outline else None, width=2)
        if lab:
            labels.append((sc(cx - rx) + 3, sc(cy) - 8, lab))

    def line(pts, col, w=3, lab=None, dash=False):
        p = [(sc(x), sc(y)) for x, y in pts]
        if dash:
            for (a, b), (c, e) in zip(p, p[1:]):
                n = max(1, int(((c - a) ** 2 + (e - b) ** 2) ** .5 // 14))
                for i in range(n):
                    if i % 2 == 0:
                        d.line([(a + (c - a) * i / n, b + (e - b) * i / n),
                                (a + (c - a) * (i + 1) / n, b + (e - b) * (i + 1) / n)], fill=col + (255,), width=w)
        else:
            d.line(p, fill=col + (255,), width=w)
        if lab:
            labels.append((p[0][0] + 4, p[0][1] - 18, lab))

    for sh in shapes:
        k = sh[0]
        m = sh[-1]
        a = list(sh[1:-1])
        variants = [a]
        if m:
            b = list(a)
            if k == "rect":
                b[0], b[2] = mx(a[0], a[2])
                if len(b) > 5 and isinstance(b[5], str):
                    b[5] = b[5] if False else b[5]
            elif k == "ell":
                b[0] = 512 - a[0]
            elif k == "line":
                b[0] = [(512 - x, y) for x, y in a[0]]
            variants.append(b)
        for v in variants:
            if k == "rect":
                rect(*v[:4], v[4], *(v[5:]))
            elif k == "ell":
                ell(*v[:5], *(v[5:]))
            elif k == "line":
                line(*v)
    # CTF strips, platform, spawn squares, tower zones always drawn
    rect(0, 128, 127, 383, (255, 220, 120), 46, None, (255, 200, 60))
    rect(384, 128, 511, 383, (255, 220, 120), 46, None, (255, 200, 60))
    labels.append((sc(4), sc(132), "CTF strip BLUE"))
    labels.append((sc(388), sc(132), "CTF strip RED"))
    rect(98, 236, 138, 276, (60, 90, 255), 200, "spawn B", (255, 255, 255))
    rect(374, 236, 414, 276, (255, 60, 60), 200, "spawn R", (255, 255, 255))
    rect(176, 240, 208, 271, (255, 255, 255), 70, None, (255, 255, 255))
    rect(304, 240, 336, 271, (255, 255, 255), 70, None, (255, 255, 255))
    labels.append((sc(150), sc(278), "tower zone B"))
    labels.append((sc(300), sc(278), "tower zone R"))
    rect(206, 240, 305, 271, (0, 255, 255), 160, "PLATFORM (script, z1)", (0, 120, 120))
    img = Image.alpha_composite(img, ov)
    d2 = ImageDraw.Draw(img)
    for x, y, t in labels:
        d2.text((x + 1, y + 1), t, fill=(0, 0, 0, 255), font=F)
        d2.text((x, y), t, fill=(255, 255, 255, 255), font=F)
    d2.rectangle([0, 0, 512 * S - 1, 512 * S - 1], outline=(255, 255, 255, 255))
    d2.text((10, 6), f"{title}", fill=(255, 255, 255, 255), font=FB)
    d2.text((10, 32), "concept mockup - not a map  (512 x 512, scale 2, west half mirrored x'=512-x)",
            fill=(255, 255, 160, 255), font=F)
    y = 512 * S + 8
    for line_ in legend:
        d2.text((10, y), line_, fill=(230, 230, 230, 255), font=F)
        y += 20
    img.convert("RGB").save(os.path.join(HERE, f"concept_{idx}.png"))


SNOW = (176, 184, 198)
FOREST = (46, 76, 66)
ICE = (140, 192, 214)
GOLD = (255, 190, 80)
CY = (90, 255, 220)

# ---------------- Concept 1: Hrafnfjord ----------------
c1 = [
    ("rect", 0, 0, 511, 112, FOREST, 255, "N fell forest + flank ridge (y~100)", False),
    ("rect", 0, 400, 511, 511, FOREST, 255, "S fell forest + flank ridge (y~412)", False),
    ("ell", 60, 60, 50, 36, (30, 60, 50), 255, None, None, True),
    ("ell", 60, 452, 50, 36, (30, 60, 50), 255, None, None, True),
    ("rect", 231, 0, 281, 511, ICE, 255, "frozen fjord (ice z44)", False),
    ("ell", 256, 256, 46, 72, ICE, 255, None, None, False),
    ("ell", 256, 256, 17, 17, (120, 130, 150), 255, "Thing-Rock isle", (255, 255, 255), False),
    ("rect", 132, 150, 178, 174, (150, 100, 60), 255, "Skali mead hall", (255, 220, 120), True),
    ("rect", 140, 186, 164, 206, (170, 70, 40), 255, "smithy", None, True),
    ("rect", 190, 190, 214, 228, (120, 90, 70), 255, "boat sheds", None, True),
    ("rect", 190, 284, 214, 322, (120, 90, 70), 255, "boat sheds", None, True),
    ("rect", 140, 296, 178, 320, (150, 100, 60), 255, "longhouse", None, True),
    ("rect", 138, 78, 166, 106, (190, 160, 110), 255, "stave church", None, True),
    ("rect", 232, 96, 280, 108, (200, 200, 210), 255, "RAVEN GATE arch", (255, 255, 255), False),
    ("rect", 244, 136, 268, 160, (255, 140, 40), 255, "YULE PYRE", (255, 230, 100), False),
    ("ell", 256, 352, 20, 20, (120, 130, 150), 255, "rune-stone ring", (255, 255, 255), False),
    ("ell", 52, 330, 30, 18, ICE, 255, "farm pond", None, True),
    ("line", [(20, 260), (95, 256)], GOLD, 3, None, True),
    ("line", [(138, 256), (176, 256)], (255, 255, 255), 5, "open front", True),
    ("line", [(10, 100), (500, 100)], CY, 3, "flank ridge route", True),
    ("line", [(10, 412), (500, 412)], CY, 3, None, True),
    ("line", [(256, 10), (256, 500)], (255, 255, 255), 2, "ice lane", False),
    ("ell", 256, 40, 16, 16, (255, 255, 200), 255, "SKY: moon", (255, 255, 200), False),
    ("line", [(310, 60), (380, 66), (440, 60)], (255, 120, 120), 3, "SKY: sleigh+reindeer", False),
]
build(1, "1  HRAFNFJORD - raven fjord thing-field", SNOW, c1, [
    "Ground Babel. Frozen fjord widens to an ice bay at the centre; Thing-Rock isle + rune ring + pyre + smithy + mead hall pack the middle.",
    "Cyan: flank ridge routes (y 100 / 412, 156 from centre). Gold shading: CTF strips (open farm fields, no roofs).",
    "Villages sit at x 130-215 (outside strips), n/s of the open front lane y 225-287.",
    "Corner tag: SW ground (x 8-60, y 470-500). Underground: NO.",
])

# ---------------- Concept 2: Haugr ----------------
MOOR = (122, 118, 112)
c2 = [
    ("ell", 256, 256, 120, 230, (140, 134, 128), 255, None, None, False),
    ("ell", 170, 120, 60, 34, (140, 134, 128), 255, None, None, True),
    ("ell", 170, 392, 60, 34, (140, 134, 128), 255, None, None, True),
    ("rect", 0, 70, 511, 102, ICE, 255, "frozen river Gjoll (N, y~86)", False),
    ("rect", 0, 410, 511, 440, ICE, 255, "frozen river (S, y~425)", False),
    ("ell", 256, 190, 34, 30, (96, 86, 78), 255, "KING'S BARROW", (255, 220, 120), False),
    ("ell", 256, 322, 34, 30, (96, 86, 78), 255, "QUEEN'S BARROW", (255, 220, 120), False),
    ("line", [(256, 190), (256, 322)], (190, 120, 255), 4, "underground draugr road", True),
    ("line", [(256, 190), (160, 130)], (190, 120, 255), 3, None, True),
    ("line", [(256, 322), (160, 382)], (190, 120, 255), 3, None, True),
    ("ell", 178, 160, 20, 20, (170, 170, 180), 255, "Seven Sisters ring", None, True),
    ("ell", 178, 352, 18, 18, (170, 170, 180), 255, None, None, True),
    ("rect", 240, 84, 272, 98, (230, 226, 210), 255, "WHALE-JAW GATE", (255, 255, 255), False),
    ("rect", 145, 306, 177, 332, (170, 70, 40), 255, "dwarf forge cave", None, True),
    ("rect", 140, 392, 166, 416, (190, 160, 110), 255, "stave church", None, True),
    ("rect", 20, 40, 100, 66, (150, 100, 60), 255, "shieling hamlet", None, True),
    ("ell", 118, 256, 38, 38, (255, 255, 255), 255, None, None, True, True),
    ("line", [(138, 256), (176, 256)], (255, 255, 255), 5, "open front", True),
    ("line", [(10, 120), (500, 120)], CY, 3, "flank: river bank y~120", True),
    ("line", [(10, 392), (500, 392)], CY, 3, None, True),
    ("ell", 80, 456, 18, 18, (255, 255, 200), 255, "SKY: moon", (255, 255, 200), False),
    ("line", [(330, 50), (400, 56), (470, 50)], (255, 120, 120), 3, "SKY: sleigh", False),
]
build(2, "2  HAUGR - the barrow downs", MOOR, c2, [
    "Ground Babel. Rolling heather moor, spawn dells (white rings = rim hills), two enterable barrows flank the platform lane.",
    "Purple: UNDERGROUND draugr road (z 50-57) joins both barrows + flank shafts; ground stays solid elsewhere.",
    "CTF strips = grave fields: rounded cairns <=2 high, stone stubs, no roofs. Hamlets/church outside the strips.",
    "Corner tag: SE ground (x 450-505, y 470-500).",
])

# ---------------- Concept 3: Skogarborg ----------------
c3 = [
    ("rect", 0, 0, 511, 511, (44, 72, 62), 255, None, False),
    ("ell", 256, 256, 70, 90, (38, 62, 52), 255, "YULE WOOD (dense grove centre)", (200, 255, 200), False),
    ("ell", 256, 68, 78, 34, ICE, 255, "frozen lake N", None, False),
    ("ell", 256, 444, 78, 34, ICE, 255, "frozen lake S", None, False),
    ("rect", 0, 128, 127, 383, (130, 138, 150), 255, None, False),
    ("rect", 384, 128, 511, 383, (130, 138, 150), 255, None, False),
    ("rect", 128, 224, 212, 288, (170, 178, 190), 255, "open front lane", True),
    ("rect", 234, 140, 280, 164, (150, 100, 60), 255, "ANTLER HALL", (255, 220, 120), False),
    ("ell", 256, 356, 28, 28, (140, 110, 80), 255, "ring fort", (255, 220, 120), False),
    ("rect", 180, 176, 204, 196, (120, 90, 70), 255, "hunting lodge", None, True),
    ("rect", 180, 316, 204, 336, (120, 90, 70), 255, "hunting lodge", None, True),
    ("rect", 168, 62, 184, 78, (255, 140, 40), 255, "beacon", None, True),
    ("rect", 168, 434, 184, 450, (255, 140, 40), 255, "beacon", None, True),
    ("ell", 60, 200, 22, 16, (110, 90, 70), 255, "charcoal clearing", None, True),
    ("line", [(10, 68), (500, 68)], CY, 3, "flank: lake-ice route", True),
    ("line", [(10, 444), (500, 444)], CY, 3, None, True),
    ("line", [(138, 256), (212, 256)], (255, 255, 255), 5, None, True),
    ("ell", 256, 30, 16, 16, (255, 255, 200), 255, "SKY: moon", (255, 255, 200), False),
    ("ell", 256, 484, 26, 20, (255, 210, 90), 255, "SKY: yule wreath ring", (255, 230, 120), False),
    ("line", [(80, 480), (150, 486), (200, 480)], (255, 120, 120), 3, "SKY: sleigh", False),
]
build(3, "3  SKOGARBORG - the yule wood", (44, 72, 62), c3, [
    "Ground Babel. Dense Yule Wood in the centre (enclosed, 7-10 gaps), exposed frozen-lake flanks N/S, burghs on the centre axis.",
    "CTF strips = felled charcoal clearings (stumps, log stacks, thin saplings; no canopies, no roofs).",
    "Open front lane y 224-288 stays passable; trees only low/thin there. Under-platform grove 15-45 % coverage, >=25 air.",
    "Corner tag: NW ground (x 8-60, y 8-40).",
])
print("ok")
