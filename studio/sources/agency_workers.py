"""The rental price run split among workers (HEDEF-01; studio/workers.py).

A company's work is cut into tasks:
1. one task per Book>Direct listing tied to the company ("link": its page and its price for every window);
2. when the company's own list is configured and needed, one task reads it ("inventory");
3. one task per listing the link did not reach and the list may tie ("fallback");
4. one task per home of the company's own inventory ("own");
5. one task reads the published rents ("published").
Every stage starts when the one before it is finished. Workers take tasks of any company: the company with the most work left per
worker that is under its site limit (`SiteGate`: at most `site_limit` workers on one site; Settings, default 4) and that the worker may
read. A worker keeps its own pace on each site (at least 8 s between two of its requests; the company's own pace when it is slower, e.g.
RealJoy 12 s), so a site sees at most `site_limit` requests per 8 s. A 429, a block page or a verification page met by any worker slows
every worker of that site (twice the gap); a second one leaves the site one worker. These events go to the run's log and metadata.

- Region-blocked companies (360 Blue, Vacasa, …) go to proxy workers only (a US exit; only the listed domains go through the proxy).
- Browser companies are never split. Protected companies (oversee.us, exclusive30a.com) are read whole in the "tarayıcı" lane through the
  program's own browser; a company read only through the extension (RealJoy) whole in the "eklenti" lane; both lanes run side by side
  with the workers. A company that shows a verification page to a worker moves, with its tasks left, to the extension lane when the
  extension is paired, else to the browser lane; the old reading order holds there (extension → the program's browser → skip).
- A worker whose proxy drops (a connection error and the proxy no longer answers), or whose proxy leaves the list, stops; its task goes
  back to the front of the queue for another worker. A worker that has not answered for STALL_S is given up the same way. The pool is
  live: every POOL_REFRESH_S the list is read again; a new working proxy becomes a new worker.
- A task's results are kept apart until it ends, so a task given to another worker is never counted twice.
"""
import copy
import logging
import threading
import time
from collections import deque

import httpx

from .. import workers as W
from .base import CollectionCanceled

log = logging.getLogger(__name__)

POOL_REFRESH_S = 60.0
STALL_S = 75 * 60          # longer than the longest 429 Retry-After wait (agency_rates.RETRY_AFTER_MAX, 1 h), so a waiting worker is not given up
IDLE_WAIT_S = 0.5
CONNECT_TIMEOUT = httpx.Timeout(45, connect=15)


class CompanyHalted(Exception):
    """The company was stopped (or failed) while this worker's task was running: the task ends without committing anything."""


class NeedsBrowser(Exception):
    def __init__(self, url):
        super().__init__(url)
        self.url = url


class Task:
    def __init__(self, state, kind, item=None):
        self.state, self.kind, self.item = state, kind, item
        self.owner = None
        self.abandoned = False


class CompanyState:
    def __init__(self, run, gate):
        self.run, self.gate = run, gate
        self.domain = run.site["domain"]
        self.pending = deque()
        self.inflight = set()
        self.stage = "links"
        self.lane = None
        self.lane_started = False
        self.finished = False
        self.units = None
        self.plan = None
        self.exits = set()
        self.halted = False
        self.requests = 0
        self.sessions = []

    @property
    def region(self):
        return self.run.region is not None


def lane_of(run):
    """The lane of a company that is never split: extension only → "eklenti"; protected (or once showed a verification page) →
    "tarayici"; else None."""
    if run.extension_only:
        return W.LANE_EXTENSION
    if run.protected:
        return W.LANE_BROWSER
    return None


class WorkerSessionMixin:
    """A worker's session on one site: the gap follows the site's gate (twice after a refusal); once the company is stopped or failed
    (`state.halted`) its next request ends the task without committing it."""

    def request(self, *args, **kwargs):
        if getattr(self.state, "halted", False):
            raise CompanyHalted()
        return super().request(*args, **kwargs)

    @property
    def gap(self):
        return self._gap * self.gate.factor

    @gap.setter
    def gap(self, value):
        self._gap = value


