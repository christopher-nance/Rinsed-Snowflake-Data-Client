"""Tests for date and location filtering utilities."""

from datetime import datetime

import pytest

from rinsed_snowflake_client._filters import (
    build_date_clause,
    build_location_clause,
    normalize_date,
    normalize_locations,
)
from rinsed_snowflake_client._exceptions import ValidationError


class TestNormalizeLocations:
    def test_none_returns_none(self):
        assert normalize_locations(None) is None

    def test_string_returns_list(self):
        assert normalize_locations("Burbank") == ["Burbank"]

    def test_list_passes_through(self):
        assert normalize_locations(["A", "B"]) == ["A", "B"]

    def test_empty_string_raises(self):
        with pytest.raises(ValidationError):
            normalize_locations("")

    def test_empty_string_in_list_raises(self):
        with pytest.raises(ValidationError):
            normalize_locations(["A", ""])

    def test_non_string_in_list_raises(self):
        with pytest.raises(ValidationError):
            normalize_locations(["A", 123])  # type: ignore


class TestNormalizeDate:
    def test_none_returns_none(self):
        assert normalize_date(None) is None

    def test_datetime_passes_through(self):
        dt = datetime(2026, 1, 1)
        assert normalize_date(dt) == dt

    def test_iso_string_parsed(self):
        result = normalize_date("2026-01-15")
        assert result == datetime(2026, 1, 15)

    def test_invalid_string_raises(self):
        with pytest.raises(ValidationError):
            normalize_date("not-a-date")

    def test_invalid_type_raises(self):
        with pytest.raises(ValidationError):
            normalize_date(12345)  # type: ignore


class TestBuildLocationClause:
    def test_single_location(self):
        sql, params = build_location_clause("loc", ["A"])
        assert sql == "loc IN (%s)"
        assert params == ["A"]

    def test_multiple_locations(self):
        sql, params = build_location_clause("loc", ["A", "B", "C"])
        assert sql == "loc IN (%s, %s, %s)"
        assert params == ["A", "B", "C"]


class TestBuildDateClause:
    def test_both_none(self):
        sql, params = build_date_clause("dt", None, None)
        assert sql == ""
        assert params == []

    def test_start_only(self):
        dt = datetime(2026, 1, 1)
        sql, params = build_date_clause("dt", dt, None)
        assert sql == "dt >= %s"
        assert params == [dt]

    def test_end_only(self):
        dt = datetime(2026, 12, 31)
        sql, params = build_date_clause("dt", None, dt)
        assert sql == "dt <= %s"
        assert params == [dt]

    def test_both_dates(self):
        s, e = datetime(2026, 1, 1), datetime(2026, 12, 31)
        sql, params = build_date_clause("dt", s, e)
        assert sql == "dt >= %s AND dt <= %s"
        assert params == [s, e]
