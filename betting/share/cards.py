#!/usr/bin/env python3
"""Final shareable cards, one design per sport, built from the decision layer (betting/final.py).

NFL "Sunday Card"       prime-time navy with yard lines, broadcast-style type, scoreboard numbers, bet-slip plays
                        with each team's colors, an injury-report QB Watch.
                        Sections: Best Bets · Totals · Sides · QB Watch · Price Watch & Model Leans · Streaks · Oddball
College "Saturday Slate" turf green with chalk lines, varsity lettering, gold pennants; Blowout Overs as a scoreboard
                        showing how few points the market expects from each underdog.
                        Sections: Blowout Overs · Weather Desk · Other Plays · Top 25 Watch · QB Changes · Model Leans ·
                        Streaks · Systems Lab · Oddball

Every play carries a "Why": a game-specific lead with the real numbers, then each supporting signal with its record.
Units convert to dollars from betting/share/settings.json.

Usage: python3 betting/final.py && python3 betting/share/cards.py [nfl|cfb]
"""
import json
import os
import subprocess
import sys
from datetime import datetime

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
BET = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, BET)
import weekly as W  # noqa: E402

E, ET = W.E, W.ET
SETTINGS = json.load(open(os.path.join(HERE, "settings.json"))) if os.path.exists(os.path.join(HERE, "settings.json")) else {}
UNIT = float(SETTINGS.get("unit_dollars", 10))
SYSTEMS = {"Blowout over", "Wind under", "Close road team", "Close road team ML", "Buy-low underdog", "Rested home team",
           "Steady wind under", "Steady rain under", "Over-streak fade"}
WEATHER = ("Steady wind under", "Steady rain under")
FONTS = {"BebasNeue-Regular.ttf": "bebasneue/BebasNeue-Regular.ttf", "Graduate-Regular.ttf": "graduate/Graduate-Regular.ttf"}


def money(u):
    d = u * UNIT
    return f"${d:,.0f}" if d == int(d) else f"${d:,.2f}"


BASE_CSS = """
.wl { margin:7px 0 0; padding:0; list-style:none; }
.wl li { position:relative; padding-left:13px; margin:4px 0; color:var(--ink2); }
.wl li::before { content:''; position:absolute; left:0; top:.6em; width:6px; height:6px; border-radius:1px; background:var(--accent2); transform:rotate(45deg); }
.wl b.l { color:var(--ink); }
.chips { margin-top:5px; }
.chip { display:inline-block; font-size:6.8pt; font-weight:700; letter-spacing:.06em; text-transform:uppercase; border-radius:4px;
        padding:2px 7px; margin:0 4px 2px 0; background:var(--soft); color:var(--ink2); }
.chip.model { background:var(--greenbg); color:var(--green); }
.chip.sys { background:#e8eefc; color:var(--blue); }
.chip.ang { background:var(--amberbg); color:var(--amber); }

/* bet slip */
.slip { display:grid; grid-template-columns:7px 1fr 118px; border:1px solid var(--line); border-radius:12px; overflow:hidden;
        margin-bottom:10px; break-inside:avoid; background:#fff; box-shadow:0 1px 0 rgba(10,20,40,.04); }
.slip .stripe { background:linear-gradient(180deg, var(--c1) 0 50%, var(--c2) 50% 100%); }
.slip .main { padding:11px 14px 11px 13px; }
.slip .top { display:flex; align-items:center; gap:10px; }
.slip .lg { display:flex; align-items:center; gap:2px; }
.slip .pk { font-family:var(--display); font-size:var(--pick-size); line-height:1; letter-spacing:var(--display-track); color:var(--ink); }
.slip .pk .odds { font-family:'Inter'; font-size:10.5pt; font-weight:600; color:var(--mute); margin-left:7px; letter-spacing:0; }
.slip .meta { margin-top:3px; }
.slip .stub { position:relative; border-left:2px dashed #cfd5de; background:var(--stub); padding:12px 10px; text-align:center;
              display:flex; flex-direction:column; justify-content:center; gap:3px; }
.slip .stub::before, .slip .stub::after { content:''; position:absolute; left:-9px; width:16px; height:16px; border-radius:50%;
              background:#fff; border:1px solid var(--line); }
.slip .stub::before { top:-9px; } .slip .stub::after { bottom:-9px; }
.stub .units { font-family:var(--display); font-size:26pt; line-height:.9; color:var(--ink); letter-spacing:var(--display-track); }
.stub .usd { font-size:11pt; font-weight:750; color:var(--green); }
.stub .bk { font-size:7pt; color:var(--mute); text-transform:uppercase; letter-spacing:.08em; font-weight:650; }
.stub .tier { font-size:6.8pt; font-weight:750; letter-spacing:.1em; text-transform:uppercase; color:#fff; background:var(--accent2);
              border-radius:3px; padding:2px 6px; align-self:center; margin-top:3px; }
.stub .tier.play { background:var(--mute); }

/* injury report */
.ir { display:grid; grid-template-columns:40px 1fr auto; column-gap:12px; align-items:start; border:1px solid var(--line);
      border-radius:12px; padding:10px 13px; margin-bottom:8px; break-inside:avoid; background:#fff; }
.ir .name { font-weight:750; font-size:10.5pt; }
.st { display:inline-block; font-size:6.8pt; font-weight:800; letter-spacing:.1em; text-transform:uppercase; padding:2px 7px;
      border-radius:3px; margin-left:7px; color:#fff; background:#b42318; vertical-align:2px; }
.st.q { background:#c77700; } .st.new, .st.chg { background:#1d4ed8; }

/* streak bars */
.bar { height:4px; border-radius:2px; margin-top:3px; background:var(--line); }
.bar i { display:block; height:4px; border-radius:2px; }
.bar i.hot { background:var(--green); } .bar i.cold { background:var(--red); } .bar i.neu { background:var(--blue); }
"""

