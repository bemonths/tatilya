"""Schema 24 → 25 (HEDEF-01, the user's decision of 26 November 2026): RealJoy's pace from 20 s to 12 s between two requests. No table
changes.

The workers' rule (studio/workers.py): a 429 from the site doubles the gap of every worker of that site (12 → 24 s, i.e. back to 20 s
and above). Only a configuration still at the GÖREV-25 value (20) is changed; a value somebody set otherwise is left as it is. The
caller owns the backup and the single transaction.
"""
import json

REALJOY = "realjoy.com"
OLD_GAP, NEW_GAP = 20, 12


def upgrade_v25(con):
    for destination_id, inventory in con.execute("SELECT destination_id, inventory FROM destination_agency_sites WHERE domain=?", (REALJOY,)).fetchall():
        options = json.loads(inventory) if inventory else None
        if isinstance(options, dict) and options.get("gap_s") == OLD_GAP:
            options["gap_s"] = NEW_GAP
            con.execute("UPDATE destination_agency_sites SET inventory=? WHERE destination_id=? AND domain=?",
                        (json.dumps(options, ensure_ascii=False), destination_id, REALJOY))
    if con.execute("PRAGMA foreign_key_check").fetchone():
        raise RuntimeError("v25 migration ilişki bütünlüğü kontrolü başarısız oldu.")
    con.execute("PRAGMA user_version=25")
