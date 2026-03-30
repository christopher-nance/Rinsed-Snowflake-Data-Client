"""Validate Snowflake wrapper data against Rinsed front-end exports."""

import json
import os
import sys
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv

# Load .env before importing the client (it reads env vars)
load_dotenv()

from rinsed_snowflake_client import RinsedClient

DATA_DIR = "From Rinsed Front End"

def parse_int(s):
    """Parse a comma-formatted integer string."""
    if isinstance(s, (int, float)):
        return int(s)
    return int(str(s).replace(",", ""))


def parse_pct(s):
    """Parse a percentage string like '21.3%' to a float."""
    return float(str(s).replace("%", "")) / 100


# -----------------------------------------------------------------------
# 1. Conversion Daily Data Validation
# -----------------------------------------------------------------------
def validate_conversion_daily(client):
    print("\n" + "=" * 70)
    print("VALIDATION 1: Conversion Daily (Total Washes, Sales, Eligible)")
    print("=" * 70)

    with open(os.path.join(DATA_DIR, "rinsed_frontend_data.json")) as f:
        frontend = json.load(f)

    # Get unique dates from frontend
    dates = sorted(set(
        datetime.strptime(r["Date"], "%B %d, %Y").strftime("%Y-%m-%d")
        for r in frontend
    ))

    start_date = dates[0]
    end_date = dates[-1]
    print(f"Date range: {start_date} to {end_date}")

    # Get Snowflake data via the client for each date
    mismatches = []
    matches = 0
    total_checks = 0

    for date_str in dates:
        # Filter frontend rows for this date
        fe_rows = [
            r for r in frontend
            if datetime.strptime(r["Date"], "%B %d, %Y").strftime("%Y-%m-%d") == date_str
        ]

        # Query Snowflake via raw SQL (to get per-location per-day data)
        df = client.query(
            """
            SELECT location_name, total_washes, redeemed_washes, free_washes,
                   eligible_washes, sales
            FROM conversion_daily
            WHERE created_date = %s
              AND location_name NOT IN ('Hub Office', 'Query Server')
            ORDER BY location_name
            """,
            [date_str],
        )

        # Build lookup from Snowflake data
        sf_map = {}
        for _, row in df.iterrows():
            sf_map[row["location_name"]] = row

        for fe_row in fe_rows:
            loc = fe_row["Location"]
            total_checks += 1

            if loc not in sf_map:
                mismatches.append(f"  {date_str} | {loc}: NOT FOUND in Snowflake")
                continue

            sf = sf_map[loc]
            fe_total = parse_int(fe_row["Total Washes"])
            fe_redeemed = parse_int(fe_row["Redeemed Washes"])
            fe_free = parse_int(fe_row["Free Washes"])
            fe_eligible = parse_int(fe_row["Eligible Washes"])
            fe_sales = parse_int(fe_row["Sales"])

            sf_total = int(sf["total_washes"])
            sf_redeemed = int(sf["redeemed_washes"])
            sf_free = int(sf["free_washes"])
            sf_eligible = int(sf["eligible_washes"])
            sf_sales = int(sf["sales"])

            diffs = []
            if fe_total != sf_total:
                diffs.append(f"total_washes FE={fe_total} SF={sf_total}")
            if fe_redeemed != sf_redeemed:
                diffs.append(f"redeemed FE={fe_redeemed} SF={sf_redeemed}")
            if fe_free != sf_free:
                diffs.append(f"free FE={fe_free} SF={sf_free}")
            if fe_eligible != sf_eligible:
                diffs.append(f"eligible FE={fe_eligible} SF={sf_eligible}")
            if fe_sales != sf_sales:
                diffs.append(f"sales FE={fe_sales} SF={sf_sales}")

            if diffs:
                mismatches.append(f"  {date_str} | {loc}: {'; '.join(diffs)}")
            else:
                matches += 1

    print(f"Checked {total_checks} location-day rows")
    print(f"  Matches: {matches}")
    print(f"  Mismatches: {len(mismatches)}")
    if mismatches:
        print("MISMATCHES:")
        for m in mismatches[:20]:
            print(m)
        if len(mismatches) > 20:
            print(f"  ... and {len(mismatches) - 20} more")
    else:
        print("  ALL MATCH!")


