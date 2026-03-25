"""Stats resource — all KPI methods."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from rinsed_snowflake_client._filters import DateInput, Locations
from rinsed_snowflake_client._query_builder import (
    active_members_at_start_sql,
    churn_count_sql,
    conversion_rate_sql,
    daily_cancellations_by_location_sql,
    daily_cancellations_sql,
    member_car_count_sql,
    membership_revenue_sql,
    new_membership_sales_sql,
    retail_car_count_sql,
    retail_revenue_sql,
    total_car_count_sql,
)
from rinsed_snowflake_client.types._stats import (
    AWPResult,
    CarCountResult,
    ChurnResult,
    ConversionResult,
    DailyCancellation,
    DailyCancellationResult,
    DailyChurnResult,
    LocationMetric,
    MembershipRevenueResult,
    MembershipSalesResult,
    RevenueResult,
    StatsReport,
)

if TYPE_CHECKING:
    from rinsed_snowflake_client._client import RinsedClient


class StatsResource:
    """Analytics and KPI methods.

    Access via ``client.stats``.
    """

    def __init__(self, client: RinsedClient) -> None:
        self._client = client

    # ------------------------------------------------------------------
    # Car counts
    # ------------------------------------------------------------------

    def total_car_count(
        self,
        start: DateInput,
        end: DateInput,
        locations: Locations = None,
    ) -> CarCountResult:
        """Total washes (retail + member + free) from CONVERSION_DAILY."""
        sql, params = total_car_count_sql(start, end, locations)
        df = self._client._execute(sql, params)
        by_loc = [LocationMetric(location_name=r["location_name"], value=int(r["value"])) for _, r in df.iterrows()]
        total = int(df["value"].sum()) if not df.empty else 0
        return CarCountResult(total=total, by_location=by_loc, period_start=str(start), period_end=str(end))

    def retail_car_count(
        self,
        start: DateInput,
        end: DateInput,
        locations: Locations = None,
    ) -> CarCountResult:
        """Retail (non-member) wash count."""
        sql, params = retail_car_count_sql(start, end, locations)
        df = self._client._execute(sql, params)
        by_loc = [LocationMetric(location_name=r["location_name"], value=int(r["value"])) for _, r in df.iterrows()]
        total = int(df["value"].sum()) if not df.empty else 0
        return CarCountResult(total=total, by_location=by_loc, period_start=str(start), period_end=str(end))

    def member_car_count(
        self,
        start: DateInput,
        end: DateInput,
        locations: Locations = None,
    ) -> CarCountResult:
        """Membership redemption (member wash) count."""
        sql, params = member_car_count_sql(start, end, locations)
        df = self._client._execute(sql, params)
        by_loc = [LocationMetric(location_name=r["location_name"], value=int(r["value"])) for _, r in df.iterrows()]
        total = int(df["value"].sum()) if not df.empty else 0
        return CarCountResult(total=total, by_location=by_loc, period_start=str(start), period_end=str(end))

    # ------------------------------------------------------------------
    # Revenue
    # ------------------------------------------------------------------

    def retail_revenue(
        self,
        start: DateInput,
        end: DateInput,
        locations: Locations = None,
    ) -> RevenueResult:
        """Revenue from retail (non-member) washes."""
        sql, params = retail_revenue_sql(start, end, locations)
        df = self._client._execute(sql, params)
        by_loc = [LocationMetric(location_name=r["location_name"], value=float(r["total_revenue"])) for _, r in df.iterrows()]
        total = float(df["total_revenue"].sum()) if not df.empty else 0.0
        tx_count = int(df["transaction_count"].sum()) if not df.empty else 0
        return RevenueResult(total=total, transaction_count=tx_count, by_location=by_loc, period_start=str(start), period_end=str(end))

    def membership_revenue(
        self,
        start: DateInput,
        end: DateInput,
        locations: Locations = None,
    ) -> MembershipRevenueResult:
        """Revenue from new + renewed memberships."""
        sql, params = membership_revenue_sql(start, end, locations)
        df = self._client._execute(sql, params)
        by_loc = [LocationMetric(location_name=r["location_name"], value=float(r["total_revenue"])) for _, r in df.iterrows()]
        total = float(df["total_revenue"].sum()) if not df.empty else 0.0
        new_rev = float(df["new_revenue"].sum()) if not df.empty else 0.0
        renewal_rev = float(df["renewal_revenue"].sum()) if not df.empty else 0.0
        return MembershipRevenueResult(
            total=total, new_revenue=new_rev, renewal_revenue=renewal_rev,
            by_location=by_loc, period_start=str(start), period_end=str(end),
        )

    def average_wash_price(
        self,
        start: DateInput,
        end: DateInput,
        locations: Locations = None,
    ) -> AWPResult:
        """Average Wash Price = retail revenue / retail car count."""
        rev = self.retail_revenue(start, end, locations)
        cars = self.retail_car_count(start, end, locations)
        awp = rev.total / cars.total if cars.total > 0 else 0.0
        return AWPResult(
            total=round(awp, 2),
            retail_revenue=rev.total,
            retail_car_count=cars.total,
            period_start=str(start),
            period_end=str(end),
        )

    # ------------------------------------------------------------------
    # Membership sales
    # ------------------------------------------------------------------

    def new_membership_sales(
        self,
        start: DateInput,
        end: DateInput,
        locations: Locations = None,
    ) -> MembershipSalesResult:
        """Count of new + rejoin membership sales."""
        sql, params = new_membership_sales_sql(start, end, locations)
        df = self._client._execute(sql, params)
        by_loc = [LocationMetric(location_name=r["location_name"], value=int(r["value"])) for _, r in df.iterrows()]
        total = int(df["value"].sum()) if not df.empty else 0
        total_rev = float(df["total_revenue"].sum()) if not df.empty else 0.0
        return MembershipSalesResult(
            total=total, total_revenue=total_rev, by_location=by_loc,
            period_start=str(start), period_end=str(end),
        )

    # ------------------------------------------------------------------
    # Conversion rate
    # ------------------------------------------------------------------

    def conversion_rate(
        self,
        start: DateInput,
        end: DateInput,
        locations: Locations = None,
    ) -> ConversionResult:
        """Conversion rate = sales / eligible washes (from CONVERSION_DAILY)."""
        sql, params = conversion_rate_sql(start, end, locations)
        df = self._client._execute(sql, params)

        total_sales = int(df["sales"].sum()) if not df.empty else 0
        total_eligible = int(df["eligible_washes"].sum()) if not df.empty else 0
        rate = total_sales / total_eligible if total_eligible > 0 else 0.0

        by_loc = []
        for _, r in df.iterrows():
            loc_eligible = int(r["eligible_washes"])
            loc_rate = int(r["sales"]) / loc_eligible if loc_eligible > 0 else 0.0
            by_loc.append(LocationMetric(location_name=r["location_name"], value=round(loc_rate, 4)))

        return ConversionResult(
            rate=round(rate, 4), sales=total_sales, eligible_washes=total_eligible,
            by_location=by_loc, period_start=str(start), period_end=str(end),
        )

    # ------------------------------------------------------------------
    # Churn
    # ------------------------------------------------------------------

    def _churn_rate(
        self,
        churn_type: str,
        start: DateInput,
        end: DateInput,
        locations: Locations = None,
    ) -> ChurnResult:
        """Internal: compute churn rate for a given churn type."""
        # Get churned members in the period
        sql, params = churn_count_sql(churn_type, start, end, locations)
        churn_df = self._client._execute(sql, params)

        # Get starting active member count (month of start date)
        am_sql, am_params = active_members_at_start_sql(start, locations)
        am_df = self._client._execute(am_sql, am_params)

        # Build per-location rates
        am_map = {r["location_name"]: int(r["total_members"]) for _, r in am_df.iterrows()}
        by_loc = []
        total_churned = 0
        for _, r in churn_df.iterrows():
            loc = r["location_name"]
            churned = int(r["churned"])
            total_churned += churned
            active = am_map.get(loc, 0)
            loc_rate = churned / active if active > 0 else 0.0
            by_loc.append(LocationMetric(location_name=loc, value=round(loc_rate, 4)))

        total_active = int(am_df["total_members"].sum()) if not am_df.empty else 0
        rate = total_churned / total_active if total_active > 0 else 0.0

        return ChurnResult(
            rate=round(rate, 4),
            churned_count=total_churned,
            starting_count=total_active,
            by_location=by_loc,
            period_start=str(start),
            period_end=str(end),
        )

    def involuntary_churn_rate(
        self,
        start: DateInput,
        end: DateInput,
        locations: Locations = None,
    ) -> ChurnResult:
        """Involuntary churn rate (expired memberships / failed payments)."""
        return self._churn_rate("expired", start, end, locations)

    def voluntary_churn_rate(
        self,
        start: DateInput,
        end: DateInput,
        locations: Locations = None,
    ) -> ChurnResult:
        """Voluntary churn rate (member-initiated cancellations)."""
        return self._churn_rate("terminated", start, end, locations)

    # ------------------------------------------------------------------
    # Daily cancellations & churn
    # ------------------------------------------------------------------

    def _build_daily_cancellations(
        self, start: DateInput, end: DateInput, locations: Locations
    ) -> tuple[list[DailyCancellation], list[LocationMetric], int, int, int]:
        """Internal: query and pivot daily cancellation data."""
        sql, params = daily_cancellations_sql(start, end, locations)
        df = self._client._execute(sql, params)

        loc_sql, loc_params = daily_cancellations_by_location_sql(start, end, locations)
        loc_df = self._client._execute(loc_sql, loc_params)

        # Pivot by date
        day_map: dict[str, dict[str, int]] = {}
        for _, r in df.iterrows():
            date_str = str(r["churn_date"])
            if date_str not in day_map:
                day_map[date_str] = {"voluntary": 0, "involuntary": 0}
            if r["churn_type"] == "terminated":
                day_map[date_str]["voluntary"] = int(r["cnt"])
            elif r["churn_type"] == "expired":
                day_map[date_str]["involuntary"] = int(r["cnt"])

        days = []
        total_vol = 0
        total_inv = 0
        for date_str in sorted(day_map):
            v = day_map[date_str]["voluntary"]
            i = day_map[date_str]["involuntary"]
            total_vol += v
            total_inv += i
            days.append(DailyCancellation(
                date=date_str, voluntary=v, involuntary=i, total=v + i,
            ))

        by_loc = [
            LocationMetric(location_name=r["location_name"], value=int(r["cnt"]))
            for _, r in loc_df.iterrows()
        ]

        return days, by_loc, total_vol, total_inv, total_vol + total_inv

    def cancellations(
        self,
        start: DateInput,
        end: DateInput,
        locations: Locations = None,
    ) -> DailyCancellationResult:
        """Daily cancellation counts (voluntary + involuntary).

        Uses Rinsed's real-time churn_date — the day the cancellation
        or expiry was recorded, not WashU's shifted billing-cycle definition.
        """
        days, by_loc, total_vol, total_inv, total = self._build_daily_cancellations(
            start, end, locations
        )
        return DailyCancellationResult(
            total=total,
            total_voluntary=total_vol,
            total_involuntary=total_inv,
            days=days,
            by_location=by_loc,
            period_start=str(start),
            period_end=str(end),
        )

    def daily_churn(
        self,
        start: DateInput,
        end: DateInput,
        locations: Locations = None,
    ) -> DailyChurnResult:
        """Daily churn counts with rate context.

        Same daily data as cancellations(), plus the active member
        denominator for computing an overall churn rate for the period.
        Uses Rinsed's real-time churn_date for the daily breakdown.
        """
        days, by_loc, total_vol, total_inv, total_churned = self._build_daily_cancellations(
            start, end, locations
        )

        # Get active member denominator (previous month)
        am_sql, am_params = active_members_at_start_sql(start, locations)
        am_df = self._client._execute(am_sql, am_params)
        total_active = int(am_df["total_members"].sum()) if not am_df.empty else 0
        rate = total_churned / total_active if total_active > 0 else 0.0

        # Per-location churn rates
        am_map = {r["location_name"]: int(r["total_members"]) for _, r in am_df.iterrows()}
        loc_rates = []
        for loc_metric in by_loc:
            active = am_map.get(loc_metric.location_name, 0)
            loc_rate = loc_metric.value / active if active > 0 else 0.0
            loc_rates.append(LocationMetric(
                location_name=loc_metric.location_name, value=round(loc_rate, 4),
            ))

        return DailyChurnResult(
            total_churned=total_churned,
            total_voluntary=total_vol,
            total_involuntary=total_inv,
            starting_count=total_active,
            rate=round(rate, 4),
            days=days,
            by_location=loc_rates,
            period_start=str(start),
            period_end=str(end),
        )

    # ------------------------------------------------------------------
    # Bundled report
    # ------------------------------------------------------------------

    def report(
        self,
        start: DateInput,
        end: DateInput,
        locations: Locations = None,
    ) -> StatsReport:
        """All KPIs in a single call."""
        total_cars = self.total_car_count(start, end, locations)
        retail_cars = self.retail_car_count(start, end, locations)
        member_cars = self.member_car_count(start, end, locations)
        ret_rev = self.retail_revenue(start, end, locations)
        mem_rev = self.membership_revenue(start, end, locations)
        awp = self.average_wash_price(start, end, locations)
        new_sales = self.new_membership_sales(start, end, locations)
        conv = self.conversion_rate(start, end, locations)

        return StatsReport(
            total_car_count=total_cars,
            retail_car_count=retail_cars,
            member_car_count=member_cars,
            retail_revenue=ret_rev,
            membership_revenue=mem_rev,
            average_wash_price=awp,
            new_membership_sales=new_sales,
            conversion=conv,
            period_start=str(start),
            period_end=str(end),
        )
