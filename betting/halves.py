#!/usr/bin/env python3
"""First-half scores for every NFL game since 2011, from nflverse play-by-play.

Writes betting/data/halves.csv: game_id, h1_home, h1_away (score at halftime). Past seasons are cached; the
current season is re-read each run. Used by first_half.py.
Usage: python3 betting/halves.py
"""
import io
import os

import pandas as pd
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CACHE = os.path.join(DATA, "pbp")
PBP_URL = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{}.parquet"
FIRST = 2011


def season_halves(season):
    r = requests.get(PBP_URL.format(season), timeout=300)
    r.raise_for_status()
    p = pd.read_parquet(io.BytesIO(r.content), columns=["game_id", "game_half", "total_home_score", "total_away_score"])
    h1 = p[p["game_half"] == "Half1"].groupby("game_id")[["total_home_score", "total_away_score"]].max()
    return h1.rename(columns={"total_home_score": "h1_home", "total_away_score": "h1_away"}).reset_index()


def main():
    os.makedirs(CACHE, exist_ok=True)
    g = pd.read_csv(os.path.join(DATA, "games.csv"), usecols=["season"])
    current = int(g["season"].max())
    parts = []
    for s in range(FIRST, current + 1):
        path = os.path.join(CACHE, f"halves_{s}.csv")
        if not os.path.exists(path) or s == current:
            season_halves(s).to_csv(path, index=False)
            print("halves", s, flush=True)
        parts.append(pd.read_csv(path))
    out = pd.concat(parts, ignore_index=True)
    out.to_csv(os.path.join(DATA, "halves.csv"), index=False)
    print(f"halftime scores for {len(out)} games")


if __name__ == "__main__":
    main()
