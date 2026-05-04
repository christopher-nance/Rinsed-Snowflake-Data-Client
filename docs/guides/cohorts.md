# Cohort Retention Analysis

Cohort methods are accessed via `client.cohorts` and return pre-aggregated retention data from `MEMBER_HISTORY`. The data shape is designed for retention grids, survival curves, and plan-level comparisons.

```python
client.cohorts.retention_grid(start, end, locations=None)
client.cohorts.retention_by_plan(start, end, locations=None)
```

!!! info "Start/end filter by cohort month"
    Unlike other methods where `start`/`end` filter by transaction date, cohort methods filter by **cohort month** — when the member signed up. `retention_grid("2024-06-01", "2024-12-01")` returns all cohorts from June–December 2024 with their full retention history through today.

---

## Retention Grid

The core method. Returns one row per cohort per tenure period — the exact shape needed for a retention heatmap.

```python
result = client.cohorts.retention_grid("2025-01-01", "2025-03-01")
print(f"Cohorts: {result.cohort_count}")   # 3
print(f"Max tenure: {result.max_period}")  # 16 months
```

Each row contains:

| Field | Description |
|---|---|
| `cohort_month` | Signup month (first of month) |
| `period_month` | Tenure period (0 = signup month, 1 = first renewal, ...) |
| `members` | Members still billing at this period |
| `churned` | Members who churned during this period |
| `voluntary_churned` | Member-initiated cancellations |
| `involuntary_churned` | Payment failures |

### Reading the Grid

```python
result = client.cohorts.retention_grid("2025-01-01", "2025-01-31")

for row in result.rows[:6]:
    print(f"Period {row.period_month:2d}: {row.members:,} members, "
          f"{row.churned:,} churned "
          f"(vol={row.voluntary_churned}, inv={row.involuntary_churned})")
# Period  0: 3,265 members, 67 churned (vol=67, inv=0)
# Period  1: 3,052 members, 339 churned (vol=326, inv=13)
# Period  2: 2,749 members, 341 churned (vol=263, inv=78)
# Period  3: 2,368 members, 256 churned (vol=197, inv=59)
# Period  4: 2,035 members, 160 churned (vol=127, inv=33)
# Period  5: 1,865 members, 120 churned (vol=86, inv=34)
```

**Period 0** is the signup month — the initial cohort size. Each subsequent period shows how many members remain and how many left.

### Computing Retention Rate

Retention rate is left to the consumer. Divide any period's member count by the period 0 count:

```python
result = client.cohorts.retention_grid("2025-01-01", "2025-01-31")

# Find period 0 (initial size)
initial = next(r for r in result.rows if r.period_month == 0)

for row in result.rows:
    retention = row.members / initial.members
    print(f"Period {row.period_month:2d}: {retention:.1%}")
# Period  0: 100.0%
# Period  1: 93.5%
# Period  2: 84.2%
# Period  3: 72.5%
# ...
```

### Building a Retention Heatmap

For multiple cohorts, group by `cohort_month` and compute retention within each group:

```python
from collections import defaultdict

result = client.cohorts.retention_grid("2024-06-01", "2025-01-01")

# Group by cohort
cohorts = defaultdict(list)
for row in result.rows:
    cohorts[row.cohort_month].append(row)

# Build retention table
print(f"{'Cohort':<12} {'M0':>6} {'M1':>6} {'M2':>6} {'M3':>6} {'M6':>6} {'M12':>6}")
print("-" * 50)
for month in sorted(cohorts):
    periods = {r.period_month: r for r in cohorts[month]}
    initial = periods[0].members
    cols = [month[:7]]
    for p in [0, 1, 2, 3, 6, 12]:
        if p in periods:
            cols.append(f"{periods[p].members / initial:.0%}")
        else:
            cols.append("—")
    print(f"{cols[0]:<12} {cols[1]:>6} {cols[2]:>6} {cols[3]:>6} {cols[4]:>6} {cols[5]:>6} {cols[6]:>6}")
```

---

## Retention by Plan

Adds the `join_plan_name` dimension — the membership plan at the time of signup. Use this to compare retention across plan tiers or evaluate promo-driven plans.

```python
result = client.cohorts.retention_by_plan("2025-01-01", "2025-01-31", "Burbank")
print(f"Plans: {result.plan_count}")  # 7
```

Each row includes everything from the base grid plus `join_plan_name`:

```python
for row in result.rows:
    if row.period_month == 0:
        print(f"{row.join_plan_name}: {row.members} members")
# New Monthly Express: 123 members
# Monthly Clean '21: 60 members
# New Monthly Protect: 55 members
# Monthly UShine: 40 members
# ...
```

### Plan-Level Retention Comparison

