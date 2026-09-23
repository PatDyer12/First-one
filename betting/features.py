"""Turn raw game/play tables into pre-game features, strictly using information known before kickoff.

Walks every game in date order. Before each game it snapshots each team's current ratings
(the features), then updates the ratings with that game's result. Nothing from a game ever
leaks into its own features.

Ratings kept per team
  elo        538-style Elo: margin-of-victory multiplier, 1/3 regression to the mean each offseason
  off_*/def_* exponentially weighted, opponent-adjusted EPA/play, success rate, pass & rush EPA
             (garbage time removed), shrunk toward league average and partly reset each offseason
  pts_for/against, pace (offensive plays per game)
Ratings kept per QB
  qb         EPA per dropback, weighted by dropbacks, shrunk toward replacement level
"""
import math
import os

import numpy as np
import pandas as pd

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

DECAY = 0.90          # weight a game keeps each time the team plays another one (~10-game memory)
CARRY = 0.45          # share of last season's weight that survives the offseason
PRIOR_GAMES = 3.0     # pseudo-games of league average mixed into every team rating
QB_DECAY = 0.95
QB_CARRY = 0.75
QB_PRIOR_DB = 250.0   # pseudo-dropbacks of replacement-level play
QB_REPL = -0.10       # replacement-level EPA per dropback
QB_DB_PER_GAME = 36.0
ELO_K = 20.0
ELO_HFA = 48.0
ELO_REVERT = 1 / 3
TEAM_STATS = ["epa", "sr", "pass_epa", "rush_epa"]
PLAIN_STATS = ["pts_for", "pts_against", "pace"]
LEAGUE_DECAY = 0.995

ALIAS = {"OAK": "LV", "SD": "LAC", "STL": "LA", "LAR": "LA"}


class Ew:
    """Exponentially weighted mean with a shrinkage prior."""
    __slots__ = ("num", "den")

    def __init__(self):
        self.num = 0.0
        self.den = 0.0

    def get(self, prior, n):
        return (self.num + prior * n) / (self.den + n)

    def add(self, x, w, decay):
        self.num = self.num * decay + x * w
        self.den = self.den * decay + w

    def shrink(self, f):
        self.num *= f
        self.den *= f


def load():
    g = pd.read_csv(os.path.join(DATA, "games.csv"))
    g = g[g["season"] >= 2009].copy()
    for c in ("home_team", "away_team"):
        g[c] = g[c].replace(ALIAS)
    g = g.sort_values(["gameday", "gametime", "game_id"]).reset_index(drop=True)
    t = pd.read_csv(os.path.join(DATA, "team_games.csv"))
    t["team"] = t["team"].replace(ALIAS)
    t["opp"] = t["opp"].replace(ALIAS)
    q = pd.read_csv(os.path.join(DATA, "qb_games.csv"))
    q["team"] = q["team"].replace(ALIAS)
    return g, t, q