NFL_CSS = """
@font-face { font-family:'Bebas'; src:url('assets/BebasNeue-Regular.ttf'); }
:root { --accent:#0b1b33; --accent2:#d50a0a; --display:'Bebas'; --display-track:.02em; --pick-size:21pt; --stub:#f4f6f9; }
.hero { position:relative; overflow:hidden; border-radius:16px; padding:22px 24px 18px; margin-bottom:18px; color:#fff;
        background:
          repeating-linear-gradient(90deg, rgba(255,255,255,.08) 0 1.5px, transparent 1.5px 46px),
          radial-gradient(ellipse at 85% 0%, rgba(213,10,10,.35), transparent 55%),
          linear-gradient(135deg, #0a1830 0%, #13294b 55%, #0a1830 100%);
        border-bottom:5px solid var(--accent2); display:flex; justify-content:space-between; align-items:flex-end; }
.hero::before, .hero::after { content:''; position:absolute; left:0; right:0; height:7px;
        background:repeating-linear-gradient(90deg, rgba(255,255,255,.22) 0 1.2px, transparent 1.2px 9.2px); }
.hero::before { top:10px; } .hero::after { bottom:10px; }
.hero .eyebrow { font-weight:700; letter-spacing:.2em; opacity:.8; }
.hero h1 { font-family:'Bebas'; font-weight:400; font-size:48pt; line-height:.9; letter-spacing:.02em; margin:6px 0 2px; }
.hero h1 span { color:#ff3b3b; }
.hero .sub { opacity:.85; }
.kpis { gap:7px; }
.kpi { background:#050d1b; border:1px solid rgba(255,255,255,.14); border-radius:8px; padding:6px 12px 7px; text-align:center; min-width:74px; }
.kpi b { font-family:'Bebas'; font-weight:400; font-size:25pt; line-height:1; color:#ffd24d; letter-spacing:.03em; }
.kpi span { font-size:6.6pt; opacity:.75; letter-spacing:.12em; }
h2 { font-family:'Bebas'; font-weight:400; font-size:17pt; letter-spacing:.05em; color:var(--ink); text-transform:none; margin:20px 0 8px; }
h2::before { content:''; width:7px; height:17px; background:var(--accent2); border-radius:1px; display:inline-block; }
h2::after { background:repeating-linear-gradient(90deg, #d7dce4 0 6px, transparent 6px 10px); height:2px; }
"""

