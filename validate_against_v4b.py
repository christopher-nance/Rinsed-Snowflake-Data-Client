"""Validate client wrapper against v4b source-of-truth query for Jan-Mar 2026.

Runs both the v4b SQL directly and the client methods, then compares
every metric at the day x location level.
"""

import os
import sys
from collections import defaultdict
from datetime import datetime

import pandas as pd
import snowflake.connector
from dotenv import load_dotenv

from rinsed_snowflake_client import RinsedClient

load_dotenv()

START = "2026-01-01"
END = "2026-03-31"

V4B_SQL = r"""
WITH
location_map AS (
    SELECT location_id, location_name
    FROM (
        SELECT location_id, location_name,
               ROW_NUMBER() OVER (PARTITION BY location_id ORDER BY created_at DESC) AS rn
        FROM WASHU_RINSED_SHARE.MB.FCT_REVENUE
        WHERE location_id IS NOT NULL AND location_name IS NOT NULL
          AND location_name NOT IN ('Hub Office', 'Query Server')
    ) WHERE rn = 1
),
retail_washes AS (
    SELECT DATE(r.created_at) AS created_day, r.location_name,
        COUNT(*) AS retail_wash, 0 AS member_wash, 0 AS retail_wash_free,
        SUM(COALESCE(r.amount, 0)) AS retail_revenue,
        0 AS member_revenue, 0 AS member_count_new, 0 AS member_revenue_new
    FROM WASHU_RINSED_SHARE.MB.FCT_REVENUE r
    WHERE r.transaction_category = 'Retail Wash'
      AND r.location_name NOT IN ('Hub Office', 'Query Server')
      AND r.location_name IS NOT NULL
      AND DATE(r.created_at) >= %s AND DATE(r.created_at) <= %s
    GROUP BY DATE(r.created_at), r.location_name
),
free_washes AS (
    SELECT DATE(r.created_at) AS created_day, r.location_name,
        0 AS retail_wash, 0 AS member_wash, COUNT(*) AS retail_wash_free,
        0 AS retail_revenue, 0 AS member_revenue, 0 AS member_count_new, 0 AS member_revenue_new
    FROM WASHU_RINSED_SHARE.MB.FCT_REVENUE r
    WHERE r.transaction_category = 'Free Wash'
      AND r.location_name NOT IN ('Hub Office', 'Query Server')
      AND r.location_name IS NOT NULL
      AND DATE(r.created_at) >= %s AND DATE(r.created_at) <= %s
    GROUP BY DATE(r.created_at), r.location_name
),
member_washes AS (
    SELECT created_day, location_name,
        0 AS retail_wash, COUNT(*) AS member_wash, 0 AS retail_wash_free,
        0 AS retail_revenue, 0 AS member_revenue, 0 AS member_count_new, 0 AS member_revenue_new
    FROM (
        SELECT DATE(rd.created_at) AS created_day, rd.location_name
        FROM WASHU_RINSED_SHARE.MB.FCT_REDEMPTIONS rd
        WHERE rd.location_name NOT IN ('Hub Office', 'Query Server')
          AND rd.location_name IS NOT NULL
          AND DATE(rd.created_at) >= %s AND DATE(rd.created_at) <= %s
        UNION ALL
        SELECT DATE(r.created_at) AS created_day, r.location_name
        FROM WASHU_RINSED_SHARE.MB.FCT_REVENUE r
        WHERE r.transaction_category IN ('New Membership & Redemption', 'Renewed Membership & Redemption')
          AND r.location_name NOT IN ('Hub Office', 'Query Server')
          AND r.location_name IS NOT NULL
          AND DATE(r.created_at) >= %s AND DATE(r.created_at) <= %s
    ) mw
    GROUP BY created_day, location_name
),
member_renewed_revenue AS (
    SELECT DATE(m.created_at) AS created_day, m.location_name,
        0 AS retail_wash, 0 AS member_wash, 0 AS retail_wash_free,
        0 AS retail_revenue, SUM(COALESCE(m.revenue, 0)) AS member_revenue,
        0 AS member_count_new, 0 AS member_revenue_new
    FROM WASHU_RINSED_SHARE.MB.FCT_MEMBERSHIPS m
    WHERE m.transaction_category = 'renewed membership'
      AND m.location_name NOT IN ('Hub Office', 'Query Server')
      AND m.location_name IS NOT NULL
      AND DATE(m.created_at) >= %s AND DATE(m.created_at) <= %s
    GROUP BY DATE(m.created_at), m.location_name
),
new_members AS (
    SELECT DATE(m.created_at) AS created_day, m.location_name,
        0 AS retail_wash, 0 AS member_wash, 0 AS retail_wash_free,
        0 AS retail_revenue, 0 AS member_revenue,
        COUNT(*) AS member_count_new, SUM(COALESCE(m.revenue, 0)) AS member_revenue_new
    FROM WASHU_RINSED_SHARE.MB.FCT_MEMBERSHIPS m
    WHERE m.transaction_category IN ('new membership', 'rejoin membership')
      AND m.location_name NOT IN ('Hub Office', 'Query Server')
      AND m.location_name IS NOT NULL
      AND DATE(m.created_at) >= %s AND DATE(m.created_at) <= %s
    GROUP BY DATE(m.created_at), m.location_name
),
combined AS (
    SELECT * FROM retail_washes
    UNION ALL SELECT * FROM free_washes
    UNION ALL SELECT * FROM member_washes
    UNION ALL SELECT * FROM member_renewed_revenue
    UNION ALL SELECT * FROM new_members
)
SELECT
    created_day AS CREATED_DAY,
    location_name AS LOCATION_NAME,
    SUM(retail_wash) AS RETAIL_WASH,
    SUM(member_wash) AS MEMBER_WASH,
    SUM(retail_wash_free) AS RETAIL_WASH_FREE,
    SUM(retail_wash) + SUM(member_wash) + SUM(retail_wash_free) AS TOTAL_WASHES,
    SUM(retail_revenue) AS RETAIL_REVENUE,
    SUM(member_revenue) AS MEMBER_REVENUE,
    SUM(member_count_new) AS MEMBER_COUNT_NEW,
    SUM(member_revenue_new) AS MEMBER_REVENUE_NEW
FROM combined
GROUP BY created_day, location_name
ORDER BY created_day, location_name
"""


