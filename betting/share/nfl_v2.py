#!/usr/bin/env python3
"""NFL card v2: page 1 is the whole card on one sheet; the pages behind it carry the support.

  1  The Sheet      every bet sorted by kickoff (sides, totals, first halves, teasers, props) + the pass list
  2  Bet detail     each full-game bet with its signals, records and price; first-half bets; teasers
  3  Props          player props (needs FanDuel/DraftKings prop lines from the Odds API)
  4  Game by game   a trends panel for every game: records, ATS / over-under, splits, form, ranks, streaks, H2H
  5  QB Watch

Run after final.py, teasers.py, first_half.py (and props.py when an Odds API key is set).
Usage: python3 betting/share/nfl_v2.py  ->  betting/share/nfl_v2_week<N>.pdf
"""
import json
import os
import subprocess
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
BET = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, BET)
import cards as K  # noqa: E402
import trends as T  # noqa: E402
import weekly as W  # noqa: E402

E = W.E
DATA = os.path.join(BET, "data")

V2_CSS = """
.sheet { width:100%; border-collapse:collapse; font-size:8.6pt; }
.sheet th { font-size:6.6pt; letter-spacing:.1em; text-transform:uppercase; color:var(--mute); text-align:left;
            padding:6px 6px; border-bottom:1.5px solid var(--ink); }
.sheet td { padding:7px 6px; border-bottom:1px solid var(--line); vertical-align:middle; }
.sheet tr.win td { background:#f6fbf8; }
.sheet td:nth-child(3) { white-space:nowrap; }
.sheet .kick { font-variant-numeric:tabular-nums; color:var(--ink2); white-space:nowrap; font-size:8pt; }
.sheet .sbet { font-family:'Bebas Neue', Impact, sans-serif; font-size:13.5pt; letter-spacing:.02em; line-height:1.05; }
.sheet .odds { font-variant-numeric:tabular-nums; white-space:nowrap; }
.sheet .su { font-weight:800; white-space:nowrap; text-align:right; }
.sheet .su small { display:block; color:var(--green); font-weight:700; }
.sheet .sig { font-size:7.6pt; color:var(--ink2); min-width:130px; }
.tier { display:inline-block; font-size:6.4pt; font-weight:800; letter-spacing:.08em; text-transform:uppercase;
        border-radius:20px; padding:2px 7px; white-space:nowrap; }
.tier.best { background:var(--red); color:#fff; } .tier.play { background:var(--soft); color:var(--ink2); border:1px solid var(--line); }
.tier.h1 { background:#eef2ff; color:var(--blue); } .tier.tz { background:var(--amberbg); color:var(--amber); }
.tier.prop { background:var(--greenbg); color:var(--green); }
.tier.sharp { background:#0e1320; color:#f5d77a; }
.wx-t { width:100%; border-collapse:collapse; font-size:8pt; }
.wx-t td, .wx-t th { padding:5px 6px; border-bottom:1px solid var(--line); text-align:left; font-variant-numeric:tabular-nums; }
.wx-t th { font-size:6.6pt; letter-spacing:.1em; text-transform:uppercase; color:var(--mute); }
.wx-t .hot { color:var(--red); font-weight:800; }
.group td { background:var(--soft); font-size:6.8pt; font-weight:800; letter-spacing:.12em; text-transform:uppercase;
            color:var(--mute); padding:5px 6px; }
.passes { columns:2; column-gap:22px; font-size:7.8pt; color:var(--ink2); margin-top:6px; }
.passes div { break-inside:avoid; padding:3px 0; border-bottom:1px dotted var(--line); }
.passes b { color:var(--ink); }
.pagebreak { break-after:page; }
.gp { border:1px solid var(--line); border-radius:12px; padding:10px 12px; margin:0 0 10px; break-inside:avoid; background:#fff; }
.gp-h { display:flex; align-items:center; gap:10px; justify-content:space-between; flex-wrap:wrap; }
.gp-h .t { font-family:'Bebas Neue', Impact, sans-serif; font-size:15pt; letter-spacing:.02em; }
.gp-h .ln { font-size:7.8pt; color:var(--ink2); text-align:right; }
.gp table { width:100%; border-collapse:collapse; font-size:7.8pt; margin-top:6px; }
.gp td, .gp th { padding:3px 6px; border-bottom:1px solid var(--line); text-align:center; font-variant-numeric:tabular-nums; }
.gp th { font-size:6.4pt; letter-spacing:.08em; text-transform:uppercase; color:var(--mute); }
.gp td:first-child, .gp th:first-child { text-align:left; color:var(--mute); width:30%; }
.form { letter-spacing:.12em; font-weight:700; }
.form .W { color:var(--green); } .form .L { color:var(--red); } .form .P { color:var(--mute); }
.gp .foot { display:flex; flex-wrap:wrap; gap:6px; margin-top:6px; font-size:7.4pt; color:var(--ink2); }
.gp .chip2 { background:var(--soft); border-radius:12px; padding:2px 8px; }
.gp .ours { background:var(--greenbg); color:var(--green); font-weight:700; border-radius:12px; padding:2px 8px; }
.gp .lean { background:var(--amberbg); color:var(--amber); border-radius:12px; padding:2px 8px; }
"""


