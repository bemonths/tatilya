"""Schema 17 → 18 (GÖREV-16, Adım 3b): the region-blocked domains.

`region_blocked_hosts`: a domain that serves only visitors inside the United States (studio/sources/page_kinds.py "bolge_engeli").
Such a domain is read only through the user's US proxy (studio/proxy.py), never through the extension; without a proxy it is skipped
and written down. `added_by` is "program" (the program saw the region block and added it, with the date and the page's title or the
words that made it one) or "kullanici" (added in Settings). The user may remove any row.

The first rows come from the raw copies the extension already made (`<data>/raw/eklenti/<date>/*.json` and the page beside it): every
record whose page is a region block (its title, its words or a redirect to a geo-block address) puts its domain on the list with that
record's date. Nothing else changes.
"""
import json
from pathlib import Path

from .migrations import execute_schema
from .sources import page_kinds

SCHEMA = """
    CREATE TABLE region_blocked_hosts (
        host TEXT PRIMARY KEY CHECK(length(host) > 0), title TEXT, url TEXT, evidence TEXT,
        added_by TEXT NOT NULL CHECK(added_by IN ('program','kullanici')),
        first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL
    );
"""


def raw_region_blocks(data_dir):
    """[(host, title, url, evidence, seen_at)] from the extension's raw records under `<data_dir>/raw/eklenti/`."""
    from .proxy import LOCAL_HOSTS, host_key
    found = []
    folder = Path(data_dir) / "raw" / "eklenti" if data_dir else None
    if folder is None or not folder.is_dir():
        return found
    for record_path in sorted(folder.glob("*/*.json")):
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(record, dict) or not isinstance(record.get("adres"), str):
            continue
        page_path = record_path.with_suffix(".html")
        page = page_path.read_text(encoding="utf-8", errors="replace") if page_path.is_file() else ""
        final = record.get("son_adres") or record["adres"]
        note = str(record.get("not") or "")
        title = str(record.get("baslik") or "")
        redirected = next((part for part in note.split('"') if page_kinds.REGION_ADDRESS.search(part) and "//" in part), None)
        kind = page_kinds.classify(page, title, redirected or final, record.get("http_durumu"))
        if kind != "bolge_engeli":
            continue
        host = host_key(record["adres"])
        if not host or host in LOCAL_HOSTS:
            continue
        evidence = page_kinds.evidence(page, title, redirected or final)
        if redirected:
            evidence = f"{host_key(redirected)} adresine yönlendi"
        found.append((host, title or None, record["adres"], evidence, record.get("okundu") or None))
    return found


def upgrade_v18(con, data_dir=None):
    from .proxy import mark, now_iso
    execute_schema(con, SCHEMA)
    for host, title, url, evidence, seen in raw_region_blocks(data_dir):
        mark(con, host, title=title, url=url, evidence=evidence, added_by="program", when=seen or now_iso())
    if con.execute("PRAGMA foreign_key_check").fetchone():
        raise RuntimeError("v18 migration ilişki bütünlüğü kontrolü başarısız oldu.")
    con.execute("PRAGMA user_version=18")
