"""Average domestic airline itinerary fares by origin airport, from the U.S. Bureau of Transportation Statistics (GÖREV-20;
docs/M20-UCAK-BILETI.md).

Generic core: the airports and the number of quarters come from the destination configuration in SQLite
(`destination_airfare_sources`). The source is the BTS page "Average Domestic Airline Itinerary Fares" (TranStats): its first answer
shows the latest published quarter; earlier quarters are asked with the page's own form (quarter, year, "Submit"). Every answer is
kept with SHA-256.

What a value is, in the source's words: the average fare of domestic itineraries **originating at the airport** (the table is "By
Origin City"), round-trip or one-way for which no return is purchased, total ticket value with taxes and fees charged at purchase,
without baggage and other fees; from the Origin & Destination Survey (a 10% sample of tickets). It is not the price of a ticket to
the airport from any particular city, and nothing here turns it into one.
"""
import hashlib
import html as html_lib
import json
import re
from datetime import datetime, timezone

import httpx

from .base import CollectionResult, SourceError
from .climate_http import USER_AGENT, check, make_client, pause

CONNECTOR_VERSION = "bts-airport-fares/1"
SOURCE_URL = "https://www.transtats.bts.gov/AverageFare/"
HOST = "www.transtats.bts.gov"
REQUEST_GAP = 8.0
MAX_BYTES = 5_000_000
LABEL = ("ABD Ulaştırma İstatistikleri Bürosu (BTS), Average Domestic Airline Itinerary Fares: havalimanından başlayan iç hat "
         "yolculuklarının (gidiş-dönüş ya da dönüşü alınmamış tek yön) ortalama bilet ücreti; satın alma anındaki vergi ve ücretler dahil, "
         "bagaj gibi sonradan ödenen ücretler hariç; biletlerin %10'luk örneğinden")
_TITLE = re.compile(r'<span id="lblTitle">(.*?)</span>', re.S)
_PERIOD = re.compile(r"By Origin City for Q([1-4]) (\d{4})")
_RANK = re.compile(r"Ranked by ([^<]+)")
_HIDDEN = re.compile(r'<input type="hidden" name="([^"]+)" id="[^"]*" value="([^"]*)"')
_GRID = re.compile(r'<table[^>]*id="GridView1"[^>]*>(.*?)</table>', re.S)
_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S)
_TAG = re.compile(r"<[^>]+>")
_NOTE = re.compile(r'<span[^>]*class="info-label"[^>]*>\s*(Source|Itinerary Fare):(.*?)</span>', re.S | re.I)


def text_of(fragment):
    return " ".join(html_lib.unescape(_TAG.sub(" ", fragment)).split())


def number(text):
    try:
        return float(text.replace(",", "").replace("$", ""))
    except ValueError:
        return None


def parse(page):
    """{year, quarter, title, rank_basis, adjusted_base, rows {code: {...}}, notes {...}, form {...}} of one answer of the page."""
    title = _TITLE.search(page)
    period = _PERIOD.search(text_of(title.group(1))) if title else None
    grid = _GRID.search(page)
    if not title or not period or not grid:
        raise SourceError("BTS sayfası beklenen biçimde değil (başlık ya da tablo bulunamadı).")
    title_text = text_of(title.group(1))
    rank = _RANK.search(title_text)
    rows, header = {}, None
    for found in _ROW.finditer(grid.group(1)):
        cells = [text_of(c) for c in _CELL.findall(found.group(1))]
        if header is None:
            header = cells
            continue
        if len(cells) < 6 or not re.fullmatch(r"[A-Z0-9]{3}", cells[1]):
            continue
        rows[cells[1]] = {"passenger_rank": int(cells[0]) if cells[0].isdigit() else None, "city_name": cells[2] or None, "state": cells[3] or None,
                          "average_fare": number(cells[4]), "adjusted_fare": number(cells[5])}
    if header is None or len(header) < 6 or "Average Fare" not in header[4] or not rows:
        raise SourceError("BTS tablosunun sütunları beklenen sırada değil; değer okunmadı.")
    base = re.search(r"Base Quarter:\s*(Q[1-4]-\d{4})", header[5])
    notes = {name.lower(): text_of(body).lstrip(": ").strip() for name, body in _NOTE.findall(page)}
    return {"year": int(period.group(2)), "quarter": int(period.group(1)), "title": title_text, "rank_basis": rank.group(1).strip() if rank else None,
            "adjusted_base": base.group(1) if base else None, "rows": rows, "notes": notes, "form": dict(_HIDDEN.findall(page))}


def earlier(year, quarter, steps):
    index = year * 4 + quarter - 1 - steps
    return index // 4, index % 4 + 1