def run_v4b_query():
    """Run v4b source-of-truth query directly against Snowflake."""
    print("Running v4b source-of-truth query...")
    conn = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        schema=os.environ["SNOWFLAKE_SCHEMA"],
        role=os.environ.get("SNOWFLAKE_ROLE"),
    )
    try:
        cur = conn.cursor()
        params = [START, END] * 6  # 6 CTEs each need start/end
        cur.execute(V4B_SQL, params)
        data = cur.fetchall()
        cols = [d[0].lower() for d in cur.description]
        df = pd.DataFrame(data, columns=cols)
        print(f"  v4b returned {len(df)} rows")
        return df
    finally:
        conn.close()


def run_client_daily_kpis():
    """Run the client's daily_kpis() method."""
    print("Running client daily_kpis()...")
    with RinsedClient() as client:
        result = client.stats.daily_kpis(START, END)
        rows = []
        for r in result.rows:
            rows.append({
                "created_day": r.date,
                "location_name": r.location_name,
                "retail_car_count": r.retail_car_count,
                "member_car_count": r.member_car_count,
                "total_car_count": r.total_car_count,
                "retail_revenue": r.retail_revenue,
                "membership_revenue_renewal": r.membership_revenue_renewal,
                "membership_revenue_new": r.membership_revenue_new,
                "membership_sales": r.membership_sales,
                "membership_sales_revenue": r.membership_sales_revenue,
            })
        df = pd.DataFrame(rows)
        print(f"  client returned {len(df)} rows")
        return df


