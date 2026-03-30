"""SQL query construction for all KPI methods.

All queries exclude Hub Office and Query Server locations.
"""

from datetime import datetime

from rinsed_snowflake_client._filters import (
    build_date_clause,
    build_location_clause,
    normalize_date,
    normalize_locations,
    DateInput,
    Locations,
)

EXCLUDED_LOCATIONS = ["Hub Office", "Query Server"]


def _add_exclusions(sql: str, params: list, column: str = "location_name") -> None:
    """Append Hub Office / Query Server exclusion to query."""
    placeholders = ", ".join(["%s"] * len(EXCLUDED_LOCATIONS))
    sql_frag = f" AND {column} NOT IN ({placeholders})"
    # We mutate in place; caller appends sql_frag to their sql string
    params.extend(EXCLUDED_LOCATIONS)
    return sql_frag


def _apply_filters(
    sql: str,
    params: list,
    date_column: str,
    start: DateInput | None,
    end: DateInput | None,
    locations: Locations,
    location_column: str = "location_name",
    cast_date: bool = False,
) -> str:
    """Apply date, location, and exclusion filters to a base query.

    Args:
        cast_date: If True, wraps the date_column in DATE() for timestamp columns.
    """
    # Exclude Hub Office / Query Server
    sql += _add_exclusions(sql, params, location_column)

    # Location filter
    normalized_locations = normalize_locations(locations)
    if normalized_locations is not None:
        loc_clause, loc_params = build_location_clause(location_column, normalized_locations)
        sql += f" AND {loc_clause}"
        params.extend(loc_params)

    # Date filter — cast timestamp columns to DATE for correct day-level comparison
    effective_column = f"DATE({date_column})" if cast_date else date_column
    normalized_start = normalize_date(start)
    normalized_end = normalize_date(end)
    date_clause, date_params = build_date_clause(effective_column, normalized_start, normalized_end)
    if date_clause:
        sql += f" AND {date_clause}"
        params.extend(date_params)

    return sql


# ---------------------------------------------------------------------------
# Car count queries
# ---------------------------------------------------------------------------


def total_car_count_sql(
    start: DateInput | None, end: DateInput | None, locations: Locations
) -> tuple[str, list]:
    """Total washes from CONVERSION_DAILY (retail + member + free)."""
    sql = """
        SELECT location_name, SUM(total_washes) as value
        FROM conversion_daily
        WHERE 1=1
    """.strip()
    params: list = []
    sql = _apply_filters(sql, params, "created_date", start, end, locations)
    sql += " GROUP BY location_name ORDER BY location_name"
    return (sql, params)


def retail_car_count_sql(
    start: DateInput | None, end: DateInput | None, locations: Locations
) -> tuple[str, list]:
    """Pure retail (non-member) wash count from FCT_REVENUE.

    Counts only 'Retail Wash' transactions. NM&R and RM&R combo washes
    are membership washes, not retail.
    """
    sql = """
        SELECT location_name, COUNT(*) as value
        FROM fct_revenue
        WHERE transaction_category = 'Retail Wash'
    """.strip()
    params: list = []
    sql = _apply_filters(sql, params, "created_at", start, end, locations, cast_date=True)
    sql += " GROUP BY location_name ORDER BY location_name"
    return (sql, params)


def member_car_count_sql(
    start: DateInput | None, end: DateInput | None, locations: Locations
) -> tuple[str, list]:
    """Membership redemption count from FCT_WASHES."""
    sql = """
        SELECT location_name, COUNT(*) as value
        FROM fct_washes
        WHERE transaction_category = 'redemption'
    """.strip()
    params: list = []
    sql = _apply_filters(sql, params, "created_at", start, end, locations, cast_date=True)
    sql += " GROUP BY location_name ORDER BY location_name"
    return (sql, params)


# ---------------------------------------------------------------------------
# Revenue queries
# ---------------------------------------------------------------------------


def retail_revenue_sql(
    start: DateInput | None, end: DateInput | None, locations: Locations
) -> tuple[str, list]:
    """Retail wash revenue from FCT_REVENUE."""
    sql = """
        SELECT location_name, SUM(amount) as total_revenue, COUNT(*) as transaction_count
        FROM fct_revenue
        WHERE transaction_category = 'Retail Wash'
    """.strip()
    params: list = []
    sql = _apply_filters(sql, params, "created_at", start, end, locations, cast_date=True)
    sql += " GROUP BY location_name ORDER BY location_name"
    return (sql, params)


def membership_revenue_sql(
    start: DateInput | None, end: DateInput | None, locations: Locations
) -> tuple[str, list]:
    """Membership revenue from FCT_MEMBERSHIPS, split by new vs. renewed."""
    sql = """
        SELECT
            location_name,
            SUM(CASE WHEN transaction_category IN ('new membership', 'rejoin membership')
                THEN revenue ELSE 0 END) as new_revenue,
            SUM(CASE WHEN transaction_category = 'renewed membership'
                THEN revenue ELSE 0 END) as renewal_revenue,
            SUM(revenue) as total_revenue
        FROM fct_memberships
        WHERE transaction_category IN ('new membership', 'rejoin membership', 'renewed membership')
    """.strip()
    params: list = []
    sql = _apply_filters(sql, params, "created_at", start, end, locations, cast_date=True)
    sql += " GROUP BY location_name ORDER BY location_name"
    return (sql, params)


