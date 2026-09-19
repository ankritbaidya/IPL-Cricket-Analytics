# Interview Prep — IPL Cricket Performance & Strategy Analytics

Every answer below is written against the actual design decisions in this
project (the schema, the DAX, the cleaning rules) — not generic cricket
trivia. The pitches and headline numbers are already filled in from a real
run of the pipeline on the full 2008–2024 dataset.

---

## 60-second explanation

"I built an end-to-end analytics project on IPL cricket — 17 seasons, about
260,000 ball-by-ball deliveries across 1,095 matches. I took the raw
Cricsheet-sourced data, cleaned it — handled franchise renames like Delhi
Daredevils to Delhi Capitals, recovered missing city values, normalized
inconsistent season labels — then engineered metrics pandas doesn't give you
for free: strike rate, economy rate, and phase-wise scoring split into
powerplay, middle overs, and death overs. I answered a fixed set of strategy
questions — does the toss matter, is chasing better than batting first,
which venues favor which strategy — in Python for the exploratory analysis,
then again in SQL with 20 queries using joins, CTEs, and window functions, so
I could cross-check that both answers agreed. On top of that I built a
4-page Power BI dashboard so someone without a Python or SQL background could
explore the same patterns interactively. The throughline across all of it:
several 'obvious' cricket beliefs are correlations in historical data, not
settled facts, and I was deliberate about not overstating them."

## 2-minute detailed explanation

"The project starts from two CSVs — a match-level file and a ball-by-ball
file, about 260,000 rows — sourced from Cricsheet and covering all 17 IPL
seasons. Before touching the data I ran a proper inspection pass: shape,
dtypes, missing-value percentages, duplicates. That surfaced a few real
issues — a handful of matches missing city (recoverable from the venue),
franchise names that changed over the years (Delhi Daredevils became Delhi
Capitals, Kings XI Punjab became Punjab Kings), and season labels stored
inconsistently. I fixed those with explicit, documented rules rather than
dropping rows.

From there I engineered the features the raw data doesn't give you directly
— batting strike rate and average, bowling economy and strike rate, and a
phase tag (Powerplay/Middle/Death) on every single delivery, which lets me
ask questions like 'does this team's powerplay strategy correlate with
winning' at the row level. For team strategy, the trickiest bit was
determining who actually batted first — I read that straight from the
ball-by-ball data's first-innings batting team rather than trying to reason
it out from the toss decision, which is a much easier way to get it
backwards than people expect.

I then answered the same set of questions two ways: once in Python/pandas
for the exploratory charts, and once in SQL — 20 queries covering CTEs,
window functions like RANK and LAG, and a correlated subquery — specifically
so I'd catch it if my pandas logic and my SQL logic ever disagreed. On top of
both, I built a 4-page Power BI dashboard. The interesting modeling problem
there was that the raw match data stores teams in two separate columns —
team1 and team2 — which doesn't slice cleanly with a single team filter, so
I unpivoted it into a bridge table, the same logic as the SQL UNION ALL
pattern I'd already written.

The headline findings — the toss winner also won the match in just 50.6% of
games, basically a coin flip, and teams won 53.9% of the time chasing vs.
45.7% batting first — are things I'm careful to frame as associations in
historical data, not proof of cause and effect, both in the README and out
loud when I talk about it."

---

## 20 technical / project questions

1. **Why IPL, and why this dataset?**
   It's large enough (260K+ deliveries) to support real aggregation and
   window-function work, has a clean two-table structure that maps directly
   to a normalized SQL schema, and — unlike a lot of tutorial datasets — has
   real messiness (franchise renames, missing cities) worth cleaning
   properly instead of glossing over.

2. **Walk me through your pipeline end to end.**
   Load → inspect (shape/dtypes/nulls/duplicates) → clean (documented rules,
   not blind drops) → feature engineer (strike rate, economy, phase tags,
   batting-first/chasing) → EDA (10 charts) → export tidy tables → the same
   questions re-answered in SQL → Power BI on top of the same model.

3. **How did you handle missing data? Give an example.**
   `city` is null for a few neutral-venue matches. Instead of dropping those
   rows, I built a venue→city lookup from every other row sharing that
   venue and filled from that, keeping the match in every downstream
   aggregation.

4. **How did you handle duplicate data?**
   `matches` deduped on `id`; `deliveries` deduped on full-row duplicates,
   after inspecting `.duplicated().sum()` first rather than assuming.

