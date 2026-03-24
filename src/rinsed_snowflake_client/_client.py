"""RinsedClient — main entry point for the package."""

from __future__ import annotations

import functools
from typing import Sequence

import pandas as pd

from rinsed_snowflake_client._config import SnowflakeConfig
from rinsed_snowflake_client._connection import RinsedConnection
from rinsed_snowflake_client.resources._stats import StatsResource


class RinsedClient:
    """Client for WashU Rinsed Snowflake data.

    Args:
        account: Snowflake account identifier. If None, loads from env.
        user: Snowflake username.
        password: Snowflake password.
        warehouse: Snowflake warehouse name.
        database: Snowflake database name.
        schema: Snowflake schema name.
        role: Optional Snowflake role.

    Examples:
        # From environment variables
        with RinsedClient() as client:
            result = client.stats.total_car_count("2026-01-01", "2026-01-31")
            print(result.total)

        # Explicit credentials
        client = RinsedClient(account="...", user="...", password="...",
                              warehouse="...", database="...", schema="...")
        client.connect()
        df = client.query("SELECT * FROM conversion_daily LIMIT 10")
        client.close()
    """

    def __init__(
        self,
        account: str | None = None,
        user: str | None = None,
        password: str | None = None,
        warehouse: str | None = None,
        database: str | None = None,
        schema: str | None = None,
        role: str | None = None,
    ) -> None:
        if all(v is None for v in (account, user, password, warehouse, database, schema)):
            self._config = SnowflakeConfig.load_config()
        else:
            if not all((account, user, password, warehouse, database, schema)):
                from rinsed_snowflake_client._exceptions import ConfigurationError
                raise ConfigurationError(
                    "When providing explicit credentials, account, user, password, "
                    "warehouse, database, and schema are all required."
                )
            self._config = SnowflakeConfig(
                account=account,  # type: ignore[arg-type]
                user=user,  # type: ignore[arg-type]
                password=password,  # type: ignore[arg-type]
                warehouse=warehouse,  # type: ignore[arg-type]
                database=database,  # type: ignore[arg-type]
                schema=schema,  # type: ignore[arg-type]
                role=role,
            )

        self._conn: RinsedConnection | None = None

    @functools.cached_property
    def stats(self) -> StatsResource:
        """Analytics and KPI methods."""
        return StatsResource(self)

    def connect(self) -> RinsedClient:
        """Establish Snowflake connection."""
        self._conn = RinsedConnection(self._config)
        self._conn.connect()
        return self

    def close(self) -> None:
        """Close the Snowflake connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> RinsedClient:
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def _execute(self, sql: str, params: Sequence | None = None) -> pd.DataFrame:
        """Internal: execute SQL via the active connection."""
        if self._conn is None:
            from rinsed_snowflake_client._exceptions import ConnectionError
            raise ConnectionError("Not connected. Use connect() or a context manager.")
        return self._conn.query(sql, params)

    def query(self, sql: str, params: Sequence | None = None) -> pd.DataFrame:
        """Execute raw SQL and return a pandas DataFrame.

        Power-user escape hatch for ad-hoc queries.

        Args:
            sql: SQL query string.
            params: Optional parameters for parameterized queries.

        Returns:
            Query results as a pandas DataFrame.
        """
        return self._execute(sql, params)
