# Fantasy Trade Scale

A fantasy football trade analyzer. Open `index.html` in a browser.

Each player is valued as **points over replacement for the rest of the season**:

```
value = max(0, PPG − replacement PPG) × weeks played   (+ 17 × age multiplier in Dynasty)
```

- Scoring (PPR / Half / Standard), league size, 1QB vs Superflex, and weeks left all move the replacement level.
- Injury status cuts the weeks a player actually plays.
- "Stud premium" weights each side's players 100% / 90% / 80%… so 2-for-1 trades don't win on volume alone.
- Projections are example estimates; edit any player's PPG in the trade card.
