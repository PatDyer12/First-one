#!/usr/bin/env python3
"""Shareable weekly betting cards, one PDF per sport (designed HTML printed to PDF with headless Chromium).

Sections: Best Bets (each with why) · Leans & price watch · QB Watch (who to avoid / bet against) ·
Streaks & trends · Oddball Matchup of the Week (hand-written in oddball_<sport>.json).

Run the models first (model.py --week / cfb_model.py --week), then:
  python3 betting/share/weekly.py            -> betting/share/nfl_week<N>.pdf and cfb_week<N>.pdf
  python3 betting/share/weekly.py nfl        (one sport)
"""
import base64
import html
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
BET = os.path.dirname(HERE)
sys.path.insert(0, BET)
ASSETS = os.path.join(HERE, "assets")
LOGOS = os.path.join(ASSETS, "logos")
ET = ZoneInfo("America/New_York")
ESPN = "https://site.api.espn.com/apis/site/v2/sports/football/{}/{}"
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
NFL_ABBR = {"WSH": "WAS", "LAR": "LA"}
KEY3 = 14.4  # % of NFL games since 2011 decided by exactly 3
QB_REPL, QB_PRIOR, QB_DB = -0.10, 250.0, 36.0
E = html.escape


# ---------------------------------------------------------------- helpers
def get(url, params=None):
    for _ in range(3):
        try:
            r = requests.get(url, params=params, timeout=60)
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            continue
    return {}


def units(stake_pct):
    return max(0.5, round(stake_pct * 2) / 2)


def fmt_odds(o):
    return f"{int(o):+d}"


def logo_img(url, key, size=22):
    if not url:
        return f"<span class='nologo' style='width:{size}px;height:{size}px'></span>"
    os.makedirs(LOGOS, exist_ok=True)
    path = os.path.join(LOGOS, re.sub(r"[^A-Za-z0-9_]", "_", key) + ".png")
    if not os.path.exists(path):
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            with open(path, "wb") as f:
                f.write(r.content)
        except requests.RequestException:
            return f"<span class='nologo' style='width:{size}px;height:{size}px'></span>"
    b64 = base64.b64encode(open(path, "rb").read()).decode()
    return f"<img class='logo' style='width:{size}px;height:{size}px' src='data:image/png;base64,{b64}'>"


def short_name(full):
    """'Kirk Cousins Jr.' -> 'K.Cousins' (nflverse passer naming)."""
    parts = [p for p in re.sub(r"[.,]", " ", full).split() if p.lower() not in ("jr", "sr", "ii", "iii", "iv")]
    return f"{parts[0][0]}.{parts[-1]}" if len(parts) >= 2 else full


# ---------------------------------------------------------------- ESPN slate (logos, kickoff, venue)
def espn_slate(sport):
    league = "nfl" if sport == "nfl" else "college-football"
    params = None if sport == "nfl" else {"groups": 80, "limit": 400}
    sb = get(ESPN.format(league, "scoreboard"), params)
    games = {}
    for ev in sb.get("events", []):
        comp = ev["competitions"][0]
        t = {c["homeAway"]: c for c in comp["competitors"]}
        if "home" not in t:
            continue
        info = {"event": ev["id"], "date": ev.get("date"), "venue": comp.get("venue", {}).get("fullName", ""),
                "neutral": comp.get("neutralSite", False), "state": ev.get("status", {}).get("type", {}).get("state", "pre")}
        for side in ("home", "away"):
            tm = t[side]["team"]
            key = NFL_ABBR.get(tm["abbreviation"], tm["abbreviation"]) if sport == "nfl" else int(tm["id"])
            info[side] = {"key": key, "name": tm.get("shortDisplayName") or tm.get("displayName"), "abbr": tm["abbreviation"],
                          "logo": tm.get("logo"), "color": "#" + (tm.get("color") or "888888")}
        k = (info["away"]["key"], info["home"]["key"]) if sport == "nfl" else int(ev["id"])
        games[k] = info
    return games


def kickoff(iso):
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(ET)
        return d.strftime("%a %-m/%-d · %-I:%M %p ET")
    except (AttributeError, ValueError):
        return ""


# ---------------------------------------------------------------- data per sport
class Sport:
    def __init__(self, sport):
        self.sport = sport
        if sport == "nfl":
            import features as F
            self.df = F.build()
            self.card = json.load(open(os.path.join(BET, "data", "card.json")))
        else:
            import cfb_features as C
            self.df = C.build()
            self.card = json.load(open(os.path.join(BET, "data", "cfb", "card.json")))
        self.week = self.card["week"]["week"]
        self.season = self.card["week"]["season"]
        self.slate = espn_slate(sport)
        self.board = {b["game"]: b for b in self.card["week"]["board"]}
        up = self.df[(self.df.season == self.season) & (self.df.week == self.week) & self.df.result.isna()]
        self.rows = {}
        for r in up.itertuples(index=False):  # only games that haven't kicked off
            info = self.slate.get((r.away, r.home)) if sport == "nfl" else self.slate.get(int(r.game_id))
            if info is None or info.get("state") == "pre":
                self.rows[f"{r.away} @ {r.home}"] = r

    def upcoming(self, game):
        return game in self.rows

    # teams / logos for a "Away @ Home" game string
    def teams(self, game):
        r = self.rows.get(game)
        if r is None:
            return None, None, None
        info = self.slate.get((r.away, r.home)) if self.sport == "nfl" else self.slate.get(int(r.game_id))
        return r, info, (info or {}).get("date")

    def logos(self, game, size=22):
        r, info, _ = self.teams(game)
        if not info:
            return ""
        a, h = info["away"], info["home"]
        return (logo_img(a["logo"], f"{self.sport}_{a['key']}", size) + "<span class='at'>@</span>"
                + logo_img(h["logo"], f"{self.sport}_{h['key']}", size))

    def when(self, game):
        _r, info, date = self.teams(game)
        return kickoff(date) if date else ""

    def weather(self, game_id):
        p = os.path.join(BET, "data", "weather.csv")
        if self.sport != "nfl" or not os.path.exists(p):
            return None
        w = pd.read_csv(p).set_index("game_id")
        return w.loc[game_id] if game_id in w.index else None


