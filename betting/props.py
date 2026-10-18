#!/usr/bin/env python3
"""NFL player props: projections from weekly player stats, priced against FanDuel/DraftKings prop lines.

Markets: passing yards, rushing yards, receiving yards, receptions.

Projection (pre-game information only): a gradient-boosted model per market on the player's averages (this
season, last 3 games, last season), usage (attempts, carries, targets, target share), what the opponent has
allowed at that stat this season vs the league, the team's implied points (spread and total), home, dome and
wind. Walk-forward: each season is predicted by a model trained only on earlier seasons.

Probabilities: how far actual results land from the projection (out-of-sample ratios, by market and projection
size) gives P(over the line). Checked for calibration on 2022-2026.

There is no free history of prop LINES, so props can't be backtested for ROI like sides and totals. The card
treats them as model-only plays: a big edge, a player with a steady role, no injury or QB questions, 0.5u max.

Writes betting/data/props.json (this week's scored props) and data/props_eval.json (test results).
Usage: python3 betting/props.py              fetch prop lines (Odds API, ~4 requests per game) and score them
       python3 betting/props.py --no-odds    reuse the last fetched lines
"""
import json
import os
import re
import sys
import unicodedata

import numpy as np
import pandas as pd
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
CACHE = os.path.join(DATA, "pbp")
STATS_URL = "https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_{}.parquet"
FIRST = 2018
TEST_FROM = 2022
ODDS_MARKETS = {"player_pass_yds": "pass_yds", "player_rush_yds": "rush_yds",
                "player_reception_yds": "rec_yds", "player_receptions": "receptions"}
STAT = {"pass_yds": "passing_yards", "rush_yds": "rushing_yards", "rec_yds": "receiving_yards", "receptions": "receptions"}
LABEL = {"pass_yds": "Passing Yards", "rush_yds": "Rushing Yards", "rec_yds": "Receiving Yards", "receptions": "Receptions"}
# who counts as having a real role going in (season-to-date or last season per-game averages)
ROLE = {"pass_yds": ("attempts", 20), "rush_yds": ("carries", 8), "rec_yds": ("targets", 3.5), "receptions": ("targets", 3.5)}
PREFERRED_BOOK = "FanDuel"
W_MODEL = 0.4         # the book's line gets the other 60%: prop markets know about role changes we can't see
MIN_EDGE = 0.03       # expected value at the posted price, after calibration and the market blend
MIN_PROB = 0.55       # blended win chance: no coin flips that only look good because of a plus-money price
MIN_HIT = 0.6         # the player's own games this season have to agree (share of games on our side of the line)
MAX_LINE_GAP = 0.3    # skip lines more than 30% off the player's season average (role change, injury we can't see)
MAX_PROPS = 5
PROP_UNITS = 0.5


def stats(seasons):
    os.makedirs(CACHE, exist_ok=True)
    current = max(seasons)
    parts = []
    for y in seasons:
        path = os.path.join(CACHE, f"stats_week_{y}.parquet")
        if not os.path.exists(path) or y == current:
            r = requests.get(STATS_URL.format(y), timeout=120)
            if r.status_code != 200:
                continue
            with open(path, "wb") as f:
                f.write(r.content)
        parts.append(pd.read_parquet(path))
    d = pd.concat(parts, ignore_index=True)
    return d[d["season_type"].isin(["REG", "POST"])].copy()


def norm(name):
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z ]", "", s.replace("-", " "))
    return " ".join(w for w in s.split() if w not in ("jr", "sr", "ii", "iii", "iv", "v"))


