#!/usr/bin/env python3
"""First-half (1H) NFL bets: estimated 1H lines, pre-registered 1H angles graded on 2012-2026.

Free data has no archive of first-half lines, so each season's 1H line is estimated from earlier seasons only:
  1H spread = b * full-game spread, 1H total = a * full-game total (fit through the origin, rounded to .5)
Every angle is written down with its reason before testing and graded at -110 against those estimates. Because
the lines are estimates, a 1H angle needs a stricter bar than full-game angles (t >= 2.0, profitable in both
2012-2018 and 2019+, not losing in 2025-26) and plays at 0.5u.

Writes betting/data/first_half.json (grades + this week's qualifying 1H bets). Usage: python3 betting/first_half.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import angles as A  # noqa: E402

DATA = os.path.join(HERE, "data")
UNITS = 0.5


def half_round(x):
    return np.round(np.asarray(x, dtype=float) * 2) / 2


def estimate_lines(L):
    """Walk-forward 1H line estimates on the long table (one row per team per game)."""
    h = pd.read_csv(os.path.join(DATA, "halves.csv"))
    L = L.merge(h, on="game_id", how="left")
    L["h1_margin"] = np.where(L["side"] == "home", L["h1_home"] - L["h1_away"], L["h1_away"] - L["h1_home"])
    L["h1_total"] = L["h1_home"] + L["h1_away"]
    g = L[L["side"] == "home"].dropna(subset=["h1_total", "line", "total_line"])
    L["h1_line"], L["h1_total_line"] = np.nan, np.nan
    fits = {}
    for s in sorted(L["season"].unique()):
        tr = g[g["season"] < s]
        if len(tr) < 200:
            tr = g[g["season"] <= s] if s == g["season"].min() else tr
        b = float((tr["line"] * tr["h1_margin"]).sum() / (tr["line"] ** 2).sum())
        a = float((tr["total_line"] * tr["h1_total"]).sum() / (tr["total_line"] ** 2).sum())
        fits[int(s)] = (round(a, 3), round(b, 3))
        m = L["season"] == s
        L.loc[m, "h1_line"] = half_round(b * L.loc[m, "line"])
        L.loc[m, "h1_total_line"] = half_round(a * L.loc[m, "total_line"])
    return L, fits


def bets(L, mask, market, side):
    x = L[mask.fillna(False).values].copy()
    if market == "spread":
        x = x[x["h1_line"].notna()]
        x["bet_side"] = np.where(side == "team", x["side"], np.where(x["side"] == "home", "away", "home"))
        both = x.groupby("game_id")["bet_side"].nunique()
        x = x[x["game_id"].isin(both[both == 1].index)].drop_duplicates("game_id")
        cover = (1 if side == "team" else -1) * (x["h1_margin"] - x["h1_line"])
    else:
        x = x[x["h1_total_line"].notna()].drop_duplicates("game_id")
        x["bet_side"] = side
        cover = (x["h1_total"] - x["h1_total_line"]) * (1 if side == "over" else -1)
    x["units"] = np.where(cover > 0, 100 / 110, np.where(cover < 0, -1.0, 0.0))
    x.loc[cover.isna().values, "units"] = np.nan
    return x


def angles(L):
    fav = L["line"] > 0
    return {
        "1H favorite (3+ pts)": (fav & (L["line"] >= 3), "spread", "team",
                                 "Better teams script their openers well and start fast; the 1H line is a flat cut of the game line."),
        "1H home dog": (L["is_home"] & (L["line"] < 0), "spread", "team",
                        "Crowd and fresh legs matter most early; home dogs start strong."),
        "1H west-coast early fade": (L["west_early"], "spread", "opp",
                                     "The 10am body clock bites hardest in the first half; the full-game edge for these "
                                     "teams comes from the second half."),
        "1H road favorite": (L["is_away"] & (L["line"] >= 3), "spread", "team",
                             "A road favorite's talent edge shows from the start, before the crowd matters late."),
        "1H off the bye": (L["bye_edge"] & (L["playoff"] == 0), "spread", "team",
                           "Two weeks to script the opening drives."),
        "1H primetime under": (L["prime"] == 1, "total", "under",
                               "Extra prep time for defenses; offenses feel each other out early under the lights."),
        "1H wind under (12+ mph)": ((L["dome"] == 0) & (L["wind"] >= 12), "total", "under",
                                    "Wind hurts passing and kicking all game, and 1H totals don't adjust for it."),
        "1H dome over": (L["dome"] == 1, "total", "over",
                         "Fast track, no weather: scripted drives play out as designed."),
        "1H high-total under (48+)": (L["total_line"] >= 48, "total", "under",
                                      "Big totals expect shootouts; first halves start slower than the full-game number implies."),
        "1H low-total over (40 or less)": (L["total_line"] <= 40, "total", "over",
                                          "A low total gets cut in half to a tiny 1H number; one early score beats it."),
    }


def grade(s, first, second):
    if s["t"] >= 2.0 and first > 0 and second > 0 and s["recent_roi%"] >= 0:
        return "Passed"
    return None


def real_lines(live, L):
    """Swap estimated 1H totals for the real FanDuel / DraftKings numbers and check them against Pinnacle's 1H price.
    Keeps an under only at or above our estimate, only when Pinnacle doesn't lean the other way, and only when our
    price is no more than 2% worse than Pinnacle's fair price."""
    import requests
    import market as MK
    totals = [p for p in live if " Under " in p["bet"] or " Over " in p["bet"]]
    key = MK.odds_key()
    if not totals or not key:
        return live
    name = MK.nfl_name()
    base = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl"
    events = requests.get(f"{base}/events", params={"apiKey": key}, timeout=30).json()
    h = L[L["side"] == "home"].dropna(subset=["h1_total", "h1_total_line"])
    out = []
    for p in live:
        if p not in totals:
            out.append(p)
            continue
        away, home = p["game_id"].split("_")[2:4]
        e = next((x for x in events if x["away_team"] == name(away) and x["home_team"] == name(home)), None)
        if e is None:
            out.append(p)
            continue
        r = requests.get(f"{base}/events/{e['id']}/odds", params={"apiKey": key, "bookmakers": "fanduel,draftkings,pinnacle",
                                                                    "markets": "totals_h1", "oddsFormat": "american"}, timeout=30)
        books = {b["key"]: {o["name"]: (o.get("point"), o["price"]) for m in b["markets"] for o in m["outcomes"]}
                 for b in r.json().get("bookmakers", [])} if r.status_code == 200 else {}
        side = "Under" if " Under " in p["bet"] else "Over"
        est = float(p["bet"].split()[-1])
        offers = [(k, v[side]) for k, v in books.items() if k in MK.OURS and side in v]
        if not offers:
            p["note"] = "no FanDuel/DraftKings 1H total posted yet: bet only at or above the estimate"
            out.append(p)
            continue
        # best number for our side, then best price
        bk, (line, odds) = max(offers, key=lambda o: ((o[1][0] if side == "Under" else -o[1][0]), MK.payout(o[1][1])))
        p.update({"bet": f"1H {side} {line:g}", "odds_real": odds, "book_real": MK.OURS[bk], "est": est})
        if (side == "Under" and line < est) or (side == "Over" and line > est):
            p["cut"] = f"the real 1H line ({line:g}) is past our estimate ({est:g})"
        pin = books.get("pinnacle", {})
        if "Over" in pin and "Under" in pin:
            pmf = h[(h["h1_total_line"] - line).abs() <= 1.5]["h1_total"].astype(int).value_counts(normalize=True).to_dict()
            q = MK.novig(pin[side][1], pin["Under" if side == "Over" else "Over"][1])
            p_up, p_down = MK.convert(pmf, pin["Over"][0], q if side == "Over" else 1 - q, line)
            pw = p_up if side == "Over" else p_down
            push = 1 - p_up - p_down
            win = 100 * pw / max(1 - push, 1e-9)
            p["sharp"] = {"win": round(win, 1), "ev": round(100 * (pw * MK.payout(odds) - (1 - pw - push)), 1),
                          "pin": f"{pin['Over'][0]:g} (o{pin['Over'][1]:+d}/u{pin['Under'][1]:+d})"}
            if win < 48.5:
                p["cut"] = f"Pinnacle leans the other way ({win:.1f}% at {line:g})"
            elif p["sharp"]["ev"] < -2.0:   # same floor as final.py's system plays
                p["cut"] = f"the price is {p['sharp']['ev']:+.1f}% against Pinnacle ({win:.1f}% at {line:g} {odds:+d})"
        out.append(p)
    return out


