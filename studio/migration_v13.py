"""v12 -> v13 (GÖREV-10): the monthly lodging window rule, suggested refresh intervals and "refresh what is due" batches, daily-need
points from OpenStreetMap (with the chain-store cross-check) and the new restaurant menu classes and methods.

The caller owns the backup and the single transaction; any failure rolls everything back. Old runs keep every row: their windows,
quotes and menus stay as they were stored. Restaurant menu tables are rebuilt only to widen their CHECK lists (new section classes
kucuk_tabak / sabit_menu, menu type catering, methods 'elle okundu' and 'gözden geçirme', the review_note fact); rows are copied
unchanged. Configuration comes from the destination profile once; a fixed window list a destination keeps is disabled only when the
destination gets a window rule.
"""
import json
import uuid
from datetime import datetime, timezone

from .destinations import DEFAULT_PROFILE
from .migrations import execute_schema

METHODS = "'yapısal veri','sayfa metni','PDF metni','platform verisi','görüntüden okundu','elle okundu','bağlantı','gözden geçirme'"
SCHEMA = f"""
    ALTER TABLE destination_lodging_sources ADD COLUMN window_rule TEXT
        CHECK(window_rule IS NULL OR json_valid(window_rule) AND json_type(window_rule)='object');
    CREATE TABLE destination_refresh_intervals (
        destination_id TEXT NOT NULL REFERENCES destinations(id), connector_name TEXT NOT NULL CHECK(length(connector_name) > 0),
        months INTEGER NOT NULL CHECK(months BETWEEN 1 AND 24), sort_order INTEGER NOT NULL,
        PRIMARY KEY(destination_id,connector_name)
    );
    CREATE TABLE refresh_batches (
        id TEXT PRIMARY KEY, destination_id TEXT NOT NULL REFERENCES destinations(id), created_at TEXT NOT NULL, finished_at TEXT,
        status TEXT NOT NULL CHECK(status IN ('running','done','failed','canceled','interrupted')), backup_file TEXT,
        plan TEXT NOT NULL CHECK(json_valid(plan) AND json_type(plan)='array'), estimate_seconds INTEGER CHECK(estimate_seconds IS NULL OR estimate_seconds >= 0),
        message TEXT
    );
    CREATE TABLE destination_poi_areas (
        destination_id TEXT PRIMARY KEY REFERENCES destinations(id),
        south REAL NOT NULL, west REAL NOT NULL, north REAL NOT NULL, east REAL NOT NULL, note TEXT NOT NULL,
        CHECK(south < north AND west < east AND south BETWEEN -90 AND 90 AND north BETWEEN -90 AND 90 AND west BETWEEN -180 AND 180 AND east BETWEEN -180 AND 180)
    );
    CREATE TABLE destination_poi_categories (
        destination_id TEXT NOT NULL REFERENCES destinations(id), category_key TEXT NOT NULL CHECK(length(category_key) > 0),
        label TEXT NOT NULL, filters TEXT NOT NULL CHECK(json_valid(filters) AND json_type(filters)='array'),
        sort_order INTEGER NOT NULL, enabled INTEGER NOT NULL DEFAULT 1 CHECK(enabled IN (0,1)),
        PRIMARY KEY(destination_id,category_key)
    );
    CREATE TABLE poi_snapshots (
        run_id TEXT PRIMARY KEY REFERENCES source_runs(id), area TEXT NOT NULL CHECK(json_valid(area)),
        categories TEXT NOT NULL CHECK(json_valid(categories)), queried_on TEXT NOT NULL CHECK(date(queried_on) IS queried_on),
        osm_timestamp TEXT, request_count INTEGER NOT NULL CHECK(request_count >= 0), element_count INTEGER NOT NULL CHECK(element_count >= 0),
        chain_check_count INTEGER NOT NULL DEFAULT 0 CHECK(chain_check_count >= 0)
    );
    CREATE TABLE poi_points (
        run_id TEXT NOT NULL REFERENCES poi_snapshots(run_id), point_id TEXT NOT NULL CHECK(length(point_id) > 0),
        category_key TEXT NOT NULL, name TEXT, brand TEXT,
        latitude REAL NOT NULL CHECK(latitude BETWEEN -90 AND 90), longitude REAL NOT NULL CHECK(longitude BETWEEN -180 AND 180),
        source TEXT NOT NULL CHECK(source IN ('openstreetmap','zincirin kendi sitesi')),
        osm_type TEXT CHECK(osm_type IS NULL OR osm_type IN ('node','way','relation')), osm_id INTEGER,
        tags TEXT CHECK(tags IS NULL OR json_valid(tags) AND json_type(tags)='object'), address TEXT, source_url TEXT, checked_on TEXT, note TEXT,
        CHECK((source = 'openstreetmap') = (osm_id IS NOT NULL)),
        PRIMARY KEY(run_id,point_id)
    );
    CREATE TABLE poi_chain_checks (
        run_id TEXT NOT NULL REFERENCES poi_snapshots(run_id), chain TEXT NOT NULL, store TEXT NOT NULL, address TEXT,
        latitude REAL CHECK(latitude IS NULL OR latitude BETWEEN -90 AND 90), longitude REAL CHECK(longitude IS NULL OR longitude BETWEEN -180 AND 180),
        store_url TEXT, checked_on TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('açık','kapalı','bölgede mağaza yok','okunamadı')),
        osm_point_id TEXT, outcome TEXT NOT NULL CHECK(outcome IN ('osm_ile_ayni','eklendi','osmde_var_zincirde_kapali','bolgede_yok','okunamadi')),
        note TEXT, PRIMARY KEY(run_id,chain,store)
    );
    CREATE TABLE restaurant_facts_v13 (
        run_id TEXT NOT NULL, external_id TEXT NOT NULL,
        field TEXT NOT NULL CHECK(field IN ('hours','reservation','kids_menu','outdoor_seating','water_view','dog_friendly','site_price_range','review_note')),
        value TEXT NOT NULL CHECK(length(value) > 0), detail TEXT, link_url TEXT, data TEXT CHECK(data IS NULL OR json_valid(data)),
        source_url TEXT NOT NULL, fetched_at TEXT, raw_sha256 TEXT,
        method TEXT NOT NULL CHECK(method IN ({METHODS})),
        CHECK(field <> 'reservation' OR value IN ('online','phone','not_taken','waitlist')),
        CHECK(field NOT IN ('kids_menu','outdoor_seating','water_view','dog_friendly') OR value IN ('yes','no')),
        CHECK(field <> 'review_note' OR value IN ('no_mains','note')),
        CHECK(field = 'review_note' OR fetched_at IS NOT NULL AND raw_sha256 IS NOT NULL),
        PRIMARY KEY(run_id,external_id,field),
        FOREIGN KEY(run_id,external_id) REFERENCES restaurant_sites(run_id,external_id)
    );
    INSERT INTO restaurant_facts_v13 SELECT * FROM restaurant_facts;
    DROP TABLE restaurant_facts;
    ALTER TABLE restaurant_facts_v13 RENAME TO restaurant_facts;
    CREATE TABLE restaurant_menus_v13 (
        run_id TEXT NOT NULL, external_id TEXT NOT NULL, menu_id INTEGER NOT NULL CHECK(menu_id > 0),
        url TEXT NOT NULL CHECK(url LIKE 'http%'), format TEXT NOT NULL CHECK(format IN ('html','pdf','image','platform')),
        menu_type TEXT NOT NULL CHECK(menu_type IN ('dinner','lunch','general','brunch','breakfast','kids','drinks','dessert','happy_hour','catering','special')),
        title TEXT, platform TEXT, linked_from TEXT, fetched_at TEXT, raw_sha256 TEXT,
        method TEXT CHECK(method IS NULL OR method IN ({METHODS})),
        status TEXT NOT NULL CHECK(status IN ('read','no_items','image_unread','error')), message TEXT,
        item_count INTEGER NOT NULL DEFAULT 0 CHECK(item_count >= 0),
        CHECK((status = 'read') = (item_count > 0)),
        PRIMARY KEY(run_id,external_id,menu_id),
        FOREIGN KEY(run_id,external_id) REFERENCES restaurant_sites(run_id,external_id)
    );
    INSERT INTO restaurant_menus_v13 SELECT * FROM restaurant_menus;
    CREATE TABLE restaurant_menu_items_v13 (
        run_id TEXT NOT NULL, external_id TEXT NOT NULL, menu_id INTEGER NOT NULL, position INTEGER NOT NULL CHECK(position > 0),
        section TEXT, section_class TEXT NOT NULL CHECK(section_class IN ('ana_yemek','baslangic','salata_corba','kucuk_tabak','sabit_menu','tatli',
                                                                           'icecek','cocuk','yan_urun','diger')),
        class_basis TEXT NOT NULL CHECK(class_basis IN ('section','name','menu','review')),
        name TEXT NOT NULL CHECK(length(name) > 0), price_text TEXT, price REAL CHECK(price IS NULL OR price >= 0),
        price_rule TEXT NOT NULL CHECK(price_rule IN ('single','lowest','market')),
        method TEXT NOT NULL CHECK(method IN ({METHODS})),
        CHECK((price_rule = 'market') = (price IS NULL)),
        PRIMARY KEY(run_id,external_id,menu_id,position),
        FOREIGN KEY(run_id,external_id,menu_id) REFERENCES restaurant_menus(run_id,external_id,menu_id)
    );
    INSERT INTO restaurant_menu_items_v13 SELECT * FROM restaurant_menu_items;
    DROP TABLE restaurant_menu_items;
    DROP TABLE restaurant_menus;
    ALTER TABLE restaurant_menus_v13 RENAME TO restaurant_menus;
    ALTER TABLE restaurant_menu_items_v13 RENAME TO restaurant_menu_items;
    CREATE INDEX restaurant_menu_items_menu ON restaurant_menu_items(run_id,external_id,menu_id);
"""


