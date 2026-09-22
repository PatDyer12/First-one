# Fantasy Trade Scale

A fantasy football trade analyzer tuned to three real leagues (Yahoo redraft, Sleeper dynasty superflex, Sleeper 32-team keeper with half PPR + TE premium).
Open `index.html` in a browser.

## Data

`python3 scripts/fetch_data.py` pulls fresh data into `data/fts-data.js`:

- **Sleeper API**: player info, injuries, weekly stats, week-by-week rest-of-season projections
- **FantasyCalc**: trade-market values (redraft/dynasty × 1QB/superflex), including dynasty picks
- **Sleeper CDN**: headshots, shrunk and inlined

Rosters and league settings live in `data/leagues.json`. Edit that file after a trade or waiver pickup and re-run the script.

## Model

Public trade market first, then this season, then your roster.

- **Market (primary)**: FantasyCalc value for the league's format (keeper = 50/50 redraft + dynasty).
- **2026 performance**: actual pts/gm vs. projection, shrunk for small samples, capped ±10%. Usage (snap share vs. positional norm) capped ±4%.
- **Team environment**: offense quality (projected output + points scored), QB situation (healthy starter's projection, QB1-out flag), winning (record), teammate health. Capped ±10%.
- Adjustments count 100% in redraft, 75% keeper, 50% dynasty; a slider scales them 0–150%.
- **Consolidation**: each side weighted 100%, 88%, 76%… (floor 40%).
- **Roster fit**: best-lineup change (starter pts/wk × weeks left, priced at the market's value per point) × fit weight, capped at ±25% of the deal.
- **Every effect**: the trade screen breaks out market Δ, adjustments Δ, consolidation, fit, per-player factors, lineup slot changes, position-room grades, roster spots, next-4-weeks vs. rest-of-season, age, and picks.

Sources: FantasyCalc; Sleeper API (Sportradar stats incl. snaps/targets/carries/team scores, RotoWire projections, injuries).
