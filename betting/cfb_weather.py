#!/usr/bin/env python3
"""Kickoff weather for college football games, history and this week's forecast.

  stadiums   ESPN team pages: home stadium city/state and whether it is indoors
  location   Open-Meteo geocoding (city, state -> lat/lon)
  history    Meteostat bulk hourly station data (nearest station with hourly records), no key needed
  forecast   Open-Meteo forecast for this week's games

Writes betting/data/cfb/weather.csv: game_id, wind (mph), temp (F), precip (mm), indoor, source.
Only games at the home team's own stadium get weather (neutral sites are left out).
Usage: python3 betting/cfb_weather.py
"""
import gzip
import io
import json
import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "cfb")
CACHE = os.path.join(DATA, "weather_cache")
STATES = {"AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado",
          "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
          "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
          "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
          "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
          "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
          "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
          "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
          "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia"}
# steady weather = the 8 hours from 3 before kickoff to 4 after, the part a forecast gets right; a wet hour has
# more than 0.2 mm of rain
WET_MM = 0.2
INDOOR = {"wind": 0.0, "temp": 70.0, "precip": 0.0, "indoor": 1, "wind8": 0.0, "wet8": 0, "source": "indoor"}
MCOLS = ["date", "hour", "temp", "dwpt", "rhum", "prcp", "snow", "wdir", "wspd", "wpgt", "pres", "tsun", "coco"]


def get(url, params=None, tries=3, timeout=20):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r
        except requests.RequestException:
            time.sleep(1.5 * (i + 1))
    return None


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def stadium(tid):
    r = get(f"https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/teams/{tid}")
    v = (r.json().get("venue") if r else None) or {}
    a = v.get("address") or {}
    return {"venue": v.get("fullName"), "city": a.get("city"), "state": a.get("state"),
            "indoor": bool(v.get("indoor")), "lat": None, "lon": None}


def geocode(s):
    r = get("https://geocoding-api.open-meteo.com/v1/search", {"name": s["city"], "count": 10, "countryCode": "US"})
    res = (r.json().get("results") if r else None) or []
    want = STATES.get(s.get("state") or "", "")
    return next((x for x in res if x.get("admin1") == want), res[0] if res else None)


def stadiums(team_ids):
    path = os.path.join(CACHE, "stadiums.json")
    have = json.load(open(path)) if os.path.exists(path) else {}
    todo = [t for t in team_ids if str(t) not in have]
    print(f"stadium lookups: {len(todo)} new, {len(have)} cached", flush=True)
    with ThreadPoolExecutor(8) as ex:
        for i, (tid, s) in enumerate(zip(todo, ex.map(stadium, todo))):
            have[str(tid)] = s
            if i % 50 == 49:
                print(f"  stadiums {i + 1}/{len(todo)}", flush=True)
                json.dump(have, open(path, "w"), indent=0)
    need = [(t, s) for t, s in have.items() if s["lat"] is None and s.get("city")]
    print(f"geocoding {len(need)}", flush=True)
    with ThreadPoolExecutor(8) as ex:
        for (tid, s), pick in zip(need, ex.map(lambda x: geocode(x[1]), need)):
            if pick:
                s["lat"], s["lon"] = pick["latitude"], pick["longitude"]
    json.dump(have, open(path, "w"), indent=0)
    return have


def stations():
    path = os.path.join(CACHE, "stations.json")
    if not os.path.exists(path):
        r = get("https://bulk.meteostat.net/v2/stations/lite.json.gz", timeout=120)
        raw = json.loads(gzip.decompress(r.content))
        keep = []
        for s in raw:
            inv = (s.get("inventory") or {}).get("hourly") or {}
            loc = s.get("location") or {}
            if inv.get("start") and inv.get("end") and loc.get("latitude") is not None and s.get("country") == "US":
                keep.append({"id": s["id"], "lat": loc["latitude"], "lon": loc["longitude"],
                             "start": inv["start"], "end": inv["end"]})
        json.dump(keep, open(path, "w"))
    return json.load(open(path))


def nearest_station(lat, lon, sts):
    best = None
    for s in sts:
        if s["start"] > "2013-01-01" or s["end"] < "2025-01-01":
            continue
        d = km((lat, lon), (s["lat"], s["lon"]))
        if best is None or d < best[0]:
            best = (d, s["id"])
    return best


def station_hours(sid):
    path = os.path.join(CACHE, f"st_{sid}.parquet")
    if os.path.exists(path) and time.time() - os.path.getmtime(path) < 3 * 86400:
        return pd.read_parquet(path)
    r = get(f"https://bulk.meteostat.net/v2/hourly/{sid}.csv.gz", timeout=120)
    if r is None:
        return None
    d = pd.read_csv(io.BytesIO(gzip.decompress(r.content)), header=None, names=MCOLS, usecols=range(13))
    d = d[d["date"] >= "2010-08-01"][["date", "hour", "temp", "prcp", "wspd"]]
    d.to_parquet(path, index=False)
    return d


