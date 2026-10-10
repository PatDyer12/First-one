#!/usr/bin/env python3
"""College football systems lab: weather, underdog, big dog, blowout, edge, trend, stats-only, season-phase,
rankings, records, head-to-head and unit-vs-unit matchup systems.

Every system is a written rule with a reason it should work, graded on 2011-2026 closing lines at -110 (college
history has no prices), with separate splits for the early season (weeks 0-4), MID-SEASON (weeks 5-9) and late
season (10+), so you can see which ones get stronger once conference play starts.

Grades (about 55 rules are tested, so a t of 2 can happen by luck; the card also wants a reason up front):
  Strong    t >= 2.5
  Moderate  t >= 1.5 and not falling apart in 2025-26
  Weak      t >= 1.0 and profitable in 2025-26
  Mid-season pick: profitable weeks 5-9 with t >= 1.5 there, and not losing 5%+ in weeks 3-4 and 10-11 next to it

Usage: python3 betting/cfb_lab.py            report + this week's plays
"""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cfb_features as C  # noqa: E402

FIRST = 2011


def _dog(df):
    return pd.Series(np.where(df["spread_line"] > 0, "away", "home"), index=df.index)


def _const(v):
    return lambda df: pd.Series(v, index=df.index)


def _toward_stat_side(df):
    return pd.Series(np.where(df["stat_edge_spread"] > 0, "home", "away"), index=df.index)


def _toward_stat_total(df):
    return pd.Series(np.where(df["stat_edge_total"] > 0, "over", "under"), index=df.index)


def _fade_hot(df):
    return pd.Series(np.where(df["h_cov3"] == 3, "away", np.where(df["a_cov3"] == 3, "home", None)), index=df.index)


def _back_cold(df):
    return pd.Series(np.where(df["h_ats3_lost"] == 3, "home", np.where(df["a_ats3_lost"] == 3, "away", None)), index=df.index)


def team_rule(cond, back=True):
    """A rule about one team -> (side, filter). cond(d, s, o) is true when team s (h/a) qualifies against o.
    Bets on that team (back=True) or against it; games where both teams qualify are skipped."""
    def both(d):
        return cond(d, "h", "a").fillna(False).astype(bool), cond(d, "a", "h").fillna(False).astype(bool)

    def side(d):
        h, a = both(d)
        pick_h = h if back else a
        return pd.Series(np.where(pick_h, "home", "away"), index=d.index)

    def mask(d):
        h, a = both(d)
        return h ^ a
    return side, mask


def fav(d, s):
    return d["spread_line"] > 0 if s == "h" else d["spread_line"] < 0


def dog(d, s):
    return d["spread_line"] < 0 if s == "h" else d["spread_line"] > 0


def wpct(d, s):
    return d[f"{s}_w"] / (d[f"{s}_w"] + d[f"{s}_l"]).where(lambda x: x > 0)


def eliminated(d, s):  # can't reach 6 wins even by winning out (regular season)
    return (d[f"{s}_w"] + d[f"{s}_rem"] + 1 < 6) & (d["postseason"] == 0)


ACADEMIES = {349, 2426, 2005}  # Army, Navy, Air Force (ESPN ids)
FBS2 = lambda d: (d["h_fbs"] == 1) & (d["a_fbs"] == 1)  # noqa: E731
A = lambda df: df["spread_line"].abs()  # noqa: E731
OUT = lambda df: df["indoor"] == 0  # noqa: E731
MID = lambda df: df["week"].between(5, 9) & (df["postseason"] == 0)  # noqa: E731