# ---------------------------------------------------------------- reasons
def model_reason(S, p):
    b = S.board.get(p["game"], {})
    edge, win = p["ev%"], p["win%"]
    need = 100 / (1 + (p["odds"] / 100 if p["odds"] > 0 else 100 / -p["odds"]))
    out = []
    if p["market"] == "total":
        line = float(p["bet"].split()[-1])
        side = p["bet"].split()[0]
        out.append(f"The model projects <b>{b.get('model_total')}</b> points against a {line:g} total "
                   f"(market-blended fair total {b.get('fair_total')}).")
        cons = b.get("market_total")
        if cons is not None and abs(cons - line) >= 0.5:
            better = (line < cons) if side == "Over" else (line > cons)
            if better:
                out.append(f"DraftKings is dealing {line:g} while the wider market is at {cons:g}, a better number for this side.")
        w = S.weather(p.get("game_id"))
        if w is not None:
            out.append(f"Forecast: {w['temp']:.0f}°F, {w['wind']:.0f} mph wind.")
    elif p["market"] == "spread":
        out.append(f"Model line {b.get('model_spread')} (fair {b.get('fair_spread')}) vs the market's {b.get('market_spread')}.")
    else:
        out.append(f"Model win chance {win:.0f}% (fair price {b.get('fair_ml')}).")
    if b.get("qbs") and "?" not in b["qbs"]:
        out.append(f"QBs: {b['qbs']}.")
    out.append(f"Wins about <b>{win:.0f}%</b> by our numbers; {need:.1f}% needed at {fmt_odds(p['odds'])}.")
    return " ".join(out)


def system_reason(S, sy, g):
    b = S.board.get(g["game"], {})
    if sy["name"] == "Wind under":
        w = S.weather(g.get("game_id"))
        wind = f"{w['wind']:.0f} mph wind, {w['temp']:.0f}°F" if w is not None else "12+ mph wind"
        return (f"Kickoff forecast: <b>{wind}</b>. Wind cuts into passing and kicking, and totals historically "
                f"don't drop enough (unders +12% ROI in 12–20 mph wind since 2011). Cooled off in 2025, so half stake.")
    if sy["name"] in ("Close road team", "Close road team ML"):
        line = g["bet"].split()[-1]
        txt = (f"Road team in a coin-flip daytime game. Home field is worth less than short lines assume "
               f"(fair line {b.get('fair_spread')}).")
        if line in ("+3", "+3.5"):
            txt += f" Getting the full field goal matters: <b>{KEY3}%</b> of NFL games since 2011 landed on exactly 3."
        if g["odds"] > -105:
            txt += f" Better-than-usual price at {fmt_odds(g['odds'])}."
        return txt
    if sy["name"] == "Blowout over":
        spread = abs(float(b["market_spread"].split()[-1]))
        total = float(g["bet"].split()[-1])
        dog = g["game"].split(" @ ")[0]
        bucket = "40+ pt spreads: overs +10% ROI" if spread > 40 else "30–40 pt spreads: overs +6% ROI"
        return (f"{g['game'].split(' @ ')[1]} by {spread:g}: the market has {E(dog)} scoring only "
                f"<b>~{(total - spread) / 2:.0f}</b>. {bucket} since 2010. Model total {b.get('model_total')}.")
    return E(sy["why"])


# ---------------------------------------------------------------- streaks
def team_logs(S):
    d = S.df[(S.df.season >= S.season - 1) & S.df.result.notna()].copy()
    d = d.sort_values(["gameday", "game_id"])
    key_h, key_a = ("home", "away") if S.sport == "nfl" else ("home_id", "away_id")
    logs = {}
    for r in d.itertuples(index=False):
        for side in ("home", "away"):
            k = getattr(r, key_h if side == "home" else key_a)
            name = r.home if side == "home" else r.away
            m = r.result if side == "home" else -r.result
            su = "W" if m > 0 else "L" if m < 0 else "T"
            ats = ou = None
            if pd.notna(r.spread_line):
                c = (r.result - r.spread_line) * (1 if side == "home" else -1)
                ats = "W" if c > 0 else "L" if c < 0 else "P"
            if pd.notna(r.total_line):
                ou = "O" if r.total > r.total_line else "U" if r.total < r.total_line else "P"
            logs.setdefault(k, {"name": name, "g": []})["g"].append((su, ats, ou))
    return logs


def streak(seq):
    seq = [x for x in seq if x is not None]
    if not seq or seq[-1] in ("P", "T"):
        return None, 0
    n = 0
    for x in reversed(seq):
        if x != seq[-1]:
            break
        n += 1
    return seq[-1], n


