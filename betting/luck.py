#!/usr/bin/env python3
"""Luck measures for every team going into every game (season to date, pre-game information only).

  close_net   one-score wins minus one-score losses (8 points or less). Close games are close to coin flips,
              so a 5-1 record in them says more about luck than about the team.
  luck_pg     points margin minus play-by-play (EPA) margin, per game: points the scoreboard gave a team beyond
              how well it played snap to snap (special teams, red-zone bounces, fumble luck, late scores).
  to_pg       turnover margin per game (NFL): takeaways repeat much less than people think.
  epa_pg      EPA margin per game (how well the team actually plays), and w / l (straight-up record)

Used by angles.py for the luck-regression angles: the market and the public read records and scoreboards,
so teams whose results run ahead of their play may be overrated, and the reverse.
"""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CLOSE = 8


def team_luck(sport):
    d = os.path.join(HERE, "data") if sport == "nfl" else os.path.join(HERE, "data", "cfb")
    g = pd.read_csv(os.path.join(d, "games.csv"), low_memory=False)
    t = pd.read_csv(os.path.join(d, "team_games.csv"))
    if sport == "nfl":
        g = g[g["game_type"] != "PRE"]
        g["date"] = pd.to_datetime(g["gameday"])
        hk, ak, hs, as_ = "home_team", "away_team", "home_score", "away_score"
    else:
        g = g[(g["home_division"] == "fbs") | (g["away_division"] == "fbs")]
        g["date"] = pd.to_datetime(g["start_date"], utc=True, errors="coerce").dt.tz_localize(None)
        hk, ak, hs, as_ = "home_id", "away_id", "home_points", "away_points"
    rows = []
    for side, team, opp, pf, pa in (("home", hk, ak, hs, as_), ("away", ak, hk, as_, hs)):
        x = g[["game_id", "season", "date", team, opp, pf, pa]].rename(columns={team: "team", opp: "opp", pf: "pf", pa: "pa"})
        rows.append(x)
    L = pd.concat(rows, ignore_index=True)
    L["margin"] = L["pf"] - L["pa"]
    # play-by-play margin: own EPA total minus the opponent's (garbage time already removed in team_games)
    t = t.copy()
    t["epa_tot"] = t["epa"] * t["plays"]
    own = t[["game_id", "team", "epa_tot"] + (["turnovers"] if "turnovers" in t else [])]
    L = L.merge(own, on=["game_id", "team"], how="left")
    opp = own.rename(columns={"team": "opp", "epa_tot": "opp_epa_tot", "turnovers": "opp_turnovers"})
    L = L.merge(opp, on=["game_id", "opp"], how="left")
    L["epa_margin"] = L["epa_tot"] - L["opp_epa_tot"]
    if "turnovers" in L:
        L["to_margin"] = L["opp_turnovers"] - L["turnovers"]
    else:
        L["to_margin"] = np.nan
    L = L.sort_values(["team", "date", "game_id"]).reset_index(drop=True)
    done = L["margin"].notna()
    L["w"] = (done & (L["margin"] > 0)).astype(int)
    L["l"] = (done & (L["margin"] < 0)).astype(int)
    L["cw"] = (done & (L["margin"] > 0) & (L["margin"] <= CLOSE)).astype(int)
    L["cl"] = (done & (L["margin"] < 0) & (L["margin"] >= -CLOSE)).astype(int)
    L["luck"] = np.where(done & L["epa_margin"].notna(), L["margin"] - L["epa_margin"], np.nan)
    L["n"] = done.astype(int)
    grp = L.groupby(["team", "season"], sort=False)
    out = L[["game_id", "team"]].copy()
    for c in ("w", "l", "cw", "cl", "n"):
        out[c] = grp[c].transform(lambda s: s.shift().fillna(0).cumsum())
    for c in ("luck", "to_margin", "epa_margin"):
        out[c + "_sum"] = grp[c].transform(lambda s: s.shift().fillna(0).cumsum())
        out[c + "_n"] = grp[c].transform(lambda s: s.shift().notna().cumsum())
    out["close_net"] = out["cw"] - out["cl"]
    out["luck_pg"] = out["luck_sum"] / out["luck_n"].where(out["luck_n"] > 0)
    out["to_pg"] = out["to_margin_sum"] / out["to_margin_n"].where(out["to_margin_n"] > 0)
    out["epa_pg"] = out["epa_margin_sum"] / out["epa_margin_n"].where(out["epa_margin_n"] > 0)
    out["wpct"] = out["w"] / (out["w"] + out["l"]).where(lambda x: x > 0)
    return out[["game_id", "team", "n", "w", "l", "wpct", "close_net", "luck_pg", "to_pg", "epa_pg"]]
