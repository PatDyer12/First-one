#!/usr/bin/env python3
"""Sharp-market edges: FanDuel / DraftKings prices checked against the sharpest market (Pinnacle).

Pinnacle takes the biggest bets with the lowest margins, so its prices, with the margin removed, are the best
public estimate of the true odds. A FanDuel or DraftKings price that pays more than those odds is +EV whichever
way it points (over, under, favorite, underdog), and our own bets get a sharp check: a play that bets into the
sharp side gets cut.

  reference   Pinnacle no-vig; without Pinnacle, the median no-vig of the sharp books (Betfair exchange,
              Matchbook, LowVig, BetOnline); without those, the median of 3+ other books
  half points different lines are converted with how often games land exactly on each number (3, 7, 10;
              41, 44, 47 ...), measured on 2011-2025 games with similar lines
  edge        EV at the FD/DK price >= 2.5% (sides and totals) or 3% (moneylines)

Odds come from The Odds API (10 named books = 3 requests per sport per run).
Writes betting/data/market_<sport>.json. Usage: python3 betting/market.py [nfl|cfb] [--no-fetch]
"""
import json
import os
import sys

import numpy as np
import pandas as pd
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
SPORT_KEY = {"nfl": "americanfootball_nfl", "cfb": "americanfootball_ncaaf"}
OURS = {"fanduel": "FanDuel", "draftkings": "DraftKings"}
SHARP = ["pinnacle", "betfair_ex_eu", "matchbook", "lowvig", "betonlineag"]
MIN_EV = {"spreads": 0.025, "totals": 0.025, "h2h": 0.03}
# up to 10 named books cost one region's requests: ours, the sharp ones, and a few big US books for consensus
BOOKS = "fanduel,draftkings,pinnacle,betfair_ex_eu,matchbook,lowvig,betonlineag,betmgm,williamhill_us,betrivers"
MAX_ML_DOG = 400


def payout(o):
    return o / 100 if o > 0 else 100 / -o


def implied(o):
    return 1 / (1 + payout(o))


def odds_key():
    k = os.environ.get("ODDS_API_KEY")
    path = os.path.join(HERE, "odds_api_key.txt")
    if not k and os.path.exists(path):
        k = open(path).read().strip()
    return k


def fetch(sport):
    key = odds_key()
    if not key:
        raise SystemExit("no Odds API key (ODDS_API_KEY or betting/odds_api_key.txt)")
    r = requests.get(f"https://api.the-odds-api.com/v4/sports/{SPORT_KEY[sport]}/odds",
                     params={"apiKey": key, "bookmakers": BOOKS, "markets": "h2h,spreads,totals", "oddsFormat": "american"},
                     timeout=60)
    r.raise_for_status()
    print(f"{sport}: {len(r.json())} events, {r.headers.get('x-requests-remaining')} Odds API requests left")
    return r.json()


# ------------------------------------------------------------------ how often games land on each number
class Landing:
    """P(home margin = k | spread) and P(total = k | total line), from past games with similar lines."""

    def __init__(self, sport):
        if sport == "nfl":
            g = pd.read_csv(os.path.join(DATA, "games.csv"), low_memory=False)
            g = g[(g["season"].between(2011, 2025)) & g["result"].notna()]
            self.margin, self.spread = g["result"].values, g["spread_line"].values      # home margin, home-fav line
            self.tot, self.tline = g["total"].values, g["total_line"].values
        else:
            g = pd.read_csv(os.path.join(DATA, "cfb", "games.csv"), low_memory=False)
            g = g[(g["season"].between(2011, 2025)) & (g["completed"] == True)]  # noqa: E712
            g = g[g["spread_line"].notna() & g["total_line"].notna()]
            self.margin = (g["home_points"] - g["away_points"]).values
            self.spread = g["spread_line"].values
            self.tot, self.tline = (g["home_points"] + g["away_points"]).values, g["total_line"].values
        self.cache = {}

    def _pmf(self, values, lines, center, width):
        key = (id(values), round(center * 2) / 2)
        if key not in self.cache:
            w = width
            sel = np.abs(lines - center) <= w
            while sel.sum() < 400 and w < 12:
                w += 1
                sel = np.abs(lines - center) <= w
            v = values[sel]
            v = v[~np.isnan(v)].astype(int)
            ks, n = np.unique(v, return_counts=True)
            self.cache[key] = dict(zip(ks.tolist(), (n / max(len(v), 1)).tolist()))
        return self.cache[key]

    def margin_pmf(self, home_line):   # home_line > 0: home favored by that many
        return self._pmf(self.margin, self.spread, home_line, 1.5)

    def total_pmf(self, total_line):
        return self._pmf(self.tot, self.tline, total_line, 2.0)


