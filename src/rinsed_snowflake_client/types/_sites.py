"""Pydantic result models for site/location data."""

from rinsed_snowflake_client.types._base import RinsedModel


class Site(RinsedModel):
    """A wash location."""

    location_id: str
    location_name: str
    location_group: str | None = None
    point_of_sale_provider: str | None = None
    region_group: str | None = None
    sonnys_site_code: str | None = None
    is_billable: bool
    address: str | None = None
    city: str | None = None
    state: str | None = None
    zip: str | None = None
    country: str | None = None
    phone: str | None = None
    latitude: float | None = None
    longitude: float | None = None