def streaks(S, top=4):
    logs = team_logs(S)
    playing = {}
    for g, r in S.rows.items():
        hk, ak = (r.home, r.away) if S.sport == "nfl" else (r.home_id, r.away_id)
        if S.sport == "cfb" and pd.isna(r.spread_line):
            continue
        line = r.spread_line
        playing[hk] = (r.away, f"vs {r.away}", -line if pd.notna(line) else None, g)
        playing[ak] = (r.home, f"@ {r.home}", line if pd.notna(line) else None, g)
    cats = {"win": [], "loss": [], "ats": [], "ou": []}
    for k, (opp, where, line, game) in playing.items():
        lg = logs.get(k)
        if not lg:
            continue
        su = streak([g[0] for g in lg["g"]])
        ats = streak([g[1] for g in lg["g"]])
        ou = streak([g[2] for g in lg["g"]])
        ats10 = [g[1] for g in lg["g"] if g[1]][-10:]
        base = {"team": lg["name"], "key": k, "next": where, "line": line, "game": game,
                "ats10": f"{ats10.count('W')}-{ats10.count('L')}" + (f"-{ats10.count('P')}" if ats10.count("P") else "")}
        if su[0] == "W":
            cats["win"].append(dict(base, n=su[1], tag=f"W{su[1]}"))
        if su[0] == "L":
            cats["loss"].append(dict(base, n=su[1], tag=f"L{su[1]}"))
        if ats[1]:
            cats["ats"].append(dict(base, n=ats[1], tag=("Covered " if ats[0] == "W" else "Failed ") + f"{ats[1]}"))
        if ou[1]:
            cats["ou"].append(dict(base, n=ou[1], tag=("Over " if ou[0] == "O" else "Under ") + f"{ou[1]}"))
    return {c: sorted(v, key=lambda x: -x["n"])[:top] for c, v in cats.items()}


# ---------------------------------------------------------------- QB watch
def qb_value(epa_sum, db):
    return (epa_sum + QB_PRIOR * QB_REPL) / (db + QB_PRIOR)


def nfl_qb_watch(S):
    qg = pd.read_csv(os.path.join(BET, "data", "qb_games.csv"))
    qg["team"] = qg["team"].replace({"OAK": "LV", "SD": "LAC", "STL": "LA", "LAR": "LA"})
    recent = qg[qg.season >= S.season - 1]
    out = []
    for game, r in S.rows.items():
        info = S.slate.get((r.away, r.home))
        if not info:
            continue
        summ = get(ESPN.format("nfl", "summary"), {"event": info["event"]})
        for tinj in summ.get("injuries", []):
            team = NFL_ABBR.get(tinj["team"]["abbreviation"], tinj["team"]["abbreviation"])
            for i in tinj.get("injuries", []):
                if i["athlete"].get("position", {}).get("abbreviation") != "QB":
                    continue
                status = i.get("status", "")
                if status not in ("Out", "Doubtful", "Questionable", "Injured Reserve"):
                    continue
                name = i["athlete"].get("displayName", "")
                tq = recent[recent.team == team]
                last_games = tq.game_id.drop_duplicates().tail(6)
                usage = tq[tq.game_id.isin(last_games)].groupby("name")["dropbacks"].sum().sort_values(ascending=False)
                if usage.empty or short_name(name) != usage.index[0]:
                    continue  # only the team's actual starter matters
                starter_rows = qg[(qg.name == usage.index[0]) & (qg.team == team) & (qg.season >= S.season - 1)]
                v_start = qb_value(starter_rows.qb_epa.sum(), starter_rows.dropbacks.sum())
                backup = usage.index[1] if len(usage) > 1 else None
                if backup:
                    br = qg[(qg.name == backup) & (qg.season >= S.season - 2)]
                    v_back = qb_value(br.qb_epa.sum(), br.dropbacks.sum())
                else:
                    v_back = QB_REPL
                impact = max(0.0, (v_start - v_back) * QB_DB)
                home = team == r.home
                moved = (-r.line_move if home else r.line_move) if pd.notna(r.line_move) else 0.0  # pts moved against team
                opp = r.away if home else r.home
                opp_line = (r.spread_line if not home else -r.spread_line) if pd.notna(r.spread_line) else None
                opp_str = f"{opp} {-opp_line:+g}" if opp_line is not None else opp
                gap = impact - max(moved, 0.0)
                if status in ("Out", "Injured Reserve", "Doubtful") and gap >= 1.5:
                    verdict, cls = f"BET AGAINST · {opp_str}", "fade"
                    why = (f"We rate the drop-off at <b>~{impact:.1f} pts</b>; the line has moved only ~{max(moved, 0):.1f} "
                           f"against {team} since last week.")
                elif status in ("Out", "Injured Reserve", "Doubtful"):
                    verdict, cls = f"AVOID {team}", "avoid"
                    why = (f"Drop-off ~{impact:.1f} pts and the market has already moved ~{max(moved, 0):.1f}: priced in. "
                           f"No edge either way.")
                else:
                    verdict, cls = f"AVOID {team} until inactives", "watch"
                    why = (f"If he sits, the drop-off is ~{impact:.1f} pts. Wait for Sunday's inactives; if he's out and "
                           f"the line hasn't moved, bet against.")
                out.append({"team": team, "qb": name, "status": status, "detail": (i.get("details") or {}).get("type", ""),
                            "backup": (backup or "replacement-level backup"), "game": game, "verdict": verdict, "cls": cls,
                            "why": why, "logo": logo_img(info["home" if home else "away"]["logo"], f"nfl_{team}", 28)})
    # projected starter different from who has been playing (backup already named)
    for game, r in S.rows.items():
        for team, qb in ((r.home, r.home_qb), (r.away, r.away_qb)):
            if not qb or any(x["team"] == team for x in out):
                continue
            tq = recent[recent.team == team]
            usage = tq[tq.game_id.isin(tq.game_id.drop_duplicates().tail(4))].groupby("name")["dropbacks"].sum()
            if usage.empty or short_name(qb) == usage.idxmax() or usage.max() < 60:
                continue
            info = S.slate.get((r.away, r.home))
            out.append({"team": team, "qb": qb, "status": "New starter", "detail": f"replacing {usage.idxmax()}",
                        "backup": None, "game": game, "verdict": f"AVOID {team}", "cls": "watch",
                        "why": f"{qb} is listed to start after {usage.idxmax()} took most snaps recently. Confirm before betting.",
                        "logo": logo_img(info["home" if team == r.home else "away"]["logo"], f"nfl_{team}", 28) if info else ""})
    return out


