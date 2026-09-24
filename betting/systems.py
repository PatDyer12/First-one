#!/usr/bin/env python3
"""Search for the most profitable betting strategy of the last 15 seasons, NFL and college, without fooling ourselves.

1. Strategy universe: every market/side (spread home/away/fav/dog, total over/under, NFL moneyline fav/dog) crossed with
   one or two situational filters (line size, division/conference, week, primetime, rest/bye, weather, total size,
   line movement, recent ATS form...), plus the model at several edge thresholds.
2. Full-period leaderboard, with a bootstrap "reality check" (White 2000): how good would the best of this many
   strategies look if none had any edge? Beating that is the bar for "real edge".
3. Walk-forward: every season, pick the strategies that had been most profitable in the seasons before, bet them
   that season. This is what "find the most profitable model" actually earns going forward.

4. Proven + hot: strategies profitable over the long run (t >= 1) ranked by the last two seasons, and a test of
   whether that rule would have picked next season's winners in the past.

Usage: python3 betting/systems.py [nfl|cfb]   (writes betting/data[/cfb]/systems.json)
"""
import itertools
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

FIRST, LAST = 2011, 2025
MIN_BETS_FULL = 200
MIN_BETS_TRAIN = 120
RNG = np.random.default_rng(0)


def payout(o):
    o = np.where(np.isnan(o), -110.0, o)
    return np.where(o > 0, o / 100, 100 / -o)


def units(diff, odds):
    """diff > 0 win, 0 push, < 0 loss."""
    return np.where(diff > 0, payout(odds), np.where(diff < 0, -1.0, 0.0))


def outcomes(df):
    r, L, T, TL = (df[c].values.astype(float) for c in ("result", "spread_line", "total", "total_line"))
    home_fav = L > 0
    o = {"spread home": units(r - L, df["home_spread_odds"].values.astype(float)),
         "spread away": units(L - r, df["away_spread_odds"].values.astype(float)),
         "total over": units(T - TL, df["over_odds"].values.astype(float)),
         "total under": units(TL - T, df["under_odds"].values.astype(float))}
    o["spread fav"] = np.where(home_fav, o["spread home"], o["spread away"])
    o["spread dog"] = np.where(home_fav, o["spread away"], o["spread home"])
    valid = {k: ~np.isnan(L) for k in o}
    for k in ("total over", "total under"):
        valid[k] = ~np.isnan(TL)
    for k in ("spread fav", "spread dog"):
        valid[k] = ~np.isnan(L) & (L != 0)
    if df["home_ml"].notna().mean() > 0.5:
        hm, am = df["home_ml"].values.astype(float), df["away_ml"].values.astype(float)
        ml_home, ml_away = units(r, hm), units(-r, am)
        o["ml fav"] = np.where(home_fav, ml_home, ml_away)
        o["ml dog"] = np.where(home_fav, ml_away, ml_home)
        ok = ~np.isnan(hm) & ~np.isnan(am) & (L != 0)
        valid["ml fav"] = valid["ml dog"] = ok
    return o, valid


def nfl_conditions(df):
    a, L, T = df["spread_line"].abs(), df["spread_line"], df["total_line"]
    reg = df["game_type"] == "REG"
    return {
        "line": {"line<=3": a <= 3, "line 3.5-7": (a > 3) & (a <= 7), "line 7.5-13.5": (a > 7) & (a < 14), "line>=14": a >= 14},
        "div": {"division": df["div"] == 1, "non-division": df["div"] == 0},
        "time": {"weeks 1-4": reg & (df["week"] <= 4), "weeks 5-12": reg & df["week"].between(5, 12),
                 "weeks 13+": reg & (df["week"] >= 13), "playoffs": ~reg},
        "slot": {"primetime": df["prime"] == 1, "daytime": df["prime"] == 0},
        "rest": {"home off bye": df["bye_diff"] == 1, "away off bye": df["bye_diff"] == -1, "short week": df["short_diff"] != 0},
        "weather": {"wind>=12": df["wind"] >= 12, "dome": df["dome"] == 1, "cold<32F": df["cold"] >= 8},
        "total": {"total<=41": T <= 41, "total 41.5-47.5": (T > 41) & (T < 48), "total>=48": T >= 48},
        "move": {"line moved to home 1.5+": df["line_move"] >= 1.5, "line moved to away 1.5+": df["line_move"] <= -1.5},
        "form": {"home hot ATS": df["h_ats"] >= 4, "away hot ATS": df["a_ats"] >= 4,
                 "home cold ATS": df["h_ats"] <= -4, "away cold ATS": df["a_ats"] <= -4},
        "site": {"neutral site": df["hfa"] == 0},
    }


