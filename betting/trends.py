#!/usr/bin/env python3
"""Per-game trend panels for the NFL card v2: records, ATS / over-under, splits, form, ranks, streaks, head-to-head.

Context only: in our tests streaks and records by themselves did not predict the next game against the closing
line, so these never trigger a bet; they sit beside the bets that tested signals produced.
"""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
FIX = {"OAK": "LV", "SD": "LAC", "STL": "LA", "LAR": "LA"}


def team_log(g):
    """One row per team per completed game with straight-up, ATS and over/under outcomes."""
    g = g[g["result"].notna() & g["spread_line"].notna()].copy()
    rows = []
    for home in (True, False):
        sgn = 1 if home else -1
        x = pd.DataFrame({
            "game_id": g["game_id"], "season": g["season"], "week": g["week"], "gameday": g["gameday"],
            "team": (g["home_team"] if home else g["away_team"]).replace(FIX),
            "opp": (g["away_team"] if home else g["home_team"]).replace(FIX),
            "home": home, "pf": g["home_score"] if home else g["away_score"], "pa": g["away_score"] if home else g["home_score"],
            "margin": sgn * g["result"], "line": sgn * g["spread_line"], "total": g["total"], "total_line": g["total_line"]})
        rows.append(x)
    L = pd.concat(rows, ignore_index=True).sort_values(["gameday", "game_id"])
    L["su"] = np.sign(L["margin"])
    L["ats"] = np.sign(L["margin"] - L["line"])         # line > 0 means this team was favored by that much
    L["ou"] = np.sign(L["total"] - L["total_line"])
    L["fav"] = L["line"] > 0
    return L


def rec(s, labels=("W", "L", "P")):
    return f"{int((s > 0).sum())}-{int((s < 0).sum())}" + (f"-{int((s == 0).sum())}" if (s == 0).any() else "")


def streak(s, pos, neg):
    s = [v for v in s if v != 0]
    if not s:
        return None
    n = 1
    while n < len(s) and s[-n - 1] == s[-1]:
        n += 1
    return n, (pos if s[-1] > 0 else neg)


def ranks(season):
    """Offense / defense EPA per play ranks this season (1 = best), garbage time removed."""
    t = pd.read_csv(os.path.join(DATA, "team_games.csv"))
    t = t[t["season"] == season].copy()
    t["team"] = t["team"].replace(FIX)
    t["opp"] = t["opp"].replace(FIX)
    off = t.groupby("team").apply(lambda x: np.average(x["epa"], weights=x["plays"]), include_groups=False)
    dfn = t.groupby("opp").apply(lambda x: np.average(x["epa"], weights=x["plays"]), include_groups=False)
    return off.rank(ascending=False).astype(int).to_dict(), dfn.rank(ascending=True).astype(int).to_dict()


def game_panels(games_up):
    """Trend panel data for each upcoming game (dict keyed by game_id)."""
    g = pd.read_csv(os.path.join(DATA, "games.csv"), low_memory=False)
    L = team_log(g)
    season = int(g["season"].max())
    off_r, def_r = ranks(season)
    out = {}
    for r in games_up.itertuples():
        side = {}
        for team, opp, home in ((r.away_team, r.home_team, False), (r.home_team, r.away_team, True)):
            team, opp = FIX.get(team, team), FIX.get(opp, opp)
            x = L[(L["team"] == team) & (L["season"] == season)]
            spot = x[x["home"] == home]
            fav = r.spread_line < 0 if not home else r.spread_line > 0  # favored this week
            role = x[x["fav"] == fav]
            last3 = x.tail(3)
            streaks = []
            for col, pos, neg, label in (("su", "W", "L", "straight up"), ("ats", "covered", "failed to cover", "ATS"),
                                         ("ou", "over", "under", "totals")):
                st = streak(x[col].tolist(), pos, neg)
                if st and st[0] >= 3:
                    streaks.append(f"{st[0]} straight {st[1]}" + (f" ({label})" if col == "su" else ""))
            side["home" if home else "away"] = {
                "team": team, "record": rec(x["su"]), "ats": rec(x["ats"]),
                "ou": f"{int((x['ou'] > 0).sum())}-{int((x['ou'] < 0).sum())}",
                "last5": "".join("W" if v > 0 else "L" if v < 0 else "P" for v in x["ats"].tail(5)),
                "spot": f"{'home' if home else 'road'} {rec(spot['ats'])}",
                "role": f"as {'fav' if fav else 'dog'} {rec(role['ats'])}",
                "pf3": round(float(last3["pf"].mean()), 1) if len(last3) else None,
                "pa3": round(float(last3["pa"].mean()), 1) if len(last3) else None,
                "off_rank": off_r.get(team), "def_rank": def_r.get(team), "streaks": streaks}
        h2h = L[(L["team"] == FIX.get(r.home_team, r.home_team)) & (L["opp"] == FIX.get(r.away_team, r.away_team))].tail(3)
        out[r.game_id] = {**side, "h2h": [
            {"season": int(m.season), "score": f"{r.home_team} {int(m.pf)}-{int(m.pa)}",
             "ats": (f"{r.home_team} covered" if m.ats > 0 else f"{r.away_team} covered" if m.ats < 0 else "push")}
            for m in h2h.itertuples()]}
    return out


