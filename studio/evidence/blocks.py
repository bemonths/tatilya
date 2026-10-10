"""Reusable data blocks of the evidence pack. Each block reads the latest successful run of its source (or a committed file of the
destination profile) and returns evidence rows; a block never interprets or ranks, and missing data becomes a "veri yok" row with
its reason instead of being left out.

A row: Turkish statement; value and unit in US units (temperatures in °F with °C beside them); scope; source (name, url, document or
access date, run id, SHA-256 when known); label (kaynak gerçeği, bizim hesabımız, türetilmiş, yaklaşık); sample size; the usage note
of its data type taken from the M documents; the source's short English quote when there is one.
"""
import csv
import statistics
from collections import Counter

from ..destinations import beach_neighborhoods as beach_mapping
from ..destinations import references as reference_table
from ..sources import agency_rates, bookdirect_lodging, daily_needs, restaurant_sites

LABELS = ("kaynak gerçeği", "bizim hesabımız", "türetilmiş", "yaklaşık")
MISSING = "veri yok"
MONTHS = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık")
MILE_KM = 1.609344

# Usage notes: the video-language rules of each data type's M document (quoted or closely restated; never invented here).
USAGE = {
    "neighborhoods": "Kaynak metinleri (kısa tanıtım, sayfa tanıtım metni, etiketler) yalnız iç araştırma kanıtıdır; videoda aynen kullanılmaz, "
                     "kendi cümlelerimizle ve atıfla kullanılır. (M7)",
    "beach_sourced": "'Resmî rehber' ve 'ilçe alt bölüm verisi' eşlemeleri kaynak gösterilerek söylenebilir (\"Walton County subdivision verisine "
                     "göre …\"). (M7)",
    "beach_approx": "'Komşu erişimlerle tutarlı' ve 'program türetimi' eşlemeleri yalnız yaklaşık konum bilgisidir ('Seagrove civarında' gibi); "
                    "kesin mahalle veya mahalle başına erişim sayısı iddiası yapılmaz. (M7)",
    "beach_features": "İlçe erişim listesindeki olanaklar (ADA erişimi, plaj tekerlekli sandalyesi) listenin söylediği kadarıyla ve liste "
                      "anılarak söylenir; listede olmayan bir olanak 'yok' anlamına gelmez. (M7)",
    "references": {
        "dogrulandi": "Kaynak gösterilerek söylenebilir (ör. \"Walton County'nin plaj yönetmeliğine göre …\"). Kısa alıntı yalnız doğrulama "
                      "içindir, videoda kullanılmaz. (M9)",
        "celiskili": "Ancak çelişki açıkça söylenerek ya da daha güncel bir resmî kaynakla çözülerek kullanılır. (M9)",
        "dogrulanamadi": "Videoda kullanılmaz. (M9)",
    },
    "climate": "Bu değer destinasyonun içinden ölçüm değildir; \"30A'nın iklimi\" denmez, \"30A'ya en yakın kıyı istasyonu Destin'in 1991–2020 "
               "normali\" denir. °C/mm dönüşümleri bizim hesabımızdır. (M8)",
    "water": "PCBF1 (Panama City Beach) ölçümlerinden hesaplanan aylık ortalama, kullanılan yıllar söylenerek; NOAA verisinden bizim hesabımız. "
             "İstasyonun sensöründe ölçülen su sıcaklığıdır; 30A kıyısındaki deniz suyu sıcaklığıyla aynı olduğu doğrulanmadı. (M8)",
    "storms": "Videoda kasırga rakamları 1991–2025 dönemiyle verilir ve dönem açıkça söylenir; sayım NOAA HURDAT2 verisinden bizim hesabımızdır. (M8)",
    "tdt": "Tutar o dönemin vergi oranıyla toplam tahsilattır; yıllar arası karşılaştırma için %2 payı kullanılır. Videoda tek ay rakamı "
           "söylenecekse kaynak belge birlikte anılmalı. (M9)",
    "lodging_inventory": "\"Visit South Walton'ın resmî rezervasyon sayfasında <tarih>'te yapılan aramada, <pencere> için <mahalle>'de N ilan "
                         "göründü\" biçiminde, arama tarihi ve pencere söylenerek. \"30A'da N ev var\" veya \"tam liste\" denmez. (M10)",
    "lodging_prices": "\"<Mahalle>'de kiralama şirketlerinin kendi sitelerinde, <tarih> tarihinde <pencere> haftası için sorduğumuz <n> evin, sitenin "
                      "gösterdiği vergiler ve ücretler dahil haftalık toplamının ortancası yaklaşık $X'ti\"; kaç ilandan hesaplandığı ve çeyrekler "
                      "söylenir. \"<Mahalle>'de bir hafta $X tutar\" denmez; ilan sayısı az hücrelerden mahalle karşılaştırması yapılmaz. (M11)",
    "restaurants": "\"İşletmenin kendi sitesindeki menüye göre (erişim tarihi) ana yemeklerin ortancası yaklaşık $X\" gibi; fiyat seviyesi kullanılırsa "
                   "\"bizim sınıflamamıza göre\" denir. \"En iyi\", \"en popüler\", \"en ucuz\" gibi sıralamalar ve sitede olmayan bilgi kullanılmaz; "
                   "bulunamayan bir olanak için \"yok\" denmez. (M12)",
    "daily_needs": "\"OpenStreetMap'e göre, <mahalle>'deki ilanların ortancası en yakın <yer>'e kuş uçuşu yaklaşık X mil\" gibi. \"Yürüme mesafesi\" "
                   "ya da yol ve süre iddiası kullanılmaz. (M13)",
    "traffic": "FDOT AADT bir sayım noktasındaki yıllık ortalama günlük araç sayısıdır (iki yön); \"<yer> sayım noktasında 2025 yıllık ortalaması\" "
               "denir, yolun tamamı için tek sayı söylenmez. Aylık oranlar FDOT'un haftalık mevsim faktörlerinden bizim hesabımızdır ve "
               "kategori söylenir; sıkışıklık ya da yolculuk süresi iddiası yapılmaz. (M9)",
}


