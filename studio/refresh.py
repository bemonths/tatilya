"""Suggested refresh (GÖREV-10): which collectors are due by the destination's refresh intervals, and the one-button batch that starts
the due ones in order. Nothing runs by itself: there is no scheduler; the user starts a batch from the home screen.

A collector is due when it never finished a run or its last successful run is at least its interval (in calendar months) old;
a lodging window collector is also due when its last run asked a different window rule than the destination's current one
(fixed windows before the monthly rule, or a changed rule): its snapshot does not belong to the current monthly series.
A batch first takes the app's own database backup (SQLite backup API, data/backups/toplu-*.sqlite3; only the last six of these are
kept, older ones are deleted by the app), then submits the due collectors one at a time through the normal job queue, waiting for
each; a collector whose input collector in the same batch did not finish is skipped. The estimate is the last successful run's
duration (scaled by the number of date windows for window collectors) — our estimate, not a promise.

GÖREV-20: the rental price estimate also counts the companies configured since the last run (their Book>Direct listings × the pages
and price questions a company needs, at the company's own pace; `agency_rates.new_site_estimate`), and a collector that measures
another collector's records (`follows`: road distances follow the lodging listings) is due when that collector is due or has a newer
run than the one it measured.
"""
import json
import sqlite3
import threading
import time
import uuid
from datetime import date, datetime, timezone

from . import proxy_list, workers
from .database import Conflict
from .sources import agency_rates
from .sources.windows import DEFAULT_RULE

BACKUP_PREFIX = "toplu"
KEEP_BACKUPS = 6
POLL_SECONDS = 2.0
WINDOW_CONNECTORS = ("bookdirect-lodging", "agency-lodging-rates")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def add_months(day, months):
    """The same day `months` calendar months later (the month's last day when it is shorter)."""
    index = day.year * 12 + day.month - 1 + months
    year, month = index // 12, index % 12 + 1
    for candidate in (day.day, 30, 29, 28):
        try:
            return date(year, month, min(day.day, candidate))
        except ValueError:
            continue
    raise ValueError(day)


def run_seconds(run):
    try:
        start = datetime.fromisoformat(run["started_at"])
        end = datetime.fromisoformat(run["finished_at"])
    except (TypeError, ValueError):
        return None
    return max(0, int((end - start).total_seconds()))


def rule_of(rule):
    """A window rule with its defaults filled in (None for fixed windows), so two runs' rules compare by meaning."""
    return {**DEFAULT_RULE, **rule} if rule else None


def window_count(metadata):
    windows = (metadata or {}).get("windows") or []
    return sum(1 for w in windows if w.get("status") in ("searched", "queried")) or None


