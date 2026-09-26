#!/usr/bin/env python3
"""Final shareable cards, one layout per sport, built from the decision layer (betting/final.py).

NFL card      Best Bets · Totals (weather + model) · Sides (situational + road-team systems) · QB Watch (injuries:
              avoid / bet against) · Price Watch & Model Leans · Streaks · Oddball
College card  Blowout Overs (headline) · Other Plays (model + situational) · QB Changes · Model Leans · Streaks · Oddball

Every play carries a "Why": a game-specific lead with the real numbers, then each supporting signal with its record.

Usage: python3 betting/final.py && python3 betting/share/cards.py [nfl|cfb]
"""
import json
import os
import subprocess
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
BET = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, BET)
import weekly as W  # noqa: E402

E, ET = W.E, W.ET
EXTRA_CSS = """
.wl { margin:6px 0 0; padding:0; list-style:none; }
.wl li { position:relative; padding-left:12px; margin:3px 0; color:var(--ink2); }
.wl li::before { content:''; position:absolute; left:0; top:.62em; width:5px; height:5px; border-radius:50%; background:var(--accent); opacity:.55; }
.wl b.l { color:var(--ink); }
.chips { margin-top:4px; }
.chip { display:inline-block; font-size:7pt; font-weight:650; letter-spacing:.05em; text-transform:uppercase; border-radius:999px;
        padding:2px 8px; margin:0 4px 2px 0; background:var(--soft); color:var(--ink2); }
.chip.model { background:var(--greenbg); color:var(--green); }
.chip.sys { background:#eef3fd; color:var(--blue); }
.chip.ang { background:var(--amberbg); color:var(--amber); }
.book { color:var(--mute); font-size:8pt; font-weight:500; margin-left:6px; }
"""
SYSTEMS = {"Blowout over", "Wind under", "Close road team", "Close road team ML", "Buy-low underdog", "Rested home team"}


def load_final(sport):
    p = os.path.join(BET, "data", "final_nfl.json") if sport == "nfl" else os.path.join(BET, "data", "cfb", "final_cfb.json")
    return json.load(open(p))


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
    for name in ("Wind under", "Blowout over", "Close road team", "Close road team ML"):
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
            continue  # already in the lead
        items.append(f"<li><b class='l'>{E(b['title'])}:</b> {E(b['text'])}</li>")
    return "<ul class='wl'>" + "".join(items) + "</ul>"


def play_card(S, p):
    return (f"<div class='bet'><div class='lg'>{S.logos(p['game'])}</div>"
            f"<div><div class='pick'>{E(p['bet'])}<span class='odds'>{W.fmt_odds(p['odds'])}</span>"
            f"<span class='book'>{E(p['book'])}</span></div>"
            f"<div class='meta'>{E(p['game'])} · {S.when(p['game'])}</div>{chips(p)}</div>"
            f"<div class='right'><span class='u'>{p['units']:g}u</span><span class='tag'>{E(p['tier'])}</span></div>"
            f"<div class='why'>{why_block(S, p)}</div></div>")


def hero(S, label, accent, kpis):
    dates = sorted(d for d in (S.teams(g)[2] for g in S.rows) if d)
    rng = ""
    if dates:
        d0 = datetime.fromisoformat(dates[0].replace("Z", "+00:00")).astimezone(ET)
        d1 = datetime.fromisoformat(dates[-1].replace("Z", "+00:00")).astimezone(ET)
        rng = d0.strftime("%b %-d") + ("" if d0.date() == d1.date() else "–" + d1.strftime("%-d" if d0.month == d1.month else "%b %-d")) + d1.strftime(", %Y")
    books = "FanDuel / DraftKings" if os.path.exists(os.path.join(BET, "odds_api_key.txt")) or os.environ.get("ODDS_API_KEY") else "DraftKings"
    h = [f"<style>{W.CSS % {'accent': accent}}{EXTRA_CSS}</style><div class='hero'><div>",
         f"<div class='eyebrow'>{label} · Week {S.week} · {rng}</div><h1>Betting Card</h1>",
         f"<div class='sub'>Prices: {books} · 1 unit = 1% of bankroll</div></div><div class='kpis'>"]
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
    ms = b.get("market_spread", "")  # e.g. "WAS +7.5" (home team's line)
    try:
        home_line = float(ms.split()[-1])
        return f"{team} {(home_line if l['side'] == 'home' else -home_line):+g}"
    except (ValueError, IndexError):
        return team


