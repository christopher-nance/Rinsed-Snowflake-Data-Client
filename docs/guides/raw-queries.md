# Raw Queries

For ad-hoc analysis beyond the built-in KPI methods, use `client.query()` to execute SQL against Snowflake. This returns a pandas DataFrame — useful for data exploration, custom aggregations, and one-off analyses.

## Basic Usage

```python
from rinsed_snowflake_client import RinsedClient

with RinsedClient() as client:
    df = client.query("SELECT * FROM conversion_daily LIMIT 10")
    print(df)
```

## Parameterized Queries

Use `%s` placeholders for safe parameterized queries. This prevents SQL injection and handles type conversion automatically:

```python
df = client.query(
    "SELECT * FROM fct_revenue WHERE location_name = %s AND DATE(created_at) = %s",
    ["Burbank", "2026-03-01"],
)
```

Multiple parameters:

```python
df = client.query(
    """
    SELECT location_name, COUNT(*) as cnt
    FROM fct_revenue
    WHERE transaction_category = %s
    AND DATE(created_at) >= %s AND DATE(created_at) <= %s
    GROUP BY location_name
    ORDER BY cnt DESC
    """,
    ["Retail Wash", "2026-02-01", "2026-02-28"],
)
```

!!! warning
    Always use parameterized queries (`%s` placeholders) for user-supplied values. Never use f-strings or string concatenation to build SQL — this exposes you to SQL injection.

## Available Tables

Key tables in the `WASHU_RINSED_SHARE.MB` schema:

### Fact Tables

| Table | Description | Key Columns |
|-------|-------------|-------------|
| `FCT_REVENUE` | All revenue transactions | `created_at` (timestamp), `location_name`, `transaction_category`, `amount`, `item_name` |
| `FCT_WASHES` | Wash records | `created_at` (timestamp), `location_name`, `transaction_category` (`base wash`, `redemption`, `free wash`) |
| `FCT_MEMBERSHIPS` | Membership billing | `created_at` (timestamp), `location_name`, `transaction_category`, `revenue`, `plan_name`, `rinsed_membership_id` |
| `FCT_REDEMPTIONS` | Member wash redemptions | `created_at` (timestamp), `location_name`, `item_name` |
| `MEMBER_HISTORY` | Member lifecycle & churn | `rinsed_membership_id`, `created_date`, `churn_type`, `churn_date`, `location_name`, `plan_name` |

### Aggregated Tables

| Table | Description | Key Columns |
|-------|-------------|-------------|
| `CONVERSION_DAILY` | Daily conversion metrics | `created_date` (date), `location_name`, `total_washes`, `eligible_washes`, `sales`, `conversion_rate` |
| `CONVERSION_HOURLY` | Hourly conversion metrics | Same as daily + `created_hour` (0-23) |
| `CONVERSION_SHIFT` | Shift-level (AM/PM) metrics | Same as daily + `shift` ('AM' or 'PM') |
| `ACTIVE_MEMBERS_MONTHLY` | Monthly active member counts | `month`, `location_id`, `active_event_type`, `members`, `definition` |

!!! info "Timestamp vs. date columns"
    `FCT_REVENUE`, `FCT_WASHES`, `FCT_MEMBERSHIPS`, and `FCT_REDEMPTIONS` use `created_at` as a **timestamp** (e.g., `2026-03-18 15:49:03`). Use `DATE(created_at)` when filtering by day:

    ```python
    # CORRECT: cast to date for day-level filtering
    df = client.query("SELECT * FROM fct_revenue WHERE DATE(created_at) = '2026-03-18'")

    # WRONG: this only matches records at exactly midnight
    df = client.query("SELECT * FROM fct_revenue WHERE created_at = '2026-03-18'")
    ```

    `CONVERSION_DAILY` uses `created_date` as a **date** — no casting needed.

## Schema Discovery

### List All Tables

```python
df = client.query("SHOW TABLES")
for _, row in df.iterrows():
    print(row["name"])
```

