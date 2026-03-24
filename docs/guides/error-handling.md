# Error Handling

All exceptions inherit from `RinsedError`, so you can catch everything with a single handler or handle specific error types individually.

## Exception Hierarchy

```
RinsedError                    # Base — catch-all for any client error
├── ConfigurationError         # Missing/invalid Snowflake credentials
├── ConnectionError            # Can't connect to Snowflake
├── QueryError                 # SQL execution failed
└── ValidationError            # Bad input (dates, locations)
```

## Catching All Errors

```python
from rinsed_snowflake_client import RinsedClient, RinsedError

try:
    with RinsedClient() as client:
        result = client.stats.total_car_count("2026-01-01", "2026-01-31")
except RinsedError as e:
    print(f"Something went wrong: {e}")
```

## Specific Error Types

### ConfigurationError

Raised when Snowflake credentials are missing or incomplete. This happens at **client creation** — before any queries are made.

```python
from rinsed_snowflake_client import RinsedClient, ConfigurationError

try:
    client = RinsedClient()  # fails if env vars missing
except ConfigurationError as e:
    print(e)
    # "Missing required environment variables: SNOWFLAKE_ACCOUNT, SNOWFLAKE_PASSWORD. ..."
```

**When using explicit credentials**, all six required fields must be provided:

```python
try:
    client = RinsedClient(account="acct", user="usr")  # missing password, warehouse, etc.
except ConfigurationError as e:
    print(e)
    # "When providing explicit credentials, account, user, password, warehouse, database, and schema are all required."
```

!!! tip
    Check your `.env` file if you get this error. Common causes:

    - `.env` file exists but `load_dotenv()` wasn't called before creating the client
    - Environment variable name is misspelled (e.g., `SNOWFLAKE_ACCOUNT` vs `SNOWFLAKE_ACCT`)
    - `.env` file is in a different directory than your script

### ConnectionError

Raised when the client can't establish a Snowflake connection. Common causes: wrong credentials, network issues, account not found.

```python
from rinsed_snowflake_client import RinsedClient, ConnectionError

try:
    with RinsedClient() as client:
        result = client.stats.total_car_count("2026-01-01", "2026-01-31")
except ConnectionError as e:
    print(f"Can't connect: {e}")
```

Also raised when you try to query without connecting first:

```python
client = RinsedClient()
# forgot client.connect()

try:
    client.stats.total_car_count("2026-01-01", "2026-01-31")
except ConnectionError as e:
    print(e)  # "Not connected. Use connect() or a context manager."
```

!!! warning "Snowflake account format"
    The `SNOWFLAKE_ACCOUNT` value must include the region identifier if applicable (e.g., `xy12345.us-east-1`). An incorrect account string will result in a `ConnectionError`.

### QueryError

Raised when SQL execution fails. The error message includes the first 100 characters of the SQL for debugging.

```python
from rinsed_snowflake_client import RinsedClient, QueryError

with RinsedClient() as client:
    try:
        df = client.query("SELECT * FROM nonexistent_table")
    except QueryError as e:
        print(f"Bad query: {e}")
```

**Common causes:**

- Table or column doesn't exist
- SQL syntax error
- Permission denied on a table
- Snowflake session timeout on very long queries

### ValidationError

Raised when input parameters fail validation — before any Snowflake query is made.

**Bad date format:**

```python
from rinsed_snowflake_client import RinsedClient, ValidationError

with RinsedClient() as client:
    try:
        client.stats.total_car_count("not-a-date", "2026-01-31")
    except ValidationError as e:
        print(e)  # "Invalid date format: 'not-a-date'. Expected ISO format (YYYY-MM-DD) or datetime object."
```

**Bad location type:**

```python
    try:
        client.stats.total_car_count("2026-01-01", "2026-01-31", locations=123)
    except ValidationError as e:
        print(e)  # "Invalid date type: expected string or datetime, got int."
```

**Empty location string:**

```python
    try:
        client.stats.total_car_count("2026-01-01", "2026-01-31", locations="")
    except ValidationError as e:
        print(e)  # "Location cannot be empty string."
```

## Recommended Pattern

For production scripts, catch specific errors to provide meaningful feedback:

```python
from rinsed_snowflake_client import (
    RinsedClient,
    ConfigurationError,
    ConnectionError,
    QueryError,
    RinsedError,
)

try:
    with RinsedClient() as client:
        report = client.stats.report("2026-02-01", "2026-02-28")
        print(f"Total cars: {report.total_car_count.total:,}")

except ConfigurationError:
    print("Check your .env file — Snowflake credentials are missing.")

except ConnectionError:
    print("Can't reach Snowflake. Check network and credentials.")

except QueryError as e:
    print(f"A query failed: {e}")

except RinsedError as e:
    print(f"Unexpected client error: {e}")
```

## Logging & Debugging

For debugging Snowflake connection issues, enable the Snowflake connector's built-in logging:

```python
import logging
logging.basicConfig()
logging.getLogger("snowflake.connector").setLevel(logging.DEBUG)

with RinsedClient() as client:
    result = client.stats.total_car_count("2026-01-01", "2026-01-31")
```

This will show detailed connection handshake, query execution, and network timing information.
