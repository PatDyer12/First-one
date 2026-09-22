"""Shared feature building for the trade-value model.

Everything here uses only what is known after the first two weeks of a season,
so the same code builds historical training rows and this season's live rows.
"""
import hashlib
import json
import os
import time
from datetime import date

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".cache")
POSITIONS = ["QB", "RB", "WR", "TE"]
EARLY_WEEKS = [1, 2]
S = requests.Session()


def get_json(url, cache=True):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, hashlib.sha1(url.encode()).hexdigest() + ".json")
    if cache and os.path.exists(path):
        return json.load(open(path))
    for attempt in range(4):
        try:
            r = S.get(url, timeout=90)
            r.raise_for_status()
            data = r.json()
            break
        except requests.RequestException:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
    if cache:
        json.dump(data, open(path, "w"))
    return data


def stats_week(season, week, cache=True):
    q = "&".join("position[]=" + p for p in POSITIONS + ["DEF"])
    return get_json("https://api.sleeper.app/stats/nfl/%s/%d?season_type=regular&%s" % (season, week, q), cache)


def proj_week(season, week, cache=True):
    q = "&".join("position[]=" + p for p in POSITIONS)
    return get_json("https://api.sleeper.app/projections/nfl/%s/%d?season_type=regular&%s" % (season, week, q), cache)


def age_at(birth, season):
    if not birth:
        return None
    try:
        y, m, d = [int(x) for x in birth.split("-")]
    except ValueError:
        return None
    ref = date(season, 9, 1)
    return (ref - date(y, m, d)).days / 365.25


def played(st):
    return (st.get("off_snp") or 0) > 0 or (st.get("pts_ppr") or 0) != 0


def team_early(rows_by_week):
    """Points for, games, wins, plays and pass attempts per team over the early window."""
    teams = {}
    for rows in rows_by_week:
        allowed = {}
        for row in rows:
            if row["player"].get("position") == "DEF" and row["stats"].get("gp"):
                allowed[row["team"]] = (row["stats"].get("pts_allow") or 0, row.get("opponent"))
        for t, (pa, opp) in allowed.items():
            if opp not in allowed:
                continue
            pf = allowed[opp][0]
            d = teams.setdefault(t, {"pf": 0, "g": 0, "w": 0.0, "plays": 0, "passAtt": 0})
            d["pf"] += pf
            d["g"] += 1
            d["w"] += 1 if pf > pa else 0.5 if pf == pa else 0
        for row in rows:
            st = row["stats"]
            if row["player"].get("position") in POSITIONS and row.get("team") in teams:
                teams[row["team"]]["plays"] += (st.get("pass_att") or 0) + (st.get("rush_att") or 0)
                teams[row["team"]]["passAtt"] += st.get("pass_att") or 0
    return teams


def player_early(rows_by_week):
    out = {}
    for rows in rows_by_week:
        for row in rows:
            pos = row["player"].get("position")
            st = row["stats"]
            if pos not in POSITIONS or not st.get("gms_active") or not played(st):
                continue
            d = out.setdefault(row["player_id"], {"pos": pos, "g": 0, "pts": 0, "snp": 0, "tmSnp": 0, "tgt": 0, "ratt": 0,
                                                   "touch": 0, "yds": 0, "rz": 0, "patt": 0, "pyd": 0, "team": None})
            d["g"] += 1
            d["pts"] += st.get("pts_ppr") or 0
            d["snp"] += st.get("off_snp") or 0
            d["tmSnp"] += st.get("tm_off_snp") or 0
            d["tgt"] += st.get("rec_tgt") or 0
            d["ratt"] += st.get("rush_att") or 0
            d["touch"] += (st.get("rec") or 0) + (st.get("rush_att") or 0)
            d["yds"] += (st.get("rec_yd") or 0) + (st.get("rush_yd") or 0)
            d["rz"] += (st.get("rec_rz_tgt") or 0) + (st.get("rush_rz_att") or 0)
            d["patt"] += st.get("pass_att") or 0
            d["pyd"] += st.get("pass_yd") or 0
            d["team"] = row.get("team") or d["team"]
    return out