5. **Why did you rename some franchises but not others?**
   Delhi Daredevils→Delhi Capitals and Kings XI Punjab→Punjab Kings are
   genuine same-entity rebrands. Deccan Chargers, Pune Warriors, and
   Gujarat Lions are defunct franchises with no later legal continuation, so
   merging them into a "successor" would misattribute history — I kept them
   separate on purpose.

6. **How did you define Powerplay/Middle/Death overs, and why those cutoffs?**
   Overs 1–6 / 7–15 / 16–20 (0-indexed 0–5 / 6–14 / 15–19) — the standard T20
   convention, chosen so the phase tags mean the same thing to anyone who
   already follows cricket, not a cutoff I invented.

7. **How is "who batted first" determined — why not just use `toss_decision`?**
   I read it directly from `deliveries` (the inning-1 batting team) instead
   of inferring it from `toss_winner` + `toss_decision`, because getting that
   inference backwards (does "field" mean the toss winner bats or bowls
   first?) is an easy, silent bug — ground truth from the ball-by-ball data
   sidesteps it entirely.

8. **Why exclude wides from balls faced but include no-balls?**
   A batter doesn't face a wide — it doesn't count as a delivery to them —
   but they do face a no-ball and can score off it, so it counts toward
   strike rate's denominator the same way a normal ball does.

9. **Why exclude run-outs from bowler wicket counts?**
   A run-out isn't a wicket the bowler earned — crediting it to them would
   inflate bowling figures for bowlers whose fielders happen to be sharp.

10. **What's a "qualified" batter/bowler and why set a minimum-balls cutoff?**
    Leaderboards on rate stats (strike rate, economy) are dominated by
    small samples otherwise — one player with 6 balls and a six looks like
    the best striker in the league. The cutoff (e.g. 200 balls faced / 300
    balls bowled) is a judgment call, stated explicitly rather than hidden.

11. **How did you validate your Python numbers were correct?**
    By re-deriving the same aggregates in SQL independently and comparing —
    if pandas says a team's win % is X and the SQL CTE says something
    different, that's a bug in one of them, not two acceptable answers.

12. **What would you do differently with more time?**
    A simple win-probability model (logistic regression on toss, venue,
    bat/chase) as a natural next step past descriptive EDA — see
    `README.md`'s Future Improvements section.

13. **How did you decide what to visualize vs. put in a table?**
    Distributions and comparisons (win % by team, run rate by phase) became
    charts; anything someone would want to look up a specific player/team
    value from (leaderboards) became a table/matrix, especially in Power BI
    where a table supports search and Top-N filtering a chart doesn't.

14. **Talk about a specific data-cleaning decision you had to make a judgment call on.**
    The franchise-rename mapping (see Q5) — there's no single "correct"
    answer for whether Delhi Daredevils and Delhi Capitals should be one
    row or two; I made the call explicitly and documented why, rather than
    leaving it implicit.

15. **How would this pipeline scale to next season's data automatically?**
    Re-running `ipl_analysis.py` against an updated CSV drop-in works as-is
    since nothing is hard-coded to a season list; the only manual step would
    be checking whether a season introduces a new franchise rename to add to
    `TEAM_NAME_MAP`.

16. **Correlation vs. causation in your toss finding — how did you communicate that?**
    Every toss-related sentence in the README and the script's own printed
    insights explicitly says "association, not causation" rather than
    "toss winners win because of the toss" — teams likely choose the
    decision that suits conditions they'd have wanted regardless.

17. **Why both Python EDA and SQL analysis — isn't that redundant?**
    It's a cross-check, not redundancy — the two are computed independently
    (different code, different tool) and are expected to agree; if they
    don't, that's a bug caught earlier than a stakeholder catching it.

18. **How did you structure your GitHub repo, and why?**
    Separated by tool/stage (`python/`, `sql/`, `powerbi/`, `notebooks/`)
    rather than by output type, so anyone reviewing the repo can go straight
    to the layer they care about without wading through the others.

19. **What testing did you do on the code itself, not just the output?**
    Ran the full pipeline (and every SQL query) against a small synthetic
    fixture with known structure before trusting it on the real 260K-row
    dataset, specifically to catch logic bugs (wrong join, wrong filter)
    that would otherwise hide inside a plausible-looking large-scale output.

