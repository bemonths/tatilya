"""Workers (HEDEF-01, the user's decision of 26 November 2026): a rental price run is read by several workers at once, each through its
own way out — the direct connection, or one of the user's proxies (Settings → ABD proxy'si; studio/proxy_list.py). Housing Atlas reads
Redfin the same way, one worker per proxy. Adding workers makes the run shorter; the sites are protected by the limits below.

Generic parts (no company, no site):
- `Exit`: one way out. The direct connection (`dogrudan`) or a proxy of the list (by its order in the list, never by its address). A
  proxy whose exit is in the US (or not known yet) may also read region-blocked sites; `general` is False for the GÖREV-16 single proxy
  in older call paths (it then reads only region-blocked sites).
- `ExitDown`: raised by a worker's transport when its proxy dropped (or was taken out of the list): the worker stops and its task goes to
  another worker.
- `SiteGate`: what every worker of one site shares: at most `limit` workers at once (Settings, default 4); after a 429, a block page or a
  verification page met by any worker the gap of every worker of the site doubles; after a second one the site has one worker. Every
  event is written to the run's log (`events`).
- `Board`: the workers of a running job for the job panel: per worker its way out (`dogrudan`, `proxy 3`, `tarayıcı`, `eklenti`), its
  company, its finished tasks and its errors; never an address.
- `simulate`: the estimate of a run's duration for a number of workers (the same rules as the run: site limit, per-worker gap,
  region-blocked companies only on proxies, browser companies whole in their own lanes).
"""
import heapq
import logging
import threading
import time
from datetime import datetime, timezone

log = logging.getLogger(__name__)

SITE_GAP = 8.0                  # seconds between two requests of one worker to one site
DIRECT = "dogrudan"
LANE_BROWSER = "tarayici"
LANE_EXTENSION = "eklenti"
LANE_LABELS = {LANE_BROWSER: "tarayıcı", LANE_EXTENSION: "eklenti"}


class ExitDown(Exception):
    """The worker's way out is gone (the proxy dropped or left the list)."""


class Exit:
    def __init__(self, key, order=0, proxy=None, country=None, *, general=True, health=None, row_id=None):
        self.key, self.order, self.proxy, self.country = key, order, proxy, country
        self.general = general
        self.row_id = row_id
        self._health = health

    @property
    def direct(self):
        return self.proxy is None

    @property
    def label(self):
        return "doğrudan" if self.direct else f"proxy {self.order}"

    @property
    def region_ok(self):
        """A region-blocked site needs a US exit: a proxy whose country is the US or not known yet."""
        return not self.direct and self.country in (None, "US")

    def healthy(self):
        """After a connection error through a proxy: does the proxy still answer (the public IP service through it)?"""
        if self.direct:
            return True
        if self._health is not None:
            return bool(self._health())
        from . import proxy as P
        try:
            return bool(P.test(self.proxy).get("ok"))
        except Exception:
            return False

    def __repr__(self):
        return f"Exit({self.label})"


def direct_exit():
    return Exit(DIRECT, 0)


def exits_from_settings(data_dir):
    """The direct connection and every usable proxy of the list (studio/proxy_list.py), in the list's order."""
    from . import proxy_list
    out = [direct_exit()]
    for row_id, order, proxy, country in proxy_list.usable(data_dir):
        out.append(Exit(f"proxy:{row_id}", order, proxy, country, row_id=row_id))
    return out


class SiteGate:
    """At most `limit` workers on one site; the shared slow-down after a refusal (see the module text)."""

    def __init__(self, domain, limit, record=None):
        self.domain, self.limit, self.factor = domain, max(1, int(limit)), 1
        self.active = 0
        self.count = 0
        self.record_event = record
        self.on_factor = None
        self.lock = threading.Lock()

    def event(self, kind, worker_label):
        with self.lock:
            self.count += 1
            if self.count == 1:
                self.factor = 2
                text = (f"{self.domain}: {kind} ({worker_label}); bu sitedeki bütün işçiler yavaşladı (istek aralığı iki katına çıktı).")
            elif self.limit > 1:
                self.limit = 1
                text = f"{self.domain}: yine {kind} ({worker_label}); bu site için işçi sayısı bire indi."
            else:
                text = f"{self.domain}: yine {kind} ({worker_label}); site zaten tek işçiyle ve yavaş aralıkla okunuyor."
        log.info(text)
        if self.on_factor is not None:
            self.on_factor(self.factor)
        if self.record_event is not None:
            self.record_event(text)
        return text


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Board:
    """The workers of one job, for the job panel (no address, no password)."""

    def __init__(self):
        self.lock = threading.Lock()
        self.rows = {}
        self.events = []
        self.updated = now_iso()

    def set(self, worker_id, **fields):
        with self.lock:
            row = self.rows.setdefault(worker_id, {"cikis": "", "sirket": None, "biten": 0, "hata": 0, "durum": "boşta"})
            row.update(fields)
            self.updated = now_iso()

    def add(self, worker_id, field, amount=1):
        with self.lock:
            row = self.rows.setdefault(worker_id, {"cikis": "", "sirket": None, "biten": 0, "hata": 0, "durum": "boşta"})
            row[field] = row.get(field, 0) + amount

    def event(self, text):
        with self.lock:
            self.events.append({"zaman": now_iso(), "metin": text})
            del self.events[:-200]

    def snapshot(self):
        with self.lock:
            rows = [{"id": key, **value} for key, value in self.rows.items()]
            order = {"doğrudan": 0, "tarayıcı": 10_000, "eklenti": 10_001}
            rows.sort(key=lambda r: (order.get(r["cikis"], int(r["cikis"].split()[-1]) if r["cikis"].startswith("proxy ") else 9_999), r["id"]))
            working = sum(1 for r in rows if r["durum"] in ("çalışıyor", "boşta") and r["cikis"] not in ("tarayıcı", "eklenti"))
            return {"isciler": rows, "calisan": working, "olaylar": list(self.events[-20:]), "guncellendi": self.updated}