def preseason(season, cache=True):
    """Week-1 projection (the preseason expectation) and ADP, per player."""
    out = {}
    for row in proj_week(season, 1, cache):
        st = row["stats"]
        out[row["player_id"]] = {"pre": st.get("pts_ppr") or 0, "adp": st.get("adp_dd_ppr") or 0,
                                 "pos": row["player"].get("position"), "team": row.get("team")}
    return out


FEATURES = {
    "QB": ["pre", "adp", "act", "snap", "passAtt", "rushAtt", "ypa", "teamPts", "winPct", "age", "age2", "exp"],
    "RB": ["pre", "adp", "act", "snap", "oppShare", "tgtShare", "rz", "ypt", "teamPts", "winPct", "qbPre", "age", "age2", "exp"],
    "WR": ["pre", "adp", "act", "snap", "oppShare", "tgtShare", "rz", "ypt", "teamPts", "winPct", "qbPre", "age", "age2", "exp"],
    "TE": ["pre", "adp", "act", "snap", "oppShare", "tgtShare", "rz", "ypt", "teamPts", "winPct", "qbPre", "age", "age2", "exp"],
}
LABELS = {
    "pre": "Preseason projection", "adp": "Draft market (ADP)", "act": "Pts/gm so far", "snap": "Snap share",
    "passAtt": "Pass attempts/gm", "rushAtt": "Rush attempts/gm", "ypa": "Yards per attempt", "oppShare": "Share of team plays",
    "tgtShare": "Target share", "rz": "Red-zone chances/gm", "ypt": "Yards per touch", "teamPts": "Team points/gm",
    "winPct": "Team win %", "qbPre": "QB quality", "age": "Age", "age2": "Age curve", "exp": "Years in league",
}


def build_rows(season, allp, early_rows, pre, season_offset):
    """Feature dicts for every player with a preseason projection or early-season snaps."""
    teams = team_early(early_rows)
    early = player_early(early_rows)
    qb_pre = {}
    for pid, e in early.items():
        if e["pos"] == "QB" and e["team"]:
            best = qb_pre.get(e["team"])
            if not best or e["patt"] > best[1]:
                qb_pre[e["team"]] = (pre.get(pid, {}).get("pre", 0), e["patt"])
    rows = {}
    for pid in set(pre) | set(early):
        info = allp.get(pid, {})
        pos = (early.get(pid) or {}).get("pos") or (pre.get(pid) or {}).get("pos") or info.get("position")
        if pos not in POSITIONS:
            continue
        pr = pre.get(pid, {"pre": 0, "adp": 0})
        e = early.get(pid)
        team = (e or {}).get("team") or pr.get("team")
        t = teams.get(team, {})
        age = age_at(info.get("birth_date"), season)
        exp = info.get("years_exp")
        exp = None if exp is None else max(0, exp - season_offset)
        f = {"pos": pos, "team": team, "g": e["g"] if e else 0,
             "pre": pr["pre"], "adp": pr["adp"] if pr["adp"] and pr["adp"] < 999 else 350,
             "age": age, "exp": exp}
        if e and e["g"]:
            g = e["g"]
            f["act"] = e["pts"] / g
            f["snap"] = e["snp"] / e["tmSnp"] if e["tmSnp"] else None
            f["passAtt"] = e["patt"] / g
            f["rushAtt"] = e["ratt"] / g
            f["ypa"] = e["pyd"] / e["patt"] if e["patt"] else None
            f["oppShare"] = (e["tgt"] + e["ratt"]) / t["plays"] if t.get("plays") else None
            f["tgtShare"] = e["tgt"] / t["passAtt"] if t.get("passAtt") else None
            f["rz"] = e["rz"] / g
            f["ypt"] = e["yds"] / e["touch"] if e["touch"] else None
        if t.get("g"):
            f["teamPts"] = t["pf"] / t["g"]
            f["winPct"] = t["w"] / t["g"]
        if team in qb_pre:
            f["qbPre"] = qb_pre[team][0]
        rows[pid] = f
    return rows


def vectorize(f, feats, means):
    """Turn a feature dict into a list, filling gaps with the training mean and deriving age terms."""
    out = []
    for k in feats:
        if k == "adp":
            v = __import__("math").log(max(1.0, f.get("adp") or 350))
        elif k == "age2":
            a = f.get("age")
            v = None if a is None else (a - 27) ** 2
        else:
            v = f.get(k)
        out.append(means[k] if v is None else float(v))
    return out
