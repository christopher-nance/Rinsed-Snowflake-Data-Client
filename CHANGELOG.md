# Changelog

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
