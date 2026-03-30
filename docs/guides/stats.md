# Stats & KPIs

All KPI methods are accessed via `client.stats` and share the same signature pattern:

```python
client.stats.<method>(start, end, locations=None)
```

## Car Counts

### Total Car Count

Returns the total number of washes across all types — retail, member redemptions, and free/comped washes. Sourced from the pre-aggregated `CONVERSION_DAILY` table.

```python
result = client.stats.total_car_count("2026-02-01", "2026-02-28")
print(f"Total washes: {result.total:,}")  # 288,389
```

**Use case — daily volume check:**

```python
result = client.stats.total_car_count("2026-03-18", "2026-03-18")
for loc in result.by_location:
    print(f"{loc.location_name}: {loc.value:,.0f}")
# Burbank: 1,471
# Des Plaines: 1,142
# Carol Stream: 1,014
# ...
```

### Retail Car Count

Counts pure retail (non-member) wash transactions from `FCT_REVENUE` where `transaction_category = 'Retail Wash'`.

```python
result = client.stats.retail_car_count("2026-02-01", "2026-02-28")
print(f"Retail washes: {result.total:,}")  # 97,865
```

!!! info "What counts as retail?"
    Only transactions categorized as `Retail Wash` in `FCT_REVENUE`. This **excludes**:

    - **NM&R** (New Membership & Redemption) — customer bought a membership and got a wash in the same transaction. This is a membership wash.
    - **RM&R** (Renewed Membership & Redemption) — customer renewed and got a wash. Also a membership wash.
    - **Free Wash** — comped or $0 transactions.

    If you need all non-member tunnel washes including NM&R/RM&R combos, use `total_car_count` minus `member_car_count`.

### Member Car Count

Counts membership redemptions — washes where a member scanned their unlimited pass. Sourced from `FCT_WASHES` where `transaction_category = 'redemption'`.

```python
result = client.stats.member_car_count("2026-02-01", "2026-02-28")
print(f"Member washes: {result.total:,}")  # 174,261
```

### Deriving Free Wash Count

There is no dedicated `free_car_count()` method. Derive it from the other counts:

```python
total = client.stats.total_car_count("2026-02-01", "2026-02-28")
retail = client.stats.retail_car_count("2026-02-01", "2026-02-28")
member = client.stats.member_car_count("2026-02-01", "2026-02-28")

# Free washes = total - retail - member - NM&R/RM&R combos
# For an approximation:
free_approx = total.total - retail.total - member.total
```

!!! note
    This approximation includes NM&R/RM&R combo washes in the "free" bucket. These combo washes are counted in `total_car_count` but not in `retail_car_count` or `member_car_count`. For exact free wash counts, use `client.query()` against `FCT_WASHES` directly.

### Use Case — Member Mix Ratio

Calculate what percentage of washes are from members:

```python
total = client.stats.total_car_count("2026-02-01", "2026-02-28")
member = client.stats.member_car_count("2026-02-01", "2026-02-28")

member_pct = member.total / total.total * 100
print(f"Member mix: {member_pct:.1f}%")  # ~60.4%
```

---

## Revenue

### Retail Revenue

Revenue from retail (non-member) wash transactions only. NM&R and RM&R combo revenue is **excluded** — those dollars are membership revenue.

```python
result = client.stats.retail_revenue("2026-02-01", "2026-02-28")
print(f"Revenue: ${result.total:,.2f}")              # $1,410,932.00
print(f"Transactions: {result.transaction_count:,}")  # 97,865
```

The `by_location` breakdown shows revenue per site:

```python
for loc in result.by_location:
    print(f"{loc.location_name}: ${loc.value:,.2f}")
# Burbank: $98,234.50
# Des Plaines: $87,654.30
# ...
```

### Membership Revenue

Revenue from membership billing — both new sales and renewals — with a breakdown:

```python
result = client.stats.membership_revenue("2026-02-01", "2026-02-28")
print(f"Total membership revenue: ${result.total:,.2f}")       # $1,233,481.74
print(f"  New member revenue:     ${result.new_revenue:,.2f}")  # $134,383.54
print(f"  Renewal revenue:        ${result.renewal_revenue:,.2f}")  # $1,099,098.20
```

