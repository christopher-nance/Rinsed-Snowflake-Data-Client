"""Pydantic result models for cohort analysis."""

from rinsed_snowflake_client.types._base import RinsedModel


class CohortPeriodRow(RinsedModel):
    """One cell of the retention grid: a cohort at a specific tenure period."""

    cohort_month: str
    period_month: int
    members: int
    churned: int
    voluntary_churned: int
    involuntary_churned: int


class CohortRetentionResult(RinsedModel):
    """Retention grid: cohort_month x period_month matrix with counts."""

    rows: list[CohortPeriodRow]
    period_start: str
    period_end: str
    cohort_count: int
    max_period: int


class CohortPlanPeriodRow(RinsedModel):
    """One cell of the plan-level retention grid."""

    cohort_month: str
    period_month: int
    join_plan_name: str
    members: int
    churned: int
    voluntary_churned: int
    involuntary_churned: int


class CohortRetentionByPlanResult(RinsedModel):
    """Retention grid sliced by membership plan at signup."""

    rows: list[CohortPlanPeriodRow]
    period_start: str
    period_end: str
    cohort_count: int
    plan_count: int
    max_period: int
