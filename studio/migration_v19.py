"""Schema 18 → 19 (GÖREV-17, Adım 2): jobs the user removed from the job panel.

`job_hidden`: one row per job taken off the panel ("Kaldır", "Bitenleri kaldır"). Removing is hiding only: the job's record, its log and
its result stay in `jobs` untouched; "Geri getir" deletes the row here and the job is back on the panel. Only a finished job (done,
failed, canceled, interrupted) can be hidden. No existing row changes and no job is hidden by the migration.
"""
from .migrations import execute_schema

SCHEMA = """
    CREATE TABLE job_hidden (
        job_id TEXT PRIMARY KEY REFERENCES jobs(id), hidden_at TEXT NOT NULL
    );
"""


def upgrade_v19(con):
    execute_schema(con, SCHEMA)
    if con.execute("PRAGMA foreign_key_check").fetchone():
        raise RuntimeError("v19 migration ilişki bütünlüğü kontrolü başarısız oldu.")
    con.execute("PRAGMA user_version=19")
