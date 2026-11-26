"""The trial run (HEDEF-01; Sol menü → Veri → Okuma denemeleri → "Deneme çekimini başlat"): every collector once, small, on the real sites
and with the workers, without touching the real data.

Where it runs: on the program's own copy of the database (SQLite backup API, `<data>/deneme/<YYYYMMDD-HHMMSS>/studio.sqlite3`, raw
files beside it). Each collector runs through the normal job flow on that copy (collect → raw files → store_records → the run), so
the storing is tried too; the real database gets only the trial's own job record. The region-blocked list, the browser hosts and the
reading methods a trial finds stay in the copy. The proxy list and the extension are the real ones (Settings; the user's Chrome).

How small (`LIMITS`):
- rental companies (`agency-lodging-rates`): two Book>Direct listings of every company (the ones tied to a company page last time
  first), one week, three pages of a company's sitemap list, two homes of a company's own inventory; through the workers;
- Book>Direct (`bookdirect-lodging`): one week, five price calendars;
- restaurant sites (`restaurant-sites`): three restaurants;
- the others (weather, climate, beaches, neighbourhoods, daily needs, roads, fares, the restaurant directory) are small already and
  run whole.
Collectors that read another's records run before it (rental prices and restaurant sites first, on the copy's real inputs; Book>Direct
last). The result per collector (and per rental company: read or not, through which worker, the error) is written to the job's result
and to `sonuc.json` beside the copy. Of older trials only the last KEEP copies keep their database and raw files; `sonuc.json` stays.
"""
import dataclasses
import json
import shutil
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from .database import Database
from .destinations import DEFAULT_DESTINATION_ID

FOLDER = "deneme"
KEEP = 3
LIMITS = {"listings": 2, "windows": 1, "inventory_pages": 3, "own_homes": 2, "calendars": 5, "restaurants": 3}
FIRST = ("agency-lodging-rates", "restaurant-sites")
LAST = ("bookdirect-lodging",)
POLL_S = 2.0
LABELS = {"done": "okundu", "failed": "hata", "canceled": "iptal edildi", "interrupted": "yarıda kaldı", "skipped": "atlandı"}
COMPANY_LABELS = {"done": "okundu", "stopped_blocked": "site reddetti; durduruldu", "stopped_errors": "hatalar yüzünden durduruldu",
                  "verification_timeout": "doğrulama süresinde geçilmedi; atlandı", "verification_unavailable": "doğrulama/eklenti gerekti; atlandı",
                  "failed": "beklenmeyen hata"}


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class TrialDatabase(Database):
    """The copy, whose contexts carry the trial's limits (`context.trial`, the lodging windows, the restaurants)."""

    limits = LIMITS

    def context(self, identifier=DEFAULT_DESTINATION_ID, inputs=(), today=None):
        context = super().context(identifier, inputs, today)
        lodging = context.lodging
        if lodging:
            lodging = {**lodging, "windows": lodging["windows"][:self.limits["windows"]], "window_rule": None,
                       "calendar_limit": self.limits["calendars"]}
        restaurants = context.restaurants
        if restaurants and restaurants.get("input"):
            rows = [r for r in restaurants["input"]["restaurants"] if r.get("website_url")][:self.limits["restaurants"]]
            restaurants = {**restaurants, "input": {**restaurants["input"], "restaurants": rows}}
        trial = {**self.limits, "preferred": self.preferred()}
        return dataclasses.replace(context, lodging=lodging, restaurants=restaurants, trial=trial)

    def preferred(self):
        """Per company the Book>Direct listings its last real run tied to a company page (asked first in the trial)."""
        with self.connect() as con:
            run = con.execute("""SELECT r.id FROM source_runs r JOIN agency_rate_snapshots s ON s.run_id=r.id WHERE r.status='done'
                ORDER BY r.rowid DESC LIMIT 1""").fetchone()
            if not run:
                return {}
            out = {}
            for domain, lodging_id in con.execute("""SELECT domain, lodging_id FROM agency_rate_listings WHERE run_id=? AND page_status='matched'
                    ORDER BY lodging_id""", (run[0],)):
                out.setdefault(domain, []).append(lodging_id)
            return out


def copy_database(source_path, target_dir):
    """The real database copied with SQLite's backup API (safe while the program runs; the source is only read)."""
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "studio.sqlite3"
    source = sqlite3.connect(Path(source_path).resolve().as_uri() + "?mode=ro", uri=True)
    copy = sqlite3.connect(target)
    try:
        source.backup(copy)
    finally:
        copy.close()
        source.close()
    return target


