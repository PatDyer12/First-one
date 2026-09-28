# ECON 385 -- Group Assignment: NFL Data Analysis
#
# Group members: Andrew Mount, Pat Dyer
#
# INSTRUCTIONS
# 1. Place this script and nfl_games_2002_2020.csv in the same folder.
# 2. Add all commands required for Questions 5--8 beneath the corresponding
#    section headings below.
# 3. Retain the commands that produce every statistic, table, and figure used
#    in your PDF submission.
# 4. Add brief comments explaining the purpose of each major block of code.
# 5. The completed script must run from beginning to end in a clean R session.
# 6. Base R is sufficient. If you use additional packages, load them explicitly
#    with library(), but do not include install.packages() in the submitted file.

# -----------------------------------------------------------------------------
# Setup: import the data
# -----------------------------------------------------------------------------

# R looks for the CSV in the current working directory. If the import fails,
# use getwd() to see the folder R is currently using. The recommended solution
# is to open the script as an RStudio project or set the working directory
# through RStudio's Files pane rather than placing a personal file path here.

nfl <- read.csv(
  "nfl_games_2002_2020.csv",
  stringsAsFactors = FALSE
)

# Convert the imported date text to R's Date class. The CSV stores dates in
# year-month-day order, such as 2020-09-10.
nfl$date <- as.Date(nfl$date, format = "%Y-%m-%d")

# Do not alter the import and date-conversion commands above. Begin your
# assignment analysis below.

# -----------------------------------------------------------------------------
# Question 5: Becoming familiar with the data
# -----------------------------------------------------------------------------

# 5.1 look at the data
head(nfl)
str(nfl)
names(nfl)
nrow(nfl)
summary(nfl)

# seasons in the data
min(nfl$season)
max(nfl$season)

# check for missing values (there are none)
sum(is.na(nfl))

# 5.2 make the new variables
nfl$score_margin <- nfl$score1 - nfl$score2
nfl$total_points <- nfl$score1 + nfl$score2
nfl$elo_difference <- nfl$elo1 - nfl$elo2

# regular season (0) vs playoff (1)
table(nfl$playoff)

# neutral site games (1 = neutral)
table(nfl$neutral)
table(nfl$playoff, nfl$neutral)

# ties (result1 = 0.5)
table(nfl$result1)

# 5.3 game with the most total points
max(nfl$total_points)
nfl[nfl$total_points == max(nfl$total_points), ]

# game with the biggest score margin (use abs so blowouts either way count)
max(abs(nfl$score_margin))
nfl[abs(nfl$score_margin) == max(abs(nfl$score_margin)), ]

# -----------------------------------------------------------------------------
# Question 6: Is there a home-field advantage?
# -----------------------------------------------------------------------------

# only non-neutral regular season games so team1 is always the home team
reg <- subset(nfl, neutral == 0 & playoff == 0)
nrow(reg)

# ties dont count as a win or loss so we take them out for win %
no_ties <- subset(reg, result1 != 0.5)
nrow(no_ties)

# 6.1
# home win % (decisive games only)
mean(no_ties$result1)

# tie %
mean(reg$result1 == 0.5)

# average home and away score
mean(reg$score1)
mean(reg$score2)

# average home margin
mean(reg$score_margin)

# 6.2 home win % and home margin by season
tapply(no_ties$result1, no_ties$season, mean)
tapply(reg$score_margin, reg$season, mean)

# 6.3 2020 vs 2002-2019
games2020 <- subset(reg, season == 2020)
games_before <- subset(reg, season < 2020)
no_ties2020 <- subset(no_ties, season == 2020)
no_ties_before <- subset(no_ties, season < 2020)

# home win %
mean(no_ties2020$result1)
mean(no_ties_before$result1)
mean(no_ties2020$result1) - mean(no_ties_before$result1)

# home margin
mean(games2020$score_margin)
mean(games_before$score_margin)
mean(games2020$score_margin) - mean(games_before$score_margin)

# 6.4 is just a written answer

# -----------------------------------------------------------------------------
# Question 7: Do better-rated teams win by more?
# -----------------------------------------------------------------------------

# 7.1 scatterplot
plot(reg$elo_difference, reg$score_margin,
     xlab = "Elo difference (home - away)",
     ylab = "Score margin (home - away)",
     main = "Elo Difference vs Score Margin")
abline(h = 0, lty = 2)
abline(v = 0, lty = 2)
abline(lm(score_margin ~ elo_difference, data = reg), col = "red")

# correlation and the slope of the red line
cor(reg$elo_difference, reg$score_margin)
lm(score_margin ~ elo_difference, data = reg)

# 7.2 split into home team better vs home team worse
# check if any games had the exact same elo (there are none)
sum(reg$elo_difference == 0)

home_better <- subset(reg, elo_difference > 0)
home_worse <- subset(reg, elo_difference < 0)
nrow(home_better)
nrow(home_worse)

# home win % (without ties)
home_better_noties <- subset(home_better, result1 != 0.5)
home_worse_noties <- subset(home_worse, result1 != 0.5)
mean(home_better_noties$result1)
mean(home_worse_noties$result1)

# average home margin
mean(home_better$score_margin)
mean(home_worse$score_margin)

# average elo gap in each group
mean(home_better$elo_difference)
mean(home_worse$elo_difference)

# -----------------------------------------------------------------------------
# Question 8: Your group's NFL finding
# -----------------------------------------------------------------------------

# Our question: are the Elo pregame win probabilities accurate?
# if Elo says a team has a 70% chance, do they actually win about 70% of the time?
# we use all games except ties

all_noties <- subset(nfl, result1 != 0.5)
nrow(all_noties)

# put the probabilities into groups of 10% (0-0.1, 0.1-0.2, etc)
all_noties$prob_group <- cut(all_noties$elo_prob1, breaks = seq(0, 1, by = 0.1))

# number of games in each group
table(all_noties$prob_group)

# average predicted probability in each group
tapply(all_noties$elo_prob1, all_noties$prob_group, mean)

# how often team 1 actually won in each group
tapply(all_noties$result1, all_noties$prob_group, mean)

# graph: predicted vs actual, if its accurate the dots should be on the line
predicted <- tapply(all_noties$elo_prob1, all_noties$prob_group, mean)
actual <- tapply(all_noties$result1, all_noties$prob_group, mean)
plot(predicted, actual, xlim = c(0, 1), ylim = c(0, 1), pch = 19,
     xlab = "Predicted win probability",
     ylab = "Actual win %",
     main = "Are Elo Predictions Accurate?")
abline(0, 1, lty = 2)

# how often the favorite won
favorite_won <- (all_noties$elo_prob1 > 0.5 & all_noties$result1 == 1) |
                (all_noties$elo_prob1 < 0.5 & all_noties$result1 == 0)
mean(favorite_won)

# -----------------------------------------------------------------------------
# Reproducibility information
# -----------------------------------------------------------------------------

# Leave this command at the end of your completed script. It records the R
# version and attached packages used for the analysis.
sessionInfo()
