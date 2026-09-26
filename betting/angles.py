#!/usr/bin/env python3
"""Situational angles, separate for the NFL and college football, each tested on 15 seasons of closing lines.

The two sports get different angle books because they bet differently:
  NFL      32 evenly matched teams, tight lines, key numbers (3 and 7), byes, short weeks, primetime,
           body-clock travel, QB injuries, wind.
  College  130+ FBS teams plus FCS opponents, huge talent gaps, 30-50 point spreads, service academies running
           the ball, conference vs non-conference, big swings in rest.

Every angle is defined in advance with a reason it should work (not found by searching), then graded against the
closing number:
  Strong    t >= 2.3 (the kind of result luck rarely produces)
  Moderate  t >= 1.5 and not falling apart in 2025-26
  Weak      t >= 1.0 and profitable in 2025-26
Stacking: each angle is also split by whether our model agreed with it, to see if the two together win more.

Usage: python3 betting/angles.py [nfl|cfb]
"""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

FIRST, LAST = 2011, 2025
ACADEMIES = {"Army", "Navy", "Air Force"}


def payout(o):
    o = np.asarray(o, dtype=float)
    o = np.where(np.isnan(o), -110.0, o)
    return np.where(o > 0, o / 100, 100 / np.abs(o))


# ------------------------------------------------------------------ long form: one row per team per game
def long_form(df, sport):
    hk, ak = ("home", "away") if sport == "nfl" else ("home_id", "away_id")
    rows = []
    for r in df.itertuples(index=False):
        neutral = r.hfa == 0
        for home in (True, False):
            sgn = 1 if home else -1
            row = {
                "game_id": r.game_id, "season": r.season, "week": r.week, "date": str(r.gameday)[:10],
                "team": getattr(r, hk if home else ak), "opp": getattr(r, ak if home else hk),
                "name": r.home if home else r.away, "opp_name": r.away if home else r.home,
                "is_home": home and not neutral, "is_away": (not home) and not neutral, "side": "home" if home else "away",
                "line": sgn * r.spread_line if pd.notna(r.spread_line) else np.nan,
                "margin": sgn * r.result if pd.notna(r.result) else np.nan,
                "odds": r.home_spread_odds if home else r.away_spread_odds,
                "opp_odds": r.away_spread_odds if home else r.home_spread_odds,
                "rating": (r.h_pts_for - r.h_pts_against) if home else (r.a_pts_for - r.a_pts_against),
                "opp_rating": (r.a_pts_for - r.a_pts_against) if home else (r.h_pts_for - r.h_pts_against),
                "total": r.total, "total_line": r.total_line, "over_odds": r.over_odds, "under_odds": r.under_odds,
            }
            if sport == "nfl":
                row.update({"div": r.div, "prime": r.prime, "wind": r.wind, "dome": r.dome, "cold": r.cold,
                            "playoff": r.playoff,
                            "bye_edge": r.bye_diff * sgn == 1, "short_vs_rested": r.short_diff * sgn == 1,
                            "west_early": (-sgn * r.west_early) > 0,
                            "qb_change": r.h_qb_change if home else r.a_qb_change})
            else:
                row.update({"conf": r.conf, "rest_edge": r.rest_diff * sgn, "opp_fcs": r.div_diff * sgn > 0,
                            "postseason": r.postseason, "line_move": r.line_move * sgn})
            rows.append(row)
    L = pd.DataFrame(rows).sort_values(["team", "date", "game_id"]).reset_index(drop=True)
    g = L.groupby(["team", "season"], sort=False)
    L["prev_margin"] = g["margin"].shift(1)
    L["prev_line"] = g["line"].shift(1)
    L["prev_is_away"] = g["is_away"].shift(1)
    L["prev2_is_away"] = g["is_away"].shift(2)
    L["next_opp_rating"] = g["opp_rating"].shift(-1)
    if sport == "cfb":
        L["prev_opp_fcs"] = g["opp_fcs"].shift(1)
    L["d"] = pd.to_datetime(L["date"])
    m = L.groupby(["team", "opp"], sort=False)
    L["last_meet_margin"] = m["margin"].shift(1)
    L["last_meet_days"] = (L["d"] - m["d"].shift(1)).dt.days
    return L