def above_below(pmf, threshold):
    """P(X > t), P(X < t), P(X == t) for integer outcomes."""
    up = sum(p for k, p in pmf.items() if k > threshold)
    down = sum(p for k, p in pmf.items() if k < threshold)
    return up, down, 1 - up - down


def convert(pmf, ref_line, q_up, target):
    """Reference no-vig chance q_up that X lands above ref_line (pushes excluded) -> P(X > target), P(X < target)."""
    up, down, push = above_below(pmf, ref_line)
    p_up = q_up * (1 - push)                       # P(X > ref_line) as the market sees it
    shift_up, shift_down, _ = above_below(pmf, target)
    # move from ref_line to target using the landing frequencies between the two numbers
    p_up_t = p_up + (shift_up - up)
    p_push_t = pmf.get(int(target), 0.0) if float(target).is_integer() else 0.0
    p_down_t = 1 - p_up_t - p_push_t
    return float(np.clip(p_up_t, 0, 1)), float(np.clip(p_down_t, 0, 1))


# ------------------------------------------------------------------ reference prices
def two_way(market, outcomes):
    """{side: (point, price)} for the two outcomes of one book's market."""
    out = {}
    for o in outcomes:
        out[o["name"]] = (o.get("point"), o["price"])
    return out


def novig(pa, pb):
    a, b = implied(pa), implied(pb)
    return a / (a + b)


def reference(event, mkey, side_name, target, L, sport):
    """Fair chance the given side wins at `target` (and pushes), from Pinnacle / sharp books / consensus."""
    home = event["home_team"]
    quotes = []
    for b in event["bookmakers"]:
        if b["key"] in OURS:
            continue
        m = next((x for x in b["markets"] if x["key"] == mkey), None)
        if not m or len(m["outcomes"]) != 2:
            continue
        o = two_way(mkey, m["outcomes"])
        if mkey == "h2h":
            other = next(k for k in o if k != side_name) if side_name in o else None
            if other is None:
                continue
            quotes.append((b["key"], novig(o[side_name][1], o[other][1]), 0.0))
        elif mkey == "totals":
            if "Over" not in o or "Under" not in o:
                continue
            line = o["Over"][0]
            q_over = novig(o["Over"][1], o["Under"][1])
            pmf = L.total_pmf(line)
            p_over, p_under = convert(pmf, line, q_over, target)
            p = p_over if side_name == "Over" else p_under
            push = 1 - p_over - p_under
            quotes.append((b["key"], p, push))
        else:  # spreads: points are per team; work in home margin
            away = event["away_team"]
            if home not in o or away not in o:
                continue
            home_pt = o[home][0]
            q_home = novig(o[home][1], o[away][1])       # home covers home_pt
            pmf = L.margin_pmf(-home_pt)                   # home favored by -home_pt
            thr_ref = -home_pt                             # home covers when margin > -home_pt
            # target is the point for side_name; express as a home-margin threshold
            thr_t = -target if side_name == home else target
            p_above, p_below = convert(pmf, thr_ref, q_home, thr_t)
            push = 1 - p_above - p_below
            p = p_above if side_name == home else p_below
            quotes.append((b["key"], p, push))
    if not quotes:
        return None
    pin = [q for q in quotes if q[0] == "pinnacle"]
    if pin:
        return pin[0][1], pin[0][2], "Pinnacle"
    sharp = [q for q in quotes if q[0] in SHARP]
    use = sharp if len(sharp) >= 3 else (quotes if len(quotes) >= 6 else [])  # thin exchanges alone aren't enough
    if not use:
        return None
    return float(np.median([q[1] for q in use])), float(np.median([q[2] for q in use])), f"{len(use)}-book consensus"