def game_of(gid):
    p = gid.split("_")
    return f"{p[2]} @ {p[3]}"


def form(s):
    return "<span class='form'>" + "".join(f"<span class='{c}'>{c}</span>" for c in s) + "</span>"


def sheet_rows(S, F):
    """Every bet on the card, one row each, with kickoff for sorting."""
    rows = []
    for p in F["plays"]:
        if not S.upcoming(p["game"]):
            continue
        tier = ("best", "Best Bet") if p["units"] >= 1 else ("play", "Play")
        rows.append({"game": p["game"], "bet": p["bet"], "odds": W.fmt_odds(p["odds"]), "book": p["book"], "u": p["units"],
                     "sig": " + ".join(p["signals"]) + (" · model agrees" if p.get("model_agrees") and "Model" not in p["signals"] else ""),
                     "tier": tier})
    fh = json.load(open(os.path.join(DATA, "first_half.json"))) if os.path.exists(os.path.join(DATA, "first_half.json")) else {}
    for p in fh.get("live", []):
        g = game_of(p["game_id"])
        if S.upcoming(g) and not p.get("cut"):
            real = "odds_real" in p
            rows.append({"game": g, "bet": p["bet"], "odds": W.fmt_odds(p["odds_real"]) if real else "−110 est.",
                         "book": p["book_real"] if real else "1H line", "u": p["units"],
                         "sig": f"{p['angle']} ({p['record']}, {p['roi']:+}%)" + (f" · Pinnacle {p['sharp']['win']:g}%" if p.get("sharp") else ""),
                         "tier": ("h1", "1st Half")})
    mk = json.load(open(os.path.join(DATA, "market_nfl.json"))) if os.path.exists(os.path.join(DATA, "market_nfl.json")) else {}
    abbr = __import__("fetch").NAMES  # full team name -> abbreviation
    for e in mk.get("edges", []) + mk.get("derivatives", []):
        g = f"{abbr.get(e['away'], e['away'])} @ {abbr.get(e['home'], e['home'])}"
        if not S.upcoming(g):
            continue
        if e["market"] == "h2h":
            bet = f"{abbr.get(e['side'], e['side'])} ML"
        elif e["market"] == "spreads":
            bet = f"{abbr.get(e['side'], e['side'])} {e['point']:+g}"
        elif e["market"] == "totals":
            bet = f"{e['side']} {e['point']:g}"
        elif e["market"] == "team_totals":
            bet = f"{abbr.get(e['team'], e['team'])} team total {e['side']} {e['point']:g}"
        else:
            bet = f"1H {abbr.get(e['side'], e['side'])} {e['point']:+g}" if e["market"] == "spreads_h1" else f"1H {e['side']} {e['point']:g}"
        rows.append({"game": g, "bet": bet, "odds": W.fmt_odds(e["odds"]), "book": e["book"], "u": e["units"],
                     "sig": f"price beats Pinnacle (fair {e['fair_odds']:+d}) · EV {e['ev']:+.1f}%", "tier": ("sharp", "Sharp price")})
    tz = json.load(open(os.path.join(DATA, "teasers.json"))) if os.path.exists(os.path.join(DATA, "teasers.json")) else {}
    for pr in tz.get("pairs", []):
        rows.append({"game": pr["games"][0], "bet": " / ".join(pr["legs"]), "odds": "2-team 6-pt", "book": "−130 or better",
                     "u": pr["units"], "sig": "Wong teaser", "tier": ("tz", "Teaser")})
    pp = os.path.join(DATA, "props.json")
    if os.path.exists(pp):
        P = json.load(open(pp))
        for p in P.get("picks", []) + P.get("sharp", []):
            g = game_of(p["game_id"])
            if S.upcoming(g) and P.get("week") == S.week:
                sharp = p in P.get("sharp", [])
                rows.append({"game": g, "bet": f"{p['player']} {p['side'].title()} {p['line']:g} {p['label']}",
                             "odds": W.fmt_odds(p["odds"]), "book": p["book"], "u": p["units"],
                             "sig": (f"price beats Pinnacle ({p['book_prob']:g}%) · EV {p['ev_sharp']:+.1f}%" if sharp else
                                     f"proj {p['proj']:g} · {p['side']} in {p['hits']}/{p['n']}"
                                     + (f" · vs Pinnacle {p['ev_sharp']:+.1f}%" if p.get("ev_sharp") is not None
                                        and p["ev_sharp"] == p["ev_sharp"] else "")),
                             "tier": ("sharp", "Prop · price") if sharp else ("prop", "Prop")})
    for r in rows:
        r["date"] = S.teams(r["game"])[2] or ""
    return sorted(rows, key=lambda r: (r["date"], r["game"]))