class BlockData:
    """Latest successful run of each connector of one destination, read once per pack."""

    def __init__(self, db, destination_id, profile, today):
        self.db, self.destination_id, self.profile, self.today = db, destination_id, profile, today
        self.context = db.context(destination_id)
        self.regions = [{"id": r["id"], "name": r["name"]} for r in self.context.canonical_regions]
        self.names = {r["id"]: r["name"] for r in self.regions}
        self.order = [r["id"] for r in self.regions]
        self.runs = {}
        for run in db.source_runs(destination_id=destination_id):
            if run["status"] == "done":
                self.runs.setdefault(run["connector_name"], run)
        self.used = {}
        self.cache = {}

    def run(self, connector):
        found = self.runs.get(connector)
        if found:
            self.used[connector] = found
        return found

    def cached(self, key, compute):
        if key not in self.cache:
            self.cache[key] = compute()
        return self.cache[key]

    def region_ids(self, spec):
        region = spec.get("region")
        return [region] if region else list(self.order)


def number(value, digits=0):
    """US formatting: thousands with commas, a dot for decimals."""
    return f"{value:,.{digits}f}"


def source_of(run, name=None, url=None, document_date=None, sha=None):
    return {"ad": name or (run["metadata"] or {}).get("source_name") or run["connector_name"], "url": url or run["source_url"],
            "belge_tarihi": document_date, "erisim_tarihi": (run["fetched_at"] or run["finished_at"] or "")[:10] or None,
            "cekim_kimligi": run["id"], "sha256": sha or run["raw_sha256"]}


def file_source(name, url, accessed, sha, document_date=None):
    return {"ad": name, "url": url, "belge_tarihi": document_date, "erisim_tarihi": accessed, "cekim_kimligi": None, "sha256": sha}


def row(statement, value=None, unit=None, *, scope, source, label="kaynak gerçeği", sample=None, usage, metric=None, quote=None, note=None,
        english=None):
    assert label in LABELS, label
    return {"ifade": statement, "ifade_en": english, "deger": value, "birim": unit, "deger_ek": metric, "kapsam": scope, "kaynak": source,
            "etiket": label, "orneklem": sample, "kullanim_notu": usage, "alinti": quote, "not": note, "durum": "var"}


def missing(statement, reason, *, scope, usage=None, source=None):
    return {"ifade": statement, "ifade_en": None, "deger": None, "birim": None, "deger_ek": None, "kapsam": scope, "kaynak": source,
            "etiket": None, "orneklem": None, "kullanim_notu": usage, "alinti": None, "not": reason, "durum": MISSING}


def f_to_c(value):
    return (value - 32) * 5 / 9


# --- Neighborhoods and beach accesses -------------------------------------------------------------------------------------------

def neighborhoods(data, spec):
    run = data.run("south-walton-neighborhoods")
    if not run:
        return [missing("Mahalle tanımı", "Mahalle toplayıcısının başarılı bir çekimi yok.", scope="30A")]
    records = {r["canonical_region_id"]: r for r in data.db.run_records(run["id"]) or [] if r.get("canonical_region_id")}
    meta = run["metadata"] or {}
    rows = []
    if not spec.get("region"):
        excluded = meta.get("excluded_neighborhoods") or []
        if meta.get("source_record_count") is not None:
            rows.append(row("Visit South Walton'ın mahalle dizinindeki kayıt sayısı", meta["source_record_count"], "kayıt", scope="South Walton",
                            source=source_of(run), usage=USAGE["neighborhoods"]))
        rows.append(row(f"Dizinden {', '.join(excluded) or 'hiçbir kayıt'} kapsam dışı bırakıldığında kalan 30A mahallesi sayısı (kapsam kuralı bizim)",
                        len(records), "mahalle", scope="30A", source=source_of(run), label="türetilmiş", usage=USAGE["neighborhoods"],
                        note=meta.get("scope")))
    for region in data.region_ids(spec):
        record = records.get(region)
        name = data.names.get(region, region)
        if not record:
            rows.append(missing(f"{name}: mahalle dizini kaydı", "Bu çekimde mahallenin dizin kaydı yok.", scope=name))
            continue
        tags = ", ".join(record.get("tags") or []) or "etiket yok"
        quote = " ".join((record.get("summary") or "").split()[:25]) or None
        rows.append(row(f"{name}: Visit South Walton mahalle dizininde 30A mahallesi olarak listeleniyor; kaynağın etiketleri: {tags}",
                        scope=name, source=source_of(run, url=record.get("page_url")), usage=USAGE["neighborhoods"], quote=quote))
    return rows


