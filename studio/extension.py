"""The bridge to the "30A Studio Yardımcısı" browser extension (GÖREV-14, Adım 7; docs/M16-TARAYICI-EKLENTISI.md).

Some sites refuse the program's own browser (a separate profile reached over CDP) but let the user's everyday Chrome in. The program never
connects to that profile; the user installs a small extension instead. The extension opens the pages the program asks for, in a window
of its own, and hands back only the page's content.

Pairing: Settings → Tarayıcı eklentisi shows a code; the user types it into the extension once. The code lives in the data folder
(`eklenti.json`) and in the extension's storage; the first extension origin (`chrome-extension://<id>`) that pairs with it is the only
one the program answers. Renewing the code drops the pairing.

Sessions: a collector that needs the extension opens a session for one domain and asks for pages ("sayfa": open an address and wait by
seconds or for an element) or requests made from inside the page ("istek": the page's own fetch, for a site whose data comes from its
JSON endpoints). The extension asks every few seconds for a session, then for its next item, and posts each result. One page at a time,
at least `aralik_saniye` (8 by default) apart on a domain. Results come back as dicts; raw copies are kept by the collector's own store
(method "eklenti") or, for the Settings trials, here under `raw/eklenti/`.

States the job panel shows: "eklenti bekleniyor" while the extension is paired but silent (Chrome closed) — the user may hand the job to
the program's own browser; after WAIT_EXTENSION_S the hand-over happens by itself and is written down. A verification page pauses the
extension (it brings its window forward and notifies the user) for at most 15 minutes; then the page is skipped. A login page is marked
"giriş gerekiyor" and skipped. The extension never clicks or types.
"""
import base64
import hashlib
import json
import os
import secrets
import tempfile
import threading
import time
import uuid
from collections import OrderedDict, deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

PAIRING_FILE = "eklenti.json"
CONNECTED_S = 20.0
DEFAULT_GAP_S, MIN_GAP_S, MAX_GAP_S = 8, 3, 120
VERIFY_WAIT_S = 15 * 60
PAGE_TIMEOUT_S = VERIFY_WAIT_S + 240
REQUEST_TIMEOUT_S = 180
WAIT_EXTENSION_S = 30 * 60
PERMISSION_WAIT_S = 15 * 60
STALE_SESSION_S = 45.0
ORIGIN_PREFIX = "chrome-extension://"
LOCAL_HOSTS = ("127.0.0.1", "localhost")
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
HEADER = "x-studio-eklenti"
RESULT_STATES = ("tamam", "dogrulama", "giris", "odeme", "izin_yok", "hata")
MAX_HTML_BYTES = 12_000_000


class ExtensionError(Exception):
    """The extension could not give the page (Turkish reason)."""


class HandedOver(ExtensionError):
    """The job was handed to the program's own browser (by the user, or after waiting too long for the extension)."""


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_code():
    return "-".join("".join(secrets.choice(CODE_ALPHABET) for _ in range(4)) for _ in range(2))


def domain_of(url_or_host):
    host = (urlsplit(url_or_host).hostname if "//" in (url_or_host or "") else url_or_host) or ""
    host = host.lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


