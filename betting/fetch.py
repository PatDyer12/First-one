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
  injuries.csv    weekly injury reports (Out / Doubtful / Questionable), 2012+
  snaps.csv       snap share for every player in every game, 2012+
  weather.csv     kickoff forecast (Open-Meteo) for the upcoming week's outdoor games
  book_odds.csv   FanDuel + DraftKings current spread / total / moneyline (The Odds API, optional:
                  free key from the-odds-api.com in env ODDS_API_KEY or betting/odds_api_key.txt; 1 request per run)

Usage: python3 betting/fetch.py            (only re-downloads the current season's plays)
       python3 betting/fetch.py --all      (re-download every season)
"""
import io
import os
import sys
import time

import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CACHE = os.path.join(DATA, "pbp")
GAMES_URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
PBP_URL = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{}.parquet"
FIRST = 2009
FIRST_PLAYERS = 2012
REL = "https://github.com/nflverse/nflverse-data/releases/download/{0}/{0}_{1}.parquet"
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


def player_tables(season):
    inj = pd.read_parquet(io.BytesIO(get(REL.format("injuries", season))))
    inj = inj[["season", "week", "team", "gsis_id", "full_name", "position", "report_status"]]
    inj.to_csv(os.path.join(CACHE, f"injuries_{season}.csv"), index=False)
    try:
        sn = pd.read_parquet(io.BytesIO(get(REL.format("snap_counts", season))))
    except requests.HTTPError:
        return
    sn = sn[["game_id", "season", "week", "team", "pfr_player_id", "player", "position", "offense_pct", "defense_pct"]]
    sn.to_csv(os.path.join(CACHE, f"snaps_{season}.csv"), index=False)


def weather(games, season):
    """Kickoff-hour forecast for next week's games that are played outdoors (one batched request)."""
    import stadiums
    up = games[(games["season"] == season) & games["result"].isna()]
    rows = []
    wk = up[(up["week"] == up["week"].min()) & ~up["roof"].isin(["dome", "closed", "retractable"])] if len(up) else up
    if len(wk):
        sites = [stadiums.game_site(g.home_team, g.season, g.stadium_id, g.location == "Neutral") for g in wk.itertuples()]
        params = {"latitude": ",".join(str(s[0]) for s in sites), "longitude": ",".join(str(s[1]) for s in sites),
                  "hourly": "temperature_2m,wind_speed_10m,precipitation", "wind_speed_unit": "mph",
                  "temperature_unit": "fahrenheit", "timezone": "America/New_York",
                  "start_date": wk["gameday"].min(), "end_date": wk["gameday"].max()}
        data = None
        for attempt in range(4):
            try:
                data = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=60).json()
                break
            except Exception as e:
                print("weather retry", attempt + 1, e)
                time.sleep(2 ** (attempt + 1))
        if isinstance(data, dict):
            data = [data]
        for g, loc in zip(wk.itertuples(), data or []):
            h = loc.get("hourly")
            if not h:
                continue
            stamp = f"{g.gameday}T{int(str(g.gametime)[:2]) + 1:02d}:00"  # middle of the game
            if stamp in h["time"]:
                i = h["time"].index(stamp)
                rows.append({"game_id": g.game_id, "temp": h["temperature_2m"][i], "wind": h["wind_speed_10m"][i],
                             "precip": h["precipitation"][i]})
    pd.DataFrame(rows, columns=["game_id", "temp", "wind", "precip"]).to_csv(os.path.join(DATA, "weather.csv"), index=False)
    print("weather forecasts:", len(rows))


NAMES = {"Arizona Cardinals": "ARI", "Atlanta Falcons": "ATL", "Baltimore Ravens": "BAL", "Buffalo Bills": "BUF",
         "Carolina Panthers": "CAR", "Chicago Bears": "CHI", "Cincinnati Bengals": "CIN", "Cleveland Browns": "CLE",
         "Dallas Cowboys": "DAL", "Denver Broncos": "DEN", "Detroit Lions": "DET", "Green Bay Packers": "GB",
         "Houston Texans": "HOU", "Indianapolis Colts": "IND", "Jacksonville Jaguars": "JAX", "Kansas City Chiefs": "KC",
         "Las Vegas Raiders": "LV", "Los Angeles Chargers": "LAC", "Los Angeles Rams": "LA", "Miami Dolphins": "MIA",
         "Minnesota Vikings": "MIN", "New England Patriots": "NE", "New Orleans Saints": "NO", "New York Giants": "NYG",
         "New York Jets": "NYJ", "Philadelphia Eagles": "PHI", "Pittsburgh Steelers": "PIT", "San Francisco 49ers": "SF",
         "Seattle Seahawks": "SEA", "Tampa Bay Buccaneers": "TB", "Tennessee Titans": "TEN", "Washington Commanders": "WAS"}


ESPN_ABBR = {"WSH": "WAS", "LAR": "LA"}


def book_odds():
    """FanDuel + DraftKings prices for this week (DraftKings is free via ESPN; FanDuel needs an Odds API key)."""
    import books
    status = books.fetch("nfl", "americanfootball_nfl",
                         key_of=lambda c: ESPN_ABBR.get(c["team"]["abbreviation"], c["team"]["abbreviation"]),
                         key_of_name=NAMES.get, out_path=os.path.join(DATA, "book_odds.csv"))
    print("book odds:", status)


def main():
    os.makedirs(CACHE, exist_ok=True)
    games = pd.read_csv(io.BytesIO(get(GAMES_URL)))
    # upcoming games at retractable-roof stadiums have no roof listed yet: use the stadium's usual setting
    usual = games.dropna(subset=["roof"]).groupby("stadium_id")["roof"].agg(lambda r: r.mode()[0])
    games["roof"] = games["roof"].fillna(games["stadium_id"].map(usual)).fillna("outdoors")
    games.to_csv(os.path.join(DATA, "games.csv"), index=False)
    current = int(games.loc[games["result"].notna(), "season"].max())
    for season in range(FIRST, current + 1):
        tf, qf = (os.path.join(CACHE, f"{k}_{season}.csv") for k in ("team", "qb"))
        if os.path.exists(tf) and season != current and "--all" not in sys.argv:
            if season < FIRST_PLAYERS or os.path.exists(os.path.join(CACHE, f"injuries_{season}.csv")):
                continue
        else:
            print("plays", season, flush=True)
            team, qb = season_tables(season)
            team.to_csv(tf, index=False)
            qb.to_csv(qf, index=False)
        if season >= FIRST_PLAYERS:
            player_tables(season)
    for k, first in (("team", FIRST), ("qb", FIRST), ("injuries", FIRST_PLAYERS), ("snaps", FIRST_PLAYERS)):
        parts = [pd.read_csv(os.path.join(CACHE, f"{k}_{s}.csv")) for s in range(first, current + 1)
                 if os.path.exists(os.path.join(CACHE, f"{k}_{s}.csv"))]
        pd.concat(parts).to_csv(os.path.join(DATA, f"{k}.csv" if k in ("injuries", "snaps") else f"{k}_games.csv"), index=False)
    weather(games, current)
    book_odds()
    print("games through", games.loc[games["result"].notna(), "gameday"].max())


if __name__ == "__main__":
    main()
