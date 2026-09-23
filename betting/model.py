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
FIRST_BASE_TEST = 2012
FIRST_REPORT = 2015
MIN_EV = {"spread": 0.03, "total": 0.03, "ml": 0.03}
LEAN_EV = 0.01
KELLY_FRACTION = 0.25
MAX_STAKE = 0.03
MARKETS = {"spread": ("result", "spread_line", F.SPREAD_FEATURES, 0.75, np.arange(-30, 30.5, 0.5)),
           "total": ("total", "total_line", F.TOTAL_FEATURES, 1.0, np.arange(28, 70.5, 0.5))}
SCORES = np.arange(-80, 121)


# ---------- base models ----------
def fit_base(train, target, cols):
    X, y = train[cols].values, train[target].values
    ridge = make_pipeline(StandardScaler(), Ridge(alpha=30.0)).fit(X, y)
    gbm = HistGradientBoostingRegressor(max_depth=3, learning_rate=0.03, max_iter=250, min_samples_leaf=60,
                                        l2_regularization=5.0, random_state=0).fit(X, y)
    return lambda d: 0.5 * ridge.predict(d[cols].values) + 0.5 * gbm.predict(d[cols].values)


def blend_weight(hist, target, line):
    """Least-squares w in [0, 1] for  target - line = w * (model - line)."""
    h = hist.dropna(subset=[target, line, "base"])
    x, y = (h["base"] - h[line]).values, (h[target] - h[line]).values
    return float(np.clip((x @ y) / max(x @ x, 1e-9), 0, 1)) if len(h) else 0.0


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


def anchored(fair_pmf, mkt_pmf, L, market_p):
    """Win/push/lose for the 'over L' side: start from the market's no-vig price and move it only by
    how far our fair line sits from the market line (measured with the real score distribution)."""
    w_f, pu, lo_f = over_under(fair_pmf, L)
    w_m, _pm, lo_m = over_under(mkt_pmf, L)
    shift = logit(w_f / (w_f + lo_f)) - logit(w_m / (w_m + lo_m))
    q = 1 / (1 + math.exp(-(logit(market_p) + shift)))
    return q * (1 - pu), pu, (1 - q) * (1 - pu)


def options(row, sp, sp_mkt, tot, tot_mkt):
    """Every bet on the board for a game with our win/push/lose probabilities."""
    out = []
    if pd.notna(row.spread_line):
        L = row.spread_line
        w, pu, lo = anchored(sp, sp_mkt, L, no_vig(row.home_spread_odds, row.away_spread_odds))
        out.append(("spread", row.home, f"{row.home} {-L:+g}", w, pu, lo, row.home_spread_odds, "home"))
        out.append(("spread", row.away, f"{row.away} {L:+g}", lo, pu, w, row.away_spread_odds, "away"))
    if pd.notna(row.home_ml) and pd.notna(row.away_ml):
        w, pu, lo = anchored(sp, sp_mkt, 0, no_vig(row.home_ml, row.away_ml))
        out.append(("ml", row.home, f"{row.home} ML", w, pu, lo, row.home_ml, "home"))
        out.append(("ml", row.away, f"{row.away} ML", lo, pu, w, row.away_ml, "away"))
    if pd.notna(row.total_line):
        L = row.total_line
        w, pu, lo = anchored(tot, tot_mkt, L, no_vig(row.over_odds, row.under_odds))
        out.append(("total", "over", f"Over {L:g}", w, pu, lo, row.over_odds, "over"))
        out.append(("total", "under", f"Under {L:g}", lo, pu, w, row.under_odds, "under"))
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
        test[f"base_{m}"] = fit_base(train, target, cols)(test)
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
        if season < FIRST_REPORT:
            continue
        for r in test[test.result.notna()].itertuples(index=False):
            for market, _t, label, w, pu, lo, odds, side in options(r, *game_pmfs(r, (info["spread"][1], info["total"][1]))):
                ev, stake = evaluate(w, pu, lo, odds)
                bets.append({"season": r.season, "week": r.week, "game_id": r.game_id, "market": market,
                             "bet": label, "p": w, "ev": ev, "stake": stake,
                             "units": settle(r, market, side, odds)})
    all_games = pd.concat(seasons_out)
    return df, all_games, pd.DataFrame(bets), info, current


