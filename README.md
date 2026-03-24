# Rinsed Snowflake Data Client

Python client for WashU Carwash Rinsed CRM data in Snowflake.

## Installation

```bash
pip install rinsed-snowflake-client
```

Or install from source:

```bash
pip install -e ".[dev]"
```

## Quick Start

```python
from rinsed_snowflake_client import RinsedClient

# Credentials loaded from environment variables
with RinsedClient() as client:
    # Car counts
    cars = client.stats.total_car_count("2026-01-01", "2026-01-31")
    print(f"Total washes: {cars.total}")
    for loc in cars.by_location:
        print(f"  {loc.location_name}: {loc.value}")

    # Revenue
    rev = client.stats.retail_revenue("2026-01-01", "2026-01-31")
    print(f"Retail revenue: ${rev.total:,.2f}")

    # Average Wash Price
    awp = client.stats.average_wash_price("2026-01-01", "2026-01-31")
    print(f"AWP: ${awp.awp:.2f}")

    # Conversion rate
    conv = client.stats.conversion_rate("2026-01-01", "2026-01-31")
    print(f"Conversion: {conv.rate:.1%}")

    # All KPIs at once
    report = client.stats.report("2026-01-01", "2026-01-31")

    # Raw SQL (returns pandas DataFrame)
    df = client.query("SELECT * FROM conversion_daily LIMIT 10")
```

## Configuration

Set the following environment variables (or pass to `RinsedClient` directly):

| Variable | Required | Description |
|----------|----------|-------------|
| `SNOWFLAKE_ACCOUNT` | Yes | Snowflake account identifier |
| `SNOWFLAKE_USER` | Yes | Username |
| `SNOWFLAKE_PASSWORD` | Yes | Password |
| `SNOWFLAKE_WAREHOUSE` | Yes | Warehouse name |
| `SNOWFLAKE_DATABASE` | Yes | Database name |
| `SNOWFLAKE_SCHEMA` | Yes | Schema name |
| `SNOWFLAKE_ROLE` | No | Role name |

## Available KPI Methods

All methods are on `client.stats` and accept `start`, `end`, and optional `locations`:

| Method | Returns | Description |
|--------|---------|-------------|
| `total_car_count()` | `CarCountResult` | Total washes (retail + member + free) |
| `retail_car_count()` | `CarCountResult` | Retail (non-member) wash count |
| `member_car_count()` | `CarCountResult` | Membership redemption count |
| `retail_revenue()` | `RevenueResult` | Revenue from retail washes |
| `membership_revenue()` | `MembershipRevenueResult` | Revenue from memberships (new + renewed) |
| `average_wash_price()` | `AWPResult` | Retail ticket average |
| `new_membership_sales()` | `MembershipSalesResult` | New + rejoin membership count |
| `conversion_rate()` | `ConversionResult` | Sales / eligible washes |
| `involuntary_churn_rate()` | `ChurnResult` | Expired memberships / failed payments |
| `voluntary_churn_rate()` | `ChurnResult` | Member-initiated cancellations |
| `report()` | `StatsReport` | All KPIs bundled |

## Location Filtering

```python
# All locations
client.stats.total_car_count("2026-01-01", "2026-01-31")

# Single location
client.stats.total_car_count("2026-01-01", "2026-01-31", locations="Burbank")

# Multiple locations
client.stats.total_car_count("2026-01-01", "2026-01-31", locations=["Burbank", "Carol Stream"])
```

Hub Office and Query Server are always excluded from results.
