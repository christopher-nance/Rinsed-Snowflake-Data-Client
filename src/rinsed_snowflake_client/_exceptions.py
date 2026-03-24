"""Exception hierarchy for rinsed-snowflake-client."""


class RinsedError(Exception):
    """Base exception for all rinsed-snowflake-client errors."""


class ConfigurationError(RinsedError):
    """Missing or invalid Snowflake configuration."""


class ConnectionError(RinsedError):
    """Snowflake connection failure."""


class QueryError(RinsedError):
    """SQL query execution failure."""


class ValidationError(RinsedError):
    """Invalid user input (dates, locations, etc.)."""