# ---------------------------------------------------------------------------
# Membership sales query
# ---------------------------------------------------------------------------


def new_membership_sales_sql(
    start: DateInput | None, end: DateInput | None, locations: Locations
) -> tuple[str, list]:
    """New + rejoin membership counts from FCT_MEMBERSHIPS."""
    sql = """
        SELECT location_name, COUNT(*) as value, SUM(revenue) as total_revenue
        FROM fct_memberships
        WHERE transaction_category IN ('new membership', 'rejoin membership')
    """.strip()
    params: list = []
    sql = _apply_filters(sql, params, "created_at", start, end, locations, cast_date=True)
    sql += " GROUP BY location_name ORDER BY location_name"
    return (sql, params)


# ---------------------------------------------------------------------------
# Conversion rate query
# ---------------------------------------------------------------------------


def conversion_rate_sql(
    start: DateInput | None, end: DateInput | None, locations: Locations
) -> tuple[str, list]:
    """Aggregated conversion metrics from CONVERSION_DAILY."""
    sql = """
        SELECT
            location_name,
            SUM(sales) as sales,
            SUM(eligible_washes) as eligible_washes
        FROM conversion_daily
        WHERE 1=1
    """.strip()
    params: list = []
    sql = _apply_filters(sql, params, "created_date", start, end, locations)
    sql += " GROUP BY location_name ORDER BY location_name"
    return (sql, params)


# ---------------------------------------------------------------------------
# Churn queries
# ---------------------------------------------------------------------------


def churn_count_sql(
    churn_type: str,
    start: DateInput | None,
    end: DateInput | None,
    locations: Locations,
) -> tuple[str, list]:
    """Count churned members from MEMBER_HISTORY by churn_type.

    WashU definition: churn is recognized when the would-be recharge doesn't
    process, not when the cancellation happens. A member billed in month N
    who cancels during month N is still a member for month N — their churn
    is reported in month N+1. So churn for month M = members whose last
    billing (created_month) was in month M-1 and who have a churn record.

    Args:
        churn_type: 'terminated' for voluntary, 'expired' for involuntary.
    """
    normalized_start = normalize_date(start)

    # Compute previous month (the last billing month for these churned members)
    if normalized_start is not None:
        first_of_month = normalized_start.replace(day=1)
        if first_of_month.month == 1:
            prev_month = first_of_month.replace(year=first_of_month.year - 1, month=12)
        else:
            prev_month = first_of_month.replace(month=first_of_month.month - 1)
    else:
        prev_month = None

    sql = """
        SELECT location_name, COUNT(DISTINCT rinsed_membership_id) as churned
        FROM member_history
        WHERE churn_type = %s
    """.strip()
    params: list = [churn_type]

    # Filter to members whose last billing was in the previous month
    if prev_month is not None:
        sql += " AND created_month = %s"
        params.append(prev_month)

    # Exclude Hub Office / Query Server
    sql += _add_exclusions(sql, params)

    # Location filter
    normalized_locations = normalize_locations(locations)
    if normalized_locations is not None:
        loc_clause, loc_params = build_location_clause("location_name", normalized_locations)
        sql += f" AND {loc_clause}"
        params.extend(loc_params)

    sql += " GROUP BY location_name ORDER BY location_name"
    return (sql, params)


def active_members_at_start_sql(
    start: DateInput | None,
    locations: Locations,
) -> tuple[str, list]:
    """Get active member count per location_name for the churn base period.

    Rinsed defines churn rate as: churned in month N / active at end of month N-1.
    So we use the PREVIOUS month's active members from ACTIVE_MEMBERS_MONTHLY.
    """
    normalized_start = normalize_date(start)
    # Use the first day of the PREVIOUS month as the denominator period
    if normalized_start is not None:
        first_of_month = normalized_start.replace(day=1)
        # Go to previous month
        if first_of_month.month == 1:
            month_start = first_of_month.replace(year=first_of_month.year - 1, month=12)
        else:
            month_start = first_of_month.replace(month=first_of_month.month - 1)
    else:
        month_start = None

    sql = """
        SELECT
            mh.location_name,
            SUM(am.members) as total_members
        FROM active_members_monthly am
        INNER JOIN (
            SELECT DISTINCT location_name, location_id
            FROM member_history
            WHERE location_name IS NOT NULL
        ) mh ON am.location_id = mh.location_id
        WHERE am.definition = 'Rinsed'
    """.strip()
    params: list = []

    # Exclude Hub Office / Query Server
    sql += _add_exclusions(sql, params, "mh.location_name")

    # Location filter
    normalized_locations = normalize_locations(locations)
    if normalized_locations is not None:
        loc_clause, loc_params = build_location_clause("mh.location_name", normalized_locations)
        sql += f" AND {loc_clause}"
        params.extend(loc_params)

    # Month filter
    if month_start is not None:
        sql += " AND am.month = %s"
        params.append(month_start)

    sql += " GROUP BY mh.location_name ORDER BY mh.location_name"
    return (sql, params)


