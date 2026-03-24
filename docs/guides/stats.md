# Stats & KPIs

All KPI methods are accessed via `client.stats`.

## Car Counts

### Total Car Count

Total washes across all types (retail + member + free), sourced from `CONVERSION_DAILY`.

```python
result = client.stats.total_car_count("2026-02-01", "2026-02-28")
print(f"Total washes: {result.total:,}")
```

### Retail Car Count

Non-member, paid wash transactions from `FCT_REVENUE`. Excludes NM&R and RM&R combo transactions (those are membership washes).

```python
result = client.stats.retail_car_count("2026-02-01", "2026-02-28")
print(f"Retail washes: {result.total:,}")
```

### Member Car Count

Membership redemptions (member scanned their unlimited pass) from `FCT_WASHES`.

```python
result = client.stats.member_car_count("2026-02-01", "2026-02-28")
print(f"Member washes: {result.total:,}")
```

## Revenue

### Retail Revenue

Revenue from retail (non-member) wash transactions only. NM&R and RM&R combo revenue is excluded — those dollars are membership revenue.

```python
result = client.stats.retail_revenue("2026-02-01", "2026-02-28")
print(f"Revenue: ${result.total:,.2f}")
print(f"Transactions: {result.transaction_count:,}")
```

### Membership Revenue

Revenue from new + renewed membership billing, with a breakdown:

```python
result = client.stats.membership_revenue("2026-02-01", "2026-02-28")
print(f"Total: ${result.total:,.2f}")
print(f"New member revenue: ${result.new_revenue:,.2f}")
print(f"Renewal revenue: ${result.renewal_revenue:,.2f}")
```

### Average Wash Price (AWP)

Retail ticket average: `retail_revenue / retail_car_count`.

```python
result = client.stats.average_wash_price("2026-02-01", "2026-02-28")
print(f"AWP: ${result.awp:.2f}")
```

## Membership Sales

### New Membership Sales

Count of new + rejoin membership transactions from `FCT_MEMBERSHIPS`.

```python
result = client.stats.new_membership_sales("2026-02-01", "2026-02-28")
print(f"New members: {result.total:,}")
print(f"Revenue: ${result.total_revenue:,.2f}")
```

## Conversion Rate

Sales / eligible washes, sourced from the pre-aggregated `CONVERSION_DAILY` table.

```python
result = client.stats.conversion_rate("2026-02-01", "2026-02-28")
print(f"Rate: {result.rate:.1%}")
print(f"Sales: {result.sales:,}")
print(f"Eligible: {result.eligible_washes:,}")

# Per-location conversion rates
for loc in result.by_location:
    print(f"  {loc.location_name}: {loc.value:.1%}")
```

## Bundled Report

Get all KPIs in a single call:

```python
report = client.stats.report("2026-02-01", "2026-02-28")

print(f"Total cars: {report.total_car_count.total:,}")
print(f"Retail cars: {report.retail_car_count.total:,}")
print(f"Member cars: {report.member_car_count.total:,}")
print(f"Retail revenue: ${report.retail_revenue.total:,.2f}")
print(f"Membership revenue: ${report.membership_revenue.total:,.2f}")
print(f"AWP: ${report.average_wash_price.awp:.2f}")
print(f"New sales: {report.new_membership_sales.total:,}")
print(f"Conversion: {report.conversion.rate:.1%}")
```

!!! tip
    `report()` makes multiple Snowflake queries internally. For dashboards where you need all KPIs, this is more convenient than calling each method individually.
