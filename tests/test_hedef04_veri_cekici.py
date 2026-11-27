"""HEDEF-04: Veri Çekici ile okuma — liste üretme (tarayıcı isteyen siteler, bir site en çok dört işçi), sonuç zip'ini içe alma
(zip olduğu gibi ham kopya, 30A'nın okuyucularıyla çözüm), "Ham kopyadan yeniden kur" ve uçlar. Ağ yok."""
import gzip
import io
import json
import sqlite3
import zipfile

import pytest
from fastapi.testclient import TestClient

from studio import veri_cekici as V
from studio.app import create_app

HEADERS = {"X-Studio-Request": "1"}
RUN = "run1"
QUOTE = ('<ul class="pdp-quote-list"><li><span class="pdp-quote-item-text">Rent</span><span class="pdp-quote-item-price" data-price="2000"></span></li>'
         '<li class="pdp-quote-total"><span class="pdp-quote-item-text">Total</span><span class="pdp-quote-item-price" data-price="2650.5"></span></li></ul>')
TRACK_PAGE = ('<title>Wave N Sea</title><form id="pdpDatesForm"><input name="checkin" value=""><input name="checkout" value="">'
              '<input type="hidden" name="propertyID" value="77"></form>')


def schema(con):
    con.executescript("""
    CREATE TABLE browser_hosts(host TEXT); CREATE TABLE destination_agency_sites(domain TEXT, adapter TEXT, protected INT, inventory TEXT,
      enabled INT DEFAULT 1, sort_order INT DEFAULT 0);
    CREATE TABLE agency_rate_companies(run_id TEXT, domain TEXT); CREATE TABLE agency_rate_windows(run_id TEXT, window_key TEXT, checkin TEXT, checkout TEXT);
    CREATE TABLE agency_rate_listings(run_id TEXT, lodging_id TEXT, domain TEXT, page_url TEXT, page_status TEXT);
    CREATE TABLE agency_rate_own_listings(run_id TEXT, domain TEXT, site_listing_id TEXT, page_url TEXT);
    CREATE TABLE restaurant_sites(run_id TEXT, external_id TEXT, name TEXT, site_url TEXT, final_url TEXT);
    CREATE TABLE restaurant_menus(run_id TEXT, external_id TEXT, url TEXT); CREATE TABLE restaurant_facts(run_id TEXT, external_id TEXT, link_url TEXT, source_url TEXT);
    """)
    con.executemany("INSERT INTO browser_hosts VALUES (?)", [("30aescapes.com",), ("modicamarket.com",), ("toasttab.com",)])
    con.executemany("INSERT INTO destination_agency_sites(domain, adapter, protected, inventory) VALUES (?,?,?,?)", [
        ("30aescapes.com", "track", 0, None), ("realjoy.com", "realjoy", 1, json.dumps({"extension_only": True})),
        ("benchmark30a.com", "rescms", 0, None), ("alysbeach.com", "vrp", 1, json.dumps({"origin": "https://vacation.alysbeach.com"}))])
    con.execute("INSERT INTO agency_rate_companies VALUES (?, '30aescapes.com')", (RUN,))
    con.executemany("INSERT INTO agency_rate_windows VALUES (?,?,?,?)", [(RUN, "ay-2027-01", "2027-01-09", "2027-01-16"),
                                                                       (RUN, "ay-2027-02", "2027-02-13", "2027-02-20"), (RUN, "ay-2027-03", "2027-03-13", "2027-03-20")])
    con.executemany("INSERT INTO agency_rate_listings VALUES (?,?,?,?,?)",
                    [(RUN, f"L{i}", "30aescapes.com", f"https://www.30aescapes.com/rentals/ev-{i}", "matched") for i in range(6)] +
                    [(RUN, "R1", "realjoy.com", "https://www.realjoy.com/beach-rentals/a", "matched"), (RUN, "B1", "benchmark30a.com", "https://b/x", "matched"),
                     (RUN, "X", "30aescapes.com", None, "not_found")])
    con.executemany("INSERT INTO agency_rate_own_listings VALUES (?,?,?,?)", [(RUN, "alysbeach.com", "103", "https://vacation.alysbeach.com/vrp/unit/103")])
    con.executemany("INSERT INTO restaurant_sites VALUES (?,?,?,?,?)", [("rr", "/listing/modica-market/", "Modica Market", "http://modicamarket.com", "https://modicamarket.com/")])
    con.executemany("INSERT INTO restaurant_menus VALUES (?,?,?)", [("rr", "/listing/modica-market/", "https://modicamarket.com/menu"),
                                                                   ("rr", "/listing/x/", "https://www.toasttab.com/local/x")])
    con.commit()