CFB_CSS = """
@font-face { font-family:'Varsity'; src:url('assets/Graduate-Regular.ttf'); }
:root { --accent:#14532d; --accent2:#e0a526; --display:'Varsity'; --display-track:0; --pick-size:15.5pt; --stub:#fbf6e8; }
.hero { position:relative; overflow:hidden; border-radius:16px; padding:22px 24px 20px; margin-bottom:18px; color:#fff;
        background:
          repeating-linear-gradient(90deg, rgba(255,255,255,.13) 0 2px, transparent 2px 48px),
          repeating-linear-gradient(90deg, rgba(0,0,0,.05) 0 24px, transparent 24px 48px),
          radial-gradient(ellipse at 80% -10%, rgba(224,165,38,.35), transparent 55%),
          linear-gradient(160deg, #1b6a3a 0%, #14532d 55%, #0e3d21 100%);
        border-bottom:5px solid var(--accent2); display:flex; justify-content:space-between; align-items:flex-end; }
.hero::after { content:''; position:absolute; left:0; right:0; top:12px; height:3px; background:rgba(255,255,255,.35); }
.hero .eyebrow { font-weight:700; letter-spacing:.2em; color:#f7d27a; opacity:1; }
.hero h1 { font-family:'Varsity'; font-weight:400; font-size:32pt; line-height:1; margin:8px 0 4px; letter-spacing:.01em;
           text-shadow:0 2px 0 rgba(0,0,0,.25); }
.hero .sub { opacity:.9; }
.kpis { gap:8px; align-items:flex-start; }
.kpi { background:#fbf3dc; color:#14532d; border-radius:4px 4px 0 0; padding:9px 10px 18px; min-width:78px; text-align:center;
       clip-path:polygon(0 0, 100% 0, 100% 100%, 50% 82%, 0 100%); }
.kpi b { font-family:'Varsity'; font-weight:400; font-size:17pt; color:#14532d; }
.kpi span { color:#6b5a2a; opacity:1; font-size:6.4pt; letter-spacing:.1em; font-weight:700; }
h2 { font-family:'Varsity'; font-weight:400; font-size:12.5pt; letter-spacing:.02em; color:#14532d; text-transform:none; margin:22px 0 9px; }
h2::after { background:var(--accent2); height:2px; opacity:.7; }

/* ranks and records */
.rk { display:inline-block; background:#e0a526; color:#0e3d21; font-weight:800; font-size:.8em; line-height:1.25;
      border-radius:4px; padding:0 3px; margin-right:3px; vertical-align:1px; }
.wl { color:var(--ink2); font-weight:500; font-size:.88em; }
.t25 td { vertical-align:top; }
.t25 .gap { font-size:7pt; font-weight:750; border-radius:10px; padding:1px 6px; white-space:nowrap; }
.t25 .gap.hi { background:#fdecea; color:#9a3b2f; } .t25 .gap.lo { background:#e7efe9; color:#14532d; }
.t25 .gap.ok { background:#f1ede2; color:#8a7a4a; }
.labcat .bench { font-size:6.9pt; color:var(--ink2); padding-top:4px; border-top:1px dashed #eee6cf; line-height:1.45; }
.labcat .bench .pos { color:var(--green); font-weight:700; } .labcat .bench .neg { color:#9a3b2f; }
.t25 { table-layout:fixed; } .t25 td { font-size:7.8pt; } .t25 .gap { font-size:6.4pt; } .t25 td, .t25 td.b, .t25 td.n { white-space:normal; }
.labcat .bench b { color:#8a7a4a; font-size:6pt; letter-spacing:.08em; text-transform:uppercase; margin-right:4px; }

/* weather desk */
.wx { border:1px solid #d6e2ea; border-radius:12px; overflow:hidden; background:#fff; }
.wx-row { display:grid; grid-template-columns:7px 58px 1.15fr 122px 1.6fr 112px; align-items:center; column-gap:10px;
          border-bottom:1px solid #e6eef3; padding:8px 10px 8px 0; break-inside:avoid; }
.wx-row:last-child { border-bottom:0; }
.wx-row .stripe { align-self:stretch; background:linear-gradient(180deg, var(--c1) 0 50%, var(--c2) 50% 100%); }
.wx-row .game b { display:block; font-size:9pt; }
.tiles { display:flex; gap:5px; }
.tile { flex:1; border-radius:8px; text-align:center; padding:5px 3px 4px; background:#eef3f6; color:#4b5d68; }
.tile b { display:block; font-family:'Varsity'; font-weight:400; font-size:14pt; line-height:1; }
.tile span { font-size:5.8pt; letter-spacing:.08em; text-transform:uppercase; font-weight:700; }
.tile.hot.wind { background:#1e3a5f; color:#cfe1f5; } .tile.hot.wind b { color:#fff; }
.tile.hot.rain { background:#0f5257; color:#c9ece9; } .tile.hot.rain b { color:#fff; }
.wx-row .sbwhy { font-size:8.2pt; color:var(--ink2); }
.windbar { height:5px; background:#e6eef3; border-radius:3px; margin-top:4px; }
.windbar i { display:block; height:5px; border-radius:3px; background:linear-gradient(90deg, #7fb3d5, #1e3a5f); }
.wx-row .sbbet { text-align:right; font-size:8.2pt; color:var(--ink2); }
.wx-row .sbbet b { font-family:'Varsity'; font-weight:400; font-size:12.5pt; color:#1e3a5f; display:block; line-height:1.15; }
.wx-row .sbbet .usd { font-weight:750; color:var(--green); }

/* systems lab */
.lab { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
.labcat { border:1px solid #e3dcc6; border-radius:10px; background:#fff; padding:8px 10px 6px; break-inside:avoid; }
.labcat h4 { margin:0 0 4px; font-family:'Varsity'; font-weight:400; font-size:10pt; color:#14532d; display:flex;
             justify-content:space-between; align-items:center; }
.labcat h4 small { font-family:inherit; font-size:6.4pt; letter-spacing:.1em; text-transform:uppercase; color:#8a7a4a; }
.labrow { display:grid; grid-template-columns:1fr 54px 54px 92px; column-gap:6px; align-items:center; font-size:7.6pt;
          padding:3px 0; border-top:1px dashed #eee6cf; }
.labrow .nm { color:var(--ink); } .labrow .nm i { display:block; font-style:normal; color:var(--ink2); font-size:6.8pt; }
.labrow .n { text-align:right; font-variant-numeric:tabular-nums; }
.labrow .pos { color:var(--green); font-weight:700; } .labrow .neg { color:#9a3b2f; }
.verdict { font-size:6.4pt; font-weight:750; letter-spacing:.05em; text-transform:uppercase; border-radius:20px;
           padding:2px 6px; text-align:center; }
.verdict.on { background:#14532d; color:#ffd46b; } .verdict.alt { background:#e7efe9; color:#14532d; }
.verdict.off { background:#f1ede2; color:#8a7a4a; }
.labhead { display:grid; grid-template-columns:1fr 54px 54px 92px; column-gap:6px; font-size:6pt; letter-spacing:.1em;
           text-transform:uppercase; color:#8a7a4a; font-weight:750; }
.labhead span { text-align:right; } .labhead span:first-child { text-align:left; }

/* scoreboard for blowout overs */
.sb { border:1px solid #e3dcc6; border-radius:12px; overflow:hidden; background:#fff; }
.sb-row { display:grid; grid-template-columns:7px 58px 1.25fr 74px 1.7fr 112px; align-items:center; column-gap:10px;
          border-bottom:1px solid #eee6cf; padding:8px 10px 8px 0; break-inside:avoid; }
.sb-row:last-child { border-bottom:0; }
.sb-row .stripe { align-self:stretch; background:linear-gradient(180deg, var(--c1) 0 50%, var(--c2) 50% 100%); }
.sb-row .game b { display:block; font-size:9pt; }
.dog { background:#0e3d21; color:#ffd46b; border-radius:8px; text-align:center; padding:5px 4px 4px; }
.dog b { display:block; font-family:'Varsity'; font-weight:400; font-size:17pt; line-height:1; }
.dog span { font-size:6pt; letter-spacing:.08em; text-transform:uppercase; color:#cfe3d4; font-weight:700; }
.sb-row .sbwhy { font-size:8.2pt; color:var(--ink2); }
.spreadbar { height:5px; background:#efe8d3; border-radius:3px; margin-top:4px; }
.spreadbar i { display:block; height:5px; border-radius:3px; background:linear-gradient(90deg, #e0a526, #b45309); }
.sb-row .sbbet { text-align:right; font-size:8.2pt; color:var(--ink2); }
.sb-row .sbbet b { font-family:'Varsity'; font-weight:400; font-size:12.5pt; color:#14532d; display:block; line-height:1.15; }
.sb-row .sbbet .usd { font-weight:750; color:var(--green); }
.sb-head { display:grid; grid-template-columns:7px 58px 1.25fr 74px 1.7fr 112px; column-gap:10px; padding:6px 10px 6px 0;
           background:#fbf6e8; font-size:6.6pt; letter-spacing:.1em; text-transform:uppercase; color:#6b5a2a; font-weight:750; }
.intro { background:#fbf6e8; border:1px solid #efe3c0; border-radius:12px; padding:11px 14px; margin-bottom:10px; }
.intro h3 { font-family:'Varsity'; font-weight:400; color:#14532d; margin:0 0 4px; font-size:12pt; }
"""


