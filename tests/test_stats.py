"""Tests for StatsResource methods with mocked data."""

import pandas as pd
import pytest

from tests.conftest import make_df


class TestCarCounts:
    def test_total_car_count(self, mock_client):
        mock_client._conn.query.return_value = make_df({
            "location_name": ["Burbank", "Carol Stream"],
            "value": [1000, 800],
        })
        result = mock_client.stats.total_car_count("2026-01-01", "2026-01-31")
        assert result.total == 1800
        assert len(result.by_location) == 2
        assert result.by_location[0].location_name == "Burbank"
        assert result.by_location[0].value == 1000

    def test_total_car_count_empty(self, mock_client):
        mock_client._conn.query.return_value = make_df({
            "location_name": [], "value": [],
        })
        result = mock_client.stats.total_car_count("2026-01-01", "2026-01-31")
        assert result.total == 0
        assert result.by_location == []

    def test_retail_car_count(self, mock_client):
        mock_client._conn.query.return_value = make_df({
            "location_name": ["Burbank"], "value": [500],
        })
        result = mock_client.stats.retail_car_count("2026-01-01", "2026-01-31")
        assert result.total == 500

    def test_member_car_count(self, mock_client):
        mock_client._conn.query.return_value = make_df({
            "location_name": ["Burbank"], "value": [300],
        })
        result = mock_client.stats.member_car_count("2026-01-01", "2026-01-31")
        assert result.total == 300


class TestRevenue:
    def test_retail_revenue(self, mock_client):
        mock_client._conn.query.return_value = make_df({
            "location_name": ["Burbank"], "total_revenue": [5000.50], "transaction_count": [350],
        })
        result = mock_client.stats.retail_revenue("2026-01-01", "2026-01-31")
        assert result.total == 5000.50
        assert result.transaction_count == 350

    def test_membership_revenue(self, mock_client):
        mock_client._conn.query.return_value = make_df({
            "location_name": ["Burbank"],
            "new_revenue": [1000.0],
            "renewal_revenue": [4000.0],
            "total_revenue": [5000.0],
        })
        result = mock_client.stats.membership_revenue("2026-01-01", "2026-01-31")
        assert result.total == 5000.0
        assert result.new_revenue == 1000.0
        assert result.renewal_revenue == 4000.0

    def test_average_wash_price(self, mock_client):
        # First call: retail_revenue, second call: retail_car_count
        mock_client._conn.query.side_effect = [
            make_df({"location_name": ["Burbank"], "total_revenue": [1000.0], "transaction_count": [100]}),
            make_df({"location_name": ["Burbank"], "value": [100]}),
        ]
        result = mock_client.stats.average_wash_price("2026-01-01", "2026-01-31")
        assert result.awp == 10.0
        assert result.retail_revenue == 1000.0
        assert result.retail_car_count == 100


class TestMembershipSales:
    def test_new_membership_sales(self, mock_client):
        mock_client._conn.query.return_value = make_df({
            "location_name": ["Burbank"], "value": [200], "total_revenue": [5000.0],
        })
        result = mock_client.stats.new_membership_sales("2026-01-01", "2026-01-31")
        assert result.total == 200
        assert result.total_revenue == 5000.0


class TestConversion:
    def test_conversion_rate(self, mock_client):
        mock_client._conn.query.return_value = make_df({
            "location_name": ["Burbank", "Carol Stream"],
            "sales": [100, 50],
            "eligible_washes": [500, 400],
        })
        result = mock_client.stats.conversion_rate("2026-01-01", "2026-01-31")
        assert result.rate == round(150 / 900, 4)
        assert result.sales == 150
        assert result.eligible_washes == 900

    def test_conversion_rate_zero_eligible(self, mock_client):
        mock_client._conn.query.return_value = make_df({
            "location_name": [], "sales": [], "eligible_washes": [],
        })
        result = mock_client.stats.conversion_rate("2026-01-01", "2026-01-31")
        assert result.rate == 0.0


class TestChurn:
    def test_voluntary_churn(self, mock_client):
        mock_client._conn.query.side_effect = [
            make_df({"location_name": ["Burbank"], "churned": [100]}),
            make_df({"location_name": ["Burbank"], "total_members": [2000]}),
        ]
        result = mock_client.stats.voluntary_churn_rate("2026-02-01", "2026-02-28")
        assert result.rate == 0.05
        assert result.churned_count == 100
        assert result.starting_count == 2000

    def test_involuntary_churn(self, mock_client):
        mock_client._conn.query.side_effect = [
            make_df({"location_name": ["Burbank"], "churned": [50]}),
            make_df({"location_name": ["Burbank"], "total_members": [2000]}),
        ]
        result = mock_client.stats.involuntary_churn_rate("2026-02-01", "2026-02-28")
        assert result.rate == 0.025
        assert result.churned_count == 50