def cfb_qb_watch(S, ours, max_items=6):
    path = os.path.join(BET, "data", "cfb", "qb_games_2026.csv")
    if not os.path.exists(path):
        return []
    q = pd.read_csv(path)
    out = []
    for game, r in S.rows.items():
        if pd.isna(r.spread_line):
            continue
        info = S.slate.get(int(r.game_id))
        for side, tid, team in (("home", r.home_id, r.home), ("away", r.away_id, r.away)):
            t = q[q.pos_team_id == tid]
            if t.empty or t.week.nunique() < 2:
                continue
            last_wk = t.week.max()
            last = t[t.week == last_wk].sort_values("att", ascending=False)
            before = t[t.week < last_wk].groupby("passer_player_name")["att"].sum().sort_values(ascending=False)
            primary, last_top = before.index[0], last.iloc[0]["passer_player_name"]
            prim_last = last[last.passer_player_name == primary]["att"].sum()
            if last_top == primary or before.iloc[0] < 25 or prim_last >= 10:
                continue
            def rate(nm):
                x = t[t.passer_player_name == nm]
                return x.epa.sum() / max(x.att.sum(), 1)
            line = r.spread_line if side == "away" else -r.spread_line
            opp = r.home if side == "away" else r.away
            mine = ours.get(game)
            if abs(r.spread_line) > 24 and not mine:
                continue  # lopsided games nobody should be betting sides in
            lean = (f" If the backup starts and the line hasn't moved, lean {opp} {-line:+g}." if abs(r.spread_line) <= 24
                    else "")
            if mine:
                lean += f" <b>Affects our play: {E(mine)}</b>. Backups can still produce garbage-time points; confirm the starter."
            out.append({"team": team, "qb": primary, "status": "QB change", "rank": (0 if mine else 1, abs(r.spread_line)),
                        "detail": f"{last_top} took over in week {int(last_wk)} ({int(last.iloc[0]['att'])} att; {primary}: {int(prim_last)})",
                        "backup": last_top, "game": game, "cls": "watch",
                        "verdict": f"AVOID {team} until confirmed",
                        "why": (f"Possible injury or benching. EPA per pass this season: {E(primary)} {rate(primary):+.2f}, "
                                f"{E(last_top)} {rate(last_top):+.2f}.{lean}"),
                        "logo": logo_img((info or {}).get(side, {}).get("logo"), f"cfb_{tid}", 28)})
    return sorted(out, key=lambda x: x["rank"])[:max_items]


# ---------------------------------------------------------------- build page
SYSTEM_COPY = {
    "Blowout over": ("Blowout Overs",
                     "When the spread is over 30, bet the Over. Books price the favorite right but underrate the underdog: "
                     "backups on both sides and garbage-time drives add points the market doesn't expect. The bigger the "
                     "spread, the better overs have done (14–21 pts −7% ROI · 30–40 +6% · 40+ +10%). The only trend that "
                     "passed our luck test across 1,192 strategies."),
    "Wind under": ("Wind Unders",
                   "Outdoor games with a 12–20 mph kickoff forecast. Wind cuts into passing and kicking, and totals "
                   "historically don't drop enough. Cooled off in 2025 and the history uses actual (not forecast) wind, "
                   "so half stakes."),
    "Close road team": ("Close Road Team",
                        "Road team in a daytime game with a spread of 3 or less. Home field is worth less than these short "
                        "lines assume. Take the spread <b>or</b> the moneyline for each game, not both; the moneyline pays more "
                        "when the road team is the underdog."),
    "Buy-low underdog": ("Buy-Low Underdog",
                         "Take the underdog when the road team has been missing the spread lately (smoothed cover margin "
                         "−4 or worse). The market overcorrects on teams that keep failing to cover. Half stakes (t = 1.4)."),
    "Rested home team": ("Rested Home Team",
                         "Home team with 3+ more days of rest when the line has moved 3+ points toward them. Profitable in "
                         "11 of 14 seasons, but a small sample. College moneylines can't be backtested (no historical prices in "
                         "free data), so there's no college moneyline system."),
}


def side_reason(S, sy, g):
    r = S.rows.get(g["game"])
    if sy["name"] == "Buy-low underdog" and r is not None:
        return (f"{E(r.away)} has missed the spread by about <b>{-r.a_ats:.0f} pts</b> a game lately (smoothed), "
                f"the kind of slump the market overreacts to. The underdog here gets that inflated number.")
    if sy["name"] == "Rested home team" and r is not None:
        return f"{E(r.home)} has {r.rest_diff:.0f} more days of rest and the line has moved {r.line_move:.1f} pts their way."
    return system_reason(S, sy, g)


