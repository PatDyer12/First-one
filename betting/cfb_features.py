"""College football pre-game features (same no-leak walk-through as features.py for the NFL).

Ratings kept per team (ESPN team id)
  elo           Elo with margin-of-victory multiplier; FCS and lower divisions start well below FBS
  off_*/def_*   exponentially weighted, opponent-adjusted EPA/play, success rate, pass & rush EPA
                (garbage time removed with Bill Connelly's score-by-quarter rule)
  pts, pace     points for/against, scrimmage plays per game
  mkt           market power rating from earlier closing spreads/totals, and how far this week's line moved off it
"""
import math
import os

import numpy as np
import pandas as pd

from features import Ew

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "cfb")
PARAMS = {"decay": 0.88, "carry": 0.35, "prior_games": 2.5, "elo_k": 30.0, "elo_revert": 0.4,
          "mkt_rate": 0.4, "mkt_carry": 0.6}
ELO_START = {"fbs": 1500.0, "fcs": 1250.0, "ii": 1050.0, "iii": 950.0}
ELO_HFA = 55.0
TEAM_STATS = ["epa", "sr", "pass_epa", "rush_epa"]
PLAIN_STATS = ["pts_for", "pts_against", "pace"]
LEAGUE_DECAY = 0.998
DIV_RANK = {"fbs": 0, "fcs": 1, "ii": 2, "iii": 3}


def load():
    g = pd.read_csv(os.path.join(DATA, "games.csv"), low_memory=False)
    # keep games with at least one FBS team; lower-division games still feed the ratings through their teams
    g = g[(g["home_division"] == "fbs") | (g["away_division"] == "fbs")].copy()
    g["result"] = g["home_points"] - g["away_points"]
    g["total"] = g["home_points"] + g["away_points"]
    g.loc[g["completed"] != True, ["result", "total"]] = np.nan  # noqa: E712
    for c in ("home_ml", "away_ml", "home_spread_odds", "away_spread_odds", "over_odds", "under_odds"):
        g[c] = np.nan
    path = os.path.join(DATA, "book_odds.csv")
    if os.path.exists(path):  # this week's lines: DraftKings stands in for the consensus
        b = pd.read_csv(path)
        b = b[b["book"] == "DraftKings"]
        dk = {(r.away, r.home, r.market, r.side): (r.line, r.odds) for r in b.itertuples(index=False)}
        for i, r in g[g["result"].isna()].iterrows():
            k = (r.away_id, r.home_id)
            if (k + ("spread", "home")) in dk:
                g.at[i, "spread_line"], g.at[i, "home_spread_odds"] = dk[k + ("spread", "home")]
                g.at[i, "away_spread_odds"] = dk.get(k + ("spread", "away"), (None, np.nan))[1]
            if (k + ("total", "over")) in dk:
                g.at[i, "total_line"], g.at[i, "over_odds"] = dk[k + ("total", "over")]
                g.at[i, "under_odds"] = dk.get(k + ("total", "under"), (None, np.nan))[1]
            if (k + ("ml", "home")) in dk and (k + ("ml", "away")) in dk:
                g.at[i, "home_ml"], g.at[i, "away_ml"] = dk[k + ("ml", "home")][1], dk[k + ("ml", "away")][1]
    g["start_date"] = pd.to_datetime(g["start_date"], utc=True, errors="coerce")
    g = g.sort_values(["start_date", "game_id"]).reset_index(drop=True)
    t = pd.read_csv(os.path.join(DATA, "team_games.csv"))
    return g, t


