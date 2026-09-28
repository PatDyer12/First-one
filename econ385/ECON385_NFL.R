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

# 5.1 -- Look at the structure of the data: size, seasons, variable types
head(nfl)
str(nfl)
names(nfl)
nrow(nfl)                 # number of games
summary(nfl)
range(nfl$season)         # first and last season
length(unique(nfl$season))
colSums(is.na(nfl))       # check for missing values (there are none)

# 5.2 -- Create the three new variables
nfl$score_margin   <- nfl$score1 - nfl$score2   # Team 1 points minus Team 2 points
nfl$total_points   <- nfl$score1 + nfl$score2   # combined points scored in the game
nfl$elo_difference <- nfl$elo1 - nfl$elo2       # Team 1 pregame rating advantage

# Counts of regular-season vs playoff games, neutral-site games, and ties
table(nfl$playoff)                      # 0 = regular season, 1 = playoff
table(nfl$neutral)                      # 1 = neutral site
table(nfl$playoff, nfl$neutral,
      dnn = c("playoff", "neutral"))    # cross-tab of both
table(nfl$result1)                      # 0.5 = tie
table(nfl$score_margin == 0)            # same tie count, checked from the scores

# 5.3 -- Highest-scoring game and largest blowout
report_cols <- c("date", "season", "playoff", "team1", "team2", "score1", "score2",
                 "total_points", "score_margin")
nfl[which.max(nfl$total_points), report_cols]
nfl[which.max(abs(nfl$score_margin)), report_cols]

# -----------------------------------------------------------------------------
# Question 6: Is there a home-field advantage?
# -----------------------------------------------------------------------------

# Keep non-neutral regular-season games only, so team1 is always the home team
reg <- subset(nfl, neutral == 0 & playoff == 0)
nrow(reg)

# Ties: a tie is neither a home win nor a home loss, so home win proportions are
# computed over DECISIVE games (ties dropped). Ties are reported separately.
reg$tie      <- reg$result1 == 0.5
decisive     <- subset(reg, !tie)

# 6.1 -- Overall home-field statistics
home_win_pct <- mean(decisive$result1 == 1)   # share of decisive games home team won
tie_pct      <- mean(reg$tie)                 # share of all games that ended tied
mean_home    <- mean(reg$score1)              # mean home score (points)
mean_away    <- mean(reg$score2)              # mean away score (points)
round(c(n_games = nrow(reg), n_decisive = nrow(decisive),
        home_win_pct = home_win_pct, tie_pct = tie_pct,
        mean_home = mean_home, mean_away = mean_away,
        mean_margin = mean_home - mean_away), 4)

# 6.2 -- Home win % and mean home margin by season
by_season <- data.frame(
  season       = sort(unique(reg$season)),
  games        = as.vector(table(reg$season)),
  home_win_pct = as.vector(tapply(decisive$result1 == 1, decisive$season, mean)),
  mean_margin  = as.vector(tapply(reg$score_margin, reg$season, mean))
)
by_season$home_win_pct <- round(by_season$home_win_pct, 4)
by_season$mean_margin  <- round(by_season$mean_margin, 2)
by_season

# Largest / smallest home advantage, by each statistic
by_season[which.max(by_season$home_win_pct), ]
by_season[which.min(by_season$home_win_pct), ]
by_season[which.max(by_season$mean_margin), ]
by_season[which.min(by_season$mean_margin), ]

# 6.3 -- 2020 (mostly empty stadiums) vs 2002-2019 combined
reg$era      <- ifelse(reg$season == 2020, "2020", "2002-2019")
decisive$era <- ifelse(decisive$season == 2020, "2020", "2002-2019")
era_win    <- tapply(decisive$result1 == 1, decisive$era, mean)
era_margin <- tapply(reg$score_margin, reg$era, mean)
era_table  <- data.frame(home_win_pct = round(era_win, 4),
                         mean_margin  = round(era_margin, 2))
era_table
# Differences (2020 minus 2002-2019)
round(c(diff_win_pct = unname(era_win["2020"] - era_win["2002-2019"]),
        diff_margin  = unname(era_margin["2020"] - era_margin["2002-2019"])), 4)

# 6.4 is a written answer (no code needed)

# -----------------------------------------------------------------------------
# Question 7: Do better-rated teams win by more?
# -----------------------------------------------------------------------------

