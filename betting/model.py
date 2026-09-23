#!/usr/bin/env python3
"""NFL spread / total / moneyline model: walk-forward backtest + this week's card.

How a prediction is made
  1. features.py rates every team (Elo, opponent-adjusted EPA, success rate, QB EPA, pace...)
     using only games before kickoff.
  2. Two base models per market, trained only on earlier seasons:
       ridge regression (linear, stable) + gradient-boosted trees (catch non-linear effects),
     averaged. Margin model predicts home margin; total model predicts combined points.
  3. Market blend: fair = w * model + (1 - w) * closing line. w is fit each season on the
     model's out-of-sample errors from earlier seasons, so it tells you honestly how much the
     model adds on top of the market.
  4. Line -> probability with the real NFL score distribution: games whose market line was near
     our fair number are kernel-weighted to get P(margin = k) for every k, so key numbers
     (3, 7, 10, 6, 14 for sides; 41, 44, 37, 51 for totals) and pushes are priced correctly.
     Probabilities are anchored to the market: start from the no-vig price (power method) and
     move it only by the gap between our fair line and the market line at those key numbers.
  5. Bet only when expected value at the actual odds clears a threshold; stake with 1/4 Kelly.

Usage: python3 betting/model.py            backtest + current week
       python3 betting/model.py --week     current week only (faster)
"""
import json
import math
import os
import sys
import warnings

os.environ.setdefault("OMP_NUM_THREADS", "1")  # small data: threads only add overhead

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import features as F  # noqa: E402

warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
FIRST_TRAIN = 2010   # 2009 only warms up the ratings
MODEL_CFG = {"alpha": 100.0, "depth": 3, "trees": 250, "leaf": 120, "ridge_w": 0.5, "resid": True}
FIRST_BASE_TEST = 2012
TUNE_FROM = 2014
BLEND_HALF_LIFE = 1.5
FIRST_REPORT = 2019  # 2014-2018 were used to choose features/settings; 2019+ is untouched
MIN_EV = {"spread": 0.03, "total": 0.03, "ml": 0.03}
LEAN_EV = 0.01
KELLY_FRACTION = 0.25
MAX_STAKE = 0.03
MARKETS = {"spread": ("result", "spread_line", F.SPREAD_FEATURES, 0.75, np.arange(-30, 30.5, 0.5)),
           "total": ("total", "total_line", F.TOTAL_FEATURES, 1.0, np.arange(28, 70.5, 0.5))}
SCORES = np.arange(-80, 121)


# ---------- base models ----------
def fit_base(train, target, cols, line=None, cfg=None):
    """Ridge + boosted trees, averaged. With `line`, both learn the gap between result and market line
    (what a bet actually depends on) and the prediction is line + gap; games without a line fall back
    to a direct model."""
    cfg = dict(MODEL_CFG, **(cfg or {}))
    def pair(X, y):
        ridge = make_pipeline(StandardScaler(), Ridge(alpha=cfg["alpha"])).fit(X, y)
        gbm = HistGradientBoostingRegressor(max_depth=cfg["depth"], learning_rate=0.03, max_iter=cfg["trees"],
                                            min_samples_leaf=cfg["leaf"], l2_regularization=5.0, random_state=0).fit(X, y)
        wr = cfg["ridge_w"]
        return lambda X2: wr * ridge.predict(X2) + (1 - wr) * gbm.predict(X2)
    direct = pair(train[cols].values, train[target].values)
    if not line or not cfg["resid"]:
        return lambda d: direct(d[cols].values)
    t = train.dropna(subset=[line])
    xc = cols + [line]
    gap = pair(t[xc].values, (t[target] - t[line]).values)

    def predict(d):
        out = direct(d[cols].values)
        has = d[line].notna().values
        if has.any():
            out[has] = d[line].values[has] + gap(d.loc[has, xc].values)
        return out
    return predict


