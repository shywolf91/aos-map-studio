"""aosmap.kit.palette: palette design helpers (2026-11-19) - OKLab/OKLCH, hue-shifted ramps, starter palettes, checks.

Complements kit.color (which bakes light/glow and enforces the owner limits per voxel). Author snow UNDER the cap with
these ramps; kit.color.enforce_brightness then stays a safety net instead of flattening every crest to 212.

Knowledge behind this module: docs/colour_palette_guide.md (sources, evidence tags, rationale).

Conventions
* RGB tuples are 0-255 ints in R, G, B order. The VXL writer (aosmap.vxl.rgb) handles the B,G,R,A byte order.
* ``luma`` is Rec.601 on 0-255 (0.299 R + 0.587 G + 0.114 B): the project's floor rule "luma >= 40" uses it
  (scenes/hollow_crown/hc_color.py).
* Perceptual work (ramps, distances) uses OKLab / OKLCH (Bjorn Ottosson 2020), which keeps hue steady while
  lightness changes far better than HSV.
* Hue angles are degrees in OKLCH. Rough landmarks: red ~29, orange ~55, yellow ~110, green ~142, cyan ~195,
  blue ~264, violet ~300, magenta ~330.

Owner limits encoded here [USER]: snow max channel <= 212, walkable floor luma >= 40, fog channels ~150+,
fog hue absent from the palette and neutral between the team colours.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .color import LUMA_FLOOR_MIN as FLOOR_MIN_LUMA, WHITE_CAP as SNOW_MAX_CHANNEL, hex_rgb  # noqa: E402,F401
# SNOW_MAX_CHANNEL = 212 [USER] "too white" cap; FLOOR_MIN_LUMA = 40 [USER] "too black" floor (shared with kit.color)
FOG_MIN_CHANNEL = 150       # [USER] fog brightness ~150+ per channel (146 has been accepted)
TEAM_BLUE = (0, 0, 255)
TEAM_RED = (255, 0, 0)


# ----------------------------------------------------------------------------------------------- conversions
def rgb_hex(rgb) -> str:
    return '#%02X%02X%02X' % tuple(int(round(c)) for c in rgb[:3])


def luma(rgb) -> np.ndarray | float:
    """Rec.601 luma on 0-255 (project floor convention). Works on tuples or (..., 3) arrays."""
    a = np.asarray(rgb, dtype=np.float64)
    v = a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114
    return float(v) if v.ndim == 0 else v


def _lin(c):
    c = np.asarray(c, dtype=np.float64) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _gam(c):
    c = np.clip(c, 0, 1)
    return 255.0 * np.where(c <= 0.0031308, 12.92 * c, 1.055 * np.power(c, 1 / 2.4) - 0.055)


def rgb_to_oklab(rgb) -> np.ndarray:
    l = _lin(rgb)
    r, g, b = l[..., 0], l[..., 1], l[..., 2]
    L_ = np.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
    M_ = np.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
    S_ = np.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    return np.stack([0.2104542553 * L_ + 0.7936177850 * M_ - 0.0040720468 * S_,
                     1.9779984951 * L_ - 2.4285922050 * M_ + 0.4505937099 * S_,
                     0.0259040371 * L_ + 0.7827717662 * M_ - 0.8086757660 * S_], -1)


def oklab_to_rgb(lab) -> np.ndarray:
    lab = np.asarray(lab, dtype=np.float64)
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    r = 4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_
    g = -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_
    bb = -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_
    return _gam(np.stack([r, g, bb], -1))


def rgb_to_oklch(rgb) -> np.ndarray:
    lab = rgb_to_oklab(rgb)
    C = np.hypot(lab[..., 1], lab[..., 2])
    h = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360
    return np.stack([lab[..., 0], C, h], -1)


def oklch_to_rgb(lch) -> np.ndarray:
    lch = np.asarray(lch, dtype=np.float64)
    h = np.radians(lch[..., 2])
    return oklab_to_rgb(np.stack([lch[..., 0], lch[..., 1] * np.cos(h), lch[..., 1] * np.sin(h)], -1))


def delta_e(a, b) -> np.ndarray | float:
    """OKLab Euclidean distance x100 (~1 = just noticeable, ~10 = clearly different swatches)."""
    d = 100 * np.linalg.norm(rgb_to_oklab(a) - rgb_to_oklab(b), axis=-1)
    return float(d) if np.ndim(d) == 0 else d


def hue_dist(h1, h2) -> float:
    d = abs(h1 - h2) % 360
    return min(d, 360 - d)


# ----------------------------------------------------------------------------------------------- ramps
def shifted_ramp(mid, n: int = 5, light_step: float = 0.075, hue_shift: float = 12.0,
                 light_hue: float | None = None, chroma_ends: float = 0.65, cap: int | None = None,
                 end_tint: float = 0.0, shadow_hue: float | None = None):
    """Hue-shifted material ramp around ``mid`` (the colour that covers most of the object).

    * Lightness moves ``light_step`` OKLab L per step either side of mid.
    * Lighter steps rotate toward ``light_hue`` (the light source: warm sun ~70, moonlight ~250), darker steps
      rotate toward ``shadow_hue`` (default: opposite the light), ``hue_shift`` degrees per step.
      With light_hue None: lights go toward yellow (~95), shadows toward blue (~275) - warm light / cool shadow.
    * Chroma falls to ``chroma_ends`` x mid at the extremes (shadows and highlights are less saturated), which
      avoids the neon highlights a straight brightness ramp produces.
    * ``cap`` (use SNOW_MAX_CHANNEL for snow) shortens the light-side steps until the top fits; only if mid itself
      is over the cap is the whole ramp scaled.
    * ``end_tint`` (OKLCH chroma, ~0.01-0.03) gives near-grey materials (snow, ash, concrete) a visible temperature at
      the ends: the lightest step gets that much chroma at the light hue, the darkest at the opposite hue. Without it
      a grey has no hue to shift. Snow presets: late sun light_hue 70 (shadows -> blue 250);
      moonlight light_hue 220, shadow_hue 290 (cool highlights, violet shadows); overcast end_tint 0.
    Returns a list of n RGB tuples, darkest first.
    """
    L0, C0, h0 = rgb_to_oklch(np.array(mid, float))
    target_light = 95.0 if light_hue is None else light_hue
    dark_hue = (target_light + 180) % 360 if shadow_hue is None else shadow_hue
    half = (n - 1) / 2

    def build(up):
        rows = []
        for i in range(n):
            k = i - half                                   # negative = darker
            L = L0 + k * (up if k > 0 else light_step)
            toward = target_light if k > 0 else dark_hue
            diff = ((toward - h0 + 540) % 360) - 180       # rotate toward the target, never past it
            h = (h0 + math.copysign(min(abs(diff), abs(k) * hue_shift), diff)) % 360
            t = min(1.0, abs(k) / max(half, 1))
            C = C0 * (1 - (1 - chroma_ends) * t)
            if end_tint and k:                             # grey has no hue of its own: add a tint vector
                ab = (C * np.array([math.cos(math.radians(h)), math.sin(math.radians(h))])
                      + end_tint * t * np.array([math.cos(math.radians(toward)), math.sin(math.radians(toward))]))
                C, h = float(np.hypot(*ab)), float(math.degrees(math.atan2(ab[1], ab[0])) % 360)
            rows.append(oklch_to_rgb(np.array([L, C, h])))
        return np.clip(np.array(rows), 0, 255)

    up = light_step
    out = build(up)
    if cap is not None:
        # compress the LIGHT side first (keeps mid = the colour you chose); scale everything only if mid is over cap
        for _ in range(40):
            if out.max() <= cap or up < 0.004:
                break
            up *= 0.85
            out = build(up)
        if out.max() > cap:
            out = out * (cap / out.max())
    return [tuple(int(round(c)) for c in row) for row in out]


def grade(rgb, mult=1.0, toward=None, amount=0.0):
    """Multiply (night DARK grade) and optionally blend toward a tint colour."""
    a = np.asarray(rgb, dtype=np.float64) * mult
    if toward is not None and amount:
        a = a * (1 - amount) + np.asarray(toward, float) * amount
    return np.clip(a, 0, 255)


# ----------------------------------------------------------------------------------------------- starter palettes
# [GUIDE] "Color palettes for VXL maps" field guide (owner-supplied PDF, 2026-11): original starting recipes,
# not client-tested by their author. Order: darkest/structural -> lightest, accent last. Labels say where to paint.
STARTERS: dict[str, list[tuple[str, str]]] = {
    'winter_crossing': [('exposed rock', '#536270'), ('packed route', '#91A6B7'), ('open snow', '#BCCBD3'),
                        ('drift crest', '#DCE3E3'), ('bridge timber', '#AC704A')],
    'snow_bank_4pass': [('rock', '#687580'), ('trough or track', '#91A6B7'), ('broad field', '#BCCBD3'),
                        ('short crest', '#DCE3E3')],
    'overcast_pass': [('exposed slate', '#647381'), ('packed track', '#90A3AD'), ('snowfield', '#B9C6CA'),
                      ('drift lip', '#D2DADA'), ('trail posts', '#A47C58')],
    'late_sun_ridge': [('stone shade', '#5B596C'), ('snow in shade', '#959BAF'), ('snowfield', '#C8C4BE'),
                       ('sunlit lip', '#E6D8BF'), ('cabin', '#945C46')],
    'blue_hour_outpost': [('dark structure', '#444D60'), ('packed snow', '#738398'), ('open snow', '#9EAFBF'),
                          ('crest', '#C3CFD5'), ('door marker', '#C28F56')],
    'stone_ramp': [('shaded stone', '#4C514C'), ('stone body', '#77796B'), ('weathered edge', '#A6A38E')],
    'timber_ramp': [('timber joint', '#55463E'), ('timber body', '#856B50'), ('worn end grain', '#B7976A')],
    'woodland_valley': [('tree shade', '#465146'), ('meadow', '#778568'), ('trail', '#A59C7D'),
                        ('riverbank', '#706052'), ('bridge post', '#B78954')],
    'desert_canyon': [('cliff recess', '#75594D'), ('sandstone', '#BE946D'), ('open sand', '#D9B991'),
                      ('gravel path', '#948673'), ('pump house', '#517A7A')],
    'industrial_rail_yard': [('door recess', '#414B50'), ('concrete', '#727E80'), ('platform lip', '#A3A5A0'),
                             ('rust cladding', '#86604F'), ('route stripe', '#CD994A')],
    'volcanic_highlands': [('basalt recess', '#3F4247'), ('ash field', '#65636A'), ('worn ledge', '#969295'),
                           ('cinder path', '#78665B'), ('kiln marker', '#C58459')],
}

# [GUIDE] trial fog pairings (fog values from our own archive, pairings new and untested).
FOG_PAIRINGS = {
    'overcast_pass': (168, 164, 178),       # moonlit lilac-grey
    'late_sun_ridge': (152, 174, 168),      # slate-green
    'blue_hour_outpost': (190, 168, 176),   # bright mauve-amber / dusty mauve
    'woodland_valley': (178, 172, 192),     # pale lilac-grey
    'desert_canyon': (152, 174, 168),       # slate-green (alt pale lilac-grey (178,172,192))
    'industrial_rail_yard': (200, 188, 206),  # lilac dusk
    'volcanic_highlands': (152, 168, 154),  # gray-green mist
}


def starter(name: str) -> dict[str, tuple[int, int, int]]:
    return {label: hex_rgb(h) for label, h in STARTERS[name]}


# ----------------------------------------------------------------------------------------------- checks
@dataclass
class PaletteReport:
    ok: bool = True
    warnings: list[str] = field(default_factory=list)
    info: dict = field(default_factory=dict)

    def warn(self, msg):
        self.ok = False
        self.warnings.append(msg)


def is_snowlike(rgb) -> np.ndarray | bool:
    """Light, low-chroma colours (snow, frost, pale plaster): OKLab L > 0.72 and chroma < 0.06."""
    lch = rgb_to_oklch(rgb)
    v = (lch[..., 0] > 0.72) & (lch[..., 1] < 0.06)
    return bool(v) if np.ndim(v) == 0 else v


def check_palette(colours: dict[str, tuple], fog=None, floors: list[str] | None = None,
                  teams=(TEAM_BLUE, TEAM_RED), snow_cap: int = SNOW_MAX_CHANNEL) -> PaletteReport:
    """Check a named authoring palette against the owner's rules and the guide's fog advice.

    colours: {label: (r,g,b)}. floors: labels that are walkable floors (luma >= 40 check).
    """
    rep = PaletteReport()
    for name, c in colours.items():
        if is_snowlike(c) and max(c) > snow_cap:
            rep.warn(f'{name} {rgb_hex(c)}: snow-like colour above the {snow_cap} max-channel cap')
    for name in floors or []:
        if luma(colours[name]) < FLOOR_MIN_LUMA:
            rep.warn(f'{name} {rgb_hex(colours[name])}: floor luma {luma(colours[name]):.0f} < {FLOOR_MIN_LUMA}')
    # value structure: a dark, a mid and a light band should all exist (three-value block-in)
    ls = sorted(float(luma(c)) for c in colours.values())
    if ls and ls[-1] - ls[0] < 70:
        rep.warn(f'value range {ls[0]:.0f}-{ls[-1]:.0f} luma is narrow (<70): shapes will not read in greyscale')
    if fog is not None:
        fog = tuple(fog)
        if min(fog) < FOG_MIN_CHANNEL - 6:
            rep.warn(f'fog {fog}: a channel below ~{FOG_MIN_CHANNEL} (owner prefers bright tints)')
        if max(fog) > 215 and rgb_to_oklch(np.array(fog, float))[1] < 0.03:
            rep.warn(f'fog {fog}: near-white fog (glare)')
        fl = rgb_to_oklch(np.array(fog, float))
        near = []
        for name, c in colours.items():
            lch = rgb_to_oklch(np.array(c, float))
            if lch[1] > 0.02 and fl[1] > 0.02 and hue_dist(lch[2], fl[2]) < 25:
                near.append(name)
            if delta_e(fog, c) < 8:
                rep.warn(f'fog {fog} nearly equals {name} {rgb_hex(c)} (dE {delta_e(fog, c):.1f}): it merges with the '
                         f'fog at distance - fine for ground, not for a skyline, landmark or objective')
        if near:
            rep.warn(f'fog hue {fl[2]:.0f} deg shares a hue family with: {", ".join(near)}')
        if teams:
            lean = fog_team_lean(fog, teams)
            rep.info['fog_team_lean'] = lean
            if lean['warn']:
                rep.warn(f"fog leans toward the {lean['side']} team hue (chroma {lean['chroma']:.3f}, "
                         f"hue {lean['hue']:.0f} deg): it will hide that team first")
    return rep


def fog_team_lean(fog, teams=(TEAM_BLUE, TEAM_RED)) -> dict:
    """Is the fog tint biased toward one team's hue? Low-chroma fog counts as neutral."""
    f = rgb_to_oklch(np.array(fog, float))
    hb = rgb_to_oklch(np.array(teams[0], float))[2]
    hr = rgb_to_oklch(np.array(teams[1], float))[2]
    db, dr = hue_dist(f[2], hb), hue_dist(f[2], hr)
    side = 'blue' if db < dr else 'red'
    warn = bool(f[1] > 0.035 and min(db, dr) < 30)   # lilac ~300 deg (36 from blue) is accepted
    return {'hue': float(f[2]), 'chroma': float(f[1]), 'deg_to_blue': round(db), 'deg_to_red': round(dr),
            'side': side, 'warn': warn}


def cap_snow(colours: dict[str, tuple], cap: int = SNOW_MAX_CHANNEL) -> dict[str, tuple]:
    """Fit a palette's snow under the owner cap by scaling ALL snow-like members by one factor.

    Scaling only the brightest swatch would erase the crest/field step the guide relies on; scaling the whole
    snow family keeps its internal value steps (the guide's own advice: "darken the field one step"). Rock, timber
    and accents are left alone, so the snow keeps its contrast against them.
    """
    snow = {k: v for k, v in colours.items() if is_snowlike(np.array(v, float))}
    mx = max((max(v) for v in snow.values()), default=0)
    f = min(1.0, cap / mx) if mx else 1.0
    return {k: (tuple(int(round(c * f)) for c in v) if k in snow else tuple(v)) for k, v in colours.items()}


# The guide's snow recipes fitted under the 212 cap (see cap_snow). Use these on owner maps.
STARTERS_CAPPED = {name: [(lab, rgb_hex(c)) for lab, c in cap_snow(starter(name)).items()]
                   for name in ('winter_crossing', 'snow_bank_4pass', 'overcast_pass', 'late_sun_ridge',
                                'blue_hour_outpost')}
