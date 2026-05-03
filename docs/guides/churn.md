# Churn Rates

## WashU vs. Rinsed Churn Definition

This client uses **WashU's billing-cycle churn definition**, which intentionally differs from Rinsed's real-time recording:

| | Rinsed | WashU (this client) |
|---|---|---|
| **When churn is recorded** | The day the cancellation or expiry happens | The month when the would-be recharge doesn't process |
| **Example** | Member billed 2/12, cancels 2/23 → **February** churn | Same member → **March** churn (3/12 recharge never happens) |
| **Rationale** | Reflects real-time system state | Member paid for February, so they're a February member |

**The key insight:** WashU's churn for month M is equivalent to Rinsed's churn for month M-1, shifted forward by one billing cycle.

| WashU Churn Month | Equals Rinsed Churn Month |
|-------------------|--------------------------|
| February 2026 | January 2026 |
| March 2026 | February 2026 |
| April 2026 | March 2026 |

!!! info
    If you're comparing this client's churn output to Rinsed's dashboard, expect a one-month offset. The totals over a multi-month window will be the same — just shifted.

## Churn Types

### Voluntary Churn

Member-initiated cancellations. The member chose to cancel their membership. In Rinsed's database, these are recorded as `churn_type = 'terminated'`.

```python
result = client.stats.voluntary_churn_rate("2026-02-01", "2026-02-28")

print(f"Voluntary churn rate: {result.rate:.2%}")    # 5.68%
print(f"Members who churned: {result.churned_count:,}")  # 2,271
print(f"Starting member base: {result.starting_count:,}")  # 39,976
```

### Involuntary Churn

Expired memberships due to failed payments — the member didn't actively cancel, but their payment method failed. In Rinsed's database, these are recorded as `churn_type = 'expired'`.

```python
result = client.stats.involuntary_churn_rate("2026-02-01", "2026-02-28")

print(f"Involuntary churn rate: {result.rate:.2%}")  # 1.59%
print(f"Members who churned: {result.churned_count:,}")  # 637
print(f"Starting member base: {result.starting_count:,}")  # 39,976
```

### Combined Churn

To get total churn, call both methods and combine:

```python
vol = client.stats.voluntary_churn_rate("2026-02-01", "2026-02-28")
inv = client.stats.involuntary_churn_rate("2026-02-01", "2026-02-28")

total_churned = vol.churned_count + inv.churned_count
total_rate = total_churned / vol.starting_count  # same denominator
print(f"Total churn: {total_rate:.2%} ({total_churned:,} members)")
```

## Per-Location Breakdown

Both churn methods include a `by_location` list with per-location churn rates:

```python
result = client.stats.voluntary_churn_rate("2026-02-01", "2026-02-28")

# Rank locations by churn rate (highest first)
ranked = sorted(result.by_location, key=lambda x: x.value, reverse=True)
for loc in ranked:
    print(f"{loc.location_name}: {loc.value:.2%}")
# Naperville: 14.74%
# Berwyn: 11.89%
# Evergreen Park: 11.03%
# ...
```

!!! note
    The `value` field in `by_location` is the **churn rate** for that location (not the count). Each location has its own denominator based on its active member count.

## How It's Calculated

### Numerator (Churned Members)

From `MEMBER_HISTORY`: count of distinct members whose `created_month` (last billing month) was the month **before** the requested period and who have a `churn_type` set.

**Why the previous month?** Under WashU's definition, a member billed in January who cancels in January is still a January member. Their churn is recognized in February — when their would-be recharge doesn't happen.

### Denominator (Starting Member Base)

From `ACTIVE_MEMBERS_MONTHLY` (Rinsed definition): total active members for the month **before** the requested period. This represents the member base that was "at risk" of churning.

### Formula

```
churn_rate = churned_count / starting_count
```

Where:

- `churned_count` = members last billed in month M-1 with `churn_type` set
- `starting_count` = active members in month M-1

## Use Cases

### Monthly Churn Trend