def blend_weight(hist, target, line):
    """Least-squares w in [0, 1] for  target - line = w * (model - line), recent seasons weighted most
    (half-life 1.5 seasons). Markets get sharper over time (legal betting since 2018 made closing lines
    much harder to beat), so an edge the model had years ago must not decide how much we trust it now."""
    h = hist.dropna(subset=[target, line, "base"])
    if not len(h):
        return 0.0
    age = h["season"].max() - h["season"]
    sw = 0.5 ** (age / BLEND_HALF_LIFE)
    x, y = (h["base"] - h[line]).values, (h[target] - h[line]).values
    return float(np.clip((sw * x) @ y / max((sw * x) @ x, 1e-9), 0, 1))


# ---------- score distributions ----------
def pmf_table(hist, target, line, bw, grid, symmetric):
    h = hist.dropna(subset=[target, line])
    lines, res = h[line].values, h[target].values.round().astype(int)
    if symmetric:
        lines, res = np.concatenate([lines, -lines]), np.concatenate([res, -res])
    table = {}
    for L in grid:
        # widen the kernel away from the common lines, where there are fewer games to learn from
        b = bw * (1 + 0.06 * abs(L - np.median(lines)))
        w = np.exp(-0.5 * ((lines - L) / b) ** 2)
        # no recentring: closing lines sit near the median, not the mean, of skewed NFL margins,
        # so the raw outcome distribution of games closed near L is the honest one
        idx = np.clip(res - SCORES[0], 0, len(SCORES) - 1)
        p = np.bincount(idx, weights=w, minlength=len(SCORES))
        table[round(L * 2) / 2] = p / p.sum()
    return table


def pmf_at(table, x):
    lo = math.floor(x * 2) / 2
    lo = min(max(lo, min(table)), max(table) - 0.5)
    t = min(max((x - lo) / 0.5, 0), 1)
    return (1 - t) * table[lo] + t * table[lo + 0.5]


def over_under(p, L):
    """P(value > L), P(value == L), P(value < L)."""
    return p[SCORES > L].sum(), p[SCORES == L].sum(), p[SCORES < L].sum()


# ---------- odds helpers ----------
def payout(odds):
    if odds is None or pd.isna(odds):
        odds = -110
    return odds / 100 if odds > 0 else 100 / -odds


def to_american(p):
    p = min(max(p, 1e-4), 1 - 1e-4)
    return round(-100 * p / (1 - p)) if p >= 0.5 else round(100 * (1 - p) / p)


def evaluate(p_win, p_push, p_lose, odds):
    b = payout(odds)
    ev = p_win * b - p_lose
    q = p_win + p_lose
    kelly = max(0.0, (b * p_win / q - p_lose / q) / b) if q > 0 else 0.0
    return ev, min(MAX_STAKE, KELLY_FRACTION * kelly)


def no_vig(odds_a, odds_b):
    """Fair probability of side A with the power method (handles favourite-longshot bias better than
    simply scaling both sides): find k with pA^k + pB^k = 1."""
    ia, ib = (1 / (1 + payout(o)) for o in (odds_a, odds_b))
    lo, hi = 0.5, 3.0
    for _ in range(60):
        k = (lo + hi) / 2
        lo, hi = (k, hi) if ia ** k + ib ** k > 1 else (lo, k)
    return ia ** k


def logit(p):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def price(row, pm, market, side, line):
    """Win/push/lose for one offer (any book's line), anchored to the consensus no-vig price: the market's
    probability at its own line, moved by our fair distribution at the offered line."""
    sp, sp_mkt, tot, tot_mkt = pm
    if market == "spread":
        fair, mkt, L_cons, p_cons = sp, sp_mkt, row.spread_line, no_vig(row.home_spread_odds, row.away_spread_odds)
    elif market == "total":
        fair, mkt, L_cons, p_cons = tot, tot_mkt, row.total_line, no_vig(row.over_odds, row.under_odds)
    else:
        fair, mkt, L_cons, line = sp, sp_mkt, 0, 0
        p_cons = no_vig(row.home_ml, row.away_ml) if pd.notna(row.home_ml) and pd.notna(row.away_ml) else 0.5
    w_f, pu, lo_f = over_under(fair, line)
    w_m, _pm, lo_m = over_under(mkt, L_cons)
    q = 1 / (1 + math.exp(-(logit(p_cons) + logit(w_f / (w_f + lo_f)) - logit(w_m / (w_m + lo_m)))))
    w, lo = q * (1 - pu), (1 - q) * (1 - pu)
    return (w, pu, lo) if side in ("home", "over") else (lo, pu, w)