def build(params=None):
    P = dict(PARAMS, **(params or {}))
    g, t = load()
    tg = {(r.game_id, r.team): r for r in t.itertuples(index=False)}
    teams = {}
    league = {k: Ew() for k in ["epa", "sr", "pass_epa", "rush_epa", "pts", "pace"]}
    for k, v in (("epa", 0.0), ("sr", 0.42), ("pass_epa", 0.1), ("rush_epa", -0.05), ("pts", 28.0), ("pace", 70.0)):
        league[k].add(v, 50, 1)
    mkt = {"hfa": 2.8, "total": 52.0}
    season_seen, last_game = {}, {}

    def team(tid, div):
        if tid not in teams:
            s = {"elo": ELO_START.get(div, 1000.0), "mkt": -12.0 if div != "fbs" else 0.0, "mkt_tot": 0.0}
            for k in TEAM_STATS:
                s["off_" + k], s["def_" + k] = Ew(), Ew()
            for k in PLAIN_STATS:
                s[k] = Ew()
            teams[tid] = s
        return teams[tid]

    def lg(k):
        return league[k].get(0, 0)

    def rating(tid, k):
        base = "pts" if k in ("pts_for", "pts_against") else k.split("_", 1)[1] if k.startswith(("off_", "def_")) else k
        return teams[tid][k].get(lg(base), P["prior_games"])

    rows = []
    for gm in g.itertuples(index=False):
        h, a = gm.home_id, gm.away_id
        hs, as_ = team(h, gm.home_division), team(a, gm.away_division)
        for tid, s in ((h, hs), (a, as_)):
            if season_seen.get(tid) not in (None, gm.season):
                start = ELO_START.get(gm.home_division if tid == h else gm.away_division, 1000.0)
                s["elo"] = s["elo"] * (1 - P["elo_revert"]) + start * P["elo_revert"]
                s["mkt"] *= P["mkt_carry"]
                s["mkt_tot"] *= P["mkt_carry"]
                for v in s.values():
                    if isinstance(v, Ew):
                        v.shrink(P["carry"])
            season_seen[tid] = gm.season
        neutral = 1 if gm.neutral_site == True else 0  # noqa: E712
        f = {"game_id": gm.game_id, "season": gm.season, "week": gm.week, "gameday": str(gm.start_date)[:10],
             "home": gm.home_team, "away": gm.away_team, "home_id": h, "away_id": a,
             "result": gm.result, "total": gm.total, "spread_line": gm.spread_line, "total_line": gm.total_line,
             "home_ml": gm.home_ml, "away_ml": gm.away_ml, "home_spread_odds": gm.home_spread_odds,
             "away_spread_odds": gm.away_spread_odds, "over_odds": gm.over_odds, "under_odds": gm.under_odds,
             "home_qb": None, "away_qb": None, "hfa": 1 - neutral, "conf": int(gm.conference_game == True),  # noqa: E712
             "div_diff": DIV_RANK.get(gm.away_division, 3) - DIV_RANK.get(gm.home_division, 3),
             "postseason": int(gm.season_type == "postseason"), "early": int(gm.week <= 3 and gm.season_type != "postseason")}
        rest = []
        for tid in (h, a):
            prev = last_game.get(tid)
            rest.append(min((gm.start_date - prev).days, 21) if prev is not None and pd.notna(gm.start_date) else 14)
        f["rest_diff"] = float(np.clip(rest[0] - rest[1], -10, 10))
        f["elo_diff"] = (hs["elo"] - as_["elo"]) / 25.0
        for side, tid in (("h", h), ("a", a)):
            for k in TEAM_STATS:
                f[f"{side}_off_{k}"] = rating(tid, "off_" + k)
                f[f"{side}_def_{k}"] = rating(tid, "def_" + k)
            for k in PLAIN_STATS:
                f[f"{side}_{k}"] = rating(tid, k)
        f["lg_pts"] = lg("pts")
        f["mkt_hfa"] = mkt["hfa"] * (1 - neutral)
        f["mkt_spread"] = hs["mkt"] - as_["mkt"] + f["mkt_hfa"]
        f["mkt_total"] = mkt["total"] + hs["mkt_tot"] + as_["mkt_tot"]
        f["line_move"] = gm.spread_line - f["mkt_spread"] if pd.notna(gm.spread_line) else 0.0
        f["total_move"] = gm.total_line - f["mkt_total"] if pd.notna(gm.total_line) else 0.0
        rows.append(f)

        if pd.notna(gm.spread_line):
            err = gm.spread_line - f["mkt_spread"]
            hs["mkt"] += P["mkt_rate"] * err / 2
            as_["mkt"] -= P["mkt_rate"] * err / 2
            mkt["hfa"] += 0.005 * err * (1 - neutral)
        if pd.notna(gm.total_line):
            err = gm.total_line - f["mkt_total"]
            hs["mkt_tot"] += P["mkt_rate"] * err / 3
            as_["mkt_tot"] += P["mkt_rate"] * err / 3
            mkt["total"] += 0.01 * err
        if pd.isna(gm.result):
            continue
        for tid in (h, a):
            last_game[tid] = gm.start_date
        margin = gm.result
        elo_d = hs["elo"] - as_["elo"] + ELO_HFA * (1 - neutral)
        exp_h = 1 / (1 + 10 ** (-elo_d / 400))
        won = 1.0 if margin > 0 else 0.0 if margin < 0 else 0.5
        winner_d = elo_d if margin > 0 else -elo_d
        mult = math.log(abs(margin) + 1) * 2.2 / (max(winner_d, -400) * 0.001 + 2.2)
        delta = P["elo_k"] * mult * (won - exp_h)
        hs["elo"] += delta
        as_["elo"] -= delta

        pre = {tid: {k: rating(tid, k) for k in ["off_" + s for s in TEAM_STATS] + ["def_" + s for s in TEAM_STATS]}
               for tid in (h, a)}
        for tid, op, pf, pa in ((h, a, gm.home_points, gm.away_points), (a, h, gm.away_points, gm.home_points)):
            s = teams[tid]
            o, d = tg.get((gm.game_id, tid)), tg.get((gm.game_id, op))
            if o is not None and d is not None:
                for k in TEAM_STATS:
                    ov, dv = getattr(o, k), getattr(d, k)
                    if pd.notna(ov):
                        s["off_" + k].add(ov - (pre[op]["def_" + k] - lg(k)), 1, P["decay"])
                        league[k].add(ov, 1, LEAGUE_DECAY)
                    if pd.notna(dv):
                        s["def_" + k].add(dv - (pre[op]["off_" + k] - lg(k)), 1, P["decay"])
                if pd.notna(o.all_plays):
                    s["pace"].add(o.all_plays, 1, P["decay"])
                    league["pace"].add(o.all_plays, 1, LEAGUE_DECAY)
            s["pts_for"].add(pf, 1, P["decay"])
            s["pts_against"].add(pa, 1, P["decay"])
            league["pts"].add(pf, 1, LEAGUE_DECAY)
    df = pd.DataFrame(rows)
    for k in TEAM_STATS:
        df[f"net_{k}"] = (df[f"h_off_{k}"] - df[f"h_def_{k}"]) - (df[f"a_off_{k}"] - df[f"a_def_{k}"])
        df[f"sum_{k}"] = df[f"h_off_{k}"] + df[f"h_def_{k}"] + df[f"a_off_{k}"] + df[f"a_def_{k}"]
    df["net_pts"] = (df["h_pts_for"] - df["h_pts_against"]) - (df["a_pts_for"] - df["a_pts_against"])
    df["sum_pts"] = df["h_pts_for"] + df["h_pts_against"] + df["a_pts_for"] + df["a_pts_against"]
    df["pace_sum"] = df["h_pace"] + df["a_pace"]
    df["game_type"] = np.where(df["postseason"] == 1, "POST", "REG")
    return df


SPREAD_FEATURES = ["elo_diff", "net_epa", "net_sr", "net_pass_epa", "net_rush_epa", "net_pts", "hfa", "mkt_hfa",
                   "rest_diff", "conf", "div_diff", "mkt_spread", "line_move", "early"]
TOTAL_FEATURES = ["sum_epa", "sum_sr", "sum_pass_epa", "sum_rush_epa", "sum_pts", "pace_sum", "lg_pts",
                  "mkt_total", "total_move", "postseason", "early"]