class Session:
    """One domain's pages and requests for one job, read by the extension one item at a time."""

    def __init__(self, bridge, domain, job_id=None, purpose="", notify=None):
        self.bridge, self.domain, self.job_id, self.purpose = bridge, domain_of(domain), job_id, purpose
        self.notify = notify or (lambda kind, value=None: None)
        self.id = uuid.uuid4().hex
        self.state = "bekliyor"            # bekliyor → calisiyor → bitti | devredildi
        self.created_at, self.active_at = time.time(), None
        self.queue, self.in_flight, self.results = deque(), {}, {}
        self.closed = False
        self.verifying = None
        self.permission_missing_since = None
        self.count = 0

    # ---- for collectors (their own thread) ----

    def page(self, url, wait=None, *, canceled=lambda: False, timeout=PAGE_TIMEOUT_S):
        """{"durum", "adres", "son_adres", "baslik", "http_durumu", "html" (bytes or None), "not", "sha256"}."""
        result = self.submit({"tur": "sayfa", "adres": url, "bekle": wait or {"saniye": 2}}, canceled, timeout)
        html = result.get("html")
        if isinstance(html, str):
            result["html"] = html.encode("utf-8")
        if result.get("html") is not None:
            result["sha256"] = hashlib.sha256(result["html"]).hexdigest()
        return result

    def request(self, method, url, *, headers=None, body=None, canceled=lambda: False, timeout=REQUEST_TIMEOUT_S):
        """A request made with the page's own fetch from the session's tab: (status, final url, headers, body bytes)."""
        result = self.submit({"tur": "istek", "yontem": method, "adres": url, "basliklar": headers or {}, "govde": body}, canceled, timeout)
        if result.get("durum") != "tamam":
            raise ExtensionError(result.get("not") or f"Eklenti isteği yapamadı ({result.get('durum')}).")
        return (int(result.get("http_durumu") or 0), result.get("son_adres") or url, result.get("basliklar") or {},
                base64.b64decode(result.get("govde_base64") or ""))

    def submit(self, item, canceled, timeout):
        with self.bridge.lock:
            if self.state == "devredildi":
                raise HandedOver("İş programın kendi tarayıcısına devredildi.")
            if self.closed:
                raise ExtensionError("Eklenti oturumu kapandı.")
            item = {**item, "id": uuid.uuid4().hex, "sira": self.count}
            self.count += 1
            self.queue.append(item)
            self.bridge.lock.notify_all()
        start, waiting_since, told = time.monotonic(), None, None
        while True:
            if canceled():
                from .sources.base import CollectionCanceled
                self.close()
                raise CollectionCanceled()
            with self.bridge.lock:
                if item["id"] in self.results:
                    return self.results.pop(item["id"])
                if self.state == "devredildi":
                    raise HandedOver("İş programın kendi tarayıcısına devredildi.")
                connected = self.bridge.connected
                missing = self.permission_missing_since
                self.bridge.lock.wait(1.0)
            if not connected:
                waiting_since = waiting_since or time.monotonic()
                if told != "bekliyor":
                    told = "bekliyor"
                    self.notify("eklenti_bekleniyor", self.domain)
                if time.monotonic() - waiting_since > WAIT_EXTENSION_S:
                    self.bridge.hand_over(self.job_id, reason="Eklenti 30 dk bağlanmadı; iş programın kendi tarayıcısına devredildi.")
                    raise HandedOver("Eklenti 30 dk bağlanmadı; iş programın kendi tarayıcısına devredildi.")
                continue
            if told == "bekliyor":
                told = None
                self.notify("eklenti_baglandi", self.domain)
            waiting_since = None
            if missing and time.time() - missing > PERMISSION_WAIT_S:
                raise ExtensionError(f"Eklentiye {self.domain} için izin verilmedi; site atlandı.")
            if time.monotonic() - start > timeout:
                raise ExtensionError("Eklenti bu sayfayı zamanında okuyamadı (zaman aşımı).")

    def close(self):
        with self.bridge.lock:
            self.closed = True
            self.bridge.lock.notify_all()

    # ---- for the extension (request threads) ----

    def view(self):
        return {"id": self.id, "alan_adi": self.domain, "aralik_saniye": self.bridge.gap(), "amac": self.purpose,
                "dogrulama_bekleme_saniye": VERIFY_WAIT_S}


