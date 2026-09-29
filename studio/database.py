import json
import hashlib
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .catalog import SEEDS
from .migrations import execute_schema, upgrade_v3


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class Conflict(Exception):
    pass


class Database:
    def __init__(self, path: Path, registry=None):
        from .sources.registry import DEFAULT_REGISTRY
        self.path = path
        self.registry = registry or DEFAULT_REGISTRY

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
            if version > 3:
                raise RuntimeError("Bu veri dosyası daha yeni bir uygulama sürümüne ait.")
            if version == 3:
                return
            if version in (1, 2):
                backup_dir = self.path.parent / "backups"
                backup_dir.mkdir(exist_ok=True)
                with sqlite3.connect(backup_dir / f"{self.path.stem}-v{version}-{uuid.uuid4().hex}.sqlite3") as backup:
                    con.backup(backup)
            con.execute("BEGIN IMMEDIATE")
            execute_schema(con, """
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
            upgrade_v3(con)

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

    def add_job(self, kind="catalog_audit", title="Kaynak kayıtlarını kontrol et", source_id=None, connector=None, source_version=None):
        identifier = uuid.uuid4().hex
        try:
            with self.connect() as con:
                con.execute("BEGIN IMMEDIATE")
                if connector:
                    source = con.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()
                    if (not source or not source["enabled"] or
                            (source_version is not None and source["version"] != source_version)):
                        raise Conflict("Kaynak değişti veya arşivlendi. Listeyi yenileyip yeniden deneyin.")
                con.execute("INSERT INTO jobs(id,kind,title,status,created_at,message,source_id) VALUES (?,?,?,?,?,?,?)",
                            (identifier, kind, title, "queued", now(), "Sırada bekliyor", source_id))
                if connector:
                    con.execute("""INSERT INTO source_runs
                        (id,source_id,job_id,status,source_url,connector_name,connector_version,metadata)
                        VALUES (?,?,?,'queued',?,?,?,?)""", (identifier, source_id, identifier, source["url"],
                        connector.name, connector.version, json.dumps({"source_name": source["name"], "source_version": source["version"]})))
        except sqlite3.IntegrityError as exc:
            raise Conflict("Aynı türde bir iş zaten sırada veya çalışıyor.") from exc
        return identifier

    @staticmethod
    def decode_job(row):
        result = dict(row)
        result["log"] = json.loads(result["log"])
        result["result"] = json.loads(result["result"]) if result["result"] else None
        result.pop("diagnostic", None)
        return result

    def jobs(self):
        with self.connect() as con:
            return [self.decode_job(row) for row in con.execute("SELECT jobs.*, sources.name AS source_name FROM jobs LEFT JOIN sources ON sources.id=jobs.source_id ORDER BY jobs.rowid DESC LIMIT 100")]

    def job(self, identifier):
        with self.connect() as con:
            row = con.execute("SELECT * FROM jobs WHERE id=?", (identifier,)).fetchone()
            return self.decode_job(row) if row else None

    def update_job(self, identifier, *, status=None, progress=None, message=None, result=None, diagnostic=None):
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
            if diagnostic is not None:
                con.execute("UPDATE jobs SET diagnostic=? WHERE id=?", (json.dumps(diagnostic), identifier))
            if status is not None:
                con.execute("""UPDATE source_runs SET status=?, started_at=CASE WHEN ?='running' THEN COALESCE(started_at,?) ELSE started_at END,
                    finished_at=?, error_message=? WHERE job_id=?""", (status, status, now(), job["finished_at"],
                    message if status in ("failed", "canceled", "interrupted") else None, identifier))
            return True

    def recover_jobs(self):
        with self.connect() as con:
            con.execute("""UPDATE jobs SET status='interrupted', finished_at=?,
                message='Önceki oturumda yarıda kaldı. Kontrolü yeniden başlatabilirsiniz.'
                WHERE status IN ('queued','running')""", (now(),))
            con.execute("""UPDATE source_runs SET status='interrupted',finished_at=?,error_message='Önceki oturumda yarıda kaldı.'
                WHERE status IN ('queued','running')""", (now(),))

    @staticmethod
    def decode_run(row):
        result = dict(row)
        result["metadata"] = json.loads(result["metadata"])
        return result

    def source_runs(self, source_id=None):
        with self.connect() as con:
            return [self.decode_run(row) for row in con.execute(
                "SELECT * FROM source_runs WHERE (? IS NULL OR source_id=?) ORDER BY rowid DESC", (source_id, source_id))]

    def source_run(self, identifier):
        with self.connect() as con:
            row = con.execute("SELECT * FROM source_runs WHERE id=?", (identifier,)).fetchone()
            return self.decode_run(row) if row else None

    def run_records(self, identifier):
        with self.connect() as con:
            run = con.execute("SELECT * FROM source_runs WHERE id=?", (identifier,)).fetchone()
            if not run:
                return None
            connector = self.registry.by_name(run["connector_name"])
            return connector.read_records(con, identifier) if connector and run["status"] == "done" else []

    def run_diff(self, identifier):
        with self.connect() as con:
            run = con.execute("SELECT rowid AS sequence,* FROM source_runs WHERE id=?", (identifier,)).fetchone()
            if not run:
                return None
            if run["status"] != "done":
                return {"available": False, "reason": "Başarılı bir sürüm seçin."}
            previous = con.execute("""SELECT id FROM source_runs WHERE source_id=? AND connector_name=?
                AND status='done' AND rowid<? ORDER BY rowid DESC LIMIT 1""",
                (run["source_id"], run["connector_name"], run["sequence"])).fetchone()
            if not previous:
                return {"available": False, "previous_run_id": None, "reason": "Önceki başarılı sürüm yok."}
            connector = self.registry.by_name(run["connector_name"])
            if not connector:
                return {"available": False, "reason": "Bu sürümün veri toplayıcısı bağlı değil."}
            before = {record["external_id"]: connector.comparison_value(record)
                      for record in connector.read_records(con, previous["id"])}
            after = {record["external_id"]: connector.comparison_value(record)
                     for record in connector.read_records(con, identifier)}
            shared = before.keys() & after.keys()
            changed = sum(before[key] != after[key] for key in shared)
            return {"available": True, "previous_run_id": previous["id"],
                    "added": len(after.keys() - before.keys()), "removed": len(before.keys() - after.keys()),
                    "changed": changed, "unchanged": len(shared) - changed}

    def record_raw_artifact(self, identifier, path):
        if not path.is_file():
            return
        relative = str(path.resolve().relative_to(self.path.parent.resolve()))
        fetched_at = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec="milliseconds")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        with self.connect() as con:
            con.execute("UPDATE source_runs SET raw_path=?,raw_sha256=?,fetched_at=COALESCE(fetched_at,?) WHERE id=?",
                        (relative, digest, fetched_at, identifier))

    def complete_source_run(self, identifier, batch, connector):
        """Domain kayıtları ve başarılı iş/run bitişi tek transaction; iptal kazanır."""
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            job = con.execute("SELECT * FROM jobs WHERE id=?", (identifier,)).fetchone()
            run = con.execute("SELECT * FROM source_runs WHERE job_id=?", (identifier,)).fetchone()
            if not job or not run or job["status"] not in ("queued", "running") or run["status"] not in ("queued", "running"):
                return False
            connector.store_records(con, run["id"], batch.records)
            stamp = now()
            metadata = {**json.loads(run["metadata"]), **batch.metadata, "total_count": batch.total_count}
            con.execute("""UPDATE source_runs SET status='done',finished_at=?,source_updated=?,
                record_count=?,excluded_count=?,metadata=?,error_message=NULL WHERE id=?""",
                (stamp, batch.source_updated, len(batch.records), batch.excluded_count, json.dumps(metadata, ensure_ascii=False), run["id"]))
            result = {"run_id": run["id"], "collection_id": run["id"], "connector_name": connector.name,
                      "included": len(batch.records), "total": batch.total_count, "excluded": batch.excluded_count}
            message = f"{len(batch.records)} kayıt ayrı bir veri sürümü olarak kaydedildi."
            entries = json.loads(job["log"])
            entries.append({"at": stamp, "text": message})
            con.execute("UPDATE jobs SET status='done',progress=100,message=?,finished_at=?,result=?,log=? WHERE id=?",
                        (message, stamp, json.dumps(result), json.dumps(entries, ensure_ascii=False), identifier))
            return True

    def collections(self):
        """v0.2 plaj ekranı/API için salt okunur uyumluluk görünümü."""
        with self.connect() as con:
            return [dict(row) for row in con.execute("SELECT collections.* FROM collections JOIN source_runs USING(id) ORDER BY source_runs.rowid DESC")]

    def collection(self, identifier):
        with self.connect() as con:
            row = con.execute("SELECT * FROM collections WHERE id=?", (identifier,)).fetchone()
            if not row:
                return None
        return {"run": dict(row), "records": self.run_records(identifier), "diff": self.run_diff(identifier)}