def scan(sport, events):
    L = Landing(sport)
    rows = []
    for e in events:
        for b in e["bookmakers"]:
            if b["key"] not in OURS:
                continue
            for m in b["markets"]:
                for o in m["outcomes"]:
                    point = o.get("point")
                    ref = reference(e, m["key"], o["name"], point if point is not None else 0.0, L, sport)
                    if ref is None:
                        continue
                    p_win, p_push, src = ref
                    ev = p_win * payout(o["price"]) - (1 - p_win - p_push)
                    rows.append({"away": e["away_team"], "home": e["home_team"], "commence": e["commence_time"],
                                 "book": OURS[b["key"]], "market": m["key"], "side": o["name"], "point": point,
                                 "odds": o["price"], "p_win": round(p_win, 4), "p_push": round(p_push, 4),
                                 "fair_odds": fair_american(p_win, p_push), "ev": round(100 * ev, 2), "ref": src})
    return pd.DataFrame(rows)


def fair_american(p, push):
    q = p / max(1 - push, 1e-9)   # win chance excluding pushes
    if q <= 0 or q >= 1:
        return None
    return int(round(-100 * q / (1 - q))) if q > 0.5 else int(round(100 * (1 - q) / q))


def check(sport, game_teams, market, side_name, point, odds, events=None):
    """Sharp check for one of our bets: EV at our price vs the reference (None when no reference)."""
    events = events if events is not None else json.load(open(os.path.join(DATA, f"market_{sport}_raw.json")))
    L = Landing(sport)
    away, home = game_teams
    e = next((x for x in events if x["away_team"] == away and x["home_team"] == home), None)
    if e is None:
        return None
    ref = reference(e, market, side_name, point if point is not None else 0.0, L, sport)
    if ref is None:
        return None
    p, push, src = ref
    return round(100 * (p * payout(odds) - (1 - p - push)), 2), src


def plain(s):
    """Team names without accents or apostrophes, lowercased: ESPN says San José State and Hawai'i, the Odds API doesn't."""
    import unicodedata
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().replace("'", "").lower()


def same_school(odds_name, school):
    """Odds API 'San Jose State Spartans' is ESPN's 'San José State'."""
    o, s = plain(odds_name), plain(school)
    return o == s or o.startswith(s + " ")


def play_check(sport, p, events, L, name=None):
    """Sharp check for one play from final.py: (EV at our price, fair win %, source) or None."""
    away, home = p["game"].split(" @ ")
    if name:
        away, home = name(away), name(home)
    e = next((x for x in events if x["away_team"] == away and x["home_team"] == home), None)
    if e is None and sport == "cfb":
        e = next((x for x in events if same_school(x["away_team"], away) and same_school(x["home_team"], home)), None)
    if e is None:
        return None
    if p["market"] == "total":
        mkey, side, point = "totals", p["side"].title(), p["line"]
    elif p["market"] == "spread":
        team = e["home_team"] if p["side"] == "home" else e["away_team"]
        mkey, side, point = "spreads", team, (-p["line"] if p["side"] == "home" else p["line"])
    else:
        mkey, side, point = "h2h", (e["home_team"] if p["side"] == "home" else e["away_team"]), 0.0
    ref = reference(e, mkey, side, point, L, sport)
    if ref is None:
        return None
    pw, push, src = ref
    return {"ev": round(100 * (pw * payout(p["odds"]) - (1 - pw - push)), 2), "fair_odds": fair_american(pw, push),
            "win": round(100 * pw / max(1 - push, 1e-9), 1), "ref": src}