# ------------------------------------------------------------------ features
def build(d, g):
    """One row per player-game with pre-game features for every market (NaN where the player has no history)."""
    g = g.copy()
    g["home_pts"] = g["total_line"] / 2 + g["spread_line"] / 2
    g["away_pts"] = g["total_line"] / 2 - g["spread_line"] / 2
    g["dome"] = g["roof"].isin(["dome", "closed"]).astype(int)
    gi = g.set_index("game_id")
    d = d[d["game_id"].isin(gi.index)].copy()
    d["home"] = (gi.loc[d["game_id"], "home_team"].values == d["team"].values).astype(int)
    d["team_pts"] = np.where(d["home"] == 1, gi.loc[d["game_id"], "home_pts"].values, gi.loc[d["game_id"], "away_pts"].values)
    d["opp_pts"] = gi.loc[d["game_id"], "total_line"].values - d["team_pts"]
    d["dome"] = gi.loc[d["game_id"], "dome"].values
    d["wind"] = np.where(d["dome"] == 1, 0, gi.loc[d["game_id"], "wind"].fillna(8).values)
    d["gameday"] = gi.loc[d["game_id"], "gameday"].values
    d = d.sort_values(["gameday", "game_id"]).reset_index(drop=True)
    d["pos"] = d["position"].map({"QB": 0, "RB": 1, "FB": 1, "WR": 2, "TE": 3}).fillna(4)
    cols = ["passing_yards", "rushing_yards", "receiving_yards", "receptions", "attempts", "carries", "targets", "target_share"]
    for c in cols:
        d[c] = d[c].fillna(0)
    grp = d.groupby(["player_id", "season"])
    for c in cols:
        d[f"{c}_avg"] = grp[c].transform(lambda s: s.shift().expanding().mean())
        d[f"{c}_l3"] = grp[c].transform(lambda s: s.shift().rolling(3, min_periods=1).mean())
    d["games"] = grp.cumcount()
    last = d.groupby(["player_id", "season"])[cols].mean().reset_index()
    last["season"] += 1
    d = d.merge(last.rename(columns={c: f"{c}_last" for c in cols}), on=["player_id", "season"], how="left")
    # what each defense has allowed so far this season, per game, to the stat (vs the league average to date)
    allowed = d.groupby(["season", "week", "opponent_team"])[["passing_yards", "rushing_yards", "receiving_yards", "receptions"]].sum().reset_index()
    allowed = allowed.sort_values(["season", "week"])
    for c in ["passing_yards", "rushing_yards", "receiving_yards", "receptions"]:
        allowed[f"{c}_allow"] = allowed.groupby(["season", "opponent_team"])[c].transform(lambda s: s.shift().expanding().mean())
        lg = allowed.groupby(["season", "week"])[c].mean().groupby(level=0).transform(lambda s: s.shift().expanding().mean())
        allowed = allowed.merge(lg.rename(f"{c}_lg").reset_index(), on=["season", "week"], how="left")
        allowed[f"{c}_opp"] = allowed[f"{c}_allow"] / allowed[f"{c}_lg"]
    keep = ["season", "week", "opponent_team"] + [f"{c}_opp" for c in ["passing_yards", "rushing_yards", "receiving_yards", "receptions"]]
    return d.merge(allowed[keep], on=["season", "week", "opponent_team"], how="left")


def feats(m):
    s = STAT[m]
    base = [f"{s}_avg", f"{s}_l3", f"{s}_last", "games", "team_pts", "opp_pts", "home", "dome", "wind", "pos",
            f"{'passing_yards' if m == 'pass_yds' else 'rushing_yards' if m == 'rush_yds' else 'receiving_yards' if m == 'rec_yds' else 'receptions'}_opp"]
    use = {"pass_yds": ["attempts_avg", "attempts_l3", "attempts_last"],
           "rush_yds": ["carries_avg", "carries_l3", "carries_last"],
           "rec_yds": ["targets_avg", "targets_l3", "targets_last", "target_share_avg", "target_share_l3"],
           "receptions": ["targets_avg", "targets_l3", "targets_last", "target_share_avg", "target_share_l3"]}[m]
    return base + use


def has_role(df, m):
    c, lo = ROLE[m]
    return (df[f"{c}_avg"].fillna(0) >= lo) | ((df["games"] < 2) & (df[f"{c}_last"].fillna(0) >= lo))


def fit(train, m):
    from sklearn.ensemble import HistGradientBoostingRegressor
    t = train[has_role(train, m)]
    return HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_leaf_nodes=24, min_samples_leaf=60,
                                         l2_regularization=1.0, random_state=0).fit(t[feats(m)], t[STAT[m]])


