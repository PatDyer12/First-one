"""Live FanDuel / DraftKings prices.

DraftKings: free, straight from ESPN's scoreboard feed (ESPN shows DraftKings lines on every game).
FanDuel:    needs a free key from the-odds-api.com (env ODDS_API_KEY or betting/odds_api_key.txt);
            with a key, DraftKings is also re-read from there so both books are from the same moment.

Rows: away, home, book, market (spread/total/ml), side (home/away/over/under), line, odds
  spread line uses the model's convention: expected home margin (home -3.5 -> 3.5)
"""
import os
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ESPN = "https://site.api.espn.com/apis/site/v2/sports/football/{}/scoreboard"
ODDS_API = "https://api.the-odds-api.com/v4/sports/{}/odds"
COLUMNS = ["away", "home", "book", "market", "side", "line", "odds"]


def get_json(url, params=None):
    for attempt in range(4):
        try:
            r = requests.get(url, params=params, timeout=60)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            if attempt == 3 or (getattr(e, "response", None) is not None and e.response.status_code in (401, 403, 422)):
                raise
            time.sleep(2 ** (attempt + 1))


def _num(s):
    s = str(s).lstrip("ou").replace("+", "")
    return float(s) if s not in ("", "None", "OFF", "EVEN") else (100.0 if s == "EVEN" else None)


def espn_draftkings(league, key_of, params=None):
    """league: 'nfl' or 'college-football'. key_of(competitor dict) -> team key used by the model."""
    rows = []
    for ev in get_json(ESPN.format(league), params).json().get("events", []):
        comp = ev["competitions"][0]
        teams = {c["homeAway"]: c for c in comp["competitors"]}
        if "home" not in teams or "away" not in teams:
            continue
        home, away = key_of(teams["home"]), key_of(teams["away"])
        for o in comp.get("odds", []):
            if "draftkings" not in o.get("provider", {}).get("name", "").lower():
                continue
            ps, tot, ml = o.get("pointSpread", {}), o.get("total", {}), o.get("moneyline", {})
            for side in ("home", "away"):
                c = ps.get(side, {}).get("close", {})
                pt, od = _num(c.get("line")), _num(c.get("odds"))
                if pt is not None and od is not None:
                    rows.append([away, home, "DraftKings", "spread", side, -pt if side == "home" else pt, od])
                c = ml.get(side, {}).get("close", {})
                od = _num(c.get("odds"))
                if od is not None:
                    rows.append([away, home, "DraftKings", "ml", side, 0, od])
            for side in ("over", "under"):
                c = tot.get(side, {}).get("close", {})
                pt, od = _num(c.get("line")), _num(c.get("odds"))
                if pt is not None and od is not None:
                    rows.append([away, home, "DraftKings", "total", side, pt, od])
    return rows


def api_key():
    key = os.environ.get("ODDS_API_KEY")
    path = os.path.join(HERE, "odds_api_key.txt")
    if not key and os.path.exists(path):
        key = open(path).read().strip()
    return key or None


def odds_api(sport_key, key_of_name):
    """FanDuel + DraftKings from The Odds API. key_of_name(full team name) -> model team key (or None)."""
    key = api_key()
    if not key:
        return None, None
    r = get_json(ODDS_API.format(sport_key), {"apiKey": key, "bookmakers": "fanduel,draftkings",
                                              "markets": "h2h,spreads,totals", "oddsFormat": "american"})
    rows = []
    for ev in r.json():
        home, away = key_of_name(ev["home_team"]), key_of_name(ev["away_team"])
        if home is None or away is None:
            continue
        for bk in ev.get("bookmakers", []):
            for mk in bk.get("markets", []):
                for o in mk.get("outcomes", []):
                    if mk["key"] == "totals":
                        rows.append([away, home, bk["title"], "total", o["name"].lower(), o["point"], o["price"]])
                        continue
                    side = "home" if o["name"] == ev["home_team"] else "away"
                    if mk["key"] == "h2h":
                        rows.append([away, home, bk["title"], "ml", side, 0, o["price"]])
                    elif mk["key"] == "spreads":
                        rows.append([away, home, bk["title"], "spread", side,
                                     -o["point"] if side == "home" else o["point"], o["price"]])
    return rows, r.headers.get("x-requests-remaining", "?")


def fetch(league, sport_key, key_of, key_of_name, out_path, espn_params=None):
    """Write FanDuel/DraftKings prices to out_path. Returns a one-line status."""
    import pandas as pd
    rows, note = [], []
    try:
        api_rows, left = odds_api(sport_key, key_of_name)
    except requests.RequestException as e:
        api_rows, left = None, None
        note.append(f"Odds API failed ({e})")
    if api_rows is not None:
        rows += api_rows
        note.append(f"FanDuel+DraftKings from Odds API ({left} requests left this month)")
    if not any(r[2] == "DraftKings" for r in rows):
        try:
            dk = espn_draftkings(league, key_of, espn_params)
            rows += dk
            note.append(f"DraftKings from ESPN ({len(dk)} prices)")
        except requests.RequestException as e:
            note.append(f"ESPN DraftKings failed ({e})")
    if api_rows is None:
        note.append("no FanDuel (add a free the-odds-api.com key to betting/odds_api_key.txt)")
    pd.DataFrame(rows, columns=COLUMNS).to_csv(out_path, index=False)
    return "; ".join(note)