!!! info "Revenue sources"
    - **New revenue**: `new membership` + `rejoin membership` from `FCT_MEMBERSHIPS`
    - **Renewal revenue**: `renewed membership` from `FCT_MEMBERSHIPS`
    - **Total**: sum of both

### Use Case — Total Revenue

Combine retail and membership revenue for total site revenue:

```python
retail = client.stats.retail_revenue("2026-02-01", "2026-02-28")
membership = client.stats.membership_revenue("2026-02-01", "2026-02-28")

total_revenue = retail.total + membership.total
print(f"Total revenue: ${total_revenue:,.2f}")
print(f"  Retail: ${retail.total:,.2f} ({retail.total/total_revenue:.1%})")
print(f"  Membership: ${membership.total:,.2f} ({membership.total/total_revenue:.1%})")
```

### Average Wash Price (AWP)

The retail ticket average: `retail_revenue / retail_car_count`. This tells you what the average non-member customer pays per wash.

```python
result = client.stats.average_wash_price("2026-02-01", "2026-02-28")
print(f"AWP: ${result.awp:.2f}")                    # $14.42
print(f"Retail revenue: ${result.retail_revenue:,.2f}")  # $1,410,932.00
print(f"Retail cars: {result.retail_car_count:,}")    # 97,865
```

!!! warning "Zero retail washes"
    If there are zero retail washes in the period (e.g., a location with only members), AWP returns `0.0` rather than raising a division error.

### Use Case — AWP by Location

AWP is only available as an aggregate. To get per-location AWP, use the component methods:

```python
rev = client.stats.retail_revenue("2026-02-01", "2026-02-28")
cars = client.stats.retail_car_count("2026-02-01", "2026-02-28")

rev_map = {loc.location_name: loc.value for loc in rev.by_location}
cars_map = {loc.location_name: loc.value for loc in cars.by_location}

for name in sorted(rev_map):
    r = rev_map[name]
    c = cars_map.get(name, 0)
    awp = r / c if c > 0 else 0
    print(f"{name}: ${awp:.2f} ({c:,.0f} cars, ${r:,.2f} revenue)")
```

---

## Membership Sales

### New Membership Sales

Count of new and rejoin membership transactions from `FCT_MEMBERSHIPS`. Includes both brand-new members and members who previously cancelled and came back.

```python
result = client.stats.new_membership_sales("2026-02-01", "2026-02-28")
print(f"New members: {result.total:,}")              # 8,479
print(f"Revenue: ${result.total_revenue:,.2f}")       # $134,383.54
```

Per-location breakdown:

```python
for loc in result.by_location:
    print(f"{loc.location_name}: {loc.value:,.0f} new members")
```

### Use Case — Revenue Per New Member

```python
result = client.stats.new_membership_sales("2026-02-01", "2026-02-28")
rev_per_member = result.total_revenue / result.total if result.total > 0 else 0
print(f"Average first-month revenue per new member: ${rev_per_member:.2f}")
```

---

## Conversion Rate

The percentage of eligible washes that convert into membership sales. Sourced from the pre-aggregated `CONVERSION_DAILY` table.

**Formula:** `conversion_rate = sales / eligible_washes`

```python
result = client.stats.conversion_rate("2026-02-01", "2026-02-28")
print(f"Rate: {result.rate:.1%}")            # 8.0%
print(f"Sales: {result.sales:,}")             # 8,479
print(f"Eligible: {result.eligible_washes:,}")  # 106,008
```

### Per-Location Conversion Rates

The `by_location` field contains each location's individual conversion rate (not a count):

```python
result = client.stats.conversion_rate("2026-02-01", "2026-02-28")

# Sort by conversion rate, highest first
ranked = sorted(result.by_location, key=lambda x: x.value, reverse=True)
for i, loc in enumerate(ranked, 1):
    print(f"{i}. {loc.location_name}: {loc.value:.1%}")
```