def label(row, market, side, line):
    team = row.home if side == "home" else row.away
    if market == "spread":
        return f"{team} {(-line if side == 'home' else line):+g}"
    if market == "ml":
        return f"{team} ML"
    return f"{side.title()} {line:g}"


def consensus_offers(row):
    out = []
    if pd.notna(row.spread_line):
        out += [("spread", "home", row.spread_line, row.home_spread_odds), ("spread", "away", row.spread_line, row.away_spread_odds)]
    if pd.notna(row.home_ml) and pd.notna(row.away_ml):
        out += [("ml", "home", 0, row.home_ml), ("ml", "away", 0, row.away_ml)]
    if pd.notna(row.total_line):
        out += [("total", "over", row.total_line, row.over_odds), ("total", "under", row.total_line, row.under_odds)]
    return out


def options(row, sp, sp_mkt, tot, tot_mkt, offers=None):
    """Every bet on the board for a game with our win/push/lose probabilities.
    offers: (market, side, line, odds, book) from your books (FanDuel/DraftKings). When given, only those are
    bettable; the consensus line still anchors the probabilities. Without them, consensus prices stand in."""
    pm = (sp, sp_mkt, tot, tot_mkt)
    allo = list(offers) if offers else [o + ("consensus",) for o in consensus_offers(row)]
    out = []
    for market, side, line, odds, book in allo:
        if (market == "spread" and pd.isna(row.spread_line)) or (market == "total" and pd.isna(row.total_line)):
            continue
        w, pu, lo = price(row, pm, market, side, line)
        out.append((market, book, label(row, market, side, line), w, pu, lo, odds, side, line))
    return out


def game_pmfs(r, tables):
    sp, tt = tables
    mkt_sp = r.spread_line if pd.notna(r.spread_line) else r.fair_spread
    mkt_tot = r.total_line if pd.notna(r.total_line) else r.fair_total
    return pmf_at(sp, r.fair_spread), pmf_at(sp, mkt_sp), pmf_at(tt, r.fair_total), pmf_at(tt, mkt_tot)


def settle(row, market, side, odds):
    if market == "total":
        d = row.total - row.total_line
        d = d if side == "over" else -d
    else:
        d = row.result - (row.spread_line if market == "spread" else 0)
        d = d if side == "home" else -d
    return 0.0 if d == 0 else (payout(odds) if d > 0 else -1.0)


# ---------- walk-forward ----------
def predict_season(df, season, oos):
    """Fair lines + pmfs for every game in `season`, trained only on earlier seasons."""
    train = df[(df.season >= FIRST_TRAIN) & (df.season < season) & df.result.notna()]
    test = df[df.season == season].copy()
    info = {}
    for m, (target, line, cols, bw, grid) in MARKETS.items():
        test[f"base_{m}"] = fit_base(train, target, cols, line)(test)
        hist = oos[m][oos[m].season < season] if len(oos[m]) else oos[m]
        w = blend_weight(hist, target, line) if len(hist) else 0.5
        test[f"w_{m}"] = w
        fair = w * test[f"base_{m}"] + (1 - w) * test[line]
        test[f"fair_{m}"] = fair.fillna(test[f"base_{m}"])
        info[m] = (w, pmf_table(train, target, line, bw, grid, m == "spread"))
    return test, info


