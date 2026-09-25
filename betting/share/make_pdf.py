#!/usr/bin/env python3
"""One-page-ish shareable PDF: Best Bets (each with why), Leans, and an Oddball Matchup.

Reads the latest NFL + college cards (betting/data/card.json, betting/data/cfb/card.json), weather, and
betting/share/oddball.json (hand-written each week). Run the models first.

Usage: python3 betting/share/make_pdf.py "Week 4"      -> betting/share/<label>_card.pdf
"""
import json
import os
import sys
from datetime import datetime

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

HERE = os.path.dirname(os.path.abspath(__file__))
BET = os.path.dirname(HERE)
INK, MUTE, LINE = colors.HexColor("#16181d"), colors.HexColor("#5b6270"), colors.HexColor("#e3e6eb")
GREEN, GREENBG = colors.HexColor("#0f7b4f"), colors.HexColor("#e7f6ee")
AMBER, AMBERBG = colors.HexColor("#8a6d00"), colors.HexColor("#fdf6dc")
BLUE, BLUEBG = colors.HexColor("#1f4fb2"), colors.HexColor("#e8eefb")

S = {
    "title": ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=INK),
    "sub": ParagraphStyle("s", fontName="Helvetica", fontSize=9.5, leading=13, textColor=MUTE),
    "h": ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=INK, spaceBefore=10, spaceAfter=4),
    "hnote": ParagraphStyle("hn", fontName="Helvetica", fontSize=8.5, leading=11.5, textColor=MUTE, spaceAfter=6),
    "pick": ParagraphStyle("p", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=INK),
    "meta": ParagraphStyle("m", fontName="Helvetica", fontSize=8.5, leading=11, textColor=MUTE),
    "why": ParagraphStyle("w", fontName="Helvetica", fontSize=9, leading=12.2, textColor=INK, alignment=TA_LEFT),
    "cell": ParagraphStyle("c", fontName="Helvetica", fontSize=8.5, leading=11, textColor=INK),
    "cellb": ParagraphStyle("cb", fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=INK),
    "foot": ParagraphStyle("f", fontName="Helvetica", fontSize=7.5, leading=10, textColor=MUTE),
}


def load(path):
    with open(path) as f:
        return json.load(f)


def units(stake_pct):
    return max(0.5, round(stake_pct * 2) / 2)


def day(d):
    try:
        return datetime.strptime(str(d)[:10], "%Y-%m-%d").strftime("%a %-m/%-d")
    except ValueError:
        return ""


def board_by_game(card):
    return {b["game"]: b for b in card["week"]["board"]}


def weather(game_id):
    p = os.path.join(BET, "data", "weather.csv")
    if not os.path.exists(p):
        return None
    w = pd.read_csv(p).set_index("game_id")
    return w.loc[game_id] if game_id in w.index else None


def model_reason(p, b, sport):
    edge, win = p["ev%"], p["win%"]
    need = 100 / (1 + (p["odds"] / 100 if p["odds"] > 0 else 100 / -p["odds"]))
    if p["market"] == "total":
        cons = b["market_total"]
        line = float(p["bet"].split()[-1])
        side = "Over" if p["bet"].startswith("Over") else "Under"
        txt = (f"Our model projects <b>{b['model_total']}</b> total points (blended with the market: {b['fair_total']}). ")
        if abs(cons - line) >= 0.5:
            better = (line < cons) if side == "Over" else (line > cons)
            txt += (f"DraftKings is dealing {line:g} while the rest of the market sits at {cons:g}, "
                    f"{'a better number for us' if better else 'so shop around'}. ")
        w = weather(p["game_id"]) if sport == "NFL" else None
        if w is not None:
            txt += f"Kickoff forecast: {w['temp']:.0f}°F, {w['wind']:.0f} mph wind. "
    elif p["market"] == "spread":
        txt = f"Model spread {b['model_spread']} (fair {b['fair_spread']}) vs the market's {b['market_spread']}. "
    else:
        txt = f"Model win chance {win}% (fair price {b['fair_ml']}). "
    if b.get("qbs") and "?" not in b["qbs"]:
        txt += f"QBs: {b['qbs']}. "
    txt += f"Wins about <b>{win:.0f}%</b> of the time by our numbers; you need {need:.1f}% at {p['odds']:+d}. Edge: <b>+{edge}%</b>."
    return txt


KEY3 = 14.4  # % of NFL games since 2011 decided by exactly 3 (nflverse)
SPREAD_BUCKET = [(40, "40+ point spreads: overs +10% ROI since 2011"), (30, "30–40 point spreads: overs +6% ROI since 2011")]


