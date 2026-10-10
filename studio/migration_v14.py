"""v13 -> v14 (GÖREV-11): daily-need categories with a brand list (big supermarkets apart from local and gourmet markets) and a
"verified only" switch (emergency and urgent care confirmed by hospital systems' and urgent-care chains' own pages); points added
from an institution's own site; the category of each reviewed check; and the stored evidence packs.

The caller owns the backup and the single transaction; any failure rolls everything back. Old daily-need runs keep their rows and
their own category list (stored in each snapshot); the two point tables are rebuilt to widen their CHECK lists, and the check rows get
their category in the key (one chain may be checked for two categories: Publix supermarkets and pharmacies). The destination's category
configuration is replaced by the profile's current one (the old "supermarket" and "urgent_care" categories are split).
"""
import json

from .destinations import DEFAULT_PROFILE
from .migrations import execute_schema

SCHEMA = """
    ALTER TABLE destination_poi_categories ADD COLUMN brands TEXT CHECK(brands IS NULL OR json_valid(brands) AND json_type(brands)='array');
    ALTER TABLE destination_poi_categories ADD COLUMN verified_only INTEGER NOT NULL DEFAULT 0 CHECK(verified_only IN (0,1));
    CREATE TABLE poi_points_v14 (
        run_id TEXT NOT NULL REFERENCES poi_snapshots(run_id), point_id TEXT NOT NULL CHECK(length(point_id) > 0),
        category_key TEXT NOT NULL, name TEXT, brand TEXT,
        latitude REAL NOT NULL CHECK(latitude BETWEEN -90 AND 90), longitude REAL NOT NULL CHECK(longitude BETWEEN -180 AND 180),
        source TEXT NOT NULL CHECK(source IN ('openstreetmap','zincirin kendi sitesi','kurumun kendi sitesi')),
        osm_type TEXT CHECK(osm_type IS NULL OR osm_type IN ('node','way','relation')), osm_id INTEGER,
        tags TEXT CHECK(tags IS NULL OR json_valid(tags) AND json_type(tags)='object'), address TEXT, source_url TEXT, checked_on TEXT, note TEXT,
        CHECK((source = 'openstreetmap') = (osm_id IS NOT NULL)),
        PRIMARY KEY(run_id,point_id)
    );
    INSERT INTO poi_points_v14 SELECT * FROM poi_points;
    DROP TABLE poi_points;
    ALTER TABLE poi_points_v14 RENAME TO poi_points;
    CREATE TABLE poi_chain_checks_v14 (
        run_id TEXT NOT NULL REFERENCES poi_snapshots(run_id), chain TEXT NOT NULL, store TEXT NOT NULL, address TEXT,
        latitude REAL CHECK(latitude IS NULL OR latitude BETWEEN -90 AND 90), longitude REAL CHECK(longitude IS NULL OR longitude BETWEEN -180 AND 180),
        store_url TEXT, checked_on TEXT, status TEXT NOT NULL CHECK(status IN ('açık','kapalı','bölgede mağaza yok','okunamadı')),
        osm_point_id TEXT,
        outcome TEXT NOT NULL CHECK(outcome IN ('osm_ile_ayni','eklendi','osmde_var_zincirde_kapali','bolgede_yok','okunamadi','osm_dogrulanamadi')),
        note TEXT, category_key TEXT NOT NULL, PRIMARY KEY(run_id,category_key,chain,store)
    );
    INSERT INTO poi_chain_checks_v14 (run_id,chain,store,address,latitude,longitude,store_url,checked_on,status,osm_point_id,outcome,note,category_key)
        SELECT run_id,chain,store,address,latitude,longitude,store_url,checked_on,status,osm_point_id,outcome,note,'supermarket' FROM poi_chain_checks;
    DROP TABLE poi_chain_checks;
    ALTER TABLE poi_chain_checks_v14 RENAME TO poi_chain_checks;
    CREATE TABLE evidence_packs (
        id TEXT PRIMARY KEY, destination_id TEXT NOT NULL REFERENCES destinations(id), template_key TEXT NOT NULL CHECK(length(template_key) > 0),
        template_version TEXT NOT NULL, title TEXT NOT NULL, params TEXT NOT NULL CHECK(json_valid(params) AND json_type(params)='object'),
        created_at TEXT NOT NULL, markdown_file TEXT NOT NULL, markdown_sha256 TEXT NOT NULL CHECK(length(markdown_sha256) = 64),
        json_file TEXT NOT NULL, json_sha256 TEXT NOT NULL CHECK(length(json_sha256) = 64),
        section_count INTEGER NOT NULL CHECK(section_count >= 0), evidence_count INTEGER NOT NULL CHECK(evidence_count >= 0),
        number_count INTEGER NOT NULL CHECK(number_count >= 0), missing_count INTEGER NOT NULL CHECK(missing_count >= 0)
    );
    CREATE INDEX evidence_packs_destination ON evidence_packs(destination_id, created_at);
"""


def seed_v14_categories(con, profile):
    """The destination's daily-need categories become the profile's current ones (with brands and verified-only)."""
    destination_id = profile.METADATA["id"]
    categories = getattr(profile, "DAILY_NEEDS_CATEGORIES", ())
    if not categories or not con.execute("SELECT 1 FROM destinations WHERE id=?", (destination_id,)).fetchone():
        return
    con.execute("DELETE FROM destination_poi_categories WHERE destination_id=?", (destination_id,))
    for order, (key, label, filters, *rest) in enumerate(categories):
        options = rest[0] if rest else {}
        con.execute("""INSERT INTO destination_poi_categories (destination_id,category_key,label,filters,sort_order,enabled,brands,verified_only)
            VALUES (?,?,?,?,?,1,?,?)""", (destination_id, key, label, json.dumps(filters, ensure_ascii=False), order,
                                          json.dumps(options["brands"], ensure_ascii=False) if options.get("brands") else None,
                                          1 if options.get("verified_only") else 0))


def upgrade_v14(con):
    execute_schema(con, SCHEMA)
    seed_v14_categories(con, DEFAULT_PROFILE)
    if con.execute("PRAGMA foreign_key_check").fetchone():
        raise RuntimeError("v14 migration ilişki bütünlüğü kontrolü başarısız oldu.")
    con.execute("PRAGMA user_version=14")