# ------------------------------------------------------------------ test on past seasons
def evaluate(d):
    """Walk-forward predictions for 2022+; returns out-of-sample predictions and a summary."""
    out, summary = [], {}
    for m in STAT:
        preds = []
        for S in sorted(d["season"].unique()):
            if S < TEST_FROM:
                continue
            tr = d[(d["season"] < S) & (d["season"] >= 2019)]
            te = d[(d["season"] == S) & has_role(d, m)].copy()
            if te.empty:
                continue
            te["pred"] = np.clip(fit(tr, m).predict(te[feats(m)]), 0.5, None)
            te["market"] = m
            te["actual"] = te[STAT[m]]
            te["naive"] = te[f"{STAT[m]}_avg"].fillna(te[f"{STAT[m]}_last"])
            preds.append(te[["season", "week", "player_id", "player_display_name", "market", "pred", "actual", "naive"]])
        p = pd.concat(preds)
        ok = p["naive"].notna()
        summary[m] = {"games": int(len(p)), "mae_model": round(float((p.pred - p.actual).abs().mean()), 2),
                      "mae_season_avg": round(float((p[ok].naive - p[ok].actual).abs().mean()), 2),
                      "under_own_avg%": round(100 * float((p[ok].actual < p[ok].naive).mean()), 1)}
        out.append(p)
    return pd.concat(out, ignore_index=True), summary


def ratio_table(ev):
    """actual/projection ratios by market and projection tercile (for P(over))."""
    tab = {}
    for m, x in ev.groupby("market"):
        cuts = np.quantile(x["pred"], [1 / 3, 2 / 3])
        tab[m] = {"cuts": cuts.tolist(), "ratios": [(x[(x.pred > lo) & (x.pred <= hi)].actual / x[(x.pred > lo) & (x.pred <= hi)].pred).values
                                                  for lo, hi in ((-1, cuts[0]), (cuts[0], cuts[1]), (cuts[1], 1e9))]}
    return tab


def p_over(tab, m, pred, line):
    t = tab[m]
    k = 0 if pred <= t["cuts"][0] else 1 if pred <= t["cuts"][1] else 2
    return float((t["ratios"][k] * pred > line).mean())


def calibrators(ev, tab):
    """Out-of-sample P(over) -> how often it actually went over, per market (isotonic). The raw model is too sure
    of itself at the extremes; this pulls its probabilities back to what happened."""
    from sklearn.isotonic import IsotonicRegression
    cal = {}
    for m, x in ev[ev["naive"].notna()].groupby("market"):
        ps, hits = [], []
        for line in (np.floor(x["naive"]) + 0.5, np.floor(x["pred"]) + 0.5):
            ps.append([p_over(tab, m, a, b) for a, b in zip(x["pred"], line)])
            hits.append(x["actual"].values > line.values)
        cal[m] = IsotonicRegression(y_min=0.02, y_max=0.98, out_of_bounds="clip").fit(np.concatenate(ps), np.concatenate(hits))
    return cal


def calibration(ev, tab):
    """Does P(over) mean what it says? Bucket out-of-sample probabilities at proxy lines (the player's own average)."""
    rows = []
    for m, x in ev[ev["naive"].notna()].groupby("market"):
        line = np.floor(x["naive"]) + 0.5
        p = np.array([p_over(tab, m, a, b) for a, b in zip(x["pred"], line)])
        hit = (x["actual"].values > line.values)
        for lo, hi in ((0, .4), (.4, .45), (.45, .5), (.5, .55), (.55, .6), (.6, 1.01)):
            s = (p >= lo) & (p < hi)
            if s.sum() >= 30:
                rows.append({"market": m, "bucket": f"{lo:.2f}-{min(hi, 1):.2f}", "n": int(s.sum()),
                             "said%": round(100 * float(p[s].mean()), 1), "happened%": round(100 * float(hit[s].mean()), 1)})
    return rows


# ------------------------------------------------------------------ this week's lines
def odds_key():
    k = os.environ.get("ODDS_API_KEY")
    path = os.path.join(HERE, "odds_api_key.txt")
    if not k and os.path.exists(path):
        k = open(path).read().strip()
    return k