def cfb_conditions(df):
    a, T = df["spread_line"].abs(), df["total_line"]
    post = df["postseason"] == 1
    return {
        "line": {"line<=3": a <= 3, "line 3.5-7": (a > 3) & (a <= 7), "line 7.5-14": (a > 7) & (a <= 14),
                 "line 14.5-21": (a > 14) & (a <= 21), "line 21.5-30": (a > 21) & (a <= 30), "line>30": a > 30},
        "conf": {"conference": df["conf"] == 1, "non-conference": df["conf"] == 0},
        "time": {"weeks 0-3": ~post & (df["week"] <= 3), "weeks 4-8": ~post & df["week"].between(4, 8),
                 "weeks 9+": ~post & (df["week"] >= 9), "bowls/playoff": post},
        "opp": {"vs FCS": df["div_diff"] != 0},
        "rest": {"home more rest": df["rest_diff"] >= 3, "away more rest": df["rest_diff"] <= -3},
        "total": {"total<=45": T <= 45, "total 45.5-55.5": (T > 45) & (T < 56), "total 56-65": (T >= 56) & (T <= 65), "total>65": T > 65},
        "move": {"line moved to home 3+": df["line_move"] >= 3, "line moved to away 3+": df["line_move"] <= -3},
        "site": {"neutral site": df["hfa"] == 0},
    }


def model_strategies(bets_path, df):
    """The model at several edge thresholds, from its walk-forward backtest (one side per game and market)."""
    if not os.path.exists(bets_path):
        return {}
    b = pd.read_csv(bets_path)
    b = b.sort_values("ev").groupby(["game_id", "market"]).tail(1)
    idx = pd.Series(np.arange(len(df)), index=df["game_id"].values)
    out = {}
    for m in b["market"].unique():
        for thr in (0.0, 0.01, 0.02, 0.03, 0.05):
            s = b[(b["market"] == m) & (b["ev"] > thr)]
            s = s[s["game_id"].isin(idx.index)]
            u = np.full(len(df), np.nan)
            u[idx[s["game_id"]].values] = s["units"].values
            out[f"MODEL {m} edge>{thr:.0%}"] = u
    return out


def build_universe(df, conds, extra):
    o, valid = outcomes(df)
    flat = [("all", None, np.ones(len(df), bool))]
    for grp, cs in conds.items():
        for name, mask in cs.items():
            flat.append((name, grp, mask.fillna(False).values if hasattr(mask, "fillna") else mask))
    combos = [(n, m) for n, _g, m in flat]
    for (n1, g1, m1), (n2, g2, m2) in itertools.combinations(flat[1:], 2):
        if g1 != g2:
            combos.append((f"{n1} & {n2}", m1 & m2))
    names, cols = [], []
    for side, u in o.items():
        for cname, mask in combos:
            m = mask & valid[side]
            if m.sum() < 60:
                continue
            names.append(f"{side} | {cname}")
            cols.append(np.where(m, u, np.nan))
    for k, u in extra.items():
        names.append(k)
        cols.append(u)
    return names, np.column_stack(cols)


def stats(U):
    bet = ~np.isnan(U)
    n = bet.sum(0)
    s = np.nansum(U, 0)
    mean = s / np.maximum(n, 1)
    sd = np.sqrt(np.nansum((U - mean) ** 2, 0) / np.maximum(n - 1, 1))
    t = mean / np.maximum(sd, 1e-9) * np.sqrt(n)
    return n, s, mean, t