def compare(v4b_df, client_df):
    """Compare v4b and client results at day x location level."""
    metric_map = {
        "RETAIL_WASH": ("retail_wash", "retail_car_count"),
        "MEMBER_WASH": ("member_wash", "member_car_count"),
        "RETAIL_REVENUE": ("retail_revenue", "retail_revenue"),
        "MEMBER_REVENUE": ("member_revenue", "membership_revenue_renewal"),
        "MEMBER_COUNT_NEW": ("member_count_new", "membership_sales"),
        "MEMBER_REVENUE_NEW": ("member_revenue_new", "membership_sales_revenue"),
    }

    v4b_df["key"] = v4b_df["created_day"].astype(str) + "|" + v4b_df["location_name"]
    client_df["key"] = client_df["created_day"].astype(str) + "|" + client_df["location_name"]

    v4b_keyed = v4b_df.set_index("key")
    client_keyed = client_df.set_index("key")

    all_keys = sorted(set(v4b_keyed.index) | set(client_keyed.index))

    print(f"\nComparing {len(all_keys)} day x location combinations")
    print("=" * 80)

    # Check for keys in one but not the other
    v4b_only = set(v4b_keyed.index) - set(client_keyed.index)
    client_only = set(client_keyed.index) - set(v4b_keyed.index)
    if v4b_only:
        print(f"\n  WARNING: {len(v4b_only)} keys in v4b but NOT in client:")
        for k in sorted(v4b_only)[:10]:
            print(f"    {k}")
    if client_only:
        print(f"\n  WARNING: {len(client_only)} keys in client but NOT in v4b:")
        for k in sorted(client_only)[:10]:
            print(f"    {k}")

    common_keys = sorted(set(v4b_keyed.index) & set(client_keyed.index))
    print(f"\n  Common keys: {len(common_keys)}")

    results = {}
    for label, (v4b_col, client_col) in metric_map.items():
        diffs = []
        total_abs_diff = 0
        max_diff = 0
        max_diff_key = ""

        for key in common_keys:
            v4b_val = float(v4b_keyed.loc[key, v4b_col])
            client_val = float(client_keyed.loc[key, client_col])
            diff = client_val - v4b_val
            if abs(diff) > 0.005:
                diffs.append((key, v4b_val, client_val, diff))
            total_abs_diff += abs(diff)
            if abs(diff) > abs(max_diff):
                max_diff = diff
                max_diff_key = key

        status = "PASS" if len(diffs) == 0 else "FAIL"
        results[label] = {
            "status": status,
            "mismatches": len(diffs),
            "total_abs_diff": total_abs_diff,
            "max_diff": max_diff,
            "max_diff_key": max_diff_key,
            "diffs": diffs,
        }

    # Print summary
    print("\n" + "=" * 80)
    print(f"{'Metric':<22} {'Status':<6} {'Mismatches':>10} {'Total Abs Diff':>16} {'Max Diff':>12}")
    print("-" * 80)
    all_pass = True
    for label, r in results.items():
        status_str = r["status"]
        if status_str == "FAIL":
            all_pass = False
        print(
            f"{label:<22} {status_str:<6} {r['mismatches']:>10} "
            f"{r['total_abs_diff']:>16.2f} {r['max_diff']:>12.2f}"
        )

    # Print first few mismatches for each failing metric
    for label, r in results.items():
        if r["diffs"]:
            print(f"\n  First 5 mismatches for {label}:")
            for key, v4b_val, client_val, diff in r["diffs"][:5]:
                print(f"    {key}: v4b={v4b_val:.2f} client={client_val:.2f} diff={diff:+.2f}")

    print("\n" + "=" * 80)
    if all_pass and not v4b_only and not client_only:
        print("ALL METRICS MATCH 1:1 across all locations and dates.")
    elif all_pass:
        print("All metrics match on common keys, but there are key differences (see above).")
    else:
        print("MISMATCHES FOUND — see details above.")

    return all_pass and not v4b_only and not client_only


def validate_total_washes(v4b_df, client_df):
    """Separate check for TOTAL_WASHES vs total_car_count (different sources)."""
    print("\n" + "=" * 80)
    print("TOTAL_WASHES comparison (v4b assembled vs client CONVERSION_DAILY)")
    print("  NOTE: These use different data sources, so small diffs are expected.")

    v4b_df["key"] = v4b_df["created_day"].astype(str) + "|" + v4b_df["location_name"]
    client_df["key"] = client_df["created_day"].astype(str) + "|" + client_df["location_name"]

    v4b_keyed = v4b_df.set_index("key")
    client_keyed = client_df.set_index("key")
    common = sorted(set(v4b_keyed.index) & set(client_keyed.index))

    diffs = []
    v4b_total = 0
    client_total = 0
    for key in common:
        v4b_val = int(v4b_keyed.loc[key, "total_washes"])
        client_val = int(client_keyed.loc[key, "total_car_count"])
        v4b_total += v4b_val
        client_total += client_val
        diff = client_val - v4b_val
        if diff != 0:
            diffs.append((key, v4b_val, client_val, diff))

    total_diff = client_total - v4b_total
    pct = abs(total_diff) / v4b_total * 100 if v4b_total else 0
    print(f"  v4b total:    {v4b_total:>12,}")
    print(f"  client total: {client_total:>12,}")
    print(f"  diff:         {total_diff:>+12,} ({pct:.4f}%)")
    print(f"  day x loc mismatches: {len(diffs)}")
    if diffs:
        print(f"  First 5:")
        for key, v4b_val, client_val, diff in diffs[:5]:
            print(f"    {key}: v4b={v4b_val} client={client_val} diff={diff:+d}")


if __name__ == "__main__":
    v4b_df = run_v4b_query()
    client_df = run_client_daily_kpis()
    success = compare(v4b_df, client_df)
    validate_total_washes(v4b_df, client_df)
    sys.exit(0 if success else 1)
