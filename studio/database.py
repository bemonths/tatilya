import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .catalog import SEEDS


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class Conflict(Exception):
    pass


class Database:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as con:
            con.execute("PRAGMA journal_mode=WAL")
            version = con.execute("PRAGMA user_version").fetchone()[0]
            if version > 2:
                raise RuntimeError("Bu veri dosyası daha yeni bir uygulama sürümüne ait.")
            con.executescript("""
                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, url TEXT NOT NULL UNIQUE,
                    category TEXT NOT NULL, region TEXT NOT NULL, method TEXT NOT NULL,
                    cadence TEXT NOT NULL, notes TEXT NOT NULL, enabled INTEGER NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS source_history (
                    id INTEGER PRIMARY KEY, source_id TEXT NOT NULL REFERENCES sources(id),
                    saved_at TEXT NOT NULL, snapshot TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, kind TEXT NOT NULL, title TEXT NOT NULL,
                    status TEXT NOT NULL, progress INTEGER NOT NULL DEFAULT 0,
                    message TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
                    finished_at TEXT, result TEXT, log TEXT NOT NULL DEFAULT '[]'
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_active_job ON jobs(kind)
                    WHERE status IN ('queued', 'running');
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS collections (
                    id TEXT PRIMARY KEY REFERENCES jobs(id), source_id TEXT NOT NULL REFERENCES sources(id),
                    source_url TEXT NOT NULL, fetched_at TEXT NOT NULL, source_updated TEXT,
                    parser_version TEXT NOT NULL, total_count INTEGER NOT NULL,
                    included_count INTEGER NOT NULL, excluded_count INTEGER NOT NULL,
                    raw_path TEXT NOT NULL, raw_sha256 TEXT NOT NULL, scope TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS beach_records (
                    run_id TEXT NOT NULL REFERENCES collections(id), external_id TEXT NOT NULL,
                    name TEXT NOT NULL, city TEXT NOT NULL, address TEXT NOT NULL,
                    latitude REAL NOT NULL, longitude REAL NOT NULL, access_type TEXT NOT NULL,
                    features TEXT NOT NULL, PRIMARY KEY(run_id, external_id)
                );
                PRAGMA user_version=2;
            """)
            if not con.execute("SELECT 1 FROM metadata WHERE key='seeded'").fetchone():
                for name, url, category, notes in SEEDS:
                    stamp, identifier = now(), uuid.uuid4().hex
                    con.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
                        identifier, name, url, category, "Tüm 30A", "Belirlenecek", "Haftalık", notes,
                        1, 1, stamp, stamp))
                con.execute("INSERT INTO metadata VALUES ('seeded', ?)", (now(),))

    def sources(self):
        with self.connect() as con:
            return [dict(row) for row in con.execute("SELECT * FROM sources ORDER BY created_at, name")]

    def source(self, identifier):
        with self.connect() as con:
            row = con.execute("SELECT * FROM sources WHERE id=?", (identifier,)).fetchone()
            return dict(row) if row else None

    def save_source(self, data, identifier=None, expected_version=None):
        identifier = identifier or uuid.uuid4().hex
        stamp = now()
        fields = (data["name"], data["url"], data["category"], data["region"], data["method"],
                  data["cadence"], data["notes"], int(data["enabled"]))
        try:
            with self.connect() as con:
                if expected_version is None:
                    con.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                                (identifier, *fields, 1, stamp, stamp))
                else:
                    cursor = con.execute("""UPDATE sources SET name=?, url=?, category=?, region=?, method=?,
                        cadence=?, notes=?, enabled=?, version=version+1, updated_at=? WHERE id=? AND version=?""",
                        (*fields, stamp, identifier, expected_version))
                    if not cursor.rowcount:
                        if not con.execute("SELECT 1 FROM sources WHERE id=?", (identifier,)).fetchone():
                            raise KeyError(identifier)
                        raise Conflict("Bu kaynak başka bir pencerede değişti. Listeyi yenileyip tekrar deneyin.")
                saved = dict(con.execute("SELECT * FROM sources WHERE id=?", (identifier,)).fetchone())
                con.execute("INSERT INTO source_history(source_id,saved_at,snapshot) VALUES (?,?,?)",
                            (identifier, stamp, json.dumps(saved, ensure_ascii=False)))
                return saved
        except sqlite3.IntegrityError as exc:
            raise Conflict("Bu adres kaynak kütüphanesinde zaten var.") from exc

    def add_job(self, kind="catalog_audit", title="Kaynak kayıtlarını kontrol et"):
        identifier = uuid.uuid4().hex
        try:
            with self.connect() as con:
                con.execute("INSERT INTO jobs(id,kind,title,status,created_at,message) VALUES (?,?,?,?,?,?)",
                            (identifier, kind, title, "queued", now(), "Sırada bekliyor"))
        except sqlite3.IntegrityError as exc:
            raise Conflict("Aynı türde bir iş zaten sırada veya çalışıyor.") from exc
        return identifier

    @staticmethod
    def decode_job(row):
        result = dict(row)
        result["log"] = json.loads(result["log"])
        result["result"] = json.loads(result["result"]) if result["result"] else None
        return result

    def jobs(self):
        with self.connect() as con:
            return [self.decode_job(row) for row in con.execute("SELECT * FROM jobs ORDER BY rowid DESC LIMIT 100")]

    def job(self, identifier):
        with self.connect() as con:
            row = con.execute("SELECT * FROM jobs WHERE id=?", (identifier,)).fetchone()
            return self.decode_job(row) if row else None

    def update_job(self, identifier, *, status=None, progress=None, message=None, result=None):
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute("SELECT * FROM jobs WHERE id=?", (identifier,)).fetchone()
            if not row or row["status"] not in ("queued", "running"):
                return False
            job = dict(row)
            if status is not None:
                job["status"] = status
            if progress is not None:
                job["progress"] = progress
            if message is not None:
                job["message"] = message
                entries = json.loads(job["log"])
                entries.append({"at": now(), "text": message})
                job["log"] = json.dumps(entries, ensure_ascii=False)
            if result is not None:
                job["result"] = json.dumps(result, ensure_ascii=False)
            if job["status"] not in ("queued", "running"):
                job["finished_at"] = now()
            con.execute("""UPDATE jobs SET status=?, progress=?, message=?, result=?, log=?, finished_at=? WHERE id=?""",
                        (job["status"], job["progress"], job["message"], job["result"], job["log"], job["finished_at"], identifier))
            return True

    def recover_jobs(self):
        with self.connect() as con:
            con.execute("""UPDATE jobs SET status='interrupted', finished_at=?,
                message='Önceki oturumda yarıda kaldı. Kontrolü yeniden başlatabilirsiniz.'
                WHERE status IN ('queued','running')""", (now(),))

    def collections(self):
        with self.connect() as con:
            return [dict(row) for row in con.execute("SELECT * FROM collections ORDER BY rowid DESC")]

    def collection(self, identifier):
        with self.connect() as con:
            row = con.execute("SELECT * FROM collections WHERE id=?", (identifier,)).fetchone()
            if not row:
                return None
            records = []
            for entry in con.execute("SELECT * FROM beach_records WHERE run_id=? ORDER BY longitude, name", (identifier,)):
                record = dict(entry)
                record["features"] = json.loads(record["features"])
                records.append(record)
            return {"run": dict(row), "records": records}

    def store_collection(self, identifier, source_id, batch, *, source_url, parser_version, raw_path, scope):
        """İptal kazanır; kayıtlar ve işin başarılı bitişi tek işlemde yayımlanır."""
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            job = con.execute("SELECT * FROM jobs WHERE id=?", (identifier,)).fetchone()
            if not job or job["status"] not in ("queued", "running"):
                return False
            stamp = now()
            con.execute("INSERT INTO collections VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
                identifier, source_id, source_url, stamp, batch.source_updated, parser_version, batch.total_count,
                len(batch.records), batch.excluded_count, raw_path, batch.raw_sha256, scope))
            for record in batch.records:
                con.execute("INSERT INTO beach_records VALUES (?,?,?,?,?,?,?,?,?)", (
                    identifier, record["external_id"], record["name"], record["city"], record["address"],
                    record["latitude"], record["longitude"], record["access_type"],
                    json.dumps(record["features"], ensure_ascii=False)))
            result = {"collection_id": identifier, "included": len(batch.records), "total": batch.total_count,
                      "excluded": batch.excluded_count}
            message = f"{len(batch.records)} plaj erişim kaydı ayrı bir sürüm olarak kaydedildi."
            entries = json.loads(job["log"])
            entries.append({"at": stamp, "text": message})
            con.execute("UPDATE jobs SET status='done',progress=100,message=?,finished_at=?,result=?,log=? WHERE id=?",
                        (message, stamp, json.dumps(result), json.dumps(entries, ensure_ascii=False), identifier))
            return True