def nfl_name():
    sys.path.insert(0, HERE)
    from fetch import NAMES
    full = {v: k for k, v in NAMES.items()}
    return lambda t: full.get(t, t)


def card_checks(sport, events):
    """EV of each bet on our final card at its own price, against the sharp reference."""
    path = os.path.join(DATA, "final_nfl.json" if sport == "nfl" else os.path.join("cfb", "final_cfb.json"))
    if not os.path.exists(path):
        return []
    if sport == "nfl":
        sys.path.insert(0, HERE)
        from fetch import NAMES
        full = {v: k for k, v in NAMES.items()}
        name = lambda t: full.get(t, t)  # noqa: E731
    else:
        name = None
    L = Landing(sport)
    out = []
    for p in json.load(open(path)).get("plays", []):
        away, home = p["game"].split(" @ ")
        if name:
            away, home = name(away), name(home)
        e = next((x for x in events if x["away_team"] == away and x["home_team"] == home), None)
        if e is None and sport == "cfb":  # college names: match on school name inside the Odds API team name
            e = next((x for x in events if same_school(x["away_team"], away) and same_school(x["home_team"], home)), None)
        if e is None:
            continue
        if p["market"] == "total":
            mkey, side, point = "totals", p["side"].title(), p["line"]
        elif p["market"] == "spread":
            team = e["home_team"] if p["side"] == "home" else e["away_team"]
            mkey, side, point = "spreads", team, (-p["line"] if p["side"] == "home" else p["line"])
        else:
            mkey, side, point = "h2h", (e["home_team"] if p["side"] == "home" else e["away_team"]), 0.0
        ref = reference(e, mkey, side, point, L, sport)
        if ref is None:
            continue
        pw, push, src = ref
        out.append({"game": p["game"], "bet": p["bet"], "odds": p["odds"], "book": p["book"], "market": p["market"],
                    "side": p["side"], "ev": round(100 * (pw * payout(p["odds"]) - (1 - pw - push)), 2), "ref": src,
                    "fair_odds": fair_american(pw, push)})
    return out


DERIV = "spreads_h1,totals_h1,team_totals"
DERIV_MIN_EV = 3.0


def derivatives(sport, events):
    """First-half spreads / totals and team totals at FanDuel / DraftKings vs Pinnacle, at the exact same number."""
    key = odds_key()
    base = f"https://api.the-odds-api.com/v4/sports/{SPORT_KEY[sport]}"
    rows, left = [], None
    for e in events:
        if not any(b["key"] == "pinnacle" for b in e["bookmakers"]):
            continue
        r = requests.get(f"{base}/events/{e['id']}/odds", params={"apiKey": key, "bookmakers": "fanduel,draftkings,pinnacle",
                                                                    "markets": DERIV, "oddsFormat": "american"}, timeout=30)
        left = r.headers.get("x-requests-remaining", left)
        if r.status_code != 200:
            continue
        books = {b["key"]: b for b in r.json().get("bookmakers", [])}
        pin = books.get("pinnacle")
        if not pin:
            continue
        for bk in OURS:
            if bk not in books:
                continue
            for m in books[bk]["markets"]:
                pm = next((x for x in pin["markets"] if x["key"] == m["key"]), None)
                if not pm:
                    continue
                for o in m["outcomes"]:
                    desc = o.get("description")
                    same = [x for x in pm["outcomes"] if x.get("description") == desc and x.get("point") is not None
                            and o.get("point") is not None and abs(abs(x["point"]) - abs(o["point"])) < 1e-9]
                    mine = next((x for x in same if x["name"] == o["name"] and x["point"] == o["point"]), None)
                    other = next((x for x in same if x["name"] != o["name"]), None)
                    if not mine or not other:
                        continue
                    q = novig(mine["price"], other["price"])
                    ev = 100 * (q * payout(o["price"]) - (1 - q))
                    rows.append({"away": e["away_team"], "home": e["home_team"], "commence": e["commence_time"],
                                 "market": m["key"], "team": desc, "side": o["name"], "point": o["point"], "odds": o["price"],
                                 "book": OURS[bk], "pin": f"{mine['price']:+d}/{other['price']:+d}",
                                 "fair_odds": fair_american(q, 0.0), "ev": round(ev, 2)})
    print(f"derivative markets: {len(rows)} FD/DK prices matched to Pinnacle ({left} Odds API requests left)")
    d = pd.DataFrame(rows)
    if d.empty:
        return []
    d = d[d["ev"] >= DERIV_MIN_EV].sort_values("ev", ascending=False)
    d = d.drop_duplicates(["away", "home", "market", "team"])
    d["units"] = 0.5
    return d.to_dict("records")