# name: (category, market, side(df), filter(df), why)
SYSTEMS = {
    "Wind under (15+ mph at kickoff)": ("Weather", "total", _const("under"), lambda d: OUT(d) & (d["wind"] >= 15),
                                        "15+ mph wind at kickoff: passing and kicking suffer, totals don't drop enough."),
    "Wind under (12+ mph at kickoff)": ("Weather", "total", _const("under"), lambda d: OUT(d) & (d["wind"] >= 12),
                                        "Same idea at a lower wind threshold."),
    "Steady wind under (15+ mph for 8 hrs)": ("Weather", "total", _const("under"), lambda d: OUT(d) & (d["wind8"] >= 15),
                                              "Wind averaging 15+ mph from 3 hours before kickoff to 4 after: the all-day "
                                              "wind a forecast catches, not a gust at kickoff."),
    "Cold under (35°F or colder)": ("Weather", "total", _const("under"), lambda d: OUT(d) & (d["temp"] <= 35),
                                    "Freezing kickoffs: hard to throw, catch and kick."),
    "Rain under (1 mm+ at kickoff)": ("Weather", "total", _const("under"), lambda d: OUT(d) & (d["precip"] >= 1.0),
                                      "Measurable rain around kickoff: fumbles, short passing, more running."),
    "Steady rain under (3+ wet hours)": ("Weather", "total", _const("under"), lambda d: OUT(d) & (d["wet8"] >= 3),
                                         "Rain in at least 3 of the 8 hours around the game: a wet day a forecast sees "
                                         "coming, not a passing shower."),
    "Wind dog (15+ mph)": ("Weather", "spread", _dog, lambda d: OUT(d) & (d["wind"] >= 15) & (A(d) >= 3),
                           "Wind lowers scoring, and fewer points make big margins harder: take the points."),
    "Conference dog (7-17)": ("Underdog", "spread", _dog, lambda d: (d["conf"] == 1) & A(d).between(7, 17),
                              "League opponents know each other; mid-size conference spreads are often too wide."),
    "Mid-season conference road dog": ("Underdog", "spread", _dog,
                                       lambda d: (d["conf"] == 1) & MID(d) & (d["spread_line"] > 0) & A(d).between(3, 14),
                                       "Road dogs in league play once conference season is underway."),
    "Big dog (21+, FBS vs FBS)": ("Big dog", "spread", _dog, lambda d: (d["div_diff"] == 0) & (A(d) >= 21),
                                  "Favorites ease off with big leads; backdoor covers come late."),
    "Big dog, low total": ("Big dog", "spread", _dog, lambda d: (A(d) >= 17) & (d["total_line"] <= 50),
                           "A big spread with a low total: few possessions to build the margin."),
    "Blowout over (30+)": ("Blowout", "total", _const("over"), lambda d: A(d) > 30,
                           "Huge mismatches: the underdog scores more than the market expects."),
    "Fade hot ATS team (covered 3 straight)": ("Trend", "spread", _fade_hot,
                                               lambda d: ((d["h_cov3"] == 3) ^ (d["a_cov3"] == 3)),
                                               "Three straight covers inflate a team's line."),
    "Back cold ATS team (failed 3 straight)": ("Trend", "spread", _back_cold,
                                               lambda d: ((d["h_ats3_lost"] == 3) ^ (d["a_ats3_lost"] == 3)),
                                               "Three straight non-covers deflate a team's line."),
    "Over-streak fade": ("Trend", "total", _const("under"), lambda d: (d["h_over3"] + d["a_over3"]) >= 5,
                         "Both teams have been going over: the total is inflated by recent shootouts."),
    "Stats model side (7+ pts off)": ("Stats-only", "spread", _toward_stat_side, lambda d: d["stat_edge_spread"].abs() >= 7,
                                      "Offense/defense numbers alone disagree with the line by 7+ points."),
    "Stats model side (10+ pts off)": ("Stats-only", "spread", _toward_stat_side, lambda d: d["stat_edge_spread"].abs() >= 10,
                                       "The same, at a 10-point disagreement."),
    "Stats model total (7+ pts off)": ("Stats-only", "total", _toward_stat_total, lambda d: d["stat_edge_total"].abs() >= 7,
                                       "Offense/defense numbers and pace alone disagree with the total by 7+ points."),
    "Conference-play under (wk 5-9)": ("Season phase", "total", _const("under"), lambda d: (d["conf"] == 1) & MID(d),
                                       "Familiar league opponents, defenses settle in by mid-season."),
    "Early-season over (wk 0-3)": ("Season phase", "total", _const("over"), lambda d: (d["week"] <= 3) & (d["postseason"] == 0),
                                   "Early totals lean on last year; new offenses outrun them."),
    "November under (wk 10+)": ("Season phase", "total", _const("under"), lambda d: (d["week"] >= 10) & (d["postseason"] == 0),
                                "Late-season weather and tired legs."),
}

