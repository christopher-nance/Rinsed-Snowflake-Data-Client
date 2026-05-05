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
    unclassified_churned: int


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
    unclassified_churned: int


class CohortRetentionByPlanResult(RinsedModel):
    """Retention grid sliced by membership plan at signup."""

    rows: list[CohortPlanPeriodRow]
    period_start: str
    period_end: str
    cohort_count: int
    plan_count: int
    max_period: int


class CohortMemberRow(RinsedModel):
    """Individual member record within a cohort."""

    rinsed_membership_id: str
    location_name: str
    join_date: str
    join_plan_name: str
    cohort_month: str
    plan_name: str
    revenue: float
    tenure_months: int
    churn_date: str | None
    churn_type: str | None
    churn_period: int | None
    status: str
    wash_count: int
    last_wash_date: str | None
    first_wash_date: str | None
    avg_washes_per_month: float


class CohortMembersResult(RinsedModel):
    """Member-level drill-down for a cohort range."""

    rows: list[CohortMemberRow]
    total_members: int
    active_count: int
    cancelled_count: int
    period_start: str
    period_end: str