@pytest.fixture
def con():
    c = sqlite3.connect(":memory:")
    schema(c)
    return c


def test_the_list_has_only_the_sites_that_need_a_browser_and_two_to_four_pages_each(con):
    sites = {s["site"]: s for s in V.tarayici_siteleri(con)}
    assert set(sites) == {"30aescapes.com", "realjoy.com", "alysbeach.com", "modicamarket.com", "toasttab.com"}   # benchmark: direct
    assert sites["realjoy.com"]["sebep"] == "korumalı, yalnız eklenti"
    rows, _, warnings = V.liste_satirlari(con, sayfa=3, hafta=2)
    by = {}
    for r in rows:
        by.setdefault(r["proje_site"], []).append(r)
    assert len(by["30aescapes.com"]) == 3 and by["30aescapes.com"][0]["eklenti"] == "track"
    assert by["30aescapes.com"][0]["haftalar"] == [{"giris": "2027-01-09", "cikis": "2027-01-16", "anahtar": "ay-2027-01"},
                                                   {"giris": "2027-02-13", "cikis": "2027-02-20", "anahtar": "ay-2027-02"}]
    assert by["alysbeach.com"][0]["site"] == "vacation.alysbeach.com" and by["alysbeach.com"][0]["eklenti"] == "vrp"
    assert [r["adres"] for r in by["modicamarket.com"]] == ["https://modicamarket.com/", "https://modicamarket.com/menu"]
    assert by["toasttab.com"][0]["adres"] == "https://www.toasttab.com/local/x" and not warnings
    with pytest.raises(V.VeriCekiciHatasi):
        V.liste_satirlari(con, sayfa=9)


def test_a_site_goes_to_at_most_four_workers():
    rows = [{"site": "a", "kimlik": str(i)} for i in range(10)] + [{"site": "b", "kimlik": "1"}]
    parts = V.bol(rows, 6)
    assert sum(any(r["site"] == "a" for r in p) for p in parts) == 4 and sum(len(p) for p in parts) == 11


def record(site, kimlik, eklenti, replies, **row):
    return {"surum": 1, "site": site, "kimlik": kimlik, "adres": replies[0]["adres"], "eklenti": eklenti, "isci": "Doğrudan",
            "satir": {"site": site, "kimlik": kimlik, "eklenti": eklenti, **row}, "okuma_zamani": "2026-11-28T01:00:00+03:00", "cevaplar": replies}


def make_zip(records, errors=()):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("paket.json", json.dumps({"bicim": "veri-cekici-sonuc", "surum": 1, "arac_surumu": "0.2.0", "liste": "x", "isci": "panel",
                                              "isciler": ["Doğrudan"], "siteler": {}}))
        for r in records:
            zf.writestr(f"cikti/{r['site']}/{r['kimlik']}.json.gz", gzip.compress(json.dumps(r).encode()))
        for e in errors:
            zf.writestr(f"cikti/hatalar/{e['site']}/{e['kimlik']}.json", json.dumps(e))
    return buf.getvalue()


def sample_zip():
    track = record("30aescapes.com", "L1", "track", [
        {"tur": "sayfa", "adres": "https://www.30aescapes.com/rentals/ev-1", "durum": 200, "govde": TRACK_PAGE},
        {"tur": "sorgu", "adres": "https://www.30aescapes.com/ajax/quote", "durum": 200, "govde": QUOTE, "not": "fiyat ay-2027-01"},
        {"tur": "sorgu", "adres": "https://www.30aescapes.com/ajax/quote", "durum": 200, "govde": "No", "not": "fiyat ay-2027-02"}],
        proje_site="30aescapes.com", tur="ilan")
    stream = record("rosemarybeach.com", "S1", "streamline", [
        {"tur": "sayfa", "adres": "https://rosemarybeach.com/ev/", "durum": 200, "govde": "<title>Ev</title>"},
        {"tur": "sorgu", "adres": "https://rosemarybeach.com/wp-admin/admin-ajax.php?action=x&params=VerifyPropertyAvailability", "durum": 200, "govde": "{}"},
        {"tur": "sorgu", "adres": "https://rosemarybeach.com/wp-admin/admin-ajax.php?action=x&params=GetPreReservationPrice", "durum": 200,
         "govde": json.dumps({"data": {"price": 1800, "total": 2300.25}})}], proje_site="rosemarybeach.com")
    page = record("modicamarket.com", "m-site", "sayfa", [{"tur": "sayfa", "adres": "https://modicamarket.com/", "durum": 200,
                                                           "govde": '<title>Modica Market</title><a href="/menu">Menu</a>'}],
                  proje_site="modicamarket.com", tur="restoran sayfası")
    return make_zip([track, stream, page], [{"site": "realjoy.com", "kimlik": "R1", "adres": "https://www.realjoy.com/a", "sebep": "Doğrulama ekranı süresinde geçilmedi."}])


