"""SVG diagrams for the GEOL 211 Exam 2 study guide (black + red only, so they can be
redrawn with two pens). Every function returns an <svg> string."""
import html, math

INK, RED = "#161616", "#c8102e"
GAP = 27            # base unit for diagram heights (px)
DW = 658            # full diagram width (px)

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
    b.append(text(w - 4, h - 6, "dashed = path with no spin", 11, anchor="end"))
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
    b.append(text(380, 170, "rises", 11)); b.append(text(622, 142, "rises", 11, anchor="end"))
    b.append(text(160, h - 46, "SINKS (AABW)", 11, weight="bold"))
    b.append(text(390, h - 44, "cold, salty DEEP (black)", 11))
    b.append(text(560, 14, "1 loop ≈ 1000 yrs", 12, weight="bold"))
    return svg(DW, h, "".join(b))



# ================================================================ study-guide diagrams (v2)
def d_density(w=330, h=165):
    b = []
    boxes = [(18, "WARM air", 8, "fewer molecules", "LESS dense → RISES", -1, RED),
             (178, "COLD air", 24, "more molecules", "MORE dense → SINKS", 1, INK)]
    pts_warm = [(20, 22), (70, 18), (45, 50), (88, 55), (22, 80), (62, 86), (95, 30), (40, 30)]
    for ox, title, n, l1, l2, updown, col in boxes:
        b.append(text(ox + 55, 16, title, 14, anchor="middle", col=col, weight="bold"))
        b.append(f'<rect x="{ox}" y="24" width="110" height="100" fill="none" stroke="{INK}" stroke-width="2"/>')
        if n == 8:
            pts = pts_warm
        else:
            pts = [(12 + (k % 6) * 17 + (8 if (k // 6) % 2 else 0), 14 + (k // 6) * 23) for k in range(n)]
        for (px, py) in pts:
            b.append(f'<circle cx="{ox + px:.0f}" cy="{24 + py:.0f}" r="3.6" fill="{INK}"/>')
        ax = ox + 124
        if updown < 0:
            b.append(arrow(ax, 110, ax, 40, RED, 2.6))
        else:
            b.append(arrow(ax, 40, ax, 110, INK, 2.6))
        b.append(text(ox + 55, 142, l1, 12.5, anchor="middle"))
        b.append(text(ox + 55, 158, l2, 12.5, anchor="middle", col=col, weight="bold"))
    return svg(w, h, "".join(b))


def d_pressure(w=340, h=185):
    b = []
    g = 140
    b.append(line(6, g, w - 6, g, INK, 2.2))
    # LOW: rising air, cloud, rain
    lx = 80
    b.append(arrow(lx - 14, g - 8, lx - 14, 62, RED, 2.2))
    b.append(arrow(lx + 14, g - 8, lx + 14, 62, RED, 2.2))
    cx0, cy0 = lx, 36
    b.append(path(f"M{cx0-30},{cy0+8} q-4,-14 12,-13 q7,-14 23,-5 q16,-5 19,10 q3,9 -9,9 h-39 q-9,0 -6,-1z", INK, 1.7))
    for k in range(4):
        b.append(line(cx0 - 22 + k * 12, cy0 + 16, cx0 - 27 + k * 12, cy0 + 25, INK, 1.4))
    b.append(text(lx, g - 42, "L", 24, anchor="middle", col=RED, weight="bold"))
    # HIGH: sinking air, sun
    hx = w - 80
    b.append(arrow(hx - 14, 62, hx - 14, g - 8, INK, 2.2))
    b.append(arrow(hx + 14, 62, hx + 14, g - 8, INK, 2.2))
    sx, sy = hx, 34
    b.append(f'<circle cx="{sx}" cy="{sy}" r="10" fill="none" stroke="{INK}" stroke-width="1.8"/>')
    for k in range(8):
        a = k * math.pi / 4
        b.append(line(sx + 14 * math.cos(a), sy + 14 * math.sin(a), sx + 20 * math.cos(a), sy + 20 * math.sin(a), INK, 1.5))
    b.append(text(hx, g - 42, "H", 24, anchor="middle", weight="bold"))
    # surface wind H -> L
    b.append(arrow(hx - 36, g - 12, lx + 36, g - 12, INK, 2.4))
    b.append(text(w / 2, g - 20, "wind: H → L", 13, anchor="middle"))
    b.append(text(lx, g + 19, "LOW: air rises", 13, anchor="middle", weight="bold"))
    b.append(text(lx, g + 35, "→ clouds + rain", 13, anchor="middle"))
    b.append(text(hx, g + 19, "HIGH: air sinks", 13, anchor="middle", weight="bold"))
    b.append(text(hx, g + 35, "→ clear + dry", 13, anchor="middle"))
    return svg(w, h, "".join(b))


def d_breeze_monsoon():
    h = 6 * GAP; pw = 318
    b = _cell_panel(0, pw, h, True, "LAND WARMER than water", "= DAY (sea breeze) or SUMMER (wet monsoon)",
                    "wind: water → land", sea_lab="WATER")
    b += _cell_panel(pw + 22, pw, h, False, "LAND COOLER than water", "= NIGHT (land breeze) or WINTER (dry)",
                     "wind: land → water", sea_lab="WATER")
    b.append(line(pw + 11, 6, pw + 11, h - 6, INK, 1.2, dash=True))
    return svg(DW, h, "".join(b))


def d_thermo(w=320, h=215):
    b = []
    X = lambda t: 62 + t * 9          # temperature (deg C) -> x
    Y = {0: 34, 200: 76, 1000: 158, 2000: 200}
    b.append(line(62, 22, 62, 206, INK, 1.6))                 # depth axis
    b.append(arrow(62, 22, 250, 22, INK, 1.6, head=7))         # temperature axis
    b.append(text(156, 14, "temperature → warmer", 12, anchor="middle"))
    b.append(text(8, 118, "depth", 12)); b.append(arrow(22, 124, 22, 150, INK, 1.4, head=7))
    for d, lab in ((0, "0 m"), (200, "200 m"), (1000, "1000 m")):
        b.append(text(56, Y[d] + 4, lab, 11, anchor="end"))
    for d in (200, 1000):
        b.append(line(62, Y[d], w - 4, Y[d], INK, 1, dash=True))
    # profile: mixed layer 13C to 200 m, thermocline to 4C at 1000 m, then ~3C
    d = (f"M{X(13)},{Y[0]} L{X(13)},{Y[200]} "
         f"C{X(12.5)},{Y[200]+45} {X(5)},{Y[1000]-30} {X(4)},{Y[1000]} "
         f"L{X(3.2)},{Y[2000]}")
    b.append(path(d, RED, 3))
    b.append(text(X(13) + 6, Y[200] - 5, "13°C", 12, col=RED, weight="bold"))
    b.append(text(X(4) + 6, Y[1000] - 5, "4°C", 12, col=RED, weight="bold"))
    b.append(text(w - 6, Y[0] + 20, "SURFACE LAYER", 12, anchor="end", weight="bold"))
    b.append(text(w - 6, Y[0] + 35, "(mixed by wind)", 11, anchor="end"))
    b.append(text(w - 6, Y[200] + 38, "THERMOCLINE", 12, anchor="end", weight="bold"))
    b.append(text(w - 6, Y[200] + 53, "(temp drops fast)", 11, anchor="end"))
    b.append(text(w - 6, Y[1000] + 22, "DEEP LAYER", 12, anchor="end", weight="bold"))
    b.append(text(w - 6, Y[1000] + 37, "(cold, uniform)", 11, anchor="end"))
    return svg(w, h, "".join(b))


def _gyre_box(x1, y1, x2, y2, nh, wname, ename, basin_top=None):
    """Schematic gyre: NH clockwise, SH counterclockwise. West side = warm (red)."""
    b = []
    r = 14
    # sides as separate strokes so the warm (west) side can be red
    b.append(path(f"M{x1+r},{y1} L{x2-r},{y1}", INK, 2))           # top
    b.append(path(f"M{x2},{y1+r} L{x2},{y2-r}", INK, 2))           # east
    b.append(path(f"M{x2-r},{y2} L{x1+r},{y2}", INK, 2))           # bottom
    b.append(path(f"M{x1},{y2-r} L{x1},{y1+r}", RED, 3.2))         # west (warm)
    for (cx, cy, a1, a2) in ((x1 + r, y1 + r, 180, 270), (x2 - r, y1 + r, 270, 360),
                             (x2 - r, y2 - r, 0, 90), (x1 + r, y2 - r, 90, 180)):
        p1 = (cx + r * math.cos(math.radians(a1)), cy + r * math.sin(math.radians(a1)))
        p2 = (cx + r * math.cos(math.radians(a2)), cy + r * math.sin(math.radians(a2)))
        b.append(path(f"M{p1[0]:.1f},{p1[1]:.1f} A{r},{r} 0 0,1 {p2[0]:.1f},{p2[1]:.1f}", INK, 2))
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    if nh:   # clockwise: top -> E, east side -> S, bottom -> W, west side -> N
        b.append(_ah(mx + 5, y1, 0, INK, 9)); b.append(_ah(x2, my + 5, math.pi / 2, INK, 9))
        b.append(_ah(mx - 5, y2, math.pi, INK, 9)); b.append(_ah(x1, my - 5, -math.pi / 2, RED, 11))
    else:    # counterclockwise: top -> W, west side -> S, bottom -> E, east side -> N
        b.append(_ah(mx - 5, y1, math.pi, INK, 9)); b.append(_ah(x1, my + 5, math.pi / 2, RED, 11))
        b.append(_ah(mx + 5, y2, 0, INK, 9)); b.append(_ah(x2, my - 5, -math.pi / 2, INK, 9))
    b.append(text(x1 + 7, my - 9 if nh else my + 20, wname, 11.5, col=RED, weight="bold"))
    b.append(text(x2 - 7, my + 20 if nh else my - 9, ename, 11.5, anchor="end", weight="bold"))
    return b


def d_world_gyres(w=680, h=330):
    b = []
    eq = 158
    land = [  # (path, label, lx, ly)
        ("M0,14 L30,14 L34,120 L0,128 Z", "Asia", 15, 70),
        ("M0,196 L26,190 L30,250 L0,256 Z", "Aus.", 13, 226),
        ("M270,10 L372,10 L360,60 L330,118 L312,136 L300,110 L276,60 Z", "N. Amer.", 318, 50),
        ("M318,168 L364,170 L352,232 L334,286 L326,286 L320,230 Z", "S. Am.", 340, 204),
        ("M470,10 L520,10 L522,70 L512,84 L470,84 Z", "Europe", 494, 50),
        ("M464,96 L530,96 L536,160 L516,236 L500,244 L488,190 L464,150 Z", "Africa", 500, 150),
        ("M540,10 L680,10 L680,126 L612,126 L594,154 L574,120 L540,96 Z", "Asia", 620, 64),
        ("M628,196 L680,190 L680,256 L632,252 Z", "Aus.", 656, 226),
    ]
    for d, lab, lx, ly in land:
        b.append(path(d, INK, 1.6))
        b.append(text(lx, ly, lab, 11, anchor="middle"))
    b.append(line(34, eq, 680, eq, INK, 1, dash=True))
    b.append(text(40, eq - 4, "equator", 10))
    # gyres
    b += _gyre_box(58, 40, 258, 138, True, "Kuroshio", "California")
    b += _gyre_box(58, 176, 258, 272, False, "E. Australian", "Peru")
    b += _gyre_box(372, 40, 462, 138, True, "Gulf", "Canary")
    b.append(text(379, 97, "Stream", 11.5, col=RED, weight="bold"))
    b += _gyre_box(372, 176, 462, 272, False, "Brazil", "Benguela")
    b += _gyre_box(546, 176, 624, 272, False, "Agulhas", "W. Aus.")
    b.append(text(158, eq - 5, "PACIFIC", 12, anchor="middle", weight="bold"))
    b.append(text(417, eq - 5, "ATLANTIC", 12, anchor="middle", weight="bold"))
    b.append(text(648, eq - 5, "INDIAN", 12, anchor="middle", weight="bold"))
    # Antarctic Circumpolar Current
    b.append(arrow(40, 300, 660, 300, INK, 2.6))
    b.append(text(350, 320, "Antarctic Circumpolar Current (West Wind Drift) → flows EAST around Antarctica", 12, anchor="middle", weight="bold"))
    return svg(w, h, "".join(b))
