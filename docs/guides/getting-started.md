# Getting Started

## Configuration

The client needs Snowflake credentials. Set them as environment variables or pass them directly.

### Environment Variables

Create a `.env` file (see `.env.example`):

```
SNOWFLAKE_ACCOUNT=your_account_identifier
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=your_warehouse
SNOWFLAKE_DATABASE=your_database
SNOWFLAKE_SCHEMA=your_schema
SNOWFLAKE_ROLE=your_role  # optional
```

Load with `python-dotenv` before creating the client:

```python
from dotenv import load_dotenv
load_dotenv()

from rinsed_snowflake_client import RinsedClient

with RinsedClient() as client:
    result = client.stats.total_car_count("2026-01-01", "2026-01-31")
```

### Explicit Credentials

```python
client = RinsedClient(
    account="your_account",
    user="your_user",
    password="your_password",
    warehouse="your_warehouse",
    database="your_database",
    schema="your_schema",
    role="your_role",  # optional
)
client.connect()
# ... use client ...
client.close()
```

## Context Manager

The recommended pattern is to use `RinsedClient` as a context manager, which automatically connects and closes the Snowflake connection:

```python
with RinsedClient() as client:
    cars = client.stats.total_car_count("2026-01-01", "2026-01-31")
    rev = client.stats.retail_revenue("2026-01-01", "2026-01-31")
```

## Date Parameters

All KPI methods accept `start` and `end` dates as either:

- **ISO format strings**: `"2026-01-01"`
- **datetime objects**: `datetime(2026, 1, 1)`

```python
from datetime import datetime

# String dates
result = client.stats.total_car_count("2026-01-01", "2026-01-31")

# datetime objects
result = client.stats.total_car_count(
    datetime(2026, 1, 1),
    datetime(2026, 1, 31),
)
```

## Location Filtering

All KPI methods accept an optional `locations` parameter:

```python
# All locations (default)
client.stats.total_car_count("2026-01-01", "2026-01-31")

# Single location
client.stats.total_car_count("2026-01-01", "2026-01-31", locations="Burbank")

# Multiple locations
client.stats.total_car_count(
    "2026-01-01", "2026-01-31",
    locations=["Burbank", "Carol Stream", "Des Plaines"],
)
```

!!! note
    Hub Office and Query Server locations are always excluded from results.

## Result Objects

All KPI methods return typed Pydantic models. Most include a scalar `total` plus a per-location breakdown:

```python
result = client.stats.total_car_count("2026-01-01", "2026-01-31")

# Aggregate total
print(result.total)  # 288389

# Per-location breakdown
for loc in result.by_location:
    print(f"{loc.location_name}: {loc.value}")

# Period metadata
print(result.period_start)  # "2026-01-01"
print(result.period_end)    # "2026-01-31"
```
