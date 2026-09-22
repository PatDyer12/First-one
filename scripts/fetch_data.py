#!/usr/bin/env python3
"""Pull live fantasy data into data/fts-data.js for the Trade Scale page.

Sources
  Sleeper   api.sleeper.app     player info, injuries, weekly stats, weekly projections
  FantasyCalc api.fantasycalc.com  trade-market values (redraft/dynasty x 1QB/superflex)
  Sleeper CDN sleepercdn.com     headshots (shrunk and inlined as data URIs)

Usage: python3 scripts/fetch_data.py
"""
import base64
import io
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import features as F  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "fts-data.js")
LEAGUES = os.path.join(ROOT, "data", "leagues.json")
POSITIONS = ["QB", "RB", "WR", "TE"]
S = requests.Session()


def get(url, **kw):
    for attempt in range(4):
        try:
            r = S.get(url, timeout=60, **kw)
            r.raise_for_status()
            return r
        except requests.RequestException:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def pos_query():
    return "&".join("position[]=" + p for p in POSITIONS)


def weekly(kind, season, week):
    q = pos_query() + ("&position[]=DEF" if kind == "stats" else "")
    url = "https://api.sleeper.app/%s/nfl/%s/%d?season_type=regular&%s" % (kind, season, week, q)
    return week, get(url).json()


def norm(name):
    return "".join(c for c in name.lower().replace("jr.", "").replace("sr.", "").replace(" iii", "").replace(" ii", "") if c.isalnum())


def headshot(pid):
    try:
        from PIL import Image
        raw = get("https://sleepercdn.com/content/nfl/players/thumb/%s.jpg" % pid).content
        im = Image.open(io.BytesIO(raw)).convert("RGB")
        im.thumbnail((112, 112))
        buf = io.BytesIO()
        im.save(buf, "WEBP", quality=72)
        return pid, "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return pid, None