# -----------------------------------------------------------------------
# 2. Aggregated stats method validation (total_car_count, conversion_rate)
# -----------------------------------------------------------------------
def validate_aggregated_stats(client):
    print("\n" + "=" * 70)
    print("VALIDATION 2: Aggregated Stats Methods (client.stats.*)")
    print("=" * 70)

    with open(os.path.join(DATA_DIR, "rinsed_frontend_data.json")) as f:
        frontend = json.load(f)

    # Pick one date to validate the client methods
    test_date = "2026-03-18"
    fe_rows = [
        r for r in frontend
        if datetime.strptime(r["Date"], "%B %d, %Y").strftime("%Y-%m-%d") == test_date
    ]

    fe_total_washes = sum(parse_int(r["Total Washes"]) for r in fe_rows)
    fe_total_sales = sum(parse_int(r["Sales"]) for r in fe_rows)
    fe_total_eligible = sum(parse_int(r["Eligible Washes"]) for r in fe_rows)
    fe_total_redeemed = sum(parse_int(r["Redeemed Washes"]) for r in fe_rows)

    print(f"\nDate: {test_date}")
    print(f"Frontend totals: washes={fe_total_washes}, sales={fe_total_sales}, "
          f"eligible={fe_total_eligible}, redeemed={fe_total_redeemed}")

    # Client methods
    car_count = client.stats.total_car_count(test_date, test_date)
    conversion = client.stats.conversion_rate(test_date, test_date)
    member_cars = client.stats.member_car_count(test_date, test_date)

    print(f"\nClient total_car_count: {car_count.total}")
    print(f"  Match: {'YES' if car_count.total == fe_total_washes else 'NO (FE=' + str(fe_total_washes) + ')'}")

    print(f"\nClient conversion_rate: sales={conversion.sales}, eligible={conversion.eligible_washes}")
    print(f"  Sales match: {'YES' if conversion.sales == fe_total_sales else 'NO (FE=' + str(fe_total_sales) + ')'}")
    print(f"  Eligible match: {'YES' if conversion.eligible_washes == fe_total_eligible else 'NO (FE=' + str(fe_total_eligible) + ')'}")

    # Check per-location car counts
    print("\nPer-location total washes comparison:")
    sf_map = {m.location_name: m.value for m in car_count.by_location}
    for fe_row in sorted(fe_rows, key=lambda r: r["Location"]):
        loc = fe_row["Location"]
        fe_val = parse_int(fe_row["Total Washes"])
        sf_val = sf_map.get(loc, "N/A")
        status = "OK" if sf_val == fe_val else "MISMATCH"
        print(f"  {loc:20s}  FE={fe_val:>6,}  SF={sf_val:>6}  {status}")