# rankings, records, head-to-head and unit-vs-unit matchups (added after the first lab)
R = lambda d, s: d[f"{s}_rank"]  # noqa: E731
NEW = {
    # rankings (AP poll, or the CFP ranking once it's out: what the public sees on TV)
    "Unranked home dog vs ranked team": ("Rankings", "spread",
        *team_rule(lambda d, s, o: (s == "h") & R(d, s).isna() & R(d, o).notna() & dog(d, s) & (A(d) <= 21)),
        "The public bets the ranked name on the road; the unranked home team gets extra points."),
    "Ranked vs ranked: take the points": ("Rankings", "spread", _dog,
        lambda d: R(d, "h").notna() & R(d, "a").notna() & (A(d) >= 3),
        "Top-25 matchups are closer than the line: both teams are good, and the favorite is the public side."),
    "Ranked team laying 14+ to unranked conference foe": ("Rankings", "spread",
        *team_rule(lambda d, s, o: R(d, s).notna() & R(d, o).isna() & fav(d, s) & (A(d) >= 14) & (d["conf"] == 1),
                   back=False),
        "League opponents know the ranked team well; big conference spreads on poll teams are inflated."),
    "Top-10 team getting points": ("Rankings", "spread",
        *team_rule(lambda d, s, o: (R(d, s) <= 10) & dog(d, s)),
        "An elite team is rarely an underdog; when it is, the market may be overreacting."),
    "Newly ranked team: fade": ("Rankings", "spread",
        *team_rule(lambda d, s, o: R(d, s).notna() & d[f"{s}_prev_rank"].isna() & (d[f"{s}_played"] >= 2)
                   & R(d, o).isna(), back=False),
        "A team that just entered the poll gets a bump in public attention and in the price."),
    "Ranked team off a loss: back": ("Rankings", "spread",
        *team_rule(lambda d, s, o: R(d, s).notna() & (d[f"{s}_last_margin"] < 0)),
        "A good team that just lost gets marked down too far by the market."),
    "Upset winner (beat a ranked team unranked): fade": ("Rankings", "spread",
        *team_rule(lambda d, s, o: (d[f"{s}_last_margin"] > 0) & d[f"{s}_last_opp_rank"].notna()
                   & d[f"{s}_prev_rank"].isna() & (d["postseason"] == 0), back=False),
        "Letdown after the biggest win of the season, and the price goes up after a headline upset."),
    "Poll overrates (market ranks them 10+ spots lower): fade": ("Rankings", "spread",
        *team_rule(lambda d, s, o: R(d, s).notna() & (d[f"{s}_mkt_rank"] - R(d, s) >= 10), back=False),
        "Polls reward records; the betting market rates teams on strength. Bet against poll teams the market doesn't believe in."),
    "Unranked but market top-20 vs ranked team: back": ("Rankings", "spread",
        *team_rule(lambda d, s, o: R(d, s).isna() & (d[f"{s}_mkt_rank"] <= 20) & R(d, o).notna()),
        "A strong team the poll ignores (early losses), facing a ranked team the public prefers."),
    "Fell out of the poll: back": ("Rankings", "spread",
        *team_rule(lambda d, s, o: R(d, s).isna() & d[f"{s}_prev_rank"].notna() & (d["postseason"] == 0)),
        "Dropping out of the top 25 is a public-perception hit bigger than the actual drop in strength."),
    # records
    "Undefeated favorite (5-0+): fade": ("Records", "spread",
        *team_rule(lambda d, s, o: (d[f"{s}_w"] >= 5) & (d[f"{s}_l"] == 0) & fav(d, s) & (d[f"{o}_l"] >= 1), back=False),
        "The public loves unbeaten teams; their lines carry a premium."),
    "Winless underdog (0-3 or worse): back": ("Records", "spread",
        *team_rule(lambda d, s, o: (d[f"{s}_w"] == 0) & (d[f"{s}_l"] >= 3) & dog(d, s) & FBS2(d)),
        "Nobody wants to bet a winless team, so the number gets too big."),
    "Worse record but favored: back the favorite": ("Records", "spread",
        *team_rule(lambda d, s, o: fav(d, s) & (d[f"{s}_played"] >= 4) & (d[f"{o}_played"] >= 4)
                   & (wpct(d, s) <= wpct(d, o) - 0.25)),
        "When the line favors the team with the worse record, the market knows something the standings don't."),
    "Win streak (4+) vs losing streak (3+): back the losing team": ("Records", "spread",
        *team_rule(lambda d, s, o: (d[f"{s}_streak"] <= -3) & (d[f"{o}_streak"] >= 4)),
        "Straight-up streaks shape public opinion more than they predict the next game."),
    "Bowl push: 5-win team vs eliminated team (wk 9+)": ("Records", "spread",
        *team_rule(lambda d, s, o: (d[f"{s}_w"] == 5) & (d["week"] >= 9) & eliminated(d, o) & ~eliminated(d, s)),
        "One win from bowl eligibility against a team with nothing left to play for."),
    "Eliminated team favored: fade": ("Records", "spread",
        *team_rule(lambda d, s, o: eliminated(d, s) & fav(d, s) & (d["week"] >= 8), back=False),
        "A team that can't make a bowl has little to play for late in the season."),
    "Last year's 10-win team, early-season favorite: fade": ("Records", "spread",
        *team_rule(lambda d, s, o: (d[f"{s}_last_wpct"] >= 0.75) & fav(d, s) & (d["week"] <= 3) & (d["postseason"] == 0),
                   back=False),
        "Early lines lean on last season; graduation and transfers aren't priced in yet."),
    "Last year's bad team, early-season dog: back": ("Records", "spread",
        *team_rule(lambda d, s, o: (d[f"{s}_last_wpct"] <= 0.34) & dog(d, s) & (d["week"] <= 3) & (d["postseason"] == 0)),
        "The mirror image: last year's losers get too many points before anyone has seen this year's team."),
    # head-to-head
    "Revenge: lost last year's meeting by 14+": ("Head-to-head", "spread",
        *team_rule(lambda d, s, o: (d["h2h_ago"] == 1) & ((d["h2h_margin"] if s == "h" else -d["h2h_margin"]) <= -14)),
        "Players and coaches remember a beating; the market prices last year's score in the line."),
    "Blowout rematch: won last year by 28+, favored by 14+ again: fade": ("Head-to-head", "spread",
        *team_rule(lambda d, s, o: (d["h2h_ago"] == 1) & ((d["h2h_margin"] if s == "h" else -d["h2h_margin"]) >= 28)
                   & fav(d, s) & (A(d) >= 14), back=False),
        "Last year's blowout inflates this year's spread."),
    "Rivalry dog (met 9+ of the last 10 years)": ("Head-to-head", "spread", _dog,
        lambda d: (d["h2h_n10"] >= 9) & (A(d) >= 7),
        "Rivals play each other close regardless of the records: take the points."),
    "Rivalry-week dog (last regular-season game)": ("Head-to-head", "spread", _dog,
        lambda d: (d["h2h_n10"] >= 9) & (d["h_rem"] == 0) & (d["a_rem"] == 0) & (d["postseason"] == 0) & (A(d) >= 3),
        "Season-ending rivalry games: the underdog's whole season is this game."),
    # unit-vs-unit matchups (percentiles among FBS teams that week)
    "Run-game mismatch: back the team that runs on a bad run D": ("Matchup", "spread",
        *team_rule(lambda d, s, o: (d[f"{s}_off_rush_epa_pct"] >= 0.8) & (d[f"{o}_def_rush_epa_pct"] <= 0.2) & FBS2(d)),
        "A top-20% rushing offense against a bottom-20% run defense: the matchup may matter more than overall ratings."),
    "Pass-game mismatch: back the team that throws on a bad pass D": ("Matchup", "spread",
        *team_rule(lambda d, s, o: (d[f"{s}_off_pass_epa_pct"] >= 0.8) & (d[f"{o}_def_pass_epa_pct"] <= 0.2) & FBS2(d)),
        "A top-20% passing offense against a bottom-20% pass defense."),
    "Elite defense vs elite offense: back the defense": ("Matchup", "spread",
        *team_rule(lambda d, s, o: (d[f"{s}_def_epa_pct"] >= 0.85) & (d[f"{o}_off_epa_pct"] >= 0.85)
                   & (d[f"{s}_off_epa_pct"] < 0.85) & (d[f"{o}_def_epa_pct"] < 0.85) & FBS2(d)),
        "\"Defense travels\": when a top defense meets a top offense, the defense side is underpriced."),
    "Elite defense vs elite offense: under": ("Matchup", "total", _const("under"),
        lambda d: FBS2(d) & (((d["h_def_epa_pct"] >= 0.85) & (d["a_off_epa_pct"] >= 0.85))
                             | ((d["a_def_epa_pct"] >= 0.85) & (d["h_off_epa_pct"] >= 0.85))),
        "The total leans on the great offense's numbers; the great defense slows it."),
    "Two slow teams: under": ("Matchup", "total", _const("under"),
        lambda d: (d["h_pace_pct"] <= 0.25) & (d["a_pace_pct"] <= 0.25) & FBS2(d),
        "Both teams in the slowest quarter of FBS: fewer plays than the total assumes."),
    "Two fast teams: over": ("Matchup", "total", _const("over"),
        lambda d: (d["h_pace_pct"] >= 0.75) & (d["a_pace_pct"] >= 0.75) & FBS2(d),
        "Both teams in the fastest quarter of FBS: more plays, more points."),
    "Line disagrees with the poll: back the market's favorite": ("Rankings", "spread",
        *team_rule(lambda d, s, o: fav(d, s) & (A(d) >= 1) & R(d, o).notna() & (R(d, s).isna() | (R(d, s) > R(d, o)))),
        "The poll is public opinion, the line is money. When the lower-ranked (or unranked) team is favored, the public "
        "is on the ranked underdog and the favorite carries value."),
    "Look-ahead: ranked favorite with a ranked opponent next": ("Rankings", "spread",
        *team_rule(lambda d, s, o: R(d, s).notna() & fav(d, s) & (A(d) >= 7) & R(d, o).isna()
                   & d[f"{s}_next_opp_rank"].notna(), back=False),
        "A ranked team with a big game next week, laying points to an unranked team this week."),
    "Sandwich: unranked foe between two ranked opponents": ("Rankings", "spread",
        *team_rule(lambda d, s, o: fav(d, s) & R(d, o).isna() & d[f"{s}_last_opp_rank"].notna()
                   & d[f"{s}_next_opp_rank"].notna() & (d["postseason"] == 0), back=False),
        "Coming off a big game and heading into another: the classic flat spot."),
    "Night home dog vs ranked team": ("Rankings", "spread",
        *team_rule(lambda d, s, o: (s == "h") & (d["hfa"] == 1) & dog(d, s) & R(d, o).notna() & R(d, s).isna()
                   & (d["kick_et"] >= 19)),
        "Home crowds are loudest at night; the ranked visitor walks into the hardest version of the trip."),
    "Service academy under": ("Matchup", "total", _const("under"),
        lambda d: d["home_id"].isin(ACADEMIES) | d["away_id"].isin(ACADEMIES),
        "Army, Navy and Air Force run the ball and the clock: few possessions."),
}
SYSTEMS.update(NEW)