def run():
    df = F.build()
    current = int(df.loc[df.result.notna(), "season"].max())
    oos = {m: pd.DataFrame() for m in MARKETS}
    bets, seasons_out = [], []
    for season in range(FIRST_BASE_TEST, current + 1):
        test, info = predict_season(df, season, oos)
        for m, (target, line, *_rest) in MARKETS.items():
            done = test[test[target].notna()][["season", target, line, f"base_{m}"]].rename(columns={f"base_{m}": "base"})
            oos[m] = pd.concat([oos[m], done])
        seasons_out.append(test)
        if season < TUNE_FROM:
            continue
        for r in test[test.result.notna()].itertuples(index=False):
            for market, _b, name, w, pu, lo, odds, side, _l in options(r, *game_pmfs(r, (info["spread"][1], info["total"][1]))):
                ev, stake = evaluate(w, pu, lo, odds)
                bets.append({"season": r.season, "week": r.week, "game_id": r.game_id, "market": market,
                             "bet": name, "p": w, "ev": ev, "stake": stake,
                             "units": settle(r, market, side, odds)})
    all_games = pd.concat(seasons_out)
    return df, all_games, pd.DataFrame(bets), info, current


def summarize(games, bets):
    g = games[(games.season >= FIRST_REPORT) & games.result.notna()]
    rm = lambda a, b: float(np.sqrt(np.mean((a - b) ** 2)))  # noqa: E731
    acc = {
        "spread": {"closing line": rm(g.result, g.spread_line), "model alone": rm(g.result, g.base_spread),
                   "blend": rm(g.result, g.fair_spread)},
        "total": {"closing line": rm(g.total, g.total_line), "model alone": rm(g.total, g.base_total),
                  "blend": rm(g.total, g.fair_total)}}
    weights = games[games.season >= TUNE_FROM].groupby("season")[["w_spread", "w_total"]].first().round(2)
    table = []
    periods = {"holdout": bets.season >= FIRST_REPORT, "tuning": bets.season < FIRST_REPORT}
    for period, mask in periods.items():
        for m in ("spread", "total", "ml"):
            for thr in (0.0, 0.02, 0.03, 0.05):
                b = bets[mask & (bets.market == m) & (bets.ev > thr)]
                # one bet per game per market: the side with the higher EV
                b = b.sort_values("ev").groupby(["game_id"]).tail(1)
                if not len(b):
                    continue
                wins, losses, pushes = (b.units > 0).sum(), (b.units < 0).sum(), (b.units == 0).sum()
                table.append({"period": period, "market": m, "min_ev": thr, "bets": len(b),
                              "record": f"{wins}-{losses}-{pushes}", "win%": round(100 * wins / max(wins + losses, 1), 1),
                              "units": round(b.units.sum(), 1), "roi%": round(100 * b.units.mean(), 1),
                              "kelly_bankroll_x": round(float(np.prod(1 + b.stake * b.units)), 2)})
    return acc, weights, pd.DataFrame(table)


