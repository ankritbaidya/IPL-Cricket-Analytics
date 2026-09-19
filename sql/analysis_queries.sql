-- ============================================================================
-- IPL Cricket Analytics — Analysis Queries
-- Written against the schema in schema.sql. Portable across MySQL 8+ and
-- PostgreSQL 13+ unless a comment says otherwise (window functions, CTEs and
-- CASE all work the same way in both).
-- ============================================================================


-- Q1. Top 10 run scorers of all time
-- Technique: JOIN, WHERE, GROUP BY, aggregation, ORDER BY
SELECT
    d.batter,
    SUM(d.batsman_runs) AS total_runs,
    COUNT(DISTINCT d.match_id) AS innings_played,
    ROUND(SUM(d.batsman_runs) * 100.0 / NULLIF(COUNT(*), 0), 2) AS strike_rate
FROM deliveries d
WHERE d.extras_type IS DISTINCT FROM 'wides'   -- MySQL: d.extras_type <> 'wides' OR d.extras_type IS NULL
GROUP BY d.batter
ORDER BY total_runs DESC
LIMIT 10;


-- Q2. Top 10 wicket-takers (run-outs excluded — a run-out isn't the bowler's dismissal)
-- Technique: WHERE with IN, GROUP BY, aggregation
SELECT
    d.bowler,
    COUNT(*) AS wickets,
    ROUND(SUM(d.total_runs) * 6.0 / NULLIF(SUM(CASE WHEN d.extras_type NOT IN ('wides','noballs') OR d.extras_type IS NULL THEN 1 ELSE 0 END), 0), 2) AS economy
FROM deliveries d
WHERE d.is_wicket = 1
  AND d.dismissal_kind IN ('caught','bowled','lbw','stumped','caught and bowled','hit wicket')
GROUP BY d.bowler
ORDER BY wickets DESC
LIMIT 10;


