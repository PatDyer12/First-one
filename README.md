# Fantasy Trade Scale

A fantasy football trade analyzer tuned to three real leagues (Yahoo redraft, Sleeper dynasty superflex, Sleeper 32-team keeper with half PPR + TE premium).
Open `index.html` in a browser.

## Data

`python3 scripts/fetch_data.py` pulls fresh data into `data/fts-data.js`:

- **Sleeper API**: player info, injuries, weekly stats, week-by-week rest-of-season projections
- **FantasyCalc**: trade-market values (redraft/dynasty × 1QB/superflex), including dynasty picks
- **Sleeper CDN**: headshots, shrunk and inlined

Rosters and league settings live in `data/leagues.json`. Edit that file after a trade or waiver pickup and re-run the script.

## Model (fixed)

One frozen formula, fit on history. Nothing in the app is adjustable.

1. **Anchor**: preseason FantasyCalc value (value − 30-day change) for the league's format. Injured players and players with no games use today's market.
2. **Fitted update**: `scripts/train_model.py` builds every 2022–2025 player-season with what was known after Week 2 (preseason projection, ADP, pts/gm so far, snap share, share of team plays, target share, red-zone chances, yards per touch/attempt, team points, team win %, QB quality, age, age curve, experience) and fits ridge regressions per position that predict rest-of-season and next-season pts/gm. The penalty and factor set are chosen by leave-one-season-out cross-validation; each position keeps whichever set tested best. Weights are saved to `data/model.json`.
3. **Value**: `ratio = model ÷ preseason-only model` (redraft: rest of season; keeper 50/50 with next season; dynasty 35/65), then `value = anchor × ratio^elasticity`, where elasticity is how steeply FantasyCalc prices expected points (fit once, frozen).
4. **Injuries & suspensions**: expected weeks out = the longest of (weeks projected at 0 from now, status minimum: Out/Doubtful/Suspended 1, IR/PUP 4, season-ending injury: ACL/Achilles/Lisfranc = rest of season). Injured players start from the pre-injury market and take `× (1 − share × (1 − available^1.5))`, share = 100% redraft, 50% keeper, 35% dynasty. Out for the season in redraft = 0.
5. **Trade**: consolidation 100/88/76…% (floor 40%); roster fit = lineup gain × fixed weight (25% redraft, 20% keeper, 10% dynasty), capped at ±15% of the deal.

Out-of-sample R² (rest of season): QB 0.33 (vs 0.33 preseason-only), RB 0.54 (0.49), WR 0.63 (0.54), TE 0.57 (0.41).

Re-fit only on purpose: `python3 scripts/train_model.py`. Weekly refresh: `python3 scripts/fetch_data.py` (applies the frozen weights).

Sources: FantasyCalc; Sleeper API (Sportradar stats incl. snaps/targets/carries/team scores, RotoWire projections and ADP, injuries).
