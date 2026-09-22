# Fantasy Trade Scale

A fantasy football trade analyzer tuned to two real leagues (Yahoo redraft, Sleeper dynasty superflex).
Open `index.html` in a browser.

## Data

`python3 scripts/fetch_data.py` pulls fresh data into `data/fts-data.js`:

- **Sleeper API**: player info, injuries, weekly stats, week-by-week rest-of-season projections
- **FantasyCalc**: trade-market values (redraft/dynasty × 1QB/superflex), including dynasty picks
- **Sleeper CDN**: headshots, shrunk and inlined

Rosters and league settings live in `data/leagues.json`. Edit that file after a trade or waiver pickup and re-run the script.

## Model

- **Projection model**: Σ over remaining weeks of max(0, projected pts − replacement level), where replacement is computed by filling every team's lineup (flex + superflex included) from the projection pool. Dynasty adds `max(0, pts/gm − repl) × 17 × age multiplier`.
- **Market**: FantasyCalc value for the league's format.
- **Blend**: model rescaled to market units, then mixed (50/50 redraft, 30/70 dynasty by default, adjustable).
- **Consolidation**: each side's assets weighted 100%, 88%, 76%… (floor 40%).
- **Lineup impact**: optimal lineup before vs. after, in projected starter points per week.
- **Trade Finder**: every 1-for-1 and 2-for-1 package from your roster vs. the top ~220 targets. Keeps fair deals that improve your lineup.
