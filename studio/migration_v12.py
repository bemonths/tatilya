"""v11 -> v12: rental company prices by link, address, location and own inventory (agency-lodging-rates/2), the Fall 2027
window, restaurant facts from the businesses' own websites (restaurant-sites/1) and the National Weather Service source's
method default.

The caller owns the backup and the single transaction; any failure rolls everything back. Existing agency runs keep their rows:
their matched listings were matched by link (match_method 'link', link_status = page_status) and their quotes were asked for two
adults where the site's request carried a guest count (ResCMS, Streamline, router) and without a guest count on Track sites;
these facts are written to the new columns. Configuration: new companies and the new options of existing companies come from the
profile once; a row the user changed is never overwritten.
"""
import json
import uuid
from datetime import datetime, timezone

from .destinations import DEFAULT_PROFILE
from .migrations import execute_schema
from .sources.weather import SOURCE_URL as NWS_URL

QUOTE_COLUMNS = """
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
        adults INTEGER CHECK(adults IS NULL OR adults > 0), children INTEGER CHECK(children IS NULL OR children >= 0),
        queried_at TEXT NOT NULL, queried_url TEXT NOT NULL,
        raw_sha256 TEXT NOT NULL CHECK(json_valid(raw_sha256) AND json_type(raw_sha256)='array'),
        CHECK(status <> 'priced' OR available = 1 AND (total IS NOT NULL OR rent IS NOT NULL)),"""

