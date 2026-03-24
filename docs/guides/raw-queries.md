# Raw Queries

For ad-hoc analysis beyond the built-in KPI methods, use `client.query()` to execute raw SQL against Snowflake. This returns a pandas DataFrame.

## Basic Usage

```python
with RinsedClient() as client:
    df = client.query("SELECT * FROM conversion_daily LIMIT 10")
    print(df)
```

## Parameterized Queries

Use `%s` placeholders for safe parameterized queries:

```python
df = client.query(
    "SELECT * FROM fct_revenue WHERE location_name = %s AND DATE(created_at) = %s",
    ["Burbank", "2026-03-01"],
)
```

## Available Tables

Key tables in the `WASHU_RINSED_SHARE.MB` schema:

| Table | Description |
|-------|-------------|
| `FCT_REVENUE` | All revenue transactions (retail washes, memberships, combos) |
| `FCT_WASHES` | Wash records with categories: `base wash`, `redemption`, `free wash` |
| `FCT_MEMBERSHIPS` | Membership billing (new, renewed, rejoin) |
| `FCT_REDEMPTIONS` | Membership wash redemptions |
| `CONVERSION_DAILY` | Pre-aggregated daily conversion metrics |
| `CONVERSION_HOURLY` | Pre-aggregated hourly conversion metrics |
| `CONVERSION_SHIFT` | Pre-aggregated shift-level (AM/PM) metrics |
| `MEMBER_HISTORY` | Member lifecycle with churn type and dates |
| `ACTIVE_MEMBERS_MONTHLY` | Monthly active member counts by location |

## Schema Discovery

```python
# List all tables
df = client.query("SHOW TABLES")

# Inspect a table's columns
df = client.query("SHOW COLUMNS IN TABLE fct_revenue")

# Sample data
df = client.query("SELECT * FROM fct_revenue LIMIT 5")
```

!!! warning
    The `query()` method executes arbitrary SQL. Only use `SELECT` statements — never write to the database.