def gather(sport):
    S = Sport(sport)
    card = S.card
    best, leans, watch = [], [], []
    for p in card["week"]["picks"]:
        if not S.upcoming(p["game"]):
            continue
        if p["tier"] == "BET":
            best.append({"game": p["game"], "pick": p["bet"], "odds": p["odds"], "u": units(p["stake%"]),
                         "edge": f"+{p['ev%']}% edge", "why": model_reason(S, p), "rank": -p["ev%"]})
        elif p["tier"] == "lean":
            b = S.board.get(p["game"], {})
            leans.append({"game": p["game"], "pick": p["bet"], "odds": p["odds"],
                          "why": f"Model edge +{p['ev%']}%, wins ~{p['win%']:.0f}%. "
                                 + (f"Fair total {b.get('fair_total')}." if p["market"] == "total"
                                    else f"Fair line {b.get('fair_spread')}.")})
    best.sort(key=lambda x: x["rank"])
    systems = card.get("systems", [])
    paired = {sy["pair"]: sy for sy in systems if sy.get("pair")}
    totals, sides = [], []
    for sy in systems:
        if sy.get("pair"):
            continue
        games = [g for g in sy["games"] if S.upcoming(g["game"])]
        if sy["group"] == "totals":
            plays = []
            for g in games:
                if g["tier"] == "SKIP":
                    need = g["skip"].split("need ")[-1].rstrip(")")
                    watch.append({"game": g["game"], "pick": g["bet"], "odds": g["odds"],
                                  "why": f"{SYSTEM_COPY.get(sy['name'], (sy['name'],))[0]} play, price too steep. Bet it at {need}."})
                else:
                    plays.append(dict(g, u=units(g["stake%"]), why=system_reason(S, sy, g)))
            totals.append((sy, plays))
        else:
            ml = paired.get(sy["name"])
            ml_games = {g["game"]: g for g in (ml["games"] if ml else []) if S.upcoming(g["game"])}
            rows = []
            for g in games:
                rows.append({"game": g["game"], "spread": g, "ml": ml_games.pop(g["game"], None),
                             "why": side_reason(S, sy, g)})
            for gm, g in ml_games.items():
                rows.append({"game": gm, "spread": None, "ml": g, "why": side_reason(S, sy, g)})
            sides.append((sy, ml, rows))
    ours = {x["game"]: x["pick"] for x in best}
    for sy, plays in totals:
        ours.update({x["game"]: x["bet"] for x in plays})
    qb = nfl_qb_watch(S) if sport == "nfl" else cfb_qb_watch(S, ours)
    odd_path = os.path.join(HERE, f"oddball_{sport}.json")
    odd = json.load(open(odd_path)) if os.path.exists(odd_path) else None
    return S, best, totals, sides, leans, watch, qb, streaks(S), odd


def record_line(sy):
    return (f"<b>{sy['record']}</b> since 2011 ({sy['roi%']:+}% ROI) · <b>{sy['recent_record']}</b> in 2025–26 "
            f"({sy['recent_roi%']:+}%, {sy['recent_units']:+}u)")


def cell_play(g):
    if g is None:
        return "<span class='meta'>—</span>"
    if g["tier"] == "SKIP":
        need = g["skip"].split("need ")[-1].rstrip(")")
        return (f"<span class='skip'>{E(g['bet'])} {fmt_odds(g['odds'])}</span>"
                f"<div class='meta'>skip · need {E(need.replace(' or better', ''))}</div>")
    return (f"<span class='nw'><b>{E(g['bet'])}</b> <span class='n'>{fmt_odds(g['odds'])}</span></span>"
            f"<div class='meta'>{units(g['stake%']):g}u</div>")