SCHEMA = f"""
    ALTER TABLE destination_agency_sites ADD COLUMN aliases TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(aliases) AND json_type(aliases)='array');
    ALTER TABLE destination_agency_sites ADD COLUMN protected INTEGER NOT NULL DEFAULT 0 CHECK(protected IN (0,1));
    ALTER TABLE destination_agency_sites ADD COLUMN guest_rule TEXT NOT NULL DEFAULT 'two_adults' CHECK(guest_rule IN ('two_adults','bedrooms_x2'));
    ALTER TABLE destination_agency_sites ADD COLUMN inventory TEXT CHECK(inventory IS NULL OR json_valid(inventory) AND json_type(inventory)='object');
    ALTER TABLE destination_agency_sites ADD COLUMN own_region_id TEXT REFERENCES regions(id);
    ALTER TABLE destination_agency_sites ADD COLUMN own_city TEXT CHECK((own_city IS NULL) = (own_region_id IS NULL));
    ALTER TABLE agency_rate_companies ADD COLUMN protected INTEGER CHECK(protected IS NULL OR protected IN (0,1));
    ALTER TABLE agency_rate_companies ADD COLUMN guest_rule TEXT CHECK(guest_rule IS NULL OR guest_rule IN ('two_adults','bedrooms_x2'));
    ALTER TABLE agency_rate_companies ADD COLUMN inventory_count INTEGER CHECK(inventory_count IS NULL OR inventory_count >= 0);
    ALTER TABLE agency_rate_companies ADD COLUMN inventory_raw_sha256 TEXT CHECK(inventory_raw_sha256 IS NULL OR json_valid(inventory_raw_sha256));
    ALTER TABLE agency_rate_companies ADD COLUMN own_count INTEGER NOT NULL DEFAULT 0 CHECK(own_count >= 0);
    ALTER TABLE agency_rate_companies ADD COLUMN own_outside INTEGER CHECK(own_outside IS NULL OR own_outside >= 0);
    ALTER TABLE agency_rate_companies ADD COLUMN own_on_bookdirect INTEGER CHECK(own_on_bookdirect IS NULL OR own_on_bookdirect >= 0);
    ALTER TABLE agency_rate_companies ADD COLUMN match_counts TEXT CHECK(match_counts IS NULL OR json_valid(match_counts));
    ALTER TABLE agency_rate_listings ADD COLUMN link_status TEXT
        CHECK(link_status IS NULL OR link_status IN ('matched','not_found','no_listing','off_site','blocked','error'));
    ALTER TABLE agency_rate_listings ADD COLUMN match_method TEXT CHECK(match_method IS NULL OR match_method IN ('link','address','location'));
    ALTER TABLE agency_rate_listings ADD COLUMN match_note TEXT;
    ALTER TABLE agency_rate_quotes ADD COLUMN adults INTEGER CHECK(adults IS NULL OR adults > 0);
    ALTER TABLE agency_rate_quotes ADD COLUMN children INTEGER CHECK(children IS NULL OR children >= 0);
    CREATE TABLE agency_rate_own_listings (
        run_id TEXT NOT NULL REFERENCES agency_rate_snapshots(run_id), domain TEXT NOT NULL,
        site_listing_id TEXT NOT NULL CHECK(length(site_listing_id) > 0), title TEXT NOT NULL,
        page_url TEXT NOT NULL CHECK(page_url LIKE 'http%'), address TEXT, city TEXT, region_id TEXT NOT NULL REFERENCES regions(id),
        bedrooms REAL CHECK(bedrooms IS NULL OR bedrooms >= 0), bathrooms REAL CHECK(bathrooms IS NULL OR bathrooms >= 0),
        sleeps REAL CHECK(sleeps IS NULL OR sleeps >= 0),
        latitude REAL CHECK(latitude IS NULL OR latitude BETWEEN -90 AND 90), longitude REAL CHECK(longitude IS NULL OR longitude BETWEEN -180 AND 180),
        page_status TEXT NOT NULL CHECK(page_status IN ('matched','not_found','no_listing','off_site','blocked','error')), message TEXT,
        PRIMARY KEY(run_id,domain,site_listing_id),
        FOREIGN KEY(run_id,domain) REFERENCES agency_rate_companies(run_id,domain)
    );
    CREATE TABLE agency_rate_own_quotes (
        run_id TEXT NOT NULL, domain TEXT NOT NULL, site_listing_id TEXT NOT NULL, window_key TEXT NOT NULL,{QUOTE_COLUMNS}
        PRIMARY KEY(run_id,domain,site_listing_id,window_key),
        FOREIGN KEY(run_id,domain,site_listing_id) REFERENCES agency_rate_own_listings(run_id,domain,site_listing_id),
        FOREIGN KEY(run_id,window_key) REFERENCES agency_rate_windows(run_id,window_key)
    );
    CREATE TABLE restaurant_site_snapshots (
        run_id TEXT PRIMARY KEY REFERENCES source_runs(id), restaurant_run_id TEXT NOT NULL REFERENCES source_runs(id),
        checked_on TEXT NOT NULL CHECK(date(checked_on) IS checked_on), request_count INTEGER NOT NULL CHECK(request_count >= 0),
        restaurant_count INTEGER NOT NULL CHECK(restaurant_count >= 0)
    );
    CREATE TABLE restaurant_sites (
        run_id TEXT NOT NULL REFERENCES restaurant_site_snapshots(run_id), external_id TEXT NOT NULL, name TEXT NOT NULL,
        site_url TEXT CHECK(site_url IS NULL OR site_url LIKE 'http%'), site_source TEXT NOT NULL CHECK(site_source IN ('directory','review','none')),
        site_status TEXT NOT NULL CHECK(site_status IN ('working','not_found','closed_permanently','closed_season','other_business','unreachable',
                                                        'social_login','no_site')),
        final_url TEXT, http_status INTEGER, status_note TEXT, fetched_at TEXT, raw_sha256 TEXT,
        page_count INTEGER NOT NULL DEFAULT 0 CHECK(page_count >= 0),
        CHECK((site_status = 'no_site') = (site_url IS NULL)),
        PRIMARY KEY(run_id,external_id)
    );
    CREATE TABLE restaurant_facts (
        run_id TEXT NOT NULL, external_id TEXT NOT NULL,
        field TEXT NOT NULL CHECK(field IN ('hours','reservation','kids_menu','outdoor_seating','water_view','dog_friendly','site_price_range')),
        value TEXT NOT NULL CHECK(length(value) > 0), detail TEXT, link_url TEXT, data TEXT CHECK(data IS NULL OR json_valid(data)),
        source_url TEXT NOT NULL, fetched_at TEXT NOT NULL, raw_sha256 TEXT NOT NULL,
        method TEXT NOT NULL CHECK(method IN ('yapısal veri','sayfa metni','PDF metni','platform verisi','görüntüden okundu','bağlantı')),
        CHECK(field <> 'reservation' OR value IN ('online','phone','not_taken','waitlist')),
        CHECK(field NOT IN ('kids_menu','outdoor_seating','water_view','dog_friendly') OR value IN ('yes','no')),
        PRIMARY KEY(run_id,external_id,field),
        FOREIGN KEY(run_id,external_id) REFERENCES restaurant_sites(run_id,external_id)
    );
    CREATE TABLE restaurant_menus (
        run_id TEXT NOT NULL, external_id TEXT NOT NULL, menu_id INTEGER NOT NULL CHECK(menu_id > 0),
        url TEXT NOT NULL CHECK(url LIKE 'http%'), format TEXT NOT NULL CHECK(format IN ('html','pdf','image','platform')),
        menu_type TEXT NOT NULL CHECK(menu_type IN ('dinner','lunch','general','brunch','breakfast','kids','drinks','dessert','happy_hour')),
        title TEXT, platform TEXT, linked_from TEXT, fetched_at TEXT, raw_sha256 TEXT,
        method TEXT CHECK(method IS NULL OR method IN ('yapısal veri','sayfa metni','PDF metni','platform verisi','görüntüden okundu','bağlantı')),
        status TEXT NOT NULL CHECK(status IN ('read','no_items','image_unread','error')), message TEXT,
        item_count INTEGER NOT NULL DEFAULT 0 CHECK(item_count >= 0),
        CHECK((status = 'read') = (item_count > 0)),
        PRIMARY KEY(run_id,external_id,menu_id),
        FOREIGN KEY(run_id,external_id) REFERENCES restaurant_sites(run_id,external_id)
    );
    CREATE TABLE restaurant_menu_items (
        run_id TEXT NOT NULL, external_id TEXT NOT NULL, menu_id INTEGER NOT NULL, position INTEGER NOT NULL CHECK(position > 0),
        section TEXT, section_class TEXT NOT NULL CHECK(section_class IN ('ana_yemek','baslangic','salata_corba','tatli','icecek','cocuk','yan_urun','diger')),
        class_basis TEXT NOT NULL CHECK(class_basis IN ('section','name','menu')),
        name TEXT NOT NULL CHECK(length(name) > 0), price_text TEXT, price REAL CHECK(price IS NULL OR price >= 0),
        price_rule TEXT NOT NULL CHECK(price_rule IN ('single','lowest','market')),
        method TEXT NOT NULL CHECK(method IN ('sayfa metni','PDF metni','platform verisi','görüntüden okundu')),
        CHECK((price_rule = 'market') = (price IS NULL)),
        PRIMARY KEY(run_id,external_id,menu_id,position),
        FOREIGN KEY(run_id,external_id,menu_id) REFERENCES restaurant_menus(run_id,external_id,menu_id)
    );
    CREATE INDEX restaurant_menu_items_menu ON restaurant_menu_items(run_id,external_id,menu_id);
    CREATE TABLE agency_rate_published (
        run_id TEXT NOT NULL, lodging_id INTEGER NOT NULL, window_key TEXT NOT NULL,
        season_start TEXT NOT NULL CHECK(date(season_start) IS season_start), season_end TEXT NOT NULL CHECK(date(season_end) IS season_end),
        rate_text TEXT NOT NULL, rate_period TEXT NOT NULL CHECK(rate_period IN ('night','week')),
        rent_low REAL NOT NULL CHECK(rent_low > 0), rent_high REAL NOT NULL CHECK(rent_high >= rent_low), basis TEXT NOT NULL,
        source_url TEXT NOT NULL, raw_sha256 TEXT NOT NULL CHECK(json_valid(raw_sha256) AND json_type(raw_sha256)='array'),
        PRIMARY KEY(run_id,lodging_id,window_key),
        FOREIGN KEY(run_id,lodging_id) REFERENCES agency_rate_listings(run_id,lodging_id),
        FOREIGN KEY(run_id,window_key) REFERENCES agency_rate_windows(run_id,window_key)
    );
"""
OLD_NWS_NOTE = "Hava verisi için başlangıç kaynağı. Bölge koordinatları ve veri uçları sonraki aşamada belirlenecek."
GUESTLESS_V1_ADAPTERS = ("track",)       # agency-lodging-rates/1 sent no guest count on these platforms


