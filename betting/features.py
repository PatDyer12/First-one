"""Turn raw game/play tables into pre-game features, strictly using information known before kickoff.

Walks every game in date order. Before each game it snapshots each team's current ratings
(the features), then updates the ratings with that game. Nothing from a game leaks into its own features.

Ratings kept per team
  elo           538-style Elo: margin-of-victory multiplier, partial regression to the mean each offseason
  off_*/def_*   exponentially weighted, opponent-adjusted EPA/play, success rate, pass & rush EPA
                (garbage time removed), shrunk toward league average and partly reset each offseason
  pts, pace     points for/against, offensive plays per game
  mkt           market power rating: what past closing spreads/totals imply about each team
  ats / ou      how the team has done against the spread / total lately (does the market over-react?)
Per QB          EPA per dropback, weighted by dropbacks, shrunk toward replacement level
Per game        injuries (snap-weighted starters out), travel, time zones, rest/bye, primetime, weather
"""
import math
import os
import re

import numpy as np
import pandas as pd

import stadiums

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

PARAMS = {  # tuned on 2013-2018 only (see tune.py); later seasons are an untouched holdout
    "decay": 0.90,        # weight a game keeps each time the team plays another one
    "carry": 0.45,        # share of last season's weight that survives the offseason
    "prior_games": 3.0,   # pseudo-games of league average mixed into every team rating
    "qb_decay": 0.95,
    "qb_carry": 0.75,
    "qb_prior_db": 250.0,  # pseudo-dropbacks of replacement-level play
    "elo_k": 25.0,
    "elo_revert": 1 / 3,
    "mkt_rate": 0.35,     # how fast market ratings chase each new closing line
    "mkt_carry": 0.75,
    "ats_decay": 0.80,
}
QB_REPL = -0.10
QB_DB_PER_GAME = 36.0
ELO_HFA = 48.0
TEAM_STATS = ["epa", "sr", "pass_epa", "rush_epa"]
PLAIN_STATS = ["pts_for", "pts_against", "pace"]
LEAGUE_DECAY = 0.995
ALIAS = {"OAK": "LV", "SD": "LAC", "STL": "LA", "LAR": "LA"}

INJ_GROUPS = {"skill": {"RB", "FB", "WR", "TE", "HB"}, "ol": {"T", "G", "C", "OL", "OT", "OG", "LT", "RT", "LG", "RG"},
              "front": {"DE", "DT", "NT", "DL", "EDGE", "LB", "ILB", "MLB", "OLB"},
              "db": {"CB", "S", "FS", "SS", "DB", "SAF"}}
STATUS_W = {"Out": 1.0, "Doubtful": 0.9, "Questionable": 0.25, "Probable": 0.05}


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


def _read(name):
    path = os.path.join(DATA, name)
    return pd.read_csv(path, low_memory=False) if os.path.exists(path) else None


def load():
    g = _read("games.csv")
    g = g[g["season"] >= 2009].copy()
    for c in ("home_team", "away_team"):
        g[c] = g[c].replace(ALIAS)
    g = g.sort_values(["gameday", "gametime", "game_id"]).reset_index(drop=True)
    w = _read("weather.csv")
    if w is not None and len(w):  # forecast for games not yet played
        w = w.set_index("game_id")
        for c in ("temp", "wind"):
            miss = g[c].isna() & g["game_id"].isin(w.index)
            g.loc[miss, c] = g.loc[miss, "game_id"].map(w[c])
    t = _read("team_games.csv")
    t["team"] = t["team"].replace(ALIAS)
    t["opp"] = t["opp"].replace(ALIAS)
    q = _read("qb_games.csv")
    q["team"] = q["team"].replace(ALIAS)
    return g, t, q


def _norm(name):
    name = re.sub(r"[^a-z ]", "", str(name).lower().replace("-", " "))
    return re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", name).strip().replace(" ", "")