# ------------------------------------------------------------------ angle books
# each angle: (mask, market, side, reason, detail(row) -> the game-specific backup sentence)
#   spread angles: side 'team' bets the row's team, 'opp' bets its opponent
#   total angles: side 'over'/'under' (game level)
def nfl_angles(L):
    fav = L["line"] > 0
    return {
        "Division home dog": (L["is_home"] & (L["line"] < 0) & (L["div"] == 1), "spread", "team",
                              "Division rivals see each other twice a year; familiarity keeps games close and home "
                              "underdogs get points they don't need.",
                              lambda r: f"{r.name} is a {-r.line:g}-pt home underdog to a division rival."),
        "Off the bye": (L["bye_edge"] & (L["playoff"] == 0), "spread", "team",
                        "An extra week to heal and game-plan, against an opponent that played last week.",
                        lambda r: f"{r.name} is coming off its bye; {r.opp_name} is not."),
        "Short-week road fade": (L["short_vs_rested"] & L["is_away"], "spread", "opp",
                                 "Road team on a short week (Thursday game) against a rested opponent: less prep, "
                                 "travel on top of it.",
                                 lambda r: f"{r.name} is on the road on a short week against a rested {r.opp_name}."),
        "West-coast early kickoff": (L["west_early"], "spread", "team",
                                     "West-coast team at a 1pm ET kickoff (10am body clock). Everyone 'knows' they "
                                     "struggle, so the line over-adjusts. We tested the fade first and it lost badly; "
                                     "backing them is the side that wins.",
                                     lambda r: f"{r.name} plays a 10am body-clock kickoff in the East."),
        "Backup QB fade": (L["qb_change"] <= -3, "spread", "opp",
                           "A downgrade at QB worth 3+ points by our QB ratings; lines often move less than the "
                           "drop-off.",
                           lambda r: f"{r.name}'s projected starter rates about {-r.qb_change:.1f} pts worse than "
                                     f"their usual QB."),
        "Bounce-back": (L["prev_margin"] <= -17, "spread", "team",
                        "The market overreacts to one ugly loss; NFL teams are more even than one score says.",
                        lambda r: f"{r.name} lost by {-r.prev_margin:.0f} last week."),
        "Upset letdown": ((L["prev_line"] <= -6) & (L["prev_margin"] > 0), "spread", "opp",
                          "Teams that just won outright as big dogs get over-rated the next week.",
                          lambda r: f"{r.name} won outright as a {-r.prev_line:g}-pt underdog last week."),
        "Revenge": ((L["last_meet_margin"] <= -10) & (L["last_meet_days"] <= 400), "spread", "team",
                    "Lost the last meeting badly; motivation plus a line shaded by the last result.",
                    lambda r: f"{r.name} lost the last meeting with {r.opp_name} by {-r.last_meet_margin:.0f}."),
        "Lookahead": (fav & (L["line"] >= 6) & (L["next_opp_rating"] >= L["opp_rating"] + 6), "spread", "opp",
                      "Big favorite with a much bigger game next week (sandwich spot).",
                      lambda r: f"{r.name} is a {r.line:g}-pt favorite with a much tougher opponent next week."),
        "Primetime under": (L["prime"] == 1, "total", "under",
                            "Primetime games draw public Over money and extra prep time for defenses.",
                            lambda r: "Primetime game."),
        "Division under (late season)": ((L["div"] == 1) & (L["week"] >= 10) & (L["playoff"] == 0), "total", "under",
                                         "Second meeting between division rivals in the back half of the season: "
                                         "defenses know the plays, weather turns.",
                                         lambda r: f"Division game in week {r.week}."),
        "Cold-weather under": ((L["dome"] == 0) & (L["cold"] >= 8), "total", "under",
                               "Kickoff below 32°F: ball harder to throw and kick.",
                               lambda r: "Sub-freezing kickoff forecast."),
    }


