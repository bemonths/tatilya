"""30A plaj erişimi -> mahalle eşleme dosyasını üretir (v3). Geliştirme aracıdır; uygulama bunu çağırmaz.

Eşleme dosyası bir kez üretilip commit edilir (studio/destinations/thirty_a_beach_neighborhoods.csv);
uygulama yalnız okur. Yöntem, kısıt ve doğrulama: docs/M7-MAHALLE-VERISI.md.

Yöntem sırası (GÖREV-05 yönetici kararı):
1. resmi_rehber: GÖREV-02 önizlemesindeki dolu satırlar olduğu gibi alınır.
2. ilce_alt_bolum: nokta, ad tablosunda bir mahalleye bağlanan bir Walton County alt bölüm poligonunun içinde.
3. ilce_alt_bolum_yakin: nokta böyle bir poligonun içinde değil; ad tablosunda bir mahalleye bağlanan poligonlar
   arasında 30 m veya daha yakın olan(lar) tek bir mahalle gösteriyor. Noktanın tabloda olmayan bir poligonun
   içinde olması bu kuralı engellemez. 30 m içinde farklı mahalleler varsa sonuç yok; 30–75 m kullanılmaz.
4. komsu_tutarliligi: ilk üç yöntemle atanamayan erişimin boylam sırasına göre batısındaki ve doğusundaki en yakın
   kaynağa dayalı erişim (yöntemi 1, 2 veya 3) aynı mahalledeyse o mahalle.
5. turetim_en_yakin_mahalle_noktasi: ilk dördü sonuç vermezse mahalle temsilî noktalarına boylam farkıyla en yakın
   mahalle (kaynak = mahalle çekiminin run kimliği); atanabilir en yakın iki aday arasındaki fark 0.003°'den küçükse
   belirsiz=evet.
Kısıt: resmî rehberin halka açık plaj erişimi olmadığını söylediği Alys Beach ve Rosemary Beach'e hiçbir yöntem
erişim atamaz. İlçe verisi bir erişimi bu iki mahallenin alt bölümüne bağlarsa satır "resmî rehberle çelişki"
notuyla işaretlenir ve sonraki yöntemlere geçilir.

Kullanım (depo kökünden; veritabanı salt okunur açılır, ağa yalnız --ilce-sorgula ile çıkılır):
  .venv\\Scripts\\python.exe -X utf8 -m tools.plaj_mahalle_esleme --data-dir <veri-klasörü> ^
      --dogrulama <dogrulama.csv> [--onceki <eski-esleme.csv> --fark <fark.csv>]
  İlçe sorgusunu yenilemek için: --ilce-sorgula --ham <ham-yanit-klasoru> [--yalniz-sorgu]
Seçenekler: --plaj-run, --mahalle-run (varsayılan: 30A'daki son başarılı çekimler), --resmi, --cikti,
--alt-bolum (sorgu sonuçları CSV'si), --alt-bolum-tablosu (alt bölüm adı -> mahalle tablosu).
"""
import argparse
import csv
import json
import math
import sqlite3
import time
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

import httpx

from studio.destinations.beach_neighborhoods import (COLUMNS, METHOD_COUNTY, METHOD_COUNTY_ADJACENT, METHOD_DERIVED,
                                                     METHOD_LABELS, METHOD_NEIGHBORS, METHOD_OFFICIAL)
from studio.destinations.thirty_a import (BEACH_NEIGHBORHOOD_MAPPING, BEACH_SUBDIVISIONS, COUNTY_SUBDIVISION_LAYER,
                                          METADATA, REGIONS, SUBDIVISION_NEIGHBORHOODS)

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_CSV = ROOT / "docs" / "gorevler" / "GOREV-02" / "plaj-mahalle-onizleme.csv"
OFFICIAL_URL = "https://www.visitsouthwalton.com/blog/guide-beach-parking-transportation/"
OFFICIAL_DATE = "2023-05-04"
OFFICIAL_SOURCE = f"{OFFICIAL_URL} (yayın {OFFICIAL_DATE})"
OFFICIAL_PREFIX = f"VSW Guide to Beach Parking and Transportation (yayın {OFFICIAL_DATE}); "
# The official guide says "No Public Beach Access" under these neighborhood headings.
NO_PUBLIC_ACCESS = ("alys-beach", "rosemary-beach")
AMBIGUITY_DEGREES = 0.003
REGION_NAMES = dict(REGIONS)
SOURCED_METHODS = (METHOD_OFFICIAL, METHOD_COUNTY, METHOD_COUNTY_ADJACENT)
SUBDIVISION_COLUMNS = ("external_id", "alt_bolum_adi", "alt_bolum_numarasi", "poligon_kimligi", "iliski", "mesafe_m",
                       "katman_url", "sorgu_zamani")
