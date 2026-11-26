#!/usr/bin/env python3
"""Touchdown scorers for one day's games: who has scored most often on Thanksgiving, and an anytime-TD model.

History: every regular-season Thanksgiving game since 1999 (nflverse weekly player stats). A rushing, receiving or
return TD counts, the way books grade "anytime touchdown"; passing TDs don't.
Model: logistic regression on 2022-2025 player-games, all pre-game: season-to-date touches inside the 10 and the 20,
share of the team's touches inside the 10, carries and targets per game, TD rate, last season's TD rate, position,
and the team's implied points from the closing line. Tested out of sample on 2025 before predicting today. The free
feeds carry no anytime-TD prices, so it gives fair odds: a player is worth a bet only if the book pays more.

Writes betting/data/td_scorers.json. Usage: python3 betting/td_scorers.py [YYYY-MM-DD]
"""
import json
import os
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CACHE = os.path.join(DATA, "pbp")
FIX = {"OAK": "LV", "SD": "LAC", "STL": "LA", "LAR": "LA"}
SKILL = ("QB", "RB", "FB", "WR", "TE")
STATS_URL = "https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_{}.parquet"
PBP_URL = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{}.parquet"
PBP_COLS = ["game_id", "week", "posteam", "yardline_100", "rush_attempt", "pass_attempt", "rusher_player_id",
            "receiver_player_id", "season_type", "two_point_attempt"]
FEATS = ["rz10_pg", "rz20_pg", "rz10_share", "car_pg", "tgt_pg", "td_pg", "td_last", "implied", "is_rb", "is_te", "is_qb"]


def fetch(url, path, refresh):
    if not os.path.exists(path) or refresh:
        r = requests.get(url, timeout=300)
        r.raise_for_status()
        with open(path, "wb") as f:
            f.write(r.content)
    return path


def weekly(seasons, current):
    os.makedirs(CACHE, exist_ok=True)
    with ThreadPoolExecutor(8) as ex:
        paths = list(ex.map(lambda y: fetch(STATS_URL.format(y), os.path.join(CACHE, f"stats_week_{y}.parquet"), y == current), seasons))
    w = pd.concat([pd.read_parquet(p) for p in paths], ignore_index=True)
    w = w[(w["season_type"] == "REG") & w["player_id"].notna()].copy()
    w["team"] = w["team"].replace(FIX)
    w["tds"] = w[["rushing_tds", "receiving_tds", "special_teams_tds"]].fillna(0).sum(axis=1)
    return w


def red_zone(seasons, current):
    """Carries + targets inside the 10 and the 20 per player-game (two-point tries left out)."""
    with ThreadPoolExecutor(5) as ex:
        paths = list(ex.map(lambda y: fetch(PBP_URL.format(y), os.path.join(CACHE, f"pbp_raw_{y}.parquet"), y == current), seasons))
    p = pd.concat([pd.read_parquet(x, columns=PBP_COLS) for x in paths], ignore_index=True)
    p = p[(p["season_type"] == "REG") & (p["two_point_attempt"] != 1)]
    out = []
    for col, flag in (("rusher_player_id", "rush_attempt"), ("receiver_player_id", "pass_attempt")):
        x = p[(p[flag] == 1) & p[col].notna()]
        out.append(pd.DataFrame({"game_id": x["game_id"], "player_id": x[col], "team": x["posteam"].replace(FIX),
                                 "rz10": (x["yardline_100"] <= 10).astype(int), "rz20": (x["yardline_100"] <= 20).astype(int)}))
    rz = pd.concat(out).groupby(["game_id", "player_id", "team"], as_index=False)[["rz10", "rz20"]].sum()
    return rz


def implied_points(g):
    """Each team's implied points from the closing line (spread_line = home margin)."""
    g = g[g["spread_line"].notna() & g["total_line"].notna()]
    home = pd.DataFrame({"game_id": g["game_id"], "team": g["home_team"].replace(FIX),
                         "implied": (g["total_line"] + g["spread_line"]) / 2})
    away = pd.DataFrame({"game_id": g["game_id"], "team": g["away_team"].replace(FIX),
                         "implied": (g["total_line"] - g["spread_line"]) / 2})
    return pd.concat([home, away], ignore_index=True)