def seed_v13_configuration(con, profile):
    """The window rule (the destination's fixed windows are kept for history but disabled), refresh intervals, the daily-need area and
    categories and the OpenStreetMap source of the destination; each added once."""
    destination_id = profile.METADATA["id"]
    if not con.execute("SELECT 1 FROM destinations WHERE id=?", (destination_id,)).fetchone():
        return
    rule = getattr(profile, "LODGING_WINDOW_RULE", None)
    if rule and con.execute("SELECT 1 FROM destination_lodging_sources WHERE destination_id=? AND window_rule IS NULL", (destination_id,)).fetchone():
        con.execute("UPDATE destination_lodging_sources SET window_rule=? WHERE destination_id=?", (json.dumps(rule), destination_id))
        con.execute("UPDATE destination_lodging_windows SET enabled=0 WHERE destination_id=?", (destination_id,))
    for order, (connector, months) in enumerate(getattr(profile, "REFRESH_INTERVALS", ())):
        con.execute("INSERT OR IGNORE INTO destination_refresh_intervals (destination_id,connector_name,months,sort_order) VALUES (?,?,?,?)",
                    (destination_id, connector, months, order))
    area = getattr(profile, "DAILY_NEEDS_AREA", None)
    if area:
        con.execute("INSERT OR IGNORE INTO destination_poi_areas (destination_id,south,west,north,east,note) VALUES (?,?,?,?,?,?)",
                    (destination_id, area["south"], area["west"], area["north"], area["east"], area["note"]))
    for order, (key, label, filters, *_) in enumerate(getattr(profile, "DAILY_NEEDS_CATEGORIES", ())):
        con.execute("INSERT OR IGNORE INTO destination_poi_categories (destination_id,category_key,label,filters,sort_order,enabled) VALUES (?,?,?,?,?,1)",
                    (destination_id, key, label, json.dumps(filters, ensure_ascii=False), order))
    seed_source(con, profile, "https://www.openstreetmap.org/?kaynak=gunluk-ihtiyac")


def seed_source(con, profile, url):
    destination_id = profile.METADATA["id"]
    if con.execute("SELECT 1 FROM sources WHERE destination_id=? AND url=?", (destination_id, url)).fetchone():
        return
    seed = next((seed for seed in profile.SEEDS if seed[1] == url), None)
    if seed is None:
        return
    name, url, category, notes, method = seed
    stamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    con.execute("""INSERT INTO sources (id,name,url,category,region,method,cadence,notes,enabled,version,
        created_at,updated_at,destination_id,scope_region_id) VALUES (?,?,?,?,?,?,?,?,1,1,?,?,?,NULL)""",
        (uuid.uuid4().hex, name, url, category, f"Tüm {profile.METADATA['name']}", method, "Gerektiğinde", notes, stamp, stamp, destination_id))


def upgrade_v13(con):
    execute_schema(con, SCHEMA)
    seed_v13_configuration(con, DEFAULT_PROFILE)
    if con.execute("PRAGMA foreign_key_check").fetchone():
        raise RuntimeError("v13 migration ilişki bütünlüğü kontrolü başarısız oldu.")
    con.execute("PRAGMA user_version=13")