def summarize(games, bets):
    lines = []
    g = games[(games.season >= FIRST_REPORT) & games.result.notna()]
    rm = lambda a, b: float(np.sqrt(np.mean((a - b) ** 2)))  # noqa: E731
    acc = {
        "spread": {"closing line": rm(g.result, g.spread_line), "model alone": rm(g.result, g.base_spread),
                   "blend": rm(g.result, g.fair_spread)},
        "total": {"closing line": rm(g.total, g.total_line), "model alone": rm(g.total, g.base_total),
                  "blend": rm(g.total, g.fair_total)}}
    weights = g.groupby("season")[["w_spread", "w_total"]].first().round(2)
    table = []
    for m in ("spread", "total", "ml"):
        for thr in (0.0, 0.02, 0.03, 0.05, 0.08):
            b = bets[(bets.market == m) & (bets.ev > thr)]
            # one bet per game per market: the side with the higher EV
            b = b.sort_values("ev").groupby(["game_id"]).tail(1)
            if not len(b):
                continue
            wins, losses, pushes = (b.units > 0).sum(), (b.units < 0).sum(), (b.units == 0).sum()
            kelly_growth = float(np.prod(1 + b.stake * b.units))
            table.append({"market": m, "min_ev": thr, "bets": len(b), "record": f"{wins}-{losses}-{pushes}",
                          "win%": round(100 * wins / max(wins + losses, 1), 1),
                          "units": round(b.units.sum(), 1), "roi%": round(100 * b.units.mean(), 1),
                          "kelly_bankroll_x": round(kelly_growth, 2)})
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
            t["base"] = fit_base(train, target, cols)(test)
            oos[m] = pd.concat([oos[m], t])
    train = df[(df.season >= FIRST_TRAIN) & df.result.notna()]
    wk = df[(df.season == current) & (df.week == week)].copy()
    pmfs = {}
    for m, (target, line, cols, bw, grid) in MARKETS.items():
        wk[f"base_{m}"] = fit_base(train, target, cols)(wk)
        w = blend_weight(oos[m], target, line)
        wk[f"w_{m}"] = w
        wk[f"fair_{m}"] = (w * wk[f"base_{m}"] + (1 - w) * wk[line]).fillna(wk[f"base_{m}"])
        pmfs[m] = pmf_table(train, target, line, bw, grid, m == "spread")
    rows, picks = [], []
    for r in wk.itertuples(index=False):
        pm = game_pmfs(r, (pmfs["spread"], pmfs["total"]))
        home_win = over_under(pm[0], 0)
        if pd.notna(r.home_ml) and pd.notna(r.away_ml):
            hw = anchored(pm[0], pm[1], 0, no_vig(r.home_ml, r.away_ml))
            home_win = (hw[0], hw[1])
        rows.append({"game": f"{r.away} @ {r.home}", "gameday": r.gameday, "qbs": f"{r.away_qb or '?'} / {r.home_qb or '?'}",
                     "market_spread": f"{r.home} {-r.spread_line:+g}" if pd.notna(r.spread_line) else "",
                     "model_spread": f"{r.home} {-r.base_spread:+.1f}", "fair_spread": f"{r.home} {-r.fair_spread:+.1f}",
                     "market_total": r.total_line, "model_total": round(r.base_total, 1), "fair_total": round(r.fair_total, 1),
                     "home_win%": round(100 * (home_win[0] + home_win[1] / 2), 1),
                     "fair_ml": f"{r.home} {to_american(home_win[0] + home_win[1] / 2):+d}"})
        best = {}
        for market, _t, label, w, pu, lo, odds, side in options(r, *pm):
            ev, stake = evaluate(w, pu, lo, odds)
            if ev > LEAN_EV and (market not in best or ev > best[market]["ev"]):
                best[market] = {"game": f"{r.away} @ {r.home}", "market": market, "bet": label,
                                "odds": int(odds) if pd.notna(odds) else -110, "win%": round(100 * w / max(w + lo, 1e-9), 1),
                                "push%": round(100 * pu, 1), "ev": ev,
                                "stake%": round(100 * stake, 2) if ev > MIN_EV[market] else 0.0,
                                "tier": "BET" if ev > MIN_EV[market] else "lean"}
        picks += best.values()
    picks = pd.DataFrame(picks)
    if len(picks):
        picks = picks.sort_values("ev", ascending=False)
        picks["ev%"] = (100 * picks.pop("ev")).round(1)
    return week, (pd.DataFrame(rows), picks, float(wk.w_spread.iloc[0]), float(wk.w_total.iloc[0]))


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
        print(f"\nBacktest {FIRST_REPORT}-{current} vs CLOSING lines, 1 unit flat bets")
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
        print(f"\n{n} bet(s) clear the {100 * MIN_EV['spread']:.0f}% EV bar; leans are 1%+ (track them, don't bet them)")
        if len(picks):
            print(picks.to_string(index=False))
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
