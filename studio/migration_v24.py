"""Schema 23 → 24 (GÖREV-25): RealJoy's configuration and the extension's allowed list of the page's own queries. No table changes.

The destination's agency configuration gets the companies of the profile's `AGENCY_SITES_V24` with their options
(`AGENCY_SITE_OPTIONS_V24`), each only when its domain is not there yet. The options carry the company's allowed queries
(`inventory.extension_queries`: the page's own price question and listing continuation, with the fields the page sends); the
extension's allowed list is read from them (studio.extension_queries). A row already there (somebody added the domain) is left as
it is. A destination without an agency configuration gets nothing. The caller owns the backup and the single transaction.
"""
import json

from .destinations import DEFAULT_PROFILE


def seed_v24_sites(con, profile):
    destination_id = profile.METADATA["id"]
    if not con.execute("SELECT 1 FROM destination_agency_sites WHERE destination_id=?", (destination_id,)).fetchone():
        return
    options = getattr(profile, "AGENCY_SITE_OPTIONS_V24", {})
    order = con.execute("SELECT COALESCE(MAX(sort_order),-1) FROM destination_agency_sites WHERE destination_id=?", (destination_id,)).fetchone()[0]
    for domain, company, adapter in getattr(profile, "AGENCY_SITES_V24", ()):
        if con.execute("SELECT 1 FROM destination_agency_sites WHERE destination_id=? AND domain=?", (destination_id, domain)).fetchone():
            continue
        chosen = options.get(domain, {})
        order += 1
        con.execute("""INSERT INTO destination_agency_sites (destination_id,domain,company,adapter,enabled,sort_order,aliases,protected,guest_rule,
            inventory) VALUES (?,?,?,?,1,?,?,?,?,?)""",
                    (destination_id, domain, company, adapter, order, json.dumps(chosen.get("aliases", [])), int(chosen.get("protected", 0)),
                     chosen.get("guest_rule", "two_adults"), json.dumps(chosen["inventory"], ensure_ascii=False) if chosen.get("inventory") else None))


def upgrade_v24(con):
    seed_v24_sites(con, DEFAULT_PROFILE)
    if con.execute("PRAGMA foreign_key_check").fetchone():
        raise RuntimeError("v24 migration ilişki bütünlüğü kontrolü başarısız oldu.")
    con.execute("PRAGMA user_version=24")