def main():
    sport = next((a for a in sys.argv[1:] if a in SPORT_KEY), "nfl")
    raw_path = os.path.join(DATA, f"market_{sport}_raw.json")
    if "--no-fetch" in sys.argv and os.path.exists(raw_path):
        events = json.load(open(raw_path))
    else:
        events = fetch(sport)
        with open(raw_path, "w") as f:
            json.dump(events, f)
    now = pd.Timestamp.now(tz="UTC")
    days = 4 if sport == "nfl" else 3   # this week's games only: next week's lines are early and thin
    events = [e for e in events if now < pd.Timestamp(e["commence_time"]) <= now + pd.Timedelta(days=days)]
    sc = scan(sport, events)
    if sc.empty:
        print("nothing to scan")
        return
    sc["min_ev"] = sc["market"].map(MIN_EV) * 100
    edges = sc[(sc["ev"] >= sc["min_ev"]) & ~((sc["market"] == "h2h") & (sc["odds"] > MAX_ML_DOG))]
    # one bet per game/market/side: the best EV across the two books
    edges = edges.sort_values("ev", ascending=False).drop_duplicates(["away", "home", "market", "side"])
    # never both sides of one market (can happen across books on different lines): keep the better
    edges = edges.drop_duplicates(["away", "home", "market"])
    edges["units"] = np.where(edges["ev"] >= 5, 1.0, 0.5)
    out = {"sport": sport, "scanned": int(len(sc)), "with_pinnacle": int(sum(1 for e in events if any(b["key"] == "pinnacle" for b in e["bookmakers"]))),
           "events": len(events), "edges": edges.drop(columns=["min_ev"]).to_dict("records")}
    out["checks"] = card_checks(sport, events)
    if "--derivatives" in sys.argv:
        out["derivatives"] = derivatives(sport, events)
        for r in out["derivatives"]:
            lab = {"spreads_h1": "1H", "totals_h1": "1H", "team_totals": f"{r['team']} team total"}[r["market"]]
            print(f"  {r['away']} @ {r['home']}: {lab} {r['side']} {r['point']:+g} {r['odds']:+d} {r['book']}  "
                  f"Pinnacle {r['pin']} (fair {r['fair_odds']})  EV {r['ev']:+.1f}%")
    with open(os.path.join(DATA, f"market_{sport}.json"), "w") as f:
        json.dump(out, f, indent=1, default=str)
    for c in out["checks"]:
        print(f"  sharp check: {c['game']} {c['bet']} {c['odds']:+d} {c['book']}: EV {c['ev']:+.1f}% vs {c['ref']}")
    print(f"{len(sc)} FD/DK prices scanned across {len(events)} games ({out['with_pinnacle']} with Pinnacle); "
          f"{len(edges)} edges:")
    for r in edges.itertuples():
        lab = r.side if r.market == "h2h" else f"{r.side} {r.point:+g}" if r.market == "spreads" else f"{r.side} {r.point:g}"
        print(f"  {r.away} @ {r.home}: {lab} {r.odds:+d} {r.book}  fair {r.fair_odds}  EV {r.ev:+.1f}%  ({r.ref})")


if __name__ == "__main__":
    main()
