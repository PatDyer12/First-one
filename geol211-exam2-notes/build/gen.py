#!/usr/bin/env python3
"""Builds notebook-style GEOL 211 Exam 2 notes as HTML (one div per notebook page).

Page model = college-ruled 8.5x11: 96 CSS px/in, rules 9/32" (27px) apart,
first rule 1" from top, 33 rules per page, red margin at 1.25".
Line 1 of every page = header (section name + "Page X"). Content = lines 2-33.
"""
import html, json, math, re, sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent
PAGE_W, PAGE_H = 816, 1056
RULE0, GAP, NLINES = 96, 27, 33
MARGIN_X = 120
TEXT_X = 130
TEXT_R = 780
FONT_PX = 18
# baseline offset inside a 27px line box for Liberation Sans 18px
# (asc .905, desc .212) -> half-leading 3.44 + ascent 16.30 = 19.74
BASE_IN_BOX = 18.99
SIT = 1.5   # baseline sits this many px above the rule

INK, RED = "#161616", "#d0021b"

def rule_y(n):          # n = 1..33
    return RULE0 + GAP * (n - 1)

# ---------------------------------------------------------------- markup
def fmt(s):
    """{r:red} {u:underline} {k:boxed} {ru:red underline}; ★ is always red."""
    out, pos = [], 0
    for m in re.finditer(r"\{(r|u|k|ru|rk):(.*?)\}", s):
        out.append(html.escape(s[pos:m.start()]))
        kind, body = m.group(1), html.escape(m.group(2))
        cls = {"r": "r", "u": "u", "k": "k", "ru": "r u", "rk": "r k"}[kind]
        out.append(f'<span class="{cls}">{body}</span>')
        pos = m.end()
    out.append(html.escape(s[pos:]))
    txt = "".join(out)
    txt = txt.replace("★", '<span class="r">★</span>')
    # keep leading spaces as indentation
    lead = len(txt) - len(txt.lstrip(" "))
    return "&nbsp;" * lead + txt.lstrip(" ")

# ---------------------------------------------------------------- blocks
class L:            # one text line
    def __init__(s, text="", tag=None, cls=""): s.text, s.tag, s.cls = text, tag, cls
    n = 1
class H(L):         # topic heading (underlined) ; key -> index entry
    def __init__(s, text, key=None, tag=None):
        super().__init__(text, tag, "h"); s.key = key or text
class BOX:          # lines with a hand-drawn box around them
    def __init__(s, lines, red=False): s.lines, s.red = lines, red; s.n = len(lines)
class TBL:          # simple line-only table; first row = header
    def __init__(s, cols, rows, tag=None):
        s.cols, s.rows, s.tag = cols, rows, tag; s.n = len(rows)
class DIA:          # diagram occupying n ruled lines
    def __init__(s, n, svg, x=TEXT_X - 4, w=TEXT_R - TEXT_X + 8):
        s.n, s.svg, s.x, s.w = n, svg, x, w
class SIDE:         # text lines on the left, diagram on the right
    def __init__(s, lines, svg, dia_w, n=None):
        s.lines, s.svg, s.dia_w = lines, svg, dia_w; s.n = n or len(lines)
class SKIP:         # blank ruled lines
    def __init__(s, n=1): s.n = n
class NEWPAGE: n = 0
class SECTION:      # sets running header for following pages
    def __init__(s, name): s.name = name; s.n = 0

# ---------------------------------------------------------------- svg helpers
def _ah(x2, y2, ang, col, size=9):
    a1, a2 = ang + math.radians(152), ang - math.radians(152)
    p = [(x2, y2), (x2 + size * math.cos(a1), y2 + size * math.sin(a1)),
         (x2 + size * math.cos(a2), y2 + size * math.sin(a2))]
    return f'<polygon points="{" ".join(f"{a:.1f},{b:.1f}" for a, b in p)}" fill="{col}"/>'

def arrow(x1, y1, x2, y2, col=INK, w=2, dash=False, head=9):
    ang = math.atan2(y2 - y1, x2 - x1)
    xe, ye = x2 - head * 0.6 * math.cos(ang), y2 - head * 0.6 * math.sin(ang)
    d = ' stroke-dasharray="6 5"' if dash else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{xe:.1f}" y2="{ye:.1f}" stroke="{col}" '
            f'stroke-width="{w}" stroke-linecap="round"{d}/>' + _ah(x2, y2, ang, col, head))

def qarrow(x1, y1, cx, cy, x2, y2, col=INK, w=2, dash=False, head=9):
    ang = math.atan2(y2 - cy, x2 - cx)
    d = ' stroke-dasharray="6 5"' if dash else ""
    return (f'<path d="M{x1},{y1} Q{cx},{cy} {x2},{y2}" fill="none" stroke="{col}" '
            f'stroke-width="{w}" stroke-linecap="round"{d}/>' + _ah(x2, y2, ang, col, head))

def path(d, col=INK, w=2, dash=False, fill="none"):
    ds = ' stroke-dasharray="6 5"' if dash else ""
    return f'<path d="{d}" fill="{fill}" stroke="{col}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"{ds}/>'

def line(x1, y1, x2, y2, col=INK, w=2, dash=False):
    ds = ' stroke-dasharray="6 5"' if dash else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="{w}" stroke-linecap="round"{ds}/>'

def text(x, y, s, size=15, anchor="start", col=INK, weight="normal", deco=""):
    dd = f' text-decoration="{deco}"' if deco else ""
    return (f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" fill="{col}" '
            f'font-weight="{weight}"{dd}>{html.escape(s)}</text>')

def waves(x1, x2, y, amp=3, step=16, col=INK, w=1.6):
    d = f"M{x1},{y}"
    x = x1
    while x + step <= x2:
        d += f" q{step/4},{-amp} {step/2},0 t{step/2},0"
        x += step
    return path(d, col, w)

def loop(cx, cy, rx, ry, clockwise, col=INK):
    s = f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx}" ry="{ry}" fill="none" stroke="{col}" stroke-width="1.8"/>'
    top_dir = 0 if clockwise else math.pi          # top arrow points right if CW
    bot_dir = math.pi if clockwise else 0
    s += _ah(cx + (4 if clockwise else -4), cy - ry, top_dir, col, 9)
    s += _ah(cx + (-4 if clockwise else 4), cy + ry, bot_dir, col, 9)
    return s

def svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'class="dia">{body}</svg>')

# ---------------------------------------------------------------- diagrams
DW = TEXT_R - TEXT_X + 8   # 658