def fetch_lines(games):
    """Prop lines for this week's games from FanDuel and DraftKings (The Odds API event endpoint)."""
    key = odds_key()
    if not key:
        print("no Odds API key: props need FanDuel/DraftKings prop lines")
        return pd.DataFrame()
    base = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl"
    ev = requests.get(f"{base}/events", params={"apiKey": key}, timeout=30).json()
    want = {(r.away_name, r.home_name) for r in games.itertuples()}
    rows, left = [], None
    for e in ev:
        if (e["away_team"], e["home_team"]) not in want:
            continue
        r = requests.get(f"{base}/events/{e['id']}/odds", params={
            "apiKey": key, "regions": "us", "bookmakers": "fanduel,draftkings", "oddsFormat": "american",
            "markets": ",".join(ODDS_MARKETS)}, timeout=30)
        left = r.headers.get("x-requests-remaining", left)
        if r.status_code != 200:
            print("prop odds failed:", e["away_team"], "@", e["home_team"], r.status_code)
            continue
        for b in r.json().get("bookmakers", []):
            for mk in b.get("markets", []):
                for o in mk.get("outcomes", []):
                    rows.append({"away": e["away_team"], "home": e["home_team"], "book": b["title"],
                                 "market": ODDS_MARKETS.get(mk["key"]), "player": o.get("description"),
                                 "side": o["name"].lower(), "line": o.get("point"), "odds": o.get("price")})
    print(f"prop lines: {len(rows)} prices ({left} Odds API requests left this month)")
    return pd.DataFrame(rows)


def payout(o):
    return o / 100 if o > 0 else 100 / -o


def no_vig(p_over_odds, p_under_odds):
    a, b = 1 / (1 + payout(p_over_odds)), 1 / (1 + payout(p_under_odds))
    return a / (a + b)


# ------------------------------------------------------------------ main
NAMES = {"ARI": "Arizona Cardinals", "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens", "BUF": "Buffalo Bills",
         "CAR": "Carolina Panthers", "CHI": "Chicago Bears", "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns",
         "DAL": "Dallas Cowboys", "DEN": "Denver Broncos", "DET": "Detroit Lions", "GB": "Green Bay Packers",
         "HOU": "Houston Texans", "IND": "Indianapolis Colts", "JAX": "Jacksonville Jaguars", "KC": "Kansas City Chiefs",
         "LA": "Los Angeles Rams", "LAC": "Los Angeles Chargers", "LV": "Las Vegas Raiders", "MIA": "Miami Dolphins",
         "MIN": "Minnesota Vikings", "NE": "New England Patriots", "NO": "New Orleans Saints", "NYG": "New York Giants",
         "NYJ": "New York Jets", "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers", "SEA": "Seattle Seahawks",
         "SF": "San Francisco 49ers", "TB": "Tampa Bay Buccaneers", "TEN": "Tennessee Titans", "WAS": "Washington Commanders"}