TABLE_COLUMNS = ("alt_bolum_adi", "bolge_id", "gerekce")
RELATIONS = ("iceride", "yakin", "sonucsuz")
# Polygons up to NEAR_METERS are recorded; only those up to ADJACENT_METERS can assign (rule 3).
NEAR_METERS, ADJACENT_METERS, SEARCH_METERS = 75, 30, 100
QUERY_GAP = 0.25
USER_AGENT = "30AStudio/0.8 (+https://github.com/bemonths/tatilya)"
VALIDATION_COLUMNS = ("external_id", "plaj_adi", "resmi_bolge_id", "ilce_bolge_id", "ilce_sonuc", "ilce_yakin_bolge_id",
                      "ilce_yakin_sonuc", "komsu_bolge_id", "komsu_sonuc", "turetilen_bolge_id", "turetme_sonuc",
                      "zincir_yontem", "zincir_bolge_id", "zincir_sonuc")
DIFF_COLUMNS = ("external_id", "plaj_adi", "onceki_bolge_id", "onceki_yontem", "yeni_bolge_id", "yeni_yontem", "degisen")


# --- Program türetimi -----------------------------------------------------------------------------

def nearest(longitude, neighborhoods):
    """Nearest assignable neighborhood point by longitude difference, with the next candidate and skipped ones."""
    distance = lambda hood: abs(hood["longitude"] - longitude)
    ranked = sorted(neighborhoods, key=lambda hood: (distance(hood), hood["longitude"]))
    allowed = [hood for hood in ranked if hood["region_id"] not in NO_PUBLIC_ACCESS]
    if len(allowed) < 2:
        raise SystemExit("Türetme için en az iki atanabilir mahalle noktası gerekir.")
    chosen, runner_up = allowed[0], allowed[1]
    return {"chosen": chosen, "distance": distance(chosen), "runner_up": runner_up, "runner_up_distance": distance(runner_up),
            "skipped": [(hood, distance(hood)) for hood in ranked[:ranked.index(chosen)]],
            "ambiguous": distance(runner_up) - distance(chosen) < AMBIGUITY_DEGREES}


def derived_note(result):
    name = lambda hood: REGION_NAMES[hood["region_id"]]
    parts = [f"En yakın temsilî nokta: {name(result['chosen'])} (boylam farkı {result['distance']:.4f}°); "
             f"sonraki aday: {name(result['runner_up'])} ({result['runner_up_distance']:.4f}°)."]
    for hood, gap in result["skipped"]:
        parts.append(f"Daha yakın {name(hood)} ({gap:.4f}°) atlandı: resmî rehber ({OFFICIAL_DATE}) burada halka açık plaj erişimi olmadığını söylüyor.")
    if result["ambiguous"]:
        parts.append(f"İki aday arasındaki fark {result['runner_up_distance'] - result['distance']:.4f}° ({AMBIGUITY_DEGREES}° altında).")
    return " ".join(parts)


# --- İlçe alt bölüm verisi ------------------------------------------------------------------------