def backfill_v11_runs(con):
    con.execute("UPDATE agency_rate_listings SET match_method='link' WHERE page_status='matched'")
    con.execute("UPDATE agency_rate_listings SET link_status=page_status WHERE page_status IN ('matched','not_found','no_listing','off_site','blocked','error')")
    con.execute(f"""UPDATE agency_rate_quotes SET adults=2, children=0 WHERE EXISTS (SELECT 1 FROM agency_rate_listings l JOIN agency_rate_companies c
        ON c.run_id=l.run_id AND c.domain=l.domain WHERE l.run_id=agency_rate_quotes.run_id AND l.lodging_id=agency_rate_quotes.lodging_id
        AND c.adapter NOT IN ({','.join('?' * len(GUESTLESS_V1_ADAPTERS))}))""", GUESTLESS_V1_ADAPTERS)
    con.execute("UPDATE agency_rate_companies SET protected=0, guest_rule='two_adults'")


def seed_v12_configuration(con, profile):
    """New companies, the new options of the companies v11 added (only while their options are still the defaults) and the new
    lodging windows; every row is added once."""
    destination_id = profile.METADATA["id"]
    if not con.execute("SELECT 1 FROM destinations WHERE id=?", (destination_id,)).fetchone():
        return
    if con.execute("SELECT 1 FROM destination_lodging_sources WHERE destination_id=?", (destination_id,)).fetchone():
        order = con.execute("SELECT COALESCE(MAX(sort_order),-1) FROM destination_lodging_windows WHERE destination_id=?", (destination_id,)).fetchone()[0]
        for key, label, checkin, checkout in getattr(profile, "LODGING_WINDOWS_V12", ()):
            if not con.execute("SELECT 1 FROM destination_lodging_windows WHERE destination_id=? AND window_key=?", (destination_id, key)).fetchone():
                order += 1
                con.execute("INSERT INTO destination_lodging_windows (destination_id,window_key,label,checkin,checkout,sort_order,enabled) VALUES (?,?,?,?,?,?,1)",
                            (destination_id, key, label, checkin, checkout, order))
    if not con.execute("SELECT 1 FROM destination_agency_sites WHERE destination_id=?", (destination_id,)).fetchone():
        return          # the destination has no agency configuration (v11 did not seed one); nothing to extend
    order = con.execute("SELECT COALESCE(MAX(sort_order),-1) FROM destination_agency_sites WHERE destination_id=?", (destination_id,)).fetchone()[0]
    for domain, company, adapter in getattr(profile, "AGENCY_SITES_V12", ()):
        if not con.execute("SELECT 1 FROM destination_agency_sites WHERE destination_id=? AND domain=?", (destination_id, domain)).fetchone():
            order += 1
            con.execute("INSERT INTO destination_agency_sites (destination_id,domain,company,adapter,enabled,sort_order) VALUES (?,?,?,?,1,?)",
                        (destination_id, domain, company, adapter, order))
    for domain, options in getattr(profile, "AGENCY_SITE_OPTIONS", {}).items():
        con.execute("""UPDATE destination_agency_sites SET aliases=?, protected=?, guest_rule=?, inventory=?, own_region_id=?, own_city=?
            WHERE destination_id=? AND domain=? AND aliases='[]' AND protected=0 AND guest_rule='two_adults' AND inventory IS NULL AND own_region_id IS NULL""",
            (json.dumps(options.get("aliases", [])), int(options.get("protected", 0)), options.get("guest_rule", "two_adults"),
             json.dumps(options["inventory"]) if options.get("inventory") else None, options.get("own_region_id"), options.get("own_city"),
             destination_id, domain))


