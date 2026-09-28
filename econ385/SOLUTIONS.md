# ECON 385 Group Assignment: Worked Answers

Part I is worked by hand, step by step. Part II numbers all come from `ECON385_NFL.R` (runs clean top to bottom). Put these in your own words for the typeset PDF. Your group should also verify each number, as the assignment requires.

---

# Part I

## Question 1: Linear combinations

### 1.1 Derivation
Let μ_X = E[X] and μ_Y = E[Y]. Then E[aX + bY] = aμ_X + bμ_Y, so

aX + bY − E[aX + bY] = a(X − μ_X) + b(Y − μ_Y).

Square it:

[a(X − μ_X) + b(Y − μ_Y)]² = a²(X − μ_X)² + b²(Y − μ_Y)² + 2ab(X − μ_X)(Y − μ_Y)

Take expectations. Expectation is linear, so the constants come out:

Var(aX + bY) = a²E[(X − μ_X)²] + b²E[(Y − μ_Y)²] + 2ab·E[(X − μ_X)(Y − μ_Y)]
            = a²Var(X) + b²Var(Y) + 2ab·Cov(X, Y) ∎

### 1.2 C = 2X + Y and D = X − Y

| | C = 2X + Y (a=2, b=1) | D = X − Y (a=1, b=−1) |
|---|---|---|
| E | 2(24) + 4 = **52 min** | 24 − 4 = **20 min** |
| Var | 4(36) + 1(25) + 2(2)(1)(6) = 144 + 25 + 24 = **193 min²** | 36 + 25 + 2(1)(−1)(6) = 61 − 12 = **49 min²** |
| SD | √193 = **13.89 min** | √49 = **7.00 min** |

### 1.3 If X and Y are independent, Cov = 0
- Var(C) = 144 + 25 = **169 min²** (SD = 13.00 min)
- Var(D) = 36 + 25 = **61 min²** (SD = 7.81 min)

### 1.4 Comparison
With positive covariance, Var(C) is **24 higher** than under independence (193 vs 169). Var(D) is **12 lower** (49 vs 61). For C, a and b have the same sign, so the positive covariance term 2abCov is added. X and Y tend to move together, so adding them compounds the spread. For D, a and b have opposite signs, so the term is subtracted: when X is high, Y also tends to be high, and taking the difference cancels some of that variation.

---

## Question 2: Discrete PMF

### 2.1 Validity + CDF
Every p(j) is between 0 and 1, and 0.10 + 0.25 + 0.35 + 0.20 + 0.10 = 1.00. So it's a valid PMF.

| j | 0 | 1 | 2 | 3 | 4 |
|---|---|---|---|---|---|
| F_J(j) | 0.10 | 0.35 | 0.70 | 0.90 | 1.00 |

The CDF is a **step function**. It's flat between the integers because J can't take values like 1.5, so F(1.5) = F(1) = 0.35. It jumps by p(j) at each integer j. F = 0 for j < 0 and F = 1 for j ≥ 4.

### 2.2 Probabilities
- P(J ≤ 2) = F(2) = **0.70**
- P(1 < J ≤ 3) = F(3) − F(1) = 0.90 − 0.35 = **0.55** (= p(2) + p(3))
- P(J ≥ 3 | J ≥ 1) = P(J ≥ 3) / P(J ≥ 1) = (0.20 + 0.10) / (1 − 0.10) = 0.30 / 0.90 = **0.3333**
  The new reference group is **students who got at least one offer**, not all graduates.

### 2.3 Moments
- E[J] = 0(.10) + 1(.25) + 2(.35) + 3(.20) + 4(.10) = 0 + .25 + .70 + .60 + .40 = **1.95 offers**
- E[J²] = 0 + 1(.25) + 4(.35) + 9(.20) + 16(.10) = .25 + 1.40 + 1.80 + 1.60 = 5.05
- Var(J) = E[J²] − (E[J])² = 5.05 − 3.8025 = **1.2475 offers²**
- SD(J) = √1.2475 = **1.12 offers**

### 2.4 B = 1000 + 750J
Use the linear rules: a constant shifts the mean but not the spread.
- E[B] = 1000 + 750(1.95) = **$2,462.50**
- Var(B) = 750²·Var(J) = 562,500 × 1.2475 = **701,718.75 dollars²**
- SD(B) = 750 × 1.1169 = **$837.69**

Interpretation: on average, a participating graduate receives about $2,462.50. Individual payments typically differ from that average by around $838, depending on how many offers the student gets.

---

## Question 3: Sample stats by hand

Data (already sorted): 17, 19, 20, 21, 22, 23, 24, 24, 24, 25, 26, 27, 28, 30, 45

### 3.1 Center
- n = **15**
- Sum = 375, so x̄ = 375/15 = **25 min**
- Median = the (15+1)/2 = 8th value = **24 min**
- Mode = **24 min** (it appears 3 times)

I'd report the **median (24 min)**. The 45 is an outlier that pulls the mean up. The median ignores how extreme the top value is, so it better represents a "typical" worker.

