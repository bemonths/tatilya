"""Schema 25 → 26 (HEDEF-03, 27 November 2026): the extension's allowed list gets the price questions of four more companies, and every
company row of a rental price version keeps its own query day.

Columns: `agency_rate_companies.queried_on` (the day the company's prices were asked) and `carried_from` (the version the row was
carried from unchanged by "Seçili şirketleri yeniden oku"; NULL when the company was read in this version). Existing rows get their
version's query day and no carry.

On 26–27 November 2026 30aescapes.com, oceanreefresorts.com, panhandlegetaways.com (Track) and rosemarybeach.com (Streamline) answered
direct requests and the proxies with Cloudflare's verification page, so they were read through the user's extension; their price
question was not on the allowed list and was not sent. The user's decision of 17 November 2026 (the page's own public queries) covers
them; the manager confirmed it in HEDEF-03. Each company's options get its page's own question (`inventory.extension_queries`) with
exactly the fields its page sends (profile: AGENCY_SITE_QUERIES_V26). A company that already has an allowed list keeps it as it is.
The caller owns the backup and the single transaction.
"""
import json

from .destinations import DEFAULT_PROFILE


def add_v26_queries(con, profile):
    destination_id = profile.METADATA["id"]
    for domain, queries in getattr(profile, "AGENCY_SITE_QUERIES_V26", {}).items():
        row = con.execute("SELECT inventory FROM destination_agency_sites WHERE destination_id=? AND domain=?", (destination_id, domain)).fetchone()
        if row is None:
            continue
        options = json.loads(row[0]) if row[0] else {}
        if not isinstance(options, dict) or options.get("extension_queries"):
            continue
        options["extension_queries"] = queries
        con.execute("UPDATE destination_agency_sites SET inventory=? WHERE destination_id=? AND domain=?",
                    (json.dumps(options, ensure_ascii=False), destination_id, domain))


def add_v26_columns(con):
    columns = {row[1] for row in con.execute("PRAGMA table_info(agency_rate_companies)")}
    if not columns:
        return
    if "queried_on" not in columns:
        con.execute("ALTER TABLE agency_rate_companies ADD COLUMN queried_on TEXT")
        con.execute("""UPDATE agency_rate_companies SET queried_on=(SELECT s.queried_on FROM agency_rate_snapshots s
            WHERE s.run_id=agency_rate_companies.run_id)""")
    if "carried_from" not in columns:
        con.execute("ALTER TABLE agency_rate_companies ADD COLUMN carried_from TEXT")


def upgrade_v26(con):
    add_v26_columns(con)
    add_v26_queries(con, DEFAULT_PROFILE)
    if con.execute("PRAGMA foreign_key_check").fetchone():
        raise RuntimeError("v26 migration ilişki bütünlüğü kontrolü başarısız oldu.")
    con.execute("PRAGMA user_version=26")