def payout(o):
    o = np.asarray(o, dtype=float)
    o = np.where(np.isnan(o), -110.0, o)
    return np.where(o > 0, o / 100, 100 / np.abs(o))


def bets(df, market, side_fn, mask_fn):
    m = mask_fn(df).fillna(False).astype(bool)
    x = df[m & (df["spread_line"].notna() if market == "spread" else df["total_line"].notna())].copy()
    x["side"] = side_fn(x)
    x = x[x["side"].notna()]
    if market == "spread":
        cover = (x["result"] - x["spread_line"]) * np.where(x["side"] == "home", 1, -1)
        odds = np.where(x["side"] == "home", x["home_spread_odds"], x["away_spread_odds"])
    else:
        cover = (x["total"] - x["total_line"]) * np.where(x["side"] == "over", 1, -1)
        odds = np.where(x["side"] == "over", x["over_odds"], x["under_odds"])
    x["units"] = np.where(cover > 0, payout(odds), np.where(cover < 0, -1.0, 0.0))
    x.loc[cover.isna().values, "units"] = np.nan
    return x


def tstat(u):
    return float(u.mean() / (u.std() / np.sqrt(len(u)))) if len(u) > 2 and u.std() > 0 else 0.0


def summarize(x):
    d = x[x["units"].notna() & (x["season"] >= FIRST)]
    u = d["units"]
    rec = lambda s: f"{(s > 0).sum()}-{(s < 0).sum()}-{(s == 0).sum()}"  # noqa: E731
    per = d[d["season"] <= 2025].groupby("season")["units"].sum()
    phase = {}
    for name, sel in (("early", d["week"] <= 4), ("mid", d["week"].between(5, 9)), ("late", d["week"] >= 10)):
        s = d[sel & (d["postseason"] == 0)]["units"]
        phase[name] = {"bets": int(len(s)), "roi%": round(100 * s.mean(), 1) if len(s) else 0.0, "t": round(tstat(s), 2)}
    edge = d[(d["week"].between(3, 4) | d["week"].between(10, 11)) & (d["postseason"] == 0)]["units"]
    phase["edges"] = {"bets": int(len(edge)), "roi%": round(100 * edge.mean(), 1) if len(edge) else 0.0}
    r19, r25 = d[d["season"] >= 2019]["units"], d[d["season"] >= 2025]["units"]
    first = d[d["season"] <= 2018]["units"]
    return {"bets": int(len(u)), "record": rec(u), "roi%": round(100 * u.mean(), 1) if len(u) else 0.0,
            "t": round(tstat(u), 2), "up": f"{int((per > 0).sum())}/{len(per)}",
            "roi_2019%": round(100 * r19.mean(), 1) if len(r19) else 0.0, "recent": rec(r25),
            "roi_2011_18%": round(100 * first.mean(), 1) if len(first) else 0.0,
            "recent_roi%": round(100 * r25.mean(), 1) if len(r25) else 0.0, "phase": phase}