class ExtensionBridge:
    def __init__(self, data_dir, clock=time.time):
        self.data_dir = Path(data_dir)
        self.path = self.data_dir / PAIRING_FILE
        self.clock = clock
        self.lock = threading.Condition()
        self.sessions = OrderedDict()
        self.last_seen, self.version, self.allowed = None, None, []
        self.pending = {}                      # domain -> first time a job waited for its permission
        self.handed_over = {}                  # job id -> reason
        self.config = self.load()

    # ---- pairing file ----

    def load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        data = data if isinstance(data, dict) else {}
        if not isinstance(data.get("kod"), str) or len(data["kod"]) != 9:
            data = {"kod": new_code(), "olusturuldu": now_iso(), "koken": None, "eslesti": None, "aralik_saniye": DEFAULT_GAP_S}
            self.save(data)
        data.setdefault("aralik_saniye", DEFAULT_GAP_S)
        return data

    def save(self, data):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(dir=self.data_dir, prefix=".eklenti-", suffix=".json")
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as out:
                json.dump(data, out, ensure_ascii=False, indent=1)
            os.replace(temporary, self.path)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise

    def code(self):
        return self.config["kod"]

    def renew(self):
        with self.lock:
            self.config = {**self.config, "kod": new_code(), "olusturuldu": now_iso(), "koken": None, "eslesti": None}
            self.save(self.config)
            self.last_seen, self.version, self.allowed = None, None, []
            return self.config["kod"]

    def gap(self):
        value = self.config.get("aralik_saniye")
        return value if isinstance(value, int) and MIN_GAP_S <= value <= MAX_GAP_S else DEFAULT_GAP_S

    def set_gap(self, seconds):
        if isinstance(seconds, bool) or not isinstance(seconds, int) or not MIN_GAP_S <= seconds <= MAX_GAP_S:
            raise ValueError(f"Bekleme {MIN_GAP_S} ile {MAX_GAP_S} saniye arasında bir tam sayı olmalı.")
        with self.lock:
            self.config = {**self.config, "aralik_saniye": seconds}
            self.save(self.config)

    def pair(self, origin, code, version=None):
        """The extension's first contact: the right code from a chrome-extension:// origin. The first origin is kept; another one is
        refused until the code is renewed."""
        if not isinstance(origin, str) or not origin.startswith(ORIGIN_PREFIX) or len(origin) > 100:
            return False
        with self.lock:
            if not secrets.compare_digest(str(code or ""), self.config["kod"]):
                return False
            if self.config.get("koken") not in (None, origin):
                return False
            if self.config.get("koken") is None:
                self.config = {**self.config, "koken": origin, "eslesti": now_iso()}
                self.save(self.config)
            self.touch(version, None)
            return True

    def authorized(self, origin, code):
        koken = self.config.get("koken")
        return bool(koken) and origin == koken and secrets.compare_digest(str(code or ""), self.config["kod"])

    @property
    def paired(self):
        return bool(self.config.get("koken"))

    @property
    def connected(self):
        return self.paired and self.last_seen is not None and self.clock() - self.last_seen <= CONNECTED_S

    def touch(self, version, allowed):
        self.last_seen = self.clock()
        if isinstance(version, str):
            self.version = version[:20]
        if isinstance(allowed, list):
            self.allowed = sorted({domain_of(a) for a in allowed if isinstance(a, str) and domain_of(a)})[:500]
            for domain in list(self.pending):
                if self.permitted(domain):
                    self.pending.pop(domain, None)
                    for session in self.sessions.values():
                        if session.domain == domain:
                            session.permission_missing_since = None

    def permitted(self, domain):
        """The program's own local address is always allowed (the extension's one required host permission); a site only when the
        user gave the extension its permission."""
        domain = domain_of(domain)
        return domain in LOCAL_HOSTS or any(domain == a or domain.endswith("." + a) for a in self.allowed)

    def status(self):
        with self.lock:
            active = [s for s in self.sessions.values() if s.state in ("bekliyor", "calisiyor") and not s.closed]
            return {"eslesti": self.paired, "bagli": self.connected, "son_gorulme": datetime.fromtimestamp(self.last_seen, timezone.utc)
                    .isoformat(timespec="seconds") if self.last_seen else None, "surum": self.version, "kod": self.code(),
                    "kod_olusturuldu": self.config.get("olusturuldu"), "eslesme_zamani": self.config.get("eslesti"),
                    "izinli_alan_adlari": list(self.allowed), "izin_bekleyen_alan_adlari": sorted(self.pending),
                    "aralik_saniye": self.gap(), "aralik_sinirlari": [MIN_GAP_S, MAX_GAP_S],
                    "acik_oturumlar": [{"alan_adi": s.domain, "durum": s.state, "dogrulama": s.verifying} for s in active]}

    # ---- sessions ----

    def open(self, domain, *, job_id=None, purpose="", notify=None):
        if job_id is not None and job_id in self.handed_over:
            raise HandedOver(self.handed_over[job_id])
        session = Session(self, domain, job_id, purpose, notify)
        with self.lock:
            self.sessions[session.id] = session
            self.lock.notify_all()
        return session

    def take(self):
        """The next session the extension should work on (FIFO): a waiting one, or a running one the extension went silent on (its
        service worker was stopped; the item it had is asked again). Sessions waiting for a permission stay until it is given."""
        with self.lock:
            self.prune()
            for session in self.sessions.values():
                if session.closed and not session.queue:
                    continue
                if session.state == "bekliyor" or (session.state == "calisiyor" and session.active_at
                                                   and self.clock() - session.active_at > STALE_SESSION_S):
                    if session.state == "calisiyor":
                        session.queue.extendleft(reversed(list(session.in_flight.values())))
                        session.in_flight.clear()
                    if not self.permitted(session.domain):
                        self.pending.setdefault(session.domain, self.clock())
                        if session.permission_missing_since is None:
                            session.permission_missing_since = self.clock()
                            session.notify("izin_yok", session.domain)
                        continue
                    session.state, session.active_at = "calisiyor", self.clock()
                    return session.view()
            return None

    def next_item(self, session_id):
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None or session.state == "devredildi":
                return {"bitti": True}
            session.active_at = self.clock()
            if session.queue:
                item = session.queue.popleft()
                session.in_flight[item["id"]] = item
                return {"oge": item}
            if session.closed:
                session.state = "bitti"
                return {"bitti": True}
            return {"bekle": True}

    def deliver(self, session_id, item_id, result):
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None or item_id not in session.in_flight:
                return False
            item = session.in_flight.pop(item_id)
            session.active_at = self.clock()
            state = result.get("durum") if result.get("durum") in RESULT_STATES else "hata"
            html = result.get("html") if isinstance(result.get("html"), str) else None
            if html is not None and len(html.encode("utf-8")) > MAX_HTML_BYTES:
                html, state = None, "hata"
                result = {**result, "not": "Sayfa boyut sınırını aştı."}
            session.results[item_id] = {"durum": state, "tur": item["tur"], "adres": item["adres"], "son_adres": result.get("son_adres") or item["adres"],
                                        "baslik": str(result.get("baslik") or "")[:300], "http_durumu": result.get("http_durumu"),
                                        "html": html, "not": str(result.get("not") or "")[:500] or None, "basliklar": result.get("basliklar"),
                                        "govde_base64": result.get("govde_base64"), "okundu": now_iso(), "yontem": "eklenti"}
            if session.verifying:
                session.verifying = None
                session.notify("dogrulama_bitti", None)
            self.lock.notify_all()
            return True

    def report(self, session_id, *, verifying=None, missing=None):
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None:
                return False
            session.active_at = self.clock()
            if verifying and session.verifying != verifying:
                session.verifying = verifying
                session.notify("dogrulama", domain_of(verifying))
            if missing:
                self.pending.setdefault(domain_of(missing), self.clock())
                session.permission_missing_since = session.permission_missing_since or self.clock()
                session.state = "bekliyor"
                session.queue.extendleft(reversed(list(session.in_flight.values())))
                session.in_flight.clear()
                session.notify("izin_yok", domain_of(missing))
            return True

    def finished(self, session_id, error=None):
        with self.lock:
            session = self.sessions.get(session_id)
            if session is None:
                return False
            if error and not session.closed:
                for item in list(session.in_flight.values()) + list(session.queue):
                    session.results[item["id"]] = {"durum": "hata", "tur": item["tur"], "adres": item["adres"], "son_adres": item["adres"],
                                                   "baslik": "", "http_durumu": None, "html": None, "not": str(error)[:300], "yontem": "eklenti"}
                session.in_flight.clear()
                session.queue.clear()
            session.state = "bitti" if session.closed else "bekliyor"
            self.lock.notify_all()
            return True

    def hand_over(self, job_id, reason="Kullanıcı işi programın kendi tarayıcısına devretti."):
        with self.lock:
            self.handed_over[job_id] = reason
            for session in self.sessions.values():
                if session.job_id == job_id and session.state in ("bekliyor", "calisiyor"):
                    session.state = "devredildi"
            self.lock.notify_all()
        return reason

    def prune(self):
        old = [k for k, s in self.sessions.items() if s.state in ("bitti", "devredildi") and not s.results and not s.queue
               and self.clock() - (s.active_at or s.created_at) > 600]
        for key in old:
            self.sessions.pop(key, None)

    # ---- raw copies of the Settings trials ----

    def save_raw(self, result, label):
        """A trial page's raw copy under raw/eklenti/<date>/ with its SHA-256 and a small record beside it (method "eklenti")."""
        folder = self.data_dir / "raw" / "eklenti" / datetime.now(timezone.utc).strftime("%Y%m%d")
        folder.mkdir(parents=True, exist_ok=True)
        stem = f"{datetime.now(timezone.utc).strftime('%H%M%S')}-{uuid.uuid4().hex[:8]}"
        body = result.get("html") or b""
        if isinstance(body, str):
            body = body.encode("utf-8")
        digest = hashlib.sha256(body).hexdigest()
        (folder / f"{stem}.html").write_bytes(body)
        record = {"yontem": "eklenti", "etiket": label, "adres": result.get("adres"), "son_adres": result.get("son_adres"),
                  "baslik": result.get("baslik"), "durum": result.get("durum"), "http_durumu": result.get("http_durumu"),
                  "okundu": result.get("okundu"), "sha256": digest, "bayt": len(body), "not": result.get("not")}
        (folder / f"{stem}.json").write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
        return {**record, "dosya": (folder / f"{stem}.html").relative_to(self.data_dir).as_posix()}