class WorkerTransport:
    """The worker's transport: a proxy that left the list or dropped raises ExitDown (the task goes to another worker)."""

    def __init__(self, inner, worker):
        self.inner, self.worker = inner, worker

    @property
    def kind(self):
        return self.inner.kind

    def send(self, method, url, **kwargs):
        if self.worker.removed:
            raise W.ExitDown("çıkarıldı")
        try:
            return self.inner.send(method, url, **kwargs)
        except httpx.ProxyError as exc:
            self.worker.down("proxy bağlantıyı kurmadı")
            raise W.ExitDown(str(exc)) from None
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
            if not self.worker.exit.direct and not self.worker.exit.healthy():
                self.worker.down("proxy yanıt vermiyor")
                raise W.ExitDown(str(exc)) from None
            raise

    def close(self):
        pass


class Worker:
    def __init__(self, scheduler, exit_, number, lane=None):
        self.scheduler, self.exit, self.number, self.lane = scheduler, exit_, number, lane
        self.id = f"{lane or exit_.key}#{number}"
        self.removed = False
        self.dropped = None
        self.task = None
        self.seen = time.monotonic()
        self.sessions = {}
        self.clients = {}
        self.thread = None
        self.lane_state = None
        self.counts = {}          # per site: this worker's consecutive refusals and errors (BLOCK_LIMIT, ERROR_LIMIT)

    @property
    def label(self):
        return W.LANE_LABELS[self.lane] if self.lane else self.exit.label

    def down(self, reason):
        if self.dropped is None:
            self.dropped = reason
            self.removed = True
            self.scheduler.exit_down(self, reason)

    def client_for(self, hosts):
        key = tuple(hosts) if hosts else None
        if key not in self.clients:
            self.clients[key] = self.scheduler.exit_client(self.exit, list(hosts) if hosts else None)
        return self.clients[key]

    def session_for(self, state):
        from . import agency_rates as ar
        if state.domain in self.sessions:
            return self.sessions[state.domain]
        run, shared = state.run, self.scheduler.shared
        if self.exit.direct:
            inner = ar.HttpTransport(shared.client)
        elif state.region:
            from ..proxy import is_listed
            hosts = sorted(run.region.hosts)
            inner = ar.HttpTransport(self.client_for(hosts), kind="proxy", proxied=lambda url: is_listed(hosts, url))
        else:
            inner = ar.HttpTransport(self.client_for(None), kind="proxy")
        session = worker_session_class().__new__(worker_session_class())
        session.gate, session.state = state.gate, state
        ar.SiteSession.__init__(session, shared.store, state.domain, WorkerTransport(inner, self), shared.canceled,
                                allowed=run.session.allowed[1:], gap=run.session._base_gap, protected=False,
                                retry_429=run.session.retry_429)
        session.on_event = lambda kind: state.gate.event(kind, self.label)
        session.on_request = self.touch
        self.sessions[state.domain] = session
        state.sessions.append(session)
        return session

    def touch(self):
        self.seen = time.monotonic()

    def close(self):
        for client in self.clients.values():
            try:
                client.close()
            except Exception:
                pass


