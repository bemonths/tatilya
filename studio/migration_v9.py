"""v8 -> v9: storm passages flag the storms that were inside a radius only in non-tropical stages.

The caller owns the backup and the single transaction; any failure rolls everything back. Existing rows keep their
values; rows of earlier hurdat2-storm-proximity/1 runs get 0 (that version did not separate stages).
"""
from .migrations import execute_schema

SCHEMA = """
    ALTER TABLE storm_passages ADD COLUMN non_tropical_only INTEGER NOT NULL DEFAULT 0 CHECK(non_tropical_only IN (0,1));
"""


def upgrade_v9(con):
    execute_schema(con, SCHEMA)
    if con.execute("PRAGMA foreign_key_check").fetchone():
        raise RuntimeError("Kasırga evresi migration ilişki bütünlüğü kontrolü başarısız oldu.")
    con.execute("PRAGMA user_version=9")
