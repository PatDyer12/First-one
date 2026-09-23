#!/usr/bin/env python3
"""Pick settings using ONLY 2014-2018 results, so 2019-now stays an honest holdout.

Scores each configuration by walk-forward prediction of the tuning seasons (each season predicted by a
model trained on earlier seasons), blended with the closing line the same way model.py does.
Prints the scores; winning settings get copied into features.PARAMS / model.MODEL_CFG by hand.

Usage: python3 betting/tune.py [experiments|params|model]
"""
import itertools
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import features as F  # noqa: E402
import model as M  # noqa: E402

TUNE = range(2014, 2019)
OLD_SPREAD = ["elo_diff", "net_epa", "net_sr", "net_pass_epa", "net_rush_epa", "net_pts", "qb_diff",
              "qb_change_diff", "hfa", "rest_diff", "div"]
OLD_TOTAL = ["sum_epa", "sum_sr", "sum_pass_epa", "sum_rush_epa", "sum_pts", "qb_sum", "pace_sum", "lg_pts",
             "dome", "wind", "cold", "div", "playoff"]


def score(df, sp_cols=None, tot_cols=None, cfg=None, seasons=TUNE):
    cfg = dict(M.MODEL_CFG, **(cfg or {}))
    out = {}
    for m, target, line, cols in (("spread", "result", "spread_line", sp_cols or F.SPREAD_FEATURES),
                                  ("total", "total", "total_line", tot_cols or F.TOTAL_FEATURES)):
        preds = []
        for s in range(min(seasons) - 2, max(seasons) + 1):
            tr = df[(df.season >= M.FIRST_TRAIN) & (df.season < s) & df[target].notna()]
            te = df[(df.season == s) & df[target].notna() & df[line].notna()].copy()
            te["base"] = M.fit_base(tr, target, cols, line if cfg["resid"] else None, cfg)(te)
            preds.append(te)
        p = pd.concat(preds)
        res = []
        for s in seasons:  # blend weight from earlier seasons only, like the live model
            w = M.blend_weight(p[p.season < s], target, line)
            t = p[p.season == s]
            res.append(pd.DataFrame({"y": t[target], "line": t[line], "fair": w * t["base"] + (1 - w) * t[line],
                                     "base": t["base"]}))
        r = pd.concat(res)
        edge = r.fair - r.line
        out[m] = {"rmse_line": np.sqrt(((r.y - r.line) ** 2).mean()), "rmse_fair": np.sqrt(((r.y - r.fair) ** 2).mean()),
                  "rmse_model": np.sqrt(((r.y - r.base) ** 2).mean()),
                  "edge_corr": np.corrcoef(edge, r.y - r.line)[0, 1] if edge.std() > 0 else 0.0}
        out[m]["gain"] = out[m]["rmse_line"] - out[m]["rmse_fair"]
    return out


def show(name, sc):
    print(f"{name:34s}" + "  ".join(f"{m}: model {v['rmse_model']:.3f} fair {v['rmse_fair']:.3f} "
                                     f"gain {v['gain']:+.4f} edge_r {v['edge_corr']:+.3f}" for m, v in sc.items()), flush=True)


def experiments():
    df = F.build()
    show("old features", score(df, OLD_SPREAD, OLD_TOTAL))
    show("new features", score(df))
    show("new features, predict gap to line", score(df, cfg={"resid": True}))
    show("old features, predict gap to line", score(df, OLD_SPREAD, OLD_TOTAL, cfg={"resid": True}))


def params():
    grid = {"decay": [0.85, 0.90, 0.94], "carry": [0.3, 0.45, 0.6], "prior_games": [1.5, 3, 5],
            "qb_prior_db": [150, 250, 400], "qb_decay": [0.92, 0.95, 0.98], "elo_k": [15, 20, 25],
            "mkt_rate": [0.2, 0.35, 0.5], "ats_decay": [0.7, 0.8, 0.9]}
    best = dict(F.PARAMS)
    total = lambda sc: sc["spread"]["gain"] + sc["total"]["gain"]  # noqa: E731
    base = total(score(F.build(best), cfg={"resid": RESID}))
    print("start", round(base, 4))
    for k, vals in grid.items():
        for v in vals:
            if v == best[k]:
                continue
            trial = dict(best, **{k: v})
            sc = score(F.build(trial), cfg={"resid": RESID})
            print(f"  {k}={v}: {total(sc):+.4f}", flush=True)
            if total(sc) > base + 0.002:
                best, base = trial, total(sc)
        print(k, "->", best[k], round(base, 4), flush=True)
    print("best params", best)


def model_cfg():
    df = F.build()
    for depth, leaf, ridge_w, alpha in itertools.product([2, 3], [60, 120], [0.3, 0.5, 0.8], [30, 100]):
        cfg = {"depth": depth, "leaf": leaf, "ridge_w": ridge_w, "alpha": alpha, "resid": RESID}
        show(str(cfg), score(df, cfg=cfg))


RESID = "--direct" not in sys.argv
if __name__ == "__main__":
    {"experiments": experiments, "params": params, "model": model_cfg}[sys.argv[1] if len(sys.argv) > 1 else "experiments"]()