def main():
    g = pd.read_csv(os.path.join(DATA, "games.csv"), low_memory=False)
    g = g[g["season"] >= FIRST]
    w = os.path.join(DATA, "weather.csv")
    if os.path.exists(w):  # kickoff forecast for this week's outdoor games
        fw = pd.read_csv(w).set_index("game_id")["wind"]
        g.loc[g["game_id"].isin(fw.index), "wind"] = g.loc[g["game_id"].isin(fw.index), "game_id"].map(fw)
    current = int(g["season"].max())
    today = pd.Timestamp.now(tz="America/New_York").strftime("%Y-%m-%d")
    up = g[g["result"].isna() & (g["gameday"] >= today)]
    up = up[up["week"] == up["week"].min()].copy()
    d = stats(range(FIRST, current + 1))

    # this week's rows: each player's latest team, facing this week's opponent
    latest = d[d["season"] == current].sort_values("week").groupby("player_id").tail(1)
    rows = []
    for r in up.itertuples():
        for team, opp in ((r.home_team, r.away_team), (r.away_team, r.home_team)):
            x = latest[latest["team"] == team].copy()
            x["week"], x["game_id"], x["opponent_team"] = r.week, r.game_id, opp
            for c in ["passing_yards", "rushing_yards", "receiving_yards", "receptions", "attempts", "carries", "targets", "target_share"]:
                x[c] = np.nan
            rows.append(x)
    fut = pd.concat(rows, ignore_index=True)
    fut["season_type"], fut["_fut"], d["_fut"] = "REG", 1, 0
    full = build(pd.concat([d, fut], ignore_index=True), g)
    is_fut = full["_fut"] == 1
    hist, now = full[~is_fut & full["season"].ge(2019)], full[is_fut].copy()

    ev, summary = evaluate(hist)
    tab = ratio_table(ev)
    iso = calibrators(ev, tab)
    cal = calibration(ev, tab)
    with open(os.path.join(DATA, "props_eval.json"), "w") as f:
        json.dump({"summary": summary, "calibration": cal}, f, indent=1)
    print("Walk-forward test (2022-2026, out of sample):")
    for m, s in summary.items():
        print(f"  {LABEL[m]:16s} {s['games']:6d} player-games  avg miss {s['mae_model']:6.2f} "
              f"(season average alone: {s['mae_season_avg']:.2f}); went under their own average {s['under_own_avg%']}% of the time")
    print("Calibration (said vs happened):", ", ".join(f"{c['market']} {c['said%']}/{c['happened%']}" for c in cal[:8]), "...")

    # project this week
    proj = []
    for m in STAT:
        model = fit(hist, m)
        x = now[has_role(now, m)].copy()
        x["pred"] = np.clip(model.predict(x[feats(m)]), 0.5, None)
        x["market"] = m
        proj.append(x)
    proj = pd.concat(proj, ignore_index=True)

    path = os.path.join(DATA, "props_lines.csv")
    if "--no-odds" in sys.argv and os.path.exists(path):
        lines = pd.read_csv(path)
    else:
        up["away_name"], up["home_name"] = up["away_team"].map(NAMES), up["home_team"].map(NAMES)
        lines = fetch_lines(up)
        if not lines.empty:
            lines.to_csv(path, index=False)
    if lines.empty:
        return
    inv = {v: k for k, v in NAMES.items()}
    lines["away_t"], lines["home_t"] = lines["away"].map(inv), lines["home"].map(inv)
    lines["key"] = lines["player"].map(norm)
    proj["key"] = proj["player_display_name"].map(norm)

    # injury report: skip anyone not fully cleared; QB uncertainty on the team: skip its passing game
    inj = pd.read_csv(os.path.join(DATA, "injuries.csv"), low_memory=False)
    wk = int(up["week"].min())
    inj = inj[(inj["season"] == current) & (inj["week"] == wk)]
    hurt = {norm(n): s for n, s in zip(inj["full_name"], inj["report_status"])}
    try:
        sys.path.insert(0, os.path.join(HERE, "share"))
        import weekly as W
        qb_flag = {x["team"]: f"{x['qb']} {x['status'].lower()}" for x in W.nfl_qb_watch(W.Sport("nfl"))}
    except Exception as e:  # network trouble shouldn't stop the props
        print("QB watch unavailable:", e)
        qb_flag = {}

    # our game totals this week: a passing/receiving prop shouldn't bet against one of them
    totals = {}
    fpath = os.path.join(DATA, "final_nfl.json")
    if os.path.exists(fpath):
        for pl in json.load(open(fpath)).get("plays", []):
            if pl["market"] == "total":
                totals[pl["game_id"]] = pl["side"]

    out = []
    for (key, m, team), x in proj.groupby(["key", "market", "team"]):
        r = x.iloc[0]
        l = lines[(lines["key"] == key) & (lines["market"] == m) & ((lines["away_t"] == team) | (lines["home_t"] == team))]
        if l.empty:
            continue
        hist_p = hist[(hist["player_id"] == r.player_id) & (hist["season"] == current)]
        for line, ll in l.groupby("line"):
            for side in ("over", "under"):
                offers = ll[ll["side"] == side]
                other = ll[ll["side"] != side]
                if offers.empty or other.empty:
                    continue
                po = float(iso[m].predict([p_over(tab, m, r.pred, line)])[0])
                p_model = po if side == "over" else 1 - po
                best = max(offers.itertuples(), key=lambda o: (payout(o.odds), o.book == PREFERRED_BOOK))
                opp = other[other["book"] == best.book]
                if opp.empty:
                    continue
                p_book = no_vig(best.odds, opp["odds"].iloc[0])  # no-vig chance of THIS side at that book
                p = W_MODEL * p_model + (1 - W_MODEL) * p_book
                evv = p * payout(best.odds) - (1 - p)
                games = hist_p[STAT[m]].values
                hits = int((games > line).sum() if side == "over" else (games < line).sum())
                avg = float(np.mean(games)) if len(games) else np.nan
                last3 = float(np.mean(games[-3:])) if len(games) else np.nan
                skip = None
                status = hurt.get(key)
                if status in ("Out", "Doubtful", "Questionable"):
                    skip = f"injury report: {status.lower()}"
                elif team in qb_flag:  # a backup QB changes the whole offense's game script, run game included
                    skip = f"QB Watch: {qb_flag[team]}"
                elif r.game_id in totals and m != "rush_yds" and totals[r.game_id] != side:
                    skip = f"would bet against our {totals[r.game_id]} in this game"
                elif len(games) < 4:
                    skip = "fewer than 4 games this season"
                elif abs(line - avg) > MAX_LINE_GAP * max(avg, 3 if m == "receptions" else 20):
                    skip = f"line {line:g} is far from his {avg:.1f} average: the book likely knows about a role change"
                elif hits < MIN_HIT * len(games):
                    skip = f"his own games don't back it ({hits}/{len(games)} on this side)"
                elif last3 < 0.5 * avg or last3 > 2 * avg:
                    skip = f"his last 3 games ({last3:.1f}) are far off his {avg:.1f} average: usage changed, likely injury"
                elif (side == "under" and last3 > line * 1.1) or (side == "over" and last3 < line * 0.9):
                    skip = f"his last 3 games ({last3:.1f}) run the other way"
                out.append({"player": r.player_display_name, "team": team, "opp": r.opponent_team, "pos": r.position,
                            "game_id": r.game_id, "market": m, "label": LABEL[m], "side": side, "line": float(line),
                            "book": best.book, "odds": int(best.odds), "proj": round(float(r.pred), 1),
                            "prob": round(100 * p, 1), "model_prob": round(100 * p_model, 1), "book_prob": round(100 * p_book, 1),
                            "ev": round(100 * evv, 1), "season_avg": round(float(np.mean(games)), 1) if len(games) else None,
                            "last3": round(float(np.mean(games[-3:])), 1) if len(games) else None,
                            "games": [int(v) for v in games], "hits": hits, "n": int(len(games)),
                            "opp_factor": round(float(r[f"{'passing_yards' if m == 'pass_yds' else 'rushing_yards' if m == 'rush_yds' else 'receiving_yards' if m == 'rec_yds' else 'receptions'}_opp"]), 2)
                            if pd.notna(r[f"{'passing_yards' if m == 'pass_yds' else 'rushing_yards' if m == 'rush_yds' else 'receiving_yards' if m == 'rec_yds' else 'receptions'}_opp"]) else None,
                            "team_pts": round(float(r.team_pts), 1) if pd.notna(r.team_pts) else None,
                            "wind": float(r.wind), "dome": int(r.dome), "skip": skip})
    sc = pd.DataFrame(out)
    if sc.empty:
        print("no props matched")
        return
    sc = sc.sort_values("ev", ascending=False)
    picks, seen_player, seen_game = [], set(), {}
    for p in sc[sc["skip"].isna() & (sc["ev"] >= 100 * MIN_EDGE) & (sc["prob"] >= 100 * MIN_PROB)].to_dict("records"):
        if p["player"] in seen_player or seen_game.get(p["game_id"], 0) >= 2:
            continue
        p["units"] = PROP_UNITS
        picks.append(p)
        seen_player.add(p["player"])
        seen_game[p["game_id"]] = seen_game.get(p["game_id"], 0) + 1
        if len(picks) >= MAX_PROPS:
            break
    with open(os.path.join(DATA, "props.json"), "w") as f:
        json.dump({"week": wk, "season": current, "picks": picks,
                   "near": sc[sc["skip"].isna() & (sc["ev"] > 0)].head(15).to_dict("records"),
                   "skipped": sc[sc["skip"].notna() & (sc["ev"] >= 100 * MIN_EDGE)].head(10).to_dict("records"),
                   "summary": summary}, f, indent=1, default=str)
    print(f"\n{len(sc)} prop prices scored, {len(picks)} plays:")
    for p in picks:
        print(f"  {p['player']:22s} {p['side'].title()} {p['line']:g} {p['label']:16s} {p['odds']:+d} {p['book']:10s} "
              f"proj {p['proj']:6.1f}  win {p['prob']}% (model {p['model_prob']}%, book {p['book_prob']}%)  ev {p['ev']:+.1f}%  "
              f"season {p['season_avg']} last3 {p['last3']}  {p['side']} in {p['hits']}/{p['n']}")


if __name__ == "__main__":
    main()
