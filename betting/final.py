#!/usr/bin/env python3
"""Decision layer: combine the model, the systems and the situational angles into one final card per sport.

For every possible bet (game x market x side) it collects the signals that point at it:
  model    the prediction model's edge at the best FanDuel/DraftKings price (a BET needs 3%+)
  system   a long-run betting system (Blowout Over, Wind Under, Close Road Team, Buy-Low Underdog, Rested Home Team)
  angle    a situational spot that held up on 15 seasons of closing lines (angles.py)
Then:
  - conflicts (signals on both sides of the same market) are passed, and listed
  - the stake comes from the strongest signal (Strong 1u, Moderate 0.5u, model BET = its Kelly size), plus 0.5u for
    each extra independent signal that agrees (stacking tested positive: angles win more when the model agrees), capped at 2u
  - a Weak or stack-only angle only plays when the model agrees
  - every play carries its backup: each signal's record and the game-specific reason
  - price: FanDuel unless DraftKings is strictly better; spreads/totals only at -115 or better

Writes betting/data/final_nfl.json / betting/data/cfb/final_cfb.json and prints the card.
Usage: python3 betting/final.py [nfl|cfb]   (run model.py/cfb_model.py --week first)
"""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import angles as A  # noqa: E402

PREFERRED = "FanDuel"
MIN_ODDS = {"spread": -115, "total": -115, "ml": -200}
SYSTEM_GRADE = {"Blowout over": "Strong", "Wind under": "Moderate", "Close road team": "Moderate",
                "Close road team ML": "Moderate", "Buy-low underdog": "Moderate", "Rested home team": "Weak"}
BASE_UNITS = {"Strong": 1.0, "Moderate": 0.5, "Weak": 0.5, "Stack only": 0.5}
MAX_UNITS = 2.0


def payout(o):
    return o / 100 if o > 0 else 100 / -o


def paths(sport):
    d = os.path.join(HERE, "data") if sport == "nfl" else os.path.join(HERE, "data", "cfb")
    return os.path.join(d, "card.json"), os.path.join(d, "book_odds.csv"), os.path.join(d, f"final_{sport}.json")


def fmt_line(market, side, line, home, away):
    if market == "total":
        return f"{side.title()} {line:g}"
    team = home if side == "home" else away
    if market == "ml":
        return f"{team} ML"
    return f"{team} {(-line if side == 'home' else line):+g}"


def best_offer(offers, market, side):
    """Better number first, then better price, FanDuel on a tie."""
    o = [x for x in offers if x["market"] == market and x["side"] == side]
    if not o:
        return None
    def key(x):
        num = 0 if market == "ml" else (-x["line"] if side in ("home", "over") else x["line"])
        return (num, payout(x["odds"]), x["book"] == PREFERRED)
    return max(o, key=key)


