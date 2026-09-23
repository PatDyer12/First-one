# NFL Betting Model (spread · total · moneyline)

Open `betting/card.html` for this week's card, fair lines for every game, and the backtest.

## Weekly routine
```
pip install pandas numpy scikit-learn pyarrow requests
python3 betting/fetch.py        # scores, lines, play-by-play, injuries, weather forecast, FanDuel/DraftKings odds
python3 betting/model.py        # retrain, backtest, price this week -> betting/card.html + bet_log.csv
```
Run it again **Saturday** (final injury reports, fresher weather) and right before you bet (fresh odds).

**FanDuel + DraftKings odds (optional, recommended):** get a free key at the-odds-api.com (500 requests/month;
one run uses 1) and put it in `betting/odds_api_key.txt` (ignored by git) or the `ODDS_API_KEY` env variable.
Then only FanDuel and DraftKings prices are bettable, and the model tells you which of the two has the better
number for each bet. Without a key it prices the consensus line. `betting/my_lines.csv` still overrides anything by hand.

**The card** shows a spread, moneyline and total pick for every game: BET (3%+ edge), lean (1–3%), or
watch (the model's side, no edge at today's price). Each has a **"bet it at"** price: the FD/DK odds (and the
odds at half a point better, if you buy or find an alt line) where it becomes a BET. With no odds key, check
those targets in your FanDuel/DraftKings app yourself.

**Bet tracker:** every BET is logged to `betting/bet_log.csv` at the line when it was first recommended,
then graded against the result and the **closing line** (CLV). Set `placed` to `no` for bets you skip.

## How a prediction is made
1. **Ratings** (`features.py`), built only from games before kickoff: Elo, opponent-adjusted EPA/success
   (pass and rush, garbage time removed), QB EPA per dropback, points, **market power ratings** (what past
   closing lines say about each team), and how far this week's line has moved off them.
2. **Model** (`model.py`): ridge regression + gradient-boosted trees predict the **gap between the result and the
   market line**, not the score itself (that tested clearly better).
3. **Blend with the market**, with the trust level learned from recent seasons (half-life 1.5 seasons).
4. **Probabilities** from the real NFL score distribution (key numbers 3/7/10, pushes), anchored to the no-vig
   market price (power method, which fixes long-shot bias).
5. **Bet** at ≥3% expected value, quarter-Kelly stakes capped at 3% of bankroll.

## What was tested and cut (`tune.py`, 2014–2018 only)
Injuries (snap-weighted starters out), travel distance and time zones, byes and short weeks, ATS form, and heat
all made predictions *worse* once the market line was known. The market already prices them. The code still
computes them in `features.py`, so they're easy to re-test.

## The big finding: 2018 changed everything
Every version of the model beat closing lines through 2018 (edge correlation +0.05 to +0.17 every season)
and fell to about zero from 2019 on. That's when legal sports betting spread after the Supreme Court's *Murphy v. NCAA*
decision (May 2018). Far more money is now bet into these lines, and they're much sharper.

## Read this before betting real money
- 2019–2026 holdout vs **closing** lines: no reliable edge on spreads or moneylines. Totals were slightly positive
  (+3% ROI at a 3% edge threshold on 160 bets), which is still within luck. The recency-weighted blend now
  trusts the spread model at only ~10%, so it will rarely bet sides.
- Two edges are still real and don't depend on predictions: **line shopping** (FanDuel vs DraftKings) and **betting early**,
  before lines move. Judge yourself by CLV in the tracker, not by win-loss. Win-loss needs 500+ bets to mean anything.
- Totals backtests use actual game-day wind, not the forecast bettors had, so they're a bit optimistic.