def current_card(df, current):
    """Fair lines and best bets for the next unplayed week, trained on everything so far."""
    upcoming = df[(df.season == current) & df.result.isna()]
    if not len(upcoming):
        return None, None
    week = int(upcoming.week.min())
    df = apply_my_lines(df, current, week)
    # out-of-sample history for the blend weights: re-use the backtest when available
    oos = {m: pd.DataFrame() for m in MARKETS}
    for season in range(FIRST_BASE_TEST, current + 1):
        train = df[(df.season >= FIRST_TRAIN) & (df.season < season) & df.result.notna()]
        test = df[(df.season == season) & df.result.notna()]
        for m, (target, line, cols, *_r) in MARKETS.items():
            t = test[["season", target, line]].copy()
            t["base"] = fit_base(train, target, cols, line)(test)
            oos[m] = pd.concat([oos[m], t])
    train = df[(df.season >= FIRST_TRAIN) & df.result.notna()]
    wk = df[(df.season == current) & (df.week == week)].copy()
    pmfs = {}
    for m, (target, line, cols, bw, grid) in MARKETS.items():
        wk[f"base_{m}"] = fit_base(train, target, cols, line)(wk)
        w = blend_weight(oos[m], target, line)
        wk[f"w_{m}"] = w
        wk[f"fair_{m}"] = (w * wk[f"base_{m}"] + (1 - w) * wk[line]).fillna(wk[f"base_{m}"])
        pmfs[m] = pmf_table(train, target, line, bw, grid, m == "spread")
    books = book_offers()
    rows, picks = [], []
    for r in wk.itertuples(index=False):
        pm = game_pmfs(r, (pmfs["spread"], pmfs["total"]))
        home_win = over_under(pm[0], 0)
        if pd.notna(r.home_ml) and pd.notna(r.away_ml):
            home_win = price(r, pm, "ml", "home", 0)[:2]
        rows.append({"game": f"{r.away} @ {r.home}", "gameday": r.gameday, "qbs": f"{r.away_qb or '?'} / {r.home_qb or '?'}",
                     "market_spread": f"{r.home} {-r.spread_line:+g}" if pd.notna(r.spread_line) else "",
                     "model_spread": f"{r.home} {-r.base_spread:+.1f}", "fair_spread": f"{r.home} {-r.fair_spread:+.1f}",
                     "market_total": r.total_line, "model_total": round(r.base_total, 1), "fair_total": round(r.fair_total, 1),
                     "home_win%": round(100 * (home_win[0] + home_win[1] / 2), 1),
                     "fair_ml": f"{r.home} {to_american(home_win[0] + home_win[1] / 2):+d}"})
        best = {}
        for market, book, name, w, pu, lo, odds, side, line in options(r, *pm, offers=books.get((r.away, r.home))):
            ev, stake = evaluate(w, pu, lo, odds)
            if market in best and ev <= best[market]["ev"]:
                continue
            tier = "BET" if ev > MIN_EV[market] else "lean" if ev > LEAN_EV else "watch"
            best[market] = {"game_id": r.game_id, "side": side, "game": f"{r.away} @ {r.home}", "market": market,
                            "line": None if market == "ml" else line, "book": book, "bet": name,
                            "odds": int(odds) if pd.notna(odds) else -110, "win%": round(100 * w / max(w + lo, 1e-9), 1),
                            "push%": round(100 * pu, 1), "ev": ev, "stake%": round(100 * stake, 2) if tier == "BET" else 0.0,
                            "tier": tier, "target": target_price(r, pm, market, side, line)}
        picks += best.values()
    picks = pd.DataFrame(picks)
    if len(picks):
        order = {"BET": 0, "lean": 1, "watch": 2}
        picks = picks.sort_values(["tier", "ev"], key=lambda c: c.map(order) if c.name == "tier" else -c)
        picks["ev%"] = (100 * picks.pop("ev")).round(1)
    return week, (pd.DataFrame(rows), picks, float(wk.w_spread.iloc[0]), float(wk.w_total.iloc[0]))


def need_odds(w, lo, thr):
    """Worst American odds that still give expected value >= thr for a bet winning w, losing lo."""
    b = (thr + lo) / max(w, 1e-9)
    return round(100 * b) if b >= 1 else -round(100 / b)


def target_price(r, pm, market, side, line):
    """The price to look for on FanDuel/DraftKings: odds needed for a BET at this line, and at half a point better."""
    def fmt(o):
        return f"{o:+d}" if abs(o) < 1000 else "no"
    w, pu, lo = price(r, pm, market, side, line)
    out = f"{fmt(need_odds(w, lo, MIN_EV[market]))} or better"
    if market != "ml":
        better = line - 0.5 if side in ("home", "over") else line + 0.5
        w2, _p, lo2 = price(r, pm, market, side, better)
        out += f"; at {label(r, market, side, better)}: {fmt(need_odds(w2, lo2, MIN_EV[market]))}"
    return out