# -----------------------------------------------------------------------
# 3. Active Members Validation
# -----------------------------------------------------------------------
def validate_active_members(client):
    print("\n" + "=" * 70)
    print("VALIDATION 3: Active Members (member_subcount_data)")
    print("=" * 70)

    with open(os.path.join(DATA_DIR, "rinsed_frontend_member_subcount_data.json")) as f:
        subcount = json.load(f)

    # Pick a recent month and sum all locations for "Rinsed" definition
    test_month = "February 1, 2026"
    fe_rows = [
        r for r in subcount
        if r["MONTH"] == test_month and r["DEFINITION"] == "Rinsed"
    ]
    fe_total = sum(parse_int(r["MEMBERS"]) for r in fe_rows)
    fe_renewed = sum(
        parse_int(r["MEMBERS"]) for r in fe_rows if r["ACTIVE_EVENT_TYPE"] == "Renewed"
    )
    fe_new = sum(
        parse_int(r["MEMBERS"]) for r in fe_rows if r["ACTIVE_EVENT_TYPE"] == "New"
    )

    print(f"\nMonth: {test_month}")
    print(f"Frontend (Rinsed definition): Total={fe_total:,}, New={fe_new:,}, Renewed={fe_renewed:,}")

    # Query Snowflake directly for comparison
    df = client.query(
        """
        SELECT am.location_id, am.active_event_type, am.members
        FROM active_members_monthly am
        WHERE am.month = %s
          AND am.definition = 'Rinsed'
        ORDER BY am.location_id
        """,
        ["2026-02-01"],
    )

    sf_total = int(df["members"].sum()) if not df.empty else 0
    sf_renewed = int(df.loc[df["active_event_type"] == "Renewed", "members"].sum()) if not df.empty else 0
    sf_new = int(df.loc[df["active_event_type"] == "New", "members"].sum()) if not df.empty else 0

    print(f"Snowflake: Total={sf_total:,}, New={sf_new:,}, Renewed={sf_renewed:,}")
    print(f"  Total match: {'YES' if sf_total == fe_total else 'NO (diff=' + str(sf_total - fe_total) + ')'}")
    print(f"  Renewed match: {'YES' if sf_renewed == fe_renewed else 'NO (diff=' + str(sf_renewed - fe_renewed) + ')'}")
    print(f"  New match: {'YES' if sf_new == fe_new else 'NO (diff=' + str(sf_new - fe_new) + ')'}")

    # Also validate against the member_data.json (total active members on a date)
    with open(os.path.join(DATA_DIR, "rinsed_frontend_member_data.json")) as f:
        member_data = json.load(f)

    # Check a few specific dates
    total_entries = [r for r in member_data if r["Member Type"] == "Total"]
    print(f"\nFrontend member_data has {len(total_entries)} 'Total' date snapshots")
    print("(These are daily snapshots — Snowflake has monthly granularity, so exact match")
    print(" is only expected for dates near month boundaries)")


# -----------------------------------------------------------------------
# 4. Membership Revenue Validation
# -----------------------------------------------------------------------
def validate_membership_revenue(client):
    print("\n" + "=" * 70)
    print("VALIDATION 4: Membership Revenue (Excel files)")
    print("=" * 70)

    # Read all location Excel files
    locations_files = [f for f in os.listdir(DATA_DIR) if f.endswith("_membership_revenue.xlsx")]

    if not locations_files:
        print("No membership revenue Excel files found.")
        return

    all_fe_data = {}
    for fname in sorted(locations_files):
        loc_name = fname.replace("_membership_revenue.xlsx", "").replace("_", " ").title()
        # Map filename to actual location names used in the system
        loc_map = {
            "Berwyn": "Berwyn", "Burbank": "Burbank", "Carolstream": "Carol Stream",
            "Desplaines": "Des Plaines", "Dickson": "Dickson",
            "Evergreenpark": "Evergreen Park", "Fairview": "Fairview",
            "Jackson": "Jackson", "Joliet": "Joliet", "Naperville": "Naperville",
            "Niles": "Niles", "Nolensville": "Nolensville", "Plainfield": "Plainfield",
            "Villapark": "Villa Park", "Wheaton": "Wheaton",
        }
        raw_key = fname.replace("_membership_revenue.xlsx", "").title()
        mapped = loc_map.get(raw_key, loc_name)

        try:
            df = pd.read_excel(os.path.join(DATA_DIR, fname))
            all_fe_data[mapped] = df
            print(f"  Loaded {fname} -> {mapped} ({len(df)} rows, columns: {list(df.columns)})")
        except Exception as e:
            print(f"  ERROR loading {fname}: {e}")

    if not all_fe_data:
        return

    # Pick a month range to validate
    # Get membership revenue from the client for a recent month
    test_start = "2026-02-01"
    test_end = "2026-02-28"
    print(f"\nComparing membership revenue for {test_start} to {test_end}")

    mem_rev = client.stats.membership_revenue(test_start, test_end)
    print(f"Client total membership revenue: ${mem_rev.total:,.2f}")
    print(f"  New: ${mem_rev.new_revenue:,.2f}")
    print(f"  Renewal: ${mem_rev.renewal_revenue:,.2f}")

    # Show per-location from client
    print("\nPer-location from client:")
    for loc_metric in mem_rev.by_location:
        print(f"  {loc_metric.location_name:20s}: ${loc_metric.value:>12,.2f}")

    # Try to compare with Excel data
    print("\nNote: Excel files need manual inspection to determine column names")
    print("and date format for comparison. Showing first file's structure:")
    first_loc = list(all_fe_data.keys())[0]
    print(f"\n{first_loc} sample data:")
    print(all_fe_data[first_loc].head().to_string())


