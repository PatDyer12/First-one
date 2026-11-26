#!/usr/bin/env python3
"""Thanksgiving trends, tested: every idea is written down with its reason first, then graded against closing lines.

Thanksgiving = the regular-season Thursday games between Nov 22 and Nov 28 (Detroit and Dallas host every year, a
night game since 2006). That's only ~75 games since 1999, so the bar is the strict one: t >= 2, profitable in both
halves of the sample (1999-2012 and 2013+), and not losing since 2016. A wider check runs the same ideas on every
non-opener Thursday game since 2011 (~250 games). Spreads and totals graded at -110, moneylines at the closing price.

Writes betting/data/thanksgiving.json. Usage: python3 betting/thanksgiving.py
"""
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
FIX = {"OAK": "LV", "SD": "LAC", "STL": "LA", "LAR": "LA"}
WIN = 100 / 110


def long_table(g):
    """One row per team per game, with the line from that team's side and its previous game's location."""
    g = g[(g["game_type"] == "REG")].copy()
    g["date"] = pd.to_datetime(g["gameday"])
    g["thanksgiving"] = (g["weekday"] == "Thursday") & (g["date"].dt.month == 11) & g["date"].dt.day.between(22, 28)
    g["night"] = g["gametime"].fillna("00:00") >= "19:00"
    rows = []
    for home in (True, False):
        s = 1 if home else -1
        rows.append(pd.DataFrame({
            "game_id": g["game_id"], "season": g["season"], "week": g["week"], "date": g["date"],
            "weekday": g["weekday"], "thanksgiving": g["thanksgiving"], "night": g["night"],
            "team": (g["home_team"] if home else g["away_team"]).replace(FIX),
            "opp": (g["away_team"] if home else g["home_team"]).replace(FIX), "home": home,
            "margin": s * g["result"], "line": s * g["spread_line"], "total": g["total"], "total_line": g["total_line"],
            "ml": g["home_moneyline"] if home else g["away_moneyline"],
            "rest": g["home_rest"] if home else g["away_rest"]}))
    L = pd.concat(rows, ignore_index=True).sort_values(["team", "date"])
    L["prev_home"] = L.groupby("team")["home"].shift(1)
    return L


def unit_side(x):
    """Units for a spread bet on this row's team (line > 0 means this team is favored by that much)."""
    c = x["margin"] - x["line"]
    return np.where(c > 0, WIN, np.where(c < 0, -1.0, 0.0))


def unit_total(x, side):
    c = (x["total"] - x["total_line"]) * (1 if side == "over" else -1)
    return np.where(c > 0, WIN, np.where(c < 0, -1.0, 0.0))


def unit_ml(x):
    won = x["margin"] > 0
    pay = np.where(x["ml"] > 0, x["ml"] / 100, 100 / x["ml"].abs())
    return np.where(won, pay, np.where(x["margin"] < 0, -1.0, 0.0))


def grade(b, split=2013, recent=2016, strict=True):
    b = b[pd.notna(b["u"])]
    if b.empty:
        return None
    u = b["u"].to_numpy(dtype=float)
    w, l, p = int((u > 0).sum()), int((u < 0).sum()), int((u == 0).sum())
    sd = u.std(ddof=1) if len(u) > 1 else np.nan
    t = float(u.mean() / (sd / np.sqrt(len(u)))) if sd and sd > 0 else 0.0
    first, second = b[b["season"] < split]["u"].mean(), b[b["season"] >= split]["u"].mean()
    rec = b[b["season"] >= recent]["u"]
    by = b.groupby("season")["u"].sum()
    out = {"bets": len(u), "record": f"{w}-{l}" + (f"-{p}" if p else ""), "win%": round(100 * w / max(w + l, 1), 1),
           "roi%": round(100 * u.mean(), 1), "t": round(t, 2), "seasons_up": f"{int((by > 0).sum())}/{len(by)}",
           "first%": round(100 * first, 1) if pd.notna(first) else None,
           "second%": round(100 * second, 1) if pd.notna(second) else None,
           "recent": f"{int((rec > 0).sum())}-{int((rec < 0).sum())}", "recent_roi%": round(100 * rec.mean(), 1) if len(rec) else None}
    ok = (t >= 2.0 and (first or 0) > 0 and (second or 0) > 0 and (out["recent_roi%"] or 0) >= 0)
    out["verdict"] = "Passed" if ok else ("Weak" if t >= 1.5 and (second or 0) > 0 else "Noise")
    return out


