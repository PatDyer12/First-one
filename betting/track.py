"""Bet log with closing-line value (CLV): the best early sign of whether the model has a real edge.

Every BET the model recommends is logged the first time it appears, at the line and odds offered then
(or the numbers from my_lines.csv). Once the game is played it is graded against the result, and against the
closing line: did the market move toward you after you bet? Beating the close consistently is what winning
bettors do; results alone take hundreds of bets to separate skill from luck.

The log lives in betting/bet_log.csv. Set `placed` to "no" on anything you didn't actually bet.
"""
import os
from datetime import datetime

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "bet_log.csv")
COLS = ["logged", "tier", "game_id", "game", "market", "side", "book", "bet", "line", "odds", "win_prob", "ev", "stake",
        "placed", "close_line", "close_odds", "clv_pts", "clv_prob", "result", "units"]


def load():
    if os.path.exists(LOG):
        return pd.read_csv(LOG, dtype={"placed": str})
    return pd.DataFrame(columns=COLS)


def log_picks(picks):
    log = load()
    have = set(zip(log.game_id, log.market, log.side))
    new = []
    for p in picks:
        if p["tier"] not in ("BET", "SYSTEM") or (p["game_id"], p["market"], p["side"]) in have:
            continue
        new.append({"logged": datetime.now().strftime("%Y-%m-%d %H:%M"), "tier": p.get("system", p["tier"]), "game_id": p["game_id"], "game": p["game"],
                    "market": p["market"], "side": p["side"], "book": p.get("book", ""), "bet": p["bet"], "line": p["line"], "odds": p["odds"],
                    "win_prob": p["win%"] / 100, "ev": p["ev%"] / 100, "stake": p["stake%"] / 100, "placed": "yes"})
    if new:
        log = pd.concat([log, pd.DataFrame(new)], ignore_index=True)
    return log


def grade(log, games, no_vig, payout):
    """Fill in closing line, CLV and result for every logged bet whose game is final."""
    g = games.set_index("game_id")
    for i, b in log.iterrows():
        if b.game_id not in g.index:
            continue
        r = g.loc[b.game_id]
        side, m = b.side, b.market
        if m == "spread":
            close = r.spread_line
            clv = (close - b.line) if side == "home" else (b.line - close)
            odds_close = r.home_spread_odds if side == "home" else r.away_spread_odds
            p_close = no_vig(r.home_spread_odds, r.away_spread_odds)
        elif m == "total":
            close = r.total_line
            clv = (close - b.line) if side == "over" else (b.line - close)
            odds_close = r.over_odds if side == "over" else r.under_odds
            p_close = no_vig(r.over_odds, r.under_odds)
        else:
            close, clv = None, None
            odds_close = r.home_ml if side == "home" else r.away_ml
            p_close = no_vig(r.home_ml, r.away_ml)
        if side in ("away", "under"):
            p_close = 1 - p_close
        log.at[i, "close_line"] = close
        log.at[i, "close_odds"] = odds_close
        log.at[i, "clv_pts"] = clv
        # CLV in probability: no-vig closing price of your side vs the break-even of the price you took
        # (for spreads/totals this counts line moves only when the closing odds move; clv_pts shows the rest)
        log.at[i, "clv_prob"] = round(p_close - 1 / (1 + payout(b.odds)), 4) if m == "ml" else None
        if pd.isna(r.result):
            continue
        if m == "spread":
            d = r.result - b.line
            d = d if side == "home" else -d
        elif m == "total":
            d = r.total - b.line
            d = d if side == "over" else -d
        else:
            d = r.result if side == "home" else -r.result
        log.at[i, "result"] = "W" if d > 0 else "L" if d < 0 else "P"
        log.at[i, "units"] = payout(b.odds) if d > 0 else -1.0 if d < 0 else 0.0
    return log


def save(log):
    log.reindex(columns=COLS).to_csv(LOG, index=False)


def summary(log):
    done = log[(log.placed.fillna("yes") != "no") & log.result.notna()]
    if not len(done):
        return None
    clv = done.clv_pts.dropna()
    return {"bets": int(len(done)), "record": f"{(done.result == 'W').sum()}-{(done.result == 'L').sum()}-{(done.result == 'P').sum()}",
            "units": round(float(done.units.sum()), 2), "roi%": round(100 * float(done.units.mean()), 1),
            "avg_clv_pts": round(float(clv.mean()), 2) if len(clv) else None,
            "beat_close%": round(100 * float((clv > 0).mean()), 1) if len(clv) else None,
            "open": int(((log.placed.fillna("yes") != "no") & log.result.isna()).sum())}