def grade(s):
    g = None
    if s["t"] >= 2.5:
        g = "Strong"
    elif s["t"] >= 1.5 and s["recent_roi%"] >= -5:
        g = "Moderate"
    elif s["t"] >= 1.0 and s["recent_roi%"] > 0:
        g = "Weak"
    mid, edges = s["phase"]["mid"], s["phase"]["edges"]
    # a real mid-season effect should still be there in weeks 3-4 and 10-11, not flip sign right outside the window
    if g is None and mid["t"] >= 1.5 and mid["roi%"] > 0 and s["recent_roi%"] > -5 and edges["roi%"] > -5:
        g = "Mid-season only"
    return g


def edge_system(df):
    """The prediction model's own picks (walk-forward backtest, 2014+) at 3% and 5% edge."""
    path = os.path.join(HERE, "data", "cfb", "backtest_bets.csv")
    if not os.path.exists(path):
        return {}
    b = pd.read_csv(path)
    b = b[b["market"].isin(["spread", "total"])].sort_values("ev").groupby(["game_id", "market"]).tail(1)
    b = b.drop(columns=[c for c in ("week", "postseason") if c in b.columns])
    b = b.merge(df[["game_id", "week", "postseason"]], on="game_id", how="inner")
    out = {}
    for thr in (0.03, 0.05):
        for m in ("spread", "total"):
            x = b[(b["market"] == m) & (b["ev"] > thr)].copy()
            out[f"Model edge {m} ({int(thr * 100)}%+)"] = ("Edge", m, x)
    return out