def ensure_fonts():
    W.ensure_font()
    import requests
    for fn, rel in FONTS.items():
        path = os.path.join(W.ASSETS, fn)
        if not os.path.exists(path):
            r = requests.get("https://raw.githubusercontent.com/google/fonts/main/ofl/" + rel, timeout=60)
            r.raise_for_status()
            open(path, "wb").write(r.content)


def load_final(sport):
    p = os.path.join(BET, "data", "final_nfl.json") if sport == "nfl" else os.path.join(BET, "data", "cfb", "final_cfb.json")
    return json.load(open(p))


def team_colors(S, game):
    _r, info, _d = S.teams(game)
    def fix(c):
        c = (c or "#8a93a3").lstrip("#")
        if len(c) != 6:
            return "#8a93a3"
        r, g, b = (int(c[i:i + 2], 16) for i in (0, 2, 4))
        return "#8a93a3" if (0.299 * r + 0.587 * g + 0.114 * b) > 225 else "#" + c
    if not info:
        return "#8a93a3", "#8a93a3"
    return fix(info["away"].get("color")), fix(info["home"].get("color"))


def chips(p):
    out = []
    for s in p["signals"]:
        cls = "model" if s == "Model" else "sys" if s in SYSTEMS else "ang"
        out.append(f"<span class='chip {cls}'>{E(s)}</span>")
    if p["model_agrees"] and "Model" not in p["signals"]:
        out.append("<span class='chip model'>Model leans same way</span>")
    return "<div class='chips'>" + "".join(out) + "</div>"


def lead(S, p):
    """The game-specific first line of the Why."""
    sig = p["signals"]
    if "Model" in sig:
        cp = next((x for x in S.card["week"]["picks"] if x["game"] == p["game"] and x["market"] == p["market"]
                   and x["side"] == p["side"]), None)
        if cp:
            return W.model_reason(S, dict(cp, bet=p["bet"], odds=p["odds"], book=p["book"]))
    for name in WEATHER + ("Wind under", "Blowout over", "Close road team", "Close road team ML", "Over-streak fade"):
        if name in sig:
            return W.system_reason(S, {"name": name, "why": ""}, p)
    if "Buy-low underdog" in sig:
        return W.side_reason(S, {"name": "Buy-low underdog"}, p)
    return None


def why_block(S, p):
    items = []
    first = lead(S, p)
    if first:
        items.append(f"<li><b class='l'>The spot:</b> {first}</li>")
    for b in p["backup"]:
        if b["title"].startswith("Model") and "Model" in p["signals"]:
            continue
        items.append(f"<li><b class='l'>{E(b['title'])}:</b> {E(b['text'])}</li>")
    return "<ul class='wl'>" + "".join(items) + "</ul>"


def play_card(S, p):
    c1, c2 = team_colors(S, p["game"])
    tier = "play" if p["tier"] == "Play" else ""
    return (f"<div class='slip' style='--c1:{c1};--c2:{c2}'><div class='stripe'></div><div class='main'>"
            f"<div class='top'><div class='lg'>{S.logos(p['game'], 26)}</div><div>"
            f"<div class='pk'>{E(p['bet'])}<span class='odds'>{W.fmt_odds(p['odds'])}</span></div>"
            f"<div class='meta'>{W.matchup(S, p['game'])} · {S.when(p['game'])}</div></div></div>"
            f"{chips(p)}{why_block(S, p)}</div>"
            f"<div class='stub'><div class='units'>{p['units']:g}U</div><div class='usd'>{money(p['units'])}</div>"
            f"<div class='bk'>{E(p['book'])}</div><div class='tier {tier}'>{E(p['tier'])}</div></div></div>")


def date_range(S):
    dates = sorted(d for d in (S.teams(g)[2] for g in S.rows) if d)
    if not dates:
        return ""
    d0 = datetime.fromisoformat(dates[0].replace("Z", "+00:00")).astimezone(ET)
    d1 = datetime.fromisoformat(dates[-1].replace("Z", "+00:00")).astimezone(ET)
    return (d0.strftime("%b %-d") + ("" if d0.date() == d1.date() else "–" + d1.strftime("%-d" if d0.month == d1.month else "%b %-d"))
            + d1.strftime(", %Y"))


def hero(S, sport, eyebrow, title_html, kpis):
    books = "FanDuel · DraftKings" if os.path.exists(os.path.join(BET, "odds_api_key.txt")) or os.environ.get("ODDS_API_KEY") else "DraftKings"
    css = W.CSS % {"accent": "#0b1b33" if sport == "nfl" else "#14532d"}
    h = [f"<style>{css}{BASE_CSS}{NFL_CSS if sport == 'nfl' else CFB_CSS}</style><div class='hero'><div>",
         f"<div class='eyebrow'>{eyebrow}</div><h1>{title_html}</h1>",
         f"<div class='sub'>Best price at {books} · 1 unit = {money(1)}</div></div><div class='kpis'>"]
    for v, k in kpis:
        h.append(f"<div class='kpi'><b>{E(str(v))}</b><span>{E(k)}</span></div>")
    h.append("</div></div>")
    return h


