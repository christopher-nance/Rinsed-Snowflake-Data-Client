"""Cohort resource — retention grid and plan-level cohort analysis."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from rinsed_snowflake_client._filters import DateInput, Locations
from rinsed_snowflake_client._query_builder import (
    cohort_retention_by_plan_sql,
    cohort_retention_grid_sql,
)
from rinsed_snowflake_client.types._cohorts import (
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