def beach_rows(data):
    run = data.run("south-walton-beaches")
    path = getattr(data.profile, "BEACH_NEIGHBORHOOD_MAPPING", None)
    if not run or not path:
        return run, None, None
    mapping = beach_mapping.load(path, data.context.canonical_regions)
    records = {r["external_id"]: r for r in data.db.run_records(run["id"]) or []}
    return run, mapping, records


SOURCED = {"resmi_rehber", "ilce_alt_bolum", "ilce_alt_bolum_yakin"}


def beach_accesses(data, spec):
    run, mapping, records = beach_rows(data)
    if run is None or mapping is None:
        return [missing("Halka açık plaj erişimleri", "Plaj erişimi çekimi ya da plaj–mahalle eşleme dosyası yok.", scope="30A")]
    source = source_of(run)
    mapping_source = file_source(f"Plaj–mahalle eşleme dosyası ({data.profile.BEACH_NEIGHBORHOOD_MAPPING.name})", None, None, None)
    rows = []
    if not spec.get("region"):
        rows.append(row("İlçenin halka açık plaj erişimi listesinde (30A kapsamı) erişim sayısı", len(records), "erişim", scope="30A",
                        source=source, usage=USAGE["beach_sourced"]))
    for region in data.region_ids(spec):
        name = data.names.get(region, region)
        mine = [m for m in mapping if m["region_id"] == region]
        sourced = [m for m in mine if m["method"] in SOURCED]
        if not mine:
            rows.append(row(f"{name}: ilçenin halka açık erişim listesinde bu mahalleye eşlenen erişim yok", 0, "erişim", scope=name,
                            source=source, label="türetilmiş", usage=USAGE["beach_sourced"],
                            note="Topluluğun kendi misafirlerine açık özel erişimleri bu listede değildir."))
            continue
        rows.append(row(f"{name}: kaynaklı eşlemeyle (resmî rehber ya da ilçe alt bölüm verisi) bu mahalleye düşen halka açık erişim sayısı",
                        len(sourced), "erişim", scope=name, source=source, label="türetilmiş", usage=USAGE["beach_sourced"],
                        note=f"Eşleme: {mapping_source['ad']}."))
        if len(mine) != len(sourced):
            rows.append(row(f"{name}: yaklaşık eşlemelerle (komşu erişimlerle tutarlı, program türetimi) birlikte erişim sayısı", len(mine), "erişim",
                            scope=name, source=source, label="yaklaşık", usage=USAGE["beach_approx"]))
        if spec.get("region") or spec.get("list"):
            for m in mine:
                usage = USAGE["beach_sourced"] if m["method"] in SOURCED else USAGE["beach_approx"]
                rows.append(row(f"{name}: {m['beach_name']} (eşleme yöntemi: {m['method_label']})", scope=name, source=source,
                                label="türetilmiş" if m["method"] in SOURCED else "yaklaşık", usage=usage, note=m.get("note")))
    return rows


def beach_features(data, spec):
    run, mapping, records = beach_rows(data)
    if run is None or mapping is None:
        return [missing("Plaj erişimlerindeki engelli olanakları", "Plaj erişimi çekimi ya da eşleme dosyası yok.", scope="30A")]
    region_of = {m["external_id"]: m["region_id"] for m in mapping}
    wanted = set(data.region_ids(spec))
    chosen = [r for key, r in records.items() if region_of.get(key) in wanted]
    scope = data.names.get(spec["region"], spec["region"]) if spec.get("region") else "30A"
    source = source_of(run)
    ada = [r for r in chosen if any("ADA" in f for f in r.get("features") or [])]
    chairs = [r for r in chosen if any("Wheelchair" in f for f in r.get("features") or [])]
    rows = [row("İlçe listesinde ADA olanağı (park, tuvalet ya da yürüyüş yolu) yazılı erişim sayısı", len(ada), "erişim", scope=scope, source=source,
                usage=USAGE["beach_features"]),
            row("İlçe listesinde 'Beach Wheelchairs Available' yazılı erişim sayısı", len(chairs), "erişim", scope=scope, source=source,
                usage=USAGE["beach_features"])]
    for record in sorted(ada, key=lambda r: r["name"]):
        features = ", ".join(f for f in record.get("features") or [] if "ADA" in f or "Wheelchair" in f)
        rows.append(row(f"{record['name']}: {features}", scope=data.names.get(region_of.get(record["external_id"]), scope), source=source,
                        usage=USAGE["beach_features"]))
    return rows


# --- Reference table ------------------------------------------------------------------------------------------------------------

def reference_rows(data):
    def load():
        path = getattr(data.profile, "REFERENCE_TABLE", None)
        if not path:
            return [], {}
        rows = reference_table.read(path)
        translations = {}
        tr_path = getattr(data.profile, "REFERENCE_TRANSLATIONS", None)
        if tr_path and tr_path.is_file():
            with open(tr_path, encoding="utf-8-sig", newline="") as handle:
                translations = {r["id"]: r["ifade_tr"] for r in csv.DictReader(handle)}
        return rows, translations
    return data.cached("references", load)