def build():
    g, t, q = load()
    tg = {(r.game_id, r.team): r for r in t.itertuples(index=False)}
    qg = {}
    for r in q.itertuples(index=False):
        qg.setdefault((r.game_id, r.team), []).append(r)

    teams = {}
    qbs = {}
    league = {k: Ew() for k in ["epa", "sr", "pass_epa", "rush_epa", "pts", "pace"]}
    for k, v in (("epa", 0.0), ("sr", 0.44), ("pass_epa", 0.05), ("rush_epa", -0.08), ("pts", 21.5), ("pace", 62.0)):
        league[k].add(v, 50, 1)
    last_starter = {}
    season_seen = {}

    def team(tm):
        if tm not in teams:
            s = {"elo": 1500.0, "team_qb": Ew()}
            for k in TEAM_STATS:
                s["off_" + k] = Ew()
                s["def_" + k] = Ew()
            for k in PLAIN_STATS:
                s[k] = Ew()
            teams[tm] = s
        return teams[tm]

    def lg(k):
        return league[k].get(0, 0)

    def new_season(tm, season):
        s = team(tm)
        if season_seen.get(tm) == season:
            return
        if tm in season_seen:
            s["elo"] = s["elo"] * (1 - ELO_REVERT) + 1505 * ELO_REVERT
            for k, v in s.items():
                if isinstance(v, Ew):
                    v.shrink(CARRY)
        season_seen[tm] = season

    def qb_val(qid):
        e = qbs.get(qid)
        return (e.get(QB_REPL, QB_PRIOR_DB) if e else QB_REPL)

    def rating(tm, k):
        s = team(tm)
        base = "pts" if k in ("pts_for", "pts_against") else k.split("_", 1)[1] if k.startswith(("off_", "def_")) else k
        return s[k].get(lg(base), PRIOR_GAMES)

    rows = []
    qb_season = {}
    for gm in g.itertuples(index=False):
        h, a = gm.home_team, gm.away_team
        for tm in (h, a):
            new_season(tm, gm.season)
        if gm.season not in qb_season:
            for e in qbs.values():
                e.shrink(QB_CARRY)
            qb_season[gm.season] = True
        hs, as_ = team(h), team(a)
        neutral = 1 if gm.location == "Neutral" else 0
        hq = gm.home_qb_id if isinstance(gm.home_qb_id, str) else last_starter.get(h)
        aq = gm.away_qb_id if isinstance(gm.away_qb_id, str) else last_starter.get(a)

        f = {"game_id": gm.game_id, "season": gm.season, "week": gm.week, "game_type": gm.game_type,
             "gameday": gm.gameday, "home": h, "away": a, "result": gm.result, "total": gm.total,
             "spread_line": gm.spread_line, "total_line": gm.total_line,
             "home_ml": gm.home_moneyline, "away_ml": gm.away_moneyline,
             "home_spread_odds": gm.home_spread_odds, "away_spread_odds": gm.away_spread_odds,
             "over_odds": gm.over_odds, "under_odds": gm.under_odds,
             "home_qb": gm.home_qb_name if isinstance(gm.home_qb_name, str) else None,
             "away_qb": gm.away_qb_name if isinstance(gm.away_qb_name, str) else None,
             "hfa": 1 - neutral, "div": gm.div_game,
             "rest_diff": np.clip((gm.home_rest or 7) - (gm.away_rest or 7), -7, 7),
             "playoff": int(gm.game_type != "REG")}
        f["elo_diff"] = (hs["elo"] - as_["elo"]) / 25.0
        for side, tm in (("h", h), ("a", a)):
            for k in TEAM_STATS:
                f[f"{side}_off_{k}"] = rating(tm, "off_" + k)
                f[f"{side}_def_{k}"] = rating(tm, "def_" + k)
            for k in PLAIN_STATS:
                f[f"{side}_{k}"] = rating(tm, k)
        hqv = qb_val(hq) if hq else QB_REPL
        aqv = qb_val(aq) if aq else QB_REPL
        f["h_qb"], f["a_qb"] = hqv * QB_DB_PER_GAME, aqv * QB_DB_PER_GAME
        f["h_qb_change"] = (hqv - hs["team_qb"].get(hqv, 1)) * QB_DB_PER_GAME
        f["a_qb_change"] = (aqv - as_["team_qb"].get(aqv, 1)) * QB_DB_PER_GAME
        roof = gm.roof if isinstance(gm.roof, str) else "outdoors"
        f["dome"] = int(roof in ("dome", "closed"))
        f["wind"] = 0.0 if f["dome"] or pd.isna(gm.wind) else float(gm.wind)
        f["cold"] = 0.0 if f["dome"] or pd.isna(gm.temp) else max(0.0, 40.0 - float(gm.temp))
        f["lg_pts"] = lg("pts")
        rows.append(f)

        if pd.isna(gm.result):
            continue
        # ---- update ratings with this game's result ----
        margin = gm.result
        elo_d = hs["elo"] - as_["elo"] + ELO_HFA * (1 - neutral)
        exp_h = 1 / (1 + 10 ** (-elo_d / 400))
        won = 1.0 if margin > 0 else 0.0 if margin < 0 else 0.5
        winner_d = elo_d if margin > 0 else -elo_d
        mult = math.log(abs(margin) + 1) * 2.2 / (max(winner_d, -400) * 0.001 + 2.2)
        delta = ELO_K * mult * (won - exp_h)
        hs["elo"] += delta
        as_["elo"] -= delta

        pre = {tm: {k: rating(tm, k) for k in ["off_" + s for s in TEAM_STATS] + ["def_" + s for s in TEAM_STATS]}
               for tm in (h, a)}
        for tm, op, pf, pa in ((h, a, gm.home_score, gm.away_score), (a, h, gm.away_score, gm.home_score)):
            s = team(tm)
            o = tg.get((gm.game_id, tm))
            d = tg.get((gm.game_id, op))
            if o is not None and d is not None:
                for k in TEAM_STATS:
                    ov, dv = getattr(o, k), getattr(d, k)
                    if pd.notna(ov):
                        s["off_" + k].add(ov - (pre[op]["def_" + k] - lg(k)), 1, DECAY)
                    if pd.notna(dv):
                        s["def_" + k].add(dv - (pre[op]["off_" + k] - lg(k)), 1, DECAY)
                s["pace"].add(o.all_plays, 1, DECAY)
                league["pace"].add(o.all_plays, 1, LEAGUE_DECAY)
                for k in TEAM_STATS:
                    if pd.notna(getattr(o, k)):
                        league[k].add(getattr(o, k), 1, LEAGUE_DECAY)
            s["pts_for"].add(pf, 1, DECAY)
            s["pts_against"].add(pa, 1, DECAY)
            league["pts"].add(pf, 1, LEAGUE_DECAY)
            played = qg.get((gm.game_id, tm), [])
            if played:
                main = max(played, key=lambda r: r.dropbacks)
                last_starter[tm] = main.qb_id
                for r in played:
                    qbs.setdefault(r.qb_id, Ew()).add(r.qb_epa / max(r.dropbacks, 1), r.dropbacks, QB_DECAY)
                s["team_qb"].add(qb_val(main.qb_id), 1, 0.7)
    return add_derived(pd.DataFrame(rows))