def status(db, destination_id, today=None):
    """Every collector of the destination with its last successful run, suggested interval, next due date and whether it is due."""
    today = today or datetime.now(timezone.utc).date()
    context = db.context(destination_id)
    current_windows = len((context.lodging or {}).get("windows") or []) or None
    current_rule = rule_of((context.lodging or {}).get("window_rule"))
    items = []
    with db.connect() as con:
        intervals = {r["connector_name"]: dict(r) for r in con.execute(
            "SELECT * FROM destination_refresh_intervals WHERE destination_id=? ORDER BY sort_order", (destination_id,))}
        batch = con.execute("SELECT * FROM refresh_batches WHERE destination_id=? ORDER BY created_at DESC, rowid DESC LIMIT 1",
                            (destination_id,)).fetchone()
        for source in con.execute("SELECT * FROM sources WHERE destination_id=? AND enabled=1 ORDER BY created_at, name", (destination_id,)):
            connector = db.registry.for_source(dict(source))
            if connector is None:
                continue
            last = con.execute("""SELECT id, started_at, finished_at, fetched_at, metadata FROM source_runs WHERE source_id=? AND status='done'
                ORDER BY rowid DESC LIMIT 1""", (source["id"],)).fetchone()
            interval = intervals.get(connector.name)
            last_day = date.fromisoformat((last["finished_at"] or last["fetched_at"])[:10]) if last else None
            next_due = add_months(last_day, interval["months"]) if interval and last_day else None
            metadata = json.loads(last["metadata"] or "{}") if last else {}
            reason = None
            if interval and last_day is None:
                reason = "hiç çekilmedi"
            elif interval and today >= next_due:
                reason = "önerilen aralık doldu"
            elif interval and connector.name in WINDOW_CONNECTORS and current_rule and rule_of(metadata.get("window_rule")) != current_rule:
                reason = "pencere kuralı son çekimden sonra değişti"
            seconds, note = None, None
            if last:
                seconds = run_seconds(last)
                old_windows = window_count(metadata)
                if seconds is not None and connector.name in WINDOW_CONNECTORS and old_windows and current_windows and old_windows != current_windows:
                    note = f"son çekimin süresi × pencere oranı ({old_windows} → {current_windows}); bizim tahminimiz"
                    seconds = int(seconds * current_windows / old_windows)
                elif seconds is not None:
                    note = "son başarılı çekimin süresi; bizim tahminimiz"
            added = []
            workers_info = None
            if connector.name == agency_rates.AgencyRatesConnector.name and last and context.agency:
                read = {r[0] for r in con.execute("SELECT domain FROM agency_rate_companies WHERE run_id=?", (last["id"],))}
                listings = (db.lodging_input(con, destination_id) or {}).get("listings") or []
                blocked = [r[0] for r in con.execute("SELECT host FROM region_blocked_hosts")]
                added = [a for a in agency_rates.new_site_estimate(context.agency["sites"], listings, read, current_windows or 0, blocked)
                         if a["requests"]]
                # HEDEF-01: the run is split among workers; the estimate lays the companies' requests out on them (studio.workers.simulate)
                companies = [dict(r) for r in con.execute(
                    "SELECT domain, listing_count, request_count, protected FROM agency_rate_companies WHERE run_id=?", (last["id"],))]
                old_windows = window_count(metadata)
                ratio = current_windows / old_windows if current_windows and old_windows else 1.0
                shaped = agency_rates.worker_companies(context.agency["sites"], companies, added, blocked, ratio)
                exits = workers.exits_from_settings(db.path.parent)
                pairs = [(e.general, e.region_ok) for e in exits]
                limit = proxy_list.site_limit(db.path.parent)
                estimate = agency_rates.worker_estimate(shaped, pairs, limit)
                if estimate is not None:
                    seconds = int(estimate)
                    examples = {n: agency_rates.worker_estimate(shaped, n, limit) for n in (10, 20)}
                    workers_info = {"workers": len(exits), "proxies": len(exits) - 1, "site_limit": limit,
                                    "examples": {str(n): int(v) if v is not None else None for n, v in examples.items()},
                                    "requests": sum(c["requests"] for c in shaped)}
                    note = (f"{len(exits)} işçiyle (doğrudan + {len(exits) - 1} proxy), site başına en çok {limit} işçi, işçi başına site "
                            f"aralığı en az {int(agency_rates.REQUEST_GAP)} sn; son çekimin istek sayıları"
                            f"{f' × pencere oranı ({old_windows} → {current_windows})' if ratio != 1.0 else ''}"
                            f"{f' ve son çekimden sonra eklenen {len(added)} şirketin istekleri' if added else ''}; bizim tahminimiz")
                    if not any(r for _, r in pairs) and any(c["region"] for c in shaped):
                        note += "; ABD proxy'si olmadığı için bölge engelli şirketler atlanır, süreye katılmadı"
            items.append({"connector": connector.name, "source_id": source["id"], "source_name": source["name"],
                          "interval_months": interval["months"] if interval else None, "sort_order": interval["sort_order"] if interval else None,
                          "last_run_id": last["id"] if last else None, "last_done_on": last_day.isoformat() if last_day else None,
                          "next_due_on": next_due.isoformat() if next_due else None,
                          "due": reason is not None, "due_reason": reason,
                          "estimate_seconds": seconds, "estimate_note": note, "added_companies": added, "workers": workers_info,
                          "last_finished_at": (last["finished_at"] or last["fetched_at"]) if last else None,
                          "follows": list(getattr(connector, "follows", ())),
                          "inputs": list(getattr(connector, "inputs", ())), "produces": getattr(connector, "produces", None)})
    by_connector = {i["connector"]: i for i in items}
    for item in items:                           # a collector that measures another's records follows it
        if item["due"] or item["interval_months"] is None or not item["last_run_id"]:
            continue
        for name in item["follows"]:
            other = by_connector.get(name)
            if other and other["due"]:
                item["due"], item["due_reason"] = True, f"girdisi yenilenecek ({other['source_name']})"
            elif other and other["last_finished_at"] and other["last_finished_at"] > item["last_finished_at"]:
                item["due"], item["due_reason"] = True, f"girdisi yenilendi ({other['source_name']})"
    items.sort(key=lambda i: (i["interval_months"] is None, i["sort_order"] if i["sort_order"] is not None else 0, i["source_name"]))
    due = [i for i in items if i["due"]]
    known = [i["estimate_seconds"] for i in due if i["estimate_seconds"] is not None]
    return {"today": today.isoformat(), "items": items, "due_count": len(due),
            "estimate_seconds": sum(known) if known else None,              # unknown stays unknown, never "~1 dk"
            "estimate_complete": all(i["estimate_seconds"] is not None for i in due),
            "batch": decode_batch(batch) if batch else None,
            "note": ("Önerilen yenileme aralıkları destinasyon yapılandırmasındadır; zamanı gelenler kendiliğinden çalışmaz, "
                     "'Zamanı gelenleri başlat' düğmesiyle başlatılır. Aralık tanımlanmayan toplayıcılar gerektiğinde elle çalıştırılır.")}