def reference_label(row_):
    note = (row_.get("not") or "").lower()
    if "türetilmiş" in note:
        return "türetilmiş"
    if "bizim hesabımız" in note or "bizim kontrolümüz" in note or "bizim seçimimiz" in note:
        return "bizim hesabımız"
    return "kaynak gerçeği"


def references(data, spec):
    table, translations = reference_rows(data)
    if not table:
        return [missing("Referans satırları", "Bu destinasyonun referans tablosu yok.", scope="30A")]
    topics, ids, match = set(spec.get("topics") or []), list(spec.get("ids") or []), (spec.get("match") or "").lower()
    by_id = {r["id"]: r for r in table}
    chosen = [by_id[i] for i in ids if i in by_id]
    rows = [missing(f"Referans satırı: {i}", "Referans tablosunda bu satır yok.", scope="—") for i in ids if i not in by_id]
    if topics or match:
        chosen += [r for r in table if r["id"] not in ids and (not topics or r["konu"] in topics)
                   and (not match or match in f"{r['ifade']} {r['deger']}".lower())]
    chosen = [r for r in chosen if r["durum"] != "yerine_gecildi"]
    if not chosen and not rows:
        what = ", ".join(sorted(topics)) or match or "seçim"
        return [missing(f"Referans satırları ({what})", "Seçime uyan doğrulanmış satır yok.", scope=spec.get("match") or "—")]
    for ref in chosen:
        usage = USAGE["references"].get(ref["durum"], USAGE["references"]["dogrulandi"])
        notes = [ref["not"]] if ref.get("not") else []
        if ref.get("celiski_notu"):
            notes.insert(0, f"Çelişki: {ref['celiski_notu']}")
        recheck = reference_table.valid_day(ref["yeniden_kontrol_tarihi"])
        if recheck and recheck < data.today:
            notes.append(f"Yeniden kontrol tarihi ({ref['yeniden_kontrol_tarihi']}) geçti.")
        statement = translations.get(ref["id"]) or f"(Türkçe ifade yok) {ref['ifade']}"
        rows.append(row(statement, ref["deger"] or None, ref["birim"] or None, scope=ref["kapsam"], english=ref["ifade"],
                        source={"ad": ref["kaynak_adi"], "sahibi": ref["kaynak_sahibi"], "url": ref["kaynak_url"],
                                "belge_tarihi": ref["belge_tarihi"] or None, "erisim_tarihi": ref["erisim_tarihi"], "cekim_kimligi": None,
                                "sha256": ref["belge_sha256"] or None, "referans": ref["id"], "durum": ref["durum"]},
                        label=reference_label(ref), usage=usage, quote=ref["kisa_alinti"] or None, note=" ".join(notes) or None))
    return rows


# --- Climate, sea water, storms -------------------------------------------------------------------------------------------------

def climate_snapshot(data, connector):
    run = data.run(connector)
    if not run:
        return None, None
    def compute():
        with data.db.connect() as con:
            return data.db.registry.by_name(connector).read_snapshot(con, run["id"])
    return run, data.cached(connector, compute)


CLIMATE_ELEMENTS = (("MLY-TMAX-NORMAL", "ortalama en yüksek sıcaklık", "°F"), ("MLY-TMIN-NORMAL", "ortalama en düşük sıcaklık", "°F"),
                    ("MLY-PRCP-NORMAL", "ortalama yağış", "inç"), ("MLY-PRCP-AVGNDS-GE010HI", "0,10 inç ve üstü yağışlı gün ortalaması", "gün"),
                    ("MLY-TMAX-AVGNDS-GRTH090", "en yüksek sıcaklığın 90 °F'yi geçtiği gün ortalaması", "gün"))


def climate_months(data, spec):
    run, snapshot = climate_snapshot(data, "ncei-climate-normals")
    if not run or not snapshot:
        return [missing("İklim normalleri (aylık)", "İklim normalleri çekimi yok.", scope="kıyı istasyonu")]
    station = next((s for s in snapshot["stations"] if s["station_key"] == spec.get("station", "coastal")), None)
    if station is None:
        return [missing("İklim normalleri (aylık)", "Yapılandırmada kıyı referans istasyonu yok.", scope="kıyı istasyonu")]
    values = {(v["element"], v["month"]): v for v in snapshot["values"] if v["station_id"] == station["station_id"]}
    scope = f"{station['label']} ({station['station_id']}), 30A kıyı koridoruna {number(station['distance_km'] / MILE_KM, 1)} mil; 1991–2020"
    rows = []
    for element, label, unit in CLIMATE_ELEMENTS:
        for month in range(1, 13):
            value = values.get((element, month))
            name = f"{MONTHS[month - 1]}: {label}"
            if value is None or value["value"] is None:
                rows.append(missing(name, "Bu ay ve değişken için normal değeri yok.", scope=scope))
                continue
            metric = (f"{number(f_to_c(value['value']), 1)} °C" if unit == "°F" else f"{number(value['value'] * 25.4, 0)} mm" if unit == "inç" else None)
            rows.append(row(name, round(value["value"], 2), unit, scope=scope, source=source_of(run), usage=USAGE["climate"], metric=metric,
                            sample=value.get("years"), note=f"NCEI tamlık işareti: {value.get('completeness_flag') or '—'}."))
    return rows