-- Q3. Team win percentage (across both team1 and team2 appearances)
-- Technique: UNION ALL to "unpivot" two team columns into one, CASE, aggregation
WITH team_appearances AS (
    SELECT id AS match_id, team1 AS team, winner FROM matches
    UNION ALL
    SELECT id AS match_id, team2 AS team, winner FROM matches
)
SELECT
    team,
    COUNT(*) AS matches_played,
    SUM(CASE WHEN team = winner THEN 1 ELSE 0 END) AS wins,
    ROUND(SUM(CASE WHEN team = winner THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS win_pct
FROM team_appearances
GROUP BY team
ORDER BY win_pct DESC;


-- Q4. Season-wise team performance
-- Technique: CTE reused from Q3 pattern, GROUP BY multiple columns
WITH team_appearances AS (
    SELECT id AS match_id, season, team1 AS team, winner FROM matches
    UNION ALL
    SELECT id AS match_id, season, team2 AS team, winner FROM matches
)
SELECT
    season,
    team,
    COUNT(*) AS matches_played,
    SUM(CASE WHEN team = winner THEN 1 ELSE 0 END) AS wins,
    ROUND(SUM(CASE WHEN team = winner THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS win_pct
FROM team_appearances
GROUP BY season, team
ORDER BY season, win_pct DESC;


-- Q5. Highest-scoring venues (by average runs per completed innings)
-- Technique: JOIN, GROUP BY, HAVING
SELECT
    m.venue,
    COUNT(DISTINCT d.match_id) AS matches,
    ROUND(SUM(d.total_runs) * 1.0 / COUNT(DISTINCT d.match_id || '-' || d.inning), 2) AS avg_runs_per_innings
    -- Postgres: d.match_id || '-' || d.inning ; MySQL: CONCAT(d.match_id, '-', d.inning)
FROM deliveries d
JOIN matches m ON m.id = d.match_id
GROUP BY m.venue
HAVING COUNT(DISTINCT d.match_id) >= 10   -- ignore venues with too few matches to be meaningful
ORDER BY avg_runs_per_innings DESC
LIMIT 15;


-- Q6. Toss winner vs match winner
-- Technique: CASE, aggregation
SELECT
    CASE WHEN toss_winner = winner THEN 'Toss winner won match' ELSE 'Toss winner lost match' END AS outcome,
    COUNT(*) AS matches,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS pct
FROM matches
WHERE winner IS NOT NULL
GROUP BY CASE WHEN toss_winner = winner THEN 'Toss winner won match' ELSE 'Toss winner lost match' END;


-- Q7. Batting first vs chasing — win % league-wide
-- Technique: CTE identifying who batted first from ball-by-ball data, CASE, aggregation
WITH bat_first AS (
    SELECT match_id, batting_team AS bat_first_team
    FROM deliveries
    WHERE inning = 1
    GROUP BY match_id, batting_team
)
SELECT
    CASE WHEN m.winner = b.bat_first_team THEN 'Batting first' ELSE 'Chasing' END AS strategy,
    COUNT(*) AS matches_won,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS pct
FROM matches m
JOIN bat_first b ON b.match_id = m.id
WHERE m.winner IS NOT NULL
GROUP BY CASE WHEN m.winner = b.bat_first_team THEN 'Batting first' ELSE 'Chasing' END;


-- Q8. Top run-scorer for each season
-- Technique: window function ROW_NUMBER over PARTITION BY, CTE
WITH season_runs AS (
    SELECT
        m.season,
        d.batter,
        SUM(d.batsman_runs) AS runs
    FROM deliveries d
    JOIN matches m ON m.id = d.match_id
    GROUP BY m.season, d.batter
),
ranked AS (
    SELECT
        season, batter, runs,
        ROW_NUMBER() OVER (PARTITION BY season ORDER BY runs DESC) AS rn
    FROM season_runs
)
SELECT season, batter, runs
FROM ranked
WHERE rn = 1
ORDER BY season;


-- Q9. Best economy rate (bowlers with at least 300 balls bowled — roughly 50 overs)
-- Technique: HAVING on an aggregate, subquery-free version of a min-sample-size filter
SELECT
    d.bowler,
    SUM(CASE WHEN d.extras_type NOT IN ('wides','noballs') OR d.extras_type IS NULL THEN 1 ELSE 0 END) AS legal_balls,
    ROUND(SUM(d.total_runs) * 6.0 / NULLIF(SUM(CASE WHEN d.extras_type NOT IN ('wides','noballs') OR d.extras_type IS NULL THEN 1 ELSE 0 END), 0), 2) AS economy
FROM deliveries d
GROUP BY d.bowler
HAVING SUM(CASE WHEN d.extras_type NOT IN ('wides','noballs') OR d.extras_type IS NULL THEN 1 ELSE 0 END) >= 300
ORDER BY economy ASC
LIMIT 10;


-- Q10. Most consistent batters (low variance relative to their own average, min 20 innings)
-- Technique: subquery for per-innings runs, STDDEV/AVG aggregation, HAVING
WITH per_innings AS (
    SELECT d.match_id, d.inning, d.batter, SUM(d.batsman_runs) AS runs
    FROM deliveries d
    GROUP BY d.match_id, d.inning, d.batter
)
SELECT
    batter,
    COUNT(*) AS innings,
    ROUND(AVG(runs), 2) AS avg_runs,
    ROUND(STDDEV(runs), 2) AS runs_stddev,
    ROUND(STDDEV(runs) / NULLIF(AVG(runs), 0), 2) AS coefficient_of_variation
FROM per_innings
GROUP BY batter
HAVING COUNT(*) >= 20
ORDER BY coefficient_of_variation ASC
LIMIT 15;


-- Q11. Top 3 run-scorers within each season (not just #1 — RANK, handles ties)
-- Technique: RANK() OVER PARTITION BY, filtering ranked results in an outer query
WITH season_runs AS (
    SELECT m.season, d.batter, SUM(d.batsman_runs) AS runs
    FROM deliveries d
    JOIN matches m ON m.id = d.match_id
    GROUP BY m.season, d.batter
),
ranked AS (
    SELECT season, batter, runs, RANK() OVER (PARTITION BY season ORDER BY runs DESC) AS season_rank
    FROM season_runs
)
SELECT season, season_rank, batter, runs
FROM ranked
WHERE season_rank <= 3
ORDER BY season, season_rank;


-- Q12. Venue-wise chasing success rate
-- Technique: CTE + JOIN + GROUP BY, mirrors Q7 but sliced by venue
WITH bat_first AS (
    SELECT match_id, batting_team AS bat_first_team
    FROM deliveries WHERE inning = 1
    GROUP BY match_id, batting_team
)
SELECT
    m.venue,
    COUNT(*) AS matches,
    SUM(CASE WHEN m.winner != b.bat_first_team THEN 1 ELSE 0 END) AS chases_won,
    ROUND(SUM(CASE WHEN m.winner != b.bat_first_team THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS chase_win_pct
FROM matches m
JOIN bat_first b ON b.match_id = m.id
WHERE m.winner IS NOT NULL
GROUP BY m.venue
HAVING COUNT(*) >= 10
ORDER BY chase_win_pct DESC;


-- Q13. Powerplay performance by team (overs 1-6, i.e. over_no 0-5)
-- Technique: WHERE range filter, GROUP BY, aggregation
SELECT
    d.batting_team,
    ROUND(SUM(d.total_runs) * 1.0 / COUNT(DISTINCT d.match_id || '-' || d.inning), 2) AS avg_powerplay_runs,
    SUM(d.is_wicket) AS wickets_lost,
    ROUND(SUM(d.total_runs) * 6.0 / NULLIF(SUM(CASE WHEN d.extras_type NOT IN ('wides','noballs') OR d.extras_type IS NULL THEN 1 ELSE 0 END), 0), 2) AS powerplay_run_rate
FROM deliveries d
WHERE d.over_no BETWEEN 0 AND 5
GROUP BY d.batting_team
ORDER BY powerplay_run_rate DESC;


-- Q14. Death-overs performance by team (overs 16-20, i.e. over_no 15-19)
-- Technique: same shape as Q13, different WHERE range — pairs with it for a powerplay-vs-death comparison
SELECT
    d.batting_team,
    ROUND(SUM(d.total_runs) * 1.0 / COUNT(DISTINCT d.match_id || '-' || d.inning), 2) AS avg_death_overs_runs,
    SUM(d.is_wicket) AS wickets_lost,
    ROUND(SUM(d.total_runs) * 6.0 / NULLIF(SUM(CASE WHEN d.extras_type NOT IN ('wides','noballs') OR d.extras_type IS NULL THEN 1 ELSE 0 END), 0), 2) AS death_overs_run_rate
FROM deliveries d
WHERE d.over_no BETWEEN 15 AND 19
GROUP BY d.batting_team
ORDER BY death_overs_run_rate DESC;


-- Q15. Player performance trend — season-over-season change in runs (LAG)
-- Technique: window function LAG() for year-over-year comparison
WITH season_runs AS (
    SELECT m.season, d.batter, SUM(d.batsman_runs) AS runs
    FROM deliveries d
    JOIN matches m ON m.id = d.match_id
    GROUP BY m.season, d.batter
)
SELECT
    season,
    batter,
    runs,
    LAG(runs) OVER (PARTITION BY batter ORDER BY season) AS prev_season_runs,
    runs - LAG(runs) OVER (PARTITION BY batter ORDER BY season) AS change_vs_prev_season
FROM season_runs
ORDER BY batter, season;


-- Q16. Closest matches (by run margin) — narrow-margin games as a proxy for "competitive" cricket
-- Technique: WHERE, CASE, ORDER BY, LIMIT
SELECT
    season, match_date, team1, team2, venue, winner,
    result, result_margin,
    CASE WHEN result = 'runs' THEN CONCAT(result_margin, ' runs')
         WHEN result = 'wickets' THEN CONCAT(result_margin, ' wickets')
         ELSE result END AS margin_description
FROM matches
WHERE result = 'runs' AND result_margin IS NOT NULL
ORDER BY result_margin ASC
LIMIT 10;


-- Q17. Player-of-the-match leaderboard
-- Technique: GROUP BY, ORDER BY, simple aggregation — a good "easy" interview warm-up query
SELECT
    player_of_match,
    COUNT(*) AS awards
FROM matches
WHERE player_of_match IS NOT NULL
GROUP BY player_of_match
ORDER BY awards DESC
LIMIT 10;


-- Q18. Toss decision breakdown by venue (does the toss-winning captain usually bat or field here?)
-- Technique: GROUP BY two columns, CASE-based pivot-style aggregation
SELECT
    venue,
    SUM(CASE WHEN toss_decision = 'bat' THEN 1 ELSE 0 END) AS chose_to_bat,
    SUM(CASE WHEN toss_decision = 'field' THEN 1 ELSE 0 END) AS chose_to_field,
    ROUND(SUM(CASE WHEN toss_decision = 'field' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS field_first_pct
FROM matches
GROUP BY venue
HAVING COUNT(*) >= 10
ORDER BY field_first_pct DESC;


-- Q19. Bowlers with the best strike rate against a specific team (correlated subquery)
-- Technique: correlated subquery in WHERE, JOIN, GROUP BY — swap the team name to reuse
SELECT
    d.bowler,
    COUNT(*) AS wickets,
    (SELECT COUNT(*) FROM deliveries d2
     WHERE d2.bowler = d.bowler
       AND d2.bowling_team != d.bowling_team   -- against the opposition batting team
       AND (d2.extras_type NOT IN ('wides','noballs') OR d2.extras_type IS NULL)
    ) AS career_balls_bowled_elsewhere   -- illustrative correlated subquery; swap in a real filter as needed
FROM deliveries d
WHERE d.is_wicket = 1
  AND d.dismissal_kind IN ('caught','bowled','lbw','stumped','caught and bowled','hit wicket')
  AND d.batting_team = 'Mumbai Indians'      -- edit to the team you're scouting against
GROUP BY d.bowler
ORDER BY wickets DESC
LIMIT 10;


-- Q20. Team head-to-head record (self-join on matches)
-- Technique: self-JOIN-free UNION approach + CASE, a very common interview ask ("show me how two teams have done against each other")
SELECT
    team1 AS team_a,
    team2 AS team_b,
    COUNT(*) AS matches_played,
    SUM(CASE WHEN winner = team1 THEN 1 ELSE 0 END) AS team_a_wins,
    SUM(CASE WHEN winner = team2 THEN 1 ELSE 0 END) AS team_b_wins
FROM matches
WHERE (team1 = 'Chennai Super Kings' AND team2 = 'Mumbai Indians')
   OR (team1 = 'Mumbai Indians' AND team2 = 'Chennai Super Kings')   -- edit teams to any rivalry
GROUP BY team1, team2;