CSS = """
@font-face { font-family: 'Inter'; src: url('assets/Inter.ttf'); font-weight: 100 900; }
@page { size: Letter; margin: 0.42in 0.45in 0.5in; }
* { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
:root { --ink:#0e1320; --ink2:#2b3345; --mute:#6a7385; --line:#e4e7ed; --soft:#f5f7fa;
        --accent:%(accent)s; --green:#0b7a4b; --greenbg:#e9f7f0; --amber:#9a6b00; --amberbg:#fdf5de;
        --red:#b42318; --redbg:#fdecea; --blue:#1d4ed8; }
body { margin:0; font-family:'Inter', system-ui, sans-serif; color:var(--ink); font-size:9.2pt; line-height:1.42;
       font-feature-settings:'tnum' 1, 'cv11' 1; }
.hero { background:var(--accent); color:#fff; border-radius:14px; padding:18px 22px 16px; display:flex;
        justify-content:space-between; align-items:flex-end; margin-bottom:16px; }
.eyebrow { font-size:8pt; letter-spacing:.14em; text-transform:uppercase; opacity:.75; font-weight:600; }
.hero h1 { margin:4px 0 0; font-size:25pt; letter-spacing:-.02em; font-weight:750; line-height:1.05; }
.hero .sub { opacity:.8; font-size:8.6pt; margin-top:5px; }
.kpis { display:flex; gap:8px; }
.kpi { background:rgba(255,255,255,.12); border-radius:10px; padding:7px 11px; min-width:72px; text-align:right; }
.kpi b { display:block; font-size:14pt; font-weight:700; letter-spacing:-.01em; }
.kpi span { font-size:7pt; opacity:.8; text-transform:uppercase; letter-spacing:.08em; }
h2 { font-size:8.2pt; letter-spacing:.14em; text-transform:uppercase; color:var(--mute); font-weight:650;
     margin:18px 0 8px; display:flex; align-items:center; gap:10px; }
h2::after { content:''; flex:1; height:1px; background:var(--line); }
h2, .note { break-after: avoid; page-break-after: avoid; }
td.lgc { white-space:nowrap; width:60px; }
.note { color:var(--mute); font-size:8pt; margin:-2px 0 8px; }
.bet { border:1px solid var(--line); border-radius:12px; padding:10px 13px 11px; margin-bottom:8px; break-inside:avoid;
       display:grid; grid-template-columns: 64px 1fr auto; column-gap:12px; }
.bet .lg { display:flex; align-items:center; gap:2px; padding-top:3px; }
.logo { object-fit:contain; display:inline-block; vertical-align:middle; }
.nologo { display:inline-block; border-radius:50%%; background:var(--soft); vertical-align:middle; }
.at { color:var(--mute); font-size:7pt; margin:0 1px; }
.pick { font-size:13.5pt; font-weight:700; letter-spacing:-.01em; }
.pick .odds { color:var(--mute); font-weight:500; font-size:11pt; margin-left:6px; }
.meta { color:var(--mute); font-size:7.9pt; margin-top:1px; }
.why { grid-column: 2 / 4; margin-top:6px; color:var(--ink2); }
.right { text-align:right; }
.u { display:inline-block; background:var(--ink); color:#fff; border-radius:999px; padding:2px 9px; font-weight:650; font-size:8.6pt; }
.tag { display:block; margin-top:5px; font-size:7.3pt; font-weight:650; letter-spacing:.06em; text-transform:uppercase; color:var(--green); }
.tag.sys { color:var(--blue); }
table { width:100%%; border-collapse:collapse; }
th { font-size:7pt; letter-spacing:.1em; text-transform:uppercase; color:var(--mute); font-weight:650; text-align:left;
     padding:5px 6px; border-bottom:1px solid var(--line); }
td { padding:6px 6px; border-bottom:1px solid var(--line); vertical-align:top; }
tr { break-inside:avoid; }
td.b { font-weight:650; white-space:nowrap; }
td.n { white-space:nowrap; color:var(--ink2); }
.panel { border:1px solid var(--line); border-radius:12px; padding:10px 13px; break-inside:avoid; margin-bottom:8px; }
.panel.green { background:var(--greenbg); border-color:#cfeadc; }
.panel.blue { background:#eef3fd; border-color:#d9e3f8; }
.rec { margin-top:6px; font-size:8.2pt; color:var(--ink2); }
.skip { color:var(--mute); text-decoration:line-through; white-space:nowrap; }
.nw { white-space:nowrap; }
.keep { break-inside: avoid; }
thead, tr:first-child th { break-after: avoid; }
.panel h3 { margin:0 0 3px; font-size:11pt; letter-spacing:-.01em; }
.qb { display:grid; grid-template-columns: 34px 1fr auto; column-gap:11px; align-items:start; }
.qb .name { font-weight:700; font-size:10.5pt; }
.pill { display:inline-block; border-radius:999px; padding:2px 9px; font-size:7.6pt; font-weight:700; letter-spacing:.03em; white-space:nowrap; }
.pill.fade { background:var(--redbg); color:var(--red); }
.pill.avoid { background:var(--soft); color:var(--ink2); }
.pill.watch { background:var(--amberbg); color:var(--amber); }
.pill.status { background:var(--redbg); color:var(--red); margin-left:6px; }
.grid2 { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
.mini { border:1px solid var(--line); border-radius:12px; padding:8px 11px 4px; break-inside:avoid; }
.mini h4 { margin:0 0 3px; font-size:7.6pt; letter-spacing:.12em; text-transform:uppercase; color:var(--mute); font-weight:650; }
.mini td { padding:4px 3px; font-size:8.2pt; }
.mini tr:last-child td { border-bottom:0; }
.sk { font-weight:700; white-space:nowrap; }
.sk.hot { color:var(--green); } .sk.cold { color:var(--red); } .sk.neu { color:var(--blue); }
.odd { background:linear-gradient(135deg, #f4f7fc, #eef2f9); border:1px solid #dfe6f2; border-radius:14px; padding:14px 16px;
       break-inside:avoid; }
.odd .t { font-size:13pt; font-weight:750; letter-spacing:-.01em; }
.odd .fact { margin-top:9px; padding:9px 12px; background:#fff; border-radius:10px; border-left:3px solid var(--accent); }
.odd .fact b.k { display:block; font-size:7pt; letter-spacing:.12em; text-transform:uppercase; color:var(--mute); margin-bottom:2px; }
.foot { color:var(--mute); font-size:7.2pt; margin-top:14px; border-top:1px solid var(--line); padding-top:8px; }
.empty { color:var(--mute); font-style:italic; }
"""


FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/inter/Inter%5Bopsz%2Cwght%5D.ttf"


def ensure_font():
    path = os.path.join(ASSETS, "Inter.ttf")
    if not os.path.exists(path):
        os.makedirs(ASSETS, exist_ok=True)
        r = requests.get(FONT_URL, timeout=60)
        r.raise_for_status()
        with open(path, "wb") as f:
            f.write(r.content)