```python
from datetime import datetime

with RinsedClient() as client:
    months = [
        ("2025-10-01", "2025-10-31"),
        ("2025-11-01", "2025-11-30"),
        ("2025-12-01", "2025-12-31"),
        ("2026-01-01", "2026-01-31"),
        ("2026-02-01", "2026-02-28"),
    ]

    print(f"{'Month':<12} {'Voluntary':>10} {'Involuntary':>12} {'Total':>8}")
    print("-" * 44)

    for start, end in months:
        vol = client.stats.voluntary_churn_rate(start, end)
        inv = client.stats.involuntary_churn_rate(start, end)
        total = (vol.churned_count + inv.churned_count) / vol.starting_count
        label = datetime.fromisoformat(start).strftime("%b %Y")
        print(f"{label:<12} {vol.rate:>9.2%} {inv.rate:>11.2%} {total:>7.2%}")
```

### Location-Level Churn Report

```python
with RinsedClient() as client:
    vol = client.stats.voluntary_churn_rate("2026-02-01", "2026-02-28")
    inv = client.stats.involuntary_churn_rate("2026-02-01", "2026-02-28")

    vol_map = {l.location_name: l.value for l in vol.by_location}
    inv_map = {l.location_name: l.value for l in inv.by_location}

    print(f"{'Location':<16} {'Voluntary':>10} {'Involuntary':>12} {'Total':>8}")
    print("-" * 48)
    for loc in sorted(vol_map):
        v = vol_map[loc]
        i = inv_map.get(loc, 0)
        print(f"{loc:<16} {v:>9.2%} {i:>11.2%} {v+i:>7.2%}")
```

### Retention Rate

Retention is the inverse of churn:

```python
vol = client.stats.voluntary_churn_rate("2026-02-01", "2026-02-28")
inv = client.stats.involuntary_churn_rate("2026-02-01", "2026-02-28")

total_churn = (vol.churned_count + inv.churned_count) / vol.starting_count
retention = 1 - total_churn
print(f"Retention rate: {retention:.2%}")
```

### Annualized Churn

```python
result = client.stats.voluntary_churn_rate("2026-02-01", "2026-02-28")
annual = 1 - (1 - result.rate) ** 12
print(f"Annualized voluntary churn: {annual:.1%}")
```

## Edge Cases

### Month Boundary

Churn methods operate on **monthly** boundaries. The `start` date determines which month is used:

```python
# Both of these query the same churn data (February churn = members last billed in January)
client.stats.voluntary_churn_rate("2026-02-01", "2026-02-28")
client.stats.voluntary_churn_rate("2026-02-15", "2026-02-28")  # same result
```

The `start` date's month is what matters. The `end` date is not used for churn calculations — it's included in the result metadata for consistency.

### New Locations

Locations that didn't exist in the previous month will have zero starting members and won't appear in churn results. They'll start appearing once they have a full month of active member data.

### Wheaton

Wheaton is not present in all churn validation data due to its later onboarding. The client will return data for Wheaton when available in the underlying tables.

### Small Locations

Locations with very few members (e.g., Jackson with ~290) can show volatile churn rates. A single cancellation has an outsized impact on the percentage. Consider this when comparing locations of different sizes.

---

## Recharge Churn (WashU Daily Methodology)

`recharge_churn()` provides **daily churn measurement** based on WashU's recharge methodology. Unlike the monthly methods above, this gives you a churn number for every day in a date range.

### How It Works

For each day D in the requested range:

1. **Denominator** = count of (recharges + new members) on the **same calendar day one month prior**
2. **Retained** = count of recharges-only on day D (new members excluded)
3. **Churned** = denominator - retained
4. **Churn rate** = churned / denominator

```
Jan 15: 1,200 recharges + 80 new = 1,280 denominator
Feb 15: 1,190 recharges (retained)
         → Churned: 1,280 - 1,190 = 90
         → Churn rate: 90 / 1,280 = 7.03%
```

The **cumulative churn rate** across a period is:

```
cumulative = sum(churned across all days) / sum(denominators across all days)
```

### Stripe-Style Anniversary Billing

Date matching uses Snowflake's `DATEADD(MONTH, 1, ...)`, which follows Stripe's anniversary billing convention:

- The billing date **clamps to end-of-month** in short months
- The **original day returns** in longer months

| Prior Month Date | Expected Recharge Date | Why |
|---|---|---|
| Jan 15 | Feb 15 | Same day, both months have it |
| Jan 31 | Feb 28 | Feb has no 31st — clamp to last day |
| Feb 28 | Mar 28 | Same day (but see note below) |
| Mar 31 | Apr 30 | Apr has no 31st — clamp to last day |
| Apr 30 | May 30 | Same day |