def lean_label(S, l):
    b = S.board.get(l["game"], {})
    away, home = l["game"].split(" @ ")
    if l["market"] == "total":
        return f"{l['side'].title()} {b.get('market_total', '')}"
    team = home if l["side"] == "home" else away
    if l["market"] == "ml":
        return f"{team} ML"
    try:
        home_line = float(b.get("market_spread", "").split()[-1])
        return f"{team} {(home_line if l['side'] == 'home' else -home_line):+g}"
    except (ValueError, IndexError):
        return team


def leans_table(S, F, avoid=()):
    rows, seen = [], set()
    for l in F["leans"]:
        if "model agrees" in l["note"]:
            continue
        seen.add((l["game"], l["market"]))
        label = lean_label(S, l)
        flag = next((t for t in avoid if label.startswith(t + " ")), None)
        note = (f"<b>Skip: QB Watch says avoid {E(flag)}.</b>" if flag else f"<span class='meta'>{E(l['note'])}</span>")
        rows.append((l["game"], label, f"{E(l['why'].rstrip('.'))}. {note}"))
    for m in F["model_leans"]:
        mk = "total" if m["bet"].split()[0] in ("Over", "Under") else "spread"
        if (m["game"], mk) in seen:
            continue
        rows.append((m["game"], f"{m['bet']} {W.fmt_odds(m['odds'])}",
                     f"Model fair {m['fair']} vs market {m['market']} (raw model {m['model_raw']}); "
                     f"{m['ev']:+.1f}% at this price. Bet at {E(str(m['target']).split(';')[0])}."))
    if not rows:
        return ["<p class='empty'>Nothing else worth tracking this week.</p>"]
    h = ["<table><tr><th style='width:60px'></th><th>Game</th><th>Lean</th><th>Why / price needed</th></tr>"]
    for g, what, why in rows:
        h.append(f"<tr><td class='lgc'>{S.logos(g, 18)}</td><td class='n'>{W.matchup(S, g)}</td><td class='b'>{E(what)}</td><td>{why}</td></tr>")
    h.append("</table>")
    return h


def status_class(s):
    s = s.lower()
    return "q" if "question" in s else "new" if "new" in s else "chg" if "change" in s else ""


def qb_block(qb):
    if not qb:
        return ["<p class='empty'>No starting-QB issues on this slate.</p>"]
    h = []
    for x in qb:
        nxt = f" · next up: {E(x['backup'])}" if x.get("backup") and x["status"] not in ("QB change", "New starter") else ""
        h.append(f"<div class='ir'><div>{x['logo']}</div><div><span class='name'>{E(x['qb'])}</span>"
                 f"<span class='st {status_class(x['status'])}'>{E(x['status'])}</span>"
                 f"<div class='meta'>{E(x['team'])} · {E(x['game'])} · {E(x['detail'])}{nxt}</div>"
                 f"<div style='margin-top:4px;color:var(--ink2)'>{x['why']}</div></div>"
                 f"<div><span class='pill {x['cls']}'>{E(x['verdict'])}</span></div></div>")
    return h


def streak_block(st):
    titles = {"win": "Winning streaks", "loss": "Losing streaks", "ats": "Against the spread", "ou": "Over / Under"}
    top = max([x["n"] for c in st.values() for x in c] + [1])
    h = ["<div class='grid2'>"]
    for c, title in titles.items():
        h.append(f"<div class='mini'><h4>{title}</h4><table>")
        for x in st[c]:
            ln = f" ({x['line']:+g})" if x["line"] is not None and c in ("win", "loss", "ats") else ""
            k = "hot" if x["tag"].startswith(("W", "Covered")) else "cold" if x["tag"].startswith(("L", "Failed")) else "neu"
            h.append(f"<tr><td class='sk {k}' style='width:74px'>{E(x['tag'])}<div class='bar'><i class='{k}' "
                     f"style='width:{max(8, 100 * x['n'] / top):.0f}%'></i></div></td><td><b>{E(str(x['team']))}</b>"
                     f"<div class='meta'>ATS last 10: {x['ats10']}</div></td><td class='n right'>{E(x['next'])}{ln}</td></tr>")
        if not st[c]:
            h.append("<tr><td class='empty'>None</td></tr>")
        h.append("</table></div>")
    h.append("</div>")
    return h


def oddball_block(S, sport):
    p = os.path.join(HERE, f"oddball_{sport}.json")
    if not os.path.exists(p):
        return []
    o = json.load(open(p))
    return ["<h2>Oddball Matchup of the Week</h2>",
            f"<div class='odd'><div style='display:flex;gap:10px;align-items:center'>{S.logos(o['game'], 32)}"
            f"<div><div class='t'>{E(o['title'])}</div><div class='meta'>{E(o['sub'])}</div></div></div>"
            f"<div style='margin-top:8px'>{E(o['body'])}</div>"
            f"<div class='fact'><b class='k'>Did you know</b>{E(o['fact'])}</div>"
            f"<div class='meta' style='margin-top:8px'>{E(o['model'])}</div></div>"]


def footer():
    return [f"<div class='foot'><b>How to read this card.</b> Model = our prediction model's edge at the listed price. "
            f"System = a betting rule with a 15-season record. Situational = a game spot tested against 15 seasons of closing "
            f"lines. Stakes grow when independent signals agree (max 2u). 1 unit = {money(1)}. Lines move: check the price "
            f"before betting; if it moves past the listed number the edge can disappear. Past results don't guarantee future "
            f"results. For entertainment only · 21+ · 1-800-GAMBLER. Generated {datetime.now(ET):%b %-d, %Y %-I:%M %p ET}.</div>"]


