# Power BI Dashboard — Data Model, DAX & Layout Spec

This is everything needed to rebuild the dashboard in Power BI Desktop: the
data model, every DAX measure (with what it does and where it's used), and
an exact page-by-page layout. A `.pbix` can't be generated outside Power BI
Desktop itself, so this document *is* the source of truth — follow it top to
bottom and the dashboard comes out the same way every time.

---

## 1. Data model

Import three tables (Get Data → Text/CSV, or point at `outputs/tables/` from
the Python pipeline once you've run it):

| Table | Grain | Source |
|---|---|---|
| **Matches** | 1 row per match | `data/matches.csv` (or `outputs/tables/match_level.csv`, which already has `bat_first_team` computed for you) |
| **Deliveries** | 1 row per ball | `data/deliveries.csv` |
| **TeamMatches** | 1 row per team *per* match (bridge table) | built in Power Query — see below |

### Why a bridge table (`TeamMatches`)

`Matches` has team names spread across two columns (`team1`, `team2`), which
Power BI can't slice cleanly with a single "Team" slicer. The fix — the same
one used in `sql/analysis_queries.sql` (Q3/Q4's `UNION ALL` CTE) — is to
unpivot it into one row per team per match.

**Power Query steps** (Home → Append Queries → New Source is Matches, twice):
1. Reference `Matches` twice → name the copies `Matches_AsTeam1`, `Matches_AsTeam2`.
2. In `Matches_AsTeam1`: rename `team1` → `Team`, `team2` → `Opponent`.
3. In `Matches_AsTeam2`: rename `team2` → `Team`, `team1` → `Opponent`.
4. Add a custom column in both: `is_winner = [Team] = [winner]`,
   `is_toss_winner = [Team] = [toss_winner]`,
   `is_bat_first = [Team] = [bat_first_team]` (needs `bat_first_team` — either
   bring it in from `match_level.csv`, or compute it in Power Query from
   `Deliveries` first-inning batting team per `match_id`).
5. `is_chasing = NOT [is_bat_first]`.
6. Append `Matches_AsTeam1` + `Matches_AsTeam2` → this is `TeamMatches`.

### Relationships
- `Matches[id]` **1 → \*** `Deliveries[match_id]`
- `Matches[id]` **1 → \*** `TeamMatches[id]` (each match appears twice in `TeamMatches`, once per team)
- Mark `Matches` as a Date table on `match_date` if you want time-intelligence visuals (season-over-season trend lines); otherwise a plain `season` slicer is enough for this project.

---

## 2. DAX measures

| Measure | DAX | What it calculates | Used on |
|---|---|---|---|
| **Total Runs** | `Total Runs = SUM(Deliveries[total_runs])` | All runs scored (bat + extras) in the current filter context | Page 1 KPI card, Page 2 batting visuals |
| **Total Wickets** | `Total Wickets = CALCULATE(COUNTROWS(Deliveries), Deliveries[is_wicket] = 1, Deliveries[dismissal_kind] IN {"caught","bowled","lbw","stumped","caught and bowled","hit wicket"})` | Wickets credited to a bowler (run-outs excluded) | Page 1 KPI, Page 2 bowling visuals |
| **Balls Faced** (supporting) | `Balls Faced = CALCULATE(COUNTROWS(Deliveries), Deliveries[extras_type] <> "wides" \|\| ISBLANK(Deliveries[extras_type]))` | Legal balls a batter faced (wides excluded, no-balls included) | Feeds Strike Rate |
| **Legal Balls Bowled** (supporting) | `Legal Balls Bowled = CALCULATE(COUNTROWS(Deliveries), Deliveries[extras_type] <> "wides" \|\| ISBLANK(Deliveries[extras_type]), Deliveries[extras_type] <> "noballs")` | Balls that count toward the bowler's over allotment | Feeds Economy Rate |
| **Matches Played** | `Matches Played = DISTINCTCOUNT(TeamMatches[id])` | Matches a team appeared in (context-filtered by `TeamMatches[Team]`) | Page 1 & 4 KPI |
| **Matches Won** | `Matches Won = CALCULATE(DISTINCTCOUNT(TeamMatches[id]), TeamMatches[is_winner] = TRUE())` | Matches a team won | Page 1 & 4 |
| **Win %** | `Win % = DIVIDE([Matches Won], [Matches Played], 0)` | Win rate for the selected team(s)/season | Page 1 team comparison, Page 4 |
| **Batting Average** | `Batting Average = DIVIDE([Total Runs], CALCULATE(COUNTROWS(Deliveries), Deliveries[is_wicket]=1), BLANK())` | Runs per dismissal, in the current batter/season filter context | Page 2 batting table |
| **Strike Rate** | `Strike Rate = DIVIDE([Total Runs], [Balls Faced]) * 100` | Runs per 100 balls faced | Page 2 batting table, Page 4 |
| **Economy Rate** | `Economy Rate = DIVIDE(SUM(Deliveries[total_runs]), [Legal Balls Bowled]) * 6` | Runs conceded per over | Page 2 bowling table, Page 4 |
| **Sixes** | `Sixes = CALCULATE(COUNTROWS(Deliveries), Deliveries[batsman_runs] = 6)` | Six count | Page 2 |
| **Fours** | `Fours = CALCULATE(COUNTROWS(Deliveries), Deliveries[batsman_runs] = 4)` | Four count | Page 2 |
| **Average Score** | `Average Score = DIVIDE([Total Runs], DISTINCTCOUNT(Deliveries[match_id] & "-" & Deliveries[inning]), BLANK())` | Average runs per completed innings | Page 1 KPI |
| **Chasing Win %** | `Chasing Win % = DIVIDE(CALCULATE(DISTINCTCOUNT(TeamMatches[id]), TeamMatches[is_winner]=TRUE(), TeamMatches[is_chasing]=TRUE()), CALCULATE(DISTINCTCOUNT(TeamMatches[id]), TeamMatches[is_chasing]=TRUE()), 0)` | Win % when batting second | Page 3 match strategy |
| **Toss Win %** | `Toss Win % = DIVIDE(CALCULATE(DISTINCTCOUNT(TeamMatches[id]), TeamMatches[is_toss_winner]=TRUE()), [Matches Played], 0)` | How often the selected team wins the toss | Page 3 |
| **Toss → Match Win %** | `Toss To Match Win % = DIVIDE(CALCULATE(DISTINCTCOUNT(TeamMatches[id]), TeamMatches[is_toss_winner]=TRUE(), TeamMatches[is_winner]=TRUE()), CALCULATE(DISTINCTCOUNT(TeamMatches[id]), TeamMatches[is_toss_winner]=TRUE()), 0)` | Of the times a team won the toss, how often it also won the match | Page 3 |

No other DAX is needed — every visual on every page is one of these
measures plus a field from `Matches`, `TeamMatches`, or `Deliveries` used as
the axis/legend/filter.

---

## 3. Page-by-page layout

Canvas: 1280×720, dark cricket-green (`#0B3D2E`) header band, white
canvas background, one accent color per team where possible (or a single
accent — `#D4AF37` gold — if you'd rather not maintain a 10-team color
table).

### Page 1 — IPL Overview
- **Top band (4 KPI cards, left to right):** Matches Played (unfiltered = total matches), Total Runs, Total Wickets, Average Score.
- **Top-right corner:** two small cards — Total Teams, Total Seasons (both `DISTINCTCOUNT`, no custom measure needed).
- **Left half, mid-page:** clustered column chart — Runs by Season (`Matches[season]` on axis, `Total Runs` as value).
- **Right half, mid-page:** bar chart — Wins by Team (`TeamMatches[Team]` on axis, `Matches Won` as value, sorted descending, top 10).
- **Bottom band:** line chart — Season trend of `Average Score` by `Matches[season]`, so the overview page tells one story top (totals) to bottom (trend) without needing to flip pages.
- **Slicer (top-left, always visible):** Season range slider.

### Page 2 — Batsman & Bowler Analytics
- **Left column:** a table/matrix visual on `Deliveries[batter]` with `Total Runs`, `Strike Rate`, `Batting Average`, `Fours`, `Sixes` — sorted by Total Runs descending, top 15 (use a Top N filter).
- **Right column:** the bowling mirror — matrix on `Deliveries[bowler]` with `Total Wickets`, `Economy Rate`, sorted by Wickets, top 15.
- **Bottom-left:** scatter chart, Batting Average (x) vs Strike Rate (y), bubble size = Total Runs — this is the same "who's both consistent and fast" question as SQL Q10 and the notebook's strike-rate-vs-average plot.
- **Bottom-right:** clustered bar — Economy Rate for the top 10 wicket-takers, so form and economy sit side by side.
- **Slicers (top of page):** Player (searchable list, applies to both tables via the shared `Deliveries` table), Season.

### Page 3 — Match Strategy
- **Top band, 3 KPI cards:** Toss → Match Win % (league-wide, no team filter), Chasing Win %, Batting-First Win % (`1 - [Chasing Win %]` computed inline or as its own trivial measure).
- **Left:** donut chart — Toss winner also won vs didn't (same split as SQL Q6).
- **Right:** bar chart — `Chasing Win %` by `Matches[venue]` (top 15 venues by match count) — this is the venue-specific "should I bat or bowl here" signal, same as SQL Q12.
- **Bottom:** stacked column — Powerplay / Middle / Death average run rate by team (needs a `phase` column on `Deliveries`, computed in Power Query exactly like `deliveries["phase"]` in the Python script — same `over_no` bucketing: 0–5 / 6–14 / 15–19).
- **Slicers:** Venue, Season, Toss Decision (bat/field).

### Page 4 — Player / Team Deep Dive
- **Top-left, 4 slicers in a row:** Team, Player, Season, Venue — these drive everything else on the page.
- **KPI card row:** Matches Played, Win %, and (if a single player is selected) Strike Rate / Economy Rate side by side — Power BI will just blank out whichever doesn't apply given the selection, which is fine.
- **Main visual:** a matrix with `Matches[season]` on rows and the selected team/player's key measures on columns, so drilling from "career" down to "this season" is one click.
- **Small multiples row at the bottom:** repeat the Page 1 "Runs by Season" visual, but filtered to the current selection, so this page reads as "everything from page 1, but just for the team/player I picked."

### General dashboard rules
- One consistent color per team across **every** page (define it once in a small `Team Colors` table and use conditional formatting / a legend, rather than letting Power BI auto-assign colors that shift between pages).
- Every table/matrix gets a Top N filter (10–15 rows) — nobody wants to scroll a 700-row batting table.
- Tooltips: use the default detail tooltip on every chart, plus one custom tooltip page on the Page 3 venue chart showing `Matches`, `Avg Target`, `Chasing Win %` together (this is the single visual most likely to come up in an interview walkthrough, so it's worth the extra polish).
- Keep drill-down to `Season → Match` (not down to individual deliveries — that's what the Python/notebook EDA is for, the dashboard is deliberately the *summarized* view).