### 3.2 Spread
Deviations (xᵢ − 25): −8, −6, −5, −4, −3, −2, −1, −1, −1, 0, 1, 2, 3, 5, 20
Squared: 64, 36, 25, 16, 9, 4, 1, 1, 1, 0, 1, 4, 9, 25, 400. **Sum = 596**

- s² = 596 / (15 − 1) = **42.57 min²**
- s = √42.57 = **6.52 min**

Note the 45 alone contributes 400 of the 596.

### 3.3 Without the 45 (n = 14)
- Sum = 375 − 45 = 330, so x̄ = 330/14 = **23.57 min**
- Median = average of the 7th and 8th values = (24 + 24)/2 = **24 min**
- SS: take the old SS about 25 without the 400, giving 196. Then re-center with SS = Σ(x−25)² − n(x̄−25)² = 196 − 14(1.4286)² = 196 − 28.57 = 167.43
- s² = 167.43/13 = 12.88, so s = **3.59 min**

Comparison: the mean dropped by 1.43 min and the SD almost **halved** (6.52 to 3.59). The median didn't move at all. The SD is the most sensitive because it squares deviations. The mean is somewhat sensitive, and the median is robust.

### 3.4 Minutes to seconds (×60)
Location and spread measures scale by 60. Variance scales by 60² = 3600.
- Mean = 25 × 60 = **1,500 s**
- Median = 24 × 60 = **1,440 s**
- Variance = 42.57 × 3600 = **153,257.14 s²**
- SD = 6.52 × 60 = **391.48 s**

---

## Question 4: Normal distributions

X ~ N(72, 8²) means μ = 72, σ = 8. Y ~ N(80, 5²) means μ = 80, σ = 5.

### 4.1 68–95–99.7 rule (μ ± 1σ, 2σ, 3σ)
| | 68% | 95% | 99.7% |
|---|---|---|---|
| Exam X | [64, 80] | [56, 88] | [48, 96] |
| Exam Y | [75, 85] | [70, 90] | [65, 95] |

### 4.2 z-scores
- z_X = (84 − 72)/8 = **1.50**
- z_Y = (87 − 80)/5 = **1.40**

The student did **relatively better on Exam X**: 1.5 SDs above the mean vs 1.4. That holds even though the raw score was lower on X.

### 4.3 P(64 ≤ X ≤ 88)
Standardize: z = (64−72)/8 = −1 and z = (88−72)/8 = 2.
P = Φ(2) − Φ(−1) = 0.9772 − 0.1587 = **0.8185**

### 4.4 Y
- P(Y ≥ 90) = P(Z ≥ (90−80)/5) = P(Z ≥ 2) = 1 − 0.9772 = **0.0228**
- P(Y = 90) = **0**

Why: Y is continuous, so probability is the **area under the density curve**. A single point has zero width, so its area is 0. The interval [90, ∞) has positive width, so it has positive area.

---

# Part II (numbers from the R script)

**How we handled things:** there are no missing values in any column. Ties (result1 = 0.5) are dropped from every win-percentage calculation ("decisive games"), and the tie rate is reported separately. Mean scores and margins use all games, ties included. Q6–7 use the 4,827 non-neutral regular-season games.

## Q5

**5.1** There are **5,075 games** over **19 seasons, 2002–2020** (the last game is the Feb 7, 2021 Super Bowl, which counts as the 2020 season). Variable types:
- `date` is character when imported, then converted to Date
- `team1` and `team2` are character
- `season`, `neutral`, `playoff`, `score1`, and `score2` are integer
- `elo1`, `elo2`, `elo_prob1`, and `result1` are numeric (double)

**5.2**
- `score_margin` is how many points Team 1 won by. It's negative if they lost.
- `total_points` is the combined scoring in the game.
- `elo_difference` is Team 1's pregame rating edge. Positive means Team 1 was rated stronger.

| | Count |
|---|---|
| Regular season | 4,864 |
| Playoff | 211 |
| Neutral site | 56 (37 regular-season, mostly London/Mexico games, + 19 playoff, i.e. Super Bowls) |
| Ties | 11 |

**5.3**
- Most total points: **2004-11-28 (2004 season), CIN 58, CLE 48**, for 106 total points.
- Largest margin: **2009-10-18 (2009 season), NE 59, TEN 0**, a 59-point margin.

## Q6: Home-field advantage (4,827 games, 10 ties, 4,817 decisive)

**6.1**

| Statistic | Value |
|---|---|
| Home win % (decisive games) | **56.82%** |
| Tie rate | **0.21%** |
| Mean home score | **23.34 pts** |
| Mean away score | **21.05 pts** |
| Mean home margin | **+2.28 pts** |

Yes, this is descriptive evidence of a home-field advantage. Home teams win well over half of decisive games and outscore visitors by about 2.3 points per game on average.

**6.2** By season (home win % on decisive games, mean margin in points):

