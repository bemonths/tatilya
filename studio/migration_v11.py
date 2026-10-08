"""v10 -> v11: lodging listings keep the rental company's own listing page and phone numbers (bookdirect-lodging/2).

The caller owns the backup and the single transaction; any failure rolls everything back. Existing rows get NULL
(bookdirect-lodging/1 did not store these fields; their raw responses still contain them).
"""
from .migrations import execute_schema

SCHEMA = """
    ALTER TABLE lodging_listings ADD COLUMN url TEXT CHECK(url IS NULL OR url LIKE 'http%');
    ALTER TABLE lodging_listings ADD COLUMN phone TEXT;
    ALTER TABLE lodging_listings ADD COLUMN toll_free TEXT;
"""


def upgrade_v11(con):
    execute_schema(con, SCHEMA)
    if con.execute("PRAGMA foreign_key_check").fetchone():
        raise RuntimeError("Konaklama ilan bağlantısı migration ilişki bütünlüğü kontrolü başarısız oldu.")
    con.execute("PRAGMA user_version=11")