def main():
    os.makedirs(CACHE, exist_ok=True)
    g = pd.read_csv(os.path.join(DATA, "games.csv"), low_memory=False)
    g = g[((g.home_division == "fbs") | (g.away_division == "fbs")) & (g.season >= 2011)].copy()
    g["kick"] = pd.to_datetime(g["start_date"], utc=True, errors="coerce")
    home = g[g["neutral_site"] != True]  # noqa: E712
    st = stadiums(sorted(home["home_id"].dropna().astype(int).unique()))
    sts = stations()
    rows = []
    by_station = {}
    for tid, s in st.items():
        if s["lat"] is None:
            continue
        ns = nearest_station(s["lat"], s["lon"], sts)
        s["station"], s["station_km"] = (ns[1], round(ns[0], 1)) if ns and ns[0] <= 60 else (None, None)
        if s["station"]:
            by_station.setdefault(s["station"], []).append(int(tid))
    print(f"stadiums {len(st)}, with a station within 60 km: {sum(1 for s in st.values() if s.get('station'))}, "
          f"indoor: {sum(1 for s in st.values() if s['indoor'])}", flush=True)
    done = home[home["result"].notna()] if "result" in home else home[home["completed"] == True]  # noqa: E712
    ids = list(by_station)
    with ThreadPoolExecutor(8) as ex:
        hours = dict(zip(ids, ex.map(station_hours, ids)))
    print(f"station files: {sum(1 for v in hours.values() if v is not None)}/{len(ids)}", flush=True)
    for i, (sid, tids) in enumerate(by_station.items()):
        d = hours[sid]
        if d is None or d.empty:
            continue
        d = d.dropna(subset=["wspd", "temp"]).copy()
        d["ts"] = pd.to_datetime(d["date"] + " " + d["hour"].astype(str) + ":00", utc=True)
        d = d.set_index("ts").sort_index()
        games = home[home["home_id"].isin(tids) & (home["completed"] == True) & home["kick"].notna()]  # noqa: E712
        for r in games.itertuples(index=False):
            s = st[str(int(r.home_id))]
            if s["indoor"]:
                rows.append(dict(INDOOR, game_id=r.game_id))
                continue
            t = (r.kick + pd.Timedelta(hours=1.5)).floor("h")
            w = d.loc[t - pd.Timedelta(hours=1): t + pd.Timedelta(hours=1)]
            k = r.kick.floor("h")
            w8 = d.loc[k - pd.Timedelta(hours=3): k + pd.Timedelta(hours=4)]
            if w.empty:
                continue
            rows.append({"game_id": r.game_id, "wind": round(float(w["wspd"].mean()) * 0.621371, 1),
                         "temp": round(float(w["temp"].mean()) * 9 / 5 + 32, 1),
                         "precip": round(float(w["prcp"].fillna(0).sum()), 1), "indoor": 0,
                         "wind8": round(float(w8["wspd"].mean()) * 0.621371, 1) if len(w8) >= 5 else np.nan,
                         "wet8": int((w8["prcp"].fillna(0) > WET_MM).sum()) if len(w8) >= 5 else np.nan,
                         "source": f"station {sid}"})
        if i % 25 == 0:
            print(f"  stations {i + 1}/{len(by_station)}", flush=True)
    # this week's forecast
    up = home[home["completed"] != True]  # noqa: E712
    now = pd.Timestamp.now(tz="UTC")
    up = up[(up["kick"] >= now - pd.Timedelta(hours=6)) & (up["kick"] <= now + pd.Timedelta(days=8))]
    locs = []
    for r in up.itertuples(index=False):
        s = st.get(str(int(r.home_id)))
        if not s or s["lat"] is None:
            continue
        if s["indoor"]:
            rows.append(dict(INDOOR, game_id=r.game_id))
        else:
            locs.append((r, s))
    def forecast(part):
        days = [r.kick.strftime("%Y-%m-%d") for r, _ in part]
        resp = get("https://api.open-meteo.com/v1/forecast", {
            "latitude": ",".join(str(s["lat"]) for _, s in part), "longitude": ",".join(str(s["lon"]) for _, s in part),
            "hourly": "temperature_2m,wind_speed_10m,precipitation", "wind_speed_unit": "mph",
            "temperature_unit": "fahrenheit", "timezone": "UTC",
            "start_date": (pd.Timestamp(min(days)) - pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            "end_date": (pd.Timestamp(max(days)) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")}, timeout=45)
        if resp is None:
            if len(part) > 1:  # split and retry
                return forecast(part[:len(part) // 2]) + forecast(part[len(part) // 2:])
            print("forecast unavailable:", part[0][0].away, "@", part[0][0].home)
            return []
        data = resp.json()
        data = data if isinstance(data, list) else [data]
        got = []
        for (r, s), loc in zip(part, data):
            h = loc.get("hourly") or {}
            if not h.get("time"):
                continue
            f = pd.DataFrame({"wind": h["wind_speed_10m"], "temp": h["temperature_2m"], "prcp": h["precipitation"]},
                             index=pd.to_datetime(h["time"], utc=True), dtype=float)
            t = (r.kick + pd.Timedelta(hours=1.5)).floor("h")
            k = r.kick.floor("h")
            w, w8 = f.loc[t - pd.Timedelta(hours=1): t + pd.Timedelta(hours=1)], f.loc[k - pd.Timedelta(hours=3): k + pd.Timedelta(hours=4)]
            if w.empty or w["wind"].isna().all():
                continue
            got.append({"game_id": r.game_id, "wind": round(w["wind"].mean(), 1), "temp": round(w["temp"].mean(), 1),
                        "precip": round(w["prcp"].fillna(0).sum(), 1), "indoor": 0, "wind8": round(w8["wind"].mean(), 1),
                        "wet8": int((w8["prcp"].fillna(0) > WET_MM).sum()), "source": "forecast"})
        return got

    for chunk in range(0, len(locs), 20):
        rows += forecast(locs[chunk:chunk + 20])
    out = pd.DataFrame(rows).drop_duplicates("game_id", keep="last")
    out.to_csv(os.path.join(DATA, "weather.csv"), index=False)
    json.dump(st, open(os.path.join(CACHE, "stadiums.json"), "w"), indent=0)
    print(f"weather for {len(out)} games ({(out.source == 'forecast').sum()} forecasts, {(out.indoor == 1).sum()} indoor)")


if __name__ == "__main__":
    main()
