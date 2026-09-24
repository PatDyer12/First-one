#!/usr/bin/env python3
"""College football spread / total / moneyline model: same engine as the NFL model (model.py), college data.

Differences from the NFL version
  - ratings from cfb_features.py: Elo (lower divisions start below FBS), opponent-adjusted EPA with Bill
    Connelly's garbage-time rule, market power ratings; no QB/injury/travel layer (no free starter data)
  - score distributions learned from college results (bigger spreads, different key numbers)
  - this week's lines are DraftKings (free via ESPN); FanDuel too with an Odds API key
  - historical lines come without odds, so the backtest assumes -110 and cannot grade moneylines

Usage: python3 betting/cfb_model.py            backtest + this week's card -> betting/cfb_card.html
       python3 betting/cfb_model.py --week     this week only
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cfb_features as C  # noqa: E402
import model as M  # noqa: E402

M.configure(
    BUILD=C.build,
    MARKETS={"spread": ("result", "spread_line", C.SPREAD_FEATURES, 1.0, np.arange(-60, 60.5, 0.5)),
             "total": ("total", "total_line", C.TOTAL_FEATURES, 1.5, np.arange(30, 95.5, 0.5))},
    FIRST_TRAIN=2011, FIRST_BASE_TEST=2012, TUNE_FROM=2014, FIRST_REPORT=2019,
    DATA=os.path.join(HERE, "data", "cfb"), MY_LINES=os.path.join(HERE, "cfb_my_lines.csv"),
    CARD_HTML=os.path.join(HERE, "cfb_card.html"), BET_LOG=os.path.join(HERE, "cfb_bet_log.csv"),
    SYSTEMS=[{"name": "Blowout over", "market": "total", "side": "over", "stake": 0.01, "min_odds": -115,
              "why": "Spread over 30 points: the big underdog scores ~1 point more than the market expects (backups, "
                     "garbage time). Overs get better the bigger the spread (14-21: -7% ROI, 30-40: +6%, 40+: +10%). "
                     "Passed the luck test across 1,192 strategies, profitable 2011-2024 AND the best proven strategy "
                     "of 2025-2026. Strongest vs FCS opponents. Books keep limits low on these games.",
              "when": lambda d: d["spread_line"].abs() > 30}],
    TITLE="College Football Betting Model", CARD_NEEDS_LINE=True, BOOK_KEYS=("away_id", "home_id"))

if __name__ == "__main__":
    M.main()