def run(verbose=True):
    df = C.build()
    df = df[df["season"] >= FIRST - 1].reset_index(drop=True)
    res = {}
    for name, (cat, market, side_fn, mask_fn, why) in SYSTEMS.items():
        x = bets(df, market, side_fn, mask_fn)
        s = summarize(x)
        res[name] = {"category": cat, "market": market, "why": why, "summary": s, "grade": grade(s),
                     "bets": x, "side_fn": side_fn, "mask_fn": mask_fn}
    for name, (cat, market, x) in edge_system(df).items():
        s = summarize(x)
        res[name] = {"category": cat, "market": market, "why": "Our prediction model's edge vs the line (walk-forward).",
                     "summary": s, "grade": grade(s), "bets": x}
    if verbose:
        rows = []
        for k, v in res.items():
            s = v["summary"]
            rows.append({"system": k, "cat": v["category"], "bets": s["bets"], "record": s["record"], "roi%": s["roi%"],
                         "t": s["t"], "up": s["up"], "11-18": s["roi_2011_18%"], "2019+": s["roi_2019%"],
                         "2025-26": f"{s['recent']} ({s['recent_roi%']:+})",
                         "mid wk5-9": f"{s['phase']['mid']['roi%']:+} ({s['phase']['mid']['bets']}, t {s['phase']['mid']['t']})",
                         "grade": v["grade"] or "-"})
        print(pd.DataFrame(rows).to_string(index=False))
    return df, res