def stat_edges(season, week, away, home):
    """Side-leaning stats for one matchup, season to date (games before `week`): each stat with both teams' value,
    league rank (1 = best) and the side it favors. Context: the model already uses these and the line prices them."""
    t = pd.read_csv(os.path.join(DATA, "team_games.csv"))
    t = t[(t["season"] == season) & (t["week"] < week)].copy()
    t["team"], t["opp"] = t["team"].replace(FIX), t["opp"].replace(FIX)
    t["rushes"] = (t["plays"] - t["dropbacks"]).clip(lower=1)
    avg = lambda x, c, wc: float(np.average(x[c], weights=x[wc])) if x[wc].sum() > 0 else np.nan  # noqa: E731

    def unit(x):
        return pd.Series({"epa": avg(x, "epa", "plays"), "sr": avg(x, "sr", "plays"), "pass": avg(x, "pass_epa", "dropbacks"),
                          "rush": avg(x, "rush_epa", "rushes"), "to": x["turnovers"].mean()})
    off = t.groupby("team").apply(unit, include_groups=False)
    dfn = t.groupby("opp").apply(unit, include_groups=False)
    last4 = {}
    for tm, x in t.sort_values("week").groupby("team"):
        wk = x["week"].tail(4)
        o = x[x["week"].isin(wk)]
        d = t[(t["opp"] == tm) & t["week"].isin(wk)]
        last4[tm] = avg(o, "epa", "plays") - avg(d, "epa", "plays")
    g = pd.read_csv(os.path.join(DATA, "games.csv"), low_memory=False)
    g = g[(g["season"] == season) & (g["week"] < week) & (g["game_type"] == "REG") & g["result"].notna()]
    pdiff = pd.concat([pd.Series(g["result"].values, index=g["home_team"].replace(FIX)),
                       pd.Series(-g["result"].values, index=g["away_team"].replace(FIX))]).groupby(level=0).mean()
    stats = [("Offense EPA per play", off["epa"], True, "{:+.3f}"), ("Defense EPA per play allowed", dfn["epa"], False, "{:+.3f}"),
             ("Net EPA per play", off["epa"] - dfn["epa"], True, "{:+.3f}"),
             ("Success rate", off["sr"], True, "{:.1%}"), ("Success rate allowed", dfn["sr"], False, "{:.1%}"),
             ("Pass EPA per dropback", off["pass"], True, "{:+.3f}"), ("Pass EPA allowed", dfn["pass"], False, "{:+.3f}"),
             ("Rush EPA per carry", off["rush"], True, "{:+.3f}"), ("Rush EPA allowed", dfn["rush"], False, "{:+.3f}"),
             ("Turnover margin per game", dfn["to"] - off["to"], True, "{:+.1f}"),
             ("Net EPA, last 4 games", pd.Series(last4), True, "{:+.3f}"), ("Point differential per game", pdiff, True, "{:+.1f}")]
    rows = []
    for name, s, high, fmt in stats:
        s = s.dropna()
        rk = s.rank(ascending=not high, method="min")
        if away not in s.index or home not in s.index:
            continue
        ra, rh = int(rk[away]), int(rk[home])
        lean = "even" if abs(ra - rh) <= 3 else (away if ra < rh else home)
        rows.append({"stat": name, "away": fmt.format(s[away]), "away_rank": ra, "home": fmt.format(s[home]),
                     "home_rank": rh, "lean": lean})
    return rows