def prune(root, keep=KEEP):
    """Older trials than the last `keep`: their copy and raw files go (the program's own temporary copies); `sonuc.json` stays."""
    folders = sorted((p for p in root.iterdir() if p.is_dir()), key=lambda p: p.name)
    for folder in folders[:-keep] if keep else folders:
        for name in ("studio.sqlite3", "studio.sqlite3-wal", "studio.sqlite3-shm"):
            (folder / name).unlink(missing_ok=True)
        for sub in ("raw", "backups"):
            shutil.rmtree(folder / sub, ignore_errors=True)


def order_sources(sources, registry):
    def rank(source):
        connector = registry.for_source(source)
        name = connector.name if connector else ""
        if name in FIRST:
            return (0, FIRST.index(name))
        if name in LAST:
            return (2, LAST.index(name))
        return (1, 0)
    return sorted(sources, key=rank)


def company_rows(metadata):
    """Per rental company of a trial run: read or not, through which worker (doğrudan, proxy N, tarayıcı, eklenti), the error."""
    summary = (metadata or {}).get("isciler") or {}
    per = summary.get("sirketler") or {}
    methods = (metadata or {}).get("okuma_yontemleri") or {}
    rows = []
    for company in (metadata or {}).get("companies") or []:
        domain = company["domain"]
        info = per.get(domain) or {}
        ways = list(info.get("cikislar") or [])
        if info.get("sira") and methods.get(domain):
            ways = [{"eklenti": "eklenti", "tarayici": "programın tarayıcısı"}.get(methods[domain], methods[domain])]
        elif info.get("sira") == "tarayici":
            ways = ["programın tarayıcısı"] if ways else []
        rows.append({"alan_adi": domain, "sirket": company["company"], "durum": company["status"],
                     "durum_metni": COMPANY_LABELS.get(company["status"], company["status"]), "ilan": company["listing_count"],
                     "eslenen": company.get("matched_count"), "fiyat": company.get("priced_count"), "istek": company.get("request_count"),
                     "isciler": ways, "mesaj": company.get("message")})
    return rows