def system_reason(sy, g, b):
    rec = f"System: {sy['record']} since 2011 ({sy['roi%']:+}% ROI), {sy['recent_record']} in 2025–26 ({sy['recent_roi%']:+}%)."
    away, home = g["game"].split(" @ ")
    if sy["name"] == "Wind under":
        w = weather(g.get("game_id"))
        wind = f"{w['wind']:.0f} mph wind" + (f" and {w['temp']:.0f}°F" if w is not None else "") if w is not None else "12+ mph wind"
        return (f"Forecast calls for <b>{wind}</b> at kickoff. Wind shortens passing games and makes kicks harder, and "
                f"totals historically don't come down enough (unders +12% ROI in 12–20 mph wind since 2011). "
                f"This trend cooled off in 2025, so half stake. {rec}")
    if sy["name"] == "Close road team, daytime":
        line = g["bet"].split()[-1]
        txt = (f"Road team in a coin-flip daytime game. Home field is worth less than these short lines assume. "
               f"Model fair line: {b.get('fair_spread', '')}. ")
        if line in ("+3", "+3.5"):
            txt += f"Getting the full field goal matters: <b>{KEY3}%</b> of NFL games since 2011 ended on exactly 3. "
        if g["odds"] > -105:
            txt += f"Plus a better-than-usual price ({g['odds']:+d}). "
        return txt + rec
    return f"{sy['why']} {rec}"


def blowout_rows(sy, games, boards):
    rows = []
    for g in games:
        b = boards.get(g["game"], {})
        spread = abs(float(b["market_spread"].split()[-1]))
        total = float(g["bet"].split()[-1])
        dog = g["game"].split(" @ ")[0]
        bucket = next(t for lo, t in SPREAD_BUCKET if spread > lo)
        why = (f"{g['game'].split(' @ ')[1]} by {spread:g}; the market has {dog} scoring only ~<b>{(total - spread) / 2:.0f}</b>. "
               f"{bucket}. Model total {b.get('model_total')}.")
        rows.append((g, b, why))
    return rows


