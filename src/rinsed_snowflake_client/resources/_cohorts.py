"""Cohort resource — retention grid and plan-level cohort analysis."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from rinsed_snowflake_client._filters import DateInput, Locations
from rinsed_snowflake_client._query_builder import (
    cohort_members_sql,
    cohort_retention_by_plan_sql,
    cohort_retention_grid_sql,
)
from rinsed_snowflake_client.types._cohorts import (
    CohortMemberRow,
    CohortMembersResult,
    CohortPeriodRow,
    CohortPlanPeriodRow,
    CohortRetentionByPlanResult,
    CohortRetentionResult,
)

if TYPE_CHECKING:
    from rinsed_snowflake_client._client import RinsedClient


def _safe_int(value) -> int:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return 0
    return int(value)


def _safe_float(value) -> float:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return 0.0
    return float(value)


class CohortResource:
    """Cohort retention analysis methods.

    Access via ``client.cohorts``.
    """

    def __init__(self, client: RinsedClient) -> None:
        self._client = client

    def retention_grid(
        self,
        start: DateInput,
        end: DateInput,
        locations: Locations = None,
    ) -> CohortRetentionResult:
        """Retention grid: cohort_month x period_month.

        Args:
            start: Earliest cohort month to include.
            end: Latest cohort month to include.
            locations: Filter by location name(s).

        Returns:
            Matrix of member counts and churn counts per cohort per
            tenure period.  Period 0 = signup month (initial cohort size).
        """
        sql, params = cohort_retention_grid_sql(start, end, locations)
        df = self._client._execute(sql, params)

        rows = [
            CohortPeriodRow(
                cohort_month=str(r["cohort_month"]),
                period_month=_safe_int(r["period_month"]),
                members=_safe_int(r["members"]),
                churned=_safe_int(r["churned"]),
                voluntary_churned=_safe_int(r["voluntary_churned"]),
                involuntary_churned=_safe_int(r["involuntary_churned"]),
            )
            for _, r in df.iterrows()
        ]

        cohorts = {r.cohort_month for r in rows}
        max_period = max((r.period_month for r in rows), default=0)

        return CohortRetentionResult(
            rows=rows,
            period_start=str(start),
            period_end=str(end),
            cohort_count=len(cohorts),
            max_period=max_period,
        )

    def retention_by_plan(
        self,
        start: DateInput,
        end: DateInput,
        locations: Locations = None,
    ) -> CohortRetentionByPlanResult:
        """Retention grid sliced by membership plan at signup.

        Same shape as ``retention_grid`` but adds a ``join_plan_name``
        dimension so the frontend can filter or compare plans.
        """
        sql, params = cohort_retention_by_plan_sql(start, end, locations)
        df = self._client._execute(sql, params)

        rows = [
            CohortPlanPeriodRow(
                cohort_month=str(r["cohort_month"]),
                period_month=_safe_int(r["period_month"]),
                join_plan_name=str(r["join_plan_name"]) if r["join_plan_name"] else "Unknown",
                members=_safe_int(r["members"]),
                churned=_safe_int(r["churned"]),
                voluntary_churned=_safe_int(r["voluntary_churned"]),
                involuntary_churned=_safe_int(r["involuntary_churned"]),
            )
            for _, r in df.iterrows()
        ]

        cohorts = {r.cohort_month for r in rows}
        plans = {r.join_plan_name for r in rows}
        max_period = max((r.period_month for r in rows), default=0)

        return CohortRetentionByPlanResult(
            rows=rows,
            period_start=str(start),
            period_end=str(end),
            cohort_count=len(cohorts),
            plan_count=len(plans),
            max_period=max_period,
        )

    def members(
        self,
        start: DateInput,
        end: DateInput,
        locations: Locations = None,
    ) -> CohortMembersResult:
        """Member-level drill-down for cohorts in the date range.

        Returns one row per member showing their latest state: current
        plan, tenure, churn status, and revenue.  Use this to inspect
        individual members within a cohort or export member lists.

        Args:
            start: Earliest cohort month to include.
            end: Latest cohort month to include.
            locations: Filter by location name(s).
        """
        sql, params = cohort_members_sql(start, end, locations)
        df = self._client._execute(sql, params)

        rows = []
        active = 0
        cancelled = 0
        for _, r in df.iterrows():
            churn_date = str(r["churn_date"]) if r["churn_date"] is not None else None
            churn_type = str(r["churn_type"]) if r["churn_type"] is not None else None
            churn_period_val = r["churn_period"]
            churn_period = None if churn_period_val is None or (isinstance(churn_period_val, float) and math.isnan(churn_period_val)) else int(churn_period_val)
            status = "cancelled" if churn_date else "active"

            if status == "active":
                active += 1
            else:
                cancelled += 1

            rows.append(CohortMemberRow(
                rinsed_membership_id=str(r["rinsed_membership_id"]),
                location_name=str(r["location_name"]),
                join_date=str(r["join_date"]),
                join_plan_name=str(r["join_plan_name"]) if r["join_plan_name"] else "Unknown",
                cohort_month=str(r["cohort_month"]),
                plan_name=str(r["plan_name"]) if r["plan_name"] else "Unknown",
                revenue=_safe_float(r["revenue"]),
                tenure_months=_safe_int(r["tenure_months"]),
                churn_date=churn_date,
                churn_type=churn_type,
                churn_period=churn_period,
                status=status,
            ))

        return CohortMembersResult(
            rows=rows,
            total_members=len(rows),
            active_count=active,
            cancelled_count=cancelled,
            period_start=str(start),
            period_end=str(end),
        )
