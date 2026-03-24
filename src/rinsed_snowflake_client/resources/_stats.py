"""Stats resource — all KPI methods."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from rinsed_snowflake_client._filters import DateInput, Locations
from rinsed_snowflake_client._query_builder import (
    active_members_at_start_sql,
    churn_count_sql,
    conversion_rate_sql,
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
            awp=round(awp, 2),
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
