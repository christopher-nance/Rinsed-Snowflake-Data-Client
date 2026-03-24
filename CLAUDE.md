# CLAUDE.md

## Project Overview

Rinsed Snowflake Data Client — a pip-installable Python package for accessing WashU Carwash Rinsed CRM data in Snowflake. Mirrors the Sonny's Data API Client patterns (`client.stats.*`, `client.sites.*`, Pydantic return types).

- **Package name:** `rinsed-snowflake-client`
- **Import:** `rinsed_snowflake_client`
- **Install:** `pip install git+https://github.com/christopher-nance/Rinsed-Snowflake-Data-Client.git`
- **Docs:** https://christopher-nance.github.io/Rinsed-Snowflake-Data-Client/

## Before Committing to GitHub

1. **Update the changelog:** Add an entry to `CHANGELOG.md` under the new version describing what changed.
2. **Bump the version number** in **both** files:
   - `pyproject.toml` → `version = "x.y.z"`
   - `src/rinsed_snowflake_client/_version.py` → `__version__ = "x.y.z"`
3. **Redeploy docs** if any docs files changed: `python -m mkdocs gh-deploy --force`

Users install via `pip install git+...` which caches by version — without a bump, they won't get new code.

## Versioning

Follow semver:
- **Patch** (0.2.1): bug fixes, no API changes
- **Minor** (0.3.0): new features, backward-compatible
- **Major** (1.0.0): breaking API changes

## Key Architecture

- `src/rinsed_snowflake_client/` — package source (src layout)
- `_client.py` — `RinsedClient` main class with `sites` and `stats` cached properties
- `_query_builder.py` — all SQL construction, Hub Office/Query Server always excluded
- `resources/_stats.py` — StatsResource with all KPI methods
- `resources/_sites.py` — SitesResource with list() from WEB_INGRESS.LOCATIONS
- `types/_stats.py` — Pydantic result models (all have `.total` field)
- `types/_sites.py` — Site model
- `_filters.py` — date/location normalization and parameterized SQL builders
- `_connection.py` — Snowflake connection wrapper, uses `DATE()` cast for timestamp columns

## Business Logic Notes

- **NM&R / RM&R** combo transactions are membership washes, NOT retail
- **Churn** uses WashU's billing-cycle definition (shifted one month forward from Rinsed)
- **Active member denominator** for churn comes from the PREVIOUS month's `ACTIVE_MEMBERS_MONTHLY`
- **Hub Office** and **Query Server** are always excluded from all queries

## Testing

- `python -m pytest tests/` — unit tests with mocked Snowflake
- Integration tests require `.env` with real Snowflake credentials
