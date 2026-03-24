"""Snowflake connection management."""

from typing import Sequence

import pandas as pd
import snowflake.connector
from snowflake.connector import SnowflakeConnection

from rinsed_snowflake_client._config import SnowflakeConfig
from rinsed_snowflake_client._exceptions import ConnectionError, QueryError


class RinsedConnection:
    """Context manager for Snowflake connections."""

    def __init__(self, config: SnowflakeConfig) -> None:
        self._config = config
        self._connection: SnowflakeConnection | None = None

    @property
    def connection(self) -> SnowflakeConnection:
        if self._connection is None:
            raise ConnectionError(
                "Not connected. Use connect() or enter the context manager first."
            )
        return self._connection

    def connect(self) -> "RinsedConnection":
        try:
            params = {
                "account": self._config.account,
                "user": self._config.user,
                "password": self._config.password,
                "warehouse": self._config.warehouse,
                "database": self._config.database,
                "schema": self._config.schema,
            }
            if self._config.role:
                params["role"] = self._config.role

            self._connection = snowflake.connector.connect(**params)
            return self
        except Exception as e:
            raise ConnectionError(
                f"Failed to connect to Snowflake: {e}. "
                "Check your credentials and network connection."
            ) from e

    def close(self) -> None:
        if self._connection is not None:
            try:
                self._connection.close()
            finally:
                self._connection = None

    def __enter__(self) -> "RinsedConnection":
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def query(self, sql: str, params: Sequence | None = None) -> pd.DataFrame:
        cursor = self.connection.cursor()
        try:
            cursor.execute(sql, params)
            data = cursor.fetchall()
            column_names = [desc[0].lower() for desc in cursor.description]
            return pd.DataFrame(data, columns=column_names)
        except Exception as e:
            sql_preview = sql[:100] + "..." if len(sql) > 100 else sql
            raise QueryError(
                f"Query execution failed: {e}. SQL: {sql_preview}"
            ) from e
        finally:
            cursor.close()