def main():
    leagues = json.load(open(LEAGUES))
    state = get("https://api.sleeper.app/v1/state/nfl").json()
    season, week = state["season"], int(state["week"])
    print("season", season, "week", week, file=sys.stderr)

    print("players…", file=sys.stderr)
    allp = get("https://api.sleeper.app/v1/players/nfl").json()

    with ThreadPoolExecutor(8) as ex:
        stats = dict(ex.map(lambda w: weekly("stats", season, w), range(1, week)))
        projs = dict(ex.map(lambda w: weekly("projections", season, w), range(week, 19)))

    fc = {}
    for key, dyn, qbs in [("r1", "false", 1), ("r2", "false", 2), ("d1", "true", 1), ("d2", "true", 2)]:
        url = "https://api.fantasycalc.com/values/current?isDynasty=%s&numQbs=%d&numTeams=12&ppr=1" % (dyn, qbs)
        fc[key] = get(url).json()

    players = {}

    def ensure(pid):
        if pid in players:
            return players[pid]
        sp = allp.get(pid)
        if not sp or sp.get("position") not in POSITIONS:
            return None
        players[pid] = {
            "id": pid,
            "n": sp.get("full_name") or (sp.get("first_name", "") + " " + sp.get("last_name", "")),
            "pos": sp["position"],
            "team": sp.get("team") or "FA",
            "age": sp.get("age"),
            "exp": sp.get("years_exp"),
            "inj": sp.get("injury_status"),
            "injNote": sp.get("injury_body_part"),
            "wk": [None] * (week - 1),
            "wkRec": [0.0] * (week - 1),
            "proj": [0.0] * (19 - week),
            "projRec": [0.0] * (19 - week),
            "opp": None,
            "use": {"snp": 0, "tmSnp": 0, "tgt": 0, "att": 0, "g": 0},
            "fc": {},
        }
        return players[pid]

    picks = {}
    for key, rows in fc.items():
        for row in rows:
            p = row["player"]
            val = [row["value"], row["overallRank"], row["positionRank"], row.get("trend30Day") or 0]
            if p["position"] == "PICK":
                picks.setdefault(p["name"], {})[key] = val
                continue
            sid = p.get("sleeperId")
            if not sid:
                continue
            rec = ensure(str(sid))
            if rec:
                rec["fc"][key] = val
                if p.get("maybeAge"):
                    rec["age"] = p["maybeAge"]

    for w, rows in projs.items():
        for row in rows:
            pts = row["stats"].get("pts_ppr") or 0
            if pts < 1.5 and row["player_id"] not in players:
                continue
            rec = ensure(row["player_id"])
            if not rec:
                continue
            rec["proj"][w - week] = round(pts, 1)
            rec["projRec"][w - week] = round(row["stats"].get("rec") or 0, 1)
            if w == week:
                rec["opp"] = row.get("opponent")
    # Team results from defense rows: a defense's points allowed = its opponent's score
    teams = {}
    for w, rows in stats.items():
        allowed = {}
        for row in rows:
            if row["player"].get("position") == "DEF" and row["stats"].get("gp"):
                allowed[row["team"]] = (row["stats"].get("pts_allow") or 0, row.get("opponent"))
        for team, (pa, opp) in allowed.items():
            if opp not in allowed:
                continue
            pf = allowed[opp][0]
            t = teams.setdefault(team, {"w": 0, "l": 0, "t": 0, "pf": 0, "pa": 0, "g": 0, "plays": 0})
            t["pf"] += pf; t["pa"] += pa; t["g"] += 1
            t["w" if pf > pa else "l" if pf < pa else "t"] += 1
        for row in rows:
            st = row["stats"]
            if row["player"].get("position") in POSITIONS and row.get("team") in teams:
                teams[row["team"]]["plays"] += (st.get("pass_att") or 0) + (st.get("rush_att") or 0)

    for w, rows in stats.items():
        for row in rows:
            rec = players.get(row["player_id"])
            st = row["stats"]
            # count a game only if he actually got on the field
            if rec and st.get("gms_active") and ((st.get("off_snp") or 0) > 0 or (st.get("pts_ppr") or 0) != 0):
                u = rec["use"]
                u["snp"] += st.get("off_snp") or 0
                u["tmSnp"] += st.get("tm_off_snp") or 0
                u["tgt"] += st.get("rec_tgt") or 0
                u["att"] += st.get("rush_att") or 0
                u["g"] += 1
                rec["wk"][w - 1] = round(row["stats"].get("pts_ppr") or 0, 1)
                rec["wkRec"][w - 1] = row["stats"].get("rec") or 0

    # Resolve each league's roster names to Sleeper ids
    index = {}
    for pid, sp in allp.items():
        if sp.get("position") in POSITIONS and sp.get("full_name"):
            index.setdefault(norm(sp["full_name"]), []).append(pid)
    for lg in leagues:
        ids, missing = [], []
        for name in lg["roster"]:
            cands = index.get(norm(name), [])
            cands.sort(key=lambda c: (c not in players, allp[c].get("team") is None, allp[c].get("search_rank") or 9e9))
            if cands:
                ensure(cands[0])
                ids.append(cands[0])
            else:
                missing.append(name)
        lg["ids"] = ids
        lg["missing"] = missing
        if missing:
            print("unmatched in %s: %s" % (lg["name"], missing), file=sys.stderr)

    # Keep players who matter: on a roster, valued by the market, or projected for real points
    rostered = {i for lg in leagues for i in lg["ids"]}
    keep = {}
    for pid, p in players.items():
        if pid in rostered or p["fc"] or sum(p["proj"]) >= 12:
            keep[pid] = p

    top = sorted(keep.values(), key=lambda p: -max([v[0] for v in p["fc"].values()] or [0]))[:260]
    want = {p["id"] for p in top} | rostered
    print("headshots…", len(want), file=sys.stderr)
    with ThreadPoolExecutor(12) as ex:
        for pid, uri in ex.map(headshot, want):
            if uri:
                keep[pid]["img"] = uri

    # Apply the frozen model (data/model.json, fit by train_model.py) to this season's first weeks
    model = json.load(open(os.path.join(ROOT, "data", "model.json")))
    early_rows = [F.stats_week(season, w, cache=False) for w in range(1, week)]
    live = F.build_rows(int(season), allp, early_rows, F.preseason(season), 0)

    def predict(m, f):
        x = F.vectorize(f, m["features"], m["means"])
        z = [(xi - mu) / sd for xi, mu, sd in zip(x, m["mu"], m["sd"])]
        contrib = [round(zi * b, 2) for zi, b in zip(z, m["coef"])]
        return m["intercept"] + sum(contrib), contrib, x

    for pid, p in keep.items():
        f = live.get(pid)
        pm = model["positions"].get(p["pos"])
        if not f or not pm:
            continue
        out = {"g": f["g"], "pre": round(f["pre"], 2), "adp": f["adp"]}
        for tgt in ("ros", "next"):
            m = pm.get(tgt)
            if not m:
                continue
            full, contrib, x = predict(m, f)
            base, _, _ = predict(m["baseline"], f)
            out[tgt] = [round(full, 2), round(base, 2)]
            if tgt == "ros":
                out["x"] = [round(v, 3) for v in x]
                out["c"] = contrib
        p["m"] = out

    data = {
        "season": int(season),
        "week": week,
        "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "sources": ["FantasyCalc (trade values)", "Sleeper: Sportradar stats, RotoWire projections, injuries"],
        "teams": teams,
        "model": {"trainedOn": model["trainedOn"], "labels": model["labels"], "elasticity": model["elasticity"],
                  "positions": {pos: {t: {k: v for k, v in m.items() if k in ("features", "importance", "cvR2", "chosen", "tested", "n")} | {"baseR2": m["baseline"]["cvR2"]}
                                      for t, m in e.items()} for pos, e in model["positions"].items()}},
        "players": list(keep.values()),
        "picks": picks,
        "leagues": leagues,
        "overrides": json.load(open(os.path.join(ROOT, "data", "overrides.json"))) if os.path.exists(os.path.join(ROOT, "data", "overrides.json")) else {},
    }
    with open(OUT, "w") as f:
        f.write("window.FTS_DATA=")
        json.dump(data, f, separators=(",", ":"))
        f.write(";\n")
    print("wrote %s: %d players, %.1f KB" % (OUT, len(keep), os.path.getsize(OUT) / 1024), file=sys.stderr)


if __name__ == "__main__":
    main()
