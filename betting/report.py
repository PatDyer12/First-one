"""Render betting/card.html from the model output (this week's card + backtest)."""
import html
import os
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
E = html.escape

CSS = """
:root{--bg:#f6f7f9;--card:#fff;--ink:#16181d;--mute:#6b7280;--line:#e5e7eb;--bet:#0f7b4f;--betbg:#e7f6ee;--lean:#8a6d00;--leanbg:#fdf6dc;--neg:#b42318}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#0f1115;--card:#171a21;--ink:#e8eaed;--mute:#9aa1ac;--line:#2a2f3a;--bet:#4ade80;--betbg:#12301f;--lean:#facc15;--leanbg:#2d2710;--neg:#f87171}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 -apple-system,system-ui,Segoe UI,Roboto,sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 48px}h1{font-size:24px;margin:0 0 4px}h2{font-size:17px;margin:28px 0 10px}
.sub{color:var(--mute);margin:0 0 16px}.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;overflow-x:auto}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}th,td{padding:7px 9px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}
th{font-size:12px;color:var(--mute);font-weight:600;text-transform:uppercase;letter-spacing:.03em}tr:last-child td{border-bottom:0}
.tag{display:inline-block;padding:2px 8px;border-radius:99px;font-size:12px;font-weight:700}.BET{background:var(--betbg);color:var(--bet)}.lean{background:var(--leanbg);color:var(--lean)}
.edge{font-weight:600}.neg{color:var(--neg)}.pos{color:var(--bet)}.note{color:var(--mute);font-size:13px;max-width:780px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}.stat{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px}
.stat b{display:block;font-size:20px}.stat span{color:var(--mute);font-size:12px}
"""


def table(rows, cols, fmt=None):
    fmt = fmt or {}
    head = "".join(f"<th>{E(label)}</th>" for label, _ in cols)
    body = ""
    for r in rows:
        cells = ""
        for _, key in cols:
            v = r.get(key, "")
            cells += f"<td>{fmt[key](v, r) if key in fmt else E(str(v))}</td>"
        body += f"<tr>{cells}</tr>"
    return f'<div class="card"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def write(out):
    wk = out.get("week") or {}
    bt = out.get("backtest") or {}
    parts = [f"<h1>NFL Betting Model</h1><p class='sub'>Updated {datetime.now():%b %d, %Y %H:%M}"
             + (f" · {wk['season']} Week {wk['week']}" if wk else "") + "</p>"]
    if wk:
        picks = wk["picks"]
        bets = [p for p in picks if p["tier"] == "BET"]
        parts.append(f"<h2>This week's card: {len(bets)} bet{'s' if len(bets) != 1 else ''}, "
                     f"{len(picks) - len(bets)} lean{'s' if len(picks) - len(bets) != 1 else ''}</h2>")
        if picks:
            parts.append(table(picks, [("", "tier"), ("Game", "game"), ("Book", "book"), ("Bet", "bet"), ("Odds", "odds"),
                                       ("Win %", "win%"), ("Push %", "push%"), ("Edge (EV)", "ev%"), ("Stake % bankroll", "stake%")],
                               {"tier": lambda v, r: f"<span class='tag {v}'>{v.upper()}</span>",
                                "odds": lambda v, r: f"{int(v):+d}",
                                "ev%": lambda v, r: f"<span class='edge pos'>+{v}%</span>"}))
        else:
            parts.append("<p class='note'>Nothing clears even the 1% lean bar. The market and the model agree everywhere, "
                         "which happens most weeks against sharp lines.</p>")
        parts.append(f"<p class='note'>BET = expected value of at least 3% at the listed odds. Stake = quarter-Kelly, capped at 3% of bankroll. "
                     f"Lean = 1–3%, too thin to bet, but worth tracking. The model's weight vs the market: spread "
                     f"{wk['w_spread']:.0%}, total {wk['w_total']:.0%}.</p>")
        parts.append("<h2>Fair lines, every game</h2>")
        parts.append(table(wk["board"], [("Game", "game"), ("QBs (away / home)", "qbs"), ("Market", "market_spread"),
                                         ("Model only", "model_spread"), ("Fair", "fair_spread"), ("Mkt total", "market_total"),
                                         ("Model total", "model_total"), ("Fair total", "fair_total"), ("Home win %", "home_win%"),
                                         ("Fair ML", "fair_ml")]))
    tr = out.get("tracker") or {}
    parts.append("<h2>Your bet tracker</h2>")
    sm = tr.get("summary")
    if sm:
        parts.append("<div class='grid'>" + "".join(f"<div class='stat'><b>{E(str(v))}</b><span>{E(k)}</span></div>" for k, v in (
            ("Record", sm["record"]), ("Units", f"{sm['units']:+}"), ("ROI", f"{sm['roi%']:+}%"),
            ("Avg CLV (points)", sm["avg_clv_pts"]), ("Beat the closing line", f"{sm['beat_close%']}%"), ("Open bets", sm["open"]))) + "</div>")
    else:
        parts.append("<p class='note'>No graded bets yet. Every BET the model makes is logged in <code>betting/bet_log.csv</code> "
                     "at the line when it was first recommended, then graded against the result and the closing line.</p>")
    if tr.get("recent"):
        parts.append(table(tr["recent"][::-1], [("Logged", "logged"), ("Game", "game"), ("Book", "book"), ("Bet", "bet"), ("Odds", "odds"),
                                                ("Close", "close_line"), ("CLV pts", "clv_pts"), ("Result", "result"), ("Units", "units")]))
    parts.append("<p class='note'>Closing-line value (CLV) is the real scoreboard. If the line keeps moving your way after you bet, "
                 "you're beating the market, even through losing streaks. Win/loss alone needs 500+ bets to mean anything.</p>")
    if bt:
        acc = bt["accuracy"]
        parts.append(f"<h2>Backtest: every bet placed at the closing line</h2>")
        parts.append("<div class='grid'>" + "".join(
            f"<div class='stat'><b>{acc[m]['closing line']:.2f} / {acc[m]['model alone']:.2f} / {acc[m]['blend']:.2f}</b>"
            f"<span>{m} RMSE: closing line / model alone / blend (points)</span></div>" for m in ("spread", "total")) + "</div>")
        parts.append(f"<p class='note'>No leakage: every season is predicted by a model trained only on earlier seasons. "
                     f"Features and settings were chosen on 2014–2018 (<b>tuning</b>), so {bt['from']}–{bt['to']} (<b>holdout</b>) is "
                     f"the honest estimate. Break-even at -110 is 52.4%.</p>")
        parts.append(table(bt["table"], [("Period", "period"), ("Market", "market"), ("Min edge", "min_ev"), ("Bets", "bets"), ("W-L-P", "record"),
                                         ("Win %", "win%"), ("Units", "units"), ("ROI", "roi%"), ("¼-Kelly bankroll ×", "kelly_bankroll_x")],
                           {"min_ev": lambda v, r: f"{v:.0%}",
                            "units": lambda v, r: f"<span class='{'pos' if v > 0 else 'neg'}'>{v:+.1f}</span>",
                            "roi%": lambda v, r: f"<span class='{'pos' if v > 0 else 'neg'}'>{v:+.1f}%</span>"}))
    doc = (f"<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
           f"<title>NFL Betting Model</title><style>{CSS}</style></head><body><main>{''.join(parts)}</main></body></html>")
    with open(os.path.join(HERE, "card.html"), "w") as f:
        f.write(doc)