def read_subdivisions(path):
    """Reviewed per-access query results grouped by beach id (all polygons inside and within NEAR_METERS)."""
    groups = {}
    with open(path, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != SUBDIVISION_COLUMNS:
            raise SystemExit("Alt bölüm sonuç dosyasının sütunları beklenen biçimde değil.")
        for row in reader:
            relation = row["iliski"]
            if relation not in RELATIONS:
                raise SystemExit(f"Alt bölüm sonucunda tanınmayan ilişki: {relation}")
            if relation == "sonucsuz":
                if any(row[key] for key in ("alt_bolum_adi", "alt_bolum_numarasi", "poligon_kimligi", "mesafe_m")):
                    raise SystemExit(f"Sonuçsuz satırda poligon bilgisi var: {row['external_id']}")
            else:
                try:
                    distance = float(row["mesafe_m"])
                except ValueError:
                    raise SystemExit(f"Alt bölüm mesafesi okunamadı: {row['external_id']}") from None
                if not row["poligon_kimligi"] or distance < 0 or distance > NEAR_METERS or (relation == "iceride" and distance != 0):
                    raise SystemExit(f"Alt bölüm sonucu tutarsız: {row['external_id']}")
            groups.setdefault(row["external_id"], []).append(row)
    for identifier, rows in groups.items():
        if len(rows) > 1 and any(row["iliski"] == "sonucsuz" for row in rows):
            raise SystemExit(f"Sonuçsuz erişimde başka satır var: {identifier}")
    return groups


def read_name_table(path):
    """Explicit subdivision name -> canonical region table; exact source spellings only."""
    region_ids = {identifier for identifier, _ in REGIONS}
    table = {}
    with open(path, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != TABLE_COLUMNS:
            raise SystemExit("Alt bölüm adı tablosunun sütunları beklenen biçimde değil.")
        for row in reader:
            name = row["alt_bolum_adi"]
            if not name or name in table:
                raise SystemExit(f"Alt bölüm adı tablosunda boş veya yinelenen ad: {name!r}")
            if row["bolge_id"] not in region_ids:
                raise SystemExit(f"Alt bölüm adı tablosunda tanınmayan bölge: {row['bolge_id']}")
            if not row["gerekce"].strip():
                raise SystemExit(f"Alt bölüm adı tablosunda gerekçe boş: {name}")
            table[name] = row["bolge_id"]
    return table


def decide(rows, table):
    """Status, region and the rows behind it for a set of candidate polygons."""
    named = [row for row in rows if row["alt_bolum_adi"] in table]
    regions = sorted({table[row["alt_bolum_adi"]] for row in named})
    if not named:
        return {"status": "tabloda_yok" if rows else "yok", "region_id": None, "rows": rows, "regions": []}
    if len(regions) > 1:
        return {"status": "karisik", "region_id": None, "rows": named, "regions": regions}
    if regions[0] in NO_PUBLIC_ACCESS:
        return {"status": "celiski", "region_id": None, "rows": named, "regions": regions}
    return {"status": "atandi", "region_id": regions[0], "rows": named, "regions": regions}


def inside_result(rows, table):
    """Rule 2: polygons that contain the point."""
    if not rows:
        return {"status": "sorgu_yok", "region_id": None, "rows": [], "regions": []}
    return decide([row for row in rows if row["iliski"] == "iceride"], table)


def adjacent_result(rows, table, inside):
    """Rule 3: only when the point is not inside a polygon whose name is in the table; mapped polygons <= 30 m."""
    if inside["status"] in ("atandi", "karisik", "celiski"):
        return {"status": "uygulanmaz", "region_id": None, "rows": [], "regions": []}
    near = sorted((row for row in rows if row["iliski"] == "yakin" and float(row["mesafe_m"]) <= ADJACENT_METERS),
                  key=lambda row: (float(row["mesafe_m"]), row["poligon_kimligi"]))
    result = decide(near, table)
    if result["status"] == "tabloda_yok":
        result["status"] = "yok"
    return result


def label(rows):
    return ", ".join(f"'{row['alt_bolum_adi'] or 'adsız'}' (alt bölüm no {row['alt_bolum_numarasi'] or '-'}, OBJECTID {row['poligon_kimligi']})"
                     for row in rows)


def county_notes(rows, inside, adjacent, table):
    """Plain-language notes on the county evidence of one access."""
    notes = []
    if inside["status"] == "sorgu_yok":
        return ["İlçe alt bölüm sorgusu bu erişim için yapılmadı."]
    unnamed_inside = [row for row in rows if row["iliski"] == "iceride" and row["alt_bolum_adi"] not in table]
    if inside["status"] == "atandi":
        notes.append(f"Walton County Subdivision Boundaries: erişim noktası {label(inside['rows'])} içinde; ad tablosu: {REGION_NAMES[inside['region_id']]}.")
    elif inside["status"] == "karisik":
        notes.append(f"İlçe verisi: nokta {label(inside['rows'])} içinde; adlar farklı mahalleler gösteriyor ({', '.join(REGION_NAMES[r] for r in inside['regions'])}).")
    elif inside["status"] == "celiski":
        region = REGION_NAMES[inside["regions"][0]]
        notes.append(f"Resmî rehberle çelişki: ilçe verisi erişimi {label(inside['rows'])} içine düşürüyor ({region}); resmî rehber ({OFFICIAL_DATE}) "
                     f"{region}'te halka açık plaj erişimi olmadığını söylüyor. Bu mahalleye atanmadı.")
    if unnamed_inside and inside["status"] != "karisik":
        notes.append(f"Nokta adı tabloda olmayan {label(unnamed_inside)} içinde.")
    if adjacent["status"] == "atandi":
        distance = adjacent["rows"][0]["mesafe_m"]
        notes.append(f"Walton County Subdivision Boundaries: erişim noktası {label(adjacent['rows'][:1])} poligonuna {distance} m "
                     f"(≤ {ADJACENT_METERS} m); ad tablosu: {REGION_NAMES[adjacent['region_id']]}.")
    elif adjacent["status"] == "karisik":
        notes.append(f"İlçe verisi: {ADJACENT_METERS} m içinde farklı mahallelere bağlanan poligonlar var: {label(adjacent['rows'])} "
                     f"({', '.join(REGION_NAMES[r] for r in adjacent['regions'])}); bitişik kural sonuç vermedi.")
    elif adjacent["status"] == "celiski":
        region = REGION_NAMES[adjacent["regions"][0]]
        notes.append(f"Resmî rehberle çelişki: {ADJACENT_METERS} m içindeki {label(adjacent['rows'])} {region} gösteriyor; "
                     f"resmî rehber {region}'te halka açık plaj erişimi olmadığını söylüyor. Bu mahalleye atanmadı.")
    elif adjacent["status"] == "yok" and inside["status"] != "atandi":
        mapped_far = [row for row in rows if row["iliski"] == "yakin" and row["alt_bolum_adi"] in table]
        if mapped_far:
            nearest_row = min(mapped_far, key=lambda row: float(row["mesafe_m"]))
            notes.append(f"İlçe verisi: tabloda olan en yakın alt bölüm {label([nearest_row])}, {nearest_row['mesafe_m']} m "
                         f"({ADJACENT_METERS} m'den uzak; kullanılmadı).")
        elif not [row for row in rows if row["iliski"] != "sonucsuz"]:
            notes.append(f"İlçe verisi: {NEAR_METERS} m içinde alt bölüm poligonu yok.")
        else:
            notes.append(f"İlçe verisi: {NEAR_METERS} m içindeki poligonların adları bir mahalleyi belirtmiyor.")
    return notes


def county_source(rows):
    date = min(row["sorgu_zamani"] for row in rows)[:10]
    return f"{rows[0]['katman_url']} (sorgu {date})"


def segment_distance(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = 0 if dx == dy == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def polygon_distance(latitude, longitude, rings):
    """Meters from a point to polygon edges (local equirectangular projection; < 1 m error at this scale)."""
    kx, ky = 111320 * math.cos(math.radians(latitude)), 110574
    best = math.inf
    for ring in rings:
        points = [((x - longitude) * kx, (y - latitude) * ky) for x, y in ring]
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            best = min(best, segment_distance(0, 0, ax, ay, bx, by))
    return best


def query_subdivisions(beaches, client, raw_dir, layer_url=COUNTY_SUBDIVISION_LAYER, pause=None):
    """Per access: every polygon containing the point and every other polygon within NEAR_METERS. Raw answers are kept."""
    pause = QUERY_GAP if pause is None else pause
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)

    def get(params, name):
        response = client.get(f"{layer_url}/query", params=params, headers={"User-Agent": USER_AGENT})
        (raw_dir / name).write_text(response.text, encoding="utf-8")
        if response.status_code != 200:
            raise SystemExit(f"İlçe katmanı sorgusu başarısız (HTTP {response.status_code}).")
        data = response.json()
        if "error" in data or not isinstance(data.get("features"), list):
            raise SystemExit(f"İlçe katmanı sorgusu hata döndürdü: {data.get('error')}")
        return data["features"]

    rows = []
    for beach in sorted(beaches, key=lambda beach: (beach["longitude"], beach["name"])):
        base = {"geometry": json.dumps({"x": beach["longitude"], "y": beach["latitude"], "spatialReference": {"wkid": 4326}}),
                "geometryType": "esriGeometryPoint", "inSR": "4326", "spatialRel": "esriSpatialRelIntersects",
                "outFields": "OBJECTID,OWNER_NAME,SUBDIVISION_NUMBER,LEGAL_1,USE_DESC", "f": "json"}
        inside = get({**base, "returnGeometry": "false"}, f"{beach['external_id']}-iceride.json")
        time.sleep(pause)
        near = get({**base, "distance": str(SEARCH_METERS), "units": "esriSRUnit_Meter", "returnGeometry": "true", "outSR": "4326"},
                   f"{beach['external_id']}-yakin.json")
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

        def row(feature, relation, distance):
            attributes = feature["attributes"]
            return {"external_id": beach["external_id"], "alt_bolum_adi": (attributes.get("OWNER_NAME") or "").strip(),
                    "alt_bolum_numarasi": (attributes.get("SUBDIVISION_NUMBER") or "").strip(),
                    "poligon_kimligi": str(attributes["OBJECTID"]), "iliski": relation, "mesafe_m": distance,
                    "katman_url": layer_url, "sorgu_zamani": stamp}

        found = [row(feature, "iceride", "0") for feature in sorted(inside, key=lambda f: f["attributes"]["OBJECTID"])]
        inside_ids = {feature["attributes"]["OBJECTID"] for feature in inside}
        measured = sorted(((polygon_distance(beach["latitude"], beach["longitude"], f["geometry"]["rings"]), f) for f in near
                           if f["attributes"]["OBJECTID"] not in inside_ids and (f.get("geometry") or {}).get("rings")),
                          key=lambda item: (item[0], item[1]["attributes"]["OBJECTID"]))
        found += [row(feature, "yakin", f"{distance:.1f}") for distance, feature in measured if distance <= NEAR_METERS]
        rows += found or [{"external_id": beach["external_id"], "alt_bolum_adi": "", "alt_bolum_numarasi": "", "poligon_kimligi": "",
                           "iliski": "sonucsuz", "mesafe_m": "", "katman_url": layer_url, "sorgu_zamani": stamp}]
        time.sleep(pause)
    return rows


# --- Üretim ---------------------------------------------------------------------------------------

def official_rows(path, beach_ids):
    """Filled rows of the GÖREV-02 preview, taken as they are; any doubt stops generation."""
    region_ids = {name: identifier for identifier, name in REGIONS}
    rows = {}
    with open(path, encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            name = row["kaynagin_verdigi_mahalle"].strip()
            if not name:
                continue
            if row["external_id"] not in beach_ids:
                raise SystemExit(f"Resmî eşlemedeki plaj kimliği plaj çekiminde yok: {row['external_id']}")
            if name not in region_ids:
                raise SystemExit(f"Resmî eşlemedeki mahalle kanonik bölgelerde yok: {name}")
            if not row["kaynak"].startswith(OFFICIAL_PREFIX):
                raise SystemExit(f"Resmî eşlemenin kaynağı beklenen rehber değil: {row['external_id']}")
            rows[row["external_id"]] = {"region_id": region_ids[name], "note": row["kaynak"][len(OFFICIAL_PREFIX):]}
    return rows


def neighbors(ordered, index, sourced):
    """Nearest sourced access to the west and to the east of ordered[index] (longitude order)."""
    west = next((ordered[i] for i in range(index - 1, -1, -1) if ordered[i]["external_id"] in sourced), None)
    east = next((ordered[i] for i in range(index + 1, len(ordered)) if ordered[i]["external_id"] in sourced), None)
    return west, east


def neighbor_result(ordered, index, sourced):
    west, east = neighbors(ordered, index, sourced)
    if not west or not east:
        return {"status": "tek_taraf", "region_id": None, "west": west, "east": east}
    same = sourced[west["external_id"]]["bolge_id"] == sourced[east["external_id"]]["bolge_id"]
    return {"status": "ayni" if same else "farkli", "region_id": sourced[west["external_id"]]["bolge_id"] if same else None,
            "west": west, "east": east}


def neighbor_note(result, sourced):
    side = lambda beach: (f"{beach['name']} ({REGION_NAMES[sourced[beach['external_id']]['bolge_id']]}, "
                          f"{METHOD_LABELS[sourced[beach['external_id']]['yontem']]})")
    if result["status"] == "ayni":
        return f"Batıdaki en yakın kaynaklı erişim {side(result['west'])} ve doğudaki {side(result['east'])} aynı mahallede."
    if result["status"] == "farkli":
        return f"Komşu tutarlılığı sonuç vermedi: batıda {side(result['west'])}, doğuda {side(result['east'])}."
    present = result["west"] or result["east"]
    return f"Komşu tutarlılığı sonuç vermedi: yalnız bir tarafta kaynaklı erişim var{f' ({side(present)})' if present else ''}."


def build(beaches, neighborhoods, official, neighborhood_run_id, subdivisions=None, table=None):
    """Return (mapping rows, validation rows, conflicts), west to east by the beach access longitude."""
    subdivisions, table = subdivisions or {}, table or {}
    ordered = sorted(beaches, key=lambda beach: (beach["longitude"], beach["name"]))
    evidence, sourced, conflicts = {}, {}, []
    for beach in ordered:
        rows = subdivisions.get(beach["external_id"], [])
        inside = inside_result(rows, table)
        adjacent = adjacent_result(rows, table, inside)
        evidence[beach["external_id"]] = (rows, inside, adjacent)
        for result in (inside, adjacent):
            if result["status"] == "celiski":
                conflicts.append({"external_id": beach["external_id"], "plaj_adi": beach["name"], "alt_bolum": label(result["rows"]),
                                  "bolge_id": result["regions"][0]})
        base = {"external_id": beach["external_id"], "plaj_adi": beach["name"], "belirsiz": "hayır"}
        if beach["external_id"] in official:
            entry = official[beach["external_id"]]
            sourced[beach["external_id"]] = {**base, "bolge_id": entry["region_id"], "yontem": METHOD_OFFICIAL,
                                             "kaynak": OFFICIAL_SOURCE, "not": entry["note"]}
        elif inside["status"] == "atandi":
            sourced[beach["external_id"]] = {**base, "bolge_id": inside["region_id"], "yontem": METHOD_COUNTY,
                                             "kaynak": county_source(inside["rows"]), "not": " ".join(county_notes(rows, inside, adjacent, table))}
        elif adjacent["status"] == "atandi":
            sourced[beach["external_id"]] = {**base, "bolge_id": adjacent["region_id"], "yontem": METHOD_COUNTY_ADJACENT,
                                             "kaynak": county_source(adjacent["rows"]), "not": " ".join(county_notes(rows, inside, adjacent, table))}
    mapping, validation = [], []
    for index, beach in enumerate(ordered):
        identifier = beach["external_id"]
        rows, inside, adjacent = evidence[identifier]
        derived = nearest(beach["longitude"], neighborhoods)
        if identifier in official:
            others = {key: value for key, value in sourced.items() if key != identifier}
            around = neighbor_result(ordered, index, others)
            validation.append(validate(beach, official[identifier]["region_id"], inside, adjacent, around, derived))
        if identifier in sourced:
            mapping.append(sourced[identifier])
            continue
        around = neighbor_result(ordered, index, sourced)
        notes = county_notes(rows, inside, adjacent, table)
        row = {"external_id": identifier, "plaj_adi": beach["name"]}
        if around["status"] == "ayni":
            west, east = around["west"]["external_id"], around["east"]["external_id"]
            mapping.append({**row, "bolge_id": around["region_id"], "yontem": METHOD_NEIGHBORS, "kaynak": f"komşu erişimler {west} ve {east}",
                            "not": " ".join([neighbor_note(around, sourced), *notes]), "belirsiz": "hayır"})
        else:
            mapping.append({**row, "bolge_id": derived["chosen"]["region_id"], "yontem": METHOD_DERIVED, "kaynak": neighborhood_run_id,
                            "not": " ".join([derived_note(derived), neighbor_note(around, sourced), *notes]),
                            "belirsiz": "evet" if derived["ambiguous"] else "hayır"})
    return mapping, validation, conflicts


def validate(beach, official_region, inside, adjacent, around, derived):
    """What each later method would say for an official access (official mapping itself is never changed)."""
    outcome = lambda region: "sonucsuz" if region is None else ("ayni" if region == official_region else "farkli")
    results = [(METHOD_COUNTY, inside["region_id"]), (METHOD_COUNTY_ADJACENT, adjacent["region_id"]),
               (METHOD_NEIGHBORS, around["region_id"]), (METHOD_DERIVED, derived["chosen"]["region_id"])]
    chain_method, chain_region = next((method, region) for method, region in results if region is not None)
    return {"external_id": beach["external_id"], "plaj_adi": beach["name"], "resmi_bolge_id": official_region,
            "ilce_bolge_id": inside["region_id"] or "", "ilce_sonuc": outcome(inside["region_id"]),
            "ilce_yakin_bolge_id": adjacent["region_id"] or "", "ilce_yakin_sonuc": outcome(adjacent["region_id"]),
            "komsu_bolge_id": around["region_id"] or "", "komsu_sonuc": outcome(around["region_id"]),
            "turetilen_bolge_id": derived["chosen"]["region_id"], "turetme_sonuc": outcome(derived["chosen"]["region_id"]),
            "zincir_yontem": chain_method, "zincir_bolge_id": chain_region, "zincir_sonuc": outcome(chain_region)}


def compare(previous, mapping):
    """Rows whose neighborhood or method changed between the previous file and this one."""
    before = {row["external_id"]: row for row in previous}
    changes = []
    for row in mapping:
        old = before.get(row["external_id"])
        old_region, old_method = (old["bolge_id"], old["yontem"]) if old else ("", "")
        changed = [name for name, a, b in (("bolge", old_region, row["bolge_id"]), ("yontem", old_method, row["yontem"])) if a != b]
        if changed:
            changes.append({"external_id": row["external_id"], "plaj_adi": row["plaj_adi"], "onceki_bolge_id": old_region,
                            "onceki_yontem": old_method, "yeni_bolge_id": row["bolge_id"], "yeni_yontem": row["yontem"],
                            "degisen": "+".join(changed)})
    return changes


def read_inputs(data_dir, beach_run=None, neighborhood_run=None):
    """Read one beach run and one neighborhood run of the 30A destination without writing to the database."""
    path = (Path(data_dir) / "studio.sqlite3").resolve()
    with closing(sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)) as con:
        def run(connector, identifier):
            row = con.execute("""SELECT id FROM source_runs WHERE connector_name=? AND status='done' AND destination_id=?
                AND (? IS NULL OR id=?) ORDER BY rowid DESC LIMIT 1""", (connector, METADATA["id"], identifier, identifier)).fetchone()
            if not row:
                raise SystemExit(f"Başarılı {connector} çekimi bulunamadı.")
            return row[0]
        beach_run, neighborhood_run = run("south-walton-beaches", beach_run), run("south-walton-neighborhoods", neighborhood_run)
        beaches = [{"external_id": r[0], "name": r[1], "latitude": r[2], "longitude": r[3]} for r in con.execute(
            "SELECT external_id,name,latitude,longitude FROM beach_records WHERE run_id=?", (beach_run,))]
        neighborhoods = [{"region_id": r[0], "longitude": r[1]} for r in con.execute(
            "SELECT canonical_region_id,longitude FROM neighborhood_records WHERE run_id=?", (neighborhood_run,))]
    return beach_run, beaches, neighborhood_run, neighborhoods


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write(path, columns, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None, client=None):
    parser = argparse.ArgumentParser(description="30A plaj erişimi -> mahalle eşleme dosyasını üretir.")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--plaj-run")
    parser.add_argument("--mahalle-run")
    parser.add_argument("--resmi", type=Path, default=OFFICIAL_CSV)
    parser.add_argument("--cikti", type=Path, default=BEACH_NEIGHBORHOOD_MAPPING)
    parser.add_argument("--dogrulama", type=Path)
    parser.add_argument("--alt-bolum", type=Path, default=BEACH_SUBDIVISIONS)
    parser.add_argument("--alt-bolum-tablosu", type=Path, default=SUBDIVISION_NEIGHBORHOODS)
    parser.add_argument("--ilce-sorgula", action="store_true", help="İlçe katmanını ağdan yeniden sorgula ve --alt-bolum dosyasını yaz.")
    parser.add_argument("--ham", type=Path, help="--ilce-sorgula için ham yanıt klasörü (work/ altında).")
    parser.add_argument("--yalniz-sorgu", action="store_true", help="Yalnız ilçe sorgusunu yap; eşleme üretme.")
    parser.add_argument("--onceki", type=Path, help="Fark tablosu için önceki eşleme dosyası.")
    parser.add_argument("--fark", type=Path, help="Önceki dosyaya göre değişen satırlar.")
    args = parser.parse_args(argv)
    beach_run, beaches, neighborhood_run, neighborhoods = read_inputs(args.data_dir, args.plaj_run, args.mahalle_run)
    print(f"plaj çekimi {beach_run}: {len(beaches)} erişim; mahalle çekimi {neighborhood_run}: {len(neighborhoods)} nokta")
    if args.ilce_sorgula:
        if not args.ham:
            raise SystemExit("--ilce-sorgula için --ham klasörü gerekir.")
        owns = client is None
        client = client or httpx.Client(timeout=httpx.Timeout(40, connect=10))
        try:
            rows = query_subdivisions(beaches, client, args.ham)
        finally:
            if owns:
                client.close()
        write(args.alt_bolum, SUBDIVISION_COLUMNS, rows)
        print(f"ilçe sorgusu: {Counter(r['iliski'] for r in rows)} satır -> {args.alt_bolum}")
        if args.yalniz_sorgu:
            return rows
    subdivisions, table = read_subdivisions(args.alt_bolum), read_name_table(args.alt_bolum_tablosu)
    mapping, validation, conflicts = build(beaches, neighborhoods, official_rows(args.resmi, {b["external_id"] for b in beaches}),
                                           neighborhood_run, subdivisions, table)
    changes = compare(read_csv(args.onceki), mapping) if args.onceki else []
    write(args.cikti, COLUMNS, mapping)
    if args.dogrulama:
        write(args.dogrulama, VALIDATION_COLUMNS, validation)
    if args.fark:
        write(args.fark, DIFF_COLUMNS, changes)
    methods = Counter(row["yontem"] for row in mapping)
    print(", ".join(f"{METHOD_LABELS[method]} {methods[method]}" for method in METHOD_LABELS)
          + f"; belirsiz {sum(row['belirsiz'] == 'evet' for row in mapping)}; resmî rehberle çelişki {len(conflicts)}")
    for key in ("ilce_sonuc", "ilce_yakin_sonuc", "komsu_sonuc", "turetme_sonuc", "zincir_sonuc"):
        print(f"doğrulama {key}: {dict(Counter(row[key] for row in validation))}")
    if args.onceki:
        print(f"önceki -> yeni değişen satır: {len(changes)}")
    return mapping, validation, conflicts, changes


if __name__ == "__main__":
    main()