class Scheduler:
    def __init__(self, shared, runs, *, exits, site_limit, exit_client, board=None, pool=None, extension_paired=False):
        self.shared = shared
        self.cond = threading.Condition()
        self.events = []
        self.board = board
        self.pool = pool
        self.exit_client = exit_client
        self.extension_paired = extension_paired
        self.states = []
        self.workers = []
        self.numbers = {}
        self.error = None
        self.stop_pool = threading.Event()
        for run in runs:
            run.session._base_gap = run.session.gap
            gate = W.SiteGate(run.site["domain"], site_limit, record=self.record)
            state = CompanyState(run, gate)
            state.lane = lane_of(run)
            run.session.on_event = (lambda kind, s=state: s.gate.event(kind, W.LANE_LABELS.get(s.lane, "tarayıcı")))
            gate.on_factor = (lambda factor, s=run.session: setattr(s, "gap", s._base_gap * factor))
            self.states.append(state)
        self.initial_exits = list(exits)
        self.region_available = any(e.region_ok for e in self.initial_exits)    # the pool's latest view: a US proxy exists

    # --- log ---------------------------------------------------------------------------------------------------------------

    def record(self, text):
        with self.cond:
            self.events.append({"zaman": W.now_iso(), "metin": text})
        if self.board is not None:
            self.board.event(text)
        self.shared.tracker.step(0, text)

    def board_set(self, worker, **fields):
        if self.board is not None:
            self.board.set(worker.id, cikis=worker.label, **fields)

    # --- workers -----------------------------------------------------------------------------------------------------------

    def add_worker(self, exit_, lane=None, start=True):
        with self.cond:
            number = self.numbers.get(lane or exit_.key, 0) + 1
            self.numbers[lane or exit_.key] = number
            worker = Worker(self, exit_, number, lane)
            self.workers.append(worker)
        self.board_set(worker, durum="boşta", sirket=None)
        worker.thread = threading.Thread(target=self.work, args=(worker,), name=f"30a-isci-{worker.label}", daemon=True)
        if start:
            worker.thread.start()
        return worker

    def exit_down(self, worker, reason):
        self.record(f"{worker.label}: {reason}; işçi durdu, elindeki iş başka işçiye geçiyor.")
        if self.pool is not None and getattr(worker.exit, "row_id", None):
            try:
                self.pool.mark_down(worker.exit.row_id, f"Çekim sırasında düştü: {reason}.")
            except Exception:
                log.exception("Proxy düştü olarak işaretlenemedi.")

    def refresh_pool(self):
        """The live pool: new usable proxies become workers; a proxy that left the list (or is marked not working) stops its worker."""
        if self.pool is None:
            return
        try:
            exits = self.pool.exits()
        except Exception:
            log.exception("Proxy listesi okunamadı.")
            return
        keys = {e.key for e in exits}
        gone, joined = [], []
        with self.cond:
            self.region_available = any(e.region_ok for e in exits)
            alive = {w.exit.key for w in self.workers if not w.removed and not w.lane}
            for worker in self.workers:
                if not worker.lane and not worker.removed and worker.exit.key not in keys:
                    worker.removed = True
                    gone.append(worker)
            for exit_ in exits:
                if exit_.key not in alive:
                    self.add_worker(exit_)
                    joined.append(exit_)
        for worker in gone:
            self.record(f"{worker.label}: proxy listeden çıkarıldı; işçi durdu, elindeki iş başka işçiye geçiyor.")
        for exit_ in joined:
            self.record(f"{exit_.label}: yeni işçi çekime katıldı.")

    def watch(self):
        """Pool refresh and the stall check, until the run ends."""
        last_refresh = time.monotonic()
        while not self.stop_pool.wait(min(1.0, POOL_REFRESH_S)):
            now = time.monotonic()
            if now - last_refresh >= POOL_REFRESH_S:
                last_refresh = now
                self.refresh_pool()
            with self.cond:
                stalled = [(w, w.task) for w in self.workers if w.task is not None and not w.removed and not w.lane and now - w.seen > STALL_S]
                for worker, task in stalled:
                    worker.removed = True
                    self.requeue(task)
                    self.add_worker(worker.exit)
            for worker, _ in stalled:
                self.record(f"{worker.label}: {STALL_S // 60} dakikadır yanıt yok; iş başka işçiye geçiyor.")

    # --- tasks -------------------------------------------------------------------------------------------------------------

    def start(self):
        from .agency_rates import CompanyStopped, own_everywhere
        with self.cond:
            for state in self.states:
                run = state.run
                try:
                    run.precheck()
                except CompanyStopped as stop:
                    run.stopped(stop)
                    state.finished = True
                    continue
                dead = (run.site["inventory"] or {}).get("dead_links")
                for row in run.members:
                    if dead:
                        run.mark_dead(row, dead)
                        run.shared.tracker.step(1, f"{run.site['company']}: {len(run.members)} ilan.")
                    else:
                        state.pending.append(Task(state, "link", row))
                if not state.pending:
                    self.advance(state)
        with self.cond:          # every first worker is on the list before any of them looks for work (the strand check counts them)
            created = [self.add_worker(exit_, start=False) for exit_ in self.initial_exits]
            created += [self.add_worker(W.direct_exit(), lane=lane, start=False) for lane in (W.LANE_BROWSER, W.LANE_EXTENSION)]
        for worker in created:
            worker.thread.start()
        watcher = threading.Thread(target=self.watch, name="30a-isci-havuz", daemon=True)
        watcher.start()

    def advance(self, state):
        """The next stage of a company whose tasks are all done (called with the lock held)."""
        from .agency_rates import FALLBACK_STATUSES, own_everywhere
        run, site = state.run, state.run.site
        while not state.pending and not state.inflight and not state.finished:
            if state.stage == "links":
                state.stage = "inventory"
                waiting = [r for r in run.members if r["page_status"] in FALLBACK_STATUSES]
                if site["inventory"] and (waiting or site["own_region_id"] or own_everywhere(site)):
                    state.pending.append(Task(state, "inventory"))
            elif state.stage == "inventory":
                state.stage = "fallback"
                if state.units is not None:
                    for row in run.members:
                        if row["page_status"] in FALLBACK_STATUSES:
                            state.pending.append(Task(state, "fallback", row))
            elif state.stage == "fallback":
                state.stage = "own"
                if state.units is not None and (site["own_region_id"] or own_everywhere(site)):
                    state.plan = run.own_plan(state.units)
                    trial = getattr(run, "trial", None)
                    if trial:      # HEDEF-01: the trial run reads a few homes of the company's own inventory
                        state.plan["homes"] = state.plan["homes"][:int(trial.get("own_homes", 2))]
                    for unit in state.plan["homes"]:
                        state.pending.append(Task(state, "own", unit))
            elif state.stage == "own":
                state.stage = "published"
                if hasattr(run.adapter, "published"):
                    state.pending.append(Task(state, "published"))
            else:
                state.finished = True
                self.cond.notify_all()

    def finished(self):
        return all(s.finished for s in self.states)

    def eligible(self, worker, state):
        if state.finished or not state.pending:
            return False
        if worker.lane:
            return state.lane == worker.lane and (state.lane_started or not state.inflight)
        if state.lane:
            return False
        if state.region:
            return worker.exit.region_ok
        return worker.exit.general

    def next_task(self, worker):
        with self.cond:
            while True:
                if self.shared.canceled() or self.error is not None:
                    return None
                if worker.removed:
                    return None
                if worker.lane and worker.lane_state is not None:
                    state = worker.lane_state
                    if state.finished:
                        worker.lane_state = None
                        continue
                    if state.pending:
                        return self.take(worker, state)
                else:
                    best = None
                    for state in self.states:
                        if not self.eligible(worker, state):
                            continue
                        if not worker.lane and state.gate.active >= state.gate.limit:
                            continue
                        score = (len(state.pending) / (state.gate.active + 1), state.domain in worker.sessions)
                        if best is None or score > best[0]:
                            best = (score, state)
                    if best is not None:
                        if worker.lane:
                            worker.lane_state = best[1]
                            best[1].lane_started = True
                        return self.take(worker, best[1])
                if self.finished():
                    return None
                self.strand_check()
                self.cond.wait(IDLE_WAIT_S)

    def take(self, worker, state):
        task = state.pending.popleft()
        task.owner = worker
        state.inflight.add(task)
        if not worker.lane:
            state.gate.active += 1
        worker.task = task
        worker.touch()
        return task

    def strand_check(self):
        """Region-blocked companies no worker may read (no US proxy left): stopped and written down (lock held)."""
        from .agency_rates import CompanyStopped
        from ..proxy import NO_PROXY_SKIP, PROXY_FAILED_SKIP
        alive = [w for w in self.workers if not w.removed and not w.lane]
        for state in self.states:
            if state.finished or not state.pending or state.inflight or state.lane or not state.region:
                continue
            if any(w.exit.region_ok for w in alive):
                continue
            if self.pool is not None and self.region_available:
                continue          # a US proxy is still listed: the next pool refresh starts its worker
            had_proxy = any(w.exit.region_ok for w in self.workers)
            state.run.stopped(CompanyStopped("stopped_blocked", f"{PROXY_FAILED_SKIP} (çekim sırasında çalışan ABD proxy'si kalmadı)"
                                             if had_proxy else NO_PROXY_SKIP))
            state.pending.clear()
            state.finished = True
            self.cond.notify_all()

    def requeue(self, task):
        if task is None:
            return
        with self.cond:
            state = task.state
            if task.abandoned or task not in state.inflight:      # already given to another worker (or finished): nothing to do
                return
            if task in state.inflight:
                state.inflight.discard(task)
                if task.owner is not None and not task.owner.lane:
                    state.gate.active = max(0, state.gate.active - 1)
            task.abandoned = True
            fresh = Task(state, task.kind, task.item)
            if not state.finished:
                state.pending.appendleft(fresh)
            if task.owner is not None:
                task.owner.task = None
            self.cond.notify_all()

    def done(self, task, *, commit=None, stop=None, to_lane=None, failed=None):
        with self.cond:
            state, worker = task.state, task.owner
            if task.abandoned:
                return
            state.inflight.discard(task)
            if not worker.lane:
                state.gate.active = max(0, state.gate.active - 1)
            worker.task = None
            if commit is not None:
                commit()
            if to_lane is not None and not state.finished:
                state.pending.appendleft(Task(state, task.kind, task.item))
                if not state.lane:
                    state.lane = to_lane
                    self.record(f"{state.domain}: doğrulama sayfası gösterdi; şirketin kalan işleri {W.LANE_LABELS[to_lane]} sırasına geçti.")
            if stop is not None and not state.finished:
                state.run.stopped(stop)
                state.pending.clear()
            elif failed is not None and not state.finished:
                state.run.result["status"], state.run.result["message"] = "failed", failed
                state.pending.clear()
            elif state.run.deferred:
                state.pending.clear()
            if not state.finished and not state.pending and not state.inflight:
                if state.run.result["status"] == "done" and not state.run.deferred:
                    try:
                        self.advance(state)
                    except Exception as exc:
                        log.exception("Kiralama şirketinin sonraki aşaması kurulamadı.")
                        state.run.result["status"], state.run.result["message"] = "failed", f"Beklenmeyen hata: {type(exc).__name__}: {str(exc)[:200]}"
                        state.pending.clear()
                        state.finished = True
                else:
                    state.finished = True
            if state.finished or stop is not None or failed is not None:
                state.halted = True
            self.cond.notify_all()

    # --- one task ------------------------------------------------------------------------------------------------------------

    def work(self, worker):
        task = None
        try:
            while True:
                task = self.next_task(worker)
                if task is None:
                    break
                try:
                    if not self.one_task(worker, task):
                        break
                except CollectionCanceled:
                    raise
                except Exception as exc:          # whatever failed around the task: the company is marked, the run goes on
                    log.exception("Kiralama işçisi beklenmedik biçimde durdu.")
                    if task.owner is worker and not task.abandoned and task in task.state.inflight:
                        self.done(task, failed=f"Beklenmeyen hata: {type(exc).__name__}: {str(exc)[:200]}")
        except CollectionCanceled:
            pass
        finally:
            if task is not None and worker.task is task:
                self.requeue(task)            # a task still in flight when the thread ends goes to another worker
            status = "düştü" if worker.dropped else "çıkarıldı" if worker.removed else "bitti"
            self.board_set(worker, durum=status, sirket=None)
            worker.close()
            with self.cond:
                self.cond.notify_all()

    def one_task(self, worker, task):
        """Run one task; False when the worker must stop (its way out is gone, or the run was cancelled)."""
        from .agency_rates import CompanyStopped
        if True:
            if True:
                state = task.state
                state.exits.add(worker.label)
                self.board_set(worker, durum="çalışıyor", sirket=state.run.site["company"])
                if worker.lane:
                    self.run_lane_task(worker, task)
                    return True
                view = self.view(worker, state)
                try:
                    commit, errors = self.execute(view, task)
                except W.ExitDown:
                    self.requeue(task)
                    return False
                except CompanyHalted:
                    self.done(task)                   # the company stopped meanwhile: nothing of this task is kept
                    return True
                except NeedsBrowser as need:
                    state.need_url = need.url
                    self.done(task, to_lane=W.LANE_EXTENSION if self.extension_paired else W.LANE_BROWSER)
                    return True
                except CompanyStopped as stop:
                    self.done(task, commit=getattr(stop, "commit", None), stop=stop)
                    return True
                except CollectionCanceled:
                    self.requeue(task)
                    return False
                except Exception as exc:
                    log.exception("Kiralama işi beklenmedik biçimde durdu.")
                    self.done(task, failed=f"Beklenmeyen hata: {type(exc).__name__}: {str(exc)[:200]}")
                    if self.board is not None:
                        self.board.add(worker.id, "hata")
                    return True
                self.done(task, commit=commit)
                if self.board is not None:
                    self.board.add(worker.id, "biten")
                    if errors:
                        self.board.add(worker.id, "hata", errors)
                return True

    def view(self, worker, state):
        """The company as one worker's task sees it: its own session (way out, pace), its own result lists, no browser."""
        from .agency_rates import VerificationNeeded
        view = copy.copy(state.run)
        view.session = worker.session_for(state)
        view.quotes, view.own_rows, view.own_quotes, view.published = [], [], [], []
        view.counts = worker.counts.setdefault(state.domain, {"blocked": 0, "errors": 0})

        def ask(call):
            try:
                return call()
            except VerificationNeeded as need:
                state.run.shared.marks[state.domain] = {"host": state.domain, "url": need.url, "reason": "doğrulama sayfası"}
                raise NeedsBrowser(need.url) from None
        view.ask = ask
        return view

    def execute(self, view, task):
        """Run one task on a view; returns (commit, error count). The commit merges the task's results into the company. A task that
        stops the company (CompanyStopped) keeps what it read, as a whole-company read did: the exception carries `commit`."""
        from .agency_rates import read_inventory, CompanyStopped
        state, run = task.state, task.state.run
        row = dict(task.item) if task.kind in ("link", "fallback") else None
        got = {}

        def commit():
            if row is not None:
                task.item.update(row)
            if "units" in got:
                state.units = got["units"]
                run.result["inventory_count"], run.result["inventory_raw_sha256"] = len(got["units"]), got["hashes"]
                run.shared.tracker.step(0, f"{run.site['company']}: şirketin listesinde {len(got['units'])} ilan.")
            run.quotes.extend(view.quotes)
            run.own_rows.extend(view.own_rows)
            run.own_quotes.extend(view.own_quotes)
            run.published.extend(view.published)
            if task.kind == "link":
                run.shared.tracker.step(1, f"{run.site['company']}: {sum(r['page_status'] != 'not_queried' for r in run.members)}/{len(run.members)} ilan.")
        try:
            if task.kind == "link":
                view.link(row)
            elif task.kind == "inventory":
                got["units"], got["hashes"] = read_inventory(view.session, view.adapter, run.site, view.ask)
            elif task.kind == "fallback":
                view.fallback_one(row, state.units)
            elif task.kind == "own":
                view.own_one(task.item, state.plan)
            elif task.kind == "published":
                view.published_rents()
        except CompanyStopped as stop:
            stop.commit = commit
            raise
        errors = sum(1 for q in view.quotes + view.own_quotes if q.get("status") == "error") + (1 if row and row.get("page_status") == "error" else 0)
        return commit, errors

    def run_lane_task(self, worker, task):
        """A browser company's task in its lane; when the company is finished its browser is closed here, in the lane's own thread
        (Playwright's sync API belongs to the thread that started it: the lane's next company starts its own; HEDEF-01 trial run,
        26 Nov 2026: oversee.us failed with "Sync API inside the asyncio loop" while exclusive30a.com's browser was still open)."""
        state, run = task.state, task.state.run
        try:
            self.lane_task(worker, task)
        finally:
            if state.finished or self.shared.canceled():
                close_browser(run)

    def lane_task(self, worker, task):
        from .agency_rates import CompanyDeferred, CompanyStopped
        state, run = task.state, task.state.run
        try:
            if not getattr(state, "opened", False):
                state.opened = True
                if getattr(state, "need_url", None):      # a worker met the verification page: the browser opens on that page
                    run.open_browser(state.need_url)
                    run.result["verification"] = "completed"
                else:
                    run.open_lane()
            commit, errors = self.execute(lane_view(run), task)
        except CompanyDeferred as wait:
            run.deferred = wait.url
            run.result["status"], run.result["message"] = "verification_timeout", "Doğrulama bekleniyor; şirket sona bırakıldı."
            self.done(task)
            return
        except CompanyStopped as stop:
            self.done(task, commit=getattr(stop, "commit", None), stop=stop)
            return
        except CollectionCanceled:
            self.requeue(task)
            raise
        except Exception as exc:
            log.exception("Kiralama işi (tarayıcı sırası) beklenmedik biçimde durdu.")
            self.done(task, failed=f"Beklenmeyen hata: {type(exc).__name__}: {str(exc)[:200]}")
            return
        self.done(task, commit=commit)
        if self.board is not None:
            self.board.add(worker.id, "biten")
            if errors:
                self.board.add(worker.id, "hata", errors)

    def wait(self):
        try:
            with self.cond:
                while not self.finished():
                    if self.shared.canceled():
                        break
                    if not any(w.thread.is_alive() for w in self.workers if w.thread.ident is not None):
                        break
                    readers = [w for w in self.workers if not w.lane and w.thread.ident is not None and w.thread.is_alive()]
                    if not readers and all(s.finished or not s.lane for s in self.states) and not (self.pool is not None and self.region_available
                                                                                                and any(not s.finished for s in self.states)):
                        break         # no worker left for the companies still waiting (and no lane work left)
                    self.strand_check()
                    self.cond.wait(1.0)
        finally:
            self.stop_pool.set()
            with self.cond:
                self.cond.notify_all()
            joined = set()
            while True:
                with self.cond:
                    pending = [w for w in self.workers if id(w) not in joined]
                if not pending:
                    break
                for worker in pending:
                    joined.add(id(worker))
                    if worker.thread.ident is not None:
                        worker.thread.join(timeout=60)
        if self.shared.canceled():
            raise CollectionCanceled()
        unfinished = [s for s in self.states if not s.finished]
        for state in unfinished:     # every worker stopped (e.g. every proxy dropped and no direct exit): written down, not lost
            from .agency_rates import CompanyStopped
            state.run.stopped(CompanyStopped("stopped_errors", "Çekim sırasında bu şirketi okuyabilecek işçi kalmadı; şirket yarım kaldı."))
            state.finished = True

    def summary(self):
        return {"isciler": [{"cikis": w.label, "durum": "düştü" if w.dropped else "çıkarıldı" if w.removed else "bitti"}
                            for w in self.workers if not w.lane],
                "sirketler": {s.domain: {"cikislar": sorted(s.exits), "istek": sum(x.requests for x in s.sessions) + s.run.session.requests,
                                         "sira": s.lane} for s in self.states},
                "olaylar": list(self.events)}


def close_browser(run):
    if run.browser is not None:
        try:
            run.browser.close()
        except Exception:
            log.exception("Şirketin tarayıcısı kapatılamadı.")
        run.browser = None


def lane_view(run):
    """In a lane the task works with the company's own session and its normal `ask` (which may open the browser); only the result
    lists are the task's own until it ends."""
    view = copy.copy(run)
    view.quotes, view.own_rows, view.own_quotes, view.published = [], [], [], []
    view.ask = run.ask
    return view


_SESSION_CLASS = None


def worker_session_class():
    global _SESSION_CLASS
    if _SESSION_CLASS is None:
        from .agency_rates import SiteSession
        _SESSION_CLASS = type("WorkerSession", (WorkerSessionMixin, SiteSession), {})
    return _SESSION_CLASS
