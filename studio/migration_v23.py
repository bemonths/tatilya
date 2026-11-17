"""Schema 22 → 23 (GÖREV-23): the rental company configuration of the readers finished in GÖREV-23. No table changes.

The destination's agency configuration gets
- the companies of the profile's `AGENCY_SITES_V23` with their options (`AGENCY_SITE_OPTIONS_V23`), each only when its domain is
  not there yet, and
- for a company that is already there, the new options of `AGENCY_SITE_OPTIONS_V23` — only when the row still holds exactly the
  options the profile gave it before (`AGENCY_SITE_OPTIONS_V22`); a row somebody changed is left as it is.
A destination without an agency configuration gets nothing. The caller owns the backup and the single transaction.
"""
import json

from .destinations import DEFAULT_PROFILE


def seed_v23_sites(con, profile):
    destination_id = profile.METADATA["id"]
    if not con.execute("SELECT 1 FROM destination_agency_sites WHERE destination_id=?", (destination_id,)).fetchone():
        return
    options, before = getattr(profile, "AGENCY_SITE_OPTIONS_V23", {}), getattr(profile, "AGENCY_SITE_OPTIONS_V22", {})
    new = {domain: (company, adapter) for domain, company, adapter in getattr(profile, "AGENCY_SITES_V23", ())}
    order = con.execute("SELECT COALESCE(MAX(sort_order),-1) FROM destination_agency_sites WHERE destination_id=?", (destination_id,)).fetchone()[0]
    for domain in sorted(set(options) | set(new), key=lambda name: (name not in new, list(new).index(name) if name in new else name)):
        chosen = options.get(domain, {})
        inventory = json.dumps(chosen["inventory"], ensure_ascii=False) if chosen.get("inventory") else None
        row = con.execute("SELECT inventory FROM destination_agency_sites WHERE destination_id=? AND domain=?", (destination_id, domain)).fetchone()
        if row is None:
            if domain not in new:
                continue
            order += 1
            company, adapter = new[domain]
            con.execute("""INSERT INTO destination_agency_sites (destination_id,domain,company,adapter,enabled,sort_order,aliases,protected,guest_rule,
                inventory) VALUES (?,?,?,?,1,?,?,?,?,?)""",
                        (destination_id, domain, company, adapter, order, json.dumps(chosen.get("aliases", [])), int(chosen.get("protected", 0)),
                         chosen.get("guest_rule", "two_adults"), inventory))
            continue
        earlier = (before.get(domain) or {}).get("inventory")
        stored = json.loads(row[0]) if row[0] else None
        if inventory is not None and earlier is not None and stored == earlier:
            con.execute("UPDATE destination_agency_sites SET inventory=? WHERE destination_id=? AND domain=?", (inventory, destination_id, domain))


def upgrade_v23(con):
    seed_v23_sites(con, DEFAULT_PROFILE)
    if con.execute("PRAGMA foreign_key_check").fetchone():
        raise RuntimeError("v23 migration ilişki bütünlüğü kontrolü başarısız oldu.")
    con.execute("PRAGMA user_version=23")