def leans_table(S, F, avoid=()):
    rows, seen = [], set()
    for l in F["leans"]:
        if "model agrees" in l["note"]:
            continue  # conditional angles the model disagrees with: not worth listing
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
        h.append(f"<tr><td class='lgc'>{S.logos(g, 18)}</td><td class='n'>{E(g)}</td><td class='b'>{E(what)}</td><td>{why}</td></tr>")
    h.append("</table>")
    return h


def qb_block(qb, sport):
    h = []
    if not qb:
        return ["<p class='empty'>No starting-QB issues on this slate.</p>"]
    for x in qb:
        nxt = f" · next up: {E(x['backup'])}" if x.get("backup") and x["status"] not in ("QB change", "New starter") else ""
        h.append(f"<div class='panel qb'><div>{x['logo']}</div><div><span class='name'>{E(x['qb'])}</span>"
                 f"<span class='pill status'>{E(x['status'])}</span>"
                 f"<div class='meta'>{E(x['team'])} · {E(x['game'])} · {E(x['detail'])}{nxt}</div>"
                 f"<div style='margin-top:4px;color:var(--ink2)'>{x['why']}</div></div>"
                 f"<div><span class='pill {x['cls']}'>{E(x['verdict'])}</span></div></div>")
    return h


def streak_block(st):
    titles = {"win": "Winning streaks", "loss": "Losing streaks", "ats": "Against the spread", "ou": "Over / Under"}
    h = ["<div class='grid2'>"]
    for c, title in titles.items():
        h.append(f"<div class='mini'><h4>{title}</h4><table>")
        for x in st[c]:
            ln = f" ({x['line']:+g})" if x["line"] is not None and c in ("win", "loss", "ats") else ""
            k = "hot" if x["tag"].startswith(("W", "Covered")) else "cold" if x["tag"].startswith(("L", "Failed")) else "neu"
            h.append(f"<tr><td class='sk {k}' style='width:70px'>{E(x['tag'])}</td><td><b>{E(str(x['team']))}</b>"
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
            f"<div class='odd'><div style='display:flex;gap:10px;align-items:center'>{S.logos(o['game'], 30)}"
            f"<div><div class='t'>{E(o['title'])}</div><div class='meta'>{E(o['sub'])}</div></div></div>"
            f"<div style='margin-top:8px'>{E(o['body'])}</div>"
            f"<div class='fact'><b class='k'>Did you know</b>{E(o['fact'])}</div>"
            f"<div class='meta' style='margin-top:8px'>{E(o['model'])}</div></div>"]


def footer():
    return [f"<div class='foot'><b>How to read this card.</b> Model = our prediction model's edge at the listed price. "
            f"System = a betting rule with a 15-season record. Situational = a game spot tested against 15 seasons of closing "
            f"lines. Stakes grow when independent signals agree (max 2u). Lines move: check the price before betting; if it "
            f"moves past the listed number the edge can disappear. Past results don't guarantee future results. "
            f"For entertainment only · 21+ · 1-800-GAMBLER. Generated {datetime.now(ET):%b %-d, %Y %-I:%M %p ET}.</div>"]


def render_nfl():
    S, F = W.Sport("nfl"), load_final("nfl")
    plays = [p for p in F["plays"] if S.upcoming(p["game"])]
    best = [p for p in plays if p["units"] >= 1]
    rest = [p for p in plays if p["units"] < 1]
    totals = [p for p in rest if p["market"] == "total"]
    sides = [p for p in rest if p["market"] != "total"]
    agree = sum(1 for p in plays if p["model_agrees"] or "Model" in p["signals"])
    h = hero(S, "NFL", "#0b1f3a", [(len(plays), "Plays"), (f"{sum(p['units'] for p in plays):g}u", "Risked"),
                                    (f"{agree}/{len(plays)}", "Model on same side")])
    h += ["<h2>Best Bets</h2>", "<div class='note'>1 unit or more: a 3%+ model edge, or two independent signals stacked.</div>"]
    h += [play_card(S, p) for p in best] or ["<p class='empty'>No best bets this week.</p>"]
    h += ["<h2>Totals</h2>", "<div class='note'>Weather-driven unders and model totals.</div>"]
    h += [play_card(S, p) for p in totals] or ["<p class='empty'>No total plays.</p>"]
    h += ["<h2>Sides</h2>", "<div class='note'>Spread or moneyline, one per team. Situational spots and road-team systems, "
          "half units unless stacked.</div>"]
    h += [play_card(S, p) for p in sides] or ["<p class='empty'>No side plays.</p>"]
    h += ["<h2>QB Watch</h2>", "<div class='note'>Starters on the injury report or already replaced. <b>Avoid</b>: don't bet "
          "on that team. <b>Bet against</b>: the line hasn't caught up to the drop-off.</div>"]
    qb = W.nfl_qb_watch(S)
    h += qb_block(qb, "nfl")
    avoid = {x["team"] for x in qb if x["cls"] in ("avoid", "watch")}
    h += ["<h2>Price Watch &amp; Model Leans</h2>", "<div class='note'>Real signals at the wrong price, and the model's "
          "strongest opinions that aren't bets yet.</div>"] + leans_table(S, F, avoid)
    h += ["<h2>Streaks &amp; Trends</h2>", "<div class='note'>Active streaks among this week's teams, back into last season. "
          "Context only: streaks by themselves didn't predict the next game in our tests.</div>"] + streak_block(W.streaks(S))
    h += oddball_block(S, "nfl") + footer()
    return S, h