def build(sport):
    card_p, books_p, out_p = paths(sport)
    card = json.load(open(card_p))
    season, week = card["week"]["season"], card["week"]["week"]
    df, L, res = A.evaluate(sport)
    up = df[(df.season == season) & (df.week == week) & df.result.isna()]
    today = pd.Timestamp.now(tz="America/New_York").strftime("%Y-%m-%d")
    up = up[up.gameday.astype(str).str[:10] >= today]
    keys = {}
    for r in up.itertuples(index=False):
        k = (r.away, r.home) if sport == "nfl" else (r.away_id, r.home_id)
        keys[f"{r.away} @ {r.home}"] = {"key": k, "home": r.home, "away": r.away, "game_id": r.game_id, "date": r.gameday}
    books = pd.read_csv(books_p) if os.path.exists(books_p) else pd.DataFrame(columns=["away", "home", "book", "market", "side", "line", "odds"])
    offers = {}
    for b in books.itertuples(index=False):
        offers.setdefault((b.away, b.home), []).append({"book": b.book, "market": b.market, "side": b.side,
                                                         "line": float(b.line), "odds": float(b.odds)})

    sig = {}   # (game, market, side) -> list of signals
    model_side = {}
    for p in card["week"]["picks"]:
        if p["game"] not in keys:
            continue
        side = p["side"]
        model_side[(p["game"], p["market"])] = side
        sig.setdefault((p["game"], p["market"], side), []).append({
            "type": "model", "name": "Model", "grade": "BET" if p["tier"] == "BET" else p["tier"],
            "ev": p["ev%"], "win": p["win%"], "stake": p.get("stake%", 0) / 100,
            "text": None})
    for sy in card.get("systems", []):
        for g in sy["games"]:
            if g["game"] not in keys:
                continue
            m, side = (g.get("market"), g.get("side"))
            if m is None:  # skipped plays carry no side; recover it from the label
                continue
            sig.setdefault((g["game"], m, side), []).append({
                "type": "system", "name": sy["name"], "grade": SYSTEM_GRADE.get(sy["name"], "Moderate"),
                "record": sy["record"], "roi": sy["roi%"], "recent": sy["recent_record"], "recent_roi": sy["recent_roi%"],
                "why": sy["why"]})
    for a in A.live(sport, season, week, res=res):
        game = f"{a['away']} @ {a['home']}"
        if game not in keys:
            continue
        s = a["summary"]
        sig.setdefault((game, a["market"], a["bet_side"]), []).append({
            "type": "angle", "name": a["angle"], "grade": a["grade"], "stack_only": a["stack_only"],
            "record": s["record"], "roi": s["roi%"], "recent": s["recent_record"], "recent_roi": s["recent_roi%"],
            "up": s["up"], "why": a["why"], "detail": a["detail"], "with_model": a["with_model"]})

    plays, conflicts, leans = [], [], []
    for (game, market, side), sigs in sig.items():
        info = keys[game]
        edge_sigs = [x for x in sigs if x["type"] != "model"]
        model = next((x for x in sigs if x["type"] == "model"), None)
        agrees = model_side.get((game, market)) == side
        opp = {"home": "away", "away": "home", "over": "under", "under": "over"}[side]
        opp_sigs = [x for x in sig.get((game, market, opp), []) if x["type"] != "model"]
        model_bet = model is not None and model["grade"] == "BET"
        if not edge_sigs and not model_bet:
            continue
        if opp_sigs and edge_sigs:
            conflicts.append({"game": game, "market": market, "a": [x["name"] for x in edge_sigs], "b": [x["name"] for x in opp_sigs]})
            continue
        live = [x for x in edge_sigs if not x.get("stack_only") and x["grade"] != "Weak"]
        cond = [x for x in edge_sigs if x.get("stack_only") or x["grade"] == "Weak"]
        if cond and agrees:
            live += cond
        if not live and not model_bet:
            for x in cond:
                leans.append({"game": game, "market": market, "side": side, "why": f"{x['name']}: {x.get('detail', '')}",
                              "note": "plays only when the model agrees; it doesn't this week"})
            continue
        units = max([BASE_UNITS.get(x["grade"], 0.5) for x in live] +
                    ([max(0.5, round(model["stake"] * 100 * 2) / 2)] if model_bet else []))
        n_signals = len(live) + (1 if model_bet else 0) + (1 if (agrees and not model_bet and model and model["ev"] > 0) else 0)
        units = min(MAX_UNITS, units + 0.5 * max(0, n_signals - 1))
        off = best_offer(offers.get(info["key"], []), market, side)
        if off is None:
            continue
        if payout(off["odds"]) < payout(MIN_ODDS[market]):
            leans.append({"game": game, "market": market, "side": side,
                          "why": " + ".join(x["name"] for x in live) or "Model",
                          "note": f"price too steep at {off['book']} {off['odds']:+.0f}; bet at {MIN_ODDS[market]:+d} or better"})
            continue
        backup = []
        for x in live:
            if x["type"] == "system":
                backup.append({"title": f"System · {x['name']} ({x['grade']})",
                               "text": f"{x['why']} Record {x['record']} since 2011 ({x['roi']:+}% ROI); "
                                       f"{x['recent']} in 2025-26 ({x['recent_roi']:+}%)."})
            else:
                wm = x["with_model"]
                backup.append({"title": f"Situational · {x['name']} ({x['grade']})",
                               "text": f"{x['detail']} {x['why']} Record {x['record']} vs the closing number since 2011 "
                                       f"({x['roi']:+}% ROI, profitable {x['up']} seasons; {x['recent']} in 2025-26)"
                                       + (f"; {wm[0]:+}% when our model agreed ({wm[1]} bets)." if wm[1] else ".")})
        if model is not None and (model_bet or agrees):
            backup.append({"title": "Model" + (" · 3%+ edge" if model_bet else " agrees"),
                           "text": f"Our model makes this side a {model['win']:.0f}% winner "
                                   f"({model['ev']:+.1f}% expected value at the card price)."})
        plays.append({"game": game, "game_id": info["game_id"], "date": str(info["date"])[:10], "market": market, "side": side,
                      "bet": fmt_line(market, side, off["line"], info["home"], info["away"]),
                      "odds": int(off["odds"]), "book": off["book"], "line": off["line"], "units": units,
                      "tier": "Best Bet" if units >= 1 else "Play",
                      "signals": [x["name"] for x in live] + (["Model"] if model_bet else []),
                      "model_agrees": bool(agrees), "backup": backup})
    # one bet per team per game: the spread by default, the moneyline only when no spread play exists
    spread_sides = {(p["game"], p["side"]) for p in plays if p["market"] == "spread"}
    plays = [p for p in plays if not (p["market"] == "ml" and (p["game"], p["side"]) in spread_sides)]
    plays.sort(key=lambda x: (-x["units"], x["date"], x["game"]))
    # the model's strongest opinions that aren't plays (for the card's Model Leans list)
    taken = {(p["game"], p["market"]) for p in plays}
    board = {b["game"]: b for b in card["week"]["board"]}
    model_leans = []
    for p in sorted(card["week"]["picks"], key=lambda x: -x["ev%"]):
        if p["game"] not in keys or (p["game"], p["market"]) in taken or p["market"] == "ml" or p["ev%"] < -0.5:
            continue
        b = board.get(p["game"], {})
        fair = b.get("fair_total") if p["market"] == "total" else b.get("fair_spread")
        mkt = b.get("market_total") if p["market"] == "total" else b.get("market_spread")
        model_leans.append({"game": p["game"], "bet": p["bet"], "odds": p["odds"], "win": p["win%"], "ev": p["ev%"],
                            "fair": fair, "market": mkt, "model_raw": b.get("model_total" if p["market"] == "total" else "model_spread"),
                            "target": p.get("target")})
        if len(model_leans) == 5:
            break
    log_plays(sport, plays)
    out = {"sport": sport, "season": season, "week": week, "plays": plays, "leans": leans, "conflicts": conflicts,
           "model_leans": model_leans,
           "angles": {k: {"grade": v["grade"], "summary": v["summary"], "market": v["market"], "why": v["why"],
                          "with_model": v["with_model"]} for k, v in res.items()}}
    with open(out_p, "w") as f:
        json.dump(out, f, indent=1, default=str)
    return out