def injury_table():
    """(season, week, team) -> snap-weighted share of each position group ruled out / doubtful / questionable."""
    inj, sn = _read("injuries.csv"), _read("snaps.csv")
    if inj is None or sn is None:
        return {}
    for d in (inj, sn):
        d["team"] = d["team"].replace(ALIAS)
    inj = inj[inj["report_status"].isin(STATUS_W)].copy()
    sn = sn.copy()
    sn["role"] = sn[["offense_pct", "defense_pct"]].max(axis=1)
    sn["key"] = sn["season"] * 100 + sn["week"]
    sn = sn.sort_values(["pfr_player_id", "key"])
    # typical role over the player's last 6 games, known after each game
    sn["role6"] = sn.groupby("pfr_player_id")["role"].transform(lambda r: r.rolling(6, min_periods=1).mean())
    sn["n"] = sn["name"] = sn["player"].map(_norm)
    ids = sn.drop_duplicates(["season", "team", "n"], keep="last").set_index(["season", "team", "n"])["pfr_player_id"]
    ids_any = sn.drop_duplicates(["season", "n"], keep="last").set_index(["season", "n"])["pfr_player_id"]
    inj["n"] = inj["full_name"].map(_norm)
    inj["pid"] = [ids.get((s, t, n), ids_any.get((s, n))) for s, t, n in zip(inj["season"], inj["team"], inj["n"])]
    inj = inj.dropna(subset=["pid"])
    inj["key"] = inj["season"].astype(int) * 100 + inj["week"].astype(int)
    last = sn[["pfr_player_id", "key", "role6"]].rename(columns={"pfr_player_id": "pid", "key": "last_key"})
    inj = inj.sort_values("key")
    last = last.sort_values("last_key")
    m = pd.merge_asof(inj, last, left_on="key", right_on="last_key", by="pid", allow_exact_matches=False)
    m = m.dropna(subset=["role6"])
    # a player who has already been out for weeks is baked into the team's ratings: fade him out
    gap = (m["key"] // 100 - m["last_key"] // 100) * 18 + (m["key"] % 100 - m["last_key"] % 100) - 1
    m["fresh"] = np.exp(-gap.clip(lower=0) / 2.5)
    m["w"] = m["role6"] * m["report_status"].map(STATUS_W) * m["fresh"]
    pos_group = {p: g for g, ps in INJ_GROUPS.items() for p in ps}
    m["group"] = m["position"].map(pos_group)
    m = m.dropna(subset=["group"])
    tab = m.groupby(["season", "week", "team", "group"])["w"].sum().unstack(fill_value=0.0)
    return {k: row.to_dict() for k, row in tab.iterrows()}


def build(params=None):
    P = dict(PARAMS, **(params or {}))
    g, t, q = load()
    tg = {(r.game_id, r.team): r for r in t.itertuples(index=False)}
    qg = {}
    for r in q.itertuples(index=False):
        qg.setdefault((r.game_id, r.team), []).append(r)
    injuries = injury_table()

    teams, qbs = {}, {}
    league = {k: Ew() for k in ["epa", "sr", "pass_epa", "rush_epa", "pts", "pace"]}
    for k, v in (("epa", 0.0), ("sr", 0.44), ("pass_epa", 0.05), ("rush_epa", -0.08), ("pts", 21.5), ("pace", 62.0)):
        league[k].add(v, 50, 1)
    mkt = {"hfa": 2.5, "total": 42.0}
    last_starter, season_seen, qb_season = {}, {}, set()

    def team(tm):
        if tm not in teams:
            s = {"elo": 1500.0, "team_qb": Ew(), "mkt": 0.0, "mkt_tot": 0.0, "ats": Ew(), "ou": Ew()}
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
            s["elo"] = s["elo"] * (1 - P["elo_revert"]) + 1505 * P["elo_revert"]
            s["mkt"] *= P["mkt_carry"]
            s["mkt_tot"] *= P["mkt_carry"]
            for v in s.values():
                if isinstance(v, Ew):
                    v.shrink(P["carry"])
        season_seen[tm] = season

    def qb_val(qid):
        e = qbs.get(qid)
        return e.get(QB_REPL, P["qb_prior_db"]) if e else QB_REPL

    def rating(tm, k):
        base = "pts" if k in ("pts_for", "pts_against") else k.split("_", 1)[1] if k.startswith(("off_", "def_")) else k
        return team(tm)[k].get(lg(base), P["prior_games"])

    rows = []
    for gm in g.itertuples(index=False):
        h, a = gm.home_team, gm.away_team
        for tm in (h, a):
            new_season(tm, gm.season)
        if gm.season not in qb_season:
            for e in qbs.values():
                e.shrink(P["qb_carry"])
            qb_season.add(gm.season)
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
             "hfa": 1 - neutral, "div": gm.div_game, "playoff": int(gm.game_type != "REG"),
             "early": int(gm.week <= 4 and gm.game_type == "REG")}
        hr, ar = (gm.home_rest if pd.notna(gm.home_rest) else 7), (gm.away_rest if pd.notna(gm.away_rest) else 7)
        f["rest_diff"] = float(np.clip(hr - ar, -7, 7))
        f["bye_diff"] = int(hr >= 12) - int(ar >= 12)
        f["short_diff"] = int(hr <= 5) - int(ar <= 5)

        # travel and body clock
        site = stadiums.game_site(h, gm.season, gm.stadium_id, neutral)
        hh, ah = stadiums.home_site(h, gm.season), stadiums.home_site(a, gm.season)
        f["travel_diff"] = math.log1p(stadiums.km(ah, site)) - math.log1p(stadiums.km(hh, site))
        f["tz_diff"] = abs(site[2] - ah[2]) - abs(site[2] - hh[2])
        kick = int(str(gm.gametime)[:2]) if isinstance(gm.gametime, str) else 13
        f["west_early"] = int(kick <= 13) * (int(ah[2] <= -2 and site[2] >= 0) - int(hh[2] <= -2 and site[2] >= 0))
        f["prime"] = int(kick >= 19)
        f["hfa_prime"] = f["hfa"] * f["prime"]

        f["elo_diff"] = (hs["elo"] - as_["elo"]) / 25.0
        for side, tm in (("h", h), ("a", a)):
            for k in TEAM_STATS:
                f[f"{side}_off_{k}"] = rating(tm, "off_" + k)
                f[f"{side}_def_{k}"] = rating(tm, "def_" + k)
            for k in PLAIN_STATS:
                f[f"{side}_{k}"] = rating(tm, k)
            f[f"{side}_ats"] = team(tm)["ats"].get(0, 2)
            f[f"{side}_ou"] = team(tm)["ou"].get(0, 2)
            inj = injuries.get((gm.season, gm.week, tm), {})
            for grp in INJ_GROUPS:
                f[f"{side}_inj_{grp}"] = inj.get(grp, 0.0)
        hqv = qb_val(hq) if hq else QB_REPL
        aqv = qb_val(aq) if aq else QB_REPL
        f["h_qb"], f["a_qb"] = hqv * QB_DB_PER_GAME, aqv * QB_DB_PER_GAME
        f["h_qb_change"] = (hqv - hs["team_qb"].get(hqv, 1)) * QB_DB_PER_GAME
        f["a_qb_change"] = (aqv - as_["team_qb"].get(aqv, 1)) * QB_DB_PER_GAME
        f["dome"] = int(gm.roof in ("dome", "closed"))
        f["wind"] = 0.0 if f["dome"] or pd.isna(gm.wind) else float(gm.wind)
        f["cold"] = 0.0 if f["dome"] or pd.isna(gm.temp) else max(0.0, 40.0 - float(gm.temp))
        f["hot"] = 0.0 if f["dome"] or pd.isna(gm.temp) else max(0.0, float(gm.temp) - 80.0)
        f["lg_pts"] = lg("pts")

        # market ratings from earlier closing lines, and how far this week's line has moved off them
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
            mkt["hfa"] += 0.01 * err * (1 - neutral)
        if pd.notna(gm.total_line):
            err = gm.total_line - f["mkt_total"]
            hs["mkt_tot"] += P["mkt_rate"] * err / 3
            as_["mkt_tot"] += P["mkt_rate"] * err / 3
            mkt["total"] += 0.02 * err
        if pd.isna(gm.result):
            continue

        # ---- update ratings with this game's result ----
        margin = gm.result
        elo_d = hs["elo"] - as_["elo"] + ELO_HFA * (1 - neutral)
        exp_h = 1 / (1 + 10 ** (-elo_d / 400))
        won = 1.0 if margin > 0 else 0.0 if margin < 0 else 0.5
        winner_d = elo_d if margin > 0 else -elo_d
        mult = math.log(abs(margin) + 1) * 2.2 / (max(winner_d, -400) * 0.001 + 2.2)
        delta = P["elo_k"] * mult * (won - exp_h)
        hs["elo"] += delta
        as_["elo"] -= delta
        if pd.notna(gm.spread_line):
            hs["ats"].add(margin - gm.spread_line, 1, P["ats_decay"])
            as_["ats"].add(gm.spread_line - margin, 1, P["ats_decay"])
        if pd.notna(gm.total_line):
            for s in (hs, as_):
                s["ou"].add(gm.total - gm.total_line, 1, P["ats_decay"])

        pre = {tm: {k: rating(tm, k) for k in ["off_" + s for s in TEAM_STATS] + ["def_" + s for s in TEAM_STATS]}
               for tm in (h, a)}
        for tm, op, pf, pa in ((h, a, gm.home_score, gm.away_score), (a, h, gm.away_score, gm.home_score)):
            s = team(tm)
            o, d = tg.get((gm.game_id, tm)), tg.get((gm.game_id, op))
            if o is not None and d is not None:
                for k in TEAM_STATS:
                    ov, dv = getattr(o, k), getattr(d, k)
                    if pd.notna(ov):
                        s["off_" + k].add(ov - (pre[op]["def_" + k] - lg(k)), 1, P["decay"])
                        league[k].add(ov, 1, LEAGUE_DECAY)
                    if pd.notna(dv):
                        s["def_" + k].add(dv - (pre[op]["off_" + k] - lg(k)), 1, P["decay"])
                s["pace"].add(o.all_plays, 1, P["decay"])
                league["pace"].add(o.all_plays, 1, LEAGUE_DECAY)
            s["pts_for"].add(pf, 1, P["decay"])
            s["pts_against"].add(pa, 1, P["decay"])
            league["pts"].add(pf, 1, LEAGUE_DECAY)
            played = qg.get((gm.game_id, tm), [])
            if played:
                main = max(played, key=lambda r: r.dropbacks)
                last_starter[tm] = main.qb_id
                for r in played:
                    qbs.setdefault(r.qb_id, Ew()).add(r.qb_epa / max(r.dropbacks, 1), r.dropbacks, P["qb_decay"])
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
    df["ats_diff"] = df["h_ats"] - df["a_ats"]
    df["ou_sum"] = df["h_ou"] + df["a_ou"]
    for grp in INJ_GROUPS:
        df[f"inj_{grp}_diff"] = df[f"h_inj_{grp}"] - df[f"a_inj_{grp}"]
    df["inj_off_sum"] = df["h_inj_skill"] + df["h_inj_ol"] + df["a_inj_skill"] + df["a_inj_ol"]
    df["inj_def_sum"] = df["h_inj_front"] + df["h_inj_db"] + df["a_inj_front"] + df["a_inj_db"]
    return df


# Chosen on 2014-2018 only (tune.py). Every candidate was tested one at a time; injuries, travel/time zones,
# byes/short weeks, ATS form and heat did not help once the market line is known (the market already prices
# them), so they are computed but left out.
SPREAD_FEATURES = ["elo_diff", "net_epa", "net_sr", "net_pass_epa", "net_rush_epa", "net_pts", "qb_diff",
                   "qb_change_diff", "hfa", "rest_diff", "div", "mkt_spread", "line_move", "mkt_hfa", "hfa_prime"]
TOTAL_FEATURES = ["sum_epa", "sum_sr", "sum_pass_epa", "sum_rush_epa", "sum_pts", "qb_sum", "lg_pts",
                  "dome", "wind", "cold", "div", "playoff", "mkt_total", "total_move"]
