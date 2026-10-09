#!/usr/bin/env python3
"""College football systems lab: weather, underdog, big dog, blowout, edge, trend, stats-only and season-phase systems.

Every system is a written rule with a reason it should work, graded on 2011-2026 closing lines at -110 (college
history has no prices), with separate splits for the early season (weeks 0-4), MID-SEASON (weeks 5-9) and late
season (10+), so you can see which ones get stronger once conference play starts.

Grades (about 20 rules are tested, so the bar is set for that):
  Strong    t >= 2.5
  Moderate  t >= 1.5 and not falling apart in 2025-26
  Weak      t >= 1.0 and profitable in 2025-26
  Mid-season pick: profitable weeks 5-9 with t >= 1.5 there

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
    r19, r25 = d[d["season"] >= 2019]["units"], d[d["season"] >= 2025]["units"]
    return {"bets": int(len(u)), "record": rec(u), "roi%": round(100 * u.mean(), 1) if len(u) else 0.0,
            "t": round(tstat(u), 2), "up": f"{int((per > 0).sum())}/{len(per)}",
            "roi_2019%": round(100 * r19.mean(), 1) if len(r19) else 0.0, "recent": rec(r25),
            "recent_roi%": round(100 * r25.mean(), 1) if len(r25) else 0.0, "phase": phase}


def grade(s):
    g = None
    if s["t"] >= 2.5:
        g = "Strong"
    elif s["t"] >= 1.5 and s["recent_roi%"] >= -5:
        g = "Moderate"
    elif s["t"] >= 1.0 and s["recent_roi%"] > 0:
        g = "Weak"
    mid = s["phase"]["mid"]
    if g is None and mid["t"] >= 1.5 and mid["roi%"] > 0 and s["recent_roi%"] > -5:
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
                         "t": s["t"], "up": s["up"], "2019+": s["roi_2019%"], "2025-26": f"{s['recent']} ({s['recent_roi%']:+})",
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
