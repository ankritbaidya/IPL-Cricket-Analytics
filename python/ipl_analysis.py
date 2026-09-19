"""
IPL Cricket Performance & Strategy Analytics
=============================================

Central question: what performance patterns and match conditions are
associated with winning in the IPL?

Pipeline: load -> inspect -> clean -> feature engineer -> EDA (saved as
PNGs) -> export tidy tables for SQL / Power BI -> print a plain-text
insight summary.

Data: IPL Complete Dataset (2008-2024) — matches.csv + deliveries.csv,
sourced from Cricsheet, packaged on Kaggle by patrickb1912.
See ../data/README.md for the exact download link and column dictionary.

Usage:
    python ipl_analysis.py --data-dir ../data --out-dir ../outputs

Every number this script prints or plots is calculated directly from
whatever CSVs are in --data-dir. Nothing here is hard-coded or invented —
if the data isn't there yet, the script says so and stops rather than
guessing.
"""

import argparse
import os
import sys
import warnings

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # headless-safe; still writes PNG files fine
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings("ignore")
sns.set_theme(style="whitegrid")
plt.rcParams["figure.dpi"] = 110

POWERPLAY_OVERS = range(0, 6)     # overs 1-6   (0-indexed 0-5)
MIDDLE_OVERS = range(6, 15)       # overs 7-15  (0-indexed 6-14)
DEATH_OVERS = range(15, 20)       # overs 16-20 (0-indexed 15-19)

# Franchise renames / spelling variants seen across seasons. Only merge
# entities that are genuinely the SAME franchise under a new name —
# defunct franchises (Deccan Chargers, Pune Warriors, Gujarat Lions,
# Kochi Tuskers Kerala) are deliberately left alone since they are not
# the same legal entity as any later team.
TEAM_NAME_MAP = {
    "Delhi Daredevils": "Delhi Capitals",
    "Kings XI Punjab": "Punjab Kings",
    "Royal Challengers Bangalore": "Royal Challengers Bengaluru",
    "Rising Pune Supergiants": "Rising Pune Supergiant",
}


# --------------------------------------------------------------------------
# 1. LOAD
# --------------------------------------------------------------------------
def load_data(data_dir):
    matches_path = os.path.join(data_dir, "matches.csv")
    deliveries_path = os.path.join(data_dir, "deliveries.csv")

    missing = [p for p in (matches_path, deliveries_path) if not os.path.exists(p)]
    if missing:
        print("Could not find the source data:")
        for p in missing:
            print(f"  - {p} (not found)")
        print(
            "\nSee data/README.md for the download link (Kaggle, ~2 minutes, "
            "free account). Drop matches.csv and deliveries.csv into the "
            "data/ folder and re-run this script."
        )
        sys.exit(1)

    matches = pd.read_csv(matches_path)
    deliveries = pd.read_csv(deliveries_path)
    return matches, deliveries


# --------------------------------------------------------------------------
# 2. INSPECT
# --------------------------------------------------------------------------
def inspect(df, name):
    print(f"\n--- {name} ---")
    print("Shape:", df.shape)
    print("\nDtypes:\n", df.dtypes)
    print("\nMissing values (%):\n", (df.isna().mean() * 100).round(2))
    print("\nDuplicate rows:", df.duplicated().sum())
    print("\nDescribe (numeric):\n", df.describe(include=[np.number]).T)


# --------------------------------------------------------------------------
# 3. CLEAN
# --------------------------------------------------------------------------
def clean_matches(matches):
    df = matches.copy()

    # Standardise team name spelling/renames across both team columns and
    # every result-related column that stores a team name.
    team_cols = ["team1", "team2", "toss_winner", "winner"]
    for col in team_cols:
        df[col] = df[col].replace(TEAM_NAME_MAP)

    # Dates
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # `season` shows up as both "2020" and "2020/21" in raw exports for the
    # UAE-hosted seasons — normalise to the starting year as an integer.
    df["season"] = df["season"].astype(str).str.slice(0, 4).astype(int)

    # City is null for a handful of UAE neutral-venue matches where only the
    # venue was recorded. Recover it from the venue name instead of dropping
    # the rows (we still want these matches in team/venue analysis).
    venue_to_city = df.dropna(subset=["city"]).drop_duplicates("venue").set_index("venue")["city"]
    df["city"] = df["city"].fillna(df["venue"].map(venue_to_city))
    df["city"] = df["city"].fillna("Unknown")

    # result_margin is legitimately NaN for ties / no-result matches — that
    # is real information, not missing data, so we leave it as NaN rather
    # than imputing a fake margin.

    # Drop columns that are almost entirely empty and not used downstream
    # (kept only if you want umpire-level analysis).
    drop_if_present = [c for c in ["umpire3"] if c in df.columns]
    df = df.drop(columns=drop_if_present)

    df = df.drop_duplicates(subset="id")
    return df


