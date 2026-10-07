"""30A plaj erişimi -> mahalle eşleme dosyasını üretir (v2). Geliştirme aracıdır; uygulama bunu çağırmaz.

Eşleme dosyası bir kez üretilip commit edilir (studio/destinations/thirty_a_beach_neighborhoods.csv);
uygulama yalnız okur. Yöntem, kısıt ve doğrulama: docs/M7-MAHALLE-VERISI.md.

Yöntem sırası:
1. resmi_rehber: GÖREV-02 önizlemesindeki dolu satırlar olduğu gibi alınır.
2. ilce_alt_bolum: erişim noktası Walton County "Subdivision Boundaries" poligonlarından birinin içindeyse ve
   içinde olduğu alt bölümlerin adları, açık ad tablosuyla tek bir mahalleye bağlanıyorsa. Yakın (içinde olmayan)
   poligonlar yalnız kaydedilir ve notta yazılır; bu yöntemde kullanılmaz.
3. turetim_en_yakin_mahalle_noktasi: ilk iki yöntem sonuç vermezse, mahalle çekimindeki temsilî noktalara boylam
   farkıyla en yakın mahalle (kaynak = mahalle çekiminin run kimliği). Atanabilir en yakın iki aday arasındaki fark
   0.003 dereceden küçükse belirsiz=evet.
Kısıt: resmî rehberin halka açık plaj erişimi olmadığını söylediği Alys Beach ve Rosemary Beach'e hiçbir erişim
atanmaz. İlçe verisi bir erişimi bu iki mahallenin alt bölümüne düşürürse erişim o mahalleye atanmaz; satır
"resmî rehberle çelişki" notuyla işaretlenir.

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

from studio.destinations.beach_neighborhoods import COLUMNS, METHOD_COUNTY, METHOD_DERIVED, METHOD_OFFICIAL
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
SUBDIVISION_COLUMNS = ("external_id", "alt_bolum_adi", "poligon_kimligi", "iliski", "mesafe_m", "katman_url", "sorgu_zamani")
TABLE_COLUMNS = ("alt_bolum_adi", "bolge_id", "gerekce")
RELATIONS = ("iceride", "yakin", "sonucsuz")
NEAR_METERS, SEARCH_METERS, TIE_METERS = 75, 100, 0.1
QUERY_GAP = 0.25
USER_AGENT = "30AStudio/0.7 (+https://github.com/bemonths/tatilya)"
VALIDATION_COLUMNS = ("external_id", "plaj_adi", "resmi_bolge_id", "ilce_durum", "ilce_alt_bolum_adi", "ilce_bolge_id",
                      "ilce_sonuc", "turetilen_bolge_id", "turetme_sonuc")
DIFF_COLUMNS = ("external_id", "plaj_adi", "v1_bolge_id", "v1_yontem", "v2_bolge_id", "v2_yontem", "degisen")


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
    """Reviewed per-access query results grouped by beach id; one relation per access."""
    groups = {}
    with open(path, encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != SUBDIVISION_COLUMNS:
            raise SystemExit("Alt bölüm sonuç dosyasının sütunları beklenen biçimde değil.")
        for row in reader:
            if row["iliski"] not in RELATIONS:
                raise SystemExit(f"Alt bölüm sonucunda tanınmayan ilişki: {row['iliski']}")
            if (row["iliski"] == "sonucsuz") != (not row["poligon_kimligi"]):
                raise SystemExit(f"Alt bölüm sonucu tutarsız: {row['external_id']}")
            groups.setdefault(row["external_id"], []).append(row)
    for identifier, rows in groups.items():
        if len({row["iliski"] for row in rows}) != 1:
            raise SystemExit(f"Bir erişim için birden fazla ilişki türü var: {identifier}")
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


def county_result(rows, table):
    """Decide the county evidence for one access. Only polygons containing the point can assign a region."""
    if not rows:
        return {"status": "sorgu_yok", "region_id": None, "rows": []}
    relation = rows[0]["iliski"]
    if relation != "iceride":
        return {"status": relation, "region_id": None, "rows": rows}
    regions = sorted({table[row["alt_bolum_adi"]] for row in rows if row["alt_bolum_adi"] in table})
    if not regions:
        return {"status": "tabloda_yok", "region_id": None, "rows": rows}
    if len(regions) > 1:
        return {"status": "karisik", "region_id": None, "rows": rows, "regions": regions}
    if regions[0] in NO_PUBLIC_ACCESS:
        return {"status": "celiski", "region_id": None, "rows": rows, "regions": regions}
    return {"status": "atandi", "region_id": regions[0], "rows": rows}


def names(rows):
    return ", ".join(f"'{row['alt_bolum_adi'] or 'adsız'}' (OBJECTID {row['poligon_kimligi']})" for row in rows)


def county_note(result, table):
    status, rows = result["status"], result["rows"]
    if status == "atandi":
        return f"Walton County Subdivision Boundaries: erişim noktası {names(rows)} içinde; ad tablosu: {REGION_NAMES[result['region_id']]}."
    if status == "celiski":
        region = REGION_NAMES[result["regions"][0]]
        return (f"Resmî rehberle çelişki: ilçe verisi erişimi {names(rows)} içine düşürüyor ({region}); resmî rehber ({OFFICIAL_DATE}) "
                f"{region}'te halka açık plaj erişimi olmadığını söylüyor. Bu mahalleye atanmadı.")
    if status == "karisik":
        return f"İlçe verisi: erişim noktası {names(rows)} içinde; adlar farklı mahalleler gösteriyor ({', '.join(REGION_NAMES[r] for r in result['regions'])})."
    if status == "tabloda_yok":
        return f"İlçe verisi: erişim noktası {names(rows)} içinde; ad bir mahalleyi açıkça belirtmiyor."
    if status == "yakin":
        mapped = sorted({REGION_NAMES[table[row['alt_bolum_adi']]] for row in rows if row["alt_bolum_adi"] in table})
        hint = f" Adı {', '.join(mapped)} gösteriyor; yakın sonuç bu yöntemde kullanılmaz." if mapped else ""
        return f"İlçe verisi: nokta alt bölüm poligonu içinde değil; en yakın: {names(rows)}, {rows[0]['mesafe_m']} m.{hint}"
    if status == "sonucsuz":
        return f"İlçe verisi: {NEAR_METERS} m içinde alt bölüm poligonu yok."
    return "İlçe alt bölüm sorgusu bu erişim için yapılmadı."


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
    """Point-in-polygon query per access; if none, the nearest polygon(s) within NEAR_METERS. Raw answers are kept."""
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
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        row = lambda feature, relation, distance: {
            "external_id": beach["external_id"], "alt_bolum_adi": (feature["attributes"].get("OWNER_NAME") or "").strip(),
            "poligon_kimligi": str(feature["attributes"]["OBJECTID"]), "iliski": relation, "mesafe_m": distance,
            "katman_url": layer_url, "sorgu_zamani": stamp}
        if inside:
            rows += [row(feature, "iceride", "0") for feature in sorted(inside, key=lambda f: f["attributes"]["OBJECTID"])]
        else:
            time.sleep(pause)
            near = get({**base, "distance": str(SEARCH_METERS), "units": "esriSRUnit_Meter", "returnGeometry": "true", "outSR": "4326"},
                       f"{beach['external_id']}-yakin.json")
            measured = sorted(((polygon_distance(beach["latitude"], beach["longitude"], f["geometry"]["rings"]), f)
                               for f in near if (f.get("geometry") or {}).get("rings")), key=lambda item: (item[0], item[1]["attributes"]["OBJECTID"]))
            measured = [(distance, feature) for distance, feature in measured if distance <= NEAR_METERS]
            if measured:
                best = measured[0][0]
                rows += [row(feature, "yakin", f"{distance:.1f}") for distance, feature in measured if distance - best <= TIE_METERS]
            else:
                rows.append({"external_id": beach["external_id"], "alt_bolum_adi": "", "poligon_kimligi": "", "iliski": "sonucsuz",
                             "mesafe_m": "", "katman_url": layer_url, "sorgu_zamani": stamp})
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


def build(beaches, neighborhoods, official, neighborhood_run_id, subdivisions=None, table=None):
    """Return (mapping rows, validation rows, conflicts), west to east by the beach access longitude."""
    subdivisions, table = subdivisions or {}, table or {}
    mapping, validation, conflicts = [], [], []
    for beach in sorted(beaches, key=lambda beach: (beach["longitude"], beach["name"])):
        derived = nearest(beach["longitude"], neighborhoods)
        county = county_result(subdivisions.get(beach["external_id"], []), table)
        row = {"external_id": beach["external_id"], "plaj_adi": beach["name"]}
        if county["status"] == "celiski":
            conflicts.append({**row, "alt_bolum": names(county["rows"]), "bolge_id": county["regions"][0]})
        if beach["external_id"] in official:
            entry = official[beach["external_id"]]
            mapping.append({**row, "bolge_id": entry["region_id"], "yontem": METHOD_OFFICIAL, "kaynak": OFFICIAL_SOURCE,
                            "not": entry["note"], "belirsiz": "hayır"})
            region = county["region_id"]
            validation.append({**row, "resmi_bolge_id": entry["region_id"], "ilce_durum": county["status"],
                               "ilce_alt_bolum_adi": " | ".join(r["alt_bolum_adi"] for r in county["rows"]),
                               "ilce_bolge_id": region or "",
                               "ilce_sonuc": "sonucsuz" if region is None else ("ayni" if region == entry["region_id"] else "farkli"),
                               "turetilen_bolge_id": derived["chosen"]["region_id"],
                               "turetme_sonuc": "ayni" if derived["chosen"]["region_id"] == entry["region_id"] else "farkli"})
        elif county["region_id"]:
            mapping.append({**row, "bolge_id": county["region_id"], "yontem": METHOD_COUNTY, "kaynak": county_source(county["rows"]),
                            "not": county_note(county, table), "belirsiz": "hayır"})
        else:
            mapping.append({**row, "bolge_id": derived["chosen"]["region_id"], "yontem": METHOD_DERIVED, "kaynak": neighborhood_run_id,
                            "not": f"{derived_note(derived)} {county_note(county, table)}",
                            "belirsiz": "evet" if derived["ambiguous"] else "hayır"})
    return mapping, validation, conflicts


def compare(previous, mapping):
    """Rows whose neighborhood or method changed between the previous file and this one."""
    before = {row["external_id"]: row for row in previous}
    changes = []
    for row in mapping:
        old = before.get(row["external_id"])
        old_region, old_method = (old["bolge_id"], old["yontem"]) if old else ("", "")
        changed = [label for label, a, b in (("bolge", old_region, row["bolge_id"]), ("yontem", old_method, row["yontem"])) if a != b]
        if changed:
            changes.append({"external_id": row["external_id"], "plaj_adi": row["plaj_adi"], "v1_bolge_id": old_region, "v1_yontem": old_method,
                            "v2_bolge_id": row["bolge_id"], "v2_yontem": row["yontem"], "degisen": "+".join(changed)})
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
    print(f"resmî rehber {methods[METHOD_OFFICIAL]}, ilçe alt bölüm {methods[METHOD_COUNTY]}, program türetimi {methods[METHOD_DERIVED]}, "
          f"belirsiz {sum(row['belirsiz'] == 'evet' for row in mapping)}, resmî rehberle çelişki {len(conflicts)}")
    print(f"doğrulama (ilçe): {Counter(row['ilce_sonuc'] for row in validation)}; (türetme): {Counter(row['turetme_sonuc'] for row in validation)}")
    if args.onceki:
        print(f"v1 -> v2 değişen satır: {len(changes)}")
    return mapping, validation, conflicts, changes


if __name__ == "__main__":
    main()
