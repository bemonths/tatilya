import json
import hashlib
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .destinations import DEFAULT_PROFILE, DEFAULT_DESTINATION_ID, PROFILES
from .destinations.context import ConnectorContext
from .migration_v6 import upgrade_v6
from .sources.windows import monthly_windows
from .migration_v7 import upgrade_v7
from .migration_v8 import upgrade_v8
from .migration_v9 import upgrade_v9
from .migration_v10 import upgrade_v10
from .migration_v11 import upgrade_v11
from .migration_v12 import upgrade_v12
from .migration_v13 import upgrade_v13
from .migration_v14 import upgrade_v14
from .migration_v15 import upgrade_v15
SEEDS = DEFAULT_PROFILE.SEEDS
SCHEMA_VERSION = 15
from .connector_defaults import reconcile_connector_defaults
from .migrations import execute_schema, upgrade_v3, upgrade_v4, upgrade_v5


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
            if version > SCHEMA_VERSION:
                raise RuntimeError("Bu veri dosyası daha yeni bir uygulama sürümüne ait.")
            if version == SCHEMA_VERSION:
                con.execute("BEGIN IMMEDIATE")
                reconcile_connector_defaults(con)
                return
            if version in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14):
                backup_dir = self.path.parent / "backups"
                backup_dir.mkdir(exist_ok=True)
                with sqlite3.connect(backup_dir / f"{self.path.stem}-v{version}-{uuid.uuid4().hex}.sqlite3") as backup:
                    con.backup(backup)
            con.execute("PRAGMA foreign_keys=OFF")
            con.execute("BEGIN IMMEDIATE")
            if version in (3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14):
                if version == 3:
                    upgrade_v4(con)
                if version < 5:
                    upgrade_v5(con)
                if version < 6:
                    upgrade_v6(con)
                if version < 7:
                    upgrade_v7(con)
                if version < 8:
                    upgrade_v8(con)
                if version < 9:
                    upgrade_v9(con)
                if version < 10:
                    upgrade_v10(con)
                if version < 11:
                    upgrade_v11(con)
                if version < 12:
                    upgrade_v12(con)
                if version < 13:
                    upgrade_v13(con)
                if version < 14:
                    upgrade_v14(con)
                upgrade_v15(con)
                reconcile_connector_defaults(con)
                return
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
                for name, url, category, notes, method in SEEDS:
                    stamp, identifier = now(), uuid.uuid4().hex
                    con.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
                        identifier, name, url, category, f"Tüm {DEFAULT_PROFILE.METADATA["name"]}", method, "Haftalık", notes,
                        1, 1, stamp, stamp))
                con.execute("INSERT INTO metadata VALUES ('seeded', ?)", (now(),))
            upgrade_v3(con)
            upgrade_v4(con)
            upgrade_v5(con)
            upgrade_v6(con)
            upgrade_v7(con)
            upgrade_v8(con)
            upgrade_v9(con)
            upgrade_v10(con)
            upgrade_v11(con)
            upgrade_v12(con)
            upgrade_v13(con)
            upgrade_v14(con)
            upgrade_v15(con)
            reconcile_connector_defaults(con)

    def destinations(self):
        with self.connect() as con:
            return [dict(r) for r in con.execute("SELECT * FROM destinations WHERE enabled=1 ORDER BY sort_order,id")]

    def destination(self, identifier=DEFAULT_DESTINATION_ID):
        with self.connect() as con:
            row=con.execute("SELECT * FROM destinations WHERE id=? AND enabled=1",(identifier,)).fetchone()
            if not row: raise KeyError(identifier)
            return dict(row)

    def context(self, identifier=DEFAULT_DESTINATION_ID, inputs=(), today=None):
        """Destination configuration for a connector; `inputs` adds data a connector reads from earlier runs (only for jobs)."""
        destination=self.destination(identifier)
        with self.connect() as con:
            regions=tuple(dict(r) for r in con.execute("SELECT * FROM regions WHERE destination_id=? ORDER BY sort_order,id",(identifier,)))
            anchors=tuple({**dict(r), "source_beach_external_id":r["provenance_external_id"] or "", "source_beach_name":r["provenance_name"] or ""} for r in con.execute("SELECT * FROM destination_weather_anchors WHERE destination_id=? AND enabled=1 ORDER BY sort_order,anchor_key",(identifier,)))
            stations=tuple(dict(r) for r in con.execute("SELECT * FROM destination_climate_stations WHERE destination_id=? AND enabled=1 ORDER BY sort_order,station_key",(identifier,)))
            row=con.execute("SELECT * FROM destination_storm_corridors WHERE destination_id=? AND enabled=1",(identifier,)).fetchone()
            corridor={**dict(row),"radii_nmi":json.loads(row["radii_nmi"])} if row else None
            row=con.execute("SELECT * FROM destination_lodging_sources WHERE destination_id=? AND enabled=1",(identifier,)).fetchone()
            rule=json.loads(row["window_rule"]) if row and row["window_rule"] else None
            # a window rule gives the windows of the day the job runs (GÖREV-10: 12 monthly weeks); otherwise the fixed list
            windows=(monthly_windows(today or datetime.now(timezone.utc).date(), rule) if rule else
                     [dict(r) for r in con.execute("SELECT window_key,label,checkin,checkout FROM destination_lodging_windows WHERE destination_id=? AND enabled=1 ORDER BY sort_order,checkin",(identifier,))])
            lodging={"clone_host":row["clone_host"],
                     "locations":{r["source_location_name"]:r["region_id"] for r in con.execute("SELECT * FROM destination_lodging_locations WHERE destination_id=? ORDER BY source_location_name",(identifier,))},
                     "windows":[{k:w[k] for k in ("window_key","label","checkin","checkout")} for w in windows],"window_rule":rule} if row else None
            sites=[{**dict(r),"aliases":json.loads(r["aliases"]),"inventory":json.loads(r["inventory"]) if r["inventory"] else None}
                   for r in con.execute("""SELECT domain,company,adapter,enabled,aliases,protected,guest_rule,inventory,own_region_id,own_city
                       FROM destination_agency_sites WHERE destination_id=? ORDER BY sort_order,domain""",(identifier,))]
            agency={"sites":sites} if sites else None
            if agency and "lodging_listings" in inputs:
                agency["input"]=self.lodging_input(con,identifier)
            profile=PROFILES.get(identifier)
            restaurants={"site_overrides":getattr(profile,"RESTAURANT_SITE_OVERRIDES",None),"menu_readings":getattr(profile,"MENU_READINGS",None),
                         "item_classes":getattr(profile,"MENU_ITEM_CLASSES",None)}
            if "restaurant_records" in inputs:
                restaurants["input"]=self.restaurant_input(con,identifier)
            browser_hosts=tuple(r[0] for r in con.execute("SELECT host FROM browser_hosts ORDER BY host"))
            area=con.execute("SELECT south,west,north,east,note FROM destination_poi_areas WHERE destination_id=?",(identifier,)).fetchone()
            categories=[{**dict(r),"filters":json.loads(r["filters"]),"brands":json.loads(r["brands"]) if r["brands"] else None,
                         "verified_only":bool(r["verified_only"])} for r in con.execute(
                "SELECT category_key,label,filters,brands,verified_only FROM destination_poi_categories WHERE destination_id=? AND enabled=1 ORDER BY sort_order",(identifier,))]
            reviewed=getattr(profile,"REVIEWED_POINT_FILES",None) or ((getattr(profile,"CHAIN_STORE_CHECKS",None),"zincirin kendi sitesi"),)
            daily_needs={"area":dict(area),"categories":categories,"reviewed_files":[(path,label) for path,label in reviewed if path]} if area and categories else None
        return ConnectorContext(destination,regions,anchors,stations,corridor,lodging,agency,restaurants,browser_hosts,daily_needs)

    @staticmethod
    def restaurant_input(con, destination_id):
        """Restaurants of the destination's latest successful directory run (name, website, phone, address); None without one."""
        run=con.execute("""SELECT id FROM source_runs WHERE destination_id=? AND connector_name='south-walton-restaurants' AND status='done'
            ORDER BY rowid DESC LIMIT 1""",(destination_id,)).fetchone()
        if not run:
            return None
        rows=[dict(r) for r in con.execute("""SELECT external_id,name,website_url,phone,address_line_1,city FROM restaurant_records
            WHERE run_id=? ORDER BY name,external_id""",(run["id"],))]
        return {"run_id":run["id"],"restaurants":rows}

    @staticmethod
    def lodging_input(con, destination_id):
        """Listings of the destination's latest successful Book>Direct run: id, title, company url, bedrooms, bathrooms, capacity,
        street address, coordinates and the regions whose location filters showed it (any window). None when there is no such run."""
        run=con.execute("""SELECT r.id, s.searched_on FROM source_runs r JOIN lodging_snapshots s ON s.run_id=r.id
            WHERE r.destination_id=? AND r.status='done' ORDER BY r.rowid DESC LIMIT 1""",(destination_id,)).fetchone()
        if not run:
            return None
        regions={}
        for row in con.execute("""SELECT DISTINCT r.lodging_id, f.region_id FROM lodging_search_results r JOIN lodging_filters f
                ON f.run_id=r.run_id AND f.window_key=r.window_key AND f.location_id=r.location_id WHERE r.run_id=?""",(run["id"],)):
            regions.setdefault(row["lodging_id"],set()).add(row["region_id"])
        listings=[{**dict(row),"region_ids":sorted(regions.get(row["lodging_id"],()))}
                  for row in con.execute("""SELECT lodging_id,title,url,bedrooms,bathrooms,sleeps,address,latitude,longitude
                      FROM lodging_listings WHERE run_id=? ORDER BY lodging_id""",(run["id"],))]
        return {"run_id":run["id"],"searched_on":run["searched_on"],"listings":listings}

    def sources(self, destination_id=DEFAULT_DESTINATION_ID):
        with self.connect() as con:
            return [dict(row) for row in con.execute("SELECT * FROM sources WHERE destination_id=? ORDER BY created_at, name",(destination_id,))]

    def source(self, identifier):
        with self.connect() as con:
            row = con.execute("SELECT * FROM sources WHERE id=?", (identifier,)).fetchone()
            return dict(row) if row else None

    def save_source(self, data, identifier=None, expected_version=None):
        identifier = identifier or uuid.uuid4().hex
        stamp = now()
        destination_id=data.get("destination_id", DEFAULT_DESTINATION_ID)
        context=self.context(destination_id)
        scope=data.get("scope_region_id")
        if scope is not None and scope not in {r["id"] for r in context.canonical_regions}:
            raise Conflict("Bölge seçili destinasyona ait değil.")
        if scope is None:
            scope=next((r["id"] for r in context.canonical_regions if r["name"]==data["region"]),None)
        fields = (data["name"], data["url"], data["category"], data["region"], data["method"],
                  data["cadence"], data["notes"], int(data["enabled"]))
        try:
            with self.connect() as con:
                if expected_version is None:
                    con.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                (identifier, *fields, 1, stamp, stamp,destination_id,scope))
                else:
                    existing=con.execute("SELECT destination_id FROM sources WHERE id=?",(identifier,)).fetchone()
                    if existing and existing[0] != destination_id:
                        raise Conflict("Kaynağın destinasyonu değiştirilemez.")
                    cursor = con.execute("""UPDATE sources SET name=?, url=?, category=?, region=?, method=?,
                        cadence=?, notes=?, enabled=?, scope_region_id=?, version=version+1, updated_at=? WHERE id=? AND version=?""",
                        (*fields, scope, stamp, identifier, expected_version))
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

    def add_job(self, kind="catalog_audit", title="Kaynak kayıtlarını kontrol et", source_id=None, connector=None, source_version=None, destination_id=DEFAULT_DESTINATION_ID):
        identifier = uuid.uuid4().hex
        try:
            with self.connect() as con:
                con.execute("BEGIN IMMEDIATE")
                self.destination(destination_id)
                if connector:
                    source = con.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()
                    if (not source or not source["enabled"] or
                            (source_version is not None and source["version"] != source_version)):
                        raise Conflict("Kaynak değişti veya arşivlendi. Listeyi yenileyip yeniden deneyin.")
                if source_id:
                    source=con.execute("SELECT * FROM sources WHERE id=?",(source_id,)).fetchone()
                    if not source: raise Conflict("Kaynak bulunamadı.")
                    destination_id=source["destination_id"]
                con.execute("INSERT INTO jobs(id,kind,title,status,created_at,message,source_id,destination_id) VALUES (?,?,?,?,?,?,?,?)",
                            (identifier, kind, title, "queued", now(), "Sırada bekliyor", source_id,destination_id))
                if connector:
                    con.execute("""INSERT INTO source_runs
                        (id,source_id,job_id,status,source_url,connector_name,connector_version,destination_id,metadata)
                        VALUES (?,?,?,'queued',?,?,?,?,?)""", (identifier, source_id, identifier, source["url"],
                        connector.name, connector.version, destination_id, json.dumps({"source_name": source["name"], "source_version": source["version"]})))
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

    def jobs(self, destination_id=DEFAULT_DESTINATION_ID):
        with self.connect() as con:
            return [self.decode_job(row) for row in con.execute("SELECT jobs.*, sources.name AS source_name, job_waits.site AS waiting_for FROM jobs LEFT JOIN sources ON sources.id=jobs.source_id LEFT JOIN job_waits ON job_waits.job_id=jobs.id AND jobs.status IN ('queued','running') WHERE (? IS NULL OR jobs.destination_id=?) ORDER BY jobs.rowid DESC LIMIT 100",(destination_id,destination_id))]

    def job(self, identifier):
        with self.connect() as con:
            row = con.execute("SELECT jobs.*, job_waits.site AS waiting_for FROM jobs LEFT JOIN job_waits ON job_waits.job_id=jobs.id AND jobs.status IN ('queued','running') WHERE id=?", (identifier,)).fetchone()
            return self.decode_job(row) if row else None

    def update_job(self, identifier, *, status=None, progress=None, message=None, result=None, diagnostic=None, waiting_for=None):
        """waiting_for names the site that waits for the user's verification; "" clears it (also after the job ended).
        A wait is shown only while its job is queued or running."""
        with self.connect() as con:
            con.execute("BEGIN IMMEDIATE")
            if waiting_for == "":
                con.execute("DELETE FROM job_waits WHERE job_id=?", (identifier,))
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
            if waiting_for:
                con.execute("INSERT OR REPLACE INTO job_waits (job_id,site,since) VALUES (?,?,?)", (identifier, waiting_for, now()))
            if status is not None:
                con.execute("""UPDATE source_runs SET status=?, started_at=CASE WHEN ?='running' THEN COALESCE(started_at,?) ELSE started_at END,
                    finished_at=?, error_message=? WHERE job_id=?""", (status, status, now(), job["finished_at"],
                    message if status in ("failed", "canceled", "interrupted") else None, identifier))
            return True

    def recover_jobs(self):
        with self.connect() as con:
            con.execute("DELETE FROM job_waits")
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

    def source_runs(self, source_id=None, destination_id=DEFAULT_DESTINATION_ID):
        with self.connect() as con:
            return [self.decode_run(row) for row in con.execute(
                "SELECT * FROM source_runs WHERE (? IS NULL OR source_id=?) AND destination_id=? ORDER BY rowid DESC", (source_id, source_id,destination_id))]

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
            connector = self.registry.by_name(run["connector_name"])
            if connector and not getattr(connector, "diff_enabled", True):
                return {"available": False, "reason": getattr(connector, "diff_reason",
                        "Bu veri türünde kayan tahmin penceresi kullanıldığı için kayıt farkı özeti gösterilmiyor.")}
            previous = con.execute("""SELECT id,connector_version FROM source_runs WHERE source_id=? AND connector_name=?
                AND destination_id=? AND status='done' AND rowid<? ORDER BY rowid DESC LIMIT 1""",
                (run["source_id"], run["connector_name"],run["destination_id"], run["sequence"])).fetchone()
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
                    "previous_connector_version": previous["connector_version"],
                    "connector_version": run["connector_version"],
                    "connector_version_changed": previous["connector_version"] != run["connector_version"],
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
            connector.store_records(con, run["id"], batch.records, batch.related)
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

    def collections(self, destination_id=DEFAULT_DESTINATION_ID):
        """v0.2 plaj ekranı/API için salt okunur uyumluluk görünümü."""
        with self.connect() as con:
            return [dict(row) for row in con.execute("SELECT collections.* FROM collections JOIN source_runs USING(id) WHERE source_runs.destination_id=? ORDER BY source_runs.rowid DESC",(destination_id,))]

    def collection(self, identifier):
        with self.connect() as con:
            row = con.execute("SELECT * FROM collections WHERE id=?", (identifier,)).fetchone()
            if not row:
                return None
        return {"run": dict(row), "records": self.run_records(identifier), "diff": self.run_diff(identifier)}