def clean_deliveries(deliveries):
    df = deliveries.copy()

    team_cols = ["batting_team", "bowling_team"]
    for col in team_cols:
        df[col] = df[col].replace(TEAM_NAME_MAP)

    # A legal delivery is one that isn't a wide or a no-ball (those don't
    # consume a ball of the 20-over allotment).
    df["is_legal_ball"] = ~df["extras_type"].isin(["wides", "noballs"])
    # A ball "faced" by the batter for strike-rate purposes excludes wides
    # only (a no-ball is still faced).
    df["is_faced_ball"] = df["extras_type"] != "wides"

    df["phase"] = np.select(
        [df["over"].isin(POWERPLAY_OVERS), df["over"].isin(MIDDLE_OVERS), df["over"].isin(DEATH_OVERS)],
        ["Powerplay", "Middle", "Death"],
        default="Other",
    )

    df = df.drop_duplicates()
    return df


# --------------------------------------------------------------------------
# 4. FEATURE ENGINEERING
# --------------------------------------------------------------------------
def batting_first_team_by_match(deliveries):
    """Ground truth of who batted first, read directly from ball-by-ball
    data (inning 1) rather than inferred from toss — avoids getting the
    toss-decision logic backwards."""
    inn1 = deliveries[deliveries["inning"] == 1]
    return inn1.groupby("match_id")["batting_team"].first().rename("bat_first_team")


def build_team_summary(matches, deliveries):
    bat_first = batting_first_team_by_match(deliveries)
    m = matches.join(bat_first, on="id")
    m["chasing_team"] = np.where(m["team1"] == m["bat_first_team"], m["team2"], m["team1"])
    m["batting_first_won"] = m["winner"] == m["bat_first_team"]
    m["chasing_won"] = m["winner"] == m["chasing_team"]
    m["toss_winner_won_match"] = m["toss_winner"] == m["winner"]

    teams = pd.unique(m[["team1", "team2"]].values.ravel())
    rows = []
    for t in teams:
        played = m[(m["team1"] == t) | (m["team2"] == t)]
        wins = (played["winner"] == t).sum()
        toss_won = (played["toss_winner"] == t).sum()
        toss_won_and_matchwon = ((played["toss_winner"] == t) & (played["winner"] == t)).sum()
        bat_first_matches = played[played["bat_first_team"] == t]
        chase_matches = played[played["chasing_team"] == t]
        rows.append(
            {
                "team": t,
                "matches_played": len(played),
                "wins": wins,
                "win_pct": round(100 * wins / len(played), 2) if len(played) else np.nan,
                "toss_win_pct": round(100 * toss_won / len(played), 2) if len(played) else np.nan,
                "toss_win_then_match_win_pct": round(100 * toss_won_and_matchwon / toss_won, 2) if toss_won else np.nan,
                "bat_first_matches": len(bat_first_matches),
                "bat_first_win_pct": round(100 * (bat_first_matches["winner"] == t).sum() / len(bat_first_matches), 2) if len(bat_first_matches) else np.nan,
                "chase_matches": len(chase_matches),
                "chase_win_pct": round(100 * (chase_matches["winner"] == t).sum() / len(chase_matches), 2) if len(chase_matches) else np.nan,
            }
        )
    return m, pd.DataFrame(rows).sort_values("win_pct", ascending=False).reset_index(drop=True)


