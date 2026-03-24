"""Snowflake configuration management."""

import os
from dataclasses import dataclass

from rinsed_snowflake_client._exceptions import ConfigurationError


@dataclass
class SnowflakeConfig:
    """Configuration for Snowflake connection.

    Attributes:
        account: Snowflake account identifier (e.g., xy12345.us-east-1).
        user: Snowflake username.
        password: Snowflake password.
        warehouse: Snowflake warehouse name.
        database: Snowflake database name.
        schema: Snowflake schema name.
        role: Optional Snowflake role.
    """

    account: str
    user: str
    password: str
    warehouse: str
    database: str
    schema: str
    role: str | None = None

    @classmethod
    def load_config(cls) -> "SnowflakeConfig":
        """Load configuration from environment variables.

        Required env vars: SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD,
        SNOWFLAKE_WAREHOUSE, SNOWFLAKE_DATABASE, SNOWFLAKE_SCHEMA.
        Optional: SNOWFLAKE_ROLE.

        Raises:
            ConfigurationError: If any required variable is missing.
        """
        required_vars = [
            ("SNOWFLAKE_ACCOUNT", "account"),
            ("SNOWFLAKE_USER", "user"),
            ("SNOWFLAKE_PASSWORD", "password"),
            ("SNOWFLAKE_WAREHOUSE", "warehouse"),
            ("SNOWFLAKE_DATABASE", "database"),
            ("SNOWFLAKE_SCHEMA", "schema"),
        ]

        missing = []
        values: dict[str, str] = {}

        for env_var, field_name in required_vars:
            value = os.environ.get(env_var)
            if not value:
                missing.append(env_var)
            else:
                values[field_name] = value

        if missing:
            raise ConfigurationError(
                f"Missing required environment variables: {', '.join(missing)}. "
                "Set these variables or check your .env file."
            )

        role = os.environ.get("SNOWFLAKE_ROLE")
        if role:
            values["role"] = role

        return cls(**values)
