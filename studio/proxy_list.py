"""The proxy list (HEDEF-01, the user's decision of 26 November 2026): Settings → "ABD proxy'si" takes many proxies; each working proxy
is one worker of a rental price run (studio/workers.py), the direct connection is one more.

- `<data>/ayarlar.json` → `abd_proxy_listesi`: per row its id, address (`scheme://host:port`), user name, state ("denenmedi",
  "calisiyor", "calismiyor"), the exit country and the time of the last test. `abd_proxy` (the GÖREV-16 single proxy) mirrors the first
  row, so the region-blocked reading keeps using "the" proxy; the single proxy of earlier versions becomes the first row.
- Passwords only in Windows Credential Manager (`studio.credentials`): the first row keeps the old name `abd_proxy_parolasi`, the others
  `abd_proxy_parolasi_<id>`. Never in a file, a log or an API answer.
- Bulk add: the user pastes one proxy per line. Accepted forms (Housing Atlas's `host:port:user:password` among them):
  `host:port`, `host:port:user:password`, `user:password@host:port`, `scheme://host:port`, `scheme://user:password@host:port`. A line
  without a scheme gets the chosen type (http or socks5). The passwords go to Credential Manager at once; every line is then tested
  through the proxy to the public IP service (`proxy.test`) and marked working or not; a row that does not work is no worker.
- `site_limit`: how many workers may read the same site at once (`isciler.site_basina`, 1–8, default 4).

Error texts name a line by its number only (a line may carry a password).
"""
import secrets as _secrets
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from . import credentials, logs
from . import proxy as P
from .ai import settings as stored_settings

ROWS = "abd_proxy_listesi"
WORKERS = "isciler"
FIRST_ID = "1"
STATES = ("denenmedi", "calisiyor", "calismiyor")
STATE_LABELS = {"denenmedi": "denenmedi", "calisiyor": "çalışıyor", "calismiyor": "çalışmıyor"}
DEFAULT_SITE_LIMIT = 4
SITE_LIMIT_RANGE = (1, 8)
MAX_ROWS = 300
TEST_WORKERS = 8
_lock = threading.RLock()


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def password_name(row_id):
    return P.PASSWORD if row_id == FIRST_ID else f"{P.PASSWORD}_{row_id}"


def new_id(taken):
    while True:
        value = _secrets.token_hex(4)
        if value not in taken and value != FIRST_ID:
            return value


def _clean_row(item):
    if not isinstance(item, dict):
        return None
    address = item.get("adres") if isinstance(item.get("adres"), str) else ""
    row_id = item.get("id") if isinstance(item.get("id"), str) else ""
    if not address or P.proxy_url_error(address) or not (row_id == FIRST_ID or credentials.LIST_PASSWORD.match(f"{P.PASSWORD}_{row_id}")):
        return None
    user = item.get("kullanici") if isinstance(item.get("kullanici"), str) else ""
    state = item.get("durum") if item.get("durum") in STATES else "denenmedi"
    country = item.get("ulke") if isinstance(item.get("ulke"), str) and len(item.get("ulke")) == 2 else None
    return {"id": row_id, "adres": address.strip(), "kullanici": user[:200], "durum": state, "ulke": country,
            "denendi": item.get("denendi") if isinstance(item.get("denendi"), str) else None,
            "not": str(item.get("not"))[:300] if item.get("not") else None}


def rows(data_dir):
    """The list as stored; the GÖREV-16 single proxy becomes the first row when there is no list yet."""
    data = stored_settings.stored_settings(data_dir)
    listed = data.get(ROWS)
    if isinstance(listed, list):
        out, seen = [], set()
        for item in listed:
            row = _clean_row(item)
            if row and row["id"] not in seen:
                seen.add(row["id"])
                out.append(row)
        return out
    single = data.get(P.SECTION) if isinstance(data.get(P.SECTION), dict) else {}
    address = single.get("adres") if isinstance(single.get("adres"), str) else ""
    if address and not P.proxy_url_error(address):
        user = single.get("kullanici") if isinstance(single.get("kullanici"), str) else ""
        return [{"id": FIRST_ID, "adres": address.strip(), "kullanici": user[:200], "durum": "denenmedi", "ulke": None, "denendi": None, "not": None}]
    return []


def write_rows(data_dir, items):
    """The list and its mirror (`abd_proxy` = the first row). The first row always carries the id whose password is the old name."""
    with _lock:
        data = stored_settings.stored_settings(data_dir)
        data[ROWS] = [{k: row.get(k) for k in ("id", "adres", "kullanici", "durum", "ulke", "denendi", "not")} for row in items]
        first = items[0] if items else None
        data[P.SECTION] = {"adres": first["adres"], "kullanici": first["kullanici"]} if first else {"adres": "", "kullanici": ""}
        stored_settings.write_settings(data_dir, data)


