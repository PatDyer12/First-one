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
WEATHER = ["wind", "temp", "precip", "indoor", "wind8", "wet8"]
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
    wpath = os.path.join(DATA, "weather.csv")
    if os.path.exists(wpath):  # kickoff weather (cfb_weather.py): station history + this week's forecast
        w = pd.read_csv(wpath)
        g = g.merge(w[["game_id"] + [c for c in WEATHER if c in w]], on="game_id", how="left")
    for c in WEATHER:
        if c not in g:
            g[c] = np.nan
    rpath = os.path.join(DATA, "rankings.csv")
    if os.path.exists(rpath):  # top-25 rank at kickoff (cfb_rankings.py); ESPN occasionally swaps home/away
        r = pd.read_csv(rpath)
        g = g.merge(r, on="game_id", how="left", suffixes=("", "_r"))
        flip = g["home_id"] == g["away_id_r"]
        g.loc[flip, ["home_rank", "away_rank"]] = g.loc[flip, ["away_rank", "home_rank"]].values
        g = g.drop(columns=["home_id_r", "away_id_r"])
    else:
        g["home_rank"] = g["away_rank"] = np.nan
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
    form = {}  # (team, season) -> list of (covered, went_over) in games with lines
    rec = {}   # (team, season) -> dict(w, l, cw, cl, streak, last_margin, last_rank, last_opp_rank, n)
    meet = {}  # frozenset(team pair) -> list of (season, {team: margin})
    # each team's next game, and that opponent's rank as of this week (look-ahead spots)
    long = pd.concat([g[["game_id", "season", "week", "start_date", "home_id", "away_id", "home_rank"]]
                      .rename(columns={"home_id": "tid", "away_id": "opp", "home_rank": "rank"}),
                      g[["game_id", "season", "week", "start_date", "away_id", "home_id", "away_rank"]]
                      .rename(columns={"away_id": "tid", "home_id": "opp", "away_rank": "rank"})]).sort_values("start_date")
    long["next_opp"] = long.groupby(["tid", "season"])["opp"].shift(-1)
    long["next_game"] = long.groupby(["tid", "season"])["game_id"].shift(-1)
    rank_now = {(r.tid, r.season, r.week): r.rank for r in long.itertuples(index=False)}
    rank_at = {(r.game_id, r.tid): r.rank for r in long.itertuples(index=False)}
    next_opp_rank = {}
    for r in long.itertuples(index=False):
        if pd.notna(r.next_opp):
            k = (int(r.next_opp), r.season, r.week)
            next_opp_rank[(r.game_id, r.tid)] = rank_now[k] if k in rank_now else rank_at.get((r.next_game, int(r.next_opp)))
    reg_games = g[g["season_type"] != "postseason"].groupby(["season"])[["home_id", "away_id"]]
    n_reg = {}
    for season, x in reg_games:
        for tid, n in pd.concat([x["home_id"], x["away_id"]]).value_counts().items():
            n_reg[(season, tid)] = int(n)

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
        for side, tid in (("h", h), ("a", a)):
            fl = form.get((tid, gm.season), [])
            last3 = fl[-3:]
            f[f"{side}_cov3"] = sum(1 for c, _o in last3 if c is True) if len(last3) == 3 else np.nan
            f[f"{side}_ats3_lost"] = sum(1 for c, _o in last3 if c is False) if len(last3) == 3 else np.nan
            f[f"{side}_over3"] = sum(1 for _c, o in last3 if o is True) if len(last3) == 3 else np.nan
            f[f"{side}_under3"] = sum(1 for _c, o in last3 if o is False) if len(last3) == 3 else np.nan
        post = gm.season_type == "postseason"
        for side, tid, rank in (("h", h, gm.home_rank), ("a", a, gm.away_rank)):
            r = rec.get((tid, gm.season), {"w": 0, "l": 0, "cw": 0, "cl": 0, "streak": 0, "n": 0,
                                           "last_margin": np.nan, "last_rank": np.nan, "last_opp_rank": np.nan})
            last = rec.get((tid, gm.season - 1))
            f[f"{side}_rank"] = rank
            f[f"{side}_w"], f[f"{side}_l"] = r["w"], r["l"]
            f[f"{side}_cw"], f[f"{side}_cl"] = r["cw"], r["cl"]
            f[f"{side}_streak"] = r["streak"]
            f[f"{side}_last_margin"] = r["last_margin"]
            f[f"{side}_prev_rank"] = r["last_rank"]           # rank going into the team's previous game
            f[f"{side}_last_opp_rank"] = r["last_opp_rank"]   # rank of the team it played last
            f[f"{side}_played"] = r["n"]
            f[f"{side}_last_wpct"] = last["w"] / max(last["w"] + last["l"], 1) if last else np.nan
            f[f"{side}_rem"] = max(n_reg.get((gm.season, tid), 12) - r["n"] - 1, 0) if not post else 0
            f[f"{side}_fbs"] = int((gm.home_division if tid == h else gm.away_division) == "fbs")
            f[f"{side}_mkt"] = (hs if tid == h else as_)["mkt"]
            f[f"{side}_next_opp_rank"] = next_opp_rank.get((gm.game_id, tid), np.nan)
        past = meet.get(frozenset((h, a)), [])
        f["kick_et"] = gm.start_date.tz_convert("America/New_York").hour if pd.notna(gm.start_date) else np.nan
        f["h2h_margin"] = past[-1][1].get(h, np.nan) if past else np.nan   # home team's margin in the last meeting
        f["h2h_ago"] = gm.season - past[-1][0] if past else np.nan        # seasons since it
        f["h2h_n10"] = len({x[0] for x in past if gm.season - 10 <= x[0] < gm.season})  # seasons met, last 10
        f["wind"] = 0.0 if gm.indoor == 1 else gm.wind
        f["temp"] = 70.0 if gm.indoor == 1 else gm.temp
        f["precip"] = 0.0 if gm.indoor == 1 else gm.precip
        f["wind8"] = 0.0 if gm.indoor == 1 else gm.wind8  # steady weather, kickoff -3h to +4h
        f["wet8"] = 0.0 if gm.indoor == 1 else gm.wet8
        f["indoor"] = gm.indoor
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
        for tid, m, rank, opp_rank in ((h, gm.result, gm.home_rank, gm.away_rank), (a, -gm.result, gm.away_rank, gm.home_rank)):
            r = rec.setdefault((tid, gm.season), {"w": 0, "l": 0, "cw": 0, "cl": 0, "streak": 0, "n": 0,
                                                  "last_margin": np.nan, "last_rank": np.nan, "last_opp_rank": np.nan})
            won = m > 0
            r["w" if won else "l"] += 1
            if gm.conference_game == True:  # noqa: E712
                r["cw" if won else "cl"] += 1
            r["streak"] = (max(r["streak"], 0) + 1) if won else (min(r["streak"], 0) - 1)
            r["last_margin"], r["last_rank"], r["last_opp_rank"] = m, rank, opp_rank
            r["n"] += 0 if gm.season_type == "postseason" else 1
        meet.setdefault(frozenset((h, a)), []).append((gm.season, {h: gm.result, a: -gm.result}))
        if pd.notna(gm.spread_line):
            cov_h = gm.result - gm.spread_line
            ou = (gm.total - gm.total_line) if pd.notna(gm.total_line) else np.nan
            for tid, c in ((h, cov_h), (a, -cov_h)):
                form.setdefault((tid, gm.season), []).append(
                    (None if c == 0 else c > 0, None if (pd.isna(ou) or ou == 0) else ou > 0))
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
    return add_stat_model(add_week_ranks(df))


