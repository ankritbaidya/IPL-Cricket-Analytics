-- ============================================================================
-- IPL Cricket Analytics — Schema
-- Target: MySQL 8+ / PostgreSQL 13+ (both are commented where syntax differs)
-- ============================================================================

CREATE DATABASE IF NOT EXISTS ipl_analytics;   -- MySQL
-- PostgreSQL: CREATE DATABASE ipl_analytics;  then \c ipl_analytics
USE ipl_analytics;                             -- MySQL only; Postgres uses \c above

DROP TABLE IF EXISTS deliveries;
DROP TABLE IF EXISTS matches;

-- ----------------------------------------------------------------------------
-- matches: one row per match
-- ----------------------------------------------------------------------------
CREATE TABLE matches (
    id                INT PRIMARY KEY,
    season            INT           NOT NULL,
    city              VARCHAR(100),
    match_date        DATE,
    match_type        VARCHAR(30),
    player_of_match   VARCHAR(100),
    venue             VARCHAR(150),
    team1             VARCHAR(60)   NOT NULL,
    team2             VARCHAR(60)   NOT NULL,
    toss_winner       VARCHAR(60),
    toss_decision     VARCHAR(10),   -- 'bat' | 'field'
    winner            VARCHAR(60),
    result            VARCHAR(20),   -- 'normal' | 'tie' | 'no result'
    result_margin     INT,
    target_runs       INT,
    target_overs      DECIMAL(4,1),
    super_over        VARCHAR(3),
    method            VARCHAR(10),   -- 'D/L' or NULL
    umpire1           VARCHAR(60),
    umpire2           VARCHAR(60)
);

-- ----------------------------------------------------------------------------
-- deliveries: one row per ball bowled
-- ----------------------------------------------------------------------------
CREATE TABLE deliveries (
    match_id          INT           NOT NULL,
    inning            TINYINT       NOT NULL,
    batting_team      VARCHAR(60)   NOT NULL,
    bowling_team      VARCHAR(60)   NOT NULL,
    over_no           TINYINT       NOT NULL,   -- 'over' is a reserved word in some engines
    ball_no           TINYINT       NOT NULL,   -- 'ball' likewise avoided
    batter            VARCHAR(100),
    bowler            VARCHAR(100),
    non_striker       VARCHAR(100),
    batsman_runs      TINYINT       NOT NULL DEFAULT 0,
    extra_runs        TINYINT       NOT NULL DEFAULT 0,
    total_runs        TINYINT       NOT NULL DEFAULT 0,
    extras_type       VARCHAR(20),
    is_wicket         TINYINT       NOT NULL DEFAULT 0,
    player_dismissed  VARCHAR(100),
    dismissal_kind    VARCHAR(30),
    fielder           VARCHAR(100),
    CONSTRAINT fk_deliveries_match FOREIGN KEY (match_id) REFERENCES matches(id)
);

CREATE INDEX idx_deliveries_match   ON deliveries(match_id);
CREATE INDEX idx_deliveries_batter  ON deliveries(batter);
CREATE INDEX idx_deliveries_bowler  ON deliveries(bowler);
CREATE INDEX idx_matches_season     ON matches(season);
CREATE INDEX idx_matches_venue      ON matches(venue);

-- ----------------------------------------------------------------------------
-- Loading the CSVs (after downloading them into data/ — see data/README.md)
-- ----------------------------------------------------------------------------

-- MySQL (run from the mysql client, adjust the path to wherever the CSVs live;
-- local_infile must be enabled on both client and server):
-- LOAD DATA LOCAL INFILE 'matches.csv'
--   INTO TABLE matches
--   FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
--   LINES TERMINATED BY '\n'
--   IGNORE 1 ROWS
--   (id, season, city, @date, match_type, player_of_match, venue, team1, team2,
--    toss_winner, toss_decision, winner, result, result_margin, target_runs,
--    target_overs, super_over, method, umpire1, umpire2)
--   SET match_date = NULLIF(@date, '');
--
-- LOAD DATA LOCAL INFILE 'deliveries.csv'
--   INTO TABLE deliveries
--   FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"'
--   LINES TERMINATED BY '\n'
--   IGNORE 1 ROWS
--   (match_id, inning, batting_team, bowling_team, over_no, ball_no, batter,
--    bowler, non_striker, batsman_runs, extra_runs, total_runs, extras_type,
--    is_wicket, player_dismissed, dismissal_kind, fielder);

-- PostgreSQL (run from psql in the same directory as the CSVs):
-- \copy matches   FROM 'matches.csv'    DELIMITER ',' CSV HEADER;
-- \copy deliveries FROM 'deliveries.csv' DELIMITER ',' CSV HEADER;
-- (rename the CSV's 'over'/'ball' header cells to over_no/ball_no first, or
--  load into a staging table with the original names and INSERT...SELECT across.)

-- If you'd rather not fight CSV-loader quirks, the Python pipeline already
-- exports load-ready tables to outputs/tables/ — point LOAD DATA / \copy at
-- those instead; column names match this schema exactly.