def _move_first_password(old_id):
    """When the first row is removed, the next row becomes the first: its password moves to the old name."""
    value = credentials.get_secret(password_name(old_id))
    if value:
        credentials.set_secret(P.PASSWORD, value)
    credentials.delete_secret(password_name(old_id))


def settings_of(row, *, with_password=True):
    password = credentials.get_secret(password_name(row["id"])) if with_password and row["kullanici"] else None
    return P.ProxySettings(row["adres"], row["kullanici"], password)


# ---- parsing a pasted line ----------------------------------------------------------------------------------------------------------

def parse_line(line, scheme="http"):
    """One pasted line -> (address `scheme://host:port`, user, password). Raises ValueError with a Turkish reason that never repeats
    the line."""
    text = (line or "").strip()
    scheme = (scheme or "http").lower()
    if scheme not in P.PROXY_SCHEMES:
        raise ValueError("tür http, https ya da socks5 olmalı")
    user = password = ""
    if "://" in text:
        scheme, text = text.split("://", 1)
        scheme = scheme.lower()
        if scheme not in P.PROXY_SCHEMES:
            raise ValueError("desteklenmeyen şema (http, https, socks5)")
    if "@" in text:
        credentials_part, text = text.rsplit("@", 1)
        user, _, password = credentials_part.partition(":")
        parts = text.split(":")
        if len(parts) != 2:
            raise ValueError("biçim tanınmadı (sunucu:port bekleniyordu)")
        host, port = parts
    else:
        parts = text.split(":", 3)
        if len(parts) == 2:
            host, port = parts
        elif len(parts) == 4:
            host, port, user, password = parts
        else:
            raise ValueError("biçim tanınmadı (sunucu:port ya da sunucu:port:kullanıcı:parola)")
    host, port, user = host.strip(), port.strip(), user.strip()
    if not host or not port.isdigit() or not 0 < int(port) < 65536:
        raise ValueError("sunucu adı ya da port geçersiz")
    if any(ch.isspace() for ch in host) or "/" in host:
        raise ValueError("sunucu adı geçersiz")
    if len(user) > 200 or len(password) > credentials.MAX_LENGTH:
        raise ValueError("kullanıcı adı ya da parola çok uzun")
    if user and not password:
        raise ValueError("kullanıcı adı var ama parola yok")
    address = f"{scheme}://{host}:{int(port)}"
    error = P.proxy_url_error(address)
    if error:
        raise ValueError("adres geçersiz")
    logs.register_secret(password or None)
    return address, user, password


# ---- view, add, remove, test --------------------------------------------------------------------------------------------------------

def view(data_dir):
    """Every row for the screen: its order, `scheme://host` label, user name, whether its password is saved, state and country."""
    out = []
    for index, row in enumerate(rows(data_dir), start=1):
        try:
            saved = credentials.has_secret(password_name(row["id"]))
        except credentials.SecretError:
            saved = False
        out.append({"id": row["id"], "sira": index, "adres": row["adres"], "etiket": logs.proxy_label(row["adres"]),
                    "kullanici": row["kullanici"], "parola_kayitli": saved, "durum": row["durum"], "durum_metni": STATE_LABELS[row["durum"]],
                    "ulke": row["ulke"], "denendi": row["denendi"], "not": row["not"],
                    "isci": row["durum"] != "calismiyor" and (saved or not row["kullanici"])})
    return out


def add_lines(data_dir, text, scheme="http", *, tester=None):
    """Bulk add: every line a proxy (a known address + user name is updated); passwords to Credential Manager at once; then every new
    or changed row is tested. Returns the counts, the line errors (by number) and the test results."""
    lines = [(number, line) for number, line in enumerate(str(text or "").splitlines(), start=1) if line.strip() and not line.strip().startswith("#")]
    errors, touched, added, updated = [], [], 0, 0
    with _lock:
        current = rows(data_dir)
        for number, line in lines:
            try:
                address, user, password = parse_line(line, scheme)
            except ValueError as exc:
                errors.append({"satir": number, "hata": str(exc)})
                continue
            row = next((r for r in current if r["adres"] == address and r["kullanici"] == user), None)
            if row is None:
                if len(current) >= MAX_ROWS:
                    errors.append({"satir": number, "hata": f"listede en çok {MAX_ROWS} proxy olabilir"})
                    continue
                row = {"id": FIRST_ID if not current else new_id({r["id"] for r in current}), "adres": address, "kullanici": user,
                       "durum": "denenmedi", "ulke": None, "denendi": None, "not": None}
                current.append(row)
                added += 1
            else:
                row.update({"durum": "denenmedi", "ulke": None, "not": None})
                updated += 1
            try:
                if password:
                    credentials.set_secret(password_name(row["id"]), password)
            except credentials.SecretError as exc:
                errors.append({"satir": number, "hata": str(exc)})
            if row["id"] not in touched:
                touched.append(row["id"])
        write_rows(data_dir, current)
    results = test_rows(data_dir, touched, tester=tester) if touched else []
    return {"eklenen": added, "guncellenen": updated, "hatalar": errors, "sonuclar": results}