### Inspect Table Columns

```python
df = client.query("SHOW COLUMNS IN TABLE fct_revenue")
for _, row in df.iterrows():
    print(f"{row['column_name']}: {row['data_type']}")
```

### Explore Distinct Values

```python
# What transaction categories exist in FCT_REVENUE?
df = client.query("""
    SELECT DISTINCT transaction_category, COUNT(*) as cnt
    FROM fct_revenue
    GROUP BY transaction_category
    ORDER BY cnt DESC
""")
print(df.to_string())
# Retail Wash                 97865
# Renewed Membership          41598
# Free Wash                    7927
# New Membership & Redemption  7538
# ...
```

### Sample Data

```python
df = client.query("SELECT * FROM fct_revenue LIMIT 5")
print(df.columns.tolist())
print(df.to_string())
```

## Use Cases

### Custom Date Aggregation

The built-in KPI methods aggregate to totals. For daily or weekly granularity, use raw queries:

```python
# Daily wash counts for a month
df = client.query("""
    SELECT created_date, location_name, total_washes, sales, conversion_rate
    FROM conversion_daily
    WHERE created_date >= '2026-02-01' AND created_date <= '2026-02-28'
    AND location_name = 'Burbank'
    ORDER BY created_date
""")
print(df.to_string())
```

### Hourly Patterns

```python
# Hourly conversion rates for a specific day
df = client.query("""
    SELECT created_hour, SUM(total_washes) as washes, SUM(sales) as sales
    FROM conversion_hourly
    WHERE created_date = '2026-03-18'
    AND location_name = 'Burbank'
    GROUP BY created_hour
    ORDER BY created_hour
""")
```

### Shift-Level Analysis

```python
# AM vs PM conversion rates
df = client.query("""
    SELECT shift,
           SUM(sales) as total_sales,
           SUM(eligible_washes) as total_eligible,
           SUM(sales)::float / NULLIF(SUM(eligible_washes), 0) as rate
    FROM conversion_shift
    WHERE created_date >= '2026-02-01' AND created_date <= '2026-02-28'
    GROUP BY shift
""")
```

### Membership Plan Breakdown

```python
# Revenue by membership plan
df = client.query("""
    SELECT plan_name,
           transaction_category,
           COUNT(*) as transactions,
           SUM(revenue) as total_revenue
    FROM fct_memberships
    WHERE DATE(created_at) >= '2026-02-01' AND DATE(created_at) <= '2026-02-28'
    AND location_name = 'Burbank'
    GROUP BY plan_name, transaction_category
    ORDER BY total_revenue DESC
""")
```

### Item-Level Wash Analysis

```python
# Which wash packages sell the most?
df = client.query("""
    SELECT item_name, COUNT(*) as cnt, SUM(amount) as revenue
    FROM fct_revenue
    WHERE transaction_category = 'Retail Wash'
    AND DATE(created_at) >= '2026-02-01' AND DATE(created_at) <= '2026-02-28'
    GROUP BY item_name
    ORDER BY cnt DESC
""")
```

### Export to CSV

```python
with RinsedClient() as client:
    df = client.query("""
        SELECT created_date, location_name, total_washes, sales, eligible_washes
        FROM conversion_daily
        WHERE created_date >= '2026-01-01' AND created_date <= '2026-02-28'
        ORDER BY created_date, location_name
    """)
    df.to_csv("conversion_data.csv", index=False)
    print(f"Exported {len(df)} rows")
```

## Error Handling

Bad SQL raises `QueryError` with the first 100 characters of the query for debugging:

```python
from rinsed_snowflake_client import RinsedClient, QueryError

with RinsedClient() as client:
    try:
        df = client.query("SELECT * FROM nonexistent_table")
    except QueryError as e:
        print(f"Query failed: {e}")
```

!!! warning "Read-only access"
    The Snowflake role used by this client should only have `SELECT` permissions. Never execute `INSERT`, `UPDATE`, `DELETE`, or DDL statements through this client.
