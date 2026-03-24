# Getting Started

## Installation

```bash
pip install git+https://github.com/christopher-nance/Rinsed-Snowflake-Data-Client.git
```

Or install from source for development:

```bash
git clone https://github.com/christopher-nance/Rinsed-Snowflake-Data-Client.git
cd Rinsed-Snowflake-Data-Client
pip install -e ".[dev]"
```

## Configuration

The client needs Snowflake credentials. You can provide them via environment variables or pass them directly.

### Environment Variables

Create a `.env` file (see `.env.example` in the repo):

```
SNOWFLAKE_ACCOUNT=your_account_identifier
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=your_warehouse
SNOWFLAKE_DATABASE=your_database
SNOWFLAKE_SCHEMA=your_schema
SNOWFLAKE_ROLE=your_role
```

Load them with `python-dotenv` before creating the client:

```python
from dotenv import load_dotenv
load_dotenv()

from rinsed_snowflake_client import RinsedClient

with RinsedClient() as client:
    result = client.stats.total_car_count("2026-01-01", "2026-01-31")
    print(result.total)
```

!!! warning
    Never commit your `.env` file to version control. The repo's `.gitignore` already excludes it.

### Explicit Credentials

Pass credentials directly when you need to connect to multiple accounts or avoid environment variables:

```python
from rinsed_snowflake_client import RinsedClient

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
result = client.stats.total_car_count("2026-01-01", "2026-01-31")
client.close()
```

!!! note
    When using explicit credentials, `account`, `user`, `password`, `warehouse`, `database`, and `schema` are all required. Passing only some of them raises `ConfigurationError`.

### Missing Configuration

If required environment variables are missing, `ConfigurationError` is raised immediately at client creation — not at query time:

```python
from rinsed_snowflake_client import RinsedClient, ConfigurationError

try:
    client = RinsedClient()  # fails if env vars are missing
except ConfigurationError as e:
    print(e)
    # "Missing required environment variables: SNOWFLAKE_ACCOUNT, SNOWFLAKE_PASSWORD. ..."
```

## Connection Management

### Context Manager (Recommended)

The context manager automatically connects on entry and closes on exit, even if an exception occurs:

```python
with RinsedClient() as client:
    cars = client.stats.total_car_count("2026-01-01", "2026-01-31")
    rev = client.stats.retail_revenue("2026-01-01", "2026-01-31")
    # connection is automatically closed when the block exits
```

This is the recommended pattern for most use cases.

### Manual Connection

For long-running processes or interactive sessions:

```python
client = RinsedClient()
client.connect()

# ... use client across multiple operations ...

client.close()  # always close when done
```

!!! warning
    If you use manual connection management, always call `client.close()` in a `finally` block to avoid leaving Snowflake connections open:

    ```python
    client = RinsedClient()
    client.connect()
    try:
        result = client.stats.report("2026-01-01", "2026-01-31")
    finally:
        client.close()
    ```

### Calling Without a Connection

If you call a method before connecting, you get a `ConnectionError`:

```python
client = RinsedClient()
# forgot to call client.connect()
client.stats.total_car_count("2026-01-01", "2026-01-31")
# raises ConnectionError: "Not connected. Use connect() or a context manager."
```

## Date Parameters

All KPI methods require `start` and `end` dates. Both accept:

- **ISO format strings**: `"2026-01-01"`, `"2026-12-31"`
- **datetime objects**: `datetime(2026, 1, 1)`
- **Mixed**: one string, one datetime

```python
from datetime import datetime

# All equivalent
client.stats.total_car_count("2026-01-01", "2026-01-31")
client.stats.total_car_count(datetime(2026, 1, 1), datetime(2026, 1, 31))
client.stats.total_car_count("2026-01-01", datetime(2026, 1, 31))
```

### Single-Day Queries

Pass the same date for both `start` and `end`:

```python
# Yesterday's total washes
result = client.stats.total_car_count("2026-03-18", "2026-03-18")
```

### Invalid Dates

Bad date strings raise `ValidationError`:

```python
client.stats.total_car_count("not-a-date", "2026-01-31")
# raises ValidationError: "Invalid date format: 'not-a-date'. ..."
```

### Date Ranges

There is no maximum date range. You can query years of data at once:

```python
# Full year
result = client.stats.total_car_count("2025-01-01", "2025-12-31")

# Multi-year
result = client.stats.total_car_count("2024-01-01", "2026-03-18")
```

!!! tip
    Unlike the Sonny's Data API Client (which has a 31-day max per request), this client has **no date range limits**. Snowflake handles large ranges efficiently.

## Location Filtering

All KPI methods accept an optional `locations` parameter:

```python
# All locations (default) — Hub Office and Query Server are always excluded
client.stats.total_car_count("2026-01-01", "2026-01-31")

# Single location
client.stats.total_car_count("2026-01-01", "2026-01-31", locations="Burbank")

# Multiple locations
client.stats.total_car_count(
    "2026-01-01", "2026-01-31",
    locations=["Burbank", "Carol Stream", "Des Plaines"],
)
```

### Location Names

Use the exact location names as they appear in Rinsed:

| Location |
|----------|
| Berwyn |
| Burbank |
| Carol Stream |
| Des Plaines |
| Dickson |
| Evergreen Park |
| Fairview |
| Jackson |
| Joliet |
| Naperville |
| Niles |
| Nolensville |
| Plainfield |
| Villa Park |
| Wheaton |

!!! note
    Location names are case-sensitive. `"burbank"` will return no results — use `"Burbank"`.

### Excluded Locations

**Hub Office** and **Query Server** are always excluded from all queries, regardless of the `locations` parameter. These are internal/test locations that don't represent real wash sites.

### Invalid Locations

```python
# Empty string raises ValidationError
client.stats.total_car_count("2026-01-01", "2026-01-31", locations="")

# Non-string in list raises ValidationError
client.stats.total_car_count("2026-01-01", "2026-01-31", locations=[123])
```

A valid location name that doesn't exist in the database will simply return zero results (no error).

## Result Objects

All KPI methods return typed Pydantic models. Most include:

- A scalar aggregate (e.g., `total`, `rate`)
- A `by_location` list with per-location breakdowns
- `period_start` and `period_end` metadata

```python
result = client.stats.total_car_count("2026-02-01", "2026-02-28")

# Aggregate
print(result.total)          # 288389
print(result.period_start)   # "2026-02-01"
print(result.period_end)     # "2026-02-28"

# Per-location breakdown
for loc in result.by_location:
    print(f"{loc.location_name}: {loc.value:,.0f}")
    # Burbank: 37,476
    # Carol Stream: 25,387
    # ...
```

### Serialization

Since all results are Pydantic models, you can easily convert them to dicts or JSON:

```python
result = client.stats.total_car_count("2026-02-01", "2026-02-28")

# To dict
data = result.model_dump()

# To JSON string
json_str = result.model_dump_json(indent=2)
```

### Empty Results

If a query returns no data (e.g., a future date or a location with no activity), results are zero/empty rather than raising an error:

```python
result = client.stats.total_car_count("2099-01-01", "2099-01-31")
print(result.total)          # 0
print(result.by_location)    # []
```
