"""Tests for RinsedClient."""

from unittest.mock import MagicMock, patch

import pytest

from rinsed_snowflake_client import RinsedClient
from rinsed_snowflake_client._exceptions import ConfigurationError, ConnectionError


class TestRinsedClient:
    def test_explicit_credentials(self):
        with patch("rinsed_snowflake_client._client.SnowflakeConfig") as mock:
            client = RinsedClient(
                account="a", user="u", password="p",
                warehouse="w", database="d", schema="s",
            )
            mock.assert_called_once()

    def test_partial_credentials_raises(self):
        with pytest.raises(ConfigurationError):
            RinsedClient(account="a", user="u")

    def test_env_credentials(self):
        with patch("rinsed_snowflake_client._config.SnowflakeConfig.load_config") as mock:
            mock.return_value = MagicMock()
            client = RinsedClient()
            mock.assert_called_once()

    def test_execute_without_connect_raises(self):
        with patch("rinsed_snowflake_client._config.SnowflakeConfig.load_config") as mock:
            mock.return_value = MagicMock()
            client = RinsedClient()
            with pytest.raises(ConnectionError):
                client._execute("SELECT 1")

    def test_stats_property(self):
        with patch("rinsed_snowflake_client._config.SnowflakeConfig.load_config") as mock:
            mock.return_value = MagicMock()
            client = RinsedClient()
            stats = client.stats
            assert stats is client.stats  # cached_property