def log_plays(sport, plays):
    """Record the final card in the tracker (graded later against results and closing lines)."""
    import track
    track.LOG = os.path.join(HERE, "bet_log.csv" if sport == "nfl" else "cfb_bet_log.csv")
    rows = [{"game_id": p["game_id"], "game": p["game"], "market": p["market"], "side": p["side"], "book": p["book"],
             "bet": p["bet"], "line": None if p["market"] == "ml" else p["line"], "odds": p["odds"], "win%": 0.0,
             "ev%": 0.0, "stake%": p["units"], "tier": "FINAL", "system": " + ".join(p["signals"])} for p in plays]
    track.save(track.log_picks(rows))


def show(out):
    print(f"\n===== {out['sport'].upper()} final card, week {out['week']}: {len(out['plays'])} plays, "
          f"{sum(p['units'] for p in out['plays']):g}u =====")
    for p in out["plays"]:
        print(f"{p['tier']:8s} {p['units']:.1f}u  {p['bet']:28s} {p['odds']:+5d} {p['book']:10s} {p['game']:40s} "
              f"[{' + '.join(p['signals'])}]{'  (model agrees)' if p['model_agrees'] and 'Model' not in p['signals'] else ''}")
    for c in out["conflicts"]:
        print(f"PASS (conflict) {c['game']} {c['market']}: {', '.join(c['a'])} vs {', '.join(c['b'])}")
    for m in out["model_leans"]:
        print(f"model lean {m['game']}: {m['bet']} {m['odds']:+d} fair {m['fair']} vs {m['market']} (ev {m['ev']:+.1f}%)")
    for l in out["leans"]:
        print(f"lean {l['game']} {l['market']} {l['side']}: {l['why']} — {l['note']}")


if __name__ == "__main__":
    for sp in (sys.argv[1:] or ["nfl", "cfb"]):
        show(build(sp))
