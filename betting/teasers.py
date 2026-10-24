#!/usr/bin/env python3
"""NFL 6-point teasers (Wong teasers): a structural edge that still holds up against closing lines.

About 43% of NFL games end with a margin of 3 to 8, so a 6-point tease that moves an underdog of +1.5 to +2.5 up to
+7.5 / +8.5 crosses both 3 and 7 and wins more often than the books' teaser price assumes.
  Legs:     underdogs of +1.5 to +2.5, in games with a total of 49 or less (more scoring = the key numbers matter less)
  Price:    a 2-team 6-point teaser needs 73.9% per leg at -120 (75.2% at -130)
  History:  computed live from games.csv (2011-now) each run
The favorite version (-7.5 to -8.5 down to -1.5/-2.5) no longer clears the bar since the 2015 extra-point rule made
7-point margins less common, so it is shown but not bet.

Writes betting/data/teasers.json. Run after final.py (it uses the QB Watch). Usage: python3 betting/teasers.py
"""
import itertools
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
DOG = (1.5, 2.5)
FAV = (7.5, 8.5)
MAX_TOTAL = 49
TEASE = 6
UNITS = 0.5
BREAK_EVEN = {"-110": 0.7238, "-120": 0.7385, "-130": 0.7518}


def history(g):
    h = g[(g["season"] >= 2011) & g["result"].notna() & g["spread_line"].notna() & (g["game_type"] == "REG")].copy()
    a = h["spread_line"].abs()
    fav_margin = np.where(h["spread_line"] > 0, h["result"], -h["result"])
    h["dog_win"] = (-fav_margin + a + TEASE) > 0
    h["fav_win"] = (fav_margin - a + TEASE) > 0
    low = h["total_line"] <= MAX_TOTAL
    dog, fav = h[a.between(*DOG) & low], h[a.between(*FAV) & low]
    by = dog.groupby("season")["dog_win"].mean()
    roi = lambda p, price: p * p * (1 + 100 / price) - 1  # noqa: E731
    return {"dog_legs": int(len(dog)), "dog_win%": round(100 * dog["dog_win"].mean(), 1),
            "dog_recent": f"{100 * dog[dog.season >= 2022]['dog_win'].mean():.1f}% on {int((dog.season >= 2022).sum())}",
            "dog_seasons_up": f"{int((by >= BREAK_EVEN['-120']).sum())}/{len(by)}",
            "dog_roi_120%": round(100 * roi(dog["dog_win"].mean(), 120), 1),
            "fav_legs": int(len(fav)), "fav_win%": round(100 * fav["fav_win"].mean(), 1),
            "high_total_win%": round(100 * h[a.between(*DOG) & ~low]["dog_win"].mean(), 1),
            "margin_3_8%": round(100 * float(np.mean((np.abs(h["result"]) >= 3) & (np.abs(h["result"]) <= 8))), 1)}


def main():
    g = pd.read_csv(os.path.join(DATA, "games.csv"), low_memory=False)
    H = history(g)
    up = g[(g["season"] == g["season"].max()) & g["result"].isna()]
    today = pd.Timestamp.now(tz="America/New_York").strftime("%Y-%m-%d")
    up = up[up["gameday"] >= today]
    up = up[up["week"] == up["week"].min()]
    books = pd.read_csv(os.path.join(DATA, "book_odds.csv")) if os.path.exists(os.path.join(DATA, "book_odds.csv")) else pd.DataFrame()
    try:
        sys.path.insert(0, os.path.join(HERE, "share"))
        import weekly as W
        qb = {x["team"]: f"{x['qb']} {x['status'].lower()}" for x in W.nfl_qb_watch(W.Sport("nfl")) if x["cls"] in ("avoid", "watch")}
    except Exception as e:  # network trouble shouldn't stop the teaser list
        print("QB watch unavailable:", e)
        qb = {}
    legs, skipped = [], []
    for r in up.itertuples():
        offers = books[(books["home"] == r.home_team) & (books["away"] == r.away_team)] if len(books) else books
        best = None
        for book, x in (offers.groupby("book") if len(offers) else []):
            sp = x[(x["market"] == "spread") & (x["side"] == "home")]
            tot = x[(x["market"] == "total") & (x["side"] == "over")]
            if sp.empty or tot.empty:
                continue
            home_line = float(sp["line"].iloc[0])  # home-margin convention: > 0 means the home team is favored
            dog, dog_pts = (r.away_team, home_line) if home_line > 0 else (r.home_team, -home_line)
            cand = {"game": f"{r.away_team} @ {r.home_team}", "game_id": r.game_id, "gameday": r.gameday,
                    "gametime": r.gametime, "team": dog, "line": dog_pts, "teased": dog_pts + TEASE,
                    "total": float(tot["line"].iloc[0]), "book": book}
            better = best is None or (cand["line"], book == "FanDuel") > (best["line"], best["book"] == "FanDuel")
            if DOG[0] <= dog_pts <= DOG[1] and cand["total"] <= MAX_TOTAL and better:
                best = cand
        if best is None:
            continue
        if best["team"] in qb:
            skipped.append(dict(best, skip=f"QB Watch: {qb[best['team']]}"))
        else:
            legs.append(best)
    pairs = [{"legs": [a["team"] + f" +{a['teased']:g}", b["team"] + f" +{b['teased']:g}"], "games": [a["game"], b["game"]],
              "units": UNITS} for a, b in itertools.combinations(legs, 2)]
    out = {"history": H, "legs": legs, "skipped": skipped, "pairs": pairs, "break_even": BREAK_EVEN}
    with open(os.path.join(DATA, "teasers.json"), "w") as f:
        json.dump(out, f, indent=1, default=str)
    print(f"Wong teaser dog legs since 2011 (total <= {MAX_TOTAL}): {H['dog_win%']}% of {H['dog_legs']} "
          f"(need 73.9% at -120), {H['dog_seasons_up']} seasons above break-even, 2022+: {H['dog_recent']}")
    print(f"  favorite legs {H['fav_win%']}% of {H['fav_legs']} (not bet); dog legs with totals over {MAX_TOTAL}: "
          f"{H['high_total_win%']}%")
    for l in legs:
        print(f"  leg: {l['team']} +{l['line']:g} -> +{l['teased']:g} ({l['game']}, total {l['total']:g}, {l['book']})")
    for s in skipped:
        print(f"  skipped: {s['team']} +{s['line']:g} ({s['skip']})")
    for p in pairs:
        print(f"  2-team teaser: {' / '.join(p['legs'])}  {p['units']}u")
    if len(legs) < 2:
        print("  fewer than two legs: no teaser this week")


if __name__ == "__main__":
    main()