def d_global():
    h = 16 * GAP
    R, cx, cy = 172, 292, h / 2
    b = []
    b.append(f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="{INK}" stroke-width="2.2"/>')
    lat = {90: cy - R, 60: cy - 2 * R / 3, 30: cy - R / 3, 0: cy,
           -30: cy + R / 3, -60: cy + 2 * R / 3, -90: cy + R}
    hw = lambda y: math.sqrt(max(R * R - (y - cy) ** 2, 0))
    for k in (60, 30, 0, -30, -60):
        y = lat[k]
        b.append(line(cx - hw(y), y, cx + hw(y), y, INK, 2.4 if k == 0 else 1.4, dash=(k != 0)))
    # pressure / wet-dry labels on the right
    labels = {90: ("90°N", "H", "cold + DRY"), 60: ("60°N", "L", "WET (storms)"),
              30: ("30°N", "H", "DRY → deserts"), 0: ("0°", "L", "ITCZ → WET"),
              -30: ("30°S", "H", "DRY → deserts"), -60: ("60°S", "L", "WET"),
              -90: ("90°S", "H", "cold + DRY")}
    for k, (latname, hl, wx) in labels.items():
        y = lat[k] + 5
        b.append(text(478, y, latname, 15))
        b.append(text(526, y + 1, hl, 19, col=RED, weight="bold"))
        b.append(text(546, y, wx, 15))
    # cells (loops) hugging the left limb; outward = left on page
    # NH: Hadley CW, Ferrel CCW, Polar CW ; SH: Hadley CCW, Ferrel CW, Polar CCW
    cells = [(0, 30, "Hadley", True), (30, 60, "Ferrel", False), (60, 90, "Polar", True),
             (-30, 0, "Hadley", False), (-60, -30, "Ferrel", True), (-90, -60, "Polar", False)]
    for lo, hi, name, cw in cells:
        ymid = (lat[lo] + lat[hi]) / 2
        lx = cx - hw(ymid) - 27
        b.append(loop(lx, ymid, 21, 23, cw))
        b.append(text(lx - 26, ymid + 5, name, 14, anchor="end"))
    # surface winds (direction checked: NH right, SH left of travel; H -> L)
    def band_winds(ytop, dx, dy, label, n=2, lab_at_top=True):
        out = []
        ly = ytop + 19 if lab_at_top else ytop + 52
        ay1, ay2 = (ytop + 27, ytop + 49) if lab_at_top else (ytop + 9, ytop + 31)
        out.append(text(cx + 25, ly, label, 14, anchor="middle"))
        starts = [cx - 60, cx + 70] if n == 2 else [cx + 25]
        for sx in starts:
            y1 = ay1 if dy > 0 else ay2
            y2 = ay2 if dy > 0 else ay1
            x1 = sx - 30 * dx
            x2 = sx + 30 * dx
            out.append(arrow(x1, y1, x2, y2, INK, 2, head=9))
        return out
    t = R / 3
    b += band_winds(lat[30], -1, +1, "NE trades")              # NH 0-30: toward SW
    b += band_winds(lat[60], +1, -1, "westerlies")             # NH 30-60: toward NE
    b += band_winds(lat[0], -1, -1, "SE trades")               # SH 0-30: toward NW
    b += band_winds(lat[-30], +1, +1, "westerlies")            # SH 30-60: toward SE
    # polar bands (narrow): one arrow each
    b.append(text(cx, lat[90] + 30, "polar easterlies", 13, anchor="middle"))
    b.append(arrow(cx + 55, lat[60] - 20, cx - 5, lat[60] - 6))      # NH polar: toward SW
    b.append(arrow(cx + 55, lat[-60] + 20, cx - 5, lat[-60] + 6))    # SH polar: toward NW
    b.append(text(cx, lat[-90] - 20, "polar easterlies", 13, anchor="middle"))
    return svg(DW, h, "".join(b))

def d_coriolis(w=300, n=7):
    h = n * GAP
    cx, cy, R = 88, h / 2, 80
    b = [f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="{INK}" stroke-width="2"/>',
         line(cx - R, cy, cx + R, cy, INK, 1.6)]
    # rotation arrow along equator (front side moves east = right)
    b.append(arrow(cx - 30, cy + 12, cx + 30, cy + 12, INK, 1.6, head=7))
    b.append(text(cx, cy + 30, "spins W→E", 12, anchor="middle"))
    # NH: object heading north bends RIGHT (east)
    b.append(line(cx - 20, cy - 8, cx - 20, cy - 62, INK, 1.3, dash=True))
    b.append(qarrow(cx - 20, cy - 8, cx - 20, cy - 52, cx + 18, cy - 62, RED, 2.2))
    # SH: object heading north bends LEFT (west)
    b.append(line(cx + 22, cy + 70, cx + 22, cy + 38, INK, 1.3, dash=True))
    b.append(qarrow(cx + 22, cy + 70, cx + 22, cy + 42, cx - 14, cy + 36, RED, 2.2))
    b.append(text(cx + R + 12, cy - 48, "NH → bends", 14))
    b.append(text(cx + R + 12, cy - 30, "RIGHT", 15, col=RED, weight="bold"))
    b.append(text(cx + R + 12, cy + 5, "0 at equator", 14))
    b.append(text(cx + R + 12, cy + 42, "SH → bends", 14))
    b.append(text(cx + R + 12, cy + 60, "LEFT", 15, col=RED, weight="bold"))
    b.append(text(cx - R + 2, 14, "-- = path w/o spin", 11))
    return svg(w, h, "".join(b))

def _cell_panel(ox, w, h, hot_land, title, sub, air_lab, land_lab="LAND", sea_lab="OCEAN",
                sun=None):
    """Side-view thermal circulation. hot_land=True -> rising over land."""
    b = []
    g = h - 32                  # ground level
    mid = ox + w * 0.48
    b.append(line(ox + 4, g, mid, g, INK, 2.2))                      # land surface
    for k in range(6):                                              # land hatching
        x = ox + 14 + k * (mid - ox - 20) / 6
        b.append(line(x, g + 4, x - 8, g + 14, INK, 1))
    b.append(waves(mid, ox + w - 6, g, 3, 14))
    b.append(text(ox + (mid - ox) / 2, g + 27, land_lab, 13, anchor="middle"))
    b.append(text(mid + (ox + w - mid) / 2, g + 27, sea_lab, 13, anchor="middle"))
    xl, xs = ox + (mid - ox) * 0.5, mid + (ox + w - mid) * 0.5
    top, bot = 56, g - 8
    if hot_land:   # rise over land, sink over sea, surface flow sea -> land
        b.append(arrow(xl, bot, xl, top))
        b.append(arrow(xl + 12, top - 8, xs - 12, top - 8))
        b.append(arrow(xs, top, xs, bot))
        b.append(arrow(xs - 12, bot + 2, xl + 12, bot + 2, RED, 2.6))
        b.append(text(xl - 14, (top + bot) / 2 + 6, "L", 19, anchor="end", col=RED, weight="bold"))
        b.append(text(xs + 14, (top + bot) / 2 + 6, "H", 19, col=RED, weight="bold"))
    else:          # sink over land, rise over sea, surface flow land -> sea
        b.append(arrow(xl, top, xl, bot))
        b.append(arrow(xs - 12, top - 8, xl + 12, top - 8))
        b.append(arrow(xs, bot, xs, top))
        b.append(arrow(xl + 12, bot + 2, xs - 12, bot + 2, RED, 2.6))
        b.append(text(xl - 14, (top + bot) / 2 + 6, "H", 19, anchor="end", col=RED, weight="bold"))
        b.append(text(xs + 14, (top + bot) / 2 + 6, "L", 19, col=RED, weight="bold"))
    b.append(text((xl + xs) / 2, bot - 8, air_lab, 13, anchor="middle", col=RED))
    b.append(text(ox + 6, 21, title, 15, weight="bold"))
    b.append(text(ox + 6, 39, sub, 13))
    if sun == "sun":
        sx, sy = ox + w - 26, 26
        b.append(f'<circle cx="{sx}" cy="{sy}" r="9" fill="none" stroke="{INK}" stroke-width="1.8"/>')
        for k in range(8):
            a = k * math.pi / 4
            b.append(line(sx + 13 * math.cos(a), sy + 13 * math.sin(a),
                          sx + 18 * math.cos(a), sy + 18 * math.sin(a), INK, 1.5))
    elif sun == "moon":
        sx, sy = ox + w - 26, 26
        b.append(path(f"M{sx+4},{sy-12} A12,12 0 1,0 {sx+4},{sy+12} A9,9 0 1,1 {sx+4},{sy-12}Z", INK, 1.6))
    elif sun == "rain":
        cx0, cy0 = xl - 2, 30
        b.append(path(f"M{cx0-26},{cy0+6} q-2,-12 12,-11 q6,-12 20,-4 q14,-4 16,9 q2,8 -8,8 h-34 q-8,0 -6,-2z", INK, 1.5))
        for k in range(4):
            b.append(line(cx0 - 20 + k * 11, cy0 + 12, cx0 - 24 + k * 11, cy0 + 19, INK, 1.3))
    return b

def d_monsoon():
    n = 6; h = n * GAP; pw = 318
    b = _cell_panel(0, pw, h, True, "SUMMER → WET season", "land HOTTER than ocean", "moist air → land")
    b += _cell_panel(pw + 22, pw, h, False, "WINTER → DRY season", "land COLDER than ocean", "dry air → sea")
    b.append(line(pw + 11, 6, pw + 11, h - 6, INK, 1.2, dash=True))
    return svg(DW, h, "".join(b))

def d_breeze():
    n = 6; h = n * GAP; pw = 318
    b = _cell_panel(0, pw, h, True, "DAY → SEA BREEZE", "land heats faster", "onshore flow",
                    sea_lab="SEA", sun="sun")
    b += _cell_panel(pw + 22, pw, h, False, "NIGHT → LAND BREEZE", "land cools faster", "offshore flow",
                     sea_lab="SEA", sun="moon")
    b.append(line(pw + 11, 6, pw + 11, h - 6, INK, 1.2, dash=True))
    return svg(DW, h, "".join(b))

def d_track():
    n = 9; h = n * GAP
    b = []
    # US coast
    b.append(path("M40,4 q14,30 4,60 q-10,30 10,58 q16,24 2,46 q-8,14 6,30", INK, 2))
    b.append(text(8, 40, "US", 15, weight="bold"))
    b.append(text(652, 196, "Africa", 13, anchor="end"))
    # Bermuda High with clockwise flow
    hx, hy, r = 450, 100, 52
    b.append(text(hx, hy + 12, "H", 34, anchor="middle", col=RED, weight="bold"))
    b.append(text(hx, hy + 30, "Bermuda High", 12, anchor="middle"))
    b.append(f'<circle cx="{hx}" cy="{hy}" r="{r}" fill="none" stroke="{INK}" stroke-width="1.4" stroke-dasharray="5 4"/>')
    b.append(_ah(hx + 3, hy - r, 0, INK, 9))           # top -> east
    b.append(_ah(hx + r, hy + 3, math.pi / 2, INK, 9))  # right side -> south
    b.append(_ah(hx - 3, hy + r, math.pi, INK, 9))      # bottom -> west
    b.append(_ah(hx - r, hy - 3, -math.pi / 2, INK, 9)) # left side -> north
    b.append(text(hx + r + 8, hy - 40, "clockwise", 12))
    # main track (red): west on trades, north around W edge, NE on westerlies
    b.append(path("M596,196 L330,196 Q282,196 280,150 L280,120 Q282,48 350,26 L560,12", RED, 3))
    b.append(_ah(560, 12, math.atan2(-14, 210), RED, 11))
    b.append(_ah(470, 196, math.pi, RED, 11))
    b.append(_ah(280, 125, -math.pi / 2, RED, 11))
    # storm symbol at start
    b.append(f'<circle cx="596" cy="196" r="7" fill="none" stroke="{RED}" stroke-width="2.2"/>')
    b.append(path("M596,189 q8,-8 16,-3 M596,203 q-8,8 -16,3", RED, 2))
    b.append(text(520, 184, "① trades push it W", 13, anchor="middle"))
    b.append(text(272, 105, "② turns N around", 13, anchor="end"))
    b.append(text(272, 122, "W edge of the H", 13, anchor="end"))
    b.append(text(430, 40, "③ westerlies → NE", 13, anchor="middle"))
    # alternate track (dashed): strong high reaching far west
    b.append(arrow(330, 196, 90, 196, INK, 1.8, dash=True, head=9))
    b.append(text(92, 219, "if H is strong/far W → keeps going W → FL / Gulf", 12))
    return svg(DW, h, "".join(b))

def d_ekman(w=230, n=6):
    h = n * GAP
    ox, oy = 50, h - 26
    b = [arrow(ox, oy, ox, 22, INK, 2.4)]
    b.append(text(ox - 6, 18, "wind", 13, anchor="end"))
    b.append(arrow(ox, oy, ox + 70, oy - 70, INK, 2))
    b.append(text(ox + 74, oy - 72, "surface 45°", 13))
    b.append(arrow(ox, oy, ox + 140, oy, RED, 2.8))
    b.append(text(ox + 20, oy + 20, "net Ekman transport 90° R", 12, col=RED))
    b.append(path(f"M{ox},{oy-26} A26,26 0 0,1 {ox+26},{oy}", INK, 1))
    b.append(text(w - 6, 16, "(NH)", 12, anchor="end"))
    return svg(w, h, "".join(b))

def d_gyre():
    n = 11; h = n * GAP
    b = []
    # coasts
    b.append(path("M38,6 q-10,40 6,80 q12,34 -2,70 q-12,40 6,80 q8,30 -2,54", INK, 2))
    b.append(path("M620,6 q12,40 -4,80 q-14,40 2,76 q14,40 -2,74 q-10,30 2,54", INK, 2))
    b.append(text(8, 150, "N.", 13)); b.append(text(4, 166, "Amer.", 12))
    b.append(text(628, 150, "Eur./", 12)); b.append(text(628, 166, "Afr.", 12))
    # winds
    b.append(arrow(200, 14, 300, 14, INK, 1.6, head=7)); b.append(arrow(360, 14, 460, 14, INK, 1.6, head=7))
    b.append(text(330, 18, "westerlies", 12, anchor="middle"))
    b.append(arrow(460, h - 12, 360, h - 12, INK, 1.6, head=7)); b.append(arrow(300, h - 12, 200, h - 12, INK, 1.6, head=7))
    b.append(text(330, h - 8, "trades", 12, anchor="middle"))
    # gyre: clockwise. West side = narrow, fast (red, thick); east side = wide, slow
    b.append(path("M112,262 Q72,262 70,220 L70,80 Q72,44 112,40", RED, 5))
    b.append(_ah(112, 40, 0, RED, 13))
    b.append(_ah(70, 150, -math.pi / 2, RED, 13))
    b.append(arrow(130, 40, 420, 40, INK, 2.2))                     # N Atlantic Current -> E
    for k, x in enumerate((398, 436, 474)):                         # wide slow EBC -> S
        b.append(arrow(x, 56 + k * 6, x - 10, 236 - k * 6, INK, 1.4, head=8))
    b.append(arrow(490, 262, 130, 262, INK, 2.2))                   # N Equatorial Current -> W
    b.append(text(280, 34, "N. Atlantic Current → E", 13, anchor="middle"))
    b.append(text(300, 254, "N. Equatorial Current → W", 13, anchor="middle"))
    b.append(text(84, 96, "GULF STREAM", 13, col=RED, weight="bold"))
    b.append(text(84, 113, "FAST, NARROW,", 13, col=RED))
    b.append(text(84, 130, "DEEP, WARM", 13, col=RED))
    b.append(text(592, 150, "CANARY", 13, anchor="end", weight="bold"))
    b.append(text(592, 167, "slow, WIDE,", 13, anchor="end"))
    b.append(text(592, 184, "shallow, cold", 13, anchor="end"))
    # hill of water pushed west
    b.append(f'<ellipse cx="230" cy="160" rx="62" ry="36" fill="none" stroke="{INK}" stroke-width="1.4" stroke-dasharray="5 4"/>')
    b.append(text(230, 157, "\"hill\" of water", 12, anchor="middle"))
    b.append(text(230, 173, "shoved WEST", 12, anchor="middle"))
    b.append(text(250, 222, "CLOCKWISE (NH)", 13, anchor="middle"))
    b.append(arrow(606, 234, 606, 204, INK, 1.4, head=7)); b.append(text(606, 248, "N", 12, anchor="middle"))
    return svg(DW, h, "".join(b))

def d_upwelling():
    n = 9; h = n * GAP
    b = []
    # --- map view (left) ---
    b.append(text(6, 15, "MAP VIEW (NH west coast)", 13, weight="bold"))
    b.append(path("M190,28 q-10,30 4,60 q12,34 -4,66 q-12,36 6,80", INK, 2.2))
    for k in range(7):
        y = 40 + k * 26
        b.append(line(202, y, 214, y + 10, INK, 1))
    b.append(text(212, 150, "LAND", 12))
    b.append(arrow(160, 40, 160, 160, INK, 2.6))
    b.append(text(150, 58, "wind", 13, anchor="end"))
    b.append(text(150, 74, "from N", 13, anchor="end"))
    b.append(arrow(150, 190, 40, 190, RED, 2.8))
    b.append(text(8, 212, "Ekman 90° right → OFFSHORE", 12, col=RED))
    b.append(text(6, 140, "OCEAN", 12))
    b.append(arrow(30, 100, 30, 76, INK, 1.4, head=7)); b.append(text(30, 116, "N", 12, anchor="middle"))
    # --- cross-section (right) ---
    ox = 262
    b.append(text(ox + 4, 15, "SIDE VIEW", 13, weight="bold"))
    sea = 64
    b.append(waves(ox, ox + 290, sea, 3, 14))
    b.append(path(f"M{ox+290},{sea} L{ox+394},{sea-14} L{ox+394},{h-6} L{ox+160},{h-6} Z", INK, 2))
    for k in range(5):
        x = ox + 300 + k * 18
        b.append(line(x, sea + 30 + k * 10, x + 10, sea + 42 + k * 10, INK, 1))
    b.append(text(ox + 360, sea + 20, "LAND", 12, anchor="middle"))
    b.append(text(ox + 290, sea - 30, "⊙ wind from N", 12, anchor="end"))
    b.append(text(ox + 290, sea - 16, "(coming at you)", 11, anchor="end"))
    b.append(arrow(ox + 270, sea + 16, ox + 60, sea + 16, RED, 2.8))
    b.append(text(ox + 60, sea + 36, "surface water pushed offshore", 12, col=RED))
    b.append(qarrow(ox + 60, h - 20, ox + 150, h - 40, ox + 255, sea + 30, INK, 2.6))
    b.append(qarrow(ox + 20, h - 40, ox + 140, h - 70, ox + 228, sea + 46, INK, 2))
    b.append(text(ox + 6, sea + 62, "cold, NUTRIENT-RICH", 13, weight="bold"))
    b.append(text(ox + 6, sea + 79, "deep water RISES", 13, weight="bold"))
    b.append(text(ox + 6, sea - 30, "→ plankton → fish!", 12))
    return svg(DW, h, "".join(b))

def _enso_panel(oy, ph, title, therm, trades, air_w, air_e, up, warm_x, notes):
    b = []
    sea, bot = oy + 58, oy + ph - 8
    L0, R0 = 64, DW - 64
    b.append(path(f"M4,{sea-8} L{L0},{sea-8} L{L0},{bot} L4,{bot}", INK, 2))
    b.append(path(f"M{DW-4},{sea-8} L{R0},{sea-8} L{R0},{bot} L{DW-4},{bot}", INK, 2))
    b.append(text(34, bot - 30, "Indo./", 11, anchor="middle")); b.append(text(34, bot - 16, "Austr.", 11, anchor="middle"))
    b.append(text(DW - 34, bot - 30, "Peru/", 11, anchor="middle")); b.append(text(DW - 34, bot - 16, "S.Am.", 11, anchor="middle"))
    b.append(line(L0, sea, R0, sea, INK, 1.8))
    b.append(line(L0, bot, R0, bot, INK, 1.2))
    yW, yE = therm
    b.append(line(L0, sea + yW, R0, sea + yE, INK, 2.4, dash=True))
    b.append(text(DW / 2 - 60, bot - 6, "cold (deep)", 12))
    b.append(text(R0 - 70, bot - 6, "thermocline - -", 11))
    b.append(text(warm_x, sea + 22, "WARM", 14, anchor="middle", col=RED, weight="bold"))
    b.append(text(8, oy + 16, title, 15, weight="bold"))
    # trade winds above the sea
    n, strength = trades
    ya = sea - 18
    if strength == "weak":
        b.append(arrow(330, ya, 290, ya, INK, 1.4, head=7))
        b.append(text(345, ya + 4, "trades WEAK (or reverse)", 12))
    else:
        xs = [440, 310, 180][:n]
        for x in xs:
            b.append(arrow(x + 90, ya, x, ya, INK, 3.2 if strength == "strong" else 2, head=10))
        lab = "trades STRONG" if strength == "strong" else "trade winds"
        b.append(text(DW / 2 + 60 if n == 2 else DW / 2, ya - 10, lab, 12, anchor="middle"))
    # air: (letter, words, x)
    for (letter, words, x) in (air_w, air_e):
        b.append(text(x, oy + 26, letter, 19, anchor="middle", col=RED, weight="bold"))
        b.append(text(x + 14, oy + 25, words, 12))
    # upwelling at Peru
    if up == "yes":
        b.append(arrow(R0 - 20, sea + 40, R0 - 20, sea + 6, INK, 2.2))
        b.append(text(R0 - 28, sea + 36, "upwelling", 11, anchor="end"))
    elif up == "strong":
        b.append(arrow(R0 - 20, sea + 46, R0 - 20, sea + 6, INK, 3.4, head=11))
        b.append(text(R0 - 30, sea + 42, "STRONG upwelling", 11, anchor="end"))
    else:
        b.append(text(R0 - 12, sea + 20, "✗ no upwelling", 12, anchor="end", col=RED))
    for (x, y, s) in notes:
        b.append(text(x, oy + y, s, 11))
    return b

def d_enso():
    ph = 5 * GAP
    n = 15; h = n * GAP
    b = []
    b += _enso_panel(0, ph, "NORMAL", (46, 10), (2, "normal"),
                     ("L", "rain", 150), ("H", "dry", DW - 150), "yes", 200, [])
    b.append(line(0, ph, DW, ph, INK, 1.2, dash=True))
    b += _enso_panel(ph, ph, "EL NIÑO", (36, 33), (1, "weak"),
                     ("H", "DROUGHT", 150), ("L", "rain, FLOODS", DW - 190), "no", 420, [])
    b.append(line(0, 2 * ph, DW, 2 * ph, INK, 1.2, dash=True))
    b += _enso_panel(2 * ph, ph, "LA NIÑA", (56, 4), (3, "strong"),
                     ("L", "heavy rain/floods", 150), ("H", "very dry", DW - 150), "strong", 150, [])
    return svg(DW, h, "".join(b))

def d_conveyor():
    n = 10; h = n * GAP
    b = []
    # continents (simple blocks)
    b.append(path("M24,20 L84,20 L90,110 L70,150 L66,210 L44,210 L30,120 Z", INK, 1.8))
    b.append(text(56, 90, "AMER.", 11, anchor="middle"))
    b.append(path("M250,16 L300,16 L304,120 L286,196 L262,196 L246,110 Z", INK, 1.8))
    b.append(text(275, 90, "EUR./", 11, anchor="middle")); b.append(text(275, 104, "AFRICA", 11, anchor="middle"))
    b.append(path("M430,16 L500,16 L500,104 L440,104 Z", INK, 1.8))
    b.append(text(465, 64, "ASIA", 11, anchor="middle"))
    b.append(path("M448,140 L500,140 L504,178 L452,178 Z", INK, 1.8))
    b.append(text(476, 164, "AUS.", 11, anchor="middle"))
    b.append(path(f"M20,{h-26} L{DW-20},{h-26} L{DW-20},{h-8} L20,{h-8} Z", INK, 1.6))
    b.append(text(DW / 2, h - 12, "ANTARCTICA", 11, anchor="middle"))
    b.append(path("M150,4 q20,-2 30,8 q-4,12 -26,12 q-10,-8 -4,-20z", INK, 1.6))   # Greenland
    b.append(text(170, 36, "Greenland", 10, anchor="middle"))
    b.append(text(175, 130, "ATLANTIC", 11, anchor="middle"))
    b.append(text(372, 76, "INDIAN", 11, anchor="middle"))
    b.append(text(590, 60, "PACIFIC", 11, anchor="middle"))
    # warm shallow return flow (red): Pacific -> Indonesia -> Indian -> around Africa -> N Atlantic
    b.append(path("M600,170 Q560,110 505,122 L420,122 Q340,124 330,180 Q316,214 272,212 "
                  "Q220,210 210,160 L196,60", RED, 3))
    b.append(_ah(196, 58, math.atan2(-102, -14), RED, 11))
    b.append(_ah(440, 122, math.pi, RED, 10))
    b.append(text(560, 214, "warm SHALLOW (red)", 11, anchor="middle", col=RED))
    # sinking in N Atlantic
    b.append(text(188, 11, "NADW: cools, salty → SINKS", 11, weight="bold"))
    b.append(text(312, 34, "heat → air", 11)); b.append(text(312, 48, "(warms Europe)", 11))
    # cold deep flow (black): down Atlantic -> east along Antarctica -> up into Indian & Pacific
    b.append(path(f"M172,54 L140,120 L128,{h-44} Q132,{h-38} 160,{h-38} L610,{h-38}", INK, 2.6))
    b.append(_ah(134, 180, math.atan2(60, -6), INK, 10))
    b.append(_ah(430, h - 38, 0, INK, 10))
    b.append(arrow(372, h - 38, 372, 150, INK, 2.2))
    b.append(arrow(630, h - 40, 630, 150, INK, 2.2))
    b.append(text(380, 170, "rises", 11)); b.append(text(624, 170, "rises", 11, anchor="end"))
    b.append(text(160, h - 46, "SINKS (AABW)", 11, weight="bold"))
    b.append(text(390, h - 44, "cold, salty DEEP (black)", 11))
    b.append(text(560, 14, "1 loop ≈ 1000 yrs", 12, weight="bold"))
    return svg(DW, h, "".join(b))

# ---------------------------------------------------------------- content
ATM, OCN = "ATMOSPHERIC CIRCULATION", "OCEAN CIRCULATION"

CHEAT = [
    "{ru:AIR}: warm or humid air = LESS dense → rises → LOW (rain)",
    "  cold + dry air = MORE dense → sinks → HIGH (clear, dry)",
    "Wind blows HIGH → LOW · densest air = POLES (cold + dry)",
    "0° {r:L} ITCZ WET · 30° {r:H} DRY · 60° {r:L} WET · 90° {r:H} DRY",
    "Cells: Hadley 0–30° · Ferrel 30–60° · Polar 60–90°",
    "Winds: trades 0–30° · westerlies 30–60° · polar east. 60–90°",
    "Coriolis: RIGHT in NH, LEFT in SH · 0 at equator, ↑ w/ lat.",
    "  ↑ w/ speed + mass · big scale only · does NOT cause wind",
    "NH: air flowing into a LOW veers right → COUNTERCLOCKWISE",
    "Land heats + cools FASTER than water → breezes, monsoons",
    "Sea breeze = DAY (sea → land) · land breeze = NIGHT",
    "Monsoon = SEASONAL; summer: ocean → land = WET",
    "★ Hurricane needs: water > 27°C, low pressure, warm air w/",
    "  high water vapor, low wind shear (< 20 knots), Coriolis",
    "Fuel = LATENT HEAT released when water vapor condenses",
    "Hazards: surge, wind, rain, flooding, waves, landslides",
    "Surge ↑: strong onshore wind, big storm, head-on, wide shelf",
    "Path: steered AROUND highs (CW) → W, then N, then NE",
    "{ru:OCEAN}: surface currents = WIND · 10% of ocean · FAST",
    "  thermohaline = DENSITY (gravity) · 90% · SLOW",
    "Thermocline: 200 m (13°C) → 1000 m (4°C) = mixing barrier",
    "Ekman: surface 45°, NET transport 90° RIGHT of wind (NH)",
    "Gyres: CLOCKWISE in NH, COUNTERCLOCKWISE in SH",
    "W boundary (Gulf Stream) = FAST, narrow, deep, WARM",
    "  why: Earth rotates E + Coriolis ↑ toward poles → squeezed",
    "Upwelling = cold, nutrient-rich water up → plankton → fish",
    "  NH W coast: wind from N → offshore → UPWELLING",
    "  gyre center converges → downwelling · equator upwells",
    "★ El Niño: FEWER Atlantic hurricanes (↑ shear), MORE Pacific",
    "★ La Niña: MORE Atlantic hurricanes (↓ shear, weak trades)",
    "Deep water forms at poles: cold + salty (sea ice) → SINKS",
    "Fresh meltwater → conveyor SLOWS (Younger Dryas cooling)",
]

def content():
    B = []
    B.append(SECTION(ATM))
    B.append(L("{ru:ATMOSPHERIC CIRCULATION}  (The Atmosphere + Wind)", cls="sec"))
    B.append(L("Why care? wind starts ocean circulation · ocean + air trade"))
    B.append(L("  heat + gases · storms reshape the coast"))

    # 1 ---------------------------------------------------------------
    B.append(H("1. Air Density — how + why it changes", key="Air density — how/why it changes"))
    B.append(L("Air moves 2 ways:"))
    B.append(L("  HORIZONTAL (along surface) → PRESSURE: flows HIGH → LOW", tag="KEY"))
    B.append(L("  VERTICAL → DENSITY: less dense air RISES, dense air sinks"))
    B.append(L("  + Earth's rotation (Coriolis) changes the direction"))
    B.append(L("Sun = ultimate energy source for ocean + wind circulation"))
    B.append(L("Air density is controlled by 2 things:", tag="★"))
    B.append(L("  1) TEMPERATURE: warm air → molecules spread out → fewer"))
    B.append(L("     per volume → LESS dense → RISES"))
    B.append(L("     cold air → molecules packed close → MORE dense → SINKS"))
    B.append(L("  2) MOISTURE: water vapor H2O (18) is LIGHTER than"))
    B.append(L("     N2 (28, 78% of air) + O2 (32, 21% of air)"))
    B.append(L("     → {k:humid air is LESS dense than dry air} → rises", tag="★ trick"))
    B.append(L("∴ Densest air = POLES (cold + dry)"))
    B.append(L("  least dense = equator (warm + humid)"))

    # 2 ---------------------------------------------------------------
    B.append(H("2. High + Low Pressure — why they form + weather",
               key="High/low pressure: why + where + weather"))
    B.append(L("WHY = DIFFERENTIAL HEATING of Earth:", tag="WHY"))
    B.append(L("  equator: sun overhead → energy concentrated → HOT"))
    B.append(L("  poles: sun low in sky → same beam spread out → COLD"))
    B.append(L("  → heat SURPLUS at low latitudes, DEFICIT near poles"))
    B.append(L("  → atmosphere + oceans move surplus heat toward poles"))
    B.append(L("  (seasons: Earth's tilt changes where sun is most direct)"))
    B.append(L("Density changes start air moving → make H + L regions"))
    B.append(TBL([285, 280], [
        ["LOW pressure (L)", "HIGH pressure (H)"],
        ["warm, humid, less dense air", "cold, dry, dense air"],
        ["air RISES + COOLS → condenses", "air SINKS + WARMS → no clouds"],
        ["CLOUDS, RAIN, storms", "CLEAR, DRY, calm"],
        ["surface winds flow IN", "surface winds flow OUT"],
        ["where: 0° (ITCZ) + 60°", "where: 30° + 90° (poles)"],
    ]))

    # 3 ---------------------------------------------------------------
    B.append(H("3. Global Atmospheric Circulation ★ (DRAW IT)", key="Global circulation diagram ★"))
    B.append(L("Non-rotating Earth → 1 big cell per hemisphere"))
    B.append(L("Rotating Earth (Coriolis) → 3 CELLS per hemisphere:"))
    B.append(DIA(16, d_global()))
    B.append(L("0° = ITCZ (Intertropical Convergence Zone) / doldrums:", tag="ITCZ"))
    B.append(L("  NE + SE trades meet → air RISES → LOW → heavy rain"))
    B.append(L("30° = horse latitudes / subtropical HIGHS: dry air sinks"))
    B.append(L("  → world's DESERTS (Sahara, Arabia, Kalahari, Australia)"))
    B.append(L("60° = subpolar LOWS: air rises → rain/snow, storms"))
    B.append(L("90° = polar HIGHS: cold dry air sinks → very dry"))
    B.append(L("ITCZ follows the sun: July = farther N, January = farther S"))
    B.append(L("Winds are named for where they come FROM (NE trades)"))

    # 4 ---------------------------------------------------------------
    B.append(H("4. Coriolis Effect ★", key="Coriolis effect — why + result ★"))
    B.append(L("= APPARENT deflection of objects moving across Earth", tag="DEF"))
    B.append(L("WHY: Earth rotates W → E; every latitude makes 1 turn a day", tag="WHY"))
    B.append(L("  but the equator travels farther → moves FASTER"))
    B.append(L("  (equator ~40,000 km/day · 60° ~20,000 km/day · pole 0)"))
    B.append(L("  → object moving N/S keeps its OLD eastward speed"))
    B.append(L("  → ground under it is faster/slower → path CURVES"))
    B.append(SIDE([
        L("RESULT: deflects to RIGHT of", tag="★"),
        L("  travel in NH, LEFT in SH"),
        L("NONE at equator, ↑ with latitude"),
        L("↑ with SPEED + MASS of object"),
        L("Only big motions (> tens of km)"),
        L("Does NOT cause wind — only"),
        L("  changes its DIRECTION"),
    ], d_coriolis(), 300))
    B.append(L("Ex: wind H → L gets bent right (NH) · makes gyres + storms spin"))
    B.append(L("  (NH: air into a LOW veers right → COUNTERCLOCKWISE)"))

    # 5 ---------------------------------------------------------------
    B.append(H("5. Monsoons", key="Monsoons"))
    B.append(L("= SEASONAL reversal of winds → WET season + DRY season", tag="DEF"))
    B.append(L("WHY: land heats + cools FASTER than water (water has a", tag="WHY"))
    B.append(L("  high heat capacity → takes lots of heat to change temp)"))
    B.append(L("SUMMER: land hotter → air rises over land → LOW"))
    B.append(L("  → moist ocean air flows ONTO land → rises, cools → RAIN"))
    B.append(L("WINTER: land colder → air sinks over land → HIGH"))
    B.append(L("  → dry air flows from land OUT to sea → DRY season"))
    B.append(DIA(6, d_monsoon()))
    B.append(L("Moves w/ ITCZ: Jun–Jul ITCZ N over India (Kozhikode rain)"))
    B.append(L("  Dec–Jan ITCZ S → rain at Darwin, Australia"))

    # 6 ---------------------------------------------------------------
    B.append(H("6. Land + Sea Breeze", key="Land/sea breeze"))
    B.append(L("Same idea as monsoon but DAILY + small (coasts only)"))
    B.append(L("DAY: land heats faster → warm air rises over land (L)"))
    B.append(L("  → cool air sinks over sea (H) → ONSHORE = SEA BREEZE"))
    B.append(L("NIGHT: land cools faster → sea is warmer → rises over sea"))
    B.append(L("  (L), sinks over land (H) → OFFSHORE = LAND BREEZE"))
    B.append(L("Tip: a breeze is named for where it comes FROM", tag="TIP"))
    B.append(DIA(6, d_breeze()))

    # 7 ---------------------------------------------------------------
    B.append(H("7. What a Hurricane Needs to Form ★", key="Hurricane — conditions to form ★"))
    B.append(L("tropical cyclone = hurricane (Atl.) = typhoon (W Pacific)"))
    B.append(L("NEED (class list):", tag="★ LIST"))
    B.append(L("  1) WARM WATER > 27°C → heat + moisture = fuel"))
    B.append(L("  2) a LOW-PRESSURE system to start from"))
    B.append(L("  3) WARM air w/ HIGH WATER VAPOR"))
    B.append(L("  4) LOW WIND SHEAR (< 20 knots) → storm stays upright"))
    B.append(L("     (high shear TILTS the storm + tears it apart)"))
    B.append(L("  5) STRONG CORIOLIS → spin (none at equator)"))
    B.append(L("ENGINE = LATENT HEAT: warm ocean evaporates water (takes", tag="WHY"))
    B.append(L("  in heat) → air rises, vapor condenses → RELEASES heat"))
    B.append(L("  → air warms, rises faster → pressure drops → stronger"))
    B.append(L("Cyclonic flow: air rushes toward the L, veers RIGHT (NH)"))
    B.append(L("  → spins COUNTERCLOCKWISE in NH (clockwise in SH)"))
    B.append(L("Structure: moist surface winds spiral IN → rise in eyewall"))
    B.append(L("  (winds > 250 km/h) → exit at top · calm EYE ~13–16 km"))
    B.append(L("Form over warm tropical water (not at equator, none in"))
    B.append(L("  S Atlantic) · die over land or cold water (no fuel)"))

    # 8 ---------------------------------------------------------------
    B.append(H("8. Hurricane Hazards (Risks)", key="Hurricane risks / storm surge"))
    B.append(L("WAVES · WIND · RAIN · FLOODING · LANDSLIDES · STORM SURGE", tag="LIST"))
    B.append(L("Rain flooding can be far inland (Ivan → Asheville NC, 2004)"))
    B.append(L("{k:STORM SURGE} = sea pushed up onto the coast", tag="★"))
    B.append(L("  caused by strong ONSHORE WINDS (wind-driven)"))
    B.append(L("  low pressure lifts water a little (only ~5% of surge)"))
    B.append(L("  water \"piles up\" as it reaches shallow water at coast"))
    B.append(L("  worst if it hits at HIGH TIDE (Sandy 2012, Atlantic City)"))
    B.append(TBL([200, 290], [
        ["factor", "surge is HIGHER when…"],
        ["wind speed", "winds are STRONGER"],
        ["radius of storm", "storm is BIGGER"],
        ["forward speed", "fast = higher on open coast"],
        ["", "slow = floods longer + wider"],
        ["angle of approach", "hits PERPENDICULAR (head-on)"],
        ["continental shelf", "WIDE + gentle slope (shallow)"],
        ["shape of coastline", "bays / inlets funnel water in"],
    ], tag="★"))

    # 9 ---------------------------------------------------------------
    B.append(H("9. Predicting a Hurricane's Path ★", key="Predicting hurricane path ★"))
    B.append(L("Hurricanes are STEERED by winds around H + L systems"))
    B.append(L("Wind flows H → L · storm can't push INTO a high → goes"))
    B.append(L("  AROUND its edge (CLOCKWISE around a H in NH)"))
    B.append(L("  + gets pulled toward LOWS / troughs"))
    B.append(DIA(9, d_track()))
    B.append(L("Typical Atlantic track: ① forms off Africa, trades push W"))
    B.append(L("  ② reaches W edge of Bermuda High → turns N"))
    B.append(L("  ③ meets westerlies (~30°N) → curves NE, out to sea"))
    B.append(L("Strong High stretching W → storm keeps going W → FL/Gulf"))
    B.append(L("Weak High / High shifted E → turns N early → out to sea"))
    B.append(L("  or up the East Coast · LOW over E US pulls storm N"))

    # 10 --------------------------------------------------------------
    B.append(H("10. Hurricanes + Climate Change", key="Hurricanes + climate change"))
    B.append(L("EXPECTED as climate warms:", tag="FUTURE"))
    B.append(L("  warmer SST = more fuel → STRONGER storms (more Cat 4–5)"))
    B.append(L("  warmer air holds more vapor → MORE RAIN + flooding"))
    B.append(L("  sea-level rise → HIGHER STORM SURGE, more coast flooded"))
    B.append(L("  faster intensification · may reach farther from tropics"))
    B.append(L("  total # of storms: same or FEWER (no big increase)"))
    B.append(L("OBSERVED over last ~100 yrs:", tag="PAST"))
    B.append(L("  total # of hurricanes: NO clear long-term trend (old"))
    B.append(L("    records miss storms at sea — no satellites pre-1960s)"))
    B.append(L("  ↑ share of MAJOR (Cat 3–5) storms + ↑ rainfall"))
    B.append(L("  $ damage ↑ a lot → more people + buildings on coasts"))
    B.append(L("{k:NOT more hurricanes, but STRONGER + WETTER ones}", tag="★"))

    # ================================================================ OCEAN
    B.append(NEWPAGE)
    B.append(SECTION(OCN))
    B.append(L("{ru:OCEAN CIRCULATION}", cls="sec"))
    B.append(L("Why care? currents regulate CLIMATE (move + store heat,"))
    B.append(L("  store gases) + control PRODUCTIVITY (nutrients, O2)"))
    B.append(L("Key concepts: gyres · Ekman · W boundary currents ·"))
    B.append(L("  upwelling/downwelling · conveyor belt"))

    # 11 --------------------------------------------------------------
    B.append(H("11. Surface vs Deep Water ★", key="Surface vs deep water ★"))
    B.append(L("Ocean is LAYERED by density (cold + salty = dense)"))
    B.append(L("THERMOCLINE = layer where temp drops FAST with depth:", tag="DEF"))
    B.append(L("  ~200 m (660 ft) 13°C / 55°F → ~1000 m (3300 ft) 4°C / 39°F"))
    B.append(L("  = BARRIER → surface + deep water don't mix"))
    B.append(TBL([108, 250, 250], [
        ["", "SURFACE layer", "DEEP layer"],
        ["temp", "WARM (varies)", "COLD (~4°C or less)"],
        ["density", "LOW", "HIGH"],
        ["mixing", "mixed by WIND + waves", "not mixed by wind"],
        ["light", "sunlit → photosynthesis", "dark"],
        ["nutrients", "LOW (used by plankton)", "HIGH (from decay)"],
        ["oxygen", "HIGH (air + photosyn.)", "lower"],
        ["moved by", "WIND · 10% · FAST", "DENSITY · 90% · SLOW"],
        ["salinity", "varies (evap. vs rain)", "uniform"],
    ]))
    B.append(L("Salinity = parts per thousand (ppt, ‰) · avg ~35 (34.7)"))
    B.append(L("  salt comes from erosion of continents + hydrothermal vents"))
    B.append(L("  HIGH in subtropics (23.5–35°): evaporation > rain (dry"))
    B.append(L("    sinking air at 30°) · Atlantic = saltiest ocean"))
    B.append(L("  LOW at equator (rain), near rivers (Amazon, Ganges)"))

    # 12 --------------------------------------------------------------
    B.append(H("12. Major Ocean Currents (recognize them)", key="Major ocean currents"))
    B.append(L("Controlled by: WIND · DENSITY · CONTINENTS · CORIOLIS", tag="4 things"))
    B.append(L("GYRES = big loops: CLOCKWISE in NH, COUNTERCLOCKWISE SH", tag="★"))
    B.append(L("  5 gyres: N + S Atlantic, N + S Pacific, Indian Ocean"))
    B.append(L("  equatorial currents flow W (trades) · ~40–50° flow E"))
    B.append(L("W boundary = warm, flows toward POLE · E boundary = cold,"))
    B.append(L("  flows toward EQUATOR"))
    B.append(TBL([116, 250, 250], [
        ["gyre", "W boundary (WARM)", "E boundary (COLD)"],
        ["N Atlantic", "Gulf Stream", "Canary"],
        ["S Atlantic", "Brazil", "Benguela"],
        ["N Pacific", "Kuroshio", "California"],
        ["S Pacific", "East Australian", "Peru (Humboldt)"],
        ["Indian", "Agulhas", "West Australian"],
    ]))
    B.append(L("Also: N Atlantic Current (→ Europe) · N Pacific Current"))
    B.append(L("  N + S Equatorial Currents (→ W) · Eq. Countercurrent (→ E)"))
    B.append(L("  Antarctic Circumpolar Current (West Wind Drift) → E"))
    B.append(L("  all the way around Antarctica · cold: Labrador, Oyashio"))
    B.append(L("Gulf Stream: seen 1513 (Ponce de León), charted 1770s"))
    B.append(L("  by Ben Franklin · flow ≈ 300× the Amazon River"))

    # 13 --------------------------------------------------------------
    B.append(H("13. Forces That Drive Surface + Deep Currents ★", key="Forces → surface + deep currents ★"))
    B.append(TBL([108, 250, 250], [
        ["", "SURFACE currents", "DEEP (thermohaline)"],
        ["driven by", "WIND (drag on surface)", "DENSITY → GRAVITY"],
        ["amount", "~10% of ocean", "~90% of ocean"],
        ["speed", "FAST", "SLOW"],
        ["where", "above thermocline", "below thermocline"],
    ]))
    B.append(L("Surface currents also turned by CORIOLIS + CONTINENTS"))
    B.append(L("EKMAN SPIRAL: wind drags top layer, each layer drags the"))
    B.append(L("  one below → each deeper layer SLOWER + turned more right"))
    B.append(SIDE([
        L("surface water moves 45° RIGHT"),
        L("  of the wind (NH)"),
        L("NET water movement = EKMAN", tag="★"),
        L("  TRANSPORT = 90° RIGHT of wind"),
        L("  in NH · 90° LEFT in SH"),
        L(""),
    ], d_ekman(), 230))
    B.append(L("DEEP: THERMO (temp) + HALINE (salt) → density"))
    B.append(L("  density is \"fixed\" at the SURFACE, then water sinks"))
    B.append(L("  temp: cooled/heated by contact w/ the atmosphere"))
    B.append(L("  salinity ↑ evaporation + SEA ICE forming (leaves salt)"))
    B.append(L("  salinity ↓ precipitation, rivers, melting ice"))
    B.append(L("  cold + salty = DENSEST → sinks near the POLES"))

    # 14 --------------------------------------------------------------
    B.append(H("14. Why Speeds Vary: W vs E Boundary Currents ★", key="W vs E boundary currents ★"))
    B.append(DIA(11, d_gyre()))
    B.append(TBL([108, 250, 250], [
        ["", "WESTERN boundary", "EASTERN boundary"],
        ["speed", "FAST", "SLOW"],
        ["width", "NARROW", "WIDE"],
        ["depth", "DEEP", "SHALLOW"],
        ["temp", "WARM (from equator)", "COLD (from poles)"],
        ["flow", "Gulf Stream ~55 Sv", "Canary ~16 Sv"],
    ]))
    B.append(L("WHY = western intensification, caused by:", tag="★ WHY"))
    B.append(L("  1) EASTWARD rotation of Earth"))
    B.append(L("  2) Coriolis INCREASES with distance from equator"))
    B.append(L("  → these COMPRESS the W boundary current → same water"))
    B.append(L("    squeezed into a narrow path → SPEED ↑"))
    B.append(L("  (Sv = Sverdrup = 1 million m³ of water / sec)"))

    # 15 --------------------------------------------------------------
    B.append(H("15. How Surface Currents Affect Weather", key="How surface currents affect weather"))
    B.append(L("Currents carry HEAT from equator → poles"))
    B.append(L("WARM currents (W boundary, E coasts) → warm, humid air,"))
    B.append(L("  lots of evaporation → RAIN + fuel for storms/hurricanes"))
    B.append(L("COLD currents (E boundary, W coasts) → cool air, fog,"))
    B.append(L("  little evaporation → DRY coasts (Atacama, Namib deserts)"))
    B.append(L("Ex: Gulf Stream + N Atlantic Current warm W Europe:", tag="EX"))
    B.append(L("  Jan avg high/low: Newfoundland 30/16°F vs Ireland 46/37°F"))
    B.append(L("  (about the same latitude!)"))
    B.append(L("Water's high heat capacity → coasts milder than inland"))

    # 16 --------------------------------------------------------------
    B.append(H("16. Upwelling + Downwelling ★", key="Upwelling / downwelling ★"))
    B.append(L("UPWELLING = deep, cold, NUTRIENT-RICH water rises", tag="DEF"))
    B.append(L("DOWNWELLING = surface water piles up + SINKS", tag="DEF"))
    B.append(L("Coastal, NH west coast (e.g. California):"))
    B.append(L("  wind from NORTH → Ekman 90° right → water moves OFFSHORE"))
    B.append(L("  → deep water rises to replace it = UPWELLING"))
    B.append(L("  wind from SOUTH → water moves ONSHORE → piles up at"))
    B.append(L("  coast → sinks = DOWNWELLING"))
    B.append(DIA(9, d_upwelling()))
    B.append(L("EQUATORIAL: Coriolis turns water RIGHT north of equator +"))
    B.append(L("  LEFT south of it → water DIVERGES → UPWELLING"))
    B.append(L("SOUTHERN OCEAN: winds around Antarctica → upwelling"))
    B.append(L("GYRE CENTER: water CONVERGES → DOWNWELLING"))
    B.append(L("MARINE LIFE:", tag="★"))
    B.append(L("  upwelling → nutrients into sunlight → phytoplankton →"))
    B.append(L("  zooplankton → FISH · best fisheries: California, Peru,"))
    B.append(L("  Canary, Benguela (all EASTERN boundary currents)"))
    B.append(L("  downwelling → carries O2 down to deep-sea life, but"))
    B.append(L("  surface stays nutrient-poor → low productivity"))
    B.append(L("CLIMATE: upwelled cold water → cool, foggy coast · mixing"))
    B.append(L("  moves heat + gases (O2, CO2) between surface + deep"))

    # 17 --------------------------------------------------------------
    B.append(H("17. El Niño + La Niña (ENSO) ★", key="El Niño / La Niña + hurricanes ★"))
    B.append(L("ENSO = El Niño–Southern Oscillation (air-pressure seesaw"))
    B.append(L("  between W + E Pacific) · ANOMALY = difference from avg"))
    B.append(L("NORMAL: trade winds blow E → W → push warm water WEST"))
    B.append(L("  → warm pool + LOW (rain) over Indonesia/Australia"))
    B.append(L("  → cold UPWELLING off Peru (HIGH, dry, great fishing)"))
    B.append(L("EL NIÑO: trades WEAKEN → warm water sloshes EAST", tag="★"))
    B.append(L("  → thermocline deepens in E → upwelling stops → fish die"))
    B.append(L("  → RAIN + FLOODS in Peru · DROUGHT in Indonesia/Austr."))
    B.append(L("  → US winter: north WARMER, south WETTER"))
    B.append(L("LA NIÑA: trades STRONGER → even more warm water W", tag="★"))
    B.append(L("  → E Pacific colder than normal, strong upwelling"))
    B.append(L("  → floods in Indonesia/Australia · dry Peru"))
    B.append(L("  → US winter: north COLDER, south DRIER + warmer"))
    B.append(DIA(15, d_enso()))
    B.append(TBL([100, 280, 230], [
        ["HURR.", "ATLANTIC hurricanes", "E + central PACIFIC"],
        ["El Niño", "FEWER: ↑ shear + trades, stable", "MORE: ↓ wind shear"],
        ["La Niña", "MORE: ↓ shear + weak trades", "FEWER: ↑ wind shear"],
    ], tag="★"))

    # 18 --------------------------------------------------------------
    B.append(H("18. Deep Water Circulation + Climate ★", key="Deep water circulation + climate ★"))
    B.append(L("Deep water FORMS at poles: cooling + sea ice (salty) →"))
    B.append(L("  dense → SINKS → spreads along bottom → slowly rises"))
    B.append(L("  AABW = Antarctic Bottom Water (densest, Weddell Sea)"))
    B.append(L("  NADW = North Atlantic Deep Water (near Greenland)"))
    B.append(L("  Pacific deep water: weak layers, sluggish, uniform"))
    B.append(L("CONVEYOR BELT: warm shallow current → N Atlantic → gives"))
    B.append(L("  heat to air → cold + salty → SINKS → deep current S →"))
    B.append(L("  Antarctica → Indian + Pacific → rises → back (~1000 yrs)"))
    B.append(DIA(10, d_conveyor()))
    B.append(L("CLIMATE EFFECTS:", tag="★"))
    B.append(L("  moves heat equator → poles → keeps N Europe mild"))
    B.append(L("  carries O2 + CO2 (dissolved gases) into the deep ocean"))
    B.append(L("IF IT SLOWS: melting ice + rain → FRESHER, less dense water"))
    B.append(L("  → can't sink → conveyor slows → less heat → N. cools"))
    B.append(L("Happened before: YOUNGER DRYAS (~12,900–11,500 yrs ago)"))
    B.append(L("  Lake Agassiz meltwater → NH back to near-glacial cold"))
    B.append(L("  · ended fast: Greenland +10°C in about a decade"))
    B.append(L("Today: AMOC slowed in 20th century → \"cold blob\" S of"))
    B.append(L("  Greenland cooled while the rest of Earth warmed"))
    return B

# ---------------------------------------------------------------- paginate
def paginate(blocks):
    """Return pages: list of dict(header, items=[(line_no, block)]), index."""
    pages, index = [], []
    cur, line_no, section = None, 2, ""

    def new_page():
        nonlocal cur, line_no
        cur = {"header": section, "items": []}
        pages.append(cur)
        line_no = 2

    first_pg = 3  # pages 1-2 are cheat box + index
    new_page()
    for i, b in enumerate(blocks):
        if isinstance(b, SECTION):
            section = b.name
            if not cur["items"]:
                cur["header"] = section
            continue
        if b is NEWPAGE:
            if cur["items"]:
                new_page()
            cur["header"] = section
            continue
        need = b.n
        if isinstance(b, H):   # keep heading with the next block (or 2 lines)
            nxt = blocks[i + 1] if i + 1 < len(blocks) else None
            need = 1 + (nxt.n if isinstance(nxt, (DIA, TBL, BOX, SIDE)) else 2)
        if line_no + need - 1 > NLINES:
            new_page()
            cur["header"] = section
        if isinstance(b, H):
            index.append((b.key, len(pages) + first_pg - 1, section))
        cur["items"].append((line_no, b))
        line_no += b.n
    return pages, index

# ---------------------------------------------------------------- render
def ln_html(n, inner, cls="", x=TEXT_X, r=TEXT_R, tag=None, extra=""):
    top = rule_y(n) - SIT - BASE_IN_BOX
    s = (f'<div class="ln {cls}" data-line="{n}" style="top:{top:.2f}px;left:{x}px;width:{r-x}px"{extra}>'
         f'<span class="t">{inner}</span></div>')
    if tag:
        s += (f'<div class="ln tag" data-line="{n}" style="top:{top+1:.2f}px;left:6px;width:{MARGIN_X-12}px">'
              f'<span class="t">{fmt(tag)}</span></div>')
    return s

def render_item(n, b):
    out = []
    if isinstance(b, H):
        out.append(ln_html(n, f'<span class="u">{fmt(b.text)}</span>', "h", tag=b.tag))
    elif isinstance(b, L):
        out.append(ln_html(n, fmt(b.text), b.cls, tag=b.tag))
    elif isinstance(b, BOX):
        for k, l in enumerate(b.lines):
            out.append(ln_html(n + k, fmt(l.text), l.cls, x=TEXT_X + 6, tag=l.tag))
        y1, y2 = rule_y(n - 1) + 4, rule_y(n + b.n - 1) + 7
        col = RED if b.red else INK
        out.append(f'<div class="box" style="top:{y1}px;left:{TEXT_X-4}px;width:{TEXT_R-TEXT_X+8}px;'
                   f'height:{y2-y1}px;border-color:{col}"></div>')
    elif isinstance(b, TBL):
        xs = [TEXT_X]
        for w in b.cols:
            xs.append(xs[-1] + w)
        for k, row in enumerate(b.rows):
            for c, cell in enumerate(row):
                x0 = xs[c] + (0 if c == 0 else 8)
                x1 = xs[c + 1] - 4 if c + 1 < len(xs) - 1 else TEXT_R
                cls = "th" if k == 0 else ""
                out.append(ln_html(n + k, fmt(cell), cls, x=x0, r=x1,
                                   tag=(b.tag if (k == 0 and c == 0) else None)))
        # header underline drawn in ink ON the ruled line; column dividers
        yh = rule_y(n)
        out.append(f'<div class="ink-h" style="top:{yh-1}px;left:{TEXT_X}px;width:{xs[-1]-TEXT_X if len(b.cols)>1 else TEXT_R-TEXT_X}px"></div>')
        y1, y2 = rule_y(n - 1) + 5, rule_y(n + b.n - 1) + 6
        for x in xs[1:-1]:
            out.append(f'<div class="ink-v" style="top:{y1}px;left:{x-1}px;height:{y2-y1}px"></div>')
    elif isinstance(b, DIA):
        top = rule_y(n - 1)
        out.append(f'<div class="dwrap" data-lines="{n}-{n+b.n-1}" style="top:{top}px;left:{b.x}px;'
                   f'width:{b.w}px;height:{b.n*GAP}px">{b.svg}</div>')
    elif isinstance(b, SIDE):
        dx = TEXT_R + 4 - b.dia_w
        for k, l in enumerate(b.lines):
            out.append(ln_html(n + k, fmt(l.text), l.cls, r=dx - 6, tag=l.tag))
        top = rule_y(n - 1)
        out.append(f'<div class="dwrap" data-lines="{n}-{n+b.n-1}" style="top:{top}px;left:{dx}px;'
                   f'width:{b.dia_w}px;height:{b.n*GAP}px">{b.svg}</div>')
    elif isinstance(b, SKIP):
        pass
    return "".join(out)

def page_html(num, header, body):
    rules = "".join(f'<div class="rule" style="top:{rule_y(k)}px"></div>' for k in range(1, NLINES + 1))
    hdr = ln_html(1, f'<span class="hd">{fmt(header)}</span>', "hdr")
    pg = ln_html(1, f'<span class="pgno">Page {num}</span>', "pg", x=TEXT_R - 150, r=TEXT_R)
    return (f'<section class="page" id="p{num}"><div class="margin"></div>{rules}'
            f'{hdr}{pg}{body}</section>')

CSS = f"""
@page {{ size: 8.5in 11in; margin: 0; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; background: #d9d9d9; }}
body {{ font-family: "Liberation Sans", Arial, Helvetica, "DejaVu Sans", sans-serif; color: {INK}; }}
.page {{ position: relative; width: {PAGE_W}px; height: {PAGE_H}px; background: #fff; overflow: hidden;
        margin: 16px auto; break-after: page; page-break-after: always; }}
.page:last-child {{ break-after: auto; page-break-after: auto; }}
@media print {{ html, body {{ background: #fff; }} .page {{ margin: 0; }} }}
.rule {{ position: absolute; left: 0; width: {PAGE_W}px; height: 0; border-top: 1px solid #9cc3e5; }}
.margin {{ position: absolute; top: 0; bottom: 0; left: {MARGIN_X - 1}px; width: 0; border-left: 2px solid #ef9a9a; }}
.ln {{ position: absolute; height: {GAP}px; line-height: {GAP}px; font-size: {FONT_PX}px; white-space: nowrap; }}
.ln .t {{ display: inline-block; }}
.tag {{ font-size: 15px; color: {RED}; text-align: right; }}
.r {{ color: {RED}; }}
.u {{ text-decoration: underline; text-decoration-thickness: 1.5px; text-underline-offset: 3px; }}
.k {{ border: 1.6px solid {INK}; padding: 0 4px; margin: 0 1px; line-height: 19px; display: inline-block; }}
.r.k {{ border-color: {RED}; }}
.h .u {{ font-weight: bold; }}
.sec .t {{ font-weight: bold; letter-spacing: .5px; }}
.sec .u {{ text-decoration-style: double; text-decoration-thickness: 1.5px; }}
.th {{ font-weight: bold; }}
.hdr .hd {{ font-size: 15px; letter-spacing: 1px; color: #555; }}
.pg {{ text-align: right; }}
.pgno {{ font-weight: bold; border: 1.8px solid {RED}; color: {RED}; padding: 0 6px; line-height: 20px; display: inline-block; }}
.box {{ position: absolute; border: 2px solid {INK}; border-radius: 3px; }}
.ink-h {{ position: absolute; height: 0; border-top: 2px solid {INK}; }}
.ink-v {{ position: absolute; width: 0; border-left: 2px solid {INK}; }}
.dwrap {{ position: absolute; }}
.dia {{ display: block; overflow: visible; font-family: "Liberation Sans", Arial, Helvetica, "DejaVu Sans", sans-serif; }}
.idx .t {{ width: 100%; }}
.lead {{ display: inline-flex; width: 100%; align-items: baseline; }}
.lead .fill {{ flex: 1; border-bottom: 2px dotted #777; margin: 0 6px; transform: translateY(-5px); }}
"""

def build():
    blocks = content()
    pages, index = paginate(blocks)
    n_topic_pages = len(pages)
    last_page = 2 + n_topic_pages + 1
    html_pages = []

    # page 1: cheat box
    body = "".join(render_item(2, BOX([L(t) for t in CHEAT], red=True)))
    html_pages.append(page_html(1, "QUICK-HIT CHEAT BOX ★ (most-tested facts)", body))

    # page 2: index
    rows, n = [], 2
    def idx_line(n, left, right, cls="", tag=None):
        inner = (f'<span class="lead"><span>{fmt(left)}</span><span class="fill"></span>'
                 f'<span>{html.escape(str(right))}</span></span>')
        return ln_html(n, inner, "idx " + cls, tag=tag)
    rows.append(ln_html(n, fmt("{u:Topic}  →  page"), "th")); n += 1
    cur_sec = None
    for key, pg, sec in index:
        if sec != cur_sec:
            rows.append(ln_html(n, fmt("{ru:" + sec + "}"), "sec")); n += 1
            cur_sec = sec
        rows.append(idx_line(n, key, pg)); n += 1
    rows.append(idx_line(n, "Class assignments / activities", last_page, tag="★")); n += 1
    n += 1
    rows.append(ln_html(n, fmt("{u:Legend}: ★ = likely exam Q · {r:red} = key idea · → = leads to"))); n += 1
    rows.append(ln_html(n, fmt("NH/SH = N/S hemisphere · H/L = high/low pressure")))
    n += 1
    rows.append(ln_html(n, fmt("SST = sea-surface temp · ↑ ↓ = increase / decrease"))); n += 2
    rows.append(ln_html(n, fmt("Exam Wed 9/30 · on paper · INDIVIDUAL part (30 min) first,"))); n += 1
    rows.append(ln_html(n, fmt("  then TEAM part (20 min)"))); n += 1
    rows.append(ln_html(n, fmt("★ Qs come from CLASS ASSIGNMENTS too → review them (p. %d)" % last_page)))
    html_pages.append(page_html(2, "INDEX", "".join(rows)))

    # topic pages
    for i, p in enumerate(pages):
        num = 3 + i
        body = "".join(render_item(ln, b) for ln, b in p["items"])
        hdr = p["header"] + ("" if i == 0 or pages[i - 1]["header"] != p["header"] else " (cont.)")
        html_pages.append(page_html(num, hdr, body))

    # last page: blank class assignments page
    body = ln_html(2, fmt("{u:Class assignments / activities}"), "h")
    html_pages.append(page_html(last_page, "CLASS ASSIGNMENTS / ACTIVITIES", body))

    doc = (f'<!doctype html><html><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width, initial-scale=1">'
           f'<title>GEOL 211 Exam 2 Notes</title><style>{CSS}</style></head><body>'
           + "".join(html_pages) + "</body></html>")
    (OUT / "geol211_exam2_notes.html").write_text(doc, encoding="utf-8")
    meta = {"pages": len(html_pages), "index": index, "last_page": last_page,
            "layout": [[(ln, type(b).__name__, getattr(b, "n", 0)) for ln, b in p["items"]] for p in pages]}
    (OUT / "build" / "layout.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    print("pages:", len(html_pages))
    for key, pg, sec in index:
        print(f"  p{pg:>2}  {key}")

if __name__ == "__main__":
    build()