def features(w, rz, imp):
    """Pre-game, season-to-date features for every skill player-game."""
    x = w[w["position"].isin(SKILL)][["player_id", "player_display_name", "position", "season", "week", "game_id", "team",
                                      "carries", "targets", "tds"]].copy()
    x = x.merge(rz.drop(columns="team"), on=["game_id", "player_id"], how="left").fillna({"rz10": 0, "rz20": 0})
    team_rz = rz.groupby(["game_id", "team"], as_index=False)["rz10"].sum().rename(columns={"rz10": "team_rz10"})
    x = x.merge(team_rz, on=["game_id", "team"], how="left").fillna({"team_rz10": 0})
    x = x.sort_values(["player_id", "season", "week"])
    grp = x.groupby(["player_id", "season"])
    for c in ("carries", "targets", "rz10", "rz20", "tds", "team_rz10"):
        x[f"cum_{c}"] = grp[c].cumsum() - x[c]
    x["cum_td_games"] = grp["tds"].transform(lambda s: (s > 0).cumsum()) - (x["tds"] > 0).astype(int)
    x["n"] = grp.cumcount()
    n = x["n"].clip(lower=1)
    x["rz10_pg"], x["rz20_pg"] = x["cum_rz10"] / n, x["cum_rz20"] / n
    x["car_pg"], x["tgt_pg"], x["td_pg"] = x["cum_carries"] / n, x["cum_targets"] / n, x["cum_td_games"] / n
    x["rz10_share"] = x["cum_rz10"] / x["cum_team_rz10"].clip(lower=1)
    last = x.groupby(["player_id", "season"]).agg(g=("tds", "size"), tg=("tds", lambda s: (s > 0).sum())).reset_index()
    last["season"] += 1
    last["td_last"] = last["tg"] / last["g"]
    x = x.merge(last[["player_id", "season", "td_last"]], on=["player_id", "season"], how="left")
    x["td_last"] = x["td_last"].fillna(x.groupby("position")["td_pg"].transform("mean"))
    x = x.merge(imp, on=["game_id", "team"], how="left")
    for p in ("RB", "TE", "QB"):
        x[f"is_{p.lower()}"] = (x["position"] == p).astype(int)
    x["y"] = (x["tds"] > 0).astype(int)
    return x


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return " ".join(w for w in s.replace(".", "").replace("-", " ").replace("'", "").split() if w not in ("jr", "sr", "ii", "iii", "iv"))


def dk_market(day):
    """Players DraftKings lists an anytime-TD market for (ESPN's feed: the names, no prices)."""
    sb = requests.get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
                      params={"dates": day.replace("-", "")}, timeout=30).json()
    refs = []
    for e in sb.get("events", []):
        base = f"http://sports.core.api.espn.com/v2/sports/football/leagues/nfl/events/{e['id']}/competitions/{e['id']}/odds"
        try:
            provs = requests.get(base, timeout=30).json().get("items", [])
        except Exception:
            continue
        for it in provs:
            if "propBets" not in it:
                continue
            pid = it["provider"]["id"]
            for page in (1, 2, 3):
                r = requests.get(f"{base}/{pid}/propBets", params={"limit": 1000, "page": page}, timeout=30).json()
                refs += [x["athlete"]["$ref"] for x in r.get("items", [])
                         if x.get("type", {}).get("name") == "Anytime Touchdown Scorer" and "$ref" in x.get("athlete", {})]
                if page >= r.get("pageCount", 1):
                    break
            break
    def name(ref):
        try:
            return norm(requests.get(ref, timeout=30).json().get("displayName", ""))
        except Exception:
            return None
    with ThreadPoolExecutor(12) as ex:
        return {n for n in ex.map(name, sorted(set(refs))) if n}


def fair(p):
    return int(round(-100 * p / (1 - p))) if p >= 0.5 else int(round(100 * (1 - p) / p))


