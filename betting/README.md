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

## Final card: model + systems + situational angles (`final.py`, `angles.py`)
```
python3 betting/fetch.py && python3 betting/model.py --week
python3 betting/cfb_fetch.py && python3 betting/cfb_rankings.py && python3 betting/cfb_weather.py && python3 betting/cfb_model.py --week
python3 betting/final.py            # decision layer -> data/final_nfl.json, data/cfb/final_cfb.json (+ tracker)
python3 betting/share/cards.py      # -> betting/share/nfl_week<N>.pdf, cfb_week<N>.pdf
```
`angles.py` has separate NFL and college angle books, each defined up front with a reason and graded on 2011–2026
closing lines. The ones that survived:

| Angle | Record | ROI | Seasons up | 2025–26 | With model agreeing |
|---|---|---|---|---|---|
| NFL Upset Letdown: fade a team that just won outright as a 6+ pt dog | 170-133 | +9.4% | 11/15 | 12-6 | +14.3% |
| NFL West-Coast Early Kickoff: back West-coast teams at 1pm ET (the fade lost) | 149-112 | +11.3% | 11/15 | 12-10 | +15.2% |
| College Rest Edge (weak) | 148-115 | +7.4% | 10/15 | 12-9 | |
| College Service Academy Dog: stack-only (plays only when the model agrees) | 128-102 | +6.1% | 9/15 | 9-9 | +10.5% |

Revenge, lookahead, bounce-back, home dogs, off-bye, primetime and division unders all tested at about zero or worse.

`final.py` collects every signal per bet: model edge, systems and angles. It passes on conflicts and sizes the stake
from the strongest signal plus 0.5u per extra agreeing signal (max 2u). One bet per team (spread by default,
moneyline only if the spread price is too steep). Prices: FanDuel unless DraftKings is strictly better. Each play
carries its backup: the game-specific reason plus every signal's record.

## Unit size
`betting/share/settings.json` sets the dollar value of a unit (`unit_dollars`) and your bankroll. Cards show every play
in units and dollars. Stakes were designed for 1 unit ≈ 1% of bankroll; bigger units mean proportionally more risk.

## Shareable weekly cards (PDF)
```
python3 betting/share/weekly.py          # -> betting/share/nfl_week<N>.pdf and cfb_week<N>.pdf
```
Run the models first. Each card has these sections:
- **Best Bets**: model plays, each with a reason.
- **Totals system**: Blowout Overs (college) or Wind Unders (NFL).
- **Weather Desk** (college): steady-wind and steady-rain unders, with the forecast wind and wet hours for each game.
- **Top 25 Watch** (college): every game with a ranked team: ranks at kickoff, records going in, poll rank vs the
  betting market's power rank, streaks and the last meeting. Context only (none of those systems made money).
- **Systems Lab** (college): every system `cfb_lab.py` tested, its ROI overall and in weeks 5–9, and whether it made the card.
- College matchups show each team's rank and record (`#7 Indiana 5-0 @ Nebraska 5-0`) everywhere on the card.
- **Spread & Moneyline Systems.** NFL: Close Road Team (spread *or* moneyline, pick one) and Buy-Low Underdog.
  College: Rested Home Team. There's no college moneyline system because the free data has no historical moneylines.
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
| NFL Close road team, moneyline version | 636-579, +4.1% | 48-41, +3.4% | Same games as the spread system; bet one or the other |
| NFL Buy-low underdog: the dog when the road team keeps missing the spread | 223-179, +7.3% | 20-13, +15.3% | Weak (t = 1.4), 0.5% stakes |
| College Rested home team: 3+ days more rest and the line moved 3+ toward them | 157-122, +7.4%, 11 of 14 seasons up | 14-11, +6.9% | Weak, 0.5% stakes |
| NFL Wind under: outdoors, 12–20 mph forecast wind | 327-238, +12.4% | 15-17, −10% | Probable but cold, 0.5% stakes |
| College Steady wind under: wind averaging 15+ mph from 3 h before kickoff to 4 h after | 329-251, +8.2%, 11 of 15 seasons up | 15-9, +19.3% | Moderate (t = 2.1), 0.5% stakes |
| College Steady rain under: rain in 3+ of those 8 hours | 370-285, +7.7%, 11 of 15 seasons up; **+10.9% in weeks 5–9** | 41-33, +5.8% | Moderate (t = 2.1), 0.5% stakes |
| College Over-streak fade: both teams over in 5+ of their combined last 6 | 434-367, +3.4% | 47-39, +4.3% | Weak (t = 1.0): plays only with the model |
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
- Not included (no free data): starting QBs, injuries, returning production, recruiting/transfer talent.
  Historical lines come without odds, so the backtest assumes -110 and can't grade moneylines.