def sea_water(data, spec):
    run, snapshot = climate_snapshot(data, "ndbc-water-temperature")
    if not run or not snapshot or not snapshot.get("summary"):
        return [missing("Deniz suyu sıcaklığı (aylık)", "Deniz suyu sıcaklığı çekimi yok.", scope="deniz istasyonu")]
    station = snapshot["stations"][0]
    months = {m["month"]: m for m in snapshot["summary"].get(station["station_id"], [])}
    scope = f"{station['label']} ({station['station_id']}), 30A kıyı koridoruna {number(station['distance_km'] / MILE_KM, 1)} mil"
    rows = []
    for month in range(1, 13):
        value = months.get(month)
        name = f"{MONTHS[month - 1]}: aylık ortalama deniz suyu sıcaklığı"
        if not value or value.get("mean_c") is None:
            rows.append(missing(name, "Bu ay için yeterli gün sayısı olan yıl yok.", scope=scope))
            continue
        fahrenheit = value["mean_c"] * 9 / 5 + 32
        rows.append(row(name, round(fahrenheit, 1), "°F", scope=f"{scope}; {value['first_year']}–{value['last_year']}", source=source_of(run),
                        label="bizim hesabımız", sample=value["years_used"], usage=USAGE["water"], metric=f"{number(value['mean_c'], 1)} °C",
                        note=f"{value['years_used']} yılın ortalaması; {value.get('excluded_year_months', 0)} yıl-ay yetersiz gün sayısı nedeniyle dışarıda."))
    return rows


def storms(data, spec):
    run, snapshot = climate_snapshot(data, "hurdat2-storm-proximity")
    if not run or not snapshot:
        return [missing("Kasırga geçişleri", "HURDAT2 çekimi yok.", scope="30A kıyı koridoru")]
    first, last, radius = int(spec.get("from", 1991)), int(spec.get("to", 2025)), float(spec.get("radius_nmi", 50))
    passages = [p for p in snapshot["passages"] if p["radius_nmi"] == radius and first <= p["season"] <= last]
    scope = f"{snapshot['corridor']['label']}, {number(radius, 0)} deniz mili ({number(radius * 1.852, 0)} km); {first}–{last}"
    source = source_of(run)
    hurricanes = {p["storm_id"]: p for p in passages if p["storm_class"] in ("HU", "MH")}
    tropical = {p["storm_id"]: p for p in passages if p["storm_class"] in ("TS", "HU", "MH")}
    rows = [row("Bu daire içinde kasırga gücünde rüzgâra ulaşan fırtına sayısı", len(hurricanes), "fırtına", scope=scope, source=source,
                label="bizim hesabımız", usage=USAGE["storms"]),
            row("Bu daire içinde en az tropikal fırtına gücüne ulaşan fırtına sayısı", len(tropical), "fırtına", scope=scope, source=source,
                label="bizim hesabımız", usage=USAGE["storms"])]
    by_month = Counter(p["first_entry_month"] for p in hurricanes.values())
    for month in sorted(by_month):
        rows.append(row(f"{MONTHS[month - 1]}: daireye ilk girişi bu ayda olan kasırga gücündeki fırtına sayısı", by_month[month], "fırtına",
                        scope=scope, source=source, label="bizim hesabımız", usage=USAGE["storms"]))
    for storm in sorted(hurricanes.values(), key=lambda p: p["season"]):
        rows.append(row(f"{storm['name'].title()} ({storm['season']}): koridora en yakın geçiş", round(storm["closest_nmi"], 1), "deniz mili",
                        scope=scope, source=source, label="bizim hesabımız", usage=USAGE["storms"], metric=f"{number(storm['closest_km'], 1)} km",
                        note=f"Daire içindeki en yüksek rüzgâr {storm['max_wind_kt']} knot; sınıf {snapshot['class_labels'].get(storm['storm_class'], storm['storm_class'])}."))
    return rows


# --- Season: tourist development tax --------------------------------------------------------------------------------------------

def tdt_season(data, spec):
    path = getattr(data.profile, "TDT_COLLECTIONS", None)
    if not path or not path.is_file():
        return [missing("Turist vergisi sezon deseni", "Bu destinasyonun turist vergisi tablosu yok.", scope="—")]
    with open(path, encoding="utf-8-sig", newline="") as handle:
        table = list(csv.DictReader(handle))
    years = {}
    for item in table:
        years.setdefault(item["mali_yil"], []).append(item)
    complete = sorted(y for y, items in years.items() if len(items) == 12)[-int(spec.get("years", 5)):]
    if not complete:
        return [missing("Turist vergisi sezon deseni", "Tam bir mali yıl yok.", scope="South Walton")]
    shares = {}
    for year in complete:
        total = sum(float(i["yuzde2_payi_usd"]) for i in years[year])
        for item in years[year]:
            shares.setdefault(int(item["ay"][5:7]), []).append(float(item["yuzde2_payi_usd"]) / total * 100)
    first = table[0]
    source = file_source("Walton County Clerk — SW TDT Collections History with Monthly FYTD Comparisons (çalışma kitabı)",
                         first["kaynak_url"], first["erisim_tarihi"], first["belge_sha256"])
    scope = f"South Walton turist vergisi bölgesi; {complete[0]}–{complete[-1]} mali yılları"
    rows = []
    for month in (10, 11, 12, 1, 2, 3, 4, 5, 6, 7, 8, 9):
        values = shares.get(month, [])
        rows.append(row(f"{MONTHS[month - 1]}: ayın mali yıl tahsilatı içindeki payı (yıllar ortalaması)", round(statistics.mean(values), 1), "%",
                        scope=scope, source=source, label="bizim hesabımız", sample=len(values), usage=USAGE["tdt"],
                        note="Ay, Clerk tablosundaki dönem ayıdır (tahsilat bir sonraki ay alınır); %2 payından hesaplandı."))
    return rows


