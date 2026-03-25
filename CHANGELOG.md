# Changelog

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