def render_cfb():
    S, F = W.Sport("cfb"), load_final("cfb")
    plays = [p for p in F["plays"] if S.upcoming(p["game"])]
    blow = sorted([p for p in plays if "Blowout over" in p["signals"]], key=lambda p: S.teams(p["game"])[2] or "")
    other = [p for p in plays if p not in blow]
    sy = next((x for x in S.card.get("systems", []) if x["name"] == "Blowout over"), None)
    h = hero(S, "College Football", "#123b2c", [(len(plays), "Plays"), (f"{sum(p['units'] for p in plays):g}u", "Risked"),
                                                 (f"{sy['recent_roi%']:+.1f}%" if sy else "", "Blowout Over 25–26")])
    h += ["<h2>Blowout Overs</h2>"]
    if sy:
        h.append(f"<div class='panel green'><h3>Blowout Overs · {len(blow)} plays · {sum(p['units'] for p in blow):g}u</h3>"
                 f"<div>{W.SYSTEM_COPY['Blowout over'][1]}</div><div class='rec'>{W.record_line(sy)}</div></div>")
    if blow:
        h.append("<table><tr><th style='width:60px'></th><th>Play</th><th>Price</th><th>Game</th><th>Why this one</th></tr>")
        for p in blow:
            extra = " Our model's total is above the line too." if p["model_agrees"] else ""
            h.append(f"<tr><td class='lgc'>{S.logos(p['game'], 18)}</td><td class='b'>{E(p['bet'])}<div class='meta'>{p['units']:g}u</div></td>"
                     f"<td class='n'>{W.fmt_odds(p['odds'])}<div class='meta'>{E(p['book'])}</div></td>"
                     f"<td class='n'>{E(p['game'])}<div class='meta'>{S.when(p['game'])}</div></td>"
                     f"<td>{W.system_reason(S, {'name': 'Blowout over', 'why': ''}, p)}{extra}</td></tr>")
        h.append("</table>")
    else:
        h.append("<p class='empty'>No blowout games at a playable price.</p>")
    h += ["<h2>Other Plays</h2>", "<div class='note'>Model edges and situational spots outside the Blowout Over system.</div>"]
    h += [play_card(S, p) for p in other] or [
        "<p class='empty'>Nothing outside the Blowout Overs cleared the bar this week: no 3%+ model edges, and the "
        "situational spots that tested well didn't come up at a playable price. The strongest near-misses are below.</p>"]
    ours = {p["game"]: p["bet"] for p in plays}
    h += ["<h2>QB Changes</h2>", "<div class='note'>Teams whose passer changed last game (from play-by-play; college injury "
          "reports aren't public). Confirm the starter before betting either side.</div>"]
    h += qb_block(W.cfb_qb_watch(S, ours), "cfb")
    h += ["<h2>Model Leans &amp; Price Watch</h2>", "<div class='note'>The model's strongest opinions that aren't bets, and "
          "real signals at the wrong price.</div>"] + leans_table(S, F)
    h += ["<h2>Streaks &amp; Trends</h2>", "<div class='note'>Active streaks among this week's teams, back into last season. "
          "Context only.</div>"] + streak_block(W.streaks(S))
    h += oddball_block(S, "cfb") + footer()
    return S, h


def write(sport):
    W.ensure_font()
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
