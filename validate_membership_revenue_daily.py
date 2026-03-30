"""Compare daily membership revenue totals from Snowflake against
monthly totals from the Rinsed front-end Excel exports."""

import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from rinsed_snowflake_client import RinsedClient

DATA_DIR = "From Rinsed Front End"

# Map Excel filenames -> location names used in Snowflake
LOC_MAP = {
    "berwyn": "Berwyn",
    "burbank": "Burbank",
    "carolstream": "Carol Stream",
    "desplaines": "Des Plaines",
    "dickson": "Dickson",
    "evergreenpark": "Evergreen Park",
    "fairview": "Fairview",
    "jackson": "Jackson",
    "joliet": "Joliet",
    "naperville": "Naperville",
    "niles": "Niles",
    "nolensville": "Nolensville",
    "plainfield": "Plainfield",
    "villapark": "Villa Park",
    "wheaton": "Wheaton",
}


def load_frontend_revenue():
    """Load all per-location Excel files and combine into one DataFrame."""
    frames = []
    for fname in os.listdir(DATA_DIR):
        if not fname.endswith("_membership_revenue.xlsx"):
            continue
        key = fname.replace("_membership_revenue.xlsx", "")
        loc_name = LOC_MAP.get(key)
        if loc_name is None:
            print(f"  WARNING: unmapped file {fname}")
            continue

        df = pd.read_excel(os.path.join(DATA_DIR, fname))
        df["location_name"] = loc_name
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)
    # Normalize column names
    combined.columns = [c.strip().lower().replace(" ", "_").replace("($)", "usd") for c in combined.columns]
    return combined