!!! info "What are eligible washes?"
    Eligible washes are non-member, non-free washes that had the opportunity to convert. This is a pre-calculated field in Rinsed's `CONVERSION_DAILY` table. It closely matches (but is not identical to) the retail car count from `FCT_REVENUE`.

### Edge Case — Zero Eligible Washes

Locations or periods with no eligible washes return a rate of `0.0`:

```python
# Querying a date when a location was closed
result = client.stats.conversion_rate("2026-12-25", "2026-12-25", locations="Fairview")
print(result.rate)  # 0.0
```

---

## Bundled Report

Get all KPIs (except churn) in a single call:

```python
report = client.stats.report("2026-02-01", "2026-02-28")

print(f"Total cars:        {report.total_car_count.total:,}")
print(f"Retail cars:       {report.retail_car_count.total:,}")
print(f"Member cars:       {report.member_car_count.total:,}")
print(f"Retail revenue:    ${report.retail_revenue.total:,.2f}")
print(f"Membership revenue:${report.membership_revenue.total:,.2f}")
print(f"AWP:               ${report.average_wash_price.awp:.2f}")
print(f"New sales:         {report.new_membership_sales.total:,}")
print(f"Conversion:        {report.conversion.rate:.1%}")
```

!!! tip "Performance"
    `report()` executes 8+ Snowflake queries internally (one per KPI, plus AWP calls retail_revenue and retail_car_count). For a single month, this typically takes 2-5 seconds depending on network latency.

### Use Case — Monthly Report Export

```python
import json

with RinsedClient() as client:
    report = client.stats.report("2026-02-01", "2026-02-28")

    # Export to JSON
    with open("feb_2026_kpis.json", "w") as f:
        f.write(report.model_dump_json(indent=2))
```

### Use Case — Month-Over-Month Comparison

```python
with RinsedClient() as client:
    jan = client.stats.report("2026-01-01", "2026-01-31")
    feb = client.stats.report("2026-02-01", "2026-02-28")

    car_change = (feb.total_car_count.total - jan.total_car_count.total) / jan.total_car_count.total
    rev_change = (feb.retail_revenue.total - jan.retail_revenue.total) / jan.retail_revenue.total
    conv_change = feb.conversion.rate - jan.conversion.rate

    print(f"Car count:  {car_change:+.1%}")
    print(f"Revenue:    {rev_change:+.1%}")
    print(f"Conversion: {conv_change:+.1%} pts")
```

### Use Case — Location Scoreboard

```python
with RinsedClient() as client:
    report = client.stats.report("2026-02-01", "2026-02-28")

    # Build per-location scoreboard from report components
    locations = set()
    for kpi in [report.total_car_count, report.retail_revenue, report.conversion]:
        for loc in kpi.by_location:
            locations.add(loc.location_name)

    cars_map = {l.location_name: l.value for l in report.total_car_count.by_location}
    rev_map = {l.location_name: l.value for l in report.retail_revenue.by_location}
    conv_map = {l.location_name: l.value for l in report.conversion.by_location}

    print(f"{'Location':<16} {'Cars':>8} {'Revenue':>12} {'Conv':>8}")
    print("-" * 46)
    for loc in sorted(locations):
        cars = cars_map.get(loc, 0)
        rev = rev_map.get(loc, 0)
        conv = conv_map.get(loc, 0)
        print(f"{loc:<16} {cars:>8,.0f} ${rev:>10,.2f} {conv:>7.1%}")
```

---

## Batch Daily KPIs

Fetch all non-churn KPIs at daily × location granularity in just **4 Snowflake queries** — regardless of date range or number of locations. Ideal for bulk data pipelines, backfills, and dashboard sync.

```python
result = client.stats.daily_kpis("2026-03-01", "2026-03-07")
print(f"{result.day_count} days × {result.location_count} locations = {len(result.rows)} rows")
# 7 days × 15 locations = 105 rows
```

Each row is a `DailyKPIRow` containing raw component values for one location on one day:

