# Rinsed Snowflake Data Client

Python client for WashU Carwash Rinsed CRM data in Snowflake.

Provides fast, bulk access to historical KPI data via Snowflake — complementing the [Sonny's Data API Client](https://christopher-nance.github.io/Sonnys-Data-API-Client/) which is best suited for real-time data pulls.

## Why This Client?

The Sonny's Data API has strict rate limits (20 requests per 15 seconds). For bulk historical analysis — monthly reports, trend analysis, churn tracking — Snowflake is significantly faster. This client mirrors the Sonny's client patterns (`client.stats.*`) so the API feels familiar.

## Quick Start

```python
from rinsed_snowflake_client import RinsedClient

with RinsedClient() as client:
    # Car counts
    cars = client.stats.total_car_count("2026-01-01", "2026-01-31")
    print(f"Total washes: {cars.total}")

    # Revenue
    rev = client.stats.retail_revenue("2026-01-01", "2026-01-31")
    print(f"Retail revenue: ${rev.total:,.2f}")

    # Conversion rate
    conv = client.stats.conversion_rate("2026-01-01", "2026-01-31")
    print(f"Conversion: {conv.rate:.1%}")

    # All KPIs at once
    report = client.stats.report("2026-01-01", "2026-01-31")
```

## Installation

```bash
pip install git+https://github.com/christopher-nance/Rinsed-Snowflake-Data-Client.git
```

Or from source for development:

```bash
git clone https://github.com/christopher-nance/Rinsed-Snowflake-Data-Client.git
cd Rinsed-Snowflake-Data-Client
pip install -e ".[dev]"
```

## Available KPIs

All methods are on `client.stats` and accept `start`, `end`, and optional `locations`:

| Method | Returns | Description |
|--------|---------|-------------|
| [`total_car_count()`](api/client.md) | `CarCountResult` | Total washes (retail + member + free) |
| [`retail_car_count()`](api/client.md) | `CarCountResult` | Retail (non-member) wash count |
| [`member_car_count()`](api/client.md) | `CarCountResult` | Membership redemption count |
| [`retail_revenue()`](api/client.md) | `RevenueResult` | Revenue from retail washes |
| [`membership_revenue()`](api/client.md) | `MembershipRevenueResult` | Revenue from memberships (new + renewed) |
| [`average_wash_price()`](api/client.md) | `AWPResult` | Retail ticket average |
| [`new_membership_sales()`](api/client.md) | `MembershipSalesResult` | New + rejoin membership count |
| [`conversion_rate()`](api/client.md) | `ConversionResult` | Sales / eligible washes |
| [`voluntary_churn_rate()`](guides/churn.md) | `ChurnResult` | Member-initiated cancellations |
| [`involuntary_churn_rate()`](guides/churn.md) | `ChurnResult` | Expired / failed payment churn |
| [`report()`](api/client.md) | `StatsReport` | All KPIs bundled |