def pass_list(S, F, bet_games):
    lean = {}
    for l in F.get("leans", []):
        lean.setdefault(l["game"], f"{l['why'].split(':')[0]}: {l['note']}")
    for m in F.get("model_leans", []):
        lean.setdefault(m["game"], f"model lean {m['bet']} ({m['ev']:+.1f}%), not enough")
    out = []
    for g in S.rows:
        if g in bet_games:
            continue
        b = S.board.get(g, {})
        why = lean.get(g) or f"market {b.get('market_spread', '?')}, fair {b.get('fair_spread', '?')}; total {b.get('market_total')} vs {b.get('fair_total')}"
        out.append((S.teams(g)[2] or "", g, why))
    return [f"<div><b>{W.matchup(S, g)}</b> · {S.when(g)}<br>{E(w)}</div>" for _d, g, w in sorted(out)]


def panel(S, g, tr, ours, leans):
    b = S.board.get(g, {})
    a, h = tr["away"], tr["home"]
    def row(label, ka, kh, fmt=lambda v: E(str(v))):
        return f"<tr><td>{label}</td><td>{fmt(a[ka])}</td><td>{fmt(h[kh])}</td></tr>"
    rk = lambda v: f"#{v}" if v else "—"  # noqa: E731
    body = (row("Record", "record", "record") + row("ATS", "ats", "ats") + row("Over-under", "ou", "ou")
            + row("Last 5 ATS", "last5", "last5", form) + row("This spot", "spot", "spot") + row("This role", "role", "role")
            + f"<tr><td>Pts for / against, last 3</td><td>{a['pf3']} / {a['pa3']}</td><td>{h['pf3']} / {h['pa3']}</td></tr>"
            + f"<tr><td>Offense / defense rank</td><td>{rk(a['off_rank'])} / {rk(a['def_rank'])}</td>"
              f"<td>{rk(h['off_rank'])} / {rk(h['def_rank'])}</td></tr>")
    chips = [f"<span class='ours'>Our bet: {E(x)}</span>" for x in ours] + [f"<span class='lean'>{E(x)}</span>" for x in leans]
    for side in (a, h):
        chips += [f"<span class='chip2'>{E(side['team'])}: {E(s)}</span>" for s in side["streaks"]]
    if tr["h2h"]:
        chips.append("<span class='chip2'>H2H: " + " · ".join(f"{m['season']} {E(m['score'])}, {E(m['ats'])}" for m in tr["h2h"]) + "</span>")
    if not ours and not leans:
        chips.append("<span class='chip2'>No tested signal on this game</span>")
    return (f"<div class='gp'><div class='gp-h'><div style='display:flex;align-items:center;gap:8px'>{S.logos(g, 22)}"
            f"<span class='t'>{E(g)}</span><span class='meta'>{S.when(g)}</span></div>"
            f"<div class='ln'>Line {E(b.get('market_spread', ''))} · total {b.get('market_total', '')}<br>"
            f"Our fair {E(b.get('fair_spread', ''))} · {b.get('fair_total', '')}</div></div>"
            f"<table><tr><th></th><th>{E(a['team'])}</th><th>{E(h['team'])}</th></tr>{body}</table>"
            f"<div class='foot'>{''.join(chips)}</div></div>")