class Pages:
    """The page's first answer and its own form, sequential and spaced; every answer kept with a manifest."""

    def __init__(self, client, manifest_path, canceled, gap=REQUEST_GAP):
        self.client, self.path, self.canceled, self.gap = client, manifest_path, canceled, gap
        self.manifest = {"connector": CONNECTOR_VERSION, "responses": []}
        self.asked = False

    def request(self, note, form=None):
        check(self.canceled)
        if self.asked:
            pause(self.gap, self.canceled)
        self.asked = True
        try:
            if form is None:
                response = self.client.get(SOURCE_URL, headers={"User-Agent": USER_AGENT}, follow_redirects=False)
            else:
                response = self.client.post(SOURCE_URL, data=form, headers={"User-Agent": USER_AGENT}, follow_redirects=False)
        except (httpx.NetworkError, httpx.TimeoutException) as exc:
            raise SourceError("BTS kaynağına bağlanılamadı veya zaman aşımı oluştu.") from exc
        except httpx.HTTPError as exc:
            raise SourceError("BTS HTTP yanıtı geçersiz.") from exc
        body = response.content
        if len(body) > MAX_BYTES:
            raise SourceError("BTS yanıtı boyut sınırını aştı.")
        sequence = len(self.manifest["responses"]) + 1
        relative = f"responses/{sequence:04d}.html"
        target = self.path.parent / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        stamp = datetime.now(timezone.utc).isoformat()
        digest = hashlib.sha256(body).hexdigest()
        self.manifest["fetched_at"] = stamp
        self.manifest["responses"].append({
            "sequence": sequence, "note": note, "method": "GET" if form is None else "POST", "requested_url": SOURCE_URL,
            "request_form": {k: v for k, v in (form or {}).items() if not k.startswith("__")} or None, "status": response.status_code,
            "content_type": response.headers.get("content-type"), "fetched_at": stamp, "raw_file": relative, "raw_sha256": digest, "bytes": len(body)})
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)
        if response.status_code in (403, 429):
            raise SourceError(f"BTS sayfası isteği reddetti (HTTP {response.status_code}); toplama bırakıldı.")
        if response.status_code != 200 or "text/html" not in (response.headers.get("content-type") or ""):
            raise SourceError(f"BTS sayfası okunamadı (HTTP {response.status_code}).")
        return body.decode("utf-8", errors="replace"), digest


def collect(raw_path, progress, canceled, *, config, client=None, today=None, gap=REQUEST_GAP):
    if not config or not config.get("airports"):
        raise SourceError("Bu destinasyon için uçak bileti havalimanları yapılandırılmamış.")
    airports, quarters = config["airports"], int(config.get("quarters") or 5)
    owns = client is None
    client = client or make_client()
    pages = Pages(client, raw_path, canceled, gap)
    try:
        progress(5, "BTS sayfası okunuyor: son yayımlanan çeyrek.")
        page, digest = pages.request("son yayımlanan çeyrek")
        latest = parse(page)
        answers = [(latest, digest)]
        for step in range(1, quarters):
            year, quarter = earlier(latest["year"], latest["quarter"], step)
            progress(5 + int(85 * step / quarters), f"BTS sayfası okunuyor: {year} Q{quarter}.")
            form = {**answers[-1][0]["form"], "dlstQuarter": str(quarter), "dlstYear": str(year), "btnSubmit": "Submit"}
            page, digest = pages.request(f"{year} Q{quarter}", form)
            answer = parse(page)
            if (answer["year"], answer["quarter"]) != (year, quarter):
                raise SourceError(f"BTS sayfası istenen dönemi ({year} Q{quarter}) döndürmedi; değer kaydedilmedi.")
            answers.append((answer, digest))
        records = []
        for answer, digest in answers:
            for airport in airports:
                row = answer["rows"].get(airport["code"])
                records.append({"airport_code": airport["code"], "airport_label": airport.get("label") or airport["code"], "year": answer["year"],
                                "quarter": answer["quarter"], "listed": int(row is not None), "city_name": row and row["city_name"],
                                "state": row and row["state"], "passenger_rank": row and row["passenger_rank"], "rank_basis": answer["rank_basis"],
                                "average_fare": row and row["average_fare"], "adjusted_fare": row and row["adjusted_fare"],
                                "adjusted_base": answer["adjusted_base"], "title": answer["title"], "raw_sha256": digest})
        today = (today or datetime.now(timezone.utc).date()).isoformat()
        snapshot = {"queried_on": today, "request_count": len(pages.manifest["responses"]), "latest_year": latest["year"],
                    "latest_quarter": latest["quarter"], "quarters": quarters, "airports": airports,
                    "source_note": latest["notes"].get("source"), "fare_note": latest["notes"].get("itinerary fare")}
        metadata = {"latest": f"{latest['year']} Q{latest['quarter']}", "quarters": [f"{a['year']} Q{a['quarter']}" for a, _ in answers],
                    "airports": [a["code"] for a in airports], "request_count": snapshot["request_count"],
                    "source_note": snapshot["source_note"], "fare_note": snapshot["fare_note"]}
        progress(97, f"{len(records)} havalimanı × çeyrek değeri kaydediliyor.")
        return CollectionResult(records, len(records), 0, f"{latest['year']} Q{latest['quarter']}", metadata, {"snapshot": snapshot})
    finally:
        if owns:
            client.close()