def render_nfl():
    S, F = W.Sport("nfl"), load_final("nfl")
    plays = [p for p in F["plays"] if S.upcoming(p["game"])]
    best = [p for p in plays if p["units"] >= 1]
    rest = [p for p in plays if p["units"] < 1]
    totals = [p for p in rest if p["market"] == "total"]
    sides = [p for p in rest if p["market"] != "total"]
    risk = sum(p["units"] for p in plays)
    h = hero(S, "nfl", f"NFL · Week {S.week} · {date_range(S)}", "Sunday <span>Card</span>",
             [(len(plays), "Plays"), (f"{risk:g}u", "Units"), (money(risk), "Risked")])
    h += ["<h2>Best Bets</h2>", "<div class='note'>1 unit or more: a 3%+ model edge, or two independent signals stacked.</div>"]
    h += [play_card(S, p) for p in best] or ["<p class='empty'>No best bets this week.</p>"]
    h += ["<h2>Totals</h2>", "<div class='note'>Weather-driven unders and model totals.</div>"]
    h += [play_card(S, p) for p in totals] or ["<p class='empty'>No total plays.</p>"]
    h += ["<h2>Sides</h2>", "<div class='note'>Spread or moneyline, one per team: situational spots and road-team systems, "
          "half units unless stacked.</div>"]
    h += [play_card(S, p) for p in sides] or ["<p class='empty'>No side plays.</p>"]
    h += ["<h2>QB Watch · Injury Report</h2>", "<div class='note'>Starters on the injury report or already replaced. "
          "<b>Avoid</b>: don't bet on that team. <b>Bet against</b>: the line hasn't caught up to the drop-off.</div>"]
    qb = W.nfl_qb_watch(S)
    h += qb_block(qb)
    avoid = {x["team"] for x in qb if x["cls"] in ("avoid", "watch")}
    h += ["<h2>Price Watch &amp; Model Leans</h2>", "<div class='note'>Real signals at the wrong price, and the model's "
          "strongest opinions that aren't bets yet.</div>"] + leans_table(S, F, avoid)
    h += ["<h2>Streaks &amp; Trends</h2>", "<div class='note'>Active streaks among this week's teams, back into last season. "
          "Context only: streaks by themselves didn't predict the next game in our tests.</div>"] + streak_block(W.streaks(S))
    h += oddball_block(S, "nfl") + footer()
    return S, h


def blowout_board(S, blow):
    h = ["<div class='sb'><div class='sb-head'><div></div><div></div><div>Matchup</div><div>Dog pts</div>"
         "<div>Why this one</div><div style='text-align:right'>Play</div></div>"]
    for p in blow:
        b = S.board.get(p["game"], {})
        spread = abs(float(b["market_spread"].split()[-1]))
        total = float(p["bet"].split()[-1])
        dog_pts = (total - spread) / 2
        dog, fav = p["game"].split(" @ ")
        if b["market_spread"].split()[0] == dog:  # rare: home team is the underdog
            dog, fav = fav, dog
        c1, c2 = team_colors(S, p["game"])
        _r, info, _d = S.teams(p["game"])
        dog_abbr = (info["away"]["abbr"] if dog == p["game"].split(" @ ")[0] else info["home"]["abbr"]) if info else dog[:10]
        bucket = "40+ pt spreads: overs +10% ROI since 2010" if spread > 40 else "30–40 pt spreads: overs +6% ROI since 2010"
        agree = " Our model's total is above the line too." if p["model_agrees"] else ""
        h.append(f"<div class='sb-row' style='--c1:{c1};--c2:{c2}'><div class='stripe'></div><div>{S.logos(p['game'], 22)}</div>"
                 f"<div class='game'><b>{W.matchup(S, p['game'])}</b><span class='meta'>{S.when(p['game'])}</span></div>"
                 f"<div class='dog'><b>{dog_pts:.0f}</b><span>{E(dog_abbr)}</span></div>"
                 f"<div class='sbwhy'>{E(fav)} by {spread:g} with a {total:g} total: the market has {E(dog)} scoring only "
                 f"<b>~{dog_pts:.0f}</b>. {bucket}. Model total {b.get('model_total')}.{agree}"
                 f"<div class='spreadbar'><i style='width:{min(100, spread / 60 * 100):.0f}%'></i></div></div>"
                 f"<div class='sbbet'><b>{E(p['bet'])}</b>{W.fmt_odds(p['odds'])} · {E(p['book'])}"
                 f"<div><span class='usd'>{p['units']:g}u · {money(p['units'])}</span></div></div></div>")
    h.append("</div>")
    return h