# -----------------------------------------------------------------------
# 5. Churn Validation
# -----------------------------------------------------------------------
def validate_churn(client):
    print("\n" + "=" * 70)
    print("VALIDATION 5: Churn Data (combined churn Excel)")
    print("=" * 70)

    churn_file = os.path.join(DATA_DIR, "rinsed_combined_churn_by_location_and_month.xlsx")
    try:
        df = pd.read_excel(churn_file)
        print(f"Loaded churn file: {len(df)} rows")
        print(f"Columns: {list(df.columns)}")
        print(f"\nSample data:")
        print(df.head(10).to_string())

        # Try to compare with client's churn methods for a specific month
        test_month = "2026-02-01"
        test_end = "2026-02-28"
        print(f"\nClient voluntary churn for {test_month}:")
        vol = client.stats.voluntary_churn_rate(test_month, test_end)
        print(f"  Rate: {vol.rate:.4f} ({vol.rate*100:.2f}%)")
        print(f"  Churned: {vol.churned_count}")
        print(f"  Starting active: {vol.starting_count}")

        print(f"\nClient involuntary churn for {test_month}:")
        inv = client.stats.involuntary_churn_rate(test_month, test_end)
        print(f"  Rate: {inv.rate:.4f} ({inv.rate*100:.2f}%)")
        print(f"  Churned: {inv.churned_count}")
        print(f"  Starting active: {inv.starting_count}")

        print(f"\nTotal churn: {vol.churned_count + inv.churned_count}")
        total_rate = (vol.churned_count + inv.churned_count) / vol.starting_count if vol.starting_count > 0 else 0
        print(f"Combined rate: {total_rate:.4f} ({total_rate*100:.2f}%)")

    except Exception as e:
        print(f"ERROR: {e}")


# -----------------------------------------------------------------------
# 6. Sites Validation
# -----------------------------------------------------------------------
def validate_sites(client):
    print("\n" + "=" * 70)
    print("VALIDATION 6: Sites / Locations")
    print("=" * 70)

    sites = client.sites.list()
    print(f"Client returned {len(sites)} sites:")
    for s in sites:
        print(f"  {s.location_name} (ID: {s.location_id})")

    # Cross-reference with locations in frontend data
    with open(os.path.join(DATA_DIR, "rinsed_frontend_data.json")) as f:
        frontend = json.load(f)

    fe_locations = sorted(set(r["Location"] for r in frontend))
    sf_locations = sorted(s.location_name for s in sites)

    print(f"\nFrontend locations ({len(fe_locations)}):")
    for loc in fe_locations:
        in_sf = "YES" if loc in sf_locations else "NO"
        print(f"  {loc:20s} -> in Snowflake: {in_sf}")

    sf_only = set(sf_locations) - set(fe_locations)
    if sf_only:
        print(f"\nIn Snowflake but not in frontend: {sf_only}")


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------
def main():
    print("=" * 70)
    print("Rinsed Snowflake Client Validation vs Frontend Data")
    print("=" * 70)

    with RinsedClient() as client:
        validate_sites(client)
        validate_conversion_daily(client)
        validate_aggregated_stats(client)
        validate_active_members(client)
        validate_membership_revenue(client)
        validate_churn(client)

    print("\n" + "=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