def main():
    print("=" * 80)
    print("Membership Revenue: Snowflake Daily Sums vs Rinsed Frontend Monthly Totals")
    print("=" * 80)

    # --- Load frontend data ---
    fe = load_frontend_revenue()
    print(f"\nFrontend data: {len(fe)} rows")
    print(f"Columns: {list(fe.columns)}")
    print(fe.head())

    # Parse the LOGDATE to datetime and extract month
    fe["logdate"] = pd.to_datetime(fe["logdate"])
    fe["month"] = fe["logdate"].dt.to_period("M")

    # Frontend monthly totals per location
    fe_monthly = fe.groupby(["location_name", "month"])["revenue_usd"].sum().reset_index()
    fe_monthly.columns = ["location_name", "month", "fe_revenue"]

    print(f"\nFrontend monthly summaries: {len(fe_monthly)} location-months")

    # --- Query Snowflake for DAILY membership revenue ---
    with RinsedClient() as client:
        # Get the date range from frontend data
        # LOGDATE in Excel is first-of-month, so extend end to last day of that month
        min_date = fe["logdate"].min().strftime("%Y-%m-%d")
        last_month_start = fe["logdate"].max()
        # Get last day of that month
        import calendar
        last_day = calendar.monthrange(last_month_start.year, last_month_start.month)[1]
        max_date = last_month_start.replace(day=last_day).strftime("%Y-%m-%d")
        print(f"\nQuerying Snowflake for daily membership revenue from {min_date} to {max_date}...")

        # Daily query: sum revenue per location per day from fct_memberships
        df = client.query(
            """
            SELECT
                location_name,
                DATE(created_at) as rev_date,
                SUM(revenue) as daily_revenue
            FROM fct_memberships
            WHERE transaction_category IN ('new membership', 'rejoin membership', 'renewed membership')
              AND location_name NOT IN ('Hub Office', 'Query Server')
              AND DATE(created_at) >= %s
              AND DATE(created_at) <= %s
            GROUP BY location_name, DATE(created_at)
            ORDER BY location_name, DATE(created_at)
            """,
            [min_date, max_date],
        )

        print(f"Snowflake returned {len(df)} daily rows")

        # Also get monthly sums via the client's membership_revenue method for
        # a few months to cross-check the raw SQL approach
        print("\n--- Cross-check: client.stats.membership_revenue vs raw SQL ---")
        for test_month in ["2025-12-01", "2026-01-01", "2026-02-01"]:
            end_map = {
                "2025-12-01": "2025-12-31",
                "2026-01-01": "2026-01-31",
                "2026-02-01": "2026-02-28",
            }
            result = client.stats.membership_revenue(test_month, end_map[test_month])
            print(f"  {test_month}: client total=${result.total:,.2f} "
                  f"(new=${result.new_revenue:,.2f}, renewal=${result.renewal_revenue:,.2f})")

    # --- Aggregate Snowflake daily data to monthly ---
    df["rev_date"] = pd.to_datetime(df["rev_date"])
    df["daily_revenue"] = df["daily_revenue"].astype(float)
    df["month"] = df["rev_date"].dt.to_period("M")
    sf_monthly = df.groupby(["location_name", "month"])["daily_revenue"].sum().reset_index()
    sf_monthly.columns = ["location_name", "month", "sf_revenue"]

    # --- Merge and compare ---
    merged = fe_monthly.merge(sf_monthly, on=["location_name", "month"], how="outer", indicator=True)

    print("\n" + "=" * 80)
    print("COMPARISON: Frontend Monthly Revenue vs Snowflake Daily Sum")
    print("=" * 80)

    # Calculate differences
    merged["diff"] = merged["sf_revenue"].fillna(0) - merged["fe_revenue"].fillna(0)
    merged["pct_diff"] = (merged["diff"] / merged["fe_revenue"].replace(0, float("nan"))) * 100

    # Summary stats
    both = merged[merged["_merge"] == "both"]
    fe_only = merged[merged["_merge"] == "left_only"]
    sf_only = merged[merged["_merge"] == "right_only"]

    print(f"\nMatched location-months: {len(both)}")
    print(f"Frontend only: {len(fe_only)}")
    print(f"Snowflake only: {len(sf_only)}")

    # Show matches with differences
    if len(both) > 0:
        exact = both[both["diff"].abs() < 0.01]
        close = both[(both["diff"].abs() >= 0.01) & (both["pct_diff"].abs() < 1)]
        off = both[both["pct_diff"].abs() >= 1]

        print(f"\n  Exact matches (<$0.01 diff): {len(exact)}")
        print(f"  Close matches (<1% diff): {len(close)}")
        print(f"  Significant differences (>=1%): {len(off)}")

    # Show all comparisons sorted by month
    print("\n--- Per-Location Per-Month Comparison ---")
    print(f"{'Location':<20} {'Month':<10} {'FE Revenue':>14} {'SF Revenue':>14} {'Diff':>12} {'%Diff':>8}")
    print("-" * 82)

    for _, row in merged.sort_values(["month", "location_name"]).iterrows():
        fe_rev = f"${row['fe_revenue']:>12,.2f}" if pd.notna(row["fe_revenue"]) else "       N/A   "
        sf_rev = f"${row['sf_revenue']:>12,.2f}" if pd.notna(row["sf_revenue"]) else "       N/A   "
        diff_str = f"${row['diff']:>10,.2f}" if pd.notna(row["diff"]) else "     N/A  "
        pct_str = f"{row['pct_diff']:>6.2f}%" if pd.notna(row["pct_diff"]) else "   N/A "
        flag = " ***" if pd.notna(row["pct_diff"]) and abs(row["pct_diff"]) >= 1 else ""
        print(f"{row['location_name']:<20} {str(row['month']):<10} {fe_rev} {sf_rev} {diff_str} {pct_str}{flag}")

    # Grand totals
    print("\n--- Grand Totals ---")
    fe_total = merged["fe_revenue"].sum()
    sf_total = merged["sf_revenue"].sum()
    print(f"Frontend total:  ${fe_total:>14,.2f}")
    print(f"Snowflake total: ${sf_total:>14,.2f}")
    print(f"Difference:      ${sf_total - fe_total:>14,.2f} ({((sf_total - fe_total) / fe_total) * 100:.3f}%)")


if __name__ == "__main__":
    main()
