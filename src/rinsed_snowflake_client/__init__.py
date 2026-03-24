"""Rinsed Snowflake Data Client — Python client for WashU Carwash Rinsed CRM data."""

from rinsed_snowflake_client._client import RinsedClient
from rinsed_snowflake_client._exceptions import (
    ConfigurationError,
    ConnectionError,
    QueryError,
    RinsedError,
    ValidationError,
)
from rinsed_snowflake_client._version import __version__
from rinsed_snowflake_client.types import (
    AWPResult,
    CarCountResult,
    ChurnResult,
    ConversionResult,
    LocationMetric,
    MembershipRevenueResult,
    MembershipSalesResult,
    RevenueResult,
    StatsReport,
)

__all__ = [
    # Client
    "RinsedClient",
    # Exceptions
    "ConfigurationError",
    "ConnectionError",
    "QueryError",
    "RinsedError",
    "ValidationError",
    # Types
    "AWPResult",
    "CarCountResult",
    "ChurnResult",
    "ConversionResult",
    "LocationMetric",
    "MembershipRevenueResult",
    "MembershipSalesResult",
    "RevenueResult",
    "StatsReport",
    # Version
    "__version__",
]