def summarize(con, run_id):
    """One run: per airport the quarters newest first, the same quarter a year earlier and the change between them (our
    calculation, nominal dollars), with the source's own notes."""
    snapshot = con.execute("SELECT * FROM airfare_snapshots WHERE run_id=?", (run_id,)).fetchone()
    if not snapshot:
        return None
    snapshot = {**dict(snapshot), "airports": json.loads(snapshot["airports"])}
    rows = [dict(r) for r in con.execute("SELECT * FROM airfare_quarters WHERE run_id=? ORDER BY airport_code, year DESC, quarter DESC", (run_id,))]
    airports = []
    for airport in snapshot["airports"]:
        mine = [r for r in rows if r["airport_code"] == airport["code"]]
        latest = next((r for r in mine if (r["year"], r["quarter"]) == (snapshot["latest_year"], snapshot["latest_quarter"])), None)
        before = next((r for r in mine if (r["year"], r["quarter"]) == (snapshot["latest_year"] - 1, snapshot["latest_quarter"])), None)
        change = None
        if latest and before and latest["average_fare"] and before["average_fare"]:
            change = {"amount": round(latest["average_fare"] - before["average_fare"], 2),
                      "percent": round((latest["average_fare"] - before["average_fare"]) / before["average_fare"] * 100, 1)}
        airports.append({"code": airport["code"], "label": airport.get("label") or airport["code"], "quarters": mine, "latest": latest,
                         "year_before": before, "change": change})
    return {"snapshot": snapshot, "airports": airports, "label": LABEL, "source_url": SOURCE_URL,
            "note": ("Değer, o havalimanından BAŞLAYAN iç hat yolculuklarının ortalamasıdır (kaynağın tablosu \"By Origin City\"); belirli bir "
                     "şehirden o havalimanına bilet fiyatı değildir. Bir yıl önceki aynı çeyrekle fark bizim hesabımızdır (nominal dolar).")}


class AirfareConnector:
    name = "bts-airport-fares"
    version = CONNECTOR_VERSION
    raw_filename = "manifest.json"
    method = "HTML"
    diff_enabled = False
    diff_reason = "Çeyreklik ortalamalar tarihli okumalardır; her sürüm kendi çeyrekleriyle okunur."

    def supports(self, source):
        return (source.get("url") or "") == SOURCE_URL

    def collect(self, source, raw_path, progress, canceled, *, context):
        return collect(raw_path, progress, canceled, config=context.airfare)

    def store_records(self, con, run_id, records, related=None):
        snapshot = related["snapshot"]
        con.execute("""INSERT INTO airfare_snapshots (run_id,queried_on,request_count,latest_year,latest_quarter,quarters,airports,source_note,fare_note)
            VALUES (?,?,?,?,?,?,?,?,?)""", (run_id, snapshot["queried_on"], snapshot["request_count"], snapshot["latest_year"], snapshot["latest_quarter"],
                                            snapshot["quarters"], json.dumps(snapshot["airports"], ensure_ascii=False), snapshot["source_note"],
                                            snapshot["fare_note"]))
        con.executemany("""INSERT INTO airfare_quarters (run_id,airport_code,year,quarter,listed,city_name,state,passenger_rank,rank_basis,average_fare,
            adjusted_fare,adjusted_base,title,raw_sha256) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [(run_id, r["airport_code"], r["year"], r["quarter"], r["listed"], r["city_name"], r["state"], r["passenger_rank"], r["rank_basis"],
              r["average_fare"], r["adjusted_fare"], r["adjusted_base"], r["title"], r["raw_sha256"]) for r in records])

    def read_records(self, con, run_id):
        return [dict(r) for r in con.execute("SELECT * FROM airfare_quarters WHERE run_id=? ORDER BY airport_code, year DESC, quarter DESC", (run_id,))]

    def comparison_value(self, record):
        raise NotImplementedError("Airfare diff is disabled.")