# --- Lodging --------------------------------------------------------------------------------------------------------------------

def lodging_summary(data):
    run = data.run("bookdirect-lodging")
    if not run:
        return None, None
    def compute():
        with data.db.connect() as con:
            return bookdirect_lodging.summarize(con, run["id"], data.order)
    return run, data.cached("lodging", compute)


def agency_summary(data):
    run = data.run("agency-lodging-rates")
    if not run:
        return None, None
    def compute():
        with data.db.connect() as con:
            return agency_rates.summarize(con, run["id"], data.order, data.names)
    return run, data.cached("agency", compute)


def windows_of(summary, spec):
    months = spec.get("months")
    windows = summary["windows"]
    return [w for w in windows if not months or w["month"][5:7] in months]


def lodging_inventory(data, spec):
    run, summary = lodging_summary(data)
    if not run or not summary:
        return [missing("Book>Direct ilan sayıları", "Konaklama (Book>Direct) çekimi yok.", scope="30A")]
    searched = summary["snapshot"]["searched_on"]
    source = source_of(run)
    cells = {(c["region_id"], c["window_key"]): c for c in summary["cells"]}
    rows = []
    for region in data.region_ids(spec):
        name = data.names.get(region, region)
        for window in windows_of(summary, spec):
            cell = cells.get((region, window["window_key"]))
            label = f"{name} · {window['label']}"
            if not cell or cell["status"] != "searched":
                rows.append(missing(f"{label}: görünen ilan sayısı", "Bu pencere için arama yapılamadı.", scope=name))
                continue
            rows.append(row(f"{label}: {searched} tarihli Book>Direct aramasında görünen ilan sayısı", cell["listing_count"], "ilan", scope=name,
                            source=source, usage=USAGE["lodging_inventory"], note=summary["label"]))
            if spec.get("detail"):
                for category, count in sorted(cell["categories"].items()):
                    rows.append(row(f"{label}: '{category}' türündeki ilan sayısı", count, "ilan", scope=name, source=source,
                                    usage=USAGE["lodging_inventory"]))
                for bucket, count in cell["bedroom_buckets"].items():
                    rows.append(row(f"{label}: {bucket}{'' if bucket == 'stüdyo' else ' yatak odalı'} ilan sayısı", count, "ilan", scope=name,
                                    source=source, usage=USAGE["lodging_inventory"], sample=cell["bedrooms_known"]))
    return rows


def lodging_prices(data, spec):
    run, summary = agency_summary(data)
    if not run or not summary:
        return [missing("Kiralama şirketlerinin haftalık fiyatları", "Kiralama şirketleri fiyat çekimi yok.", scope="30A")]
    queried = summary["snapshot"]["queried_on"]
    source = source_of(run)
    cells = {(c["region_id"], c["window_key"]): c for c in summary["cells"]}
    small = int(spec.get("small_sample", 20))      # our small-sample threshold per window (M11)
    rows = []
    for region in data.region_ids(spec):
        name = data.names.get(region, region)
        for window in windows_of(summary, spec):
            cell = cells.get((region, window["window_key"]))
            label = f"{name} · {window['label']}"
            if cell and cell["priced_count"]:
                note = summary["label"]
                if cell["priced_count"] < small:
                    note = f"Küçük örnek ({cell['priced_count']} ilan); mahalle karşılaştırmasında kullanılmaz. {note}"
                rows.append(row(f"{label}: kiralama şirketlerinin sitelerinde {queried} tarihinde sorulan 7 gecelik toplam fiyatın ortancası "
                                f"(çeyrekler ${number(cell['total_q1'])}–${number(cell['total_q3'])})", round(cell["total_median"]), "USD (7 gece)",
                                scope=name, source=source, label="bizim hesabımız", sample=cell["priced_count"], usage=USAGE["lodging_prices"],
                                note=note))
            elif cell and cell["own"]["priced_count"]:
                own = cell["own"]
                rows.append(row(f"{label}: şirketin kendi envanterinden (Book>Direct'te olmayan evler) 7 gecelik toplam fiyatın ortancası "
                                f"(çeyrekler ${number(own['total_q1'])}–${number(own['total_q3'])})", round(own["total_median"]), "USD (7 gece)",
                                scope=name, source=source, label="bizim hesabımız", sample=own["priced_count"], usage=USAGE["lodging_prices"],
                                note="Bu mahallenin fiyatları tek bir şirketin kendi envanterinden; Book>Direct ilanlarıyla karşılaştırılmaz. " + summary["source_note"]))
            else:
                rows.append(missing(f"{label}: 7 gecelik toplam fiyat ortancası", "Bu hücrede fiyatı okunan ilan yok.", scope=name,
                                    usage=USAGE["lodging_prices"]))
    return rows


