"""Schema 21 → 22 (GÖREV-22): rental companies whose homes are read as the company's own inventory across the neighbourhoods, and
three more company sites.

`agency_rate_own_listings` is rebuilt (every row and column kept) so that `region_id` may be empty: a home whose site names no
neighbourhood is stored without one ("mahallesi belirtilmemiş") — it is counted apart and enters no neighbourhood's medians; a
neighbourhood is never taken from an address or from coordinates. Homes stored by earlier runs all have a neighbourhood (the one
community of a company's official rental program) and keep it.

The destination's agency configuration gets the companies of the profile's `AGENCY_SITES_V22` with their options
(`AGENCY_SITE_OPTIONS_V22`), each only when its domain is not there yet; a destination without an agency configuration gets nothing.
The caller owns the backup and the single transaction.
"""
import json

from .destinations import DEFAULT_PROFILE
from .migrations import execute_schema

SCHEMA = """
    CREATE TABLE agency_rate_own_listings_v22 (
        run_id TEXT NOT NULL REFERENCES agency_rate_snapshots(run_id), domain TEXT NOT NULL,
        site_listing_id TEXT NOT NULL CHECK(length(site_listing_id) > 0), title TEXT NOT NULL,
        page_url TEXT NOT NULL CHECK(page_url LIKE 'http%'), address TEXT, city TEXT, region_id TEXT REFERENCES regions(id),
        bedrooms REAL CHECK(bedrooms IS NULL OR bedrooms >= 0), bathrooms REAL CHECK(bathrooms IS NULL OR bathrooms >= 0),
        sleeps REAL CHECK(sleeps IS NULL OR sleeps >= 0),
        latitude REAL CHECK(latitude IS NULL OR latitude BETWEEN -90 AND 90), longitude REAL CHECK(longitude IS NULL OR longitude BETWEEN -180 AND 180),
        page_status TEXT NOT NULL CHECK(page_status IN ('matched','not_found','no_listing','off_site','blocked','error')), message TEXT,
        PRIMARY KEY(run_id,domain,site_listing_id),
        FOREIGN KEY(run_id,domain) REFERENCES agency_rate_companies(run_id,domain)
    );
    INSERT INTO agency_rate_own_listings_v22 (run_id,domain,site_listing_id,title,page_url,address,city,region_id,bedrooms,bathrooms,sleeps,
        latitude,longitude,page_status,message)
        SELECT run_id,domain,site_listing_id,title,page_url,address,city,region_id,bedrooms,bathrooms,sleeps,latitude,longitude,page_status,message
        FROM agency_rate_own_listings;
    DROP TABLE agency_rate_own_listings;
    ALTER TABLE agency_rate_own_listings_v22 RENAME TO agency_rate_own_listings
"""


def seed_v22_sites(con, profile):
    """The profile's new company sites with their options, each once (a domain already configured is left as it is)."""
    destination_id = profile.METADATA["id"]
    if not con.execute("SELECT 1 FROM destination_agency_sites WHERE destination_id=?", (destination_id,)).fetchone():
        return
    order = con.execute("SELECT COALESCE(MAX(sort_order),-1) FROM destination_agency_sites WHERE destination_id=?", (destination_id,)).fetchone()[0]
    options = getattr(profile, "AGENCY_SITE_OPTIONS_V22", {})
    for domain, company, adapter in getattr(profile, "AGENCY_SITES_V22", ()):
        if con.execute("SELECT 1 FROM destination_agency_sites WHERE destination_id=? AND domain=?", (destination_id, domain)).fetchone():
            continue
        order += 1
        chosen = options.get(domain, {})
        con.execute("""INSERT INTO destination_agency_sites (destination_id,domain,company,adapter,enabled,sort_order,aliases,protected,guest_rule,
            inventory) VALUES (?,?,?,?,1,?,?,?,?,?)""",
                    (destination_id, domain, company, adapter, order, json.dumps(chosen.get("aliases", [])), int(chosen.get("protected", 0)),
                     chosen.get("guest_rule", "two_adults"), json.dumps(chosen["inventory"], ensure_ascii=False) if chosen.get("inventory") else None))


def upgrade_v22(con):
    execute_schema(con, SCHEMA)
    seed_v22_sites(con, DEFAULT_PROFILE)
    if con.execute("PRAGMA foreign_key_check").fetchone():
        raise RuntimeError("v22 migration ilişki bütünlüğü kontrolü başarısız oldu.")
    con.execute("PRAGMA user_version=22")
