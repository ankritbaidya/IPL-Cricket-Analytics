# Resume — IPL Cricket Performance & Strategy Analytics

**Tech stack:** Python (pandas, NumPy, Matplotlib, Seaborn) | SQL (MySQL/PostgreSQL) | Power BI (Power Query, DAX) | Excel | Git/GitHub

### Bullets

- Built an end-to-end analytics pipeline in Python to clean, feature-engineer,
  and analyze **1,095 IPL matches and 260,000+ ball-by-ball deliveries
  (2008–2024)**, engineering metrics not present in the raw data — strike
  rate, economy rate, and Powerplay/Middle/Death-over phase splits.
- Wrote **20 SQL queries** against a normalized two-table schema using joins,
  CTEs, window functions (`RANK`, `ROW_NUMBER`, `LAG`), and a correlated
  subquery to answer team-, player-, and venue-strategy questions, cross-
  checking every SQL result against the equivalent Python aggregation.
- Designed a **4-page Power BI dashboard** (custom data model with a
  bridge table to unpivot two team columns into a single slicer, 15 DAX
  measures) enabling interactive team/player/season/venue exploration for
  non-technical users.
- Documented and defended every data-cleaning judgment call (franchise-
  rename mapping, missing-city recovery via venue lookup, wicket-type
  attribution) and explicitly separated correlational findings from causal
  claims throughout the analysis and README.

### Fifth bullet, with the real numbers

- Analyzed 17 seasons of IPL data (1,095 matches, 260,000+ deliveries) to
  find that teams won 53.9% of matches chasing vs. 45.7% batting first, and
  that toss outcome predicted the match winner only 50.6% of the time —
  quantified evidence against a widely-repeated broadcast narrative.
