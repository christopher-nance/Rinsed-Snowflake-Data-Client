"""Date and location filtering utilities for SQL query construction."""

from datetime import datetime

from rinsed_snowflake_client._exceptions import ValidationError

Locations = str | list[str] | None
DateInput = datetime | str


def normalize_locations(locations: Locations) -> list[str] | None:
    """Normalize location parameter to a list or None.

    Args:
        locations: Single location string, list of locations, or None for all.

    Raises:
        ValidationError: If list contains non-strings or empty strings.
    """
    if locations is None:
        return None
    if isinstance(locations, str):
        if not locations:
            raise ValidationError("Location cannot be empty string.")
        return [locations]
    for item in locations:
        if not isinstance(item, str):
            raise ValidationError(
                f"Invalid location: expected string, got {type(item).__name__}."
            )
        if not item:
            raise ValidationError("Location cannot be empty string.")
    return locations


def normalize_date(date: DateInput | None) -> datetime | None:
    """Normalize date parameter to datetime or None.

    Args:
        date: Datetime object, ISO format string, or None.

    Raises:
        ValidationError: If date string is not valid ISO format.
    """
    if date is None:
        return None
    if isinstance(date, datetime):
        return date
    if isinstance(date, str):
        try:
            return datetime.fromisoformat(date)
        except ValueError:
            raise ValidationError(
                f"Invalid date format: '{date}'. "
                "Expected ISO format (YYYY-MM-DD) or datetime object."
            )
    raise ValidationError(
        f"Invalid date type: expected string or datetime, got {type(date).__name__}."
    )


def build_location_clause(column: str, locations: list[str]) -> tuple[str, list[str]]:
    """Build parameterized SQL IN clause for locations."""
    placeholders = ", ".join(["%s"] * len(locations))
    return (f"{column} IN ({placeholders})", locations)


def build_date_clause(
    column: str, start_date: datetime | None, end_date: datetime | None
) -> tuple[str, list[datetime]]:
    """Build parameterized SQL date range clause."""
    if start_date is None and end_date is None:
        return ("", [])
    if start_date is not None and end_date is None:
        return (f"{column} >= %s", [start_date])
    if start_date is None and end_date is not None:
        return (f"{column} <= %s", [end_date])
    return (f"{column} >= %s AND {column} <= %s", [start_date, end_date])