# 7.1 -- Scatterplot of Elo difference vs final score margin (home perspective)
# Saved to a PNG for the PDF write-up and also drawn on screen.
draw_q7_plot <- function() {
  plot(reg$elo_difference, reg$score_margin,
       pch = 16, cex = 0.5, col = rgb(0, 0, 0.6, 0.25),
       xlab = "Elo difference (home Elo - away Elo)",
       ylab = "Score margin (home points - away points)",
       main = "NFL regular season, non-neutral games, 2002-2020")
  abline(h = 0, v = 0, lty = 2, col = "gray50")
  abline(lm(score_margin ~ elo_difference, data = reg), col = "red", lwd = 2)
}
png("q7_scatter.png", width = 900, height = 650, res = 120)
draw_q7_plot()
dev.off()
draw_q7_plot()

# Correlation and fitted line to describe the pattern in the plot
cor(reg$elo_difference, reg$score_margin)
coef(lm(score_margin ~ elo_difference, data = reg))

# 7.2 -- Split by whether the home team had the higher pregame Elo
sum(reg$elo_difference == 0)   # games with exactly equal ratings (none)
reg$home_stronger      <- ifelse(reg$elo_difference > 0, "Home higher Elo", "Home lower Elo")
decisive$home_stronger <- ifelse(decisive$elo_difference > 0, "Home higher Elo", "Home lower Elo")

q7_table <- data.frame(
  games        = as.vector(table(reg$home_stronger)),
  home_win_pct = round(as.vector(tapply(decisive$result1 == 1, decisive$home_stronger, mean)), 4),
  mean_margin  = round(as.vector(tapply(reg$score_margin, reg$home_stronger, mean)), 2),
  mean_elo_gap = round(as.vector(tapply(reg$elo_difference, reg$home_stronger, mean)), 1),
  row.names    = sort(unique(reg$home_stronger))
)
q7_table

# -----------------------------------------------------------------------------
# Question 8: Your group's NFL finding
# -----------------------------------------------------------------------------

# Empirical question: Are Elo's pregame win probabilities well calibrated?
# When Elo says Team 1 has a p% chance to win, does Team 1 actually win about
# p% of the time?
# Subsample: all 5,075 games minus the 11 ties (decisive games only), grouped
# into bins of the pregame probability elo_prob1.

games_dec <- subset(nfl, result1 != 0.5)
games_dec$prob_bin <- cut(games_dec$elo_prob1,
                          breaks = seq(0, 1, by = 0.1),
                          include.lowest = TRUE)

calib <- data.frame(
  games         = as.vector(table(games_dec$prob_bin)),
  mean_pred     = round(as.vector(tapply(games_dec$elo_prob1, games_dec$prob_bin, mean)), 3),
  actual_winpct = round(as.vector(tapply(games_dec$result1, games_dec$prob_bin, mean)), 3),
  row.names     = levels(games_dec$prob_bin)
)
calib$gap <- calib$actual_winpct - calib$mean_pred
calib <- calib[calib$games > 0, ]
calib

# How often does the Elo favorite actually win? (upset rate = 1 - this)
fav_won <- (games_dec$elo_prob1 > 0.5) == (games_dec$result1 == 1)
mean(fav_won)

# Calibration plot: predicted vs actual win rate; points on the 45-degree line
# mean the probabilities are accurate on average
draw_q8_plot <- function() {
  plot(calib$mean_pred, calib$actual_winpct, pch = 19, cex = 1.3,
       xlim = c(0, 1), ylim = c(0, 1),
       xlab = "Mean Elo pregame win probability (Team 1)",
       ylab = "Actual Team 1 win rate",
       main = "How accurate are Elo's pregame probabilities?")
  abline(0, 1, lty = 2, col = "gray40")
  text(calib$mean_pred, calib$actual_winpct, labels = calib$games,
       pos = 4, cex = 0.7, col = "gray30")
}
png("q8_calibration.png", width = 900, height = 650, res = 120)
draw_q8_plot()
dev.off()
draw_q8_plot()

# -----------------------------------------------------------------------------
# Reproducibility information
# -----------------------------------------------------------------------------

# Leave this command at the end of your completed script. It records the R
# version and attached packages used for the analysis.
sessionInfo()
