"""v10 -> v11: lodging listings keep the rental company's own listing page and phone numbers (bookdirect-lodging/2), and
rental companies' own sites are asked for prices (agency-lodging-rates/1).

The caller owns the backup and the single transaction; any failure rolls everything back. Existing lodging rows get NULL
(bookdirect-lodging/1 did not store these fields; their raw responses still contain them). Existing sources, history, runs,
domain snapshots and raw files are not modified; the destination's agency site list and source are added once.
"""
import uuid
from datetime import datetime, timezone

from .destinations import DEFAULT_PROFILE
from .migrations import execute_schema
from .sources.agency_rates import AgencyRatesConnector

SCHEMA = """
    ALTER TABLE lodging_listings ADD COLUMN url TEXT CHECK(url IS NULL OR url LIKE 'http%');
    ALTER TABLE lodging_listings ADD COLUMN phone TEXT;
    ALTER TABLE lodging_listings ADD COLUMN toll_free TEXT;
    CREATE TABLE job_waits (
        job_id TEXT PRIMARY KEY REFERENCES jobs(id), site TEXT NOT NULL CHECK(length(site) > 0), since TEXT NOT NULL
    );
    CREATE TABLE destination_agency_sites (
        destination_id TEXT NOT NULL REFERENCES destinations(id),
        domain TEXT NOT NULL CHECK(domain = lower(domain) AND domain NOT LIKE 'www.%' AND instr(domain, '.') > 1
                                   AND domain NOT GLOB '*[^a-z0-9.-]*'),
        company TEXT NOT NULL CHECK(length(trim(company)) > 0),
        adapter TEXT NOT NULL CHECK(length(adapter) > 0 AND adapter NOT GLOB '*[^a-z_]*'),
        enabled INTEGER NOT NULL CHECK(enabled IN (0,1)), sort_order INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY(destination_id,domain)
    );
    CREATE TABLE agency_rate_snapshots (
        run_id TEXT PRIMARY KEY REFERENCES source_runs(id), lodging_run_id TEXT NOT NULL REFERENCES lodging_snapshots(run_id),
        queried_on TEXT NOT NULL CHECK(date(queried_on) IS queried_on), request_count INTEGER NOT NULL CHECK(request_count >= 0),
        listing_count INTEGER NOT NULL CHECK(listing_count >= 0)
    );
    CREATE TABLE agency_rate_windows (
        run_id TEXT NOT NULL REFERENCES agency_rate_snapshots(run_id), window_key TEXT NOT NULL, label TEXT NOT NULL,
        checkin TEXT NOT NULL CHECK(date(checkin) IS checkin), checkout TEXT NOT NULL CHECK(date(checkout) IS checkout AND checkout > checkin),
        nights INTEGER NOT NULL CHECK(nights > 0), status TEXT NOT NULL CHECK(status IN ('queried','skipped_past')),
        PRIMARY KEY(run_id,window_key)
    );
    CREATE TABLE agency_rate_companies (
        run_id TEXT NOT NULL REFERENCES agency_rate_snapshots(run_id), domain TEXT NOT NULL, company TEXT NOT NULL, adapter TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('done','stopped_blocked','stopped_errors','verification_timeout','verification_unavailable','failed')),
        listing_count INTEGER NOT NULL CHECK(listing_count >= 0), matched_count INTEGER NOT NULL CHECK(matched_count BETWEEN 0 AND listing_count),
        quote_count INTEGER NOT NULL CHECK(quote_count >= 0), priced_count INTEGER NOT NULL CHECK(priced_count BETWEEN 0 AND quote_count),
        request_count INTEGER NOT NULL CHECK(request_count >= 0),
        verification TEXT CHECK(verification IS NULL OR verification IN ('completed','timeout','unavailable')), message TEXT,
        PRIMARY KEY(run_id,domain)
    );
    CREATE TABLE agency_rate_listings (
        run_id TEXT NOT NULL REFERENCES agency_rate_snapshots(run_id), lodging_id INTEGER NOT NULL CHECK(lodging_id > 0), title TEXT NOT NULL,
        bedrooms REAL CHECK(bedrooms IS NULL OR bedrooms >= 0),
        region_ids TEXT NOT NULL CHECK(json_valid(region_ids) AND json_type(region_ids)='array'),
        listing_url TEXT CHECK(listing_url IS NULL OR listing_url LIKE 'http%'), url_host TEXT, domain TEXT,
        page_status TEXT NOT NULL CHECK(page_status IN ('matched','not_found','no_listing','off_site','blocked','error','not_queried','no_adapter','no_url')),
        page_url TEXT, http_status INTEGER, site_listing_id TEXT, message TEXT,
        CHECK((page_status IN ('no_url','no_adapter')) = (domain IS NULL)),
        CHECK((page_status = 'matched') = (site_listing_id IS NOT NULL)),
        PRIMARY KEY(run_id,lodging_id),
        FOREIGN KEY(run_id,domain) REFERENCES agency_rate_companies(run_id,domain)
    );
    CREATE TABLE agency_rate_quotes (
        run_id TEXT NOT NULL, lodging_id INTEGER NOT NULL, window_key TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('priced','unavailable','restricted','no_price','error')),
        available INTEGER CHECK(available IS NULL OR available IN (0,1)),
        nightly_rates TEXT CHECK(nightly_rates IS NULL OR json_valid(nightly_rates) AND json_type(nightly_rates)='array'),
        rent REAL, cleaning_fee REAL, other_fees REAL,
        fees TEXT CHECK(fees IS NULL OR json_valid(fees) AND json_type(fees)='array'),
        taxes REAL, tax_items TEXT CHECK(tax_items IS NULL OR json_valid(tax_items) AND json_type(tax_items)='array'),
        total REAL CHECK(total IS NULL OR total >= 0),
        total_includes_fees INTEGER CHECK(total_includes_fees IS NULL OR total_includes_fees IN (0,1)),
        total_includes_taxes INTEGER CHECK(total_includes_taxes IS NULL OR total_includes_taxes IN (0,1)),
        excluded_items TEXT CHECK(excluded_items IS NULL OR json_valid(excluded_items) AND json_type(excluded_items)='array'),
        currency TEXT CHECK(currency IS NULL OR length(currency) = 3), min_stay INTEGER CHECK(min_stay IS NULL OR min_stay > 0),
        checkin_days TEXT CHECK(checkin_days IS NULL OR json_valid(checkin_days) AND json_type(checkin_days)='array'),
        rule_source TEXT CHECK(rule_source IS NULL OR rule_source IN ('sayfa','yanıt')), message TEXT,
        queried_at TEXT NOT NULL, queried_url TEXT NOT NULL,
        raw_sha256 TEXT NOT NULL CHECK(json_valid(raw_sha256) AND json_type(raw_sha256)='array'),
        CHECK(status <> 'priced' OR available = 1 AND (total IS NOT NULL OR rent IS NOT NULL)),
        PRIMARY KEY(run_id,lodging_id,window_key),
        FOREIGN KEY(run_id,lodging_id) REFERENCES agency_rate_listings(run_id,lodging_id),
        FOREIGN KEY(run_id,window_key) REFERENCES agency_rate_windows(run_id,window_key)
    );
    CREATE INDEX agency_rate_quotes_window ON agency_rate_quotes(run_id,window_key);
"""