class Boards:
    """The boards of the running jobs (memory only; a finished job's summary is in its run's metadata)."""

    def __init__(self):
        self.lock = threading.Lock()
        self.items = {}

    def open(self, job_id):
        with self.lock:
            self.items[job_id] = Board()
            return self.items[job_id]

    def get(self, job_id):
        with self.lock:
            board = self.items.get(job_id)
        return board.snapshot() if board else None

    def close(self, job_id):
        with self.lock:
            self.items.pop(job_id, None)


BOARDS = Boards()


# ---- the estimate -------------------------------------------------------------------------------------------------------------------

def simulate(companies, exits, site_limit=4, answer_seconds=1.0):
    """The duration of a run in seconds, our estimate. `companies`: dicts with `domain`, `requests`, `gap` (a worker's seconds between
    two requests), `units` (how many tasks the company splits into: its listings), `lane` (None, "tarayici", "eklenti") and `region`
    (region-blocked: only US proxies). `exits`: a list of (general, region_ok) per worker, or an int (one direct + n-1 US proxies).
    Every task is one listing's share of the company's requests; workers take the company with the most work left that is under its
    site limit and that they may read, the same way the run does. Lanes read their companies one after another."""
    if isinstance(exits, int):
        exits = [(True, False)] + [(True, True)] * max(0, exits - 1)
    workers = [{"general": g, "region": r} for g, r in exits]
    lanes = {}
    jobs = []
    for company in companies:
        seconds = company["requests"] * (company["gap"] + answer_seconds)
        if seconds <= 0:
            continue
        if company.get("lane"):
            lanes[company["lane"]] = lanes.get(company["lane"], 0.0) + seconds
            continue
        units = max(1, int(company.get("units") or 1))
        jobs.append({"domain": company["domain"], "left": units, "each": seconds / units, "active": 0, "region": bool(company.get("region")),
                     "limit": max(1, int(site_limit))})
    if not workers:
        return max(lanes.values(), default=0.0) if not jobs else None
    clock, events, free = 0.0, [], list(range(len(workers)))
    end = 0.0
    while True:
        progress = False
        for index in sorted(free):
            worker = workers[index]
            pick = None
            for job in jobs:
                if job["left"] <= 0 or job["active"] >= job["limit"]:
                    continue
                if job["region"] and not worker["region"]:
                    continue
                if not job["region"] and not worker["general"]:
                    continue
                if pick is None or job["left"] * job["each"] / (job["active"] + 1) > pick["left"] * pick["each"] / (pick["active"] + 1):
                    pick = job
            if pick is None:
                continue
            pick["left"] -= 1
            pick["active"] += 1
            free.remove(index)
            heapq.heappush(events, (clock + pick["each"], index, id(pick), pick))
            progress = True
        if not events:
            if any(job["left"] > 0 for job in jobs) and not progress:
                return None          # a company no worker may read (a region-blocked site and no US proxy)
            break
        clock, index, _, job = heapq.heappop(events)
        job["active"] -= 1
        free.append(index)
        end = max(end, clock)
    return max(end, max(lanes.values(), default=0.0))


class ProxyPool:
    """The live pool of a run: the direct connection and the usable proxies of the list, read again on every call."""

    def __init__(self, data_dir):
        self.data_dir = data_dir

    def exits(self):
        return exits_from_settings(self.data_dir)

    def mark_down(self, row_id, note):
        from . import proxy_list
        proxy_list.mark_down(self.data_dir, row_id, note)

    def site_limit(self):
        from . import proxy_list
        return proxy_list.site_limit(self.data_dir)
