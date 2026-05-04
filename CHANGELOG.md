# Changelog

## 0.7.0 — 2026-05-04

### Added
- `client.cohorts` resource — cohort retention analysis powered by `MEMBER_HISTORY`.
- `client.cohorts.retention_grid(start, end, locations?)` — pre-aggregated retention matrix: `cohort_month` x `period_month` with member counts, churned counts (voluntary/involuntary). Period 0 = signup month. Start/end filter by cohort month, not calendar date.
- `client.cohorts.retention_by_plan(start, end, locations?)` — same retention grid sliced by `join_plan_name` (membership plan at time of signup) for plan-level cohort comparison.
- `client.cohorts.members(start, end, locations?)` — member-level drill-down returning one row per member with latest state: current plan, tenure, revenue, churn status, and wash activity (`wash_count`, `last_wash_date`, `first_wash_date`, `avg_washes_per_month`). Wash counts sourced from `FCT_REDEMPTIONS` + NM&R/RM&R combos from `FCT_REVENUE`. Useful for usage frequency analysis, at-risk member identification, promo quality evaluation, and CSV exports.
- New types: `CohortPeriodRow`, `CohortRetentionResult`, `CohortPlanPeriodRow`, `CohortRetentionByPlanResult`, `CohortMemberRow`, `CohortMembersResult`.
- Cohort analysis guide in documentation with retention grid examples, plan-level slicing, member drill-down use cases, SQLite caching patterns, and data model explanation.

### Notes
- `MEMBER_HISTORY` contains one row per member per billing period (~3M rows), with pre-built cohort fields: `cohort_month`, `period_month`, `churn_period`, `join_plan_name`, `join_date`. The client aggregates these into the retention grid shape the frontend needs.
- Retention rate is derived by the consumer: `members_at_period_N / members_at_period_0`. Raw counts are returned to avoid prescribing a single retention definition.
- Members can cancel and rejoin — each stint is a separate cohort entry. A March 2025 cohort includes both new signups and rejoins from that month.

## 0.6.1 — 2026-05-03

### Fixed
- Handle NaN/None values gracefully when constructing result objects from Snowflake query results. All `int()` and `float()` conversions now use `_safe_int()` / `_safe_float()` helpers that coerce NaN/None to 0, preventing `ValueError: cannot convert float NaN to integer` crashes.

## 0.6.0 — 2026-05-03

### Added
- `client.stats.recharge_churn(start, end, locations?)` — daily churn using WashU's recharge methodology. Denominator = prior month same-day (recharges + new members). Retained = current day recharges only. Uses Stripe-style `DATEADD(MONTH, 1, ...)` for day matching — clamps to end-of-month in short months, original day returns in longer months.
- Voluntary/involuntary overlay from `MEMBER_HISTORY` by `churn_date`, documented as using a different date definition than the recharge methodology.
- New types: `DailyRechargeChurn` (per-day breakdown with denominator, retained, churned, rate, vol/invol), `RechargeChurnResult` (aggregate with cumulative rate and by-location).
- Comprehensive churn methodology docs with Stripe billing examples and edge case documentation.

## 0.5.0 — 2026-05-03

### Changed
- **Breaking**: `member_car_count` now sourced from `FCT_REDEMPTIONS` + NM&R/RM&R combos from `FCT_REVENUE` (was `FCT_WASHES` with `transaction_category = 'redemption'`). Includes combo wash events that were previously not counted.
- All queries now filter `location_name IS NOT NULL` to match the v4b source-of-truth query.

### Added
- `client.stats.active_member_count(start, end, locations?)` — active member roster count at end of period, sourced from `ACTIVE_MEMBERS_RINSED`. Matches Rinsed frontend "Active Members Over Time" exactly (46,708 on 2026-03-31).
- New type: `ActiveMemberResult` with `total`, `snapshot_date`, and `by_location` fields.

### Validated
- All 6 metrics (RETAIL_WASH, MEMBER_WASH, RETAIL_REVENUE, MEMBER_REVENUE, MEMBER_COUNT_NEW, MEMBER_REVENUE_NEW) match the v4b source-of-truth query 1:1 across 1,350 day x location rows (Jan 1 – Mar 31, 2026). Zero diffs.
- TOTAL_WASHES (CONVERSION_DAILY vs v4b assembled) differs by 38 washes (0.005%) due to different data sources — acceptable.
- Active member count matches Rinsed frontend to the row.

## 0.4.2 — 2026-03-30

