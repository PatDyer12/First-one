# NFL + College Football Betting Models (spread · total · moneyline)

Open `betting/card.html` for this week's card, fair lines for every game, and the backtest.

## Weekly routine
```
pip install pandas numpy scikit-learn pyarrow requests
python3 betting/fetch.py        # scores, lines, play-by-play, injuries, weather forecast, FanDuel/DraftKings odds
python3 betting/model.py        # retrain, backtest, price this week -> betting/card.html + bet_log.csv
```
Run it again **Saturday** (final injury reports, fresher weather) and right before you bet (fresh odds).

**FanDuel + DraftKings odds:** DraftKings comes free from ESPN's feed on every run, no setup needed. For FanDuel too,
get a free key at the-odds-api.com (500 requests/month; each fetch uses 1) and put it in `betting/odds_api_key.txt`
(ignored by git) or the `ODDS_API_KEY` env variable. Only FD/DK prices are bettable; the market consensus
line is used only to anchor probabilities. **FanDuel is the default book**: a bet moves to DraftKings only when DK
has a strictly better line or price (`PREFERRED_BOOK` in `model.py`). `betting/my_lines.csv` still overrides anything by hand.

**The card** shows a spread, moneyline and total pick for every game: BET (3%+ edge), lean (1–3%), or
watch (the model's side, no edge at today's price). Each has a **"bet it at"** price: the FD/DK odds (and the
odds at half a point better, if you buy or find an alt line) where it becomes a BET. With no odds key, check
those targets in your FanDuel/DraftKings app yourself.

**Bet tracker:** every BET is logged to `betting/bet_log.csv` at the line when it was first recommended,
then graded against the result and the **closing line** (CLV). Set `placed` to `no` for bets you skip.

## Shareable weekly cards (PDF)
```
python3 betting/share/weekly.py          # -> betting/share/nfl_week<N>.pdf and cfb_week<N>.pdf
```
Run the models first. Each card has these sections:
- **Best Bets**, each with a reason.
- **Leans & Price Watch**: system plays waiting on a better price.
- **QB Watch.** NFL: live ESPN injury report; each starter is marked *avoid* or *bet against*, depending on whether the
  line has already moved as much as we think the drop-off is worth. College: passer changes from play-by-play.
- **Streaks & Trends**: straight-up, against-the-spread and over/under streaks.
- **Oddball Matchup of the Week**: write it each week in `betting/share/oddball_nfl.json` / `oddball_cfb.json`.

## The strategy search: what actually made money (`systems.py`)
`python3 betting/systems.py` tests every market/side crossed with one or two situational filters, plus the model at
several edge thresholds: 2,055 NFL and 1,192 college strategies over 2011–2025. It checks four things:
- **Luck test:** a bootstrap reality check (White 2000) of how good the best of that many strategies would look
  if none had any edge.
- **Walk-forward:** each season, bet whatever had been best in the seasons before it.
- **Persistence:** do 2011–18 winners keep winning in 2019–25?
- **Proven + hot:** strategies profitable long-term that are also best over the last two seasons.

| System (on the cards) | Long-term | 2025–26 | Verdict |
|---|---|---|---|
| **College Blowout over**: Over when spread > 30 | 750-581, +7.5% ROI; overs improve steadily with spread size; passes the luck test | 103-77, **+9.2%** (+16.6 u) | **Real edge**, 1% stakes |
| NFL Close road team, daytime: road team, spread ≤ 3, not primetime | 627-546, +4.4% | 49-39, +6.4% | Weak (t = 1.5), 0.5% stakes, only at -110 or better |
| NFL Wind under: outdoors, 12–20 mph forecast wind | 327-238, +12.4% | 15-17, −10% | Probable but cold, 0.5% stakes |
| Everything else, including the spread/ML models | Top 10% of 2011–18 strategies: +10% ROI → −2 to −4% in 2019–25 | | Luck. Don't bet |

Picking by "proven + hot" worked in college historically (top 3: +2.2% ROI, 8 of 10 seasons up) but not in the
NFL (hot streaks didn't carry over). Each system has a minimum price: the win rates are only a few points above
break-even, so a -120 price can erase the edge. The card marks those games SKIP.

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

## College football version
```
python3 betting/cfb_fetch.py    # schedules, ESPN play-by-play + lines 2010-now, DraftKings/FanDuel for this week
python3 betting/cfb_model.py    # backtest + this week's card -> betting/cfb_card.html (tracker: cfb_bet_log.csv)
```
Same engine as the NFL model: gap-to-line ridge + boosted trees, recency-weighted market blend, key-number
score distributions learned from college results, no-vig anchoring, quarter-Kelly staking.
College ratings (`cfb_features.py`): Elo (FCS and lower divisions start well below FBS), opponent-adjusted EPA,
success rate, pass/rush split with Bill Connelly's garbage-time rule, pace, points, market power ratings
and line movement, rest, conference games, division gaps.

What testing showed:
- College **closing** lines are very efficient, even before 2019. The model's edge correlation vs the close is ~0.
  Holdout 2019–2026: spreads +2% ROI on 243 bets (any edge), totals −0.4% on 798. A zero-edge bettor averages about
  −4.5% at -110, so there's maybe a sliver on totals, but nothing proven.
- Overs have beaten closing college totals lately (+1.3 to +1.4 pts/game in 2023, 2024, 2026). The model has picked
  that up a little.
- The softness people talk about in college is in **opening** lines and small games early in the week. Historical
  opening lines aren't in the free data, so bet early and let the tracker's CLV tell you whether it's working.
- Not included (no free data): starting QBs, injuries, returning production, recruiting/transfer talent, weather.
  Historical lines come without odds, so the backtest assumes -110 and can't grade moneylines.
