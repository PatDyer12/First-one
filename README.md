# Sweat Board

A live betting board for a monitor: today's record and P/L in units, open bets with live ESPN scores, and FanDuel vs DraftKings splits. Bets sync between your phone and the monitor through your own Firebase project.

This branch is served by GitHub Pages. It is separate from the fantasy trade app on the main branch.

## Files

- `index.html`: the whole app
- `config.js`: your Firebase web config (safe to publish; Firestore rules decide who can read or write)

## Data

- Bets live in Firestore under `bets/`, the unit size in `config/settings`.
- Scores and lines come straight from ESPN's public scoreboard, refreshed every 30 seconds while the page is open.
- Settings → Download backup / Import backup moves the full bet history in and out.