### Changed
- **Breaking**: Churn/cancellation data now sourced from `MEMBER_ACTIVITY_OVERVIEW_MONTHLY` instead of `member_history`. Achieves 100% match with Rinsed frontend (was ~41%).
- `batch_cancellations_sql` now returns `voluntary_cancellations`, `involuntary_cancellations`, AND `active_members` from a single query against `MEMBER_ACTIVITY_OVERVIEW_MONTHLY`
- Removed `batch_active_members_sql` (merged into `batch_cancellations_sql`)
- `daily_kpis()` now executes 5 queries (was 6)

## 0.4.1 — 2026-03-30

### Changed
- **Breaking**: `batch_cancellations_sql` now uses WashU's billing-cycle definition — cancellations are reported in the first month the member is NOT charged (`DATEADD(MONTH, 1, created_month)`) instead of the real-time `churn_date`. This changes `voluntary_cancellations` and `involuntary_cancellations` values in `DailyKPIRow` from daily to monthly granularity.

### Added
- `active_members` field on `DailyKPIRow` — monthly active member count per location from `ACTIVE_MEMBERS_MONTHLY`
- `batch_active_members_sql` query function for monthly active member counts
- `daily_kpis()` now executes 6 queries (was 5) — adds active member denominator for churn rate computation

### Notes
- Cancellation and active member rows use first-of-month dates in the grid. Daily KPI rows without cancellation data keep `0` defaults.
- Consumer computes churn rate as `(voluntary + involuntary) / active_members_prev_month * 100`.

## 0.4.0 — 2026-03-30

### Added
- `client.stats.daily_kpis(start, end, locations?)` — batch method returning all non-churn KPIs at daily × location granularity in just 4 Snowflake queries (vs. 7+ per location per day previously)
- New types: `DailyKPIRow` (single location-day with all KPI components), `DailyKPIResult` (batch result with metadata)
- Each `DailyKPIRow` includes raw components: `total_car_count`, `retail_car_count`, `member_car_count`, `retail_revenue`, `retail_transaction_count`, `membership_revenue`, `membership_revenue_new`, `membership_revenue_renewal`, `membership_sales`, `membership_sales_revenue`, `eligible_washes`, `conversion_sales`, `voluntary_cancellations`, `involuntary_cancellations`
- Derived metrics (AWP, conversion rate) left to consumer — avoids division-by-zero in the data layer

### Notes
- Churn *rates* are a monthly metric and are excluded from `daily_kpis()`. Use `voluntary_churn_rate()` / `involuntary_churn_rate()` separately.
- Daily cancellation *counts* (voluntary + involuntary) are included per location per day via `member_history.churn_date`.

## 0.3.1 — 2026-03-25

### Changed
- Added Wash Associates Business Internal Use License 1.0 (matching Sonny's Data API Client)
- Updated pyproject.toml license reference

## 0.3.0 — 2026-03-24

### Added
- `client.stats.cancellations(start, end, locations?)` — daily cancellation counts (voluntary + involuntary) using Rinsed's real-time churn_date
- `client.stats.daily_churn(start, end, locations?)` — daily churn counts with active member denominator and rate context
- New types: `DailyCancellation`, `DailyCancellationResult`, `DailyChurnResult`

## 0.2.0 — 2026-03-24

### Added
- `client.sites.list()` method returning typed `Site` objects from `WEB_INGRESS.LOCATIONS`
- Sites guide in documentation with use cases and cross-reference examples

### Fixed
- `AWPResult` now has `.total` field for consistency with all other result models (`.awp` preserved as alias)
- Timestamp columns (`created_at`) now use `DATE()` cast for correct day-level filtering
- Churn denominator uses previous month's active members (matching Rinsed's calculation)
- Churn numerator uses WashU's billing-cycle definition (shifted one month from Rinsed)
- Retail car count correctly excludes NM&R/RM&R combo washes
- Install command in docs corrected to use GitHub URL

### Documentation
- Comprehensive guides with examples, use cases, and edge cases
- Error handling guide with exception hierarchy and debugging tips
- Raw queries guide with table reference and parameterized query examples
- API reference auto-generated from docstrings

## 0.1.0 — 2026-03-24

### Added
- Initial release
- `RinsedClient` with context manager and explicit credential support
- 10 KPI methods on `client.stats`: `total_car_count`, `retail_car_count`, `member_car_count`, `retail_revenue`, `membership_revenue`, `average_wash_price`, `new_membership_sales`, `conversion_rate`, `voluntary_churn_rate`, `involuntary_churn_rate`
- `report()` bundled method for all KPIs in one call
- `query()` raw SQL escape hatch returning pandas DataFrames
- Pydantic v2 typed result models
- MkDocs documentation with GitHub Pages
