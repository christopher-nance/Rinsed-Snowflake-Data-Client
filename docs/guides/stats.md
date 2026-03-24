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