def live(df, res, season=None, week=None):
    up = df[df["result"].isna() & (df["season"] == (season or df["season"].max()))]
    today = pd.Timestamp.now(tz="America/New_York").strftime("%Y-%m-%d")
    up = up[up["gameday"].astype(str).str[:10] >= today]
    if week is not None:
        up = up[up["week"] == week]
    else:
        up = up[up["week"] == up["week"].min()]
    out = []
    for name, v in res.items():
        if not v.get("grade") or "side_fn" not in v:
            continue
        m = v["mask_fn"](up).fillna(False).astype(bool)
        x = up[m]
        if x.empty:
            continue
        sides = v["side_fn"](x)
        for (_, r), side in zip(x.iterrows(), sides):
            if side is None:
                continue
            out.append({"system": name, "category": v["category"], "grade": v["grade"], "market": v["market"],
                        "side": side, "game": f"{r.away} @ {r.home}", "game_id": r.game_id, "spread_line": r.spread_line,
                        "total_line": r.total_line, "wind": r.wind, "temp": r.temp,
                        "stat_margin": r.stat_margin, "stat_total": r.stat_total, "week": r.week})
    return out


# lab systems that made the weekly card (cfb_model.py SYSTEMS), by lab name -> card name
ON_CARD = {"Blowout over (30+)": "Blowout over", "Steady wind under (15+ mph for 8 hrs)": "Steady wind under",
           "Steady rain under (3+ wet hours)": "Steady rain under", "Over-streak fade": "Over-streak fade"}


def save(res, plays):
    """Lab scoreboard for the Saturday Slate's Systems Lab panel: betting/data/cfb/lab.json."""
    out = []
    for name, v in res.items():
        s = v["summary"]
        out.append({"name": name, "category": v["category"], "market": v["market"], "why": v["why"],
                    "grade": v["grade"], "on_card": ON_CARD.get(name), "bets": s["bets"], "record": s["record"],
                    "roi": s["roi%"], "t": s["t"], "up": s["up"], "recent": s["recent"], "recent_roi": s["recent_roi%"],
                    "mid": s["phase"]["mid"], "live": sorted({p["game"] for p in plays if p["system"] == name})})
    with open(os.path.join(HERE, "data", "cfb", "lab.json"), "w") as f:
        json.dump(out, f, indent=1)


if __name__ == "__main__":
    d, r = run()
    plays = live(d, r)
    save(r, plays)
    print(f"\nThis week's qualifying plays (the card uses only: {', '.join(ON_CARD.values())}):")
    for (game, market, side), ps in pd.DataFrame(plays).groupby(["game", "market", "side"], sort=False) if plays else []:
        print(f"  {game} {market} {side}: " + " + ".join(f"{p.system} [{p.grade}]" for p in ps.itertuples()))