def weather_desk(S, plays):
    h = ["<div class='wx'>"]
    for p in plays:
        r = S.rows.get(p["game"])
        c1, c2 = team_colors(S, p["game"])
        wind = float(r.wind8) if r is not None and pd.notna(r.wind8) else 0.0
        wet = int(r.wet8) if r is not None and pd.notna(r.wet8) else 0
        reason = W.system_reason(S, {"name": next(x for x in WEATHER if x in p["signals"]), "why": ""}, p)
        extra = [x for x in p["signals"] if x not in WEATHER]
        stack = f" <b>Also:</b> {E(', '.join(extra))}." if extra else ""
        h.append(f"<div class='wx-row' style='--c1:{c1};--c2:{c2}'><div class='stripe'></div><div>{S.logos(p['game'], 22)}</div>"
                 f"<div class='game'><b>{W.matchup(S, p['game'])}</b><span class='meta'>{S.when(p['game'])}</span></div>"
                 f"<div class='tiles'><div class='tile wind{' hot' if wind >= 15 else ''}'><b>{wind:.0f}</b><span>mph wind</span></div>"
                 f"<div class='tile rain{' hot' if wet >= 3 else ''}'><b>{wet}/8</b><span>wet hrs</span></div></div>"
                 f"<div class='sbwhy'>{reason}{stack}<div class='windbar'><i style='width:{min(100, wind / 30 * 100):.0f}%'></i></div></div>"
                 f"<div class='sbbet'><b>{E(p['bet'])}</b>{W.fmt_odds(p['odds'])} · {E(p['book'])}"
                 f"<div><span class='usd'>{p['units']:g}u · {money(p['units'])}</span></div></div></div>")
    h.append("</div>")
    return h


LAB_ORDER = ["Weather", "Blowout", "Trend", "Rankings", "Records", "Head-to-head", "Matchup", "Underdog", "Big dog",
             "Stats-only", "Season phase", "Edge"]
LAB_BLURB = {"Weather": "wind, rain, cold", "Blowout": "30+ pt spreads", "Trend": "ATS & over streaks",
             "Rankings": "AP / CFP poll spots", "Records": "W-L, streaks, bowl math", "Head-to-head": "revenge, rivalries",
             "Matchup": "unit vs unit, pace", "Underdog": "conference & road dogs", "Big dog": "21+ pt dogs",
             "Stats-only": "offense/defense numbers only", "Season phase": "early, mid-season, November",
             "Edge": "our model vs the line"}


def lab_board(S):
    """Every tested system by category: the ones that passed in full, the benched ones as a one-line list."""
    path = os.path.join(BET, "data", "cfb", "lab.json")
    if not os.path.exists(path):
        return []
    lab = json.load(open(path))
    cats = {}
    for x in lab:
        cats.setdefault(x["category"], []).append(x)
    h = ["<div class='lab'>"]
    for cat in [c for c in LAB_ORDER if c in cats] + [c for c in cats if c not in LAB_ORDER]:
        xs = cats[cat]
        good = [x for x in xs if x["grade"]]
        bench = [x for x in xs if not x["grade"]]
        h.append(f"<div class='labcat'><h4>{E(cat)}<small>{len(xs)} tested · {E(LAB_BLURB.get(cat, ''))}</small></h4>")
        if good:
            h.append("<div class='labhead'><span>System</span><span>ROI</span><span>Wk 5–9</span><span>Verdict</span></div>")
        for x in good:
            if x["on_card"]:
                v, cls = f"On card · {x['grade']}", "on"
            elif "kickoff" in x["name"] or "12+" in x["name"]:
                v, cls = "Steady version used", "alt"
            else:
                v, cls = f"Passed · {x['grade']}", "alt"
            live = f" · this week: {len(x['live'])}" if x["on_card"] and x["live"] else ""
            since = "2014" if cat == "Edge" else "2011"
            mid = x["mid"]
            h.append(f"<div class='labrow'><div class='nm'>{E(x['name'])}<i>{x['record']} since {since}{live}</i></div>"
                     f"<div class='n {'pos' if x['roi'] > 0 else 'neg'}'>{x['roi']:+.1f}%</div>"
                     f"<div class='n {'pos' if mid['roi%'] > 0 else 'neg'}'>{(format(mid['roi%'], '+.1f') + '%') if mid['bets'] else '—'}</div>"
                     f"<div class='verdict {cls}'>{E(v)}</div></div>")
        if bench:
            items = " · ".join(f"{E(x['name'])} <span class='{'pos' if x['roi'] > 0 else 'neg'}'>{x['roi']:+.1f}%</span>"
                               + (" (too few bets)" if x["bets"] < 100 else "") for x in bench)
            h.append(f"<div class='bench'><b>{'Benched' if good else 'All benched'}</b>{items}</div>")
        h.append("</div>")
    h.append("</div>")
    return h


def lab_count():
    path = os.path.join(BET, "data", "cfb", "lab.json")
    return len(json.load(open(path))) if os.path.exists(path) else 0


def top25_watch(S, F):
    """This week's games with a ranked team: records, poll vs betting-market rank, streaks, last meeting."""
    games = [(g, r) for g, r in S.rows.items() if pd.notna(getattr(r, "h_rank", np.nan)) or pd.notna(getattr(r, "a_rank", np.nan))]
    if not games:
        return ["<p class='empty'>No ranked teams on the board this week.</p>"]
    games.sort(key=lambda x: min(v for v in (x[1].h_rank, x[1].a_rank) if pd.notna(v)))
    ours = {}
    for p in F["plays"]:
        ours.setdefault(p["game"], []).append(f"{p['bet']} · {p['units']:g}u")
    h = ["<table class='t25'><tr><th style='width:72px'></th><th style='width:25%'>Matchup</th><th style='width:10%'>Line</th>"
         "<th style='width:24%'>Poll vs market rank</th><th style='width:21%'>Streaks · last meeting</th><th style='width:13%'>Our play</th></tr>"]
    for g, r in games:
        b = S.board.get(g, {})
        gaps = []
        for s, name in (("a", r.away), ("h", r.home)):
            rank, mrank = getattr(r, f"{s}_rank"), getattr(r, f"{s}_mkt_rank")
            if pd.isna(rank) or pd.isna(mrank):
                continue
            d = int(mrank) - int(rank)
            cls, txt = ("hi", f"poll higher by {d}") if d >= 8 else ("lo", f"market higher by {-d}") if d <= -8 else ("ok", "agree")
            gaps.append(f"<div>{E(name)} #{int(rank)} · market #{int(mrank)} <span class='gap {cls}'>{txt}</span></div>")
        streaks = []
        for s, name in (("a", r.away), ("h", r.home)):
            k = int(getattr(r, f"{s}_streak"))
            if abs(k) >= 2:
                streaks.append(f"{E(name)} {'W' if k > 0 else 'L'}{abs(k)}")
        form = [" · ".join(streaks)] if streaks else []
        if pd.notna(r.h2h_ago):
            m, ago = r.h2h_margin, int(r.h2h_ago)
            who = r.home if m > 0 else r.away
            form.append(f"<span class='meta'>Last met {int(r.season) - ago}: {E(who)} by {abs(m):g}</span>")
        line = f"{E(b.get('market_spread', ''))}<div class='meta'>O/U {E(str(b.get('market_total', '')))}</div>"
        play = "<br>".join(E(x) for x in ours.get(g, [])) or "<span class='meta'>—</span>"
        h.append(f"<tr><td class='lgc'>{S.logos(g, 18)}</td><td class='n'>{W.matchup(S, g)}"
                 f"<div class='meta'>{S.when(g)}</div></td><td class='n'>{line}</td><td>{''.join(gaps)}</td>"
                 f"<td>{'<br>'.join(form) or '—'}</td><td class='b'>{play}</td></tr>")
    h.append("</table>")
    return h