def seed_restaurant_sites_source(con, profile):
    """The restaurant-sites source of the destination, added once from the profile seeds."""
    from .sources.restaurant_sites import RestaurantSitesConnector
    destination_id = profile.METADATA["id"]
    if not con.execute("SELECT 1 FROM destinations WHERE id=?", (destination_id,)).fetchone():
        return
    connector = RestaurantSitesConnector()
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


def repair_nws_default(con):
    """The NWS source still carrying the first-install placeholder method gets its connector's method (and the current default note
    when its note is the untouched old one)."""
    from .sources.weather import WeatherConnector
    method = WeatherConnector.method
    current = next(seed[3] for seed in DEFAULT_PROFILE.SEEDS if seed[1] == NWS_URL)
    con.execute("UPDATE sources SET method=? WHERE url=? AND method='Belirlenecek'", (method, NWS_URL))
    con.execute("UPDATE sources SET notes=? WHERE url=? AND notes=?", (current, NWS_URL, OLD_NWS_NOTE))


def upgrade_v12(con):
    execute_schema(con, SCHEMA)
    backfill_v11_runs(con)
    seed_v12_configuration(con, DEFAULT_PROFILE)
    seed_restaurant_sites_source(con, DEFAULT_PROFILE)
    repair_nws_default(con)
    if con.execute("PRAGMA foreign_key_check").fetchone():
        raise RuntimeError("v12 migration ilişki bütünlüğü kontrolü başarısız oldu.")
    con.execute("PRAGMA user_version=12")