def add_derived(df):
    """Matchup features: home minus away (for the spread) and sums (for the total)."""
    for k in TEAM_STATS:
        df[f"net_{k}"] = (df[f"h_off_{k}"] - df[f"h_def_{k}"]) - (df[f"a_off_{k}"] - df[f"a_def_{k}"])
        df[f"sum_{k}"] = df[f"h_off_{k}"] + df[f"h_def_{k}"] + df[f"a_off_{k}"] + df[f"a_def_{k}"]
    df["net_pts"] = (df["h_pts_for"] - df["h_pts_against"]) - (df["a_pts_for"] - df["a_pts_against"])
    df["sum_pts"] = df["h_pts_for"] + df["h_pts_against"] + df["a_pts_for"] + df["a_pts_against"]
    df["qb_diff"] = df["h_qb"] - df["a_qb"]
    df["qb_change_diff"] = df["h_qb_change"] - df["a_qb_change"]
    df["qb_sum"] = df["h_qb"] + df["a_qb"]
    df["pace_sum"] = df["h_pace"] + df["a_pace"]
    return df


SPREAD_FEATURES = ["elo_diff", "net_epa", "net_sr", "net_pass_epa", "net_rush_epa", "net_pts",
                   "qb_diff", "qb_change_diff", "hfa", "rest_diff", "div"]
TOTAL_FEATURES = ["sum_epa", "sum_sr", "sum_pass_epa", "sum_rush_epa", "sum_pts", "qb_sum", "pace_sum",
                  "lg_pts", "dome", "wind", "cold", "div", "playoff"]