| Season | Win % | Margin | | Season | Win % | Margin |
|---|---|---|---|---|---|---|
| 2002 | .5804 | 2.25 | | 2012 | .5748 | 2.59 |
| 2003 | **.6157** | 3.63 | | 2013 | .6008 | 3.23 |
| 2004 | .5664 | 2.51 | | 2014 | .5754 | 2.67 |
| 2005 | .5952 | **3.74** | | 2015 | .5375 | 1.48 |
| 2006 | .5312 | 0.85 | | 2016 | .5777 | 2.60 |
| 2007 | .5765 | 2.89 | | 2017 | .5697 | 2.50 |
| 2008 | .5709 | 2.55 | | 2018 | .6056 | 2.34 |
| 2009 | .5725 | 2.33 | | 2019 | .5200 | **−0.05** |
| 2010 | .5591 | 1.95 | | 2020 | **.4980** | 0.05 |
| 2011 | .5686 | 3.30 | | | | |

- By **home win %**: the largest was **2003 (61.57%)** and the smallest was **2020 (49.80%)**.
- By **mean margin**: the largest was **2005 (+3.74 pts)** and the smallest was **2019 (−0.05 pts)**.

The two statistics don't pick the same seasons. Say which one you're using. Win % only counts whether the home team won, while margin also reflects how big the wins and losses were.

**6.3**

| | Home win % | Mean margin |
|---|---|---|
| 2002–2019 | 57.21% | +2.41 pts |
| 2020 | 49.80% | +0.05 pts |
| **Difference** | **−7.41 pp** | **−2.36 pts** |

In 2020, the home advantage essentially disappeared.

**6.4** This is just a comparison of two samples, not a controlled experiment, so we can't say empty stadiums caused the drop. Other things also differed in 2020:
- **Random variation.** It's a single season of about 256 games. 2019 had a margin of −0.05 with full crowds, so a near-zero season can happen anyway.
- **Pandemic-related changes beyond crowds.** COVID protocols, player opt-outs, no preseason games, altered practices, and roster disruptions.
- **Travel and routine.** Teams changed travel logistics, and some did more remote meetings, which may have reduced the away team's usual disadvantage.
- **Rule and officiating trends.** Penalty rates, referee behavior (fewer crowd-influenced calls?), and rule changes over the years.
- **Team quality mix.** Which teams happened to be strong, and their schedules, differ from season to season. Elo shows that team strength matters a lot (Q7).
- **Longer-run trend.** The 2019 number suggests home advantage may have been shrinking already.

## Q7: Elo vs margin

**7.1** See `q7_scatter.png`. There's a clear **positive** but very noisy relationship. The correlation is **0.378**. The fitted line is margin = 2.24 + 0.0407 × Elo diff, so about 4 extra points of margin for every 100 Elo points. The intercept of about 2.2 at an Elo difference of 0 is basically the home advantage between evenly matched teams.

**7.2**

| | Games | Home win % | Mean home margin | Mean Elo gap |
|---|---|---|---|---|
| Home team higher Elo | 2,407 | **69.86%** | **+6.72 pts** | +111.2 |
| Home team lower Elo | 2,420 | **43.85%** | **−2.13 pts** | −108.1 |

(No games had exactly equal Elo ratings.)

Team strength matters much more than venue here. When the home team is stronger, it wins about 70% of the time by almost 7 points. When it's weaker, it still loses more often than not. But the home advantage is still visible in both groups. The two groups have roughly the same-size Elo gap (about ±110), yet the stronger home team wins by +6.72 while the stronger away team only wins by 2.13. If there were no home effect, those would be about equal. Roughly: (6.72 − 2.13)/2 ≈ 2.3 pts, which matches the overall home edge from Q6.

## Q8: Our finding: are Elo's pregame probabilities accurate?

**Question:** When Elo gives Team 1 a p% chance of winning, does Team 1 actually win about p% of the time?

**Sample:** all 5,064 decisive games (the 11 ties are dropped), grouped into 10-percentage-point bins of `elo_prob1`.

| Predicted bin | Games | Mean predicted | Actual win rate | Gap |
|---|---|---|---|---|
| 0.1–0.2 | 55 | .172 | .200 | +.028 |
| 0.2–0.3 | 244 | .256 | .270 | +.014 |
| 0.3–0.4 | 502 | .353 | .337 | −.016 |
| 0.4–0.5 | 761 | .453 | .461 | +.008 |
| 0.5–0.6 | 1,046 | .552 | .545 | −.007 |
| 0.6–0.7 | 1,089 | .652 | .615 | −.037 |
| 0.7–0.8 | 862 | .748 | .724 | −.024 |
| 0.8–0.9 | 453 | .841 | .843 | +.002 |
| 0.9–1.0 | 52 | .919 | .885 | −.034 |

**Answer:** Elo is **well calibrated**. Every bin is within about 4 percentage points of its prediction, and the points in `q8_calibration.png` sit right on the 45° line. The favorite won **64.3%** of games, so about 1 in 3 games is an "upset," and that is exactly what the probabilities predict. There's a slight tendency for moderate favorites (60–80%) to win a bit *less* often than predicted. A possible reason, which connects to Q6: Elo's built-in home bonus may overstate home advantage in the later seasons.
