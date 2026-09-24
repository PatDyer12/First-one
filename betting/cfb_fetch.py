#!/usr/bin/env python3
"""Download college football schedules, lines and play-by-play; boil them down to small tables.

Sources (free):
  cfbfastR-data schedules   every game with teams, divisions, neutral site, final score
  ESPN play-by-play         every play with EPA and success, plus each game's spread and total
                            (sportsdataverse-data release espn_cfb_pbp)
  ESPN scoreboard           this week's DraftKings spread / total / moneyline (FanDuel via Odds API key)

Writes betting/data/cfb/: games.csv, team_games.csv, book_odds.csv

Usage: python3 betting/cfb_fetch.py         (re-downloads only the current season's plays)
       python3 betting/cfb_fetch.py --all
"""
import io
import os
import sys

import numpy as np
import pandas as pd
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import books  # noqa: E402

DATA = os.path.join(HERE, "data", "cfb")
CACHE = os.path.join(DATA, "pbp")
FIRST = 2010
SCHED = "https://raw.githubusercontent.com/sportsdataverse/cfbfastR-data/main/schedules/csv/cfb_schedules_{}.csv"
PBP = "https://github.com/sportsdataverse/sportsdataverse-data/releases/download/espn_cfb_pbp/play_by_play_{}.parquet"
PBP_COLS = ["game_id", "pos_team_id", "def_pos_team_id", "EPA", "EPA_success", "rush", "pass", "scrimmage_play",
            "period", "pos_score_diff_start", "homeTeamId", "awayTeamId", "homeTeamSpread", "overUnder",
            "gameSpreadAvailable"]


def season_tables(season):
    raw = requests.get(PBP.format(season), timeout=300)
    raw.raise_for_status()
    p = pd.read_parquet(io.BytesIO(raw.content), columns=PBP_COLS)
    lines = p.groupby("game_id").agg(spread_line=("homeTeamSpread", "first"), total_line=("overUnder", "first"),
                                     has_line=("gameSpreadAvailable", "first")).reset_index()
    lines.loc[lines["has_line"] != True, ["spread_line", "total_line"]] = np.nan  # noqa: E712
    for c in ("spread_line", "total_line"):
        lines.loc[lines[c] == 0, c] = np.nan if c == "total_line" else lines.loc[lines[c] == 0, c]
    s = p[(p["scrimmage_play"] == True) & (p["rush"] | p["pass"])].dropna(subset=["EPA", "pos_team_id"]).copy()  # noqa: E712
    # garbage time (Bill Connelly's definition): lead > 38 in Q2, > 28 in Q3, > 22 in Q4
    lead = s["pos_score_diff_start"].abs()
    per = pd.to_numeric(s["period"], errors="coerce")
    garbage = ((per == 2) & (lead > 38)) | ((per == 3) & (lead > 28)) | ((per >= 4) & (lead > 22))
    s = s[~garbage]
    s["success"] = s["EPA_success"].astype(float)
    g = s.groupby(["game_id", "pos_team_id", "def_pos_team_id"])
    team = g.agg(plays=("EPA", "size"), epa=("EPA", "mean"), sr=("success", "mean")).reset_index()
    pas = s[s["pass"] == True].groupby(["game_id", "pos_team_id"])["EPA"].mean().rename("pass_epa")  # noqa: E712
    rus = s[s["rush"] == True].groupby(["game_id", "pos_team_id"])["EPA"].mean().rename("rush_epa")  # noqa: E712
    allp = p[(p["scrimmage_play"] == True)].groupby(["game_id", "pos_team_id"]).size().rename("all_plays")  # noqa: E712
    team = team.join(pas, on=["game_id", "pos_team_id"]).join(rus, on=["game_id", "pos_team_id"]).join(allp, on=["game_id", "pos_team_id"])
    team = team.rename(columns={"pos_team_id": "team", "def_pos_team_id": "opp"})
    return team, lines[["game_id", "spread_line", "total_line"]]


def main():
    os.makedirs(CACHE, exist_ok=True)
    sched = []
    season = FIRST
    while True:
        r = requests.get(SCHED.format(season), timeout=120)
        if r.status_code != 200:
            break
        sched.append(pd.read_csv(io.BytesIO(r.content), low_memory=False))
        season += 1
    games = pd.concat(sched, ignore_index=True)
    current = int(games["season"].max())
    for season in range(FIRST, current + 1):
        tf, lf = (os.path.join(CACHE, f"{k}_{season}.csv") for k in ("team", "lines"))
        if os.path.exists(tf) and season != current and "--all" not in sys.argv:
            continue
        print("plays", season, flush=True)
        try:
            team, lines = season_tables(season)
        except requests.HTTPError as e:
            print("  no play-by-play:", e)
            continue
        team.to_csv(tf, index=False)
        lines.to_csv(lf, index=False)
    team = pd.concat(pd.read_csv(os.path.join(CACHE, f"team_{s}.csv")) for s in range(FIRST, current + 1)
                     if os.path.exists(os.path.join(CACHE, f"team_{s}.csv")))
    lines = pd.concat(pd.read_csv(os.path.join(CACHE, f"lines_{s}.csv")) for s in range(FIRST, current + 1)
                      if os.path.exists(os.path.join(CACHE, f"lines_{s}.csv")))
    keep = ["game_id", "season", "week", "season_type", "start_date", "neutral_site", "conference_game", "venue",
            "home_id", "home_team", "home_division", "home_conference", "home_points",
            "away_id", "away_team", "away_division", "away_conference", "away_points", "completed"]
    games = games[keep].drop_duplicates("game_id").merge(lines, on="game_id", how="left")
    games.to_csv(os.path.join(DATA, "games.csv"), index=False)
    team.to_csv(os.path.join(DATA, "team_games.csv"), index=False)

    names = {}
    try:
        t = books.get_json("https://site.api.espn.com/apis/site/v2/sports/football/college-football/teams",
                           {"limit": 1000}).json()
        names = {x["team"]["displayName"]: int(x["team"]["id"]) for x in t["sports"][0]["leagues"][0]["teams"]}
    except Exception as e:  # only needed to match FanDuel names
        print("team list failed:", e)
    status = books.fetch("college-football", "americanfootball_ncaaf", key_of=lambda c: int(c["team"]["id"]),
                         key_of_name=names.get, out_path=os.path.join(DATA, "book_odds.csv"),
                         espn_params={"groups": 80, "limit": 400})
    print("book odds:", status)
    done = games[games["completed"] == True]  # noqa: E712
    print(f"{len(games)} games, {len(done)} final, lines on {games['spread_line'].notna().mean():.0%}; "
          f"latest {done['start_date'].max()}")


if __name__ == "__main__":
    main()