!!! info "End-of-month edge case (days 29-31)"
    Members whose anchor billing day is 29, 30, or 31 get clamped to the last day of short months (e.g., Jan 31 → Feb 28). When moving from a short month to a long month, `DATEADD` maps Feb 28 → Mar 28, even though Stripe would return the member to Mar 31. At the aggregate level without member-level ID tracking, we cannot distinguish "genuine 28th billers" from "clamped 31st billers" in February's data.

    **Impact:** Daily rates on the 28th of months following February may be slightly distorted. March 29-31 may show recharges with no matching denominator. **Monthly aggregates are unaffected** — the same total number of prior-month transactions map to the same total number of current-month recharges.

### Basic Usage

```python
result = client.stats.recharge_churn("2026-03-01", "2026-03-31")
print(f"Denominator: {result.total_denominator:,}")       # 51,318
print(f"Retained:    {result.total_retained:,}")           # 47,593
print(f"Churned:     {result.total_churned:,}")            # 3,725
print(f"Churn rate:  {result.cumulative_churn_rate:.2%}")  # 7.26%
```

### Daily Breakdown

Each day includes the denominator, retained, churned, rate, and voluntary/involuntary counts:

```python
result = client.stats.recharge_churn("2026-03-01", "2026-03-31")

for day in result.days[:5]:
    print(f"{day.date}: denom={day.denominator:,} ret={day.retained:,} "
          f"ch={day.churned:,} rate={day.churn_rate:.2%} "
          f"vol={day.voluntary} inv={day.involuntary}")
# 2026-03-01: denom=2,033 ret=1,891 ch=142 rate=6.98% vol=165 inv=24
# 2026-03-02: denom=1,925 ret=1,812 ch=113 rate=5.87% vol=165 inv=24
# ...
```

### Voluntary / Involuntary Overlay

The `voluntary` and `involuntary` fields on each day come from `MEMBER_HISTORY` grouped by `churn_date` (the date the cancellation or expiry event was recorded in Rinsed).

!!! warning "Different date definitions"
    The recharge methodology's `churned` count is based on the **missed billing date** (the day the member was expected to recharge but didn't). The `voluntary`/`involuntary` counts are based on the **cancellation event date** from `MEMBER_HISTORY`.

    These are different dates for the same event: a member who cancels on Feb 20 shows as `voluntary` on Feb 20, but shows as `churned` on Mar 15 (when their expected recharge doesn't happen).

    On any given day, `voluntary + involuntary` will NOT equal `churned`. Over a full month, the totals are generally close but not identical.

### Per-Location Churn Rates

```python
result = client.stats.recharge_churn("2026-03-01", "2026-03-31")

ranked = sorted(result.by_location, key=lambda x: x.value, reverse=True)
for loc in ranked[:5]:
    print(f"{loc.location_name}: {loc.value:.2%}")
```

### Flexible Date Ranges

Unlike the monthly churn methods, `recharge_churn()` works with any date range:

```python
# Single day
result = client.stats.recharge_churn("2026-03-15", "2026-03-15")

# One week
result = client.stats.recharge_churn("2026-03-01", "2026-03-07")

# Full quarter
result = client.stats.recharge_churn("2026-01-01", "2026-03-31")
```

### Negative Churned Values

In months where the business is growing rapidly, `churned` can be negative — meaning more members recharged than the prior month's pool. This is net growth exceeding churn and is a healthy signal.

```python
result = client.stats.recharge_churn("2025-05-01", "2025-05-31")
print(result.total_churned)  # -46 (negative = net growth exceeded churn)
```

### Denominator Difference vs Rinsed/MAOM

The recharge method's denominator (prior month recharges + new members) differs from the Rinsed dashboard/MAOM denominator (active member count). These are intentionally different measures:

| | Recharge Method | Rinsed / MAOM |
|---|---|---|
| **Denominator** | Prior month billing transactions | Active member count |
| **Granularity** | Daily | Monthly |
| **Best for** | Day-level churn tracking, cohort analysis | Monthly reporting, frontend tie-outs |