class TrialRun:
    """One trial: the copy, a job queue on it, every collector one after another; progress and the result on the real job."""

    def __init__(self, db, job_id, *, extension=None, region_factory=None, destination_id=DEFAULT_DESTINATION_ID, limits=None):
        self.db, self.job_id, self.extension, self.destination_id = db, job_id, extension, destination_id
        self.region_factory = region_factory
        self.limits = {**LIMITS, **(limits or {})}
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.root = db.path.parent / FOLDER
        self.folder = self.root / stamp
        self.rows = []
        self.started = time.monotonic()

    def canceled(self):
        job = self.db.job(self.job_id) or {}
        return job.get("status") not in ("queued", "running")

    def run(self):
        from .jobs import JobQueue
        try:
            self.db.update_job(self.job_id, status="running", progress=1, message="Veritabanının kopyası alınıyor (gerçek veriye dokunulmaz).")
            self.root.mkdir(parents=True, exist_ok=True)
            path = copy_database(self.db.path, self.folder)
            copy = TrialDatabase(path, self.db.registry)
            copy.limits = self.limits
            copy.initialize()
            region = self.region_factory(copy) if self.region_factory else None
            queue = JobQueue(copy, extension=self.extension, region=(lambda: region) if region is not None else None)
            sources = [s for s in copy.sources(self.destination_id) if s["enabled"] and copy.registry.for_source(s)]
            sources = order_sources(sources, copy.registry)
            try:
                for number, source in enumerate(sources, start=1):
                    if self.canceled():
                        break
                    self.db.update_job(self.job_id, progress=int(2 + 96 * (number - 1) / max(1, len(sources))),
                                       message=f"{number}/{len(sources)} · {source['name']} deneniyor.")
                    self.rows.append(self.one(copy, queue, source, number, len(sources)))
                    self.write()
            finally:
                queue.shutdown()
            canceled = self.canceled()
            read = sum(r["durum"] == "done" for r in self.rows)
            result = self.result()
            self.write()
            prune(self.root)
            if canceled:
                self.db.update_job(self.job_id, status="canceled", result=result, message="Deneme çekimi durduruldu; o ana kadarki sonuçlar saklandı.")
            else:
                self.db.update_job(self.job_id, status="done", progress=100, result=result,
                                   message=f"Deneme çekimi bitti: {read}/{len(self.rows)} toplayıcı okundu (sonuç tablosu Veri → Okuma denemeleri'nde).")
        except Exception as exc:
            from .diagnostics import diagnostic
            self.write()
            self.db.update_job(self.job_id, status="failed", message=f"Deneme çekimi tamamlanamadı: {type(exc).__name__}.",
                               diagnostic=diagnostic(exc), result=self.result())

    def one(self, copy, queue, source, number, total):
        connector = copy.registry.for_source(source)
        started = time.monotonic()
        row = {"kaynak": source["name"], "toplayici": connector.name, "durum": None, "durum_metni": None, "kayit": None, "sure_s": None,
               "mesaj": None, "sirketler": None}
        try:
            job = queue.submit_collection(source["id"])
        except Exception as exc:
            row.update({"durum": "skipped", "durum_metni": LABELS["skipped"], "mesaj": str(exc)[:300]})
            return row
        while True:
            time.sleep(POLL_S)
            inner = copy.job(job["id"])
            if inner["status"] not in ("queued", "running"):
                break
            if self.canceled():
                queue.cancel(job["id"])
                continue
            self.db.update_job(self.job_id, progress=int(2 + 96 * (number - 1 + inner["progress"] / 100) / max(1, total)),
                               message=f"{number}/{total} · {source['name']}: {inner['message']}", waiting_for=inner.get("waiting_for") or "")
        run = None
        with copy.connect() as con:
            found = con.execute("SELECT id, record_count, metadata FROM source_runs WHERE job_id=?", (job["id"],)).fetchone()
            if found:
                run = dict(found)
        metadata = json.loads(run["metadata"]) if run and run.get("metadata") else {}
        row.update({"durum": inner["status"], "durum_metni": LABELS.get(inner["status"], inner["status"]),
                    "kayit": run["record_count"] if run else None, "sure_s": int(time.monotonic() - started), "mesaj": inner["message"]})
        if connector.name == "agency-lodging-rates":
            row["sirketler"] = company_rows(metadata)
            row["olaylar"] = ((metadata.get("isciler") or {}).get("olaylar") or [])[-30:]
            row["isciler"] = (metadata.get("isciler") or {}).get("isciler")
        elif metadata.get("okuma_yontemleri"):
            row["okuma_yontemleri"] = metadata["okuma_yontemleri"]
        with copy.connect() as con:
            row["bolge_engelli"] = [r[0] for r in con.execute("SELECT host FROM region_blocked_hosts ORDER BY host")]
        self.db.update_job(self.job_id, waiting_for="")
        return row

    def result(self):
        return {"klasor": str(self.folder.relative_to(self.db.path.parent)).replace("\\", "/"), "baslangic": self.started_at,
                "bitis": now_iso(), "sinirlar": self.limits, "toplayicilar": self.rows}

    @property
    def started_at(self):
        if not hasattr(self, "_started_at"):
            self._started_at = now_iso()
        return self._started_at

    def write(self):
        try:
            self.folder.mkdir(parents=True, exist_ok=True)
            target = self.folder / "sonuc.json"
            temporary = target.with_suffix(".tmp")
            temporary.write_text(json.dumps(self.result(), ensure_ascii=False, indent=1), encoding="utf-8")
            temporary.replace(target)
        except OSError:
            pass


def latest(data_dir):
    """The latest trial's result (`sonuc.json`), or None."""
    root = Path(data_dir) / FOLDER
    if not root.exists():
        return None
    for folder in sorted((p for p in root.iterdir() if p.is_dir()), key=lambda p: p.name, reverse=True):
        target = folder / "sonuc.json"
        if target.exists():
            try:
                return json.loads(target.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
    return None


def start(db, *, extension=None, region_factory=None, destination_id=DEFAULT_DESTINATION_ID, limits=None):
    job_id = db.add_job("deneme_cekimi", "Deneme çekimi · bütün toplayıcılar küçük ölçekte (gerçek veriye karışmaz)", destination_id=destination_id)
    trial = TrialRun(db, job_id, extension=extension, region_factory=region_factory, destination_id=destination_id, limits=limits)
    trial.started_at
    threading.Thread(target=trial.run, name="30a-deneme-cekimi", daemon=True).start()
    return db.job(job_id)