def first_half_block(S):
    path = os.path.join(DATA, "first_half.json")
    if not os.path.exists(path):
        return []
    fh = json.load(open(path))
    passed = {k: v for k, v in fh["angles"].items() if v["grade"]}
    h = [f"<div class='propnote'><b>How first-half bets qualify.</b> Free data has no archive of first-half lines, so each "
         f"season's 1H line is estimated from earlier seasons (about {float(fh['fits'][max(fh['fits'])][0]):.2f}× the game total, "
         f"{float(fh['fits'][max(fh['fits'])][1]):.2f}× the spread). Ten first-half ideas were tested at −110, each against "
         f"a stricter bar (t ≥ 2, profitable in 2012–18 and 2019+, not losing in 2025–26). Passed: "
         + " ".join(f"<b>{E(k)}</b>: {v['summary']['record']} ({v['summary']['roi%']:+}%), {v['summary']['recent_record']} in 2025–26."
                    for k, v in passed.items())
         + " A play needs the real FanDuel/DraftKings 1H number at or above our estimate and a price within 2% of "
           "Pinnacle's fair price. <b>0.5u.</b></div>"]
    live = [p for p in fh["live"] if S.upcoming(game_of(p["game_id"]))]
    plays = [p for p in live if not p.get("cut")]
    if not plays:
        h.append("<p class='empty'>No first-half bet qualifies this week.</p>")
    for p in plays:
        g = game_of(p["game_id"])
        c1, c2 = K.team_colors(S, g)
        real = "odds_real" in p
        price = f"{W.fmt_odds(p['odds_real'])} · {E(p['book_real'])}" if real else "est. line"
        sharp = (f"<li><b class='l'>Sharp check:</b> Pinnacle's 1H total is {E(p['sharp']['pin'])}, which makes this side "
                 f"{p['sharp']['win']:g}% at {p['bet'].split()[-1]} ({p['sharp']['ev']:+.1f}% at our price). Our estimate was "
                 f"{p['est']:g}; the real number is at or above it.</li>") if p.get("sharp") else ""
        h.append(f"<div class='slip' style='--c1:{c1};--c2:{c2}'><div class='stripe'></div><div class='main'>"
                 f"<div class='top'><div class='lg'>{S.logos(g, 26)}</div><div>"
                 f"<div class='pk'>{E(p['bet'])}<span class='odds'>{price}</span></div>"
                 f"<div class='meta'>{W.matchup(S, g)} · {S.when(g)}</div></div></div>"
                 f"<ul class='wl'><li><b class='l'>{E(p['angle'])}:</b> {E(p['why'])} Record {p['record']} since 2012 "
                 f"({p['roi']:+}%), {p['recent']} in 2025–26.</li>{sharp}</ul></div>"
                 f"<div class='stub'><div class='units'>{p['units']:g}U</div><div class='usd'>{K.money(p['units'])}</div>"
                 f"<div class='tier play'>1st Half</div></div></div>")
    cut = [p for p in live if p.get("cut")]
    if cut:
        h.append("<ul class='wl'>" + "".join(f"<li><b>{E(game_of(p['game_id']))} {E(p['bet'])}</b>: passed, {E(p['cut'])}.</li>"
                                             for p in cut) + "</ul>")
    return h


def sharp_block(S):
    """The sharp-market section: how prices are checked, the price edges found, and the derivative scan."""
    mk = json.load(open(os.path.join(DATA, "market_nfl.json"))) if os.path.exists(os.path.join(DATA, "market_nfl.json")) else {}
    P = json.load(open(os.path.join(DATA, "props.json"))) if os.path.exists(os.path.join(DATA, "props.json")) else {}
    h = ["<div class='propnote'><b>How the sharp check works.</b> Pinnacle takes the biggest bets at the lowest margins, so "
         "its prices with the margin removed are the best public read on the true odds. Every FanDuel and DraftKings price is "
         "checked against them; where the lines differ, half points are valued by how often games land exactly on each "
         "number (3, 7, 41, 44...). A price that pays more than the true odds is a <b>sharp price</b> bet, whichever side it "
         "is on. Every other bet on this card was checked too: a model-only bet the sharp market doesn't back gets cut, and "
         "a system bet is cut when the sharp market leans the other way or our price is 2%+ worse than the fair price.</div>"]
    n_edges = len(mk.get("edges", [])) + len(mk.get("derivatives", [])) + len(P.get("sharp", []) if P.get("week") == S.week else [])
    h.append(f"<p class='meta'>Scanned {mk.get('scanned', 0)} main-market prices across {mk.get('events', 0)} games "
             f"({mk.get('with_pinnacle', 0)} with Pinnacle), plus "
             + ("first-half and team-total markets and " if "derivatives" in mk else "")
             + "player props. "
             + (f"{n_edges} price edge{'s' if n_edges != 1 else ''} found; they're on the Sheet as Sharp price.</p>" if n_edges else
                "No price edges right now: FanDuel and DraftKings are sitting on Pinnacle's numbers. Edges mostly show up "
                "earlier in the week and right after news, so check again before kickoff.</p>"))
    # the card's own bets as final.py checked them (market.py runs before final.py, so its copy can be a run behind)
    fp = os.path.join(DATA, "final_nfl.json")
    fin = json.load(open(fp)) if os.path.exists(fp) else {}
    checks = [c for c in fin.get("plays", []) if c.get("sharp") and S.upcoming(c["game"])]
    cut = [c for c in fin.get("leans", []) if c.get("note", "").startswith("cut by the sharp check") and S.upcoming(c["game"])]
    if checks or cut:
        h.append("<ul class='wl'>"
                 + "".join(f"<li><b>{E(c['game'])} {E(c['bet'])}</b> {W.fmt_odds(c['odds'])} {E(c['book'])}: kept, "
                           f"{c['sharp']['ev']:+.1f}% against {E(c['sharp']['ref'])} (fair {W.fmt_odds(c['sharp']['fair_odds'])})</li>"
                           for c in checks)
                 + "".join(f"<li><b>{E(c['game'])}</b> {E(c['why'])} ({E(c['market'])}, {E(c['side'])}): "
                           f"{E(c['note'].replace('cut by the sharp check: ', 'cut, '))}</li>" for c in cut)
                 + "</ul>")
    return h