def seed_destination_agencies(con, profile):
    """Copy the profile's agency site list and source into SQLite once; existing rows are never overwritten."""
    destination_id = profile.METADATA["id"]
    sites = getattr(profile, "AGENCY_SITES", ())
    host = getattr(profile, "LODGING_CLONE_HOST", None)
    if not sites or not host or not con.execute("SELECT 1 FROM destinations WHERE id=?", (destination_id,)).fetchone():
        return
    if not con.execute("SELECT 1 FROM destination_agency_sites WHERE destination_id=?", (destination_id,)).fetchone():
        con.executemany("INSERT INTO destination_agency_sites (destination_id,domain,company,adapter,enabled,sort_order) VALUES (?,?,?,?,1,?)",
                        [(destination_id, domain, company, adapter, order) for order, (domain, company, adapter) in enumerate(sites)])
    connector = AgencyRatesConnector()
    if any(connector.supports(dict(row)) for row in con.execute("SELECT * FROM sources WHERE destination_id=?", (destination_id,))):
        return
    seed = next((seed for seed in profile.SEEDS if connector.supports({"url": seed[1]})), None)
    if seed is None:
        return
    name, url, category, notes, method = seed
    stamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    con.execute("""INSERT INTO sources (id,name,url,category,region,method,cadence,notes,enabled,version,
        created_at,updated_at,destination_id,scope_region_id) VALUES (?,?,?,?,?,?,?,?,1,1,?,?,?,NULL)""",
        (uuid.uuid4().hex, name, url, category, f"Tüm {profile.METADATA['name']}", method, "Gerektiğinde", notes, stamp, stamp, destination_id))


def upgrade_v11(con):
    execute_schema(con, SCHEMA)
    seed_destination_agencies(con, DEFAULT_PROFILE)
    if con.execute("PRAGMA foreign_key_check").fetchone():
        raise RuntimeError("Konaklama fiyatı migration ilişki bütünlüğü kontrolü başarısız oldu.")
    con.execute("PRAGMA user_version=11")