def test_the_zip_is_kept_as_it_is_and_read_with_30as_readers(tmp_path):
    src = tmp_path / "in.zip"
    src.write_bytes(sample_zip())
    out = V.ice_aktar(tmp_path / "data", src, "veri_cekici_sonuclari_PC_panel.zip")
    kept = next((tmp_path / "data" / "veri_cekici" / "ice_aktarmalar").glob("*/veri_cekici_sonuclari_PC_panel.zip"))
    assert kept.read_bytes() == src.read_bytes()
    sites = {s["site"]: s for s in out["siteler"]}
    assert sites["30aescapes.com"] == {"site": "30aescapes.com", "okunan": 1, "hata": 0, "sorgu": 2, "fiyatli": 1, "isciler": ["Doğrudan"]}
    assert sites["rosemarybeach.com"]["fiyatli"] == 1 and sites["realjoy.com"]["hata"] == 1
    track = next(r for r in out["kayitlar"] if r["kimlik"] == "L1")
    assert track["ev_numarasi"] == "77" and track["fiyatlar"][0] == {"not": "fiyat ay-2027-01", "durum": "priced", "toplam": 2650.5, "kira": 2000.0}
    assert track["fiyatlar"][1]["durum"] == "unavailable"
    assert next(r for r in out["kayitlar"] if r["kimlik"] == "m-site")["menu_baglantilari"] == ["/menu"]
    again = V.yeniden_kur(tmp_path / "data", out["kimlik"])
    assert again["siteler"] == out["siteler"] and again["yeniden_kuruldu"]
    kept.write_bytes(b"bozuk")
    with pytest.raises(V.VeriCekiciHatasi, match="SHA-256"):
        V.yeniden_kur(tmp_path / "data", out["kimlik"])


def test_a_zip_that_is_not_veri_cekicis_is_refused(tmp_path):
    bad = tmp_path / "b.zip"
    with zipfile.ZipFile(bad, "w") as zf:
        zf.writestr("x.txt", "x")
    with pytest.raises(V.VeriCekiciHatasi, match="paket.json"):
        V.ice_aktar(tmp_path / "data", bad)


def test_the_endpoints(tmp_path):
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        view = client.get("/api/veri-cekici").json()
        assert view["listeler"] == [] and view["ice_aktarmalar"] == [] and view["site_basina_isci"] == 4
        r = client.post("/api/veri-cekici/ice-aktar", content=sample_zip(), headers={**HEADERS, "Content-Type": "application/zip",
                                                                                  "X-Dosya-Adi": "veri_cekici_sonuclari_PC_panel.zip"})
        assert r.status_code == 201 and r.json()["okunan"] == 3
        assert client.get("/api/veri-cekici").json()["ice_aktarmalar"][0]["fiyatli"] == 2
        assert client.post(f"/api/veri-cekici/ice-aktarma/{r.json()['kimlik']}/yeniden-kur").status_code == 200
        assert client.post("/api/veri-cekici/ice-aktarma/yok/yeniden-kur").status_code == 404
        assert client.post("/api/veri-cekici/ice-aktar", content=b"zip degil", headers={**HEADERS, "Content-Type": "application/zip"}).status_code == 400
        r = client.post("/api/veri-cekici/liste", json={"sayfa": 3})
        assert r.status_code in (201, 400)       # an empty program has no browser sites: a Turkish 400, not a crash


def test_the_extension_is_a_closed_fallback_way(tmp_path):
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        assert client.get("/api/tarayici-eklentisi").json()["yedek_yol"] == "acik"      # an old pairing file: as before
        assert client.put("/api/tarayici-eklentisi/yedek-yol", json={"acik": False}).json()["yedek_yol"] == "kapali"
        bridge = client.app.state.extension
        bridge.config["koken"], bridge.last_seen = "chrome-extension://x", bridge.clock()
        assert not bridge.connected                    # closed: the program gives the extension no job
        client.put("/api/tarayici-eklentisi/yedek-yol", json={"acik": True})
        assert bridge.connected