def ideas():
    """(name, scope, market, side, filter on the long table, why) -- written before testing."""
    fav = lambda x: x["line"] > 0          # noqa: E731
    return [
        ("Thanksgiving host", "tg", "spread", lambda x: x["home"],
         "Detroit and Dallas host every year and keep their routine; the road team flies in on three days' rest."),
        ("Lions on Thanksgiving", "tg", "spread", lambda x: x["team"] == "DET",
         "The most famous holiday trend on TV: does Detroit's annual home game mean anything against the spread?"),
        ("Cowboys on Thanksgiving", "tg", "spread", lambda x: x["team"] == "DAL",
         "America's Team draws the heaviest public money of the year on Thanksgiving: the line should be inflated."),
        ("Thanksgiving underdog", "tg", "spread", lambda x: x["line"] < 0,
         "Casual holiday bettors pile onto favorites, so the dog should get an extra half point or more."),
        ("Thanksgiving home underdog", "tg", "spread", lambda x: x["home"] & (x["line"] < 0),
         "Home dog with the routine edge plus the public fading it."),
        ("Thanksgiving big dog (+7 or more)", "tg", "spread", lambda x: x["line"] <= -7,
         "Lopsided holiday lines get bet up further by the public; a week's worth of fatigue keeps games closer."),
        ("Thanksgiving: fade the road team off a road game", "tg", "spread", lambda x: x["home"] & (x["opp_prev_home"] == False),  # noqa: E712
         "A road team coming off a road game travels twice in five days."),
        ("Thanksgiving under", "tg", "under", None,
         "Short week: tired legs and simpler game plans. Holiday bettors also love overs."),
        ("Thanksgiving night-game under", "tg", "under", lambda x: x["night"],
         "The third game of the day: the road team has the longest travel day and the latest finish."),
        ("Thanksgiving underdog moneyline", "tg", "ml", lambda x: x["line"] < 0,
         "If public money inflates favorites, the dog's moneyline should pay more than it should."),
        ("Thursday home team (all Thursdays)", "thu", "spread", lambda x: x["home"],
         "Every Thursday is a short week; only the road team has to travel on it."),
        ("Thursday home underdog (all Thursdays)", "thu", "spread", lambda x: x["home"] & (x["line"] < 0),
         "Short-week home dog: rest-and-travel edge plus points."),
        ("Thursday under (all Thursdays)", "thu", "under", None,
         "Short-week offenses run simpler plans."),
        ("Thursday favorite of 7+ (all Thursdays): fade", "thu", "spread", lambda x: x["line"] <= -7,
         "Big Thursday favorites have no time to install anything; the dog keeps it closer."),
    ]