```python
from collections import defaultdict

result = client.cohorts.retention_by_plan("2025-01-01", "2025-01-31")

# Group by plan
plans = defaultdict(dict)
for row in result.rows:
    plans[row.join_plan_name][row.period_month] = row

print(f"{'Plan':<35} {'Size':>6} {'M3':>6} {'M6':>6} {'M12':>6}")
print("-" * 60)
for plan in sorted(plans, key=lambda p: plans[p][0].members, reverse=True):
    periods = plans[plan]
    initial = periods[0].members
    m3 = f"{periods[3].members / initial:.0%}" if 3 in periods else "—"
    m6 = f"{periods[6].members / initial:.0%}" if 6 in periods else "—"
    m12 = f"{periods[12].members / initial:.0%}" if 12 in periods else "—"
    print(f"{plan[:35]:<35} {initial:>6} {m3:>6} {m6:>6} {m12:>6}")
```

### Promo Analysis

Filter a specific cohort month to evaluate a promotion's member quality:

```python
# March 2025 had a $9.95 promo — how did those members retain?
result = client.cohorts.retention_by_plan("2025-03-01", "2025-03-31")

promo_plans = [r for r in result.rows if "9.95" in r.join_plan_name]
regular_plans = [r for r in result.rows if "9.95" not in r.join_plan_name]

# Compare 6-month retention
for group, label in [(promo_plans, "Promo"), (regular_plans, "Regular")]:
    periods = {r.period_month: r for r in group}
    if 0 in periods and 6 in periods:
        ret = periods[6].members / periods[0].members
        print(f"{label}: {ret:.1%} retention at 6 months ({periods[0].members} initial)")
```

---

## Location Filtering

Both methods accept the standard `locations` parameter:

```python
# Single location
result = client.cohorts.retention_grid("2025-01-01", "2025-06-01", "Burbank")

# Multiple locations
result = client.cohorts.retention_grid(
    "2025-01-01", "2025-06-01",
    locations=["Burbank", "Plainfield", "Dickson"],
)
```

---

## Data Model

### How MEMBER_HISTORY Works

`MEMBER_HISTORY` is **not** a one-row-per-member table. It contains one row per member per billing period (~3M rows total). Key columns:

| Column | Description |
|---|---|
| `rinsed_membership_id` | Unique member identifier |
| `cohort_month` | First day of signup month |
| `join_date` | Exact signup date |
| `join_plan_name` | Plan at time of signup |
| `period_month` | Tenure: 0 = signup month, 1 = first renewal, etc. |
| `churn_period` | Tenure month when churn occurred (NULL if still active) |
| `churn_type` | `'terminated'` (voluntary) or `'expired'` (involuntary) |
| `churn_date` | Date of cancellation event |
| `location_name` | Member's location |

### Rejoins

Members can cancel and rejoin. Each membership stint is a separate entry — a member who signs up in January, cancels in April, and rejoins in September appears in both the January and September cohorts. This is intentional: it lets you evaluate promo-driven rejoins as their own cohort.

### Churned vs. Members Delta

The difference between `members[period N]` and `members[period N+1]` may not exactly equal `churned[period N]`. This happens because some members may drop out of the billing table without a formal churn event recorded. The `churned` count represents members with an explicit `churn_period` match — it's the reliable floor for churn measurement.

---

## SQLite Caching Pattern

The retention grid maps directly to a SQLite table for the connector:

```python
import sqlite3

with RinsedClient() as client:
    result = client.cohorts.retention_grid("2020-01-01", "2026-05-01")

    conn = sqlite3.connect("cohorts.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cohort_retention (
            cohort_month TEXT,
            period_month INTEGER,
            members INTEGER,
            churned INTEGER,
            voluntary_churned INTEGER,
            involuntary_churned INTEGER,
            PRIMARY KEY (cohort_month, period_month)
        )
    """)

    for row in result.rows:
        conn.execute(
            """INSERT OR REPLACE INTO cohort_retention
               VALUES (?, ?, ?, ?, ?, ?)""",
            (row.cohort_month, row.period_month, row.members,
             row.churned, row.voluntary_churned, row.involuntary_churned),
        )
    conn.commit()
```

For plan-level data, add `join_plan_name` to the schema and primary key.

### JSON Export

All result models serialize cleanly:

```python
result = client.cohorts.retention_grid("2025-01-01", "2025-06-01")

with open("retention_grid.json", "w") as f:
    f.write(result.model_dump_json(indent=2))
```

---

## Performance

| Query | Scope | Approx. Time |
|---|---|---|
| `retention_grid` | 1 month | ~2s |
| `retention_grid` | 1 year | ~3s |
| `retention_grid` | All time | ~5s |
| `retention_by_plan` | 1 month | ~3s |
| `retention_by_plan` | 1 year | ~5s |
| `retention_by_plan` | All time | ~8s |

Plan-level queries are slower due to the additional grouping dimension and higher row count.