def lodging_bedrooms(data, spec):
    run, summary = agency_summary(data)
    if not run or not summary:
        return [missing("Oda gruplarına göre fiyat", "Kiralama şirketleri fiyat çekimi yok.", scope="30A")]
    source = source_of(run)
    cells = {(c["region_id"], c["window_key"]): c for c in summary["cells"]}
    rows = []
    for region in data.region_ids(spec):
        name = data.names.get(region, region)
        for window in windows_of(summary, spec):
            cell = cells.get((region, window["window_key"]))
            for group, stats in (cell or {}).get("bedrooms", {}).items():
                label = f"{name} · {window['label']} · {group} yatak odası"
                if not stats["count"]:
                    reason = ("Bu mahallenin fiyatları şirketin kendi envanterinden; oda grubu kırılımı yalnız Book>Direct ilanları için var."
                              if not cell["priced_count"] and cell["own"]["priced_count"] else "Bu oda grubunda fiyatı okunan ilan yok.")
                    rows.append(missing(f"{label}: 7 gecelik toplam fiyat ortancası", reason, scope=name))
                    continue
                rows.append(row(f"{label}: 7 gecelik toplam fiyatın ortancası", round(stats["median"]), "USD (7 gece)", scope=name, source=source,
                                label="bizim hesabımız", sample=stats["count"], usage=USAGE["lodging_prices"], note=summary["bedroom_note"]))
            if not cell:
                rows.append(missing(f"{name} · {window['label']}: oda gruplarına göre fiyat", "Bu hücre yok.", scope=name))
    return rows


# --- Restaurants ----------------------------------------------------------------------------------------------------------------

def restaurant_summary(data):
    run = data.run("restaurant-sites")
    if not run:
        return None, None
    def compute():
        with data.db.connect() as con:
            return restaurant_sites.summarize(con, run["id"], data.order, data.names)
    return run, data.cached("restaurants", compute)


RESERVATION = {"online": "çevrimiçi rezervasyon bağlantısı var", "phone": "telefonla rezervasyon", "not_taken": "rezervasyon almıyor",
               "unknown": "sitede bilgi yok"}


def restaurants(data, spec):
    run, summary = restaurant_summary(data)
    if not run or not summary:
        return [missing("Restoranlar", "İşletme siteleri çekimi yok.", scope="30A")]
    source = source_of(run)
    regions = {r["region_id"]: r for r in summary["regions"]}
    rows = []
    for region in data.region_ids(spec):
        name = data.names.get(region, region)
        info = regions.get(region)
        if not info or not info["restaurant_count"]:
            rows.append(missing(f"{name}: restoranlar", "Visit South Walton restoran dizininde bu mahalleye bağlı restoran yok.", scope=name))
            continue
        rows.append(row(f"{name}: Visit South Walton restoran dizininde bu mahalleye bağlı restoran sayısı", info["restaurant_count"], "restoran",
                        scope=name, source=source, usage=USAGE["restaurants"]))
        levels = info["levels"]
        rows.append(row(f"{name}: fiyat seviyesi hesaplanabilen restoran sayısı ($ {levels['$']}, $$ {levels['$$']}, $$$ {levels['$$$']}, "
                        f"$$$$ {levels['$$$$']})", sum(levels.values()), "restoran", scope=name, source=source, label="bizim hesabımız",
                        usage=USAGE["restaurants"], note=summary["level_note"]))
        rows.append(row(f"{name}: sitesinde çevrimiçi rezervasyon bağlantısı bulunan restoran sayısı", info["online_reservation"], "restoran",
                        scope=name, source=source, usage=USAGE["restaurants"]))
        rows.append(row(f"{name}: sitesinde çocuk menüsü yayımlayan restoran sayısı", info["kids_menu"], "restoran", scope=name, source=source,
                        usage=USAGE["restaurants"]))
        if spec.get("list"):
            for item in sorted((r for r in summary["restaurants"] if region in r["regions"]), key=lambda r: r["name"]):
                with data.db.connect() as con:
                    detail = restaurant_sites.restaurant_detail(con, run["id"], item["external_id"])
                hours = ((detail or {}).get("facts") or {}).get("hours") or {}
                parts = [f"seviye {item['price_level']} (bizim sınıflamamız)" if item.get("price_level") else "seviye hesaplanmadı",
                         RESERVATION.get(item.get("reservation"), item.get("reservation") or "rezervasyon bilgisi yok"),
                         "çocuk menüsü sitede var" if item.get("kids_menu") == "yes" else "çocuk menüsü sitede bulunamadı",
                         f"saatler: {hours['detail']}" if hours.get("detail") else "saatler sitede bulunamadı"]
                median = (item.get("main") or {}).get("median")
                rows.append(row(f"{item['name']}: " + "; ".join(parts), median, "USD (ana yemek ortancası)" if median else None, scope=name,
                                source=source_of(run, url=item.get("site_url")), label="bizim hesabımız" if median else "kaynak gerçeği",
                                sample=(item.get("main") or {}).get("count") or None, usage=USAGE["restaurants"],
                                note=item.get("level_reason") or (f"Site durumu: {item['site_status']}" if item.get("site_status") != "working" else None)))
    return rows


# --- Daily needs ----------------------------------------------------------------------------------------------------------------

