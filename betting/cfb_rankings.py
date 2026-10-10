#!/usr/bin/env python3
"""Top-25 rank of both teams at kickoff for every FBS game since 2011 (ESPN scoreboard).

ESPN shows the rank TV shows: the AP poll, or the College Football Playoff ranking once it is out.
Writes betting/data/cfb/rankings.csv: game_id, home_id, away_id, home_rank, away_rank (blank = unranked).
Past seasons are cached in data/cfb/rank_cache/; the current season is re-downloaded each run.
Usage: python3 betting/cfb_rankings.py
"""
import os
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "cfb")
CACHE = os.path.join(DATA, "rank_cache")
FIRST = 2011
URL = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"


def week(season, seasontype, wk):
    for _ in range(3):
        try:
            r = requests.get(URL, params={"dates": season, "seasontype": seasontype, "week": wk, "groups": 80,
                                          "limit": 500}, timeout=30)
            if r.status_code == 200:
                break
        except requests.RequestException:
            pass
    else:
        return []
    out = []
    for e in r.json().get("events", []):
        if not e.get("competitions"):
            continue
        c = e["competitions"][0]
        side = {x["homeAway"]: x for x in c["competitors"]}
        if set(side) != {"home", "away"}:
            continue
        rank = {k: (v.get("curatedRank") or {}).get("current") for k, v in side.items()}
        out.append({"game_id": int(e["id"]), "home_id": int(side["home"]["team"]["id"]),
                    "away_id": int(side["away"]["team"]["id"]),
                    "home_rank": rank["home"] if rank["home"] and rank["home"] <= 25 else None,
                    "away_rank": rank["away"] if rank["away"] and rank["away"] <= 25 else None})
    return out


def season_ranks(season):
    jobs = [(season, 2, w) for w in range(1, 18)] + [(season, 3, 1)]
    with ThreadPoolExecutor(6) as ex:
        rows = [r for part in ex.map(lambda j: week(*j), jobs) for r in part]
    return pd.DataFrame(rows).drop_duplicates("game_id")


def main():
    os.makedirs(CACHE, exist_ok=True)
    g = pd.read_csv(os.path.join(DATA, "games.csv"), usecols=["season"])
    current = int(g["season"].max())
    parts = []
    for season in range(FIRST, current + 1):
        path = os.path.join(CACHE, f"ranks_{season}.csv")
        if os.path.exists(path) and season != current:
            parts.append(pd.read_csv(path))
            continue
        d = season_ranks(season)
        d.to_csv(path, index=False)
        parts.append(d)
        print(f"{season}: {len(d)} games, {d[['home_rank', 'away_rank']].notna().any(axis=1).sum()} with a ranked team",
              flush=True)
    out = pd.concat(parts, ignore_index=True).drop_duplicates("game_id", keep="last")
    out.to_csv(os.path.join(DATA, "rankings.csv"), index=False)
    print(f"rankings for {len(out)} games")


if __name__ == "__main__":
    main()