def decode_batch(row):
    result = dict(row)
    result["plan"] = json.loads(result["plan"])
    return result


def backup(db_path, prefix=BACKUP_PREFIX, keep=KEEP_BACKUPS):
    """The app's own copy of the database (SQLite backup API) in data/backups; only the newest `keep` copies with this prefix stay."""
    folder = db_path.parent / "backups"
    folder.mkdir(exist_ok=True)
    target = folder / f"{prefix}-{datetime.now(timezone.utc):%Y%m%d-%H%M%S-%f}-{uuid.uuid4().hex[:6]}.sqlite3"   # name order = time order
    source = sqlite3.connect(db_path, timeout=30)
    try:
        destination = sqlite3.connect(target)
        try:
            source.backup(destination)
        finally:
            destination.close()
    finally:
        source.close()
    copies = sorted(folder.glob(f"{prefix}-*.sqlite3"), key=lambda p: p.name)
    for old in copies[:-keep] if keep else copies:
        old.unlink()
    return target


class BatchRunner:
    """Starts the due collectors of a destination one after another through the job queue (one batch at a time)."""

    def __init__(self, db, queue, poll=POLL_SECONDS):
        self.db, self.queue, self.poll = db, queue, poll
        self.lock = threading.Lock()
        self.thread = None
        self.closing = False

    def recover(self):
        with self.db.connect() as con:
            con.execute("UPDATE refresh_batches SET status='interrupted', finished_at=?, message='Uygulama kapandığı için yarıda kaldı.' "
                        "WHERE status='running'", (now(),))

    def start(self, destination_id, today=None):
        with self.lock:
            if self.closing:
                raise Conflict("Uygulama kapanıyor.")
            with self.db.connect() as con:
                if con.execute("SELECT 1 FROM refresh_batches WHERE status='running'").fetchone():
                    raise Conflict("Bir toplu çalıştırma zaten sürüyor.")
            if any(job["status"] in ("queued", "running") for job in self.db.jobs(None)):
                raise Conflict("Süren bir iş var; bitmesini bekleyin.")
            current = status(self.db, destination_id, today)
            due = [i for i in current["items"] if i["due"]]
            if not due:
                raise Conflict("Güncelleme zamanı gelen toplayıcı yok.")
            copy = backup(self.db.path)
            plan = [{"connector": i["connector"], "source_id": i["source_id"], "source_name": i["source_name"], "inputs": i["inputs"],
                     "produces": i["produces"], "job_id": None, "status": "waiting", "message": None} for i in due]
            identifier = uuid.uuid4().hex
            with self.db.connect() as con:
                con.execute("""INSERT INTO refresh_batches (id,destination_id,created_at,status,backup_file,plan,estimate_seconds,message)
                    VALUES (?,?,?,'running',?,?,?,?)""", (identifier, destination_id, now(), copy.relative_to(self.db.path.parent).as_posix(),
                                                          json.dumps(plan, ensure_ascii=False), current["estimate_seconds"],
                                                          f"Uygulamanın yedeği alındı: {copy.name}"))
            self.thread = threading.Thread(target=self.run, args=(identifier,), name="30a-refresh", daemon=True)
            self.thread.start()
            return self.batch(identifier)

    def batch(self, identifier):
        with self.db.connect() as con:
            row = con.execute("SELECT * FROM refresh_batches WHERE id=?", (identifier,)).fetchone()
        return decode_batch(row) if row else None

    def save(self, identifier, plan, **fields):
        assignments = ", ".join(f"{k}=?" for k in ("plan", *fields))
        with self.db.connect() as con:
            con.execute(f"UPDATE refresh_batches SET {assignments} WHERE id=?", (json.dumps(plan, ensure_ascii=False), *fields.values(), identifier))

    def run(self, identifier):
        plan = self.batch(identifier)["plan"]
        finished = {}
        try:
            for step in plan:
                current = self.batch(identifier)
                if current["status"] != "running" or self.closing:
                    step["status"], step["message"] = "skipped", "toplu çalıştırma durduruldu"
                    continue
                missing = [needed for needed in step["inputs"]
                           if any(other["produces"] == needed for other in plan) and finished.get(needed) != "done"]
                if missing:
                    step["status"], step["message"] = "skipped", "girdisini üreten toplayıcı bu çalıştırmada tamamlanmadı"
                    self.save(identifier, plan)
                    continue
                try:
                    job = self.queue.submit_collection(step["source_id"])
                except Conflict as exc:
                    step["status"], step["message"] = "failed", str(exc)
                    self.save(identifier, plan)
                    continue
                step["job_id"], step["status"] = job["id"], "running"
                self.save(identifier, plan)
                while True:
                    job = self.db.job(step["job_id"])
                    if job is None or job["status"] not in ("queued", "running"):
                        break
                    if self.batch(identifier)["status"] != "running" or self.closing:
                        self.queue.cancel(step["job_id"])
                    time.sleep(self.poll)
                step["status"] = job["status"] if job else "failed"
                if step["produces"]:
                    finished[step["produces"]] = step["status"]
                self.save(identifier, plan)
        finally:
            current = self.batch(identifier)
            if current and current["status"] == "running":
                final = "done" if all(s["status"] == "done" for s in plan) else "interrupted" if self.closing else "failed"
                done = sum(s["status"] == "done" for s in plan)
                self.save(identifier, plan, status=final, finished_at=now(), message=f"{done}/{len(plan)} toplayıcı tamamlandı.")
            else:
                self.save(identifier, plan, finished_at=now())

    def cancel(self, identifier):
        batch = self.batch(identifier)
        if batch is None:
            return None
        if batch["status"] == "running":
            with self.db.connect() as con:
                con.execute("UPDATE refresh_batches SET status='canceled', message='Kullanıcı durdurdu.' WHERE id=? AND status='running'", (identifier,))
            for step in batch["plan"]:
                if step["status"] == "running" and step["job_id"]:
                    self.queue.cancel(step["job_id"])
        return self.batch(identifier)

    def shutdown(self):
        with self.lock:
            self.closing = True
        with self.db.connect() as con:
            con.execute("UPDATE refresh_batches SET status='interrupted', message='Uygulama kapanırken toplu çalıştırma durdu.' "
                        "WHERE status='running'")
        if self.thread is not None:
            self.thread.join(timeout=10)