def run(g):
    L = long_table(g)
    L = L.merge(L[["game_id", "team", "prev_home"]].rename(columns={"team": "opp", "prev_home": "opp_prev_home"}),
                on=["game_id", "opp"], how="left")
    done = L[L["margin"].notna() & L["line"].notna()]
    tg = done[done["thanksgiving"] & (done["season"] >= 1999)]
    thu = done[(done["weekday"] == "Thursday") & (done["season"] >= 2011) & (done["week"] > 1)]
    today = L[L["margin"].isna() & L["thanksgiving"] & (L["season"] == L["season"].max())]
    res = []
    for name, scope, market, f, why in ideas():
        hit = today[f(today)] if f is not None else today
        if market in ("under", "over"):
            points = [f"{r.opp if r.home else r.team} @ {r.team if r.home else r.opp} {market} {r.total_line:g}"
                      for r in hit[hit["home"]].itertuples()]
        elif market == "ml":
            points = [f"{r.team} ML" for r in hit.itertuples()]
        else:
            points = [f"{r.team} {-r.line:+g}" for r in hit.drop_duplicates("game_id").itertuples()]
        base = tg if scope == "tg" else thu
        x = base[f(base)] if f is not None else base
        if market in ("under", "over"):
            x = x.drop_duplicates("game_id").copy()
            x = x[x["total_line"].notna()]
            x["u"] = unit_total(x, market)
        elif market == "ml":
            x = x[x["ml"].notna()].copy()
            x["u"] = unit_ml(x)
        else:
            x = x.drop_duplicates("game_id").copy()
            x["u"] = unit_side(x)
        s = grade(x, split=2013 if scope == "tg" else 2018, recent=2016 if scope == "tg" else 2021)
        if s:
            res.append({"idea": name, "scope": "Thanksgiving 1999-2025" if scope == "tg" else "All Thursdays 2011-2025",
                        "market": market, "why": why, "today": points, **s})
    return L, pd.DataFrame(res)


def team_history(L, teams):
    """Each of today's teams on Thanksgiving and on all Thursdays (ATS, SU), for the trends panel."""
    done = L[L["margin"].notna() & L["line"].notna()]
    out = {}
    for t in teams:
        x = done[(done["team"] == t) & done["thanksgiving"]]
        th = done[(done["team"] == t) & (done["weekday"] == "Thursday") & (done["season"] >= 2011) & (done["week"] > 1)]
        ats = lambda d: f"{int(((d['margin'] - d['line']) > 0).sum())}-{int(((d['margin'] - d['line']) < 0).sum())}"  # noqa: E731
        su = lambda d: f"{int((d['margin'] > 0).sum())}-{int((d['margin'] < 0).sum())}"  # noqa: E731
        last = x.sort_values("date").tail(5)
        out[t] = {"tg_games": len(x), "tg_su": su(x), "tg_ats": ats(x),
                  "tg_last5": [f"{int(r.season)}: {'W' if r.margin > 0 else 'L' if r.margin < 0 else 'T'} vs {r.opp} "
                               f"({'covered' if r.margin - r.line > 0 else 'no cover' if r.margin - r.line < 0 else 'push'})"
                               for r in last.itertuples()],
                  "thu_su": su(th), "thu_ats": ats(th), "thu_games": len(th)}
    return out


def main():
    g = pd.read_csv(os.path.join(DATA, "games.csv"), low_memory=False)
    L, res = run(g)
    up = g[(g["game_type"] == "REG") & g["result"].isna()].copy()
    up["date"] = pd.to_datetime(up["gameday"])
    today = up[(up["weekday"] == "Thursday") & (up["date"].dt.month == 11) & up["date"].dt.day.between(22, 28)]
    teams = sorted(set(today["home_team"].replace(FIX)) | set(today["away_team"].replace(FIX)))
    pd.set_option("display.width", 250)
    print(res[["idea", "scope", "bets", "record", "win%", "roi%", "t", "seasons_up", "first%", "second%", "recent",
               "recent_roi%", "verdict"]].to_string(index=False))
    out = {"ideas": res.to_dict("records"), "games": today[["game_id", "away_team", "home_team", "gametime", "spread_line",
                                                            "total_line"]].to_dict("records"),
           "teams": team_history(L, teams)}
    with open(os.path.join(DATA, "thanksgiving.json"), "w") as f:
        json.dump(out, f, indent=1, default=str)
    print("\ntoday:", [f"{r['away_team']} @ {r['home_team']}" for r in out["games"]])
    for t, v in out["teams"].items():
        print(f"  {t}: Thanksgiving {v['tg_su']} SU, {v['tg_ats']} ATS ({v['tg_games']} games) · all Thursdays since 2011: "
              f"{v['thu_su']} SU, {v['thu_ats']} ATS")


if __name__ == "__main__":
    main()
