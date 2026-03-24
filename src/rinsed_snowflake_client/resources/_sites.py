"""Sites resource — location listing."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rinsed_snowflake_client.types._sites import Site

if TYPE_CHECKING:
    from rinsed_snowflake_client._client import RinsedClient


class SitesResource:
    """Location/site listing methods.

    Access via ``client.sites``.
    """

    def __init__(self, client: RinsedClient) -> None:
        self._client = client

    def list(self) -> list[Site]:
        """List all wash locations.

        Returns only active, billable locations (excludes Hub Office,
        Query Server, and legacy duplicate location IDs). Sourced from
        the ``WEB_INGRESS.LOCATIONS`` table.

        Returns:
            List of Site objects with location details.

        Examples:
            >>> with RinsedClient() as client:
            ...     sites = client.sites.list()
            ...     for site in sites:
            ...         print(f"{site.location_name} ({site.city}, {site.state})")
        """
        sql = """
            SELECT
                location_id,
                location_name,
                location_group,
                point_of_sale_provider,
                region_group,
                sonnys_site_code,
                is_billable,
                address,
                city,
                state,
                zip,
                country,
                phone,
                latitude,
                longitude
            FROM WEB_INGRESS.LOCATIONS
            WHERE is_billable = TRUE
            AND location_name NOT IN ('Hub Office', 'Query Server')
            AND sonnys_site_code IS NOT NULL
            ORDER BY location_name
        """.strip()
        df = self._client._execute(sql)
        sites = []
        for _, r in df.iterrows():
            sites.append(Site(
                location_id=r["location_id"],
                location_name=r["location_name"],
                location_group=r["location_group"] if r["location_group"] else None,
                point_of_sale_provider=r["point_of_sale_provider"] if r["point_of_sale_provider"] else None,
                region_group=r["region_group"] if r["region_group"] else None,
                sonnys_site_code=r["sonnys_site_code"] if r["sonnys_site_code"] else None,
                is_billable=bool(r["is_billable"]),
                address=r["address"] if r["address"] else None,
                city=r["city"] if r["city"] else None,
                state=r["state"] if r["state"] else None,
                zip=r["zip"] if r["zip"] else None,
                country=r["country"] if r["country"] else None,
                phone=r["phone"] if r["phone"] else None,
                latitude=float(r["latitude"]) if r["latitude"] is not None else None,
                longitude=float(r["longitude"]) if r["longitude"] is not None else None,
            ))
        return sites
