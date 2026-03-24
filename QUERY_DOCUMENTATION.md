# Daily Location Item Report — Query Documentation

## Overview

This query produces a daily, location-level, item-level report of wash activity, retail revenue, and membership billing from the WashU Rinsed Snowflake database (`WASHU_RINSED_SHARE.MB`). It is designed to feed into Datarails for financial reporting.

**Output grain:** One row per **day** x **location** x **item/plan name**.

**Date parameters:** `:start_date` and `:end_date` (replace with Datarails template variables for production use).

**Excluded locations:** `Hub Office` and `Query Server` are filtered out of all CTEs.

---

## Output Columns

| Column | Type | Description |
|---|---|---|
| `CREATED_DAY` | Date | The calendar date of the activity. |
| `LOCATION_NAME` | String | The wash location name as it appears in Rinsed (e.g., "Burbank", "Carol Stream"). |
| `ITEM_NAME` | String | The wash item or membership plan name. See [Item Name Sources](#item-name-sources) below. |
| `RETAIL_WASH` | Integer | Count of paid base washes by non-members. Pure retail transactions only — no membership involvement. |
| `MEMBER_WASH` | Integer | Count of all member washes. Includes: (1) Redemptions — member scanned their unlimited pass. (2) NM&R — customer bought a new membership and got a wash. (3) RM&R — member renewed and got a wash. If someone buys a membership and gets a wash, that's a member wash, not retail. |
| `RETAIL_WASH_FREE` | Integer | Count of free/comped washes ($0 retail transactions). |
| `TOTAL_WASHES` | Integer | `RETAIL_WASH + MEMBER_WASH + RETAIL_WASH_FREE`. Should match `CONVERSION_DAILY.total_washes` when summed by location and day. |
| `RETAIL_REVENUE` | Decimal | Net revenue from paid retail (non-member) washes only. NM&R and RM&R combo transaction revenue is excluded — those dollars are membership revenue and appear in `MEMBER_REVENUE` or `MEMBER_REVENUE_NEW`. |
| `MEMBER_COUNT` | Integer | Count of **distinct** members who were billed a membership renewal/recharge on this day. Only counts each member's **first** billing event of the month. Subsequent billings (plan changes, mid-cycle adjustments) are captured in `MEMBER_COUNT_MIDCYCLE`. This column is summable across days to produce the monthly distinct renewed member count. |
| `MEMBER_COUNT_MIDCYCLE` | Integer | Count of additional renewal billing events for members who were already counted in `MEMBER_COUNT` earlier in the month. These represent plan switches, mid-cycle adjustments, or other multi-billing scenarios. |
| `MEMBER_REVENUE` | Decimal | Total revenue from all renewed/recharged membership transactions (includes both first billings and mid-cycle billings). |
| `MEMBER_COUNT_NEW` | Integer | Count of **distinct** new membership sales (includes both `new membership` and `rejoin membership` transaction categories). Only counts each member's **first** new sale event of the month. Summable across days to produce the monthly distinct new member count. |
| `MEMBER_COUNT_NEW_MIDCYCLE` | Integer | Count of additional new sale billing events for members already counted in `MEMBER_COUNT_NEW` earlier in the month. Rare in practice. |
| `MEMBER_REVENUE_NEW` | Decimal | Total revenue from all new membership sale transactions. |

### Deriving Monthly Totals

To get the total active member count for a location in a given month (matching the Rinsed frontend):

```
Monthly Active Members = SUM(MEMBER_COUNT) + SUM(MEMBER_COUNT_NEW)
```

This works because each distinct member is only counted once (on their first billing day), so summing across all days in the month produces a true distinct count.

To understand mid-cycle activity volume:

```
Monthly Mid-Cycle Events = SUM(MEMBER_COUNT_MIDCYCLE) + SUM(MEMBER_COUNT_NEW_MIDCYCLE)
```

To reconcile total billing transactions:

```
Total Billing Transactions = SUM(MEMBER_COUNT) + SUM(MEMBER_COUNT_MIDCYCLE) + SUM(MEMBER_COUNT_NEW) + SUM(MEMBER_COUNT_NEW_MIDCYCLE)
```

---

## Item Name Sources

The `ITEM_NAME` column comes from different source tables depending on the metric:

| Metric | Source Table | Column | Examples |
|---|---|---|---|
| Wash counts (RETAIL_WASH, MEMBER_WASH, RETAIL_WASH_FREE) | `FCT_REVENUE` / `FCT_REDEMPTIONS` | `item_name` | "Express Wash", "Clean Wash", "Protect Wash", "UShine Wash" |
| Membership counts and revenue | `FCT_MEMBERSHIPS` | `plan_name` | "Express Monthly Membership (MAIN)", "Family Premium", "Plus Monthly Membership (DOWNSELL)" |

Wash item names and membership plan names are **not** consolidated or grouped. They appear exactly as stored in the source tables. A single row will have either wash metrics populated (with a wash item name) or membership metrics populated (with a plan name), with zeros in the other columns.

---

## Source Tables

| CTE | Source Table | What It Captures |
|---|---|---|
| `retail_washes` | `FCT_REVENUE` | Paid non-member washes: `Retail Wash` transaction category only. |
| `free_washes` | `FCT_REVENUE` | Free/comped washes: `Free Wash` transaction category. |
| `member_washes` | `FCT_REDEMPTIONS` | Membership redemptions (member scanned their unlimited pass). |
| `combo_member_washes` | `FCT_REVENUE` | Combo transactions: `New Membership & Redemption` and `Renewed Membership & Redemption`. Customer bought/renewed a membership AND got a wash — counted as MEMBER_WASH. Revenue is NOT included (it's membership revenue captured via FCT_MEMBERSHIPS). |
| `member_renewed` | `FCT_MEMBERSHIPS` | Renewed/recharged membership billings: `renewed membership` transaction category. Uses `ROW_NUMBER()` to identify first vs. subsequent billings per member per month. |
| `new_members` | `FCT_MEMBERSHIPS` | New membership sales: `new membership` and `rejoin membership` transaction categories. Uses `ROW_NUMBER()` to identify first vs. subsequent billings per member per month. |

---

## WashU Definition of "Active Member"

An active member is **any member who was billed during the calendar month** — whether through a renewal recharge or a new sale. Specifically:

- A member billed on March 19 who cancels in April before their recharge date counts as active for March but **not** April.
- A member who purchased in January and cancels on March 2 (before being billed) counts as a new member in January, a recharged member in February, and is **not** counted in March.
- **Family plans** count each individual member. A family plan with 3 members generates 1 billing transaction but 3 member records — all 3 count toward the membership count.

This differs from Rinsed's definition, which uses a "recharge cadence" snapshot (active if billed within the plan's cadence window). In practice, the two definitions produce totals within ~0.1% of each other.

---

## Validation Against Rinsed Frontend

The query has been validated against the Rinsed frontend across 15 locations and 25 months (Feb 2024 – Feb 2026).

### Wash Counts
- Match `CONVERSION_DAILY` totals exactly across all locations and dates tested.
- One isolated classification edge case: a single wash at Carol Stream on March 18, 2026 is classified as retail in our query vs. free in `CONVERSION_DAILY`. The total wash count is unaffected.

### Member Counts
| Month | Our Query | Rinsed Frontend | Difference |
|---|---|---|---|
| Oct 2025 | 37,031 | 37,019 | +12 (0.03%) |
| Nov 2025 | 38,046 | 38,022 | +24 (0.06%) |
| Dec 2025 | 38,867 | 38,853 | +14 (0.04%) |
| Jan 2026 | 40,032 | 39,976 | +56 (0.14%) |
| Feb 2026 | 45,111 | 45,074 | +37 (0.08%) |

### Sources of the Small Difference (~0.1%)
1. **NULL membership IDs**: ~1% of legacy renewal records lack a `rinsed_membership_id` and cannot be deduplicated. They are counted on their billing day, which may slightly inflate the total.
2. **Rinsed's cadence-based definition** excludes members who were billed but then churned before the snapshot date; our billing-based definition includes them.

---

## Known Nuances

### Combo Transactions (NM&R / RM&R)
`New Membership & Redemption` and `Renewed Membership & Redemption` in `FCT_REVENUE` represent a customer who got a physical wash **and** purchased/renewed a membership in the same transaction. These are counted as `MEMBER_WASH` (the customer is a member at time of wash). Their revenue goes to the membership columns (`MEMBER_REVENUE_NEW` for NM&R, `MEMBER_REVENUE` for RM&R) via `FCT_MEMBERSHIPS`. They do **not** appear in `RETAIL_WASH` or `RETAIL_REVENUE`.

### Family Plans
Locations with significant family plan populations (notably **Dickson** and **Fairview**) have many $0-revenue renewal records. When a family plan renews, the primary member is billed the full amount and each additional family member gets a $0 renewal row in `FCT_MEMBERSHIPS`. All individual family members are counted in `MEMBER_COUNT`.

### New vs. Renewed Classification
At a few locations (Dickson, Fairview, Nolensville), the `transaction_category` in `FCT_MEMBERSHIPS` may classify some members as "renewed" that Rinsed's frontend labels as "New" (or vice versa). The **combined totals** match — this is a labeling difference in the upstream data, not a counting error.

### DRB to Sonny's POS Migration (Two Phases)
Illinois locations transitioned from DRB to Sonny's POS in two phases:
- **Phase 1 (Dec 2024 / Jan 2025):** First group of IL sites migrated. May show similar overlap/double-counting issues as Phase 2.
- **Phase 2 (Apr / May 2025):** Remaining IL sites (Plainfield, Burbank, Berwyn, Joliet, Evergreen Park) migrated. Berwyn showed the largest overlap at +130 members in April 2025 due to overlapping location IDs (legacy `80001` and new `BERWYN0001`).

Both are one-time transition events. Data outside migration months is unaffected.

### Mid-Cycle Changes
Members who switch plans mid-month, receive billing adjustments, or have other mid-cycle events will have multiple rows in `FCT_MEMBERSHIPS` for the same month. The `MEMBER_COUNT_MIDCYCLE` column captures these subsequent billings so that `MEMBER_COUNT` remains a clean, summable distinct count.

---

## File Reference

| File | Purpose |
|---|---|
| `daily_location_item_report.sql` | The production SQL query with `:start_date` / `:end_date` parameters. |
| `generate_report.py` | Python script to query Snowflake and generate the XLSX report with monthly sheets and a summary tab. |
| `QUERY_DOCUMENTATION.md` | This file. |
