"""30A plaj erişimi -> mahalle eşleme dosyasını üretir. Geliştirme aracıdır; uygulama bunu çağırmaz.

Eşleme dosyası bir kez üretilip commit edilir (studio/destinations/thirty_a_beach_neighborhoods.csv);
uygulama yalnız okur. Yöntem, kısıt ve doğrulama: docs/M7-MAHALLE-VERISI.md.

Yöntem sırası:
1. Resmî rehber: GÖREV-02 önizlemesindeki dolu satırlar olduğu gibi alınır (yontem=resmi_rehber).
2. Program türetimi: kalan erişimlere, mahalle çekimindeki temsilî noktalara boylam farkıyla en yakın
   mahalle atanır (yontem=turetim_en_yakin_mahalle_noktasi, kaynak=mahalle çekiminin run kimliği).
   Resmî rehberin halka açık plaj erişimi olmadığını söylediği Alys Beach ve Rosemary Beach atanmaz;
   sıradaki en yakın mahalle seçilir ve notta yazılır. Atanabilir en yakın iki aday arasındaki fark
   0.003 dereceden küçükse belirsiz=evet olur.
3. Doğrulama: aynı türetme resmî satırlara da uygulanır ve sonuç ayrı bir tabloya yazılır.

Kullanım (depo kökünden; veritabanı salt okunur açılır):
  .venv\\Scripts\\python.exe -X utf8 -m tools.plaj_mahalle_esleme --data-dir work\\gorev-03\\temp-data ^
      --dogrulama docs\\gorevler\\GOREV-03\\esleme-dogrulama.csv
Seçenekler: --plaj-run ve --mahalle-run (varsayılan: 30A'daki son başarılı çekimler), --resmi, --cikti.
"""
import argparse
import csv
import sqlite3
from contextlib import closing
from pathlib import Path

from studio.destinations.beach_neighborhoods import COLUMNS, METHOD_DERIVED, METHOD_OFFICIAL
from studio.destinations.thirty_a import BEACH_NEIGHBORHOOD_MAPPING, METADATA, REGIONS

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_CSV = ROOT / "docs" / "gorevler" / "GOREV-02" / "plaj-mahalle-onizleme.csv"
OFFICIAL_URL = "https://www.visitsouthwalton.com/blog/guide-beach-parking-transportation/"
OFFICIAL_DATE = "2023-05-04"
OFFICIAL_SOURCE = f"{OFFICIAL_URL} (yayın {OFFICIAL_DATE})"
OFFICIAL_PREFIX = f"VSW Guide to Beach Parking and Transportation (yayın {OFFICIAL_DATE}); "
# The official guide says "No Public Beach Access" under these neighborhood headings.
NO_PUBLIC_ACCESS = ("alys-beach", "rosemary-beach")
AMBIGUITY_DEGREES = 0.003
VALIDATION_COLUMNS = ("external_id", "plaj_adi", "resmi_bolge_id", "turetilen_bolge_id", "ayni", "boylam_farki",
                      "sonraki_aday", "sonraki_fark", "belirsiz", "atlanan")
REGION_NAMES = dict(REGIONS)


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


def build(beaches, neighborhoods, official, neighborhood_run_id):
    """Return (mapping rows, validation rows), both west to east by the beach access longitude."""
    mapping, validation = [], []
    for beach in sorted(beaches, key=lambda beach: (beach["longitude"], beach["name"])):
        result = nearest(beach["longitude"], neighborhoods)
        derived = result["chosen"]["region_id"]
        row = {"external_id": beach["external_id"], "plaj_adi": beach["name"]}
        if beach["external_id"] in official:
            entry = official[beach["external_id"]]
            mapping.append({**row, "bolge_id": entry["region_id"], "yontem": METHOD_OFFICIAL, "kaynak": OFFICIAL_SOURCE,
                            "not": entry["note"], "belirsiz": "hayır"})
            validation.append({**row, "resmi_bolge_id": entry["region_id"], "turetilen_bolge_id": derived,
                               "ayni": "evet" if derived == entry["region_id"] else "hayır",
                               "boylam_farki": f"{result['distance']:.4f}", "sonraki_aday": result["runner_up"]["region_id"],
                               "sonraki_fark": f"{result['runner_up_distance']:.4f}", "belirsiz": "evet" if result["ambiguous"] else "hayır",
                               "atlanan": ", ".join(hood["region_id"] for hood, _ in result["skipped"])})
        else:
            mapping.append({**row, "bolge_id": derived, "yontem": METHOD_DERIVED, "kaynak": neighborhood_run_id,
                            "not": derived_note(result), "belirsiz": "evet" if result["ambiguous"] else "hayır"})
    return mapping, validation


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
        beaches = [{"external_id": r[0], "name": r[1], "longitude": r[2]} for r in con.execute(
            "SELECT external_id,name,longitude FROM beach_records WHERE run_id=?", (beach_run,))]
        neighborhoods = [{"region_id": r[0], "longitude": r[1]} for r in con.execute(
            "SELECT canonical_region_id,longitude FROM neighborhood_records WHERE run_id=?", (neighborhood_run,))]
    return beach_run, beaches, neighborhood_run, neighborhoods


def write(path, columns, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description="30A plaj erişimi -> mahalle eşleme dosyasını üretir.")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--plaj-run")
    parser.add_argument("--mahalle-run")
    parser.add_argument("--resmi", type=Path, default=OFFICIAL_CSV)
    parser.add_argument("--cikti", type=Path, default=BEACH_NEIGHBORHOOD_MAPPING)
    parser.add_argument("--dogrulama", type=Path)
    args = parser.parse_args(argv)
    beach_run, beaches, neighborhood_run, neighborhoods = read_inputs(args.data_dir, args.plaj_run, args.mahalle_run)
    mapping, validation = build(beaches, neighborhoods, official_rows(args.resmi, {b["external_id"] for b in beaches}), neighborhood_run)
    write(args.cikti, COLUMNS, mapping)
    if args.dogrulama:
        write(args.dogrulama, VALIDATION_COLUMNS, validation)
    same = sum(row["ayni"] == "evet" for row in validation)
    print(f"plaj çekimi {beach_run}: {len(beaches)} erişim; mahalle çekimi {neighborhood_run}: {len(neighborhoods)} nokta")
    print(f"resmî rehber {sum(r['yontem'] == METHOD_OFFICIAL for r in mapping)}, program türetimi "
          f"{sum(r['yontem'] == METHOD_DERIVED for r in mapping)}, belirsiz {sum(r['belirsiz'] == 'evet' for r in mapping)}")
    print(f"doğrulama: {same}/{len(validation)} resmî eşlemede türetme aynı sonucu verdi")
    return mapping, validation


if __name__ == "__main__":
    main()