def render_cfb():
    S, F = W.Sport("cfb"), load_final("cfb")
    plays = [p for p in F["plays"] if S.upcoming(p["game"])]
    blow = sorted([p for p in plays if "Blowout over" in p["signals"]], key=lambda p: S.teams(p["game"])[2] or "")
    wx = [p for p in plays if p not in blow and any(x in p["signals"] for x in WEATHER)]
    other = [p for p in plays if p not in blow and p not in wx]
    sy = next((x for x in S.card.get("systems", []) if x["name"] == "Blowout over"), None)
    risk = sum(p["units"] for p in plays)
    h = hero(S, "cfb", f"College Football · Week {S.week} · {date_range(S)}", "Saturday Slate",
             [(len(plays), "Plays"), (f"{risk:g}u", "Units"), (money(risk), "Risked")])
    h += ["<h2>Blowout Overs</h2>"]
    if sy:
        h.append(f"<div class='intro'><h3>{len(blow)} play{'' if len(blow) == 1 else 's'} · {sum(p['units'] for p in blow):g}u · "
                 f"{money(sum(p['units'] for p in blow))}</h3><div>{W.SYSTEM_COPY['Blowout over'][1]}</div>"
                 f"<div class='rec'>{W.record_line(sy)}</div></div>")
    h += blowout_board(S, blow) if blow else ["<p class='empty'>No blowout games at a playable price.</p>"]
    h += ["<h2>Weather Desk</h2>", "<div class='note'>Outdoor games with steady 15+ mph wind or rain in 3+ of the 8 hours "
          "around kickoff (hourly forecast). Two weather systems on one game stack to a bigger stake.</div>"]
    h += weather_desk(S, wx) if wx else ["<p class='empty'>No steady wind or rain games at a playable price this week.</p>"]
    h += ["<h2>Other Plays</h2>", "<div class='note'>Model edges, trend fades and situational spots.</div>"]
    h += [play_card(S, p) for p in other] or [
        "<p class='empty'>Nothing else cleared the bar this week. The strongest near-misses are below.</p>"]
    h += ["<h2>Top 25 Watch</h2>", "<div class='note'>Ranks at kickoff (AP, or CFP once it's out), records going in, and "
          "where the betting market ranks each team. Context, not bets: every rank, record and poll-vs-market system we "
          "tested lost money against the closing line (Systems Lab below).</div>"]
    h += top25_watch(S, F)
    ours = {p["game"]: p["bet"] for p in plays}
    h += ["<h2>QB Changes</h2>", "<div class='note'>Teams whose passer changed last game (from play-by-play; college injury "
          "reports aren't public). Confirm the starter before betting either side.</div>"]
    h += qb_block(W.cfb_qb_watch(S, ours))
    h += ["<h2>Model Leans &amp; Price Watch</h2>", "<div class='note'>The model's strongest opinions that aren't bets, and "
          "real signals at the wrong price.</div>"] + leans_table(S, F)
    h += ["<h2>Streaks &amp; Trends</h2>", "<div class='note'>Active streaks among this week's teams, back into last season. "
          "Context only.</div>"] + streak_block(W.streaks(S))
    h += ["<h2>Systems Lab</h2>", f"<div class='note'>All {lab_count()} college systems we tested, graded on 2011–2026 closing "
          "lines at −110. Only the ones that held up make the card; the rest are listed so you know they were checked.</div>"]
    h += lab_board(S)
    h += oddball_block(S, "cfb") + footer()
    return S, h


def write(sport):
    ensure_fonts()
    S, h = render_nfl() if sport == "nfl" else render_cfb()
    page = "<!doctype html><html><head><meta charset='utf-8'></head><body>" + "".join(h) + "</body></html>"
    html_path = os.path.join(HERE, f"{sport}_week{S.week}.html")
    pdf_path = os.path.join(HERE, f"{sport}_week{S.week}.pdf")
    with open(html_path, "w") as f:
        f.write(page)
    subprocess.run([W.CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf_path}", "file://" + html_path], check=True, capture_output=True, timeout=120)
    os.remove(html_path)
    print(pdf_path)


if __name__ == "__main__":
    for sp in (sys.argv[1:] or ["nfl", "cfb"]):
        write(sp)