### College systems lab (`cfb_lab.py`, `cfb_weather.py`, `cfb_rankings.py`)
```
python3 betting/cfb_rankings.py  # top-25 rank of both teams at kickoff for every FBS game since 2011 (ESPN: AP, then CFP)
python3 betting/cfb_weather.py   # kickoff weather: Meteostat station history 2011-now + Open-Meteo forecast this week
python3 betting/cfb_lab.py       # grade every system -> data/cfb/lab.json (the card's Systems Lab) + this week's plays
```
Weather comes from the nearest Meteostat station with hourly records (all 141 home stadiums have one within 60 km;
6 are indoors). Each game gets kickoff wind/temp/rain plus *steady* measures over the 8 hours from 3 before kickoff to
4 after: average wind (`wind8`) and wet hours (`wet8`, hours with more than 0.2 mm of rain). This week's games use the
same windows from the hourly forecast.

58 systems in 12 categories, each written down with a reason before testing, graded on 2011–2026 closing lines at
-110 with early (weeks 0–4), mid-season (5–9) and late (10+) splits. A "mid-season only" pass also has to hold up in
weeks 3–4 and 10–11 (two candidates looked great in weeks 5–9 and lost 6–34% right outside that window: noise).

Ranking/record/matchup features (`cfb_features.py`): rank at kickoff and in the team's previous game, W-L and
conference W-L going in, straight-up streak, last season's win %, regular-season games left and bowl-eligibility math,
the last meeting (margin, how long ago, how many of the last 10 seasons they met), the next opponent's current rank,
kickoff hour (ET), market power rank among FBS teams that week, and unit percentiles (rush/pass offense and defense,
pace).

| Category | Systems | Verdict |
|---|---|---|
| Weather | wind under (kickoff 15+ / 12+, steady 15+), rain under (kickoff, steady), cold under, wind dog | Wind and rain unders pass (+5 to +10% ROI, t ≈ 2). The card uses the **steady** versions. Cold under and wind dog fail |
| Blowout | spread over 30 → over | Strong (t = 2.9), but mostly an early-season system: +2.1% in weeks 5–9 |
| Trend | fade 3 straight covers, back 3 straight non-covers, fade over streaks | Only the over-streak fade survives (weak) |
| Underdog | conference dogs 7–17, mid-season conference road dogs | −5.2% / −1.8%: no edge |
| Big dog | 21+ point dogs, big dog with a low total | −3.5% / −6.6% |
| Stats-only | a walk-forward ridge on offense/defense EPA, success rate, pass/rush, points, pace (`stat_margin`, `stat_total`); bet when it's 7+ or 10+ off the line | −4 to −6%: the line already knows the box-score numbers |
| Season phase | conference unders weeks 5–9, early-season overs, November unders | −1.7 to −4.5% |
| Edge | our prediction model at 3%/5% edge | too few bets to grade |
| Rankings (14) | unranked home dog vs ranked, ranked vs ranked dog, ranked favorite laying 14+ in league play, top-10 dog, newly ranked fade, ranked team off a loss, upset-winner fade, poll vs market rank (fade/back), fell out of the poll, line-contradicts-poll favorite, look-ahead, sandwich, night home dog | All benched (best +2.7%, t < 1). Ranked-vs-ranked **favorites** covered 334-263 (+6.7%), but only after flipping a failed idea, t = 1.75, mostly home favorites (road favorites lost) and losing at 7–10.5 point spreads: not trusted |
| Records (8) | undefeated favorite fade, winless dog, worse record but favored, win streak vs losing streak, bowl push, eliminated favorite fade, last year's 10-win team early, last year's bad team early | All benched (−6.6% to +2.0%) |
| Head-to-head (4) | revenge after a 14+ loss, blowout-rematch fade, rivalry dog, rivalry-week dog | All benched (−10.4% to +2.2%) |
| Matchup (7) | run-game and pass-game mismatches, elite defense vs elite offense (side and under), two slow teams under, two fast teams over, service academy under | All benched (−11.7% to −0.4%) |

Also tested and cut (mid-season ideas): conference home dogs, off-bye teams, following/fading line steam, fading big
total moves, letdown after an upset win, bounce-back after an upset loss or a blowout, two-good-defense unders, big
conference favorites. None beat -110.

Weather caveat: the history uses **measured** weather, but you bet on a **forecast**. Two checks say the edge isn't
only hindsight: (1) closing totals do drop about a point in 15+ mph wind or rain, yet those games still finish 1–2
points further under; (2) the steady (all-day, forecastable) versions hold up as well as the kickoff ones.
Wind **and** rain on the same game went 35-16 to the under (+30%, small sample), so the card stacks them to 1u.
A Blowout over that meets any under system is a pass (those overs lost with each one: 15-20, 15-17, 26-32).