UNITS = ["off_epa", "def_epa", "off_pass_epa", "def_pass_epa", "off_rush_epa", "def_rush_epa", "pace"]


def add_week_ranks(df):
    """Where each FBS team stands that week among FBS teams playing: market power rank (1 = best) and
    percentiles for each unit (1.0 = best; for defenses, lower EPA allowed is better)."""
    long = pd.concat([df[["game_id", "season", "week", "postseason", f"{s}_fbs", f"{s}_mkt"] + [f"{s}_{u}" for u in UNITS]]
                      .rename(columns=lambda c, s=s: c[2:] if c.startswith(s + "_") else c).assign(side=s)
                      for s in ("h", "a")], ignore_index=True)
    fbs = long[long["fbs"] == 1].copy()
    grp = fbs.groupby(["season", "week", "postseason"])
    fbs["mkt_rank"] = grp["mkt"].rank(ascending=False, method="min")
    for u in UNITS:
        fbs[f"{u}_pct"] = grp[u].rank(pct=True, ascending=not u.startswith("def_"))
    cols = ["mkt_rank"] + [f"{u}_pct" for u in UNITS]
    for s in ("h", "a"):
        x = fbs[fbs["side"] == s].set_index("game_id")[cols].add_prefix(f"{s}_")
        df = df.join(x, on="game_id")
    return df


STAT_SIDE = ["elo_diff", "net_epa", "net_sr", "net_pass_epa", "net_rush_epa", "net_pts", "hfa", "rest_diff",
             "div_diff", "conf", "early"]
STAT_TOTAL = ["sum_epa", "sum_sr", "sum_pass_epa", "sum_rush_epa", "sum_pts", "pace_sum", "lg_pts", "postseason", "early"]


def add_stat_model(df):
    """Stats-only power ratings: margin and total predicted from offense/defense numbers alone (no betting line),
    walk-forward (each season predicted by a ridge model trained only on earlier seasons)."""
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    df = df.copy()
    df["stat_margin"] = np.nan
    df["stat_total"] = np.nan
    for season in sorted(df["season"].unique()):
        if season < 2012:
            continue
        tr = df[(df["season"] < season) & (df["season"] >= 2010) & df["result"].notna()]
        te = df["season"] == season
        for cols, target, out in ((STAT_SIDE, "result", "stat_margin"), (STAT_TOTAL, "total", "stat_total")):
            t = tr.dropna(subset=cols + [target])
            m = make_pipeline(StandardScaler(), Ridge(alpha=10.0)).fit(t[cols].values, t[target].values)
            x = df.loc[te, cols]
            ok = x.notna().all(axis=1)
            df.loc[x[ok].index, out] = m.predict(x[ok].values)
    df["stat_edge_spread"] = df["stat_margin"] - df["spread_line"]
    df["stat_edge_total"] = df["stat_total"] - df["total_line"]
    return df


SPREAD_FEATURES = ["elo_diff", "net_epa", "net_sr", "net_pass_epa", "net_rush_epa", "net_pts", "hfa", "mkt_hfa",
                   "rest_diff", "conf", "div_diff", "mkt_spread", "line_move", "early"]
TOTAL_FEATURES = ["sum_epa", "sum_sr", "sum_pass_epa", "sum_rush_epa", "sum_pts", "pace_sum", "lg_pts",
                  "mkt_total", "total_move", "postseason", "early"]
