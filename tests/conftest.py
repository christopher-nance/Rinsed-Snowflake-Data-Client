"""Test fixtures for rinsed-snowflake-client."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from rinsed_snowflake_client import RinsedClient


@pytest.fixture
def mock_client():
    """Create a RinsedClient with a mocked Snowflake connection."""
    with patch("rinsed_snowflake_client._config.SnowflakeConfig.load_config") as mock_config:
        mock_config.return_value = MagicMock(
            account="test", user="test", password="test",
            warehouse="test", database="test", schema="test", role=None,
        )
        client = RinsedClient()

    # Mock the connection
    client._conn = MagicMock()
    return client


def make_df(data: dict) -> pd.DataFrame:
    """Helper to create DataFrames for mock returns."""
    return pd.DataFrame(data)