def cfb_angles(L):
    fav = L["line"] > 0
    acad = L["name"].isin(ACADEMIES)
    opp_acad = L["opp_name"].isin(ACADEMIES)
    return {
        "Service academy under": (acad | opp_acad, "total", "under",
                                  "Army, Navy and Air Force run the ball on almost every down, which keeps the clock "
                                  "moving and shortens the game.",
                                  lambda r: f"{r.name if r.name in ACADEMIES else r.opp_name} runs its option offense."),
        "Service academy dog": (acad & (L["line"] < 0), "spread", "team",
                                "The same clock-draining offense keeps the academies close as underdogs: fewer "
                                "possessions means fewer chances for the favorite to pull away.",
                                lambda r: f"{r.name} is a {-r.line:g}-pt underdog with a clock-killing offense."),
        "Conference home dog": (L["is_home"] & (L["line"] < 0) & (L["conf"] == 1), "spread", "team",
                                "Conference opponents know each other; home dogs in league play get extra points.",
                                lambda r: f"{r.name} is a {-r.line:g}-pt home underdog in conference play."),
        "Big road favorite fade": (L["is_away"] & (L["line"] >= 14) & (L["conf"] == 1), "spread", "opp",
                                   "Laying two touchdowns on the road in conference play asks a lot.",
                                   lambda r: f"{r.name} is laying {r.line:g} on the road in a conference game."),
        "Rest edge": ((L["rest_edge"] >= 3) & (L["line_move"] >= 3) & L["is_home"], "spread", "team",
                      "Home team with 3+ more days of rest, and the line has moved 3+ points its way.",
                      lambda r: f"{r.name} has {r.rest_edge:.0f} more days of rest; line moved {r.line_move:.1f} its way."),
        "Bounce-back": (L["prev_margin"] <= -24, "spread", "team",
                        "Blowout losses inflate the next line.",
                        lambda r: f"{r.name} lost by {-r.prev_margin:.0f} last game."),
        "Upset letdown": ((L["prev_line"] <= -10) & (L["prev_margin"] > 0), "spread", "opp",
                          "A double-digit dog that won outright gets over-rated next week.",
                          lambda r: f"{r.name} won outright as a {-r.prev_line:g}-pt dog last game."),
        "Blowout fade": ((L["prev_margin"] >= 35) & (L["prev_opp_fcs"] != True), "spread", "opp",  # noqa: E712
                         "A 35-point win over an FBS team inflates the next number.",
                         lambda r: f"{r.name} won by {r.prev_margin:.0f} last game."),
        "Revenge": ((L["last_meet_margin"] <= -17) & (L["last_meet_days"] <= 400), "spread", "team",
                    "Lost the last meeting by 17+.",
                    lambda r: f"{r.name} lost the last meeting by {-r.last_meet_margin:.0f}."),
        "Lookahead": (fav & (L["line"] >= 10) & (L["next_opp_rating"] >= L["opp_rating"] + 10), "spread", "opp",
                      "Big favorite with a much tougher game next week.",
                      lambda r: f"{r.name} is laying {r.line:g} with a much tougher opponent next."),
        "Huge total under": (L["total_line"] >= 65, "total", "under",
                             "Totals of 65+ price in a shootout; the market leans too hard into it.",
                             lambda r: f"Total of {r.total_line:g}."),
    }


ANGLES = {"nfl": nfl_angles, "cfb": cfb_angles}


# ------------------------------------------------------------------ grading
def bets_for(L, mask, market, side):
    x = L[mask.fillna(False).values].copy()
    if market == "spread":
        x = x[x["line"].notna()]
        x["bet_side"] = np.where(side == "team", x["side"], np.where(x["side"] == "home", "away", "home"))
        both = x.groupby("game_id")["bet_side"].nunique()
        x = x[x["game_id"].isin(both[both == 1].index)].drop_duplicates("game_id")
        sgn = 1 if side == "team" else -1
        cover = sgn * (x["margin"] - x["line"])
        odds = x["odds"] if side == "team" else x["opp_odds"]
    else:
        x = x[x["total_line"].notna()].drop_duplicates("game_id")
        x["bet_side"] = side
        cover = (x["total"] - x["total_line"]) * (1 if side == "over" else -1)
        odds = x["over_odds"] if side == "over" else x["under_odds"]
    x["units"] = np.where(cover > 0, payout(odds.values), np.where(cover < 0, -1.0, 0.0))
    x.loc[cover.isna().values, "units"] = np.nan
    return x


def summary(b):
    d = b[b["units"].notna() & (b["season"] >= FIRST)]
    u = d["units"]
    per = d[d["season"] <= LAST].groupby("season")["units"].sum()
    t = float(u.mean() / (u.std() / np.sqrt(len(u)))) if len(u) > 2 and u.std() > 0 else 0.0
    rec = lambda s: f"{(s > 0).sum()}-{(s < 0).sum()}-{(s == 0).sum()}"  # noqa: E731
    r19, r25 = d[d["season"] >= 2019]["units"], d[d["season"] >= 2025]["units"]
    return {"bets": int(len(u)), "record": rec(u), "roi%": round(100 * u.mean(), 1) if len(u) else 0.0, "t": round(t, 2),
            "up": f"{int((per > 0).sum())}/{len(per)}", "roi_2019%": round(100 * r19.mean(), 1) if len(r19) else 0.0,
            "recent_record": rec(r25), "recent_roi%": round(100 * r25.mean(), 1) if len(r25) else 0.0,
            "win%": round(100 * (u > 0).sum() / max(((u > 0) | (u < 0)).sum(), 1), 1)}


