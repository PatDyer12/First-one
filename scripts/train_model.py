#!/usr/bin/env python3
"""Fit the trade-value model on 2022-2025 and freeze it in data/model.json.

For every player-season we take what was known after week 2 (preseason
projection, ADP, early production, usage, team scoring, record, QB quality,
age, experience) and learn how well each factor predicted:
  ros  - points per game over weeks 3-17 of that season
  next - points per game the following season (for dynasty / keeper)

Ridge regression on standardized factors; the penalty is picked by
leave-one-season-out cross-validation. Re-run only when you want to
re-fit; fetch_data.py just applies the frozen coefficients.
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from features import FEATURES, LABELS, POSITIONS, ROOT, build_rows, get_json, played, preseason, stats_week, vectorize  # noqa: E402

SEASONS = [2022, 2023, 2024, 2025]
CURRENT = 2026
ALPHAS = [0.3, 1, 3, 10, 30, 100, 300, 1000]
CORE = {"QB": ["pre", "adp", "act", "rushAtt", "teamPts"], "RB": ["pre", "adp", "act", "snap", "oppShare", "tgtShare"],
        "WR": ["pre", "adp", "act", "snap", "tgtShare"], "TE": ["pre", "adp", "act", "snap", "tgtShare"]}
OUT = os.path.join(ROOT, "data", "model.json")


def season_ppg(season, weeks, min_games):
    tot = {}
    for w in weeks:
        for row in stats_week(season, w):
            st = row["stats"]
            if row["player"].get("position") in POSITIONS and st.get("gms_active") and played(st):
                d = tot.setdefault(row["player_id"], [0, 0])
                d[0] += st.get("pts_ppr") or 0
                d[1] += 1
    return {pid: p / g for pid, (p, g) in tot.items() if g >= min_games}


def ridge_fit(X, y, alpha):
    mu, sd = X.mean(0), X.std(0)
    sd[sd == 0] = 1
    Z = (X - mu) / sd
    ym = y.mean()
    A = Z.T @ Z + alpha * np.eye(Z.shape[1])
    b = np.linalg.solve(A, Z.T @ (y - ym))
    return {"mu": mu, "sd": sd, "b": b, "c": ym}


def ridge_pred(m, X):
    return ((X - m["mu"]) / m["sd"]) @ m["b"] + m["c"]


def r2(y, p):
    return 1 - ((y - p) ** 2).sum() / ((y - y.mean()) ** 2).sum()


def cv(X, y, seasons, alpha):
    preds = np.zeros_like(y)
    for s in set(seasons):
        tr, te = seasons != s, seasons == s
        preds[te] = ridge_pred(ridge_fit(X[tr], y[tr], alpha), X[te])
    return r2(y, preds), float(np.sqrt(((y - preds) ** 2).mean()))


def fit_target(rows, feats, target_key, pos):
    data = [r for r in rows if r["pos"] == pos and r.get(target_key) is not None]
    if len(data) < 40:
        return None
    means = {}
    for k in feats:
        if k == "adp":
            vals = [math.log(max(1.0, r["adp"])) for r in data]
        elif k == "age2":
            vals = [(r["age"] - 27) ** 2 for r in data if r.get("age") is not None]
        else:
            vals = [r[k] for r in data if r.get(k) is not None]
        means[k] = float(np.mean(vals)) if vals else 0.0
    X = np.array([vectorize(r, feats, means) for r in data])
    y = np.array([r[target_key] for r in data])
    seasons = np.array([r["season"] for r in data])
    best = max(ALPHAS, key=lambda a: cv(X, y, seasons, a)[0])
    score, rmse = cv(X, y, seasons, best)
    m = ridge_fit(X, y, best)
    return {"features": feats, "means": means, "mu": m["mu"].tolist(), "sd": m["sd"].tolist(), "coef": m["b"].tolist(),
            "intercept": float(m["c"]), "alpha": best, "cvR2": round(float(score), 4), "cvRmse": round(rmse, 3), "n": len(data)}


def main():
    allp = get_json("https://api.sleeper.app/v1/players/nfl")
    rows = []
    for y in SEASONS:
        print("season", y, file=sys.stderr)
        early = [stats_week(y, w) for w in (1, 2)]
        feats = build_rows(y, allp, early, preseason(y), CURRENT - y)
        ros = season_ppg(y, range(3, 18), 4)
        nxt = season_ppg(y + 1, range(1, 18), 6) if y + 1 < CURRENT else {}
        for pid, f in feats.items():
            if f["g"] < 1 or (f["pre"] < 3 and (f.get("act") or 0) < 6):
                continue
            f["season"] = y
            f["ros"] = ros.get(pid)
            f["next"] = nxt.get(pid)
            rows.append(f)
    print("training rows:", len(rows), file=sys.stderr)

    model = {"trainedOn": SEASONS, "labels": LABELS, "positions": {}}
    for pos in POSITIONS:
        entry = {}
        for tgt in ("ros", "next"):
            base = fit_target(rows, ["pre", "adp"], tgt, pos)
            cands = [("all factors", fit_target(rows, FEATURES[pos], tgt, pos)), ("core factors", fit_target(rows, CORE[pos], tgt, pos)), ("preseason only", base)]
            cands = [c for c in cands if c[1]]
            name, best = max(cands, key=lambda c: c[1]["cvR2"])
            best = dict(best)
            z = np.abs(np.array(best["coef"]))
            best["importance"] = (z / z.sum()).round(4).tolist()
            best["baseline"] = base
            best["chosen"] = name
            best["tested"] = {n: m["cvR2"] for n, m in cands}
            entry[tgt] = best
            print("%s %-4s n=%4d  chose %-14s R2 %.3f   tested %s" % (pos, tgt, best["n"], name, best["cvR2"], best["tested"]), file=sys.stderr)
        model["positions"][pos] = entry

    # Elasticity: how steeply the public market prices expected points, per format and position.
    # Fit on the preseason market (value 30 days ago) against the preseason expectation.
    pre26 = preseason(CURRENT)
    model["elasticity"] = {}
    for key, dyn, qbs in [("r1", "false", 1), ("r2", "false", 2), ("d1", "true", 1), ("d2", "true", 2)]:
        fc = get_json("https://api.fantasycalc.com/values/current?isDynasty=%s&numQbs=%d&numTeams=12&ppr=1" % (dyn, qbs))
        model["elasticity"][key] = {}
        for pos in POSITIONS:
            base = model["positions"][pos]["ros"]["baseline"]
            xs, ys = [], []
            for row in fc:
                p = row["player"]
                sid = p.get("sleeperId")
                if p["position"] != pos or not sid or sid not in pre26:
                    continue
                val = row["value"] - (row.get("trend30Day") or 0)
                f = {"pre": pre26[sid]["pre"], "adp": pre26[sid]["adp"] if pre26[sid]["adp"] and pre26[sid]["adp"] < 999 else 350}
                exp = float(np.dot((np.array(vectorize(f, base["features"], base["means"])) - base["mu"]) / base["sd"], base["coef"]) + base["intercept"])
                if val > 300 and exp > 4:
                    xs.append(math.log(exp))
                    ys.append(math.log(val))
            e = float(np.polyfit(xs, ys, 1)[0]) if len(xs) > 10 else 2.0
            model["elasticity"][key][pos] = round(max(0.8, min(4.0, e)), 3)
    print("elasticity", model["elasticity"], file=sys.stderr)
    json.dump(model, open(OUT, "w"), indent=1)
    print("wrote", OUT, file=sys.stderr)


if __name__ == "__main__":
    main()