def reality_check(U, keep, reps=400):
    """Distribution of the best t-stat among all strategies when every strategy truly has zero edge
    (each strategy's results re-centred to mean 0, games resampled with replacement)."""
    Uk = U[:, keep]
    bet = ~np.isnan(Uk)
    n, _s, mean, _t = stats(Uk)
    sd = np.sqrt(np.nansum((Uk - mean) ** 2, 0) / np.maximum(n - 1, 1))
    C = np.where(bet, Uk - mean, 0.0)
    B = bet.astype(float)
    best = []
    for _ in range(reps // 50):
        w = RNG.multinomial(len(C), np.ones(len(C)) / len(C), size=50).astype(float)
        ns, ss = w @ B, w @ C
        best.append(((ss / np.maximum(ns, 1)) / np.maximum(sd, 1e-9) * np.sqrt(ns)).max(1))
    return np.concatenate(best)


def walk_forward(U, seasons, names, top_k, window, rank_by, first_test=2016):
    rows, picks = [], {}
    for S in sorted(set(seasons)):
        if S < first_test:
            continue
        tr = (seasons < S) & (seasons >= (S - window if window else FIRST))
        n, s, mean, t = stats(U[tr])
        score = t if rank_by == "t" else mean
        ok = (n >= (MIN_BETS_TRAIN if not window else MIN_BETS_TRAIN // 2)) & (mean > 0)
        order = [j for j in np.argsort(-np.where(ok, score, -np.inf)) if ok[j]][:top_k]
        picks[int(S)] = [names[j] for j in order]
        te = seasons == S
        for j in order:
            u = U[te, j]
            u = u[~np.isnan(u)]
            rows.append({"season": int(S), "strategy": names[j], "bets": len(u), "units": float(u.sum())})
    r = pd.DataFrame(rows)
    return r, picks


def hot_pick(U, seasons, S, k=10):
    """Profitable over seasons < S-2 (t >= 1, 150+ bets), then ranked by units in seasons S-2 and S-1."""
    lo, re = seasons < S - 2, (seasons >= S - 2) & (seasons < S)
    n1, _s1, m1, t1 = stats(U[lo])
    n2, s2, m2, _t2 = stats(U[re])
    ok = (n1 >= 150) & (t1 >= 1.0) & (m1 > 0) & (n2 >= 25) & (m2 > 0)
    return [j for j in np.argsort(-np.where(ok, s2, -np.inf)) if ok[j]][:k], (n1, m1, t1, n2, s2, m2)


def proven_and_hot(U, seasons, names):
    now = int(seasons.max()) + 1
    order, (n1, m1, t1, n2, s2, m2) = hot_pick(U, seasons, now)
    board = [{"strategy": names[j], "bets_before": int(n1[j]), "roi_before%": round(100 * float(m1[j]), 1), "t": round(float(t1[j]), 2),
              "bets_last2": int(n2[j]), "units_last2": round(float(s2[j]), 1), "roi_last2%": round(100 * float(m2[j]), 1)} for j in order]
    test = {}
    for k in (1, 3, 10):
        per = {}
        for S in range(2016, now - 1):
            o, _ = hot_pick(U, seasons, S)
            u = [U[seasons == S, j] for j in o[:k]]
            u = np.concatenate([x[~np.isnan(x)] for x in u]) if u else np.array([])
            per[S] = (len(u), float(u.sum()))
        bets, tot = sum(v[0] for v in per.values()), sum(v[1] for v in per.values())
        test[k] = {"bets": bets, "roi%": round(100 * tot / max(bets, 1), 1),
                   "winning_seasons": f"{sum(v[1] > 0 for v in per.values())}/{len(per)}"}
    return board, test


def run(sport):
    if sport == "nfl":
        import features as F
        df = F.build()
        conds_fn, bets_path, out_dir = nfl_conditions, os.path.join(HERE, "data", "backtest_bets.csv"), os.path.join(HERE, "data")
    else:
        import cfb_features as C
        df = C.build()
        conds_fn, bets_path, out_dir = cfb_conditions, os.path.join(HERE, "data", "cfb", "backtest_bets.csv"), os.path.join(HERE, "data", "cfb")
    df = df[df["result"].notna() & df["spread_line"].notna() & (df["season"] >= FIRST)].reset_index(drop=True)
    names, U = build_universe(df, conds_fn(df), model_strategies(bets_path, df))
    seasons = df["season"].values
    hist = seasons <= LAST
    n, s, mean, t = stats(U[hist])
    keep = np.where(n >= MIN_BETS_FULL)[0]
    print(f"\n===== {sport.upper()}: {len(names)} strategies tested, {len(keep)} with {MIN_BETS_FULL}+ bets, {FIRST}-{LAST} =====")
    null_best = reality_check(U[hist], keep)
    order = keep[np.argsort(-t[keep])][:15]
    board = []
    for j in order:
        p = float((null_best >= t[j]).mean())
        board.append({"strategy": names[j], "bets": int(n[j]), "units": round(float(s[j]), 1), "roi%": round(100 * float(mean[j]), 1),
                      "t": round(float(t[j]), 2), "luck_p": round(p, 3)})
    print(pd.DataFrame(board).to_string(index=False))
    print(f"best t-stat expected from pure luck: median {np.median(null_best):.2f}, 95th pct {np.percentile(null_best, 95):.2f}")

    wf = {}
    for top_k, window, rank_by in itertools.product([1, 5, 20], [0, 5], ["roi", "t"]):
        r, picks = walk_forward(U, seasons, names, top_k, window, rank_by)
        key = f"top {top_k} by {rank_by}, {'all prior seasons' if not window else f'last {window} seasons'}"
        tot_b, tot_u = int(r["bets"].sum()), float(r["units"].sum())
        per = r.groupby("season")["units"].sum().round(1).to_dict()
        wf[key] = {"bets": tot_b, "units": round(tot_u, 1), "roi%": round(100 * tot_u / max(tot_b, 1), 1),
                   "winning_seasons": f"{sum(v > 0 for v in per.values())}/{len(per)}", "by_season": per,
                   "latest_picks": picks[max(picks)]}
    print("\nWalk-forward: each season bet what had been best before it (2016-2026, never peeking ahead)")
    print(pd.DataFrame({k: {c: v[c] for c in ("bets", "units", "roi%", "winning_seasons")} for k, v in wf.items()}).T.to_string())

    # persistence: does a strategy's first-half ROI predict its second-half ROI?
    half = (FIRST + LAST) // 2
    n1, _s1, m1, _t1 = stats(U[seasons <= half])
    n2, _s2, m2, _t2 = stats(U[(seasons > half) & hist])
    ok = (n1 >= 100) & (n2 >= 100)
    top = ok & (m1 >= np.nanpercentile(m1[ok], 90))
    pers = {"corr": round(float(np.corrcoef(m1[ok], m2[ok])[0, 1]), 3),
            "top10pct_first_half_roi%": round(100 * float(m1[top].mean()), 1),
            "same_strategies_second_half_roi%": round(100 * float(m2[top].mean()), 1)}
    print(f"\nPersistence {FIRST}-{half} -> {half + 1}-{LAST}: {pers}")
    hot, hot_test = proven_and_hot(U, seasons, names)
    print("\nProven + hot: profitable before the last two seasons (t >= 1), ranked by the last two seasons' units")
    print(pd.DataFrame(hot).to_string(index=False))
    print("Rule tested on past seasons (pick this way, bet the next season): "
          + "; ".join(f"top {k}: {v['bets']} bets, ROI {v['roi%']:+}%, {v['winning_seasons']} winning" for k, v in hot_test.items()))
    out = {"sport": sport, "tested": len(names), "proven_and_hot": hot, "proven_and_hot_test": hot_test, "leaderboard": board, "walk_forward": wf, "persistence": pers,
           "luck_best_t": {"median": round(float(np.median(null_best)), 2), "p95": round(float(np.percentile(null_best, 95)), 2)}}
    with open(os.path.join(out_dir, "systems.json"), "w") as f:
        json.dump(out, f, indent=1)
    return out


if __name__ == "__main__":
    for sp in (sys.argv[1:] or ["nfl", "cfb"]):
        run(sp)
