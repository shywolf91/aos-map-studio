"""Concept mockups for babel-ideas: three flat top-down sketches (512x512 map, scale 2).
Not a map. Run: python mockup.py   -> concept_1.png, concept_2.png, concept_3.png next to this file.
Mirror flags: 'x' (x' = 512-x), 'y' (y' = 512-y), 'xy' both.
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

S = 2
HERE = os.path.dirname(os.path.abspath(__file__))
try:
    F = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 12)
    FB = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 15)
except OSError:
    F = FB = ImageFont.load_default()

PLATFORM = (206, 240, 305, 271)
SPAWNS = [(98, 236, 138, 276, "BLUE spawn"), (374, 236, 414, 276, "RED spawn")]
TOWERZONES = [(176, 236, 208, 276), (304, 236, 336, 276)]


def mirrors(mode):
    out = [lambda x, y: (x, y)]
    if mode in ("x", "xy"):
        out.append(lambda x, y: (512 - x, y))
    if mode in ("y", "xy"):
        out.append(lambda x, y: (x, 512 - y))
    if mode == "xy":
        out.append(lambda x, y: (512 - x, 512 - y))
    return out


class Canvas:
    def __init__(self, base, title, subtitle, legend):
        self.w = 512 * S
        self.head = 46
        self.leg = 20 * (len(legend) + 1) + 14
        self.img = Image.new("RGB", (self.w, self.w + self.head + self.leg), (28, 28, 32))
        self.d = ImageDraw.Draw(self.img)
        self.d.rectangle((0, self.head, self.w, self.head + self.w), fill=base)
        self.title, self.subtitle, self.legend = title, subtitle, legend

    def P(self, x, y):
        return (x * S, y * S + self.head)

    def rect(self, x0, y0, x1, y1, col, mode=None, label=None, outline=None):
        for m in mirrors(mode):
            a = m(x0, y0)
            b = m(x1, y1)
            xa, xb = sorted((a[0], b[0]))
            ya, yb = sorted((a[1], b[1]))
            self.d.rectangle((*self.P(xa, ya), *self.P(xb, yb)), fill=col, outline=outline)
            if label:
                self.d.text(self.P(xa + 2, ya + 2), label, fill=(20, 20, 20), font=F)

    def ell(self, cx, cy, rx, ry, col, mode=None, label=None, outline=None):
        for m in mirrors(mode):
            x, y = m(cx, cy)
            self.d.ellipse((*self.P(x - rx, y - ry), *self.P(x + rx, y + ry)), fill=col, outline=outline)
            if label:
                self.d.text(self.P(x - rx + 2, y - 6), label, fill=(20, 20, 20), font=F)

    def line(self, pts, col, width=3, mode=None):
        for m in mirrors(mode):
            q = [self.P(*m(x, y)) for x, y in pts]
            self.d.line(q, fill=col, width=width * S, joint="curve")

    def dots(self, pts, r, col, mode=None):
        for m in mirrors(mode):
            for x, y in pts:
                x, y = m(x, y)
                self.d.ellipse((*self.P(x - r, y - r), *self.P(x + r, y + r)), fill=col)

    def landmark(self, n, cx, cy, w, h, name, col=(255, 255, 255), side="r"):
        self.d.rectangle((*self.P(cx - w / 2, cy - h / 2), *self.P(cx + w / 2, cy + h / 2)), outline=(0, 0, 0), width=2, fill=col)
        self.d.ellipse((*self.P(cx - 8, cy - 8), *self.P(cx + 8, cy + 8)), fill=(0, 0, 0))
        self.d.text(self.P(cx - 3 - (3 if n > 9 else 0), cy - 7), str(n), fill=(255, 255, 255), font=F)

    def text(self, x, y, s, col=(20, 20, 20)):
        self.d.text(self.P(x, y), s, fill=col, font=F)

    def overlay(self):
        d = self.d
        # flank bands, centre zone
        for y in (46, 126, 386, 466):
            d.line([self.P(0, y), self.P(512, y)], fill=(255, 255, 255), width=1)
        d.rectangle((*self.P(156, 150), *self.P(356, 362)), outline=(255, 255, 0), width=2)
        d.rectangle((*self.P(*PLATFORM[:2]), *self.P(PLATFORM[2], PLATFORM[3])), fill=(0, 255, 255), outline=(0, 0, 0), width=2)
        d.text(self.P(222, 248), "PLATFORM", fill=(0, 0, 0), font=F)
        for x0, y0, x1, y1, lab in SPAWNS:
            col = (230, 40, 40) if "RED" in lab else (40, 60, 255)
            d.rectangle((*self.P(x0, y0), *self.P(x1, y1)), outline=col, width=3, fill=None)
            d.text(self.P(x0, y0 - 14), lab, fill=col, font=FB)
        for z in TOWERZONES:
            d.rectangle((*self.P(z[0], z[1]), *self.P(z[2], z[3])), outline=(255, 140, 0), width=2)
        d.text(self.P(160, 280), "tower zone", fill=(255, 140, 0), font=F)
        d.text(self.P(300, 280), "tower zone", fill=(255, 140, 0), font=F)

    def finish(self, path):
        d = self.d
        d.rectangle((0, 0, self.w, self.head), fill=(20, 20, 24))
        d.text((8, 4), self.title, fill=(255, 255, 255), font=FB)
        d.text((8, 24), self.subtitle + "   |   concept mockup - not a map", fill=(255, 200, 80), font=F)
        # grid ticks every 64
        for g in range(0, 513, 64):
            d.text(self.P(g + 1, 1), str(g), fill=(255, 255, 255), font=F)
        y0 = self.head + self.w + 6
        d.text((8, y0), "Legend (yellow box = centre zone, white lines = flank bands 130/210 from centre, orange = tower zones)", fill=(230, 230, 230), font=F)
        for i, (col, txt) in enumerate(self.legend):
            yy = y0 + 20 * (i + 1)
            d.rectangle((8, yy, 28, yy + 14), fill=col, outline=(0, 0, 0))
            d.text((36, yy), txt, fill=(230, 230, 230), font=F)
        self.img.save(path)


# ---------------------------------------------------------------- concept 1
def c1():
    SAND, DUNE, MESA, PAN, WASH, STONE = (216, 178, 122), (200, 150, 96), (168, 98, 66), (234, 228, 212), (150, 112, 84), (190, 120, 84)
    leg = [(SAND, "sand flats (ground z 46)"), (DUNE, "dune shoulders / front dressing"), (MESA, "mesas z 24-30 (corners, N/S edges)"),
           (PAN, "salt pan + evaporation dikes (centre)"), (WASH, "The Wash: dry canyon flank route (z 52 floor)"),
           (STONE, "hoodoos / ruins"), ((60, 130, 70), "oasis camp + palms (spawn)")]
    c = Canvas(SAND, "1  SUNSCAR REACH - ground Babel, desert salt flat, late-afternoon amber",
               "stock Babel, no assist; build gap ~44", leg)
    c.ell(256, 30, 120, 40, MESA, label="N mesa shelf")
    c.ell(256, 482, 120, 40, MESA, label="S mesa shelf")
    c.ell(46, 60, 60, 50, MESA, "xy")
    c.ell(190, 360 + 40, 30, 12, DUNE, "x")
    c.rect(186, 176, 326, 336, PAN, label="salt pan")
    c.line([(20, 120), (110, 104), (200, 92), (256, 98), (312, 92), (402, 104), (492, 120)], WASH, 12, "y")
    c.ell(118, 256, 52, 48, (150, 180, 100), "x")
    c.dots([(60, 232), (66, 272), (74, 254), (60, 300), (62, 214)], 6, (60, 130, 70), "x")
    # front dressing: low dune ridges / cairns (not blocking)
    c.dots([(150, 224), (158, 296), (168, 214), (172, 300), (190, 208), (186, 306), (150, 256 + 0)], 4, DUNE, "x")
    # centre: hoodoo field
    hood = [(204, 170), (230, 160), (284, 164), (310, 174), (200, 210), (316, 206), (200, 300), (312, 304), (222, 330), (292, 332),
            (236, 300), (276, 296), (240, 230), (276, 228), (226, 262), (286, 262), (256, 256), (246, 282), (268, 244)]
    c.dots(hood, 5, STONE)
    c.rect(214, 140, 298, 176, (180, 120, 90), label="caravanserai")
    c.ell(256, 322, 24, 24, (240, 232, 200), label="")
    c.line([(60, 256), (150, 256), (206, 256)], (255, 255, 255), 2, "x")  # open front
    c.line([(124, 292), (100, 372), (110, 420), (150, 436)], (255, 255, 255), 2, "xy")  # flank access
    c.landmark(1, 256, 210, 14, 14, "Great Gnomon", (255, 235, 150))
    c.landmark(2, 256, 322, 26, 26, "Heliostat Court", (255, 255, 255))
    c.landmark(3, 256, 100, 40, 12, "Dunewreck", (200, 255, 255))
    c.landmark(4, 256, 416, 30, 30, "Cistern Stair", (200, 255, 255))
    c.landmark(5, 140, 120, 22, 16, "Needle Gate", (255, 220, 200))
    c.landmark(6, 372, 396, 22, 16, "Needle Gate 2", (255, 220, 200))
    c.landmark(7, 256, 160, 30, 12, "Caravanserai", (255, 200, 150))
    c.overlay()
    c.text(8, 470, "1 Great Gnomon  2 Heliostat Court  3 Dunewreck  4 Cistern Stair  5/6 Needle Gates  7 Caravanserai")
    c.finish(os.path.join(HERE, "concept_1.png"))


# ---------------------------------------------------------------- concept 2
def c2():
    WATER, SHALLOW, LAND, TERR, KARST, BAMB = (110, 170, 168), (140, 195, 188), (120, 170, 90), (170, 200, 110), (150, 160, 150), (70, 140, 80)
    leg = [(WATER, "paddy lake / shallow wading (seabed z 59)"), (LAND, "spawn plateau z 42 (rice terraces step down)"),
           (TERR, "terrace steps = safe way down"), (KARST, "karst pillars z 14-30 (cores solid to seabed)"),
           (BAMB, "bamboo ridge islets: flank route"), ((200, 150, 90), "causeways / plank bridges"), ((235, 235, 240), "mist (painted z 63 cloud sea, visual)")]
    c = Canvas(WATER, "2  JADEWATER KARSTS - island Babel in a paddy lake, misty jade dawn",
               "stock Babel, no assist; build gap ~41 (lower ground = honest tower race)", leg)
    c.ell(256, 256, 120, 110, SHALLOW)
    c.ell(112, 256, 86, 78, LAND, "x")
    c.rect(150, 226, 216, 286, LAND, "x")
    for i, r in enumerate((62, 48, 34)):
        c.ell(110, 256, r, r * 0.9, [(150, 190, 100), TERR, (190, 215, 130)][i], "x")
    c.ell(256, 50, 170, 24, BAMB, "y")
    c.ell(60, 120, 36, 24, BAMB, "xy")
    # causeways from plateau to centre
    c.line([(214, 200), (240, 190), (256, 160)], (200, 150, 90), 5, "xy")
    c.line([(216, 312), (240, 330), (256, 352)], (200, 150, 90), 5, "xy")
    c.line([(60, 160), (80, 100), (150, 60), (256, 50), (362, 60), (432, 100), (452, 160)], (200, 150, 90), 3)
    c.line([(60, 352), (80, 412), (150, 452), (256, 462), (362, 452), (432, 412), (452, 352)], (200, 150, 90), 3)
    # karst pillars
    pil = [(226, 180, 9), (290, 178, 8), (200, 218, 7), (312, 214, 7), (236, 330, 10), (284, 336, 8), (206, 292, 7), (314, 296, 8),
           (256, 126, 12), (256, 392, 12), (170, 130, 9), (342, 130, 9), (170, 384, 9), (342, 384, 9), (256, 212, 8), (230, 270, 6), (284, 252, 6)]
    for x, y, r in pil:
        c.ell(x, y, r, r, KARST, outline=(60, 70, 60))
    c.rect(226, 342, 290, 368, (200, 150, 90), label="stilt market")
    c.landmark(1, 256, 356, 36, 12, "Moon Gate Bridge", (255, 255, 255))
    c.landmark(2, 256, 126, 22, 22, "Cloud Ladder", (255, 235, 150))
    c.landmark(3, 236, 330, 18, 18, "Bell Pagoda", (255, 200, 150))
    c.landmark(4, 256, 24, 40, 14, "Waterfall Scar", (200, 255, 255))
    c.landmark(5, 256, 460, 40, 14, "Cormorant Raft Village", (200, 255, 255))
    c.landmark(6, 256, 188, 36, 10, "Bamboo Aqueduct", (255, 220, 200))
    c.overlay()
    c.text(8, 470, "1 Moon Gate Bridge  2 Cloud Ladder  3 Bell Pagoda  4 Waterfall Scar  5 Raft Village  6 Aqueduct")
    c.finish(os.path.join(HERE, "concept_2.png"))


# ---------------------------------------------------------------- concept 3
def c3():
    JUNG, CLEAR, STN, RIVER, MOSS = (62, 112, 64), (116, 156, 88), (150, 160, 150), (80, 140, 170), (40, 90, 60)
    leg = [(JUNG, "jungle floor z 44, canopy groves in groups"), (CLEAR, "spawn clearings (flat, cover ring)"), (STN, "step pyramids: assist, top z 9 / z 8 below lip"),
           (RIVER, "cenote + stream (shallow)"), (MOSS, "Root Cage / dense fig roots (under platform)"), ((220, 190, 90), "glow-lit shrines and braziers"),
           ((200, 255, 255), "broken causeway arm ends 7 short of platform lip")]
    c = Canvas(JUNG, "3  VERDIGRIS STAIR - Babel with assist structures, overgrown step-pyramid jungle, blue-hour rain",
               "assist: two ruined pyramids N/S of platform, gap 8 up + 7 across, equal for both teams", leg)
    c.ell(118, 256, 52, 48, CLEAR, "x")
    c.dots([(160, 214), (168, 300), (186, 206), (190, 308), (150, 252), (176, 252)], 4, MOSS, "x")
    c.rect(222, 150, 290, 218, STN, label="Sun Stair")
    c.rect(222, 294, 290, 362, STN, label="Moon Stair")
    c.rect(250, 218, 262, 233, (200, 255, 255))
    c.rect(250, 278, 262, 294, (200, 255, 255))
    c.ell(256, 256, 24, 22, MOSS)
    c.ell(256, 98, 34, 22, RIVER)
    c.line([(222, 98), (150, 80), (60, 70), (10, 60)], RIVER, 6, "x")
    c.rect(300, 168, 358, 198, (130, 140, 130), "x", label="")
    c.rect(150, 168, 214, 198, (130, 140, 130))
    c.line([(150, 372), (190, 392), (230, 380), (256, 396), (290, 380), (330, 392), (362, 372)], (110, 150, 100), 7)
    c.ell(256, 428, 22, 18, (120, 130, 120))
    # ruins scatter
    c.dots([(170, 330), (196, 340), (330, 330), (316, 340), (176, 190), (336, 190), (200, 120), (312, 120), (200, 400), (312, 400), (240, 230), (272, 230), (240, 284), (272, 284), (180, 280), (332, 232)], 4, STN)
    c.dots([(256, 102), (236, 90), (276, 90), (236, 110), (276, 110)], 2, (220, 190, 90))
    c.line([(60, 256), (150, 256), (206, 256)], (255, 255, 255), 2, "x")
    c.landmark(1, 256, 184, 24, 24, "Sun Stair", (255, 235, 150))
    c.landmark(2, 256, 328, 24, 24, "Moon Stair", (200, 215, 255))
    c.landmark(3, 256, 256, 20, 20, "Root Cage", (200, 255, 200))
    c.landmark(4, 256, 98, 24, 16, "Cenote", (200, 255, 255))
    c.landmark(5, 256, 394, 30, 10, "Coil Wall", (255, 220, 200))
    c.landmark(6, 182, 183, 24, 12, "Ball Courts", (255, 255, 255))
    c.landmark(7, 256, 428, 24, 20, "Mossy Head", (255, 200, 150))
    c.overlay()
    c.text(8, 470, "1 Sun Stair  2 Moon Stair  3 Root Cage  4 Cenote  5 Coil Wall  6 Ball Courts (twin, E and W)  7 Mossy Head")
    c.finish(os.path.join(HERE, "concept_3.png"))


if __name__ == "__main__":
    c1(); c2(); c3()
    for n in (1, 2, 3):
        p = os.path.join(HERE, f"concept_{n}.png")
        print(p, os.path.exists(p), np.asarray(Image.open(p)).shape)
