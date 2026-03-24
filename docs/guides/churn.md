# Churn Rates

## WashU Churn Definition

This client uses WashU's billing-cycle churn definition, which differs from Rinsed's real-time recording:

- **Rinsed** records churn on the day the cancellation or expiry happens
- **WashU** recognizes churn when the would-be recharge doesn't process (one billing cycle later)

**Example:** A member buys on 1/12, gets recharged on 2/12, then cancels on 2/23. Rinsed records the churn in February. WashU reports it in March — when the 3/12 recharge would have occurred but didn't, since the member cancelled.

The rationale: a member who was billed for the month has already paid, so they're still a member for that month. Their departure is recognized the following month.

!!! info
    WashU's churn numbers for any given month are equivalent to Rinsed's churn numbers from the **previous** month, shifted forward by one billing cycle.

## Churn Types

### Voluntary Churn

Member-initiated cancellations (`terminated` in Rinsed).

```python
result = client.stats.voluntary_churn_rate("2026-02-01", "2026-02-28")
print(f"Rate: {result.rate:.2%}")
print(f"Churned: {result.churned_count:,}")
print(f"Starting members: {result.starting_count:,}")
```

### Involuntary Churn

Expired memberships due to failed payments (`expired` in Rinsed).

```python
result = client.stats.involuntary_churn_rate("2026-02-01", "2026-02-28")
print(f"Rate: {result.rate:.2%}")
print(f"Churned: {result.churned_count:,}")
```

## Per-Location Breakdown

Both churn methods include a `by_location` breakdown with per-location churn rates:

```python
result = client.stats.voluntary_churn_rate("2026-02-01", "2026-02-28")

for loc in result.by_location:
    print(f"{loc.location_name}: {loc.value:.2%}")
```

## How It's Calculated

**Numerator:** Count of distinct members from `MEMBER_HISTORY` whose last billing (`created_month`) was in the month before the requested period and who have a churn record.

**Denominator:** Active members from `ACTIVE_MEMBERS_MONTHLY` (Rinsed definition) for the month before the requested period.

**Rate:** `churned_count / starting_count`

## Comparing to Rinsed

Since the WashU definition is Rinsed's numbers shifted by one month:

| WashU Month | Equals Rinsed Month |
|-------------|-------------------|
| February 2026 churn | January 2026 churn |
| March 2026 churn | February 2026 churn |
| April 2026 churn | March 2026 churn |