def main():
    df, L = A.build("nfl")
    L, fits = estimate_lines(L)
    res = {}
    rows = []
    for name, (mask, market, side, why) in angles(L).items():
        b = bets(L, mask, market, side)
        s = A.summary(b)
        d = b[b["units"].notna() & (b["season"] >= 2012)]
        first = 100 * d[d["season"] <= 2018]["units"].mean()
        second = 100 * d[d["season"] >= 2019]["units"].mean()
        gr = grade(s, first, second)
        res[name] = {"market": market, "side": side, "why": why, "summary": s, "roi_2012_18%": round(first, 1),
                     "roi_2019%": round(second, 1), "grade": gr}
        rows.append({"angle": name, "bets": s["bets"], "record": s["record"], "roi%": s["roi%"], "t": s["t"], "up": s["up"],
                     "12-18": round(first, 1), "19+": round(second, 1), "25-26": f"{s['recent_record']} ({s['recent_roi%']:+})",
                     "grade": gr or "-"})
        res[name]["bets_df"] = b
    print("1H line estimates (latest): total x%.3f, spread x%.3f" % fits[max(fits)])
    print(pd.DataFrame(rows).to_string(index=False))
    # this week's qualifiers for passed angles
    up = L[L["margin"].isna() & (L["season"] == L["season"].max())]
    up = up[up["week"] == up["week"].min()] if len(up) else up
    live = []
    for name, v in res.items():
        if not v["grade"]:
            continue
        mask, market, side, why = angles(up)[name]
        for r in up[mask.fillna(False).values].drop_duplicates("game_id").itertuples():
            team = r.name if side == "team" else r.opp_name
            line = r.h1_line if side == "team" else -r.h1_line
            bet = f"1H {team} {-line:+g}" if market == "spread" else f"1H {side.title()} {r.h1_total_line:g}"
            live.append({"angle": name, "game_id": r.game_id, "bet": bet, "units": UNITS, "why": why,
                         "record": v["summary"]["record"], "roi": v["summary"]["roi%"], "recent": v["summary"]["recent_record"],
                         "est_line": True})
    live = real_lines(live, L)
    out = {"fits": {str(k): v for k, v in fits.items()},
           "angles": {k: {kk: vv for kk, vv in v.items() if kk != "bets_df"} for k, v in res.items()}, "live": live}
    with open(os.path.join(DATA, "first_half.json"), "w") as f:
        json.dump(out, f, indent=1, default=str)
    print(f"\nthis week's 1H plays: {len(live)}")
    for p in live:
        print("  ", p["bet"], p.get("odds_real", ""), p.get("book_real", ""), "|", p["angle"], "| sharp", p.get("sharp"),
              "| CUT: " + p["cut"] if p.get("cut") else "")


if __name__ == "__main__":
    main()
