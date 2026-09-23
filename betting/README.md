# NFL Betting Model (spread · total · moneyline)

Open `betting/card.html` for this week's card, fair lines for every game, and the backtest.

## Weekly routine
```
pip install pandas numpy scikit-learn pyarrow requests
python3 betting/fetch.py        # pull latest scores, lines, play-by-play (~20s)
python3 betting/model.py        # retrain, backtest, price this week -> betting/card.html
```
Got better numbers at your own book? Put them in `betting/my_lines.csv` and re-run with `--week`.

## What's inside, and where each idea comes from
| Piece | Borrowed from | Why |
|---|---|---|
| Elo with margin-of-victory multiplier, 1/3 offseason regression | FiveThirtyEight NFL Elo | Solid all-around power rating |
| Opponent-adjusted EPA/play, success rate, pass/rush split, garbage time removed | nflfastR / Ben Baldwin, Football Outsiders DVOA | EPA predicts future scoring better than points do |
| QB rating from EPA per dropback, shrunk toward replacement; "QB change" feature | 538 QB adjustment, PFF | The QB is the biggest single driver of a line |
| Ridge regression + gradient-boosted trees, averaged | Standard Kaggle/sports-analytics ensembling | Linear stability plus non-linear effects |
| Walk-forward training (each season predicted only from earlier seasons) | Standard quant backtesting | No leakage, so the backtest is honest |
| Blend with the closing line, weight learned out-of-sample | "Wisdom of the market" (Pinnacle, Levitt) | The market is the best predictor; the model only nudges it |
| Score distribution from real results near each line (key numbers 3/7/10, pushes) | Sharp "key number" pricing, Stern (1991) | 3 points across a key number ≠ 3 points anywhere else |
| No-vig prices via the power method, probabilities anchored to the market | Sharp devig methods (power/Shin) | Fixes the long-shot bias (big dogs win less than priced) |
| Bet only at ≥3% expected value; quarter-Kelly stakes, max 3% | Kelly (1956), pro bankroll practice | Bet size grows with edge without risking ruin |

## Read this before betting real money
- Every backtest bet is placed at the **closing line**, the sharpest number of the week. On spreads and totals the model comes out around break-even to slightly positive at a 2–3% edge threshold, which is inside the noise. Moneylines don't beat the close. That's normal: almost no public model beats closing lines.
- In the blend, the model's weight is only ~10–15%. The market already prices in almost everything in public data.
- Your real edge comes from **line shopping** (plug your book's numbers into `my_lines.csv`) and **betting early** before lines move toward the model. Track your closing-line value (did the line move your way after you bet?). That's the best sign you have an edge.
- Not included yet: injuries beyond QB, weather forecasts for upcoming games (uses the listed number), opening lines.