STACK_MIN_ROI, STACK_MIN_N = 5.0, 75


def grade(s):
    if s["t"] >= 2.3:
        return "Strong"
    if s["t"] >= 1.5 and s["recent_roi%"] >= -5:
        return "Moderate"
    if s["t"] >= 1.0 and s["recent_roi%"] > 0:
        return "Weak"
    return None


def model_sides(sport, df):
    path = os.path.join(HERE, "data", "backtest_bets.csv" if sport == "nfl" else os.path.join("cfb", "backtest_bets.csv"))
    if not os.path.exists(path):
        return {}
    b = pd.read_csv(path)
    homes = df.set_index("game_id")["home"].astype(str)
    out = {}
    for m in ("spread", "total"):
        x = b[b["market"] == m].sort_values("ev").groupby("game_id").tail(1)
        for gid, lab in zip(x["game_id"], x["bet"]):
            lab = str(lab)
            if m == "total":
                out[(gid, m)] = "over" if lab.startswith("Over") else "under"
            elif gid in homes.index:
                out[(gid, m)] = "home" if lab.startswith(homes[gid] + " ") else "away"
    return out


def build(sport):
    if sport == "nfl":
        import features as F
        df = F.build()
    else:
        import cfb_features as C
        df = C.build()
    df = df[df["season"] >= FIRST - 1].reset_index(drop=True)
    return df, long_form(df, sport)


def evaluate(sport, df=None, L=None):
    if L is None:
        df, L = build(sport)
    ms = model_sides(sport, df)
    res = {}
    for name, (mask, market, side, why, detail) in ANGLES[sport](L).items():
        b = bets_for(L, mask, market, side)
        s = summary(b)
        agree = [(ms.get((g, market)) == bs, u) for g, bs, u, sea in zip(b["game_id"], b["bet_side"], b["units"], b["season"])
                 if (g, market) in ms and pd.notna(u) and sea >= 2014]
        a = pd.DataFrame(agree, columns=["agree", "u"]) if agree else pd.DataFrame(columns=["agree", "u"])
        with_m = a[a["agree"] == True]["u"]  # noqa: E712
        res[name] = {"market": market, "side": side, "why": why, "detail": detail, "summary": s, "grade": grade(s),
                     "with_model": (round(100 * with_m.mean(), 1), int(len(with_m))) if len(with_m) else (None, 0),
                     "bets": b}
    return df, L, res


def report(sport):
    _df, _L, res = evaluate(sport)
    rows = [{"angle": k, "mkt": v["market"], **v["summary"], "w/ model": f"{v['with_model'][0]:+}% ({v['with_model'][1]})"
             if v["with_model"][1] else "", "grade": v["grade"] or "-"} for k, v in res.items()]
    print(f"\n==== {sport.upper()} situational angles vs the closing number, {FIRST}-2026 ====")
    print(pd.DataFrame(rows).to_string(index=False))
    return res


def live(sport, season, week, res=None, L=None):
    """This week's triggered angles (only graded ones), with game-specific backup."""
    if res is None:
        _df, L, res = evaluate(sport)
    out = []
    for name, a in res.items():
        roi_m, n_m = a["with_model"]
        stack_only = not a["grade"] and roi_m is not None and roi_m >= STACK_MIN_ROI and n_m >= STACK_MIN_N
        if not a["grade"] and not stack_only:
            continue
        b = a["bets"]
        now = b[(b["season"] == season) & (b["week"] == week) & b["units"].isna()]
        for r in now.itertuples(index=False):
            out.append({"angle": name, "grade": a["grade"] or "Stack only", "stack_only": stack_only,
                        "market": a["market"], "game_id": r.game_id,
                        "bet_side": r.bet_side, "home": r.name if r.side == "home" else r.opp_name,
                        "away": r.opp_name if r.side == "home" else r.name, "why": a["why"], "detail": a["detail"](r),
                        "summary": a["summary"], "with_model": a["with_model"]})
    return out


if __name__ == "__main__":
    for sp in (sys.argv[1:] or ["nfl", "cfb"]):
        report(sp)
