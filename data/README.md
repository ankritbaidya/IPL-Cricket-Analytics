# Data folder

This folder is where the two source CSV files go. They are **not committed to
the repo** (see root `.gitignore`) because of size and because Kaggle asks
downloaders to get the file from Kaggle directly rather than have it
re-hosted — you grab it once, for free, in about 2 minutes.

## Dataset

**IPL Complete Dataset (2008–2024)** — the standard, widely-used IPL dataset
for analytics projects like this one.

- **Source / download:** https://www.kaggle.com/datasets/patrickb1912/ipl-complete-dataset-20082020
- **Underlying data provider:** [Cricsheet](https://cricsheet.org) (the
  original ball-by-ball source; the Kaggle upload just packages it as two
  clean CSVs)
- **License:** Kaggle lists no extra restriction beyond Cricsheet's own terms.
  Cricsheet data is free to use for personal/research/educational purposes
  with attribution — credit **"Data: Cricsheet (cricsheet.org), packaged via
  Kaggle — IPL Complete Dataset (2008–2024) by patrickb1912"** wherever you
  publish results (the README below already does this for you).
- **How to download:** you need a free Kaggle account. Go to the link above →
  "Download" → unzip → you'll get `matches.csv` and `deliveries.csv`. Drop
  both directly into this `data/` folder.

## Files and columns

### `matches.csv` — one row per match (1,095 rows, 20 columns)

| Column | Description |
|---|---|
| `id` | Unique match ID (joins to `deliveries.match_id`) |
| `season` | IPL season, e.g. `2023` |
| `city` | City the match was played in |
| `date` | Match date |
| `match_type` | Usually `League`, also `Qualifier`, `Final`, etc. |
| `player_of_match` | Player of the match |
| `venue` | Stadium name |
| `team1`, `team2` | The two competing teams |
| `toss_winner` | Team that won the toss |
| `toss_decision` | `bat` or `field` |
| `winner` | Match-winning team |
| `result` | `normal`, `tie`, `no result` |
| `result_margin` | Margin of victory (runs or wickets, see `result`) |
| `target_runs`, `target_overs` | Chase target, when applicable |
| `super_over` | Whether the match went to a super over |
| `method` | `D/L` if Duckworth-Lewis applied, else blank |
| `umpire1`, `umpire2` | On-field umpires |

### `deliveries.csv` — one row per ball bowled (~260,000 rows, 17 columns)

| Column | Description |
|---|---|
| `match_id` | Joins to `matches.id` |
| `inning` | 1 or 2 (3/4 for super overs) |
| `batting_team`, `bowling_team` | Teams for this delivery |
| `over`, `ball` | Over number (0-indexed) and ball-in-over |
| `batter` | Batter facing the ball |
| `bowler` | Bowler delivering the ball |
| `non_striker` | Batter at the non-striker's end |
| `batsman_runs` | Runs credited to the batter off this ball |
| `extra_runs` | Extra runs (wide/no-ball/bye/leg-bye) |
| `total_runs` | `batsman_runs + extra_runs` |
| `extras_type` | Type of extra, if any |
| `is_wicket` | 1 if a wicket fell on this ball |
| `player_dismissed` | Player out, if `is_wicket == 1` |
| `dismissal_kind` | How they were out |
| `fielder` | Fielder involved in the dismissal, if applicable |

Everything downstream (`python/ipl_analysis.py`, the SQL schema, the Power BI
model) is written against these exact column names, so once the two files are
in this folder the whole pipeline runs end to end with no edits needed.
