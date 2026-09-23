#!/usr/bin/env python3
"""Download NFL schedules/lines and play-by-play, boil them down to small tables.

Sources (all free, from nflverse):
  games.csv             every game since 1999 with scores, closing spread/total/moneylines,
                        rest, roof, weather and starting QBs
  play_by_play_YYYY     every play since 1999 with EPA and success

Writes to betting/data/:
  games.csv       schedule + lines + results
  team_games.csv  one row per team per game: offensive EPA/play, success, pass/rush EPA, plays
  qb_games.csv    one row per QB per game: dropbacks and EPA

Usage: python3 betting/fetch.py            (only re-downloads the current season's plays)
       python3 betting/fetch.py --all      (re-download every season)
"""
import io
import os
import sys

import pandas as pd
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CACHE = os.path.join(DATA, "pbp")
GAMES_URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
PBP_URL = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{}.parquet"
FIRST = 2009
COLS = ["game_id", "season", "week", "posteam", "defteam", "play_type", "pass", "rush", "epa", "success",
        "qb_epa", "passer_player_id", "passer_player_name", "rusher_player_id", "qb_dropback",
        "interception", "fumble_lost", "wp", "half_seconds_remaining", "qtr"]


def get(url):
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    return r.content


def season_tables(season):
    pbp = pd.read_parquet(io.BytesIO(get(PBP_URL.format(season))), columns=COLS)
    p = pbp[(pbp["pass"] == 1) | (pbp["rush"] == 1)].dropna(subset=["epa", "posteam"]).copy()
    # Garbage time (win prob outside 5-95% in the 4th quarter) says little about true strength.
    p["live"] = ~((p["qtr"] == 4) & ((p["wp"] < 0.05) | (p["wp"] > 0.95)))
    p["to"] = p["interception"].fillna(0) + p["fumble_lost"].fillna(0)
    lv = p[p["live"]]
    g = lv.groupby(["game_id", "season", "week", "posteam", "defteam"])
    team = g.agg(plays=("epa", "size"), epa=("epa", "mean"), sr=("success", "mean")).reset_index()
    pas = lv[lv["pass"] == 1].groupby(["game_id", "posteam"])["epa"].agg(pass_epa="mean", dropbacks="size")
    rus = lv[lv["rush"] == 1].groupby(["game_id", "posteam"])["epa"].agg(rush_epa="mean")
    to = p.groupby(["game_id", "posteam"])["to"].sum().rename("turnovers")
    allp = p.groupby(["game_id", "posteam"])["epa"].size().rename("all_plays")
    team = team.join(pas, on=["game_id", "posteam"]).join(rus, on=["game_id", "posteam"])
    team = team.join(to, on=["game_id", "posteam"]).join(allp, on=["game_id", "posteam"])
    team = team.rename(columns={"posteam": "team", "defteam": "opp"})

    d = p[(p["qb_dropback"] == 1) & p["passer_player_id"].notna()]
    qb = d.groupby(["game_id", "season", "week", "posteam", "passer_player_id"]).agg(
        name=("passer_player_name", "last"), dropbacks=("qb_epa", "size"), qb_epa=("qb_epa", "sum")).reset_index()
    return team, qb.rename(columns={"posteam": "team", "passer_player_id": "qb_id"})


def main():
    os.makedirs(CACHE, exist_ok=True)
    games = pd.read_csv(io.BytesIO(get(GAMES_URL)))
    games.to_csv(os.path.join(DATA, "games.csv"), index=False)
    current = int(games.loc[games["result"].notna(), "season"].max())
    for season in range(FIRST, current + 1):
        tf, qf = (os.path.join(CACHE, f"{k}_{season}.csv") for k in ("team", "qb"))
        if os.path.exists(tf) and season != current and "--all" not in sys.argv:
            continue
        print("plays", season, flush=True)
        team, qb = season_tables(season)
        team.to_csv(tf, index=False)
        qb.to_csv(qf, index=False)
    for k in ("team", "qb"):
        parts = [pd.read_csv(os.path.join(CACHE, f"{k}_{s}.csv")) for s in range(FIRST, current + 1)]
        pd.concat(parts).to_csv(os.path.join(DATA, f"{k}_games.csv"), index=False)
    print("games through", games.loc[games["result"].notna(), "gameday"].max())


if __name__ == "__main__":
    main()