def daily_needs_block(data, spec):
    run = data.run("openstreetmap-daily-needs")
    if not run:
        return [missing("Günlük ihtiyaç mesafeleri", "Günlük ihtiyaç çekimi yok.", scope="30A")]
    def compute():
        with data.db.connect() as con:
            return daily_needs.summarize(con, run["id"], data.order, data.names)
    summary = data.cached("daily_needs", compute)
    if not summary:
        return [missing("Günlük ihtiyaç mesafeleri", "Bu çekimin özeti okunamadı.", scope="30A")]
    labels = summary["labels"]
    wanted = spec.get("categories") or list(labels)
    source = source_of(run)
    regions = {r["region_id"]: r for r in summary["regions"]}
    rows = []
    for region in data.region_ids(spec):
        name = data.names.get(region, region)
        info = regions.get(region)
        for key in wanted:
            label = labels.get(key)
            if label is None:
                rows.append(missing(f"{name}: en yakın '{key}' mesafesi", "Bu çekimde bu kategori yok (kategori ayrımından önceki çekim).", scope=name))
                continue
            measure = (info or {}).get("measures", {}).get(key)
            if not measure or measure["median_mi"] is None:
                rows.append(missing(f"{name}: en yakın {label.lower()} için kuş uçuşu mesafe ortancası", "Bu mahallede ölçülen ilan ya da nokta yok.",
                                    scope=name, usage=USAGE["daily_needs"]))
                continue
            share = measure["within_1mi_share"]
            rows.append(row(f"{name}: ilanların en yakın {label.lower()} noktasına kuş uçuşu mesafe ortancası (ilanların %{number(share * 100, 0)}'i "
                            f"1 mil içinde)", measure["median_mi"], "mil", scope=name, source=source, label="bizim hesabımız",
                            sample=measure["count"], usage=USAGE["daily_needs"], metric=f"{number(measure['median_km'], 2)} km",
                            note=summary["note"] + (f" {summary['beach_note']}" if key == "beach" else "")))
    for key in spec.get("list_points") or []:
        points = [p for p in summary["points"] if p["category_key"] == key]
        if not points:
            rows.append(missing(f"{labels.get(key, key)}: nokta listesi", "Bu çekimde bu kategoride nokta yok.", scope="bölge kutusu"))
        for point in sorted(points, key=lambda p: p["name"] or ""):
            rows.append(row(f"{labels.get(key, key)}: {point['name'] or 'adı yok'}" + (f", {point['address']}" if point.get("address") else ""),
                            scope="bölge kutusu", source=source_of(run, name=point["source"], url=point.get("source_url")),
                            usage=USAGE["daily_needs"], note=point.get("note")))
    return rows


# --- Traffic --------------------------------------------------------------------------------------------------------------------

def traffic(data, spec):
    path = getattr(data.profile, "TRAFFIC_TABLE", None)
    if not path or not path.is_file():
        return [missing("Trafik sayıları", "Bu destinasyonun trafik tablosu yok.", scope="—")]
    with open(path, encoding="utf-8-sig", newline="") as handle:
        table = list(csv.DictReader(handle))
    categories, kinds = spec.get("categories"), spec.get("kinds") or ["aadt", "season"]
    rows = []
    for item in table:
        if (item["tur"] == "AADT") != ("aadt" in kinds) and not ("aadt" in kinds and "season" in kinds):
            continue
        if item["tur"] != "AADT" and categories and item["kategori"].split()[0] not in categories:
            continue
        source = {"ad": item["kaynak_adi"], "sahibi": item["kaynak_sahibi"], "url": item["kaynak_url"], "belge_tarihi": item["belge_tarihi"] or None,
                  "erisim_tarihi": item["erisim_tarihi"], "cekim_kimligi": None, "sha256": item["belge_sha256"], "referans": item["id"]}
        if item["tur"] == "AADT":
            statement = f"{item['yol']}, sayım noktası {item['sayim_noktasi']} ({item['aciklama']}): {item['yil']} yıllık ortalama günlük trafik"
            rows.append(row(statement, int(item["deger"]), "araç/gün (iki yön)", scope=item["yol"], source=source, label=item["etiket"],
                            usage=USAGE["traffic"], note=item["not"]))
        elif item["ay"]:
            month = int(item["ay"])
            statement = f"{item['aciklama']} · {MONTHS[month - 1]}: trafiğin yıllık ortalamaya oranı ({item['yil']} haftalık faktörlerden)"
            rows.append(row(statement, float(item["deger"]), "oran", scope="Walton County", source=source, label=item["etiket"],
                            usage=USAGE["traffic"], note=item["not"]))
        else:
            rows.append(row(f"{item['aciklama']}: FDOT'un yoğun sezon (peak season) haftaları {item['deger']}", scope="Walton County",
                            source=source, label=item["etiket"], usage=USAGE["traffic"], note=item["not"]))
    return rows


BLOCKS = {
    "neighborhoods": neighborhoods,
    "beach_accesses": beach_accesses,
    "beach_features": beach_features,
    "references": references,
    "climate_months": climate_months,
    "sea_water": sea_water,
    "storms": storms,
    "tdt_season": tdt_season,
    "lodging_inventory": lodging_inventory,
    "lodging_prices": lodging_prices,
    "lodging_bedrooms": lodging_bedrooms,
    "restaurants": restaurants,
    "daily_needs": daily_needs_block,
    "traffic": traffic,
}