def render(sport):
    ensure_font()
    S, best, totals, sides, leans, watch, qb, st, odd = gather(sport)
    systems = S.card.get("systems", [])
    label = "NFL" if sport == "nfl" else "College Football"
    accent = "#0b1f3a" if sport == "nfl" else "#123b2c"
    dates = sorted(d for d in (S.teams(g)[2] for g in S.rows) if d)
    rng = ""
    if dates:
        d0 = datetime.fromisoformat(dates[0].replace("Z", "+00:00")).astimezone(ET)
        d1 = datetime.fromisoformat(dates[-1].replace("Z", "+00:00")).astimezone(ET)
        rng = d0.strftime("%b %-d") + ("" if d0.date() == d1.date() else "–" + d1.strftime("%-d" if d0.month == d1.month else "%b %-d")) + d1.strftime(", %Y")
    side_rows = [r for _sy, _ml, rows in sides for r in rows
                 if (r["spread"] and r["spread"]["tier"] == "SYSTEM") or (r["ml"] and r["ml"]["tier"] == "SYSTEM")]
    n_plays = len(best) + sum(len(p) for _s, p in totals) + len(side_rows)
    tot_u = (sum(b["u"] for b in best) + sum(t["u"] for _s, p in totals for t in p)
             + sum(units((r["spread"] if r["spread"] and r["spread"]["tier"] == "SYSTEM" else r["ml"])["stake%"]) for r in side_rows))
    main_sys = max((x for x in systems if not x.get("pair")), key=lambda s: s["recent_roi%"]) if systems else None
    h = [f"<style>{CSS % {'accent': accent}}</style>",
         "<div class='hero'><div>",
         f"<div class='eyebrow'>{label} · Week {S.week} · {rng}</div>",
         "<h1>Betting Card</h1>",
         "<div class='sub'>Prices: DraftKings · 1 unit = 1% of bankroll</div></div><div class='kpis'>",
         f"<div class='kpi'><b>{n_plays}</b><span>Plays</span></div>",
         f"<div class='kpi'><b>{tot_u:g}u</b><span>Risked</span></div>"]
    if main_sys:
        h.append(f"<div class='kpi'><b>{main_sys['recent_roi%']:+.1f}%</b><span>{E(main_sys['name'])} 25–26</span></div>")
    h.append("</div></div>")

    # best bets (model)
    h.append("<h2>Best Bets</h2>")
    h.append("<div class='note'>Model plays: at least a 3% edge at the listed DraftKings price.</div>")
    for b in best:
        h.append(f"<div class='bet'><div class='lg'>{S.logos(b['game'])}</div>"
                 f"<div><div class='pick'>{E(b['pick'])}<span class='odds'>{fmt_odds(b['odds'])}</span></div>"
                 f"<div class='meta'>{E(b['game'])} · {S.when(b['game'])}</div></div>"
                 f"<div class='right'><span class='u'>{b['u']:g}u</span><span class='tag'>{E(b['edge'])}</span></div>"
                 f"<div class='why'>{b['why']}</div></div>")
    if not best:
        h.append("<p class='empty'>No model plays clear the 3% bar this week. The system sections below are the card.</p>")

    # totals systems (Blowout Overs / Wind Unders)
    for sy, plays in totals:
        title, copy = SYSTEM_COPY.get(sy["name"], (sy["name"], E(sy["why"])))
        h.append(f"<h2>{E(title)}</h2>")
        h.append("<div class='keep'>" if len(plays) <= 5 else "<div>")
        h.append(f"<div class='panel green'><h3>{E(title)} · {len(plays)} play{'s' if len(plays) != 1 else ''}"
                 f"{' · ' + format(sum(p['u'] for p in plays), 'g') + 'u' if plays else ''}</h3>"
                 f"<div>{copy}</div><div class='rec'>{record_line(sy)}</div></div>")
        if plays:
            h.append("<table><tr><th style='width:60px'></th><th>Play</th><th>Price</th><th>Game</th><th>Why this one</th></tr>")
            for t in plays:
                h.append(f"<tr><td class='lgc'>{S.logos(t['game'], 18)}</td><td class='b'>{E(t['bet'])}"
                         f"<div class='meta'>{t['u']:g}u</div></td><td class='n'>{fmt_odds(t['odds'])}</td>"
                         f"<td class='n'>{E(t['game'])}<div class='meta'>{S.when(t['game'])}</div></td><td>{t['why']}</td></tr>")
            h.append("</table>")
        else:
            h.append("<p class='empty'>No qualifying games at a bettable price this week.</p>")
        h.append("</div>")

    # spread & moneyline systems
    h.append("<h2>Spread &amp; Moneyline Systems</h2>")
    h.append("<div class='note'>Situational systems on sides. Weaker evidence than the totals systems above, so every play "
             "is a half unit, and only at the listed price or better.</div>")
    for sy, ml, rows in sides:
        title, copy = SYSTEM_COPY.get(sy["name"], (sy["name"], E(sy["why"])))
        live = [r for r in rows if (r["spread"] and r["spread"]["tier"] == "SYSTEM") or (r["ml"] and r["ml"]["tier"] == "SYSTEM")]
        rec = f"Spread: {record_line(sy)}" + (f"<br>Moneyline: {record_line(ml)}" if ml else "")
        h.append("<div class='keep'>" if len(rows) <= 8 else "<div>")
        h.append(f"<div class='panel blue'><h3>{E(title)} · {len(live)} play{'s' if len(live) != 1 else ''}</h3>"
                 f"<div>{copy}</div><div class='rec'>{rec}</div></div>")
        if rows:
            head = "<th style='width:112px'>Spread</th>" + ("<th style='width:112px'>or Moneyline</th>" if ml else "")
            h.append(f"<table><tr><th style='width:60px'></th><th>Game</th>{head}<th>Why</th></tr>")
            for r in rows:
                mlc = f"<td>{cell_play(r['ml'])}</td>" if ml else ""
                h.append(f"<tr><td class='lgc'>{S.logos(r['game'], 18)}</td><td class='n'>{E(r['game'])}"
                         f"<div class='meta'>{S.when(r['game'])}</div></td><td>{cell_play(r['spread'])}</td>{mlc}"
                         f"<td>{r['why']}</td></tr>")
            h.append("</table>")
        else:
            h.append("<p class='empty'>No qualifying games this week.</p>")
        h.append("</div>")

    # leans
    h.append("<h2>Leans &amp; Price Watch</h2>")
    rows = leans + watch
    if rows:
        h.append("<table><tr><th style='width:60px'></th><th>Lean</th><th>Price</th><th>Game</th><th>Why</th></tr>")
        for l in rows:
            h.append(f"<tr><td class='lgc'>{S.logos(l['game'], 18)}</td><td class='b'>{E(l['pick'])}</td><td class='n'>{fmt_odds(l['odds'])}</td>"
                     f"<td class='n'>{E(l['game'])}</td><td>{E(l['why'])}</td></tr>")
        h.append("</table>")
    else:
        h.append("<p class='empty'>No leans this week.</p>")

    # QB watch
    h.append("<h2>QB Watch</h2>")
    h.append("<div class='note'>" + ("Starting QBs on the injury report or already replaced. <b>Avoid</b>: don't bet on this team. "
             "<b>Bet against</b>: the line hasn't caught up to the drop-off." if sport == "nfl" else
             "Teams whose passer changed last game (from play-by-play; college injury reports aren't public). "
             "Confirm who's starting before betting either side.") + "</div>")
    if qb:
        for x in qb:
            h.append(f"<div class='panel qb'><div>{x['logo']}</div><div><span class='name'>{E(x['qb'])}</span>"
                     f"<span class='pill status'>{E(x['status'])}</span>"
                     f"<div class='meta'>{E(x['team'])} · {E(x['game'])} · {E(x['detail'])}"
                     + (f" · next up: {E(x['backup'])}" if x.get("backup") and x["status"] not in ("QB change", "New starter") else "") + "</div>"
                     f"<div style='margin-top:4px;color:var(--ink2)'>{x['why']}</div></div>"
                     f"<div><span class='pill {x['cls']}'>{E(x['verdict'])}</span></div></div>")
    else:
        h.append("<p class='empty'>No starting-QB issues on this week's slate.</p>")

    # streaks
    h.append("<h2>Streaks &amp; Trends</h2>")
    h.append("<div class='note'>Active streaks among this week's teams, counting back into last season. Context only: our "
             "15-season test found hot and cold ATS runs don't predict the next game.</div>")
    titles = {"win": ("Winning streaks", "hot"), "loss": ("Losing streaks", "cold"),
              "ats": ("Against the spread", "neu"), "ou": ("Over / Under", "neu")}
    h.append("<div class='grid2'>")
    for c, (title, cls) in titles.items():
        h.append(f"<div class='mini'><h4>{title}</h4><table>")
        for x in st[c]:
            ln = f" ({x['line']:+g})" if x["line"] is not None and c in ("win", "loss", "ats") else ""
            k = "hot" if x["tag"].startswith(("W", "Covered")) else "cold" if x["tag"].startswith(("L", "Failed")) else "neu"
            h.append(f"<tr><td class='sk {k}' style='width:70px'>{E(x['tag'])}</td><td><b>{E(str(x['team']))}</b>"
                     f"<div class='meta'>ATS last 10: {x['ats10']}</div></td><td class='n right'>{E(x['next'])}{ln}</td></tr>")
        if not st[c]:
            h.append("<tr><td class='empty'>None</td></tr>")
        h.append("</table></div>")
    h.append("</div>")

    # oddball
    if odd:
        h.append("<h2>Oddball Matchup of the Week</h2>")
        h.append(f"<div class='odd'><div style='display:flex;gap:10px;align-items:center'>{S.logos(odd['game'], 30)}"
                 f"<div><div class='t'>{E(odd['title'])}</div><div class='meta'>{E(odd['sub'])}</div></div></div>"
                 f"<div style='margin-top:8px'>{E(odd['body'])}</div>"
                 f"<div class='fact'><b class='k'>Did you know</b>{E(odd['fact'])}</div>"
                 f"<div class='meta' style='margin-top:8px'>{E(odd['model'])}</div></div>")

    h.append("<div class='foot'>Lines move. Check the current DraftKings price before betting; if the number moves against "
             "you, the edge can disappear. Past results don't guarantee future results. For entertainment only · 21+ · "
             f"bet responsibly (1-800-GAMBLER). Generated {datetime.now(ET):%b %-d, %Y %-I:%M %p ET}.</div>")

    page = "<!doctype html><html><head><meta charset='utf-8'></head><body>" + "".join(h) + "</body></html>"
    html_path = os.path.join(HERE, f"{sport}_week{S.week}.html")
    pdf_path = os.path.join(HERE, f"{sport}_week{S.week}.pdf")
    with open(html_path, "w") as f:
        f.write(page)
    subprocess.run([CHROME, "--headless=new", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf_path}", "file://" + html_path], check=True, capture_output=True, timeout=120)
    os.remove(html_path)
    print(pdf_path)
    return pdf_path


if __name__ == "__main__":
    for sp in (sys.argv[1:] or ["nfl", "cfb"]):
        render(sp)