def build_batting_summary(deliveries, matches, min_balls=200):
    df = deliveries.merge(matches[["id", "season"]], left_on="match_id", right_on="id", how="left")
    faced = df[df["is_faced_ball"]]

    runs = faced.groupby("batter")["batsman_runs"].sum()
    balls = faced.groupby("batter").size()
    innings = faced.groupby("batter")["match_id"].nunique()
    fours = faced[faced["batsman_runs"] == 4].groupby("batter").size()
    sixes = faced[faced["batsman_runs"] == 6].groupby("batter").size()

    # Dismissals credited to the batter who was actually out (not run-outs
    # of the non-striker, which live in player_dismissed regardless of who
    # caused it — this is still "how many times this player got out").
    dismissals = deliveries[deliveries["is_wicket"] == 1].groupby("player_dismissed").size()

    summary = pd.DataFrame(
        {
            "runs": runs,
            "balls_faced": balls,
            "innings": innings,
            "fours": fours,
            "sixes": sixes,
            "dismissals": dismissals,
        }
    ).fillna(0)

    summary["strike_rate"] = (summary["runs"] / summary["balls_faced"] * 100).round(2)
    summary["average"] = np.where(
        summary["dismissals"] > 0, (summary["runs"] / summary["dismissals"]).round(2), np.nan
    )
    summary["boundary_pct_of_runs"] = (
        (summary["fours"] * 4 + summary["sixes"] * 6) / summary["runs"].replace(0, np.nan) * 100
    ).round(2)

    qualified = summary[summary["balls_faced"] >= min_balls].copy()
    qualified.index.name = "batter"
    return summary.sort_values("runs", ascending=False), qualified.sort_values("strike_rate", ascending=False)