def pick_block(label, meta, why, accent, bg):
    t = Table([[Paragraph(label, S["pick"])], [Paragraph(meta, S["meta"])], [Paragraph(why, S["why"])]],
              colWidths=[7.0 * inch])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("LINEBEFORE", (0, 0), (0, -1), 3, accent),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, 0), 7), ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
                           ("TOPPADDING", (0, 1), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -2), 1)]))
    return KeepTogether([t, Spacer(1, 6)])


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "This week"
    nfl, cfb = load(os.path.join(BET, "data", "card.json")), load(os.path.join(BET, "data", "cfb", "card.json"))
    odd = load(os.path.join(HERE, "oddball.json"))
    best, leans, watch, blowouts = [], [], [], []
    blow_sys, blow_boards = None, {}
    for sport, card in (("NFL", nfl), ("CFB", cfb)):
        boards = board_by_game(card)
        for p in card["week"]["picks"]:
            b = boards.get(p["game"], {})
            if p["tier"] == "BET":
                best.append((p["ev%"], sport, p, b, model_reason(p, b, sport), "Model"))
            elif p["tier"] == "lean":
                leans.append((sport, p, b))
        for sy in card.get("systems", []):
            for g in sy["games"]:
                b = boards.get(g["game"], {})
                g = dict(g, **({"game_id": g.get("game_id")} if g.get("game_id") else {}))
                if g["tier"] == "SYSTEM" and sy["name"] == "Blowout over":
                    blowouts.append(g)
                    blow_sys = sy
                    blow_boards = boards
                elif g["tier"] == "SYSTEM":
                    best.append((0, sport, g, b, system_reason(sy, g, b), sy["name"]))
                elif g["tier"] == "SKIP":
                    watch.append((sport, g, sy["name"]))
    order = {"Model": 0, "Wind under": 1, "Close road team, daytime": 2}
    best.sort(key=lambda x: (order.get(x[5], 3), x[1] != "NFL", -x[0]))

    out = os.path.join(HERE, f"{label.lower().replace(' ', '_')}_card.pdf")
    doc = SimpleDocTemplate(out, pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                            topMargin=0.6 * inch, bottomMargin=0.6 * inch, title=f"{label} Betting Card")
    st = [Paragraph(f"{label} Betting Card", S["title"]),
          Paragraph(f"College Football Week {cfb['week']['week']} · NFL Week {nfl['week']['week']} · "
                    f"prices: DraftKings · 1 unit = 1% of bankroll", S["sub"]), Spacer(1, 8)]

    tot_units = sum(units(x[2]["stake%"]) for x in best) + sum(units(g["stake%"]) for g in blowouts)
    st.append(Paragraph(f"Best Bets ({len(best) + len(blowouts)} plays, {tot_units:g} units)", S["h"]))
    st.append(Paragraph("Model plays have at least a 3% edge at the listed price. System plays come from betting trends "
                        "that held up over 15 seasons of data.", S["hnote"]))
    for _ev, sport, p, b, why, src in best:
        u = units(p["stake%"])
        tag = "MODEL" if src == "Model" else f"SYSTEM: {src.upper()}"
        st.append(pick_block(f"{p['bet']}  ({p['odds']:+d})  ·  {u:g}u",
                             f"{sport} · {p['game']} · {day(b.get('gameday'))} · {tag}", why, GREEN, GREENBG))

    if blowouts:
        sy = blow_sys
        st.append(KeepTogether([pick_block(
            f"College Blowout Overs: {len(blowouts)} plays, 1u each",
            f"CFB Week {cfb['week']['week']} · SYSTEM: BLOWOUT OVER · {sy['record']} since 2011 ({sy['roi%']:+}% ROI), "
            f"{sy['recent_record']} in 2025–26 ({sy['recent_roi%']:+}%)",
            "When the spread is over 30, bet the Over. The market prices the favorite correctly but underrates the "
            "underdog: second-stringers on both sides and garbage-time drives add about a point the market doesn't "
            "expect. Overs get better the bigger the spread (14–21 points: −7% ROI; 30–40: +6%; 40+: +10%). "
            "This is the one trend that passed our luck test across 1,192 strategies, and it's still winning in 2025–26.",
            GREEN, GREENBG)]))
        rows = [[Paragraph(h, S["cellb"]) for h in ("Bet", "Game", "Price", "Why this one")]]
        for g, b, why in blowout_rows(sy, blowouts, blow_boards):
            rows.append([Paragraph(g["bet"], S["cellb"]), Paragraph(f"{g['game']} · {day(b.get('gameday'))}", S["cell"]),
                         Paragraph(f"{g['odds']:+d}", S["cell"]), Paragraph(why, S["cell"])])
        t = Table(rows, colWidths=[0.95 * inch, 2.05 * inch, 0.5 * inch, 3.5 * inch], repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), GREENBG), ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINE),
                               ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
        st += [t, Spacer(1, 4)]

    st.append(Paragraph("Leans", S["h"]))
    st.append(Paragraph("A real but thin edge (1–3%) or waiting on a better price. Worth tracking, not worth "
                        "a full bet.", S["hnote"]))
    rows = [[Paragraph(h, S["cellb"]) for h in ("Lean", "Game", "Price", "Why")]]
    for sport, p, b in leans:
        why = (f"Model edge +{p['ev%']}%, wins ~{p['win%']:.0f}%. "
               + (f"Fair total {b.get('fair_total')}." if p["market"] == "total" else f"Fair line {b.get('fair_spread')}, fair ML {b.get('fair_ml')}."))
        rows.append([Paragraph(p["bet"], S["cellb"]), Paragraph(f"{sport} · {p['game']}", S["cell"]),
                     Paragraph(f"{p['odds']:+d}", S["cell"]), Paragraph(why, S["cell"])])
    for sport, g, name in watch:
        need = g["skip"].split("need ")[-1].rstrip(")")
        rows.append([Paragraph(g["bet"], S["cellb"]), Paragraph(f"{sport} · {g['game']}", S["cell"]),
                     Paragraph(f"{g['odds']:+d}", S["cell"]),
                     Paragraph(f"{name} system play, but the price is too steep. Bet it if it gets to {need}.", S["cell"])])
    t = Table(rows, colWidths=[1.35 * inch, 2.0 * inch, 0.6 * inch, 3.05 * inch], repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), AMBERBG), ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINE),
                           ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 4),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    st += [t, Spacer(1, 6)]

    st.append(Paragraph("Oddball Matchup of the Week", S["h"]))
    ob = Table([[Paragraph(odd["title"], S["pick"])], [Paragraph(odd["sub"], S["meta"])],
                [Paragraph(odd["body"], S["why"])], [Paragraph(f"<b>Did you know?</b> {odd['fact']}", S["why"])],
                [Paragraph(odd["model"], S["meta"])]], colWidths=[7.0 * inch])
    ob.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), BLUEBG), ("LINEBEFORE", (0, 0), (0, -1), 3, BLUE),
                            ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                            ("TOPPADDING", (0, 0), (-1, 0), 8), ("BOTTOMPADDING", (0, -1), (-1, -1), 8)]))
    st += [ob, Spacer(1, 10)]
    st.append(Paragraph("Lines move. Check the current DraftKings price before betting; if a number moves against you, the "
                        "edge can disappear. Past results don't guarantee future results. For entertainment only; "
                        "21+, bet responsibly (1-800-GAMBLER).", S["foot"]))

    def page(c, d):
        c.saveState()
        c.setFont("Helvetica", 7.5)
        c.setFillColor(MUTE)
        c.drawRightString(letter[0] - 0.75 * inch, 0.4 * inch, f"{label} card · page {d.page}")
        c.restoreState()
    doc.build(st, onFirstPage=page, onLaterPages=page)
    print(out)


if __name__ == "__main__":
    main()
