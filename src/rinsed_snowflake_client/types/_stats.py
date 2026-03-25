"""Pydantic result models for stats KPIs."""

from rinsed_snowflake_client.types._base import RinsedModel


class LocationMetric(RinsedModel):
    """A single location's metric value."""

    location_name: str
    value: float


class CarCountResult(RinsedModel):
    """Car count totals with per-location breakdown."""

    total: int
    by_location: list[LocationMetric]
    period_start: str
    period_end: str


class RevenueResult(RinsedModel):
    """Revenue totals with per-location breakdown."""

    total: float
    transaction_count: int
    by_location: list[LocationMetric]
    period_start: str
    period_end: str


class MembershipRevenueResult(RinsedModel):
    """Membership revenue with new vs. renewal breakdown."""

    total: float
    new_revenue: float
    renewal_revenue: float
    by_location: list[LocationMetric]
    period_start: str
    period_end: str


class AWPResult(RinsedModel):
    """Average Wash Price (retail ticket average)."""

    total: float
    retail_revenue: float
    retail_car_count: int
    period_start: str
    period_end: str

    @property
    def awp(self) -> float:
        """Alias for total — the average wash price."""
        return self.total


class MembershipSalesResult(RinsedModel):
    """New membership sales totals."""

    total: int
    total_revenue: float
    by_location: list[LocationMetric]
    period_start: str
    period_end: str


class ConversionResult(RinsedModel):
    """Conversion rate with component breakdown."""

    rate: float
    sales: int
    eligible_washes: int
    by_location: list[LocationMetric]
    period_start: str
    period_end: str


class ChurnResult(RinsedModel):
    """Churn rate with component breakdown."""

    rate: float
    churned_count: int
    starting_count: int
    by_location: list[LocationMetric]
    period_start: str
    period_end: str


class DailyCancellation(RinsedModel):
    """Cancellation counts for a single day."""

    date: str
    voluntary: int
    involuntary: int
    total: int


class DailyCancellationResult(RinsedModel):
    """Daily cancellation counts over a date range."""

    total: int
    total_voluntary: int
    total_involuntary: int
    days: list[DailyCancellation]
    by_location: list[LocationMetric]
    period_start: str
    period_end: str


class DailyChurnResult(RinsedModel):
    """Daily churn counts with rate context."""

    total_churned: int
    total_voluntary: int
    total_involuntary: int
    starting_count: int
    rate: float
    days: list[DailyCancellation]
    by_location: list[LocationMetric]
    period_start: str
    period_end: str


class StatsReport(RinsedModel):
    """All KPIs bundled into a single result."""

    total_car_count: CarCountResult
    retail_car_count: CarCountResult
    member_car_count: CarCountResult
    retail_revenue: RevenueResult
    membership_revenue: MembershipRevenueResult
    average_wash_price: AWPResult
    new_membership_sales: MembershipSalesResult
    conversion: ConversionResult
    period_start: str
    period_end: str