def remove(data_dir, row_id):
    with _lock:
        current = rows(data_dir)
        index = next((i for i, r in enumerate(current) if r["id"] == row_id), None)
        if index is None:
            return False
        try:
            credentials.delete_secret(password_name(row_id))
        except credentials.SecretError as exc:
            raise P.ProxyError(str(exc)) from exc
        del current[index]
        if index == 0 and current:              # the next row becomes the first: it takes the first row's id and password name
            old = current[0]["id"]
            try:
                _move_first_password(old)
            except credentials.SecretError as exc:
                raise P.ProxyError(str(exc)) from exc
            current[0]["id"] = FIRST_ID
        write_rows(data_dir, current)
        return True


def update_state(data_dir, row_id, result):
    with _lock:
        current = rows(data_dir)
        for row in current:
            if row["id"] == row_id:
                row["durum"] = "calisiyor" if result.get("ok") else "calismiyor"
                row["ulke"] = result.get("ulke") if result.get("ok") else row.get("ulke")
                row["denendi"] = now_iso()
                row["not"] = result.get("uyari") or (None if result.get("ok") else "; ".join(result.get("satirlar", [])[1:])[:300] or None)
        write_rows(data_dir, current)


def mark_down(data_dir, row_id, note):
    """A proxy that dropped during a run (studio/workers.py): marked "çalışmıyor" so the next run does not start a worker for it."""
    update_state(data_dir, row_id, {"ok": False, "satirlar": ["", note]})


def test_row(data_dir, row_id, *, tester=None):
    tester = tester or P.test
    row = next((r for r in rows(data_dir) if r["id"] == row_id), None)
    if row is None:
        raise P.ProxyError("Bu proxy listede yok.")
    order = next(i for i, r in enumerate(rows(data_dir), start=1) if r["id"] == row_id)
    try:
        proxy = settings_of(row)
        result = tester(proxy)
    except (P.ProxyError, credentials.SecretError) as exc:
        result = {"ok": False, "ip": None, "ulke": None, "uyari": None, "satirlar": [f"Proxy: {logs.proxy_label(row['adres'])}", str(exc)]}
    update_state(data_dir, row_id, result)
    return {**result, "id": row_id, "sira": order, "etiket": logs.proxy_label(row["adres"])}


def test_rows(data_dir, row_ids=None, *, tester=None):
    """Every row (or the given ones), side by side (TEST_WORKERS at a time); one result per row in the list's order."""
    ids = [r["id"] for r in rows(data_dir)] if row_ids is None else list(row_ids)
    if not ids:
        return []
    with ThreadPoolExecutor(max_workers=min(TEST_WORKERS, len(ids)), thread_name_prefix="30a-proxy-test") as pool:
        results = list(pool.map(lambda i: test_row(data_dir, i, tester=tester), ids))
    return sorted(results, key=lambda r: r["sira"])


def usable(data_dir):
    """(row id, order, ProxySettings, country) of every row that may be a worker: not marked "çalışmıyor", password saved when a user
    name is set. Credential Manager unreadable: no proxy worker."""
    out = []
    for index, row in enumerate(rows(data_dir), start=1):
        if row["durum"] == "calismiyor":
            continue
        try:
            proxy = settings_of(row)
        except credentials.SecretError:
            continue
        if proxy.missing_password:
            continue
        out.append((row["id"], index, proxy, row["ulke"]))
    return out


# ---- the workers' site limit --------------------------------------------------------------------------------------------------------

def site_limit(data_dir):
    section = stored_settings.stored_settings(data_dir).get(WORKERS)
    value = section.get("site_basina") if isinstance(section, dict) else None
    low, high = SITE_LIMIT_RANGE
    return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else DEFAULT_SITE_LIMIT


def set_site_limit(data_dir, value):
    low, high = SITE_LIMIT_RANGE
    if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
        raise P.ProxyError(f"Aynı siteye aynı anda çalışan işçi sayısı {low} ile {high} arasında olmalı.")
    with _lock:
        data = stored_settings.stored_settings(data_dir)
        data[WORKERS] = {**(data.get(WORKERS) if isinstance(data.get(WORKERS), dict) else {}), "site_basina": value}
        stored_settings.write_settings(data_dir, data)
    return site_limit(data_dir)