def book_offers():
    """(away, home) -> [(market, side, line, odds, book)] from betting/data/book_odds.csv (fetch.py, needs an API key)."""
    path = os.path.join(HERE, "data", "book_odds.csv")
    if not os.path.exists(path):
        return {}
    out = {}
    for r in pd.read_csv(path).itertuples(index=False):
        out.setdefault((r.away, r.home), []).append((r.market, r.side, r.line, r.odds, r.book))
    return out


def apply_my_lines(df, season, week):
    """betting/my_lines.csv lets you price games at the numbers your own book is offering."""
    path = os.path.join(HERE, "my_lines.csv")
    if not os.path.exists(path):
        return df
    df = df.copy()
    mine = pd.read_csv(path, comment="#").dropna(how="all")
    for r in mine.itertuples(index=False):
        idx = df[(df.season == season) & (df.week == week) & (df.home == r.home) & (df.away == r.away)].index
        for col, src, conv in (("spread_line", "home_spread", lambda v: -v), ("home_spread_odds", "home_spread_odds", None),
                               ("away_spread_odds", "away_spread_odds", None), ("total_line", "total", None),
                               ("over_odds", "over_odds", None), ("under_odds", "under_odds", None),
                               ("home_ml", "home_ml", None), ("away_ml", "away_ml", None)):
            v = getattr(r, src, None)
            if v is not None and pd.notna(v):
                df.loc[idx, col] = conv(v) if conv else v
    return df


def main():
    week_only = "--week" in sys.argv
    df = F.build()
    current = int(df.loc[df.result.notna(), "season"].max())
    out = {}
    if not week_only:
        _df, games, bets, _info, _c = run()
        acc, weights, table = summarize(games, bets)
        print("\nRMSE, 2015-now (lower is better)")
        for m, d in acc.items():
            print(" ", m, {k: round(v, 3) for k, v in d.items()})
        print("\nBlend weight on the model each season (0 = trust the market fully)")
        print(weights.to_string())
        print(f"\nBacktest vs CLOSING lines, 1 unit flat bets. holdout = {FIRST_REPORT}-{current} (never used for tuning)")
        print(table.to_string(index=False))
        out["backtest"] = {"accuracy": acc, "weights": weights.reset_index().to_dict("records"),
                           "table": table.to_dict("records"), "from": FIRST_REPORT, "to": current}
        bets.to_csv(os.path.join(HERE, "data", "backtest_bets.csv"), index=False)
    week, card = current_card(df, current)
    if card:
        board, picks, ws, wt = card
        print(f"\n{current} week {week}: fair lines (model weight spread {ws:.2f}, total {wt:.2f})")
        print(board.to_string(index=False))
        n = int((picks["tier"] == "BET").sum()) if len(picks) else 0
        if not book_offers():
            print("\nNo FanDuel/DraftKings odds loaded (add betting/odds_api_key.txt). Prices below are consensus:"
                  " check your FD/DK app against the target column.")
        print(f"\n{n} bet(s) clear the {100 * MIN_EV['spread']:.0f}% EV bar. lean = 1-3%, watch = model's side but no edge at this price")
        if len(picks):
            print(picks.drop(columns=["game_id", "side", "line", "push%"]).to_string(index=False))
        import track
        log = track.grade(track.log_picks(picks.to_dict("records")), df, no_vig, payout)
        track.save(log)
        out["tracker"] = {"summary": track.summary(log), "recent": log.tail(25).fillna("").to_dict("records")}
        out["week"] = {"season": current, "week": week, "board": board.to_dict("records"),
                       "picks": picks.to_dict("records"), "w_spread": ws, "w_total": wt}
    path = os.path.join(HERE, "data", "card.json")
    if week_only and os.path.exists(path):
        with open(path) as f:
            out["backtest"] = json.load(f).get("backtest")
    with open(path, "w") as f:
        json.dump(out, f, indent=1, default=str)
    import report
    report.write(out)


if __name__ == "__main__":
    main()