20. **If a stakeholder asked "should we always bowl first," what would you tell them?**
    I'd show them the league-wide chase/defend split *and* the venue-level
    breakdown side by side — a league-wide number can reverse at a specific
    ground (dew, pitch behavior), so "always" is the wrong frame; "check
    this specific venue's history first" is the honest answer.

---

## 15 SQL questions

1. **Explain the CTE that unions `team1`/`team2` (Q3/Q4).**
   `matches` stores each team in a separate column per row; the CTE does
   `SELECT team1 AS team ... UNION ALL SELECT team2 AS team ...` to turn two
   columns into one, so a single `GROUP BY team` gives per-team stats.

2. **`RANK()` vs `ROW_NUMBER()` — where did you use each?**
   `ROW_NUMBER()` for "the #1 scorer per season" (Q8) where ties don't
   matter for a single winner; `RANK()` for "top 3 per season" (Q11), which
   correctly gives two players rank 1 if they're tied, rather than
   arbitrarily picking one as #1 and the other as #2.

3. **Walk through the `LAG()` query (Q15).**
   It computes each batter's season-over-season run change: `LAG(runs) OVER
   (PARTITION BY batter ORDER BY season)` pulls the *previous* row's value
   within that player's partition, so subtracting it from the current
   season's runs gives a trend, without a self-join.

4. **Why `HAVING` instead of `WHERE` in several queries?**
   `WHERE` filters rows before aggregation; `HAVING` filters after — the
   minimum-sample-size checks (e.g. `HAVING COUNT(*) >= 10`) depend on the
   aggregated count, which doesn't exist yet at the `WHERE` stage.

5. **What's a correlated subquery, and where did you use one (Q19)?**
   A subquery that references a column from the outer query (so it
   re-runs per outer row rather than once). Q19's inner `SELECT COUNT(*)
   FROM deliveries d2 WHERE d2.bowler = d.bowler ...` depends on the outer
   `d.bowler`, making it correlated rather than a one-shot subquery.

6. **Explain `SUM(COUNT(*)) OVER ()` used for percentage-of-total (Q6/Q7).**
   The inner `COUNT(*)` is the per-group count from the `GROUP BY`; wrapping
   it in a window `SUM(...) OVER ()` (no `PARTITION BY`) sums it back up
   across *all* groups, giving each row access to the grand total to divide
   into — without a second query or a self-join.

7. **Why index `match_id`, `batter`, `bowler`, `season`, `venue` specifically?**
   Those are exactly the columns every query in `analysis_queries.sql`
   joins or groups on — indexing the columns actually used in `JOIN`/`WHERE`
   /`GROUP BY` is the return on an index; indexing unused columns isn't.

8. **How would you get a batter's single highest score using window functions?**
   `ROW_NUMBER() OVER (PARTITION BY batter, match_id ORDER BY runs DESC)`
   on a per-innings runs table, then filter to rank 1 — same pattern as Q8,
   partitioned by player instead of by season.

9. **`INNER JOIN` vs `LEFT JOIN` — did you need a `LEFT JOIN` anywhere?**
   Every join in this project is `matches`↔`deliveries` on a guaranteed
   foreign key, so `INNER JOIN` is correct and complete — a `LEFT JOIN`
   would only matter if I needed matches with zero recorded deliveries to
   still show up, which isn't a real case in this dataset.

10. **Design a query for a team's running win total over a season.**
    `SUM(CASE WHEN winner = team THEN 1 ELSE 0 END) OVER (PARTITION BY
    team, season ORDER BY match_date ROWS UNBOUNDED PRECEDING)` on the
    `team_appearances` CTE — a running total via a window frame, same CTE
    as Q3/Q4 with a different window function on top.

11. **`COUNT(*)` vs `COUNT(column)` vs `COUNT(DISTINCT column)` — where does the distinction matter?**
    `COUNT(*)` counts rows regardless of nulls; `COUNT(column)` skips nulls
    in that column; `COUNT(DISTINCT match_id)` in Q5 specifically avoids
    counting the same match multiple times across its many delivery rows.

12. **Why avoid `SELECT *` throughout?**
    Naming columns explicitly makes every query self-documenting (you can
    read what it returns without running it) and avoids silently breaking
    if the table gains a column later.

13. **How would you find teams that have never won after winning the toss, using a subquery?**
    `SELECT DISTINCT team FROM team_appearances t WHERE NOT EXISTS (SELECT
    1 FROM matches m WHERE m.toss_winner = t.team AND m.winner = t.team)` —
    a `NOT EXISTS` anti-join pattern.

14. **What's the practical risk of not declaring the foreign key in `schema.sql`?**
    Without it, a bad `match_id` in `deliveries` (typo, bad load) would
    insert silently instead of being rejected — the FK is what turns a data
    entry mistake into an immediate, loud error instead of a quietly wrong
    join result three queries later.

15. **How would you optimize the highest-scoring-venues query at 50M rows?**
    Make sure `(venue)` and `(match_id)` are indexed (already are), consider
    a materialized/pre-aggregated summary table refreshed on load instead of
    aggregating 50M rows per dashboard refresh, and confirm the query plan
    isn't doing a full scan via `EXPLAIN` before assuming it's slow.

---

## 10 Python / Pandas questions

1. **Why `groupby().size()` vs `value_counts()` in different places?**
   `value_counts()` for a single column's frequency (e.g. matches per
   season); `groupby(...).size()`/`.agg()` when I need the count alongside
   other aggregates in the same table (runs, balls, dismissals together).

2. **Explain the `np.select()` call for phase tagging.**
   `np.select([condition_list], [choice_list], default=...)` evaluates each
   condition (is `over` in the Powerplay range? Middle? Death?) in order and
   assigns the matching label — a vectorized if/elif/elif across the whole
   column instead of a slow `.apply()` row loop.

3. **Why `fillna()` with a mapped value instead of `dropna()` for city?**
   Dropping those rows would silently remove real matches from every
   downstream team/venue aggregate; filling from a venue→city map keeps the
   match while fixing the specific missing field.

4. **`merge()` vs `join()` — you use both, why?**
   `.merge()` when joining on a column value (`deliveries.merge(matches[...],
   left_on="match_id", right_on="id")`); `.join()` when aligning on the
   index (`matches.join(bat_first_series, on="id")`) — same underlying
   operation, chosen for whichever is already indexed the right way.

5. **How does `.replace()` with a dict handle the franchise renames?**
   `df[col].replace(TEAM_NAME_MAP)` swaps any value matching a dict key for
   its value and leaves everything else untouched — applied to all four
   team-name columns (`team1`, `team2`, `toss_winner`, `winner`) so a rename
   can't create a mismatch between which column says the old name and which
   says the new one.

6. **Walk through strike rate step by step in pandas.**
   Filter to faced balls (`extras_type != "wides"`) → `groupby("batter")
   ["batsman_runs"].sum()` for runs → `groupby("batter").size()` for balls
   faced on the same filtered frame → `runs / balls * 100`.

7. **Why `matplotlib.use("Agg")` at the top of the script?**
   Forces the non-interactive backend so the script can save PNGs on a
   headless machine (a server, a CI runner, this sandbox) without needing a
   display — without it, `plt.savefig()` can fail or hang in some environments.

8. **What would break with inconsistent column casing, and how do you defend against it?**
   Every column reference in the script is a literal exact-case string, so
   `Over` instead of `over` would raise a `KeyError` immediately — loud and
   at the top of the script, rather than silently producing wrong numbers,
   which is the safer failure mode to design for.

9. **How do you avoid `SettingWithCopyWarning` in the cleaning functions?**
   Every clean function starts with `df = matches.copy()` / `deliveries.copy()`
   before mutating, so pandas isn't unsure whether it's a view or a copy of
   the original frame.

10. **If `deliveries.csv` were too large to fit in memory, how would you adapt this?**
    Switch the aggregation steps to chunked reads (`pd.read_csv(...,
    chunksize=...)`, accumulating partial groupby sums) or push the heavy
    aggregation into the SQL layer (which is already built) and have Python
    consume the aggregated result instead of every raw row.

---

## 10 Power BI / DAX questions

1. **Why a bridge table (`TeamMatches`) instead of two relationships with `USERELATIONSHIP`?**
   The bridge table is easier to reason about and to explain — one active
   relationship, one row per team per match, filters just work — versus
   juggling multiple inactive relationships and remembering to activate the
   right one in every single measure.

2. **`DIVIDE()` vs plain `/` in DAX?**
   `DIVIDE(a, b, alt)` returns a defined fallback (0 or blank) on a
   divide-by-zero instead of throwing an error — matters here because a
   team/season slice with zero matches is a completely normal filter state,
   not an edge case to special-case everywhere.

3. **Walk through the Win % measure.**
   `DIVIDE([Matches Won], [Matches Played], 0)` — both `[Matches Won]` and
   `[Matches Played]` are themselves measures using `CALCULATE` +
   `DISTINCTCOUNT` over `TeamMatches`, so `Win %` inherits whatever
   team/season/venue filters are active on the visual automatically.

4. **Calculated column vs. measure — where did you use each?**
   The `is_winner`/`is_toss_winner`/`is_chasing` flags on `TeamMatches` are
   calculated columns (fixed per row, computed once at refresh); everything
   that changes with the visual's filter context (`Win %`, `Economy Rate`)
   is a measure, computed on the fly.

5. **How does `CALCULATE()` change filter context in `Total Wickets`?**
   It layers the dismissal-type filter (`IN {"caught","bowled",...}`) on
   top of whatever filters the visual already applies (team, season,
   player), rather than replacing them — `CALCULATE` adds filters, it
   doesn't reset the context.

6. **Why compute `Toss Win %` as `CALCULATE(...)/[Matches Played]` rather than its own fully independent ratio?**
   Reusing `[Matches Played]` as the denominator keeps the definition of
   "played" consistent across every rate measure in the model — if that
   definition ever needs to change, it changes in one place.

7. **How would you add a "best economy rate this season" KPI that updates with slicers?**
   A measure like `MINX(VALUES(Deliveries[bowler]), [Economy Rate])` —
   evaluates `[Economy Rate]` per bowler in the current filter context and
   returns the smallest, so it responds to whatever season/team slicer is
   selected without a separate query per season.

8. **How does the Season slicer affect every page without per-page filter logic?**
   `Matches[season]` is the field the slicer is built on, and every visual
   on every page is ultimately filtered through the `Matches`→`Deliveries`/
   `TeamMatches` relationships — one slicer, propagated by the model, not
   four copies of the same filter logic.

9. **Ball-by-ball drill-down in Power BI vs. keeping it match/innings level — what's the tradeoff?**
   Ball-level detail is ~260K rows per season range, which is fine for
   aggregation but slow and unreadable as a literal table visual; the
   dashboard deliberately stops at match/innings granularity and leaves
   true ball-by-ball exploration to the Python notebook, which is the
   better tool for that anyway.

10. **How would you set up row-level security for multiple team analysts?**
    A DAX role filtering `TeamMatches[Team] = USERPRINCIPALNAME()` (or a
    mapping table from email to team), applied dynamically so each
    analyst's login only ever sees their own team's rows across every page,
    without maintaining separate dashboard copies.

---

## 10 Analytical / business questions

1. **Most actionable finding for a team's think tank?**
   The venue-level chase/defend split (Q12 / Page 3) — it's specific enough
   to change a real toss decision at a real ground, unlike a league-wide
   average that may not hold locally.

2. **How would a franchise use the venue-based signal practically?**
   As one input into the toss-decision conversation before a specific
   match at a specific ground — not a rule to follow blindly, but a
   data point alongside pitch report and dew forecast.

3. **Risk of over-trusting the toss-impact number?**
   Treating it as causal would lead a captain to think winning the toss
   guarantees an advantage worth chasing (bribing umpires, obsessing over
   coin-flip strategy) when the real lever is probably conditions and team
   strength, which the toss decision merely reflects.

4. **How would you test if a player is genuinely "clutch" in chases vs. just variance?**
   Compare their strike rate/average specifically in run-chase innings vs.
   their overall numbers, across enough innings that the gap isn't just a
   couple of lucky/unlucky games — and be upfront that even a real gap
   could still be small-sample noise without a few dozen chase innings.

5. **If one team's win % varies a lot season to season, how do you investigate why?**
   Break it down by the same cuts already in the model — toss-decision
   pattern that season, batting-first vs chasing split, powerplay/death
   run rate — to see whether the swing tracks a strategy change, a squad
   change, or just variance around a stable underlying win rate.

6. **How would you present this to a non-technical stakeholder in 2 minutes?**
   Skip the pipeline mechanics entirely and lead with the dashboard: "here's
   what actually predicts winning, and here's what looks predictive but
   isn't" — the toss finding is a strong opener because it's counter to
   popular belief and immediately memorable.

7. **What decision would you NOT make based on this analysis alone?**
   I wouldn't set a specific match's toss-decision strategy off the
   league-wide split alone — that decision needs the venue-specific number
   at minimum, and ideally pitch/weather data this project doesn't have.

8. **How would you get closer to causal toss impact, conceptually?**
   You can't randomize a coin toss's outcome, but you could compare
   otherwise-similar matches (same venue, similar team strength) where the
   toss decision differed, or look at whether the toss-decision *choice
   itself* correlates with conditions that independently predict winning —
   a natural-experiment framing rather than a true randomized one.

9. **What additional data would most improve the venue analysis?**
   Pitch reports and dew/weather data — right now the venue signal is
   purely behavioral (what teams did there), with no visibility into *why*
   a venue favors chasing (dew making the ball slide at night, e.g.).

10. **How do you handle a stakeholder who wants one dramatic headline number?**
    Give them the real number with the honest caveat attached in the same
    breath, rather than dropping the caveat to make the headline cleaner —
    a number that doesn't survive follow-up questions is worse for
    credibility than a slightly less punchy one that does.

---

## 10 difficult follow-up questions

1. **"Your dataset is public and well-known — what's actually YOUR work here?"**
   The dataset is a commodity; the pipeline isn't. The cleaning rules, the
   phase/chasing feature definitions, the cross-checked SQL, the Power BI
   bridge-table model, and the explicit correlation-vs-causation framing are
   all decisions I made and can defend — a different analyst given the same
   raw CSVs would build a different project.

2. **"Couldn't you have just used a pre-built Kaggle notebook?"**
   I could have copied one, but then I couldn't defend a single design
   decision in it under questioning — every choice here (why this phase
   cutoff, why this join, why this DAX pattern) is one I made and can
   explain and would make differently if I disagreed with it in hindsight.

3. **"Your qualified-batter cutoff is arbitrary — defend it."**
   It is a judgment call, stated as one rather than hidden — the
   alternative (no cutoff) is worse, because it lets a single-innings fluke
   top a "best strike rate" leaderboard, which is a more misleading default
   than an explicit, disclosed threshold.

4. **"Why should I trust your economy-rate numbers over ESPN Cricinfo's official stats?"**
   They should match closely for standard cases; where they might not
   (edge cases like how a specific extras type is attributed) the
   definition is fully documented in the README and the code, so any
   discrepancy is traceable to a specific, statable rule rather than a
   black box.

5. **"Your franchise-rename mapping is a judgment call — what if I disagree with merging Delhi Daredevils into Delhi Capitals?"**
   That's a fair disagreement to have — it's one dict (`TEAM_NAME_MAP`) in
   one place, so removing that merge and treating them as separate
   franchises is a one-line change, not a re-architecture.

6. **"If I gave you next season's data right now, how long would it take to refresh everything, and what would break?"**
   The Python pipeline and SQL just re-run against the new CSVs directly;
   nothing's hard-coded to a season list. The one thing to check manually is
   whether the new season introduces another franchise rename to add to the
   mapping — that's the single spot that needs a human eye.

7. **"Your toss finding is basically 50/50 — isn't that just saying the toss doesn't matter? Why call it an insight at all?"**
   A number close to 50% *is* the insight — it's evidence against the
   popular "win the toss, win the match" narrative, not a null result to
   hide. A boring, well-supported finding that contradicts common belief is
   more useful than a dramatic one that doesn't hold up.

8. **"Walk me through a bug you hit and how you fixed it."**
   I initially inferred which team batted first from `toss_winner` +
   `toss_decision` by hand, which is easy to get backwards (does "field"
   mean the toss winner bats or bowls first?). I caught it by cross-checking
   against the ball-by-ball data directly and switched to reading the
   inning-1 batting team from `deliveries` instead — ground truth over
   inference wherever the raw data actually contains the answer.

9. **"Why SQL AND Power BI AND Python — pick one, why not just do it in Power BI alone?"**
   Each does something the others don't well: Python for exploratory
   iteration and custom feature engineering, SQL for a structured, auditable
   set of queries that's tool-agnostic and easy to hand to anyone with
   database access, Power BI for interactive exploration by people who
   don't write code — a real analytics stack, not a redundant one.

10. **"What's the weakest part of this project, in your own opinion?"**
    It's descriptive, not predictive — every finding is "here's a pattern in
    what already happened," and the honest next step (a win-probability
    model) is explicitly called out as future work rather than something I
    quietly skipped without acknowledging it.
