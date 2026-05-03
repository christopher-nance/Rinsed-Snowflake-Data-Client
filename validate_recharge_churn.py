"""Validate recharge churn methodology.

Shows the recharge method results alongside MAOM and Rinsed export
for comparison. Note: the denominators differ by design — the recharge
method uses prior-month transaction count while MAOM/Rinsed use active
member count.
"""

import os
from datetime import datetime

import pandas as pd
import snowflake.connector
from dotenv import load_dotenv

from rinsed_snowflake_client import RinsedClient

load_dotenv()

RINSED_FILE = r"C:\Users\Chris\Downloads\washu_subscriber_churn_by_type_monthly_2026-05-03T04_32_32.613122287-07_00.xlsx"

MONTHS = [
    ("2025-05-01", "2025-05-31"),
    ("2025-06-01", "2025-06-30"),
    ("2025-07-01", "2025-07-31"),
    ("2025-08-01", "2025-08-31"),
    ("2025-09-01", "2025-09-30"),
    ("2025-10-01", "2025-10-31"),
    ("2025-11-01", "2025-11-30"),
    ("2025-12-01", "2025-12-31"),
    ("2026-01-01", "2026-01-31"),
    ("2026-02-01", "2026-02-28"),
    ("2026-03-01", "2026-03-31"),
    ("2026-04-01", "2026-04-30"),
]


def load_rinsed_export():
    df = pd.read_excel(RINSED_FILE)
    df["CREATED_MONTH"] = pd.to_datetime(df["CREATED_MONTH"]).dt.date
    df["TOTAL_CHURN"] = df["VOLUNTARY_CHURN"] + df["CC_CHURN"]
    return df


def query_maom():
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
        cur.execute("""
            SELECT
                created_month,
                SUM(voluntary_churn) AS vol_count,
                SUM(cc_churn) AS inv_count,
                SUM(transaction_count_prior) AS denominator
            FROM member_activity_overview_monthly
            WHERE created_month >= '2025-05-01' AND created_month <= '2026-04-01'
              AND location_name NOT IN ('Hub Office', 'Query Server')
              AND location_name IS NOT NULL
            GROUP BY created_month
            ORDER BY created_month
        """)
        data = cur.fetchall()
        cols = [d[0].lower() for d in cur.description]
        df = pd.DataFrame(data, columns=cols)
        df["created_month"] = pd.to_datetime(df["created_month"]).dt.date
        return df
    finally:
        conn.close()


def main():
    rinsed = load_rinsed_export()
    print("Querying MEMBER_ACTIVITY_OVERVIEW_MONTHLY...")
    maom = query_maom()

    print("Running recharge_churn() for 12 months...\n")
    rows = []
    with RinsedClient() as client:
        for start, end in MONTHS:
            result = client.stats.recharge_churn(start, end)
            month_dt = datetime.fromisoformat(start).date()
            rows.append({
                "month": month_dt,
                "rc_denom": result.total_denominator,
                "rc_churned": result.total_churned,
                "rc_rate": result.cumulative_churn_rate,
                "rc_vol": result.total_voluntary,
                "rc_inv": result.total_involuntary,
                "rc_days": len(result.days),
            })

    print("=" * 100)
    print("COMPARISON: Recharge Method vs MAOM vs Rinsed Export")
    print("  Recharge method denominator = prior month (recharges + new members)")
    print("  MAOM/Rinsed denominator = active member count (different measure)")
    print("=" * 100)
    print(f"\n{'Month':<10} {'RC Denom':>10} {'RC Churn':>10} {'RC Rate':>9} | "
          f"{'MAOM Denom':>11} {'MAOM Churn':>11} {'MAOM Rate':>10} {'Rinsed':>10} {'Days':>5}")
    print("-" * 100)

    for rc in rows:
        m = rc["month"]

        rinsed_row = rinsed[rinsed["CREATED_MONTH"] == m]
        rinsed_rate = float(rinsed_row["TOTAL_CHURN"].iloc[0]) if not rinsed_row.empty else None

        maom_row = maom[maom["created_month"] == m]
        if not maom_row.empty:
            maom_d = int(maom_row["denominator"].iloc[0])
            maom_c = int(maom_row["vol_count"].iloc[0]) + int(maom_row["inv_count"].iloc[0])
            maom_r = maom_c / maom_d if maom_d > 0 else 0
        else:
            maom_d = maom_c = None
            maom_r = None

        maom_d_s = f"{maom_d:>11,}" if maom_d is not None else f"{'—':>11}"
        maom_c_s = f"{maom_c:>11,}" if maom_c is not None else f"{'—':>11}"
        maom_r_s = f"{maom_r:>10.4%}" if maom_r is not None else f"{'—':>10}"
        rinsed_s = f"{rinsed_rate:>10.4%}" if rinsed_rate is not None else f"{'—':>10}"

        flag = " *" if rc["rc_churned"] < 0 else ""
        print(
            f"{str(m)[:7]:<10} {rc['rc_denom']:>10,} {rc['rc_churned']:>10,} {rc['rc_rate']:>9.4%} | "
            f"{maom_d_s} {maom_c_s} {maom_r_s} {rinsed_s} {rc['rc_days']:>5}{flag}"
        )

    print("\n * = negative churned (retained > denominator — net membership growth that month)")

    # Validate MAOM rate matches Rinsed export rate
    print("\n\nMAOM vs Rinsed export rate check:")
    for _, maom_row in maom.iterrows():
        m = maom_row["created_month"]
        rinsed_row = rinsed[rinsed["CREATED_MONTH"] == m]
        if not rinsed_row.empty:
            maom_d = int(maom_row["denominator"])
            maom_c = int(maom_row["vol_count"]) + int(maom_row["inv_count"])
            maom_r = maom_c / maom_d
            rinsed_r = float(rinsed_row["TOTAL_CHURN"].iloc[0])
            diff = abs(maom_r - rinsed_r)
            match = "MATCH" if diff < 0.001 else f"DIFF {diff:.6f}"
            print(f"  {str(m)[:7]}: MAOM={maom_r:.6f} Rinsed={rinsed_r:.6f}  {match}")


if __name__ == "__main__":
    main()