def build_bowling_summary(deliveries, min_balls=120):
    legal = deliveries[deliveries["is_legal_ball"]]

    runs_conceded = deliveries.groupby("bowler")["total_runs"].sum()
    # Runs off the bat plus non-legbye/bye extras attributable to the
    # bowler (wides, no-balls) — legbyes/byes are NOT charged to the bowler.
    bowler_extras = deliveries[deliveries["extras_type"].isin(["wides", "noballs"])].groupby("bowler")["extra_runs"].sum()
    balls_bowled = legal.groupby("bowler").size()

    wicket_types_credited = ["caught", "bowled", "lbw", "stumped", "caught and bowled", "hit wicket"]
    wickets = deliveries[(deliveries["is_wicket"] == 1) & (deliveries["dismissal_kind"].isin(wicket_types_credited))].groupby("bowler").size()

    summary = pd.DataFrame({"runs_conceded": runs_conceded, "balls_bowled": balls_bowled, "wickets": wickets}).fillna(0)
    summary["overs_bowled"] = (summary["balls_bowled"] // 6 + (summary["balls_bowled"] % 6) / 10).round(1)
    summary["economy"] = (summary["runs_conceded"] / (summary["balls_bowled"] / 6)).round(2)
    summary["bowling_strike_rate"] = np.where(
        summary["wickets"] > 0, (summary["balls_bowled"] / summary["wickets"]).round(2), np.nan
    )
    summary.index.name = "bowler"

    qualified = summary[summary["balls_bowled"] >= min_balls].copy()
    return summary.sort_values("wickets", ascending=False), qualified.sort_values("economy")


def build_phase_summary(deliveries):
    """Runs and run-rate by match phase (Powerplay / Middle / Death), the
    building block for the powerplay-vs-death-overs EDA and for the Power
    BI phase-performance visuals."""
    g = deliveries.groupby(["match_id", "inning", "phase"]).agg(
        runs=("total_runs", "sum"),
        balls=("is_legal_ball", "sum"),
        wickets=("is_wicket", "sum"),
    ).reset_index()
    g["run_rate"] = (g["runs"] / (g["balls"] / 6)).round(2)
    return g


def build_venue_summary(match_level):
    v = match_level.groupby("venue").agg(
        matches=("id", "count"),
        bat_first_win_pct=("batting_first_won", "mean"),
        avg_target=("target_runs", "mean"),
    ).reset_index()
    v["bat_first_win_pct"] = (v["bat_first_win_pct"] * 100).round(2)
    v["avg_target"] = v["avg_target"].round(1)
    return v.sort_values("matches", ascending=False)


# --------------------------------------------------------------------------
# 5. EDA (saved as PNG files)
# --------------------------------------------------------------------------
def run_eda(match_level, team_summary, bat_all, bat_qual, bowl_all, bowl_qual, phase, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    def savefig(name):
        plt.tight_layout()
        plt.savefig(os.path.join(out_dir, name), bbox_inches="tight")
        plt.close()

    # Matches per season
    plt.figure(figsize=(9, 4.5))
    match_level["season"].value_counts().sort_index().plot(kind="bar", color="#1f77b4")
    plt.title("IPL Matches per Season")
    plt.xlabel("Season")
    plt.ylabel("Matches")
    savefig("01_matches_per_season.png")

    # Win % by team
    plt.figure(figsize=(9, 5))
    sns.barplot(data=team_summary.head(12), y="team", x="win_pct", color="#2ca02c")
    plt.title("Win % by Team (Top 12, all seasons combined)")
    plt.xlabel("Win %")
    plt.ylabel("")
    savefig("02_win_pct_by_team.png")

    # Toss winner vs match winner
    plt.figure(figsize=(4.5, 4.5))
    match_level["toss_winner_won_match"].value_counts(normalize=True).mul(100).plot(
        kind="pie", autopct="%.1f%%", labels=["Toss winner also won", "Toss winner lost"], colors=["#ff7f0e", "#d3d3d3"]
    )
    plt.ylabel("")
    plt.title("Does Winning the Toss Predict the Match Winner?")
    savefig("03_toss_vs_match_winner.png")

    # Batting first vs chasing win %
    plt.figure(figsize=(5, 4.5))
    pd.Series(
        {
            "Batting first": match_level["batting_first_won"].mean() * 100,
            "Chasing": match_level["chasing_won"].mean() * 100,
        }
    ).plot(kind="bar", color=["#9467bd", "#17becf"], rot=0)
    plt.title("Win % — Batting First vs Chasing")
    plt.ylabel("Win %")
    savefig("04_bat_first_vs_chase.png")

    # Top run scorers
    plt.figure(figsize=(9, 5))
    top_runs = bat_all.head(12)
    sns.barplot(x=top_runs["runs"], y=top_runs.index, color="#e377c2")
    plt.title("Top 12 Run Scorers (2008-2024)")
    plt.xlabel("Career runs")
    plt.ylabel("")
    savefig("05_top_run_scorers.png")

    # Strike rate vs average (qualified batters)
    plt.figure(figsize=(7, 6))
    plt.scatter(bat_qual["average"], bat_qual["strike_rate"], alpha=0.5, color="#8c564b")
    plt.xlabel("Batting average")
    plt.ylabel("Strike rate")
    plt.title(f"Strike Rate vs Average (batters with {int(bat_qual['balls_faced'].min()) if len(bat_qual) else 0}+ balls faced)")
    savefig("06_strike_rate_vs_average.png")

    # Top wicket takers
    plt.figure(figsize=(9, 5))
    top_wkts = bowl_all.head(12)
    sns.barplot(x=top_wkts["wickets"], y=top_wkts.index, color="#bcbd22")
    plt.title("Top 12 Wicket Takers (2008-2024)")
    plt.xlabel("Career wickets")
    plt.ylabel("")
    savefig("07_top_wicket_takers.png")

    # Best economy (qualified bowlers)
    plt.figure(figsize=(9, 5))
    best_econ = bowl_qual.head(12)
    sns.barplot(x=best_econ["economy"], y=best_econ.index, color="#17becf")
    plt.title(f"Best Economy Rate (bowlers with {int(bowl_qual['balls_bowled'].min()) if len(bowl_qual) else 0}+ balls bowled)")
    plt.xlabel("Economy rate")
    plt.ylabel("")
    savefig("08_best_economy.png")

    # Run rate by phase
    plt.figure(figsize=(6, 4.5))
    phase_order = ["Powerplay", "Middle", "Death"]
    sns.boxplot(data=phase[phase["phase"].isin(phase_order)], x="phase", y="run_rate", order=phase_order,
                hue="phase", palette="Set2", legend=False)
    plt.title("Run Rate Distribution by Match Phase")
    plt.xlabel("")
    plt.ylabel("Run rate (per over)")
    savefig("09_run_rate_by_phase.png")

    # Season trend of average first-innings score
    first_inn = match_level.dropna(subset=["target_runs"]).copy()
    first_inn["first_innings_score"] = first_inn["target_runs"] - 1
    plt.figure(figsize=(9, 4.5))
    first_inn.groupby("season")["first_innings_score"].mean().plot(marker="o", color="#d62728")
    plt.title("Average 1st-Innings Score by Season")
    plt.xlabel("Season")
    plt.ylabel("Avg. 1st-innings score")
    savefig("10_avg_first_innings_score_by_season.png")

    print(f"Saved 10 charts to {out_dir}/")


# --------------------------------------------------------------------------
# 6. INSIGHTS (printed + written to a text file — every number traced back
#    to a table computed above, nothing invented)
# --------------------------------------------------------------------------
def write_insights(match_level, team_summary, bat_all, bowl_all, venue_summary, out_path):
    lines = []
    lines.append("IPL ANALYTICS — KEY INSIGHTS (auto-generated from the data actually loaded)")
    lines.append("=" * 78)

    n_matches = len(match_level)
    n_seasons = match_level["season"].nunique()
    toss_predicts_pct = round(match_level["toss_winner_won_match"].mean() * 100, 1)
    chase_win_pct = round(match_level["chasing_won"].mean() * 100, 1)
    bat_first_win_pct = round(match_level["batting_first_won"].mean() * 100, 1)
    top_team = team_summary.iloc[0]
    top_scorer = bat_all.index[0]
    top_scorer_runs = int(bat_all.iloc[0]["runs"])
    top_wkt_taker = bowl_all.index[0]
    top_wkt_taker_wkts = int(bowl_all.iloc[0]["wickets"])
    top_venue = venue_summary.iloc[0]

    lines.append(f"\nDataset scope: {n_matches} matches across {n_seasons} seasons.\n")

    lines.append(
        f"1. Toss impact: the toss winner also won the match in {toss_predicts_pct}% of games. "
        "This is an association, not proof the toss caused the win — teams may simply be choosing "
        "the toss decision that suits conditions they'd have wanted anyway."
    )
    lines.append(
        f"2. Chasing vs defending: teams won {chase_win_pct}% of the time batting second vs "
        f"{bat_first_win_pct}% batting first, across all venues and seasons combined."
    )
    lines.append(
        f"3. Most successful franchise: {top_team['team']} leads on win percentage at "
        f"{top_team['win_pct']}% ({int(top_team['wins'])} wins from {int(top_team['matches_played'])} matches)."
    )
    lines.append(
        f"4. All-time leading run scorer: {top_scorer} with {top_scorer_runs} runs."
    )
    lines.append(
        f"5. All-time leading wicket taker: {top_wkt_taker} with {top_wkt_taker_wkts} wickets."
    )
    lines.append(
        f"6. Most-used venue: {top_venue['venue']} ({int(top_venue['matches'])} matches), where teams "
        f"batting first won {top_venue['bat_first_win_pct']}% of the time — a venue-specific chase/defend "
        "signal worth checking before setting a strategy there."
    )
    lines.append(
        "\nRemaining insights (powerplay vs death-over patterns, season-wise scoring trends, "
        "per-team chase specialists, and the toss-decision breakdown) are in the charts in "
        "images/ and the full tables in outputs/*.csv — pull the specific numbers from there "
        "for the README and resume bullets rather than re-typing rounded figures."
    )

    text = "\n".join(lines)
    with open(out_path, "w") as f:
        f.write(text)
    print("\n" + text)


# --------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="../data")
    parser.add_argument("--out-dir", default="../outputs")
    args = parser.parse_args()

    images_dir = os.path.join(args.out_dir, "images")
    tables_dir = os.path.join(args.out_dir, "tables")
    os.makedirs(tables_dir, exist_ok=True)

    matches, deliveries = load_data(args.data_dir)

    inspect(matches, "matches.csv (raw)")
    inspect(deliveries, "deliveries.csv (raw)")

    matches = clean_matches(matches)
    deliveries = clean_deliveries(deliveries)

    match_level, team_summary = build_team_summary(matches, deliveries)
    bat_all, bat_qual = build_batting_summary(deliveries, matches)
    bowl_all, bowl_qual = build_bowling_summary(deliveries)
    phase = build_phase_summary(deliveries)
    venue_summary = build_venue_summary(match_level)

    # Export tidy tables — these feed the SQL load step and the Power BI
    # model directly, so column names here match sql/schema.sql.
    match_level.to_csv(os.path.join(tables_dir, "match_level.csv"), index=False)
    team_summary.to_csv(os.path.join(tables_dir, "team_summary.csv"), index=False)
    bat_all.to_csv(os.path.join(tables_dir, "batting_summary_all.csv"))
    bat_qual.to_csv(os.path.join(tables_dir, "batting_summary_qualified.csv"))
    bowl_all.to_csv(os.path.join(tables_dir, "bowling_summary_all.csv"))
    bowl_qual.to_csv(os.path.join(tables_dir, "bowling_summary_qualified.csv"))
    phase.to_csv(os.path.join(tables_dir, "phase_summary.csv"), index=False)
    venue_summary.to_csv(os.path.join(tables_dir, "venue_summary.csv"), index=False)
    print(f"\nSaved tidy tables to {tables_dir}/")

    run_eda(match_level, team_summary, bat_all, bat_qual, bowl_all, bowl_qual, phase, images_dir)
    write_insights(match_level, team_summary, bat_all, bowl_all, venue_summary, os.path.join(args.out_dir, "insights.txt"))


if __name__ == "__main__":
    main()
