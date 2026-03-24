"""Tests for Snowflake configuration."""

import os
from unittest.mock import patch

import pytest

from rinsed_snowflake_client._config import SnowflakeConfig
from rinsed_snowflake_client._exceptions import ConfigurationError


class TestSnowflakeConfig:
    def test_load_config_success(self):
        env = {
            "SNOWFLAKE_ACCOUNT": "acct",
            "SNOWFLAKE_USER": "user",
            "SNOWFLAKE_PASSWORD": "pass",
            "SNOWFLAKE_WAREHOUSE": "wh",
            "SNOWFLAKE_DATABASE": "db",
            "SNOWFLAKE_SCHEMA": "sc",
            "SNOWFLAKE_ROLE": "role",
        }
        with patch.dict(os.environ, env, clear=False):
            config = SnowflakeConfig.load_config()
            assert config.account == "acct"
            assert config.user == "user"
            assert config.role == "role"

    def test_load_config_missing_raises(self):
        env = {"SNOWFLAKE_ACCOUNT": "acct"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ConfigurationError, match="Missing required"):
                SnowflakeConfig.load_config()

    def test_load_config_optional_role(self):
        env = {
            "SNOWFLAKE_ACCOUNT": "acct",
            "SNOWFLAKE_USER": "user",
            "SNOWFLAKE_PASSWORD": "pass",
            "SNOWFLAKE_WAREHOUSE": "wh",
            "SNOWFLAKE_DATABASE": "db",
            "SNOWFLAKE_SCHEMA": "sc",
        }
        with patch.dict(os.environ, env, clear=True):
            config = SnowflakeConfig.load_config()
            assert config.role is None