def main():
    day = sys.argv[1] if len(sys.argv) > 1 else pd.Timestamp.now(tz="America/New_York").strftime("%Y-%m-%d")
    g = pd.read_csv(os.path.join(DATA, "games.csv"), low_memory=False)
    g = g[g["game_type"] == "REG"].copy()
    current = int(g["season"].max())
    today = g[g["gameday"] == day]
    teams = set(today["home_team"].replace(FIX)) | set(today["away_team"].replace(FIX))
    w = weekly(range(1999, current + 1), current)

    # ---- Thanksgiving history for today's players
    g["date"] = pd.to_datetime(g["gameday"])
    tg = g[(g["weekday"] == "Thursday") & (g["date"].dt.month == 11) & g["date"].dt.day.between(22, 28) & g["result"].notna()]
    tg_keys = set(zip(tg["game_id"], tg["home_team"].replace(FIX))) | set(zip(tg["game_id"], tg["away_team"].replace(FIX)))
    w["tg"] = [k in tg_keys for k in zip(w["game_id"], w["team"])]
    cur = w[(w["season"] == current)]
    last_game = cur.sort_values("week").groupby("player_id").tail(1)
    inj = pd.read_csv(os.path.join(DATA, "injuries.csv"))
    week = int(today["week"].iloc[0])
    out_ids = set(inj[(inj["season"] == current) & (inj["week"] == week) &
                      inj["report_status"].isin(["Out", "Doubtful"])]["gsis_id"])
    quest = set(inj[(inj["season"] == current) & (inj["week"] == week) & (inj["report_status"] == "Questionable")]["gsis_id"])
    try:
        dk = dk_market(day)
    except Exception as e:
        print("DraftKings market list unavailable:", e)
        dk = set()
    act = last_game[last_game["team"].isin(teams) & (last_game["week"] >= week - 4) & last_game["position"].isin(SKILL)
                    & ~last_game["player_id"].isin(out_ids)]
    if dk:
        act = act[act["player_display_name"].map(norm).isin(dk)]
    print(f"{len(act)} skill players expected to play today ({len(dk)} with a DraftKings anytime-TD market)")
    hist = []
    for r in act.itertuples():
        x = w[(w["player_id"] == r.player_id) & w["tg"]].sort_values("season")
        if x.empty:
            continue
        hist.append({"player": r.player_display_name, "team": r.team, "pos": r.position, "tg_games": len(x),
                     "tg_td_games": int((x["tds"] > 0).sum()), "tg_tds": int(x["tds"].sum()),
                     "pass_tds": int(x["passing_tds"].fillna(0).sum()) if r.position == "QB" else None,
                     "log": [f"{int(y.season)} {y.team} vs {y.opponent_team}: {int(y.tds)} TD" for y in x.itertuples()]})
    hist = sorted(hist, key=lambda h: (-h["tg_td_games"] / h["tg_games"], -h["tg_games"], -h["tg_tds"]))

    # ---- anytime-TD model
    rz = red_zone(range(2022, current + 1), current)
    imp = implied_points(g)
    X = features(w[w["season"] >= 2021], rz, imp)
    X = X[(X["season"] >= 2022) & (X["n"] >= 3) & X["implied"].notna()]
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import log_loss
    # fit on past seasons, then calibrate on this season's games (out of sample): the raw logistic overshoots at
    # the top (a back with a huge red-zone share is not an 85% scorer)
    tr, te = X[X["season"] < current], X[X["season"] == current]
    m = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000)).fit(tr[FEATS], tr["y"])
    raw = m.predict_proba(te[FEATS])[:, 1]
    lg = lambda q: np.log(np.clip(q, 1e-4, 1 - 1e-4) / (1 - np.clip(q, 1e-4, 1 - 1e-4))).reshape(-1, 1)  # noqa: E731
    platt = LogisticRegression(C=1e6, max_iter=1000).fit(lg(raw), te["y"])   # smooth recalibration, no ties
    base = te["position"].map(tr.groupby("position")["y"].mean())
    cal = pd.DataFrame({"p": raw, "y": te["y"].values})
    cal["bin"] = pd.qcut(cal["p"], 8, duplicates="drop")
    calib = [{"said": round(100 * b["p"].mean(), 1), "happened": round(100 * b["y"].mean(), 1), "n": len(b)}
             for _, b in cal.groupby("bin", observed=True)]
    test = {"season": current, "games": int(len(te)), "logloss": round(log_loss(te["y"], raw), 4),
            "base_logloss": round(log_loss(te["y"], base), 4), "calibration": calib}
    test["recal"] = {"slope": round(float(platt.coef_[0][0]), 3), "intercept": round(float(platt.intercept_[0]), 3)}
    # how the top end held up: player-games the model made 65%+ (this season, out of sample, plus last season
    # from a model fit before it)
    m24 = make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=2000)).fit(X[X["season"] < current - 1][FEATS],
                                                                                    X[X["season"] < current - 1]["y"])
    prev = X[X["season"] == current - 1]
    hi = pd.concat([pd.DataFrame({"p": raw, "y": te["y"].values}),
                    pd.DataFrame({"p": m24.predict_proba(prev[FEATS])[:, 1], "y": prev["y"].values})])
    hi = hi[hi["p"] >= 0.65]
    test["top"] = {"n": int(len(hi)), "said": round(100 * hi["p"].mean(), 1) if len(hi) else None,
                   "happened": round(100 * hi["y"].mean(), 1) if len(hi) else None}
    print(f"{current} out-of-sample (model fit on 2022-{current - 1}):", test)

    # today's features: the whole season so far, plus today's implied points
    card = json.load(open(os.path.join(DATA, "card.json")))
    lines = {}
    for b in card["week"]["board"]:
        if b.get("gameday") != day:
            continue
        away, home = b["game"].split(" @ ")
        fav, num = b["market_spread"].split()[0], float(b["market_spread"].split()[1])
        home_margin = -num if fav == home else num
        lines[home] = (float(b["market_total"]) + home_margin) / 2
        lines[away] = (float(b["market_total"]) - home_margin) / 2
    F = features(w[w["season"] >= current - 1], rz, imp)
    F = F[F["season"] == current]
    rows = []
    for r in act.itertuples():
        x = F[F["player_id"] == r.player_id].sort_values("week")
        if len(x) < 3:
            continue
        n = len(x)
        last_row = x.iloc[-1]
        feat = {"rz10_pg": x["rz10"].sum() / n, "rz20_pg": x["rz20"].sum() / n,
                "rz10_share": x["rz10"].sum() / max(x["team_rz10"].sum(), 1), "car_pg": x["carries"].sum() / n,
                "tgt_pg": x["targets"].sum() / n, "td_pg": (x["tds"] > 0).sum() / n, "td_last": last_row["td_last"],
                "implied": lines.get(r.team, np.nan), "is_rb": int(r.position == "RB"), "is_te": int(r.position == "TE"),
                "is_qb": int(r.position == "QB")}
        if pd.isna(feat["implied"]):
            continue
        p = float(platt.predict_proba(lg(m.predict_proba(pd.DataFrame([feat])[FEATS])[:, 1]))[:, 1][0])
        th = next((h for h in hist if h["player"] == r.player_display_name), None)
        rows.append({"player": r.player_display_name, "team": r.team, "pos": r.position, "prob": round(100 * p, 1),
                     "fair": fair(p), "games": n, "tds": int(x["tds"].sum()), "td_games": int((x["tds"] > 0).sum()),
                     "last3": int((x["tds"].tail(3) > 0).sum()),
                     "rz10": int(x["rz10"].sum()), "rz20": int(x["rz20"].sum()),
                     "rz10_share": round(100 * feat["rz10_share"]), "implied": round(feat["implied"], 1),
                     "questionable": r.player_id in quest,
                     "tg": f"{th['tg_td_games']}/{th['tg_games']}" if th else "—"})
    rows = sorted(rows, key=lambda r: -r["prob"])
    print("\nAnytime TD, today (model):")
    for r in rows[:20]:
        print(f"  {r['player']:24s} {r['team']:3s} {r['pos']:2s} {r['prob']:5.1f}%  fair {r['fair']:+5d}  "
              f"scored in {r['td_games']}/{r['games']} ({r['tds']} TD) · inside-10 touches {r['rz10']} ({r['rz10_share']}% of team) · "
              f"Thanksgiving {r['tg']}{'  (questionable)' if r['questionable'] else ''}")
    print("\nThanksgiving TD history (today's players):")
    for h in hist[:20]:
        print(f"  {h['player']:24s} {h['team']:3s} {h['pos']:2s} TD in {h['tg_td_games']}/{h['tg_games']} Thanksgivings "
              f"({h['tg_tds']} TDs) · {' | '.join(h['log'])}")
    with open(os.path.join(DATA, "td_scorers.json"), "w") as f:
        json.dump({"day": day, "test": test, "model": rows, "history": hist, "dk_listed": len(dk)}, f, indent=1, default=str)


if __name__ == "__main__":
    main()
