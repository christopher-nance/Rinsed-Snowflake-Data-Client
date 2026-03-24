# Exceptions

All exceptions inherit from `RinsedError`, allowing you to catch all client errors with a single handler:

```python
from rinsed_snowflake_client import RinsedClient, RinsedError

try:
    with RinsedClient() as client:
        result = client.stats.total_car_count("2026-01-01", "2026-01-31")
except RinsedError as e:
    print(f"Client error: {e}")
```

## Exception Hierarchy

```
RinsedError
├── ConfigurationError
├── ConnectionError
├── QueryError
└── ValidationError
```

## RinsedError

::: rinsed_snowflake_client.RinsedError

## ConfigurationError

::: rinsed_snowflake_client.ConfigurationError

## ConnectionError

::: rinsed_snowflake_client.ConnectionError

## QueryError

::: rinsed_snowflake_client.QueryError

## ValidationError

::: rinsed_snowflake_client.ValidationError
