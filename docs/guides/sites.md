# Sites

List all active wash locations with their details using `client.sites.list()`.

## Basic Usage

```python
from rinsed_snowflake_client import RinsedClient

with RinsedClient() as client:
    sites = client.sites.list()
    for site in sites:
        print(f"{site.location_name} - {site.city}, {site.state}")
```

## Site Object Fields

Each `Site` object contains:

| Field | Type | Description |
|-------|------|-------------|
| `location_id` | `str` | Rinsed location identifier (e.g., `BURBT10001`) |
| `location_name` | `str` | Display name (e.g., `Burbank`) |
| `location_group` | `str \| None` | Parent group (`WashU` or `Wash Associates`) |
| `point_of_sale_provider` | `str \| None` | POS system (`sonnys`) |
| `region_group` | `str \| None` | Geographic region (`Illinois` or `Tennessee`) |
| `sonnys_site_code` | `str \| None` | Sonny's site code (e.g., `BURBT1`) |
| `is_billable` | `bool` | Whether the site is an active, billable location |
| `address` | `str \| None` | Street address |
| `city` | `str \| None` | City |
| `state` | `str \| None` | State abbreviation |
| `zip` | `str \| None` | ZIP code |
| `country` | `str \| None` | Country code |
| `phone` | `str \| None` | Phone number |
| `latitude` | `float \| None` | GPS latitude |
| `longitude` | `float \| None` | GPS longitude |

## Filtering

`list()` automatically filters to only active, billable locations with a Sonny's site code. Hub Office, Query Server, and legacy duplicate location IDs are excluded.

## Use Cases

### Get Location Names for Stats Queries

```python
with RinsedClient() as client:
    sites = client.sites.list()
    location_names = [s.location_name for s in sites]

    # Use in a stats call
    result = client.stats.total_car_count(
        "2026-02-01", "2026-02-28",
        locations=location_names[:5],  # first 5 locations
    )
```

### Filter by Region

```python
with RinsedClient() as client:
    sites = client.sites.list()

    il_sites = [s for s in sites if s.region_group == "Illinois"]
    tn_sites = [s for s in sites if s.region_group == "Tennessee"]

    print(f"Illinois: {len(il_sites)} sites")
    print(f"Tennessee: {len(tn_sites)} sites")

    # Get stats for Illinois only
    il_names = [s.location_name for s in il_sites]
    result = client.stats.total_car_count(
        "2026-02-01", "2026-02-28",
        locations=il_names,
    )
    print(f"Illinois total washes: {result.total:,}")
```

### Build a Location Reference Table

```python
with RinsedClient() as client:
    sites = client.sites.list()

    print(f"{'Name':<16} {'City':<16} {'State':<6} {'Site Code':<10} {'Region'}")
    print("-" * 64)
    for s in sites:
        print(f"{s.location_name:<16} {s.city or '':<16} {s.state or '':<6} {s.sonnys_site_code or '':<10} {s.region_group or ''}")
```

### Export Sites to JSON

```python
import json

with RinsedClient() as client:
    sites = client.sites.list()
    data = [s.model_dump() for s in sites]

    with open("sites.json", "w") as f:
        json.dump(data, f, indent=2)
```

### Cross-Reference with Sonny's Data API Client

The `sonnys_site_code` maps to the `site_code` used in the [Sonny's Data API Client](https://christopher-nance.github.io/Sonnys-Data-API-Client/):

```python
from rinsed_snowflake_client import RinsedClient

with RinsedClient() as client:
    sites = client.sites.list()
    code_map = {s.sonnys_site_code: s.location_name for s in sites}

# Use the mapping with Sonny's client
# sonnys_client = SonnysClient(api_id, api_key, site_code="BURBT1")
# rinsed_name = code_map["BURBT1"]  # "Burbank"
```

## Data Source

Site data comes from the `WEB_INGRESS.LOCATIONS` table in Snowflake. This table is maintained by the Rinsed platform and includes all locations — active, inactive, and internal. The `list()` method filters to only return active, billable wash sites.