class JobAccess:
    """What a collector job gets: the bridge, and job panel messages for the extension's states."""

    def __init__(self, bridge, db, job_id):
        self.bridge, self.db, self.job_id = bridge, db, job_id

    @property
    def paired(self):
        return self.bridge.paired

    def open(self, domain, purpose=""):
        return self.bridge.open(domain, job_id=self.job_id, purpose=purpose, notify=self.notify)

    def notify(self, kind, value=None):
        messages = {
            "eklenti_bekleniyor": ("Eklenti bekleniyor: tarayıcı eklentisi bağlı değil. Chrome'u açın; isterseniz İşler panelinden işi "
                                   "programın kendi tarayıcısına devredin.", {"tur": "eklenti", "bekliyor": True}),
            "eklenti_baglandi": ("Eklenti bağlandı; sayfalar kullanıcının Chrome'unda, eklentinin kendi penceresinde okunuyor.",
                                 {"tur": "eklenti", "bekliyor": False}),
            "izin_yok": (f"Eklentinin {value} için izni yok: Chrome'da eklenti simgesine tıklayıp “İzin ver” düğmesine basın.", None),
            "dogrulama": (f"Kullanıcı doğrulaması bekleniyor: {value}. Chrome'da öne gelen 30A Studio Yardımcısı penceresinde doğrulamayı "
                          f"tamamlayın (en çok {VERIFY_WAIT_S // 60} dk).", None),
            "dogrulama_bitti": ("Doğrulama beklemesi bitti; okuma devam ediyor.", None),
        }
        message, info = messages.get(kind, (None, None))
        if message is None or self.db is None or self.job_id is None:
            return
        extra = {}
        if kind == "dogrulama":
            extra["waiting_for"] = value
        elif kind == "dogrulama_bitti":
            extra["waiting_for"] = ""
        if info is not None:
            extra["progress_info"] = info
        self.db.update_job(self.job_id, message=message, **extra)