def weather_block(S):
    path = os.path.join(DATA, "weather.csv")
    if not os.path.exists(path):
        return []
    w = pd.read_csv(path)
    rows = []
    for g in sorted(S.rows, key=lambda x: (S.teams(x)[2] or "", x)):
        r = S.rows[g]
        x = w[w["game_id"] == r.game_id]
        if x.empty:
            continue
        x = x.iloc[0]
        flags = []
        if x["wind"] >= 12:
            flags.append("1H wind under spot (12+ mph): 45-34 since 2024, watch list")
        if x["precip"] >= 1:
            flags.append("rain at kickoff")
        if x["temp"] <= 32:
            flags.append("sub-freezing")
        rows.append(f"<tr><td>{W.matchup(S, g)}</td><td>{S.when(g)}</td><td class='{'hot' if x['wind'] >= 12 else ''}'>"
                    f"{x['wind']:.0f} mph</td><td>{x['temp']:.0f}°F</td><td>{x['precip']:.1f} mm</td>"
                    f"<td>{E('; '.join(flags)) or '—'}</td></tr>")
    note = ("<div class='note'>Kickoff forecasts for every outdoor game. Full-game wind unders were retired: they won 305-211 "
            "through 2023 but went 38-41 since 2024 as books started pricing wind in. First-half wind unders still hold "
            "(45-34 since 2024) but haven't cleared our bar overall, so they're a watch list, not a bet.</div>")
    hot = any("hot" in r for r in rows)
    wk = w[w["game_id"].isin([S.rows[g].game_id for g in S.rows])]
    top = wk.loc[wk["wind"].idxmax()] if len(wk) else None
    windiest = (f" (windiest: {E(game_of(top['game_id']))}, {top['wind']:.0f} mph)" if top is not None else "")
    wet = "" if (wk["precip"] >= 1).any() else " and no rain at kickoff"
    lead = "" if hot else f"<p class='empty'>No weather spot this week: no game forecast at 12+ mph{windiest}{wet}.</p>"
    return [note, lead, "<table class='wx-t'><tr><th>Game</th><th>Kickoff</th><th>Wind</th><th>Temp</th><th>Rain</th>"
            "<th>Spot</th></tr>"] + rows + ["</table>"]


def props_section(S):
    pp = os.path.join(DATA, "props.json")
    if os.path.exists(pp) and json.load(open(pp)).get("week") == S.week:
        return K.props_block(S)
    return ["<p class='empty'>Props need FanDuel/DraftKings prop lines, which come from the Odds API key. "
            "Add the key and rerun props.py, and this page fills in with yards, receptions and their game logs.</p>"]