```python
for row in result.rows[:3]:
    print(f"{row.date} {row.location_name}: "
          f"cars={row.total_car_count} "
          f"retail=${row.retail_revenue:,.2f} "
          f"membership=${row.membership_revenue:,.2f}")
# 2026-03-01 Berwyn: cars=658 retail=$1,102.00 membership=$5,740.20
# 2026-03-01 Burbank: cars=1,296 retail=$2,348.00 membership=$7,014.30
# ...
```

### Available Fields

| Field | Type | Source Table |
|-------|------|-------------|
| `total_car_count` | int | CONVERSION_DAILY |
| `retail_car_count` | int | FCT_REVENUE |
| `member_car_count` | int | FCT_WASHES |
| `retail_revenue` | float | FCT_REVENUE |
| `retail_transaction_count` | int | FCT_REVENUE |
| `membership_revenue` | float | FCT_MEMBERSHIPS |
| `membership_revenue_new` | float | FCT_MEMBERSHIPS |
| `membership_revenue_renewal` | float | FCT_MEMBERSHIPS |
| `membership_sales` | int | FCT_MEMBERSHIPS |
| `membership_sales_revenue` | float | FCT_MEMBERSHIPS |
| `eligible_washes` | int | CONVERSION_DAILY |
| `conversion_sales` | int | CONVERSION_DAILY |

### Derived Metrics

AWP and conversion rate are left to the consumer to avoid division-by-zero in the data layer:

```python
for row in result.rows:
    awp = row.retail_revenue / row.retail_car_count if row.retail_car_count else 0
    conv = row.conversion_sales / row.eligible_washes if row.eligible_washes else 0
    print(f"{row.date} {row.location_name}: AWP=${awp:.2f} Conv={conv:.1%}")
```

### Performance

| Range | Rows | Time |
|-------|------|------|
| 1 day | ~15 | ~2s |
| 1 week | ~105 | ~1.5s |
| 1 month | ~420 | ~1.5s |
| 1 year | ~5,400 | ~4s |

!!! tip "vs. report()"
    `report()` returns KPIs aggregated over the entire period. `daily_kpis()` returns them at daily granularity — one row per location per day. Use `daily_kpis()` when you need to import daily data into a database or build time-series charts.

!!! info "Churn excluded"
    Churn is a monthly metric based on billing cycles, not a daily one. Use `voluntary_churn_rate()` / `involuntary_churn_rate()` separately for churn data.

### Use Case — Bulk Database Import

```python
import sqlite3

with RinsedClient() as client:
    result = client.stats.daily_kpis("2025-01-01", "2026-03-29")

    conn = sqlite3.connect("kpis.db")
    for row in result.rows:
        awp = row.retail_revenue / row.retail_car_count if row.retail_car_count else 0
        conn.execute(
            "INSERT OR REPLACE INTO kpi_data (date, location, kpi, value) VALUES (?, ?, ?, ?)",
            (row.date, row.location_name, 'car_count', row.total_car_count),
        )
        # ... repeat for other KPIs
    conn.commit()
```

### Use Case — Monthly Aggregation from Daily Data

```python
from collections import defaultdict

result = client.stats.daily_kpis("2026-01-01", "2026-03-29")

monthly = defaultdict(lambda: defaultdict(float))
for row in result.rows:
    month = row.date[:7]  # "2026-01"
    monthly[month]['membership_rev'] += row.membership_revenue
    monthly[month]['retail_rev'] += row.retail_revenue

for month in sorted(monthly):
    m = monthly[month]
    print(f"{month}: membership=${m['membership_rev']:,.2f} retail=${m['retail_rev']:,.2f}")
```

---

## Daily Cancellations

Get daily cancellation counts (both voluntary and involuntary) using Rinsed's real-time `churn_date` — the day the cancellation or expiry was recorded.

```python
result = client.stats.cancellations("2026-03-01", "2026-03-18")
print(f"Total: {result.total:,}")
print(f"Voluntary: {result.total_voluntary:,}")
print(f"Involuntary: {result.total_involuntary:,}")
```

### Daily Breakdown

Each day includes voluntary, involuntary, and total counts:

```python
result = client.stats.cancellations("2026-03-01", "2026-03-18")

for day in result.days:
    print(f"{day.date}: {day.voluntary:>4} vol, {day.involuntary:>4} invol, {day.total:>4} total")
# 2026-03-01:  166 vol,   26 invol,  192 total
# 2026-03-02:  166 vol,   23 invol,  189 total
# ...
```

### Per-Location Totals

The `by_location` field shows total cancellations (both types) per location for the period:

```python
ranked = sorted(result.by_location, key=lambda x: x.value, reverse=True)
for loc in ranked:
    print(f"{loc.location_name}: {loc.value:,.0f} cancellations")
```

!!! info "Cancellations vs. monthly churn methods"
    `cancellations()` uses **Rinsed's real-time dates** — the day the event was recorded. The monthly `voluntary_churn_rate()` and `involuntary_churn_rate()` methods use **WashU's shifted billing-cycle definition**. These are complementary views of the same underlying data.

### Use Case — Weekly Cancellation Summary

```python
from datetime import datetime, timedelta

with RinsedClient() as client:
    result = client.stats.cancellations("2026-03-01", "2026-03-14")

    # Group by week
    for day in result.days:
        dt = datetime.fromisoformat(day.date)
        week = dt.isocalendar()[1]
        print(f"Week {week}: {day.date} — {day.total} cancellations")
```

### Use Case — Cancellations for a Single Location

```python
result = client.stats.cancellations(
    "2026-03-01", "2026-03-18",
    locations="Naperville",
)
print(f"Naperville cancellations: {result.total}")
for day in result.days:
    print(f"  {day.date}: {day.total}")
```

---

## Daily Churn

Same daily data as `cancellations()`, plus the active member denominator for computing an overall churn rate. Useful when you want to see both the raw counts and the rate in context.

```python
result = client.stats.daily_churn("2026-03-01", "2026-03-18")
print(f"Churned: {result.total_churned:,}")
print(f"Starting members: {result.starting_count:,}")
print(f"Churn rate: {result.rate:.2%}")
```

### Per-Location Churn Rates

The `by_location` field shows churn **rates** (not counts) per location:

```python
ranked = sorted(result.by_location, key=lambda x: x.value, reverse=True)
for loc in ranked[:5]:
    print(f"{loc.location_name}: {loc.value:.2%}")
```

### Daily Breakdown

The `days` field is identical to `cancellations()` — daily voluntary/involuntary/total counts:

```python
for day in result.days:
    print(f"{day.date}: {day.total} churned")
```

!!! note
    The `rate` and `by_location` rates use the **previous month's** active member count as the denominator (from `ACTIVE_MEMBERS_MONTHLY`). The `days` breakdown uses Rinsed's real-time `churn_date`.

---

## Edge Cases & Known Nuances

### Combo Transactions (NM&R / RM&R)

When a customer buys or renews a membership and gets a wash in the same transaction:

- The **wash** counts as a member wash (in `member_car_count` via `FCT_WASHES`)
- The **revenue** goes to membership revenue (in `membership_revenue` via `FCT_MEMBERSHIPS`)
- It does **not** appear in `retail_car_count` or `retail_revenue`

### Family Plans

Locations with significant family plan populations (notably Dickson and Fairview) have many $0 renewal records. When a family plan renews, the primary member is billed the full amount and each additional family member gets a $0 renewal row. All individual family members are counted in membership counts.

### DRB to Sonny's POS Migration

Illinois locations transitioned from DRB to Sonny's POS in two phases:

- **Phase 1** (Dec 2024 / Jan 2025): First group of IL sites
- **Phase 2** (Apr / May 2025): Plainfield, Burbank, Berwyn, Joliet, Evergreen Park

During migration months, there may be slight discrepancies due to overlapping location IDs. Data outside migration months is unaffected.

### Snowflake Data Freshness

Snowflake data is **not real-time**. There is typically a 24-48 hour lag before data appears. For real-time data, use the [Sonny's Data API Client](https://christopher-nance.github.io/Sonnys-Data-API-Client/).