# ---------------------------------------------------------------------------
# Daily cancellation queries
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Batch daily KPI queries
# ---------------------------------------------------------------------------


def batch_conversion_daily_sql(
    start: DateInput | None, end: DateInput | None, locations: Locations
) -> tuple[str, list]:
    """Daily car count + conversion components from CONVERSION_DAILY."""
    sql = """
        SELECT
            created_date AS kpi_date,
            location_name,
            SUM(total_washes) AS total_car_count,
            SUM(sales) AS conversion_sales,
            SUM(eligible_washes) AS eligible_washes
        FROM conversion_daily
        WHERE 1=1
    """.strip()
    params: list = []
    sql = _apply_filters(sql, params, "created_date", start, end, locations)
    sql += " GROUP BY created_date, location_name ORDER BY created_date, location_name"
    return (sql, params)


def batch_fct_revenue_sql(
    start: DateInput | None, end: DateInput | None, locations: Locations
) -> tuple[str, list]:
    """Daily retail car count + revenue from FCT_REVENUE."""
    sql = """
        SELECT
            DATE(created_at) AS kpi_date,
            location_name,
            COUNT(*) AS retail_car_count,
            SUM(amount) AS retail_revenue,
            COUNT(*) AS retail_transaction_count
        FROM fct_revenue
        WHERE transaction_category = 'Retail Wash'
    """.strip()
    params: list = []
    sql = _apply_filters(sql, params, "created_at", start, end, locations, cast_date=True)
    sql += " GROUP BY DATE(created_at), location_name ORDER BY kpi_date, location_name"
    return (sql, params)


def batch_fct_washes_sql(
    start: DateInput | None, end: DateInput | None, locations: Locations
) -> tuple[str, list]:
    """Daily member car count from FCT_WASHES."""
    sql = """
        SELECT
            DATE(created_at) AS kpi_date,
            location_name,
            COUNT(*) AS member_car_count
        FROM fct_washes
        WHERE transaction_category = 'redemption'
    """.strip()
    params: list = []
    sql = _apply_filters(sql, params, "created_at", start, end, locations, cast_date=True)
    sql += " GROUP BY DATE(created_at), location_name ORDER BY kpi_date, location_name"
    return (sql, params)


def batch_fct_memberships_sql(
    start: DateInput | None, end: DateInput | None, locations: Locations
) -> tuple[str, list]:
    """Daily membership revenue + sales from FCT_MEMBERSHIPS."""
    sql = """
        SELECT
            DATE(created_at) AS kpi_date,
            location_name,
            SUM(CASE WHEN transaction_category IN ('new membership', 'rejoin membership')
                THEN revenue ELSE 0 END) AS membership_revenue_new,
            SUM(CASE WHEN transaction_category = 'renewed membership'
                THEN revenue ELSE 0 END) AS membership_revenue_renewal,
            SUM(revenue) AS membership_revenue,
            COUNT(CASE WHEN transaction_category IN ('new membership', 'rejoin membership')
                THEN 1 END) AS membership_sales,
            SUM(CASE WHEN transaction_category IN ('new membership', 'rejoin membership')
                THEN revenue ELSE 0 END) AS membership_sales_revenue
        FROM fct_memberships
        WHERE transaction_category IN ('new membership', 'rejoin membership', 'renewed membership')
    """.strip()
    params: list = []
    sql = _apply_filters(sql, params, "created_at", start, end, locations, cast_date=True)
    sql += " GROUP BY DATE(created_at), location_name ORDER BY kpi_date, location_name"
    return (sql, params)


# ---------------------------------------------------------------------------
# Daily cancellation queries
# ---------------------------------------------------------------------------


def daily_cancellations_sql(
    start: DateInput | None, end: DateInput | None, locations: Locations
) -> tuple[str, list]:
    """Daily cancellation/churn counts by churn_date and churn_type.

    Uses Rinsed's real-time churn_date (NOT WashU's shifted definition).
    churn_date is a DATE column, so no cast needed.
    """
    sql = """
        SELECT churn_date, churn_type, COUNT(DISTINCT rinsed_membership_id) as cnt
        FROM member_history
        WHERE churn_type IS NOT NULL
    """.strip()
    params: list = []
    sql = _apply_filters(sql, params, "churn_date", start, end, locations)
    sql += " GROUP BY churn_date, churn_type ORDER BY churn_date, churn_type"
    return (sql, params)


def daily_cancellations_by_location_sql(
    start: DateInput | None, end: DateInput | None, locations: Locations
) -> tuple[str, list]:
    """Total cancellations per location for the period."""
    sql = """
        SELECT location_name, COUNT(DISTINCT rinsed_membership_id) as cnt
        FROM member_history
        WHERE churn_type IS NOT NULL
    """.strip()
    params: list = []
    sql = _apply_filters(sql, params, "churn_date", start, end, locations)
    sql += " GROUP BY location_name ORDER BY location_name"
    return (sql, params)