def render():
    S, F = W.Sport("nfl"), K.load_final("nfl")
    rows = sheet_rows(S, F)
    risk = sum(r["u"] for r in rows)
    h = K.hero(S, "nfl", f"NFL · Week {S.week} · {K.date_range(S)}", "Sunday <span>Card</span>",
               [(len(rows), "Bets"), (f"{risk:g}u", "Units"), (K.money(risk), "Risked")])
    h.insert(0, f"<style>{V2_CSS}{K.PROP_CSS}</style>")
    # page 1: the sheet
    h += ["<h2>The Sheet</h2>", "<div class='note'>Every bet on the card, by kickoff. Details for each are on the pages "
          "behind this one.</div>",
          "<table class='sheet'><tr><th style='width:58px'>Kick</th><th style='width:60px'></th><th>Game</th><th>Bet</th>"
          "<th>Price</th><th>Signals</th><th style='text-align:right'>Units</th></tr>"]
    last_day = None
    for r in rows:
        day, _, kick = S.when(r["game"]).partition(" · ")
        if day != last_day:
            h.append(f"<tr class='group'><td colspan='7'>{E(day)}</td></tr>")
            last_day = day
        h.append(f"<tr><td class='kick'>{E(kick.replace(' ET', ''))}</td><td class='lgc'>{S.logos(r['game'], 18)}</td>"
                 f"<td>{W.matchup(S, r['game'])}</td><td><span class='sbet'>{E(r['bet'])}</span><br>"
                 f"<span class='tier {r['tier'][0]}'>{E(r['tier'][1])}</span></td>"
                 f"<td class='odds'>{E(r['odds'])}<div class='meta'>{E(r['book'])}</div></td>"
                 f"<td class='sig'>{E(r['sig'])}</td><td class='su'>{r['u']:g}u<small>{K.money(r['u'])}</small></td></tr>")
    if not rows:
        h.append("<tr><td colspan='7' class='empty'>No bets cleared the bar this week.</td></tr>")
    h.append("</table>")
    bet_games = {r["game"] for r in rows}
    h += ["<h3 style='margin-top:14px'>Passed</h3>", "<div class='passes'>"] + pass_list(S, F, bet_games) + ["</div>"]
    h.append("<div class='pagebreak'></div>")
    # page 2: support for each bet
    h += ["<h2>Bet Detail</h2>", "<div class='note'>Each full-game bet with every signal behind it, its record, and the "
          "price to beat.</div>"]
    plays = [p for p in F["plays"] if S.upcoming(p["game"])]
    h += [K.play_card(S, p) for p in plays] or ["<p class='empty'>No full-game bets this week.</p>"]
    h += ["<h2>Sharp Prices</h2>"] + sharp_block(S)
    h += ["<h2>First Half</h2>"] + first_half_block(S)
    h += ["<h2>Teasers</h2>"] + K.teaser_block(S)
    h += ["<h2>Player Props</h2>"] + props_section(S)
    h.append("<div class='pagebreak'></div>")
    # game by game
    h += ["<h2>Game by Game</h2>", "<div class='note'>Every game on the slate. Records and streaks are context: on their "
          "own they didn't predict the next game against the closing line in our tests.</div>"]
    g = pd.read_csv(os.path.join(DATA, "games.csv"), low_memory=False)
    up = g[(g["season"] == S.season) & (g["week"] == S.week)]
    panels = T.game_panels(up)
    ours = {}
    for r in rows:
        ours.setdefault(r["game"], []).append(f"{r['bet']} ({r['u']:g}u)")
    leans = {}
    for l in F.get("leans", []):
        leans.setdefault(l["game"], []).append(f"lean: {l['why'].split(':')[0]}")
    order = sorted(S.rows, key=lambda x: (S.teams(x)[2] or "", x))
    for gm in order:
        gid = next((k for k in panels if game_of(k) == gm), None)
        if gid:
            h.append(panel(S, gm, panels[gid], ours.get(gm, []), leans.get(gm, [])))
    h += ["<h2>Weather Spots</h2>"] + weather_block(S)
    h += ["<h2>QB Watch · Injury Report</h2>"] + K.qb_block(W.nfl_qb_watch(S))
    h += K.footer()
    return S, h


def write():
    K.ensure_fonts()
    S, h = render()
    page = "<!doctype html><html><head><meta charset='utf-8'></head><body>" + "".join(h) + "</body></html>"
    html_path = os.path.join(HERE, f"nfl_v2_week{S.week}.html")
    pdf_path = os.path.join(HERE, f"nfl_v2_week{S.week}.pdf")
    with open(html_path, "w") as f:
        f.write(page)
    subprocess.run([W.CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf_path}", "file://" + html_path], check=True, capture_output=True, timeout=120)
    os.remove(html_path)
    print(pdf_path)


if __name__ == "__main__":
    write()
