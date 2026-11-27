"""HEDEF-04: Veri Çekici ile okuma (Sol menü → Veri → Okuma denemeleri → "Veri Çekici ile okuma").

Veri Çekici (`C:\\Users\\1\\source\\Repos\\veri-cekici`) projelerin ortak veri çekim aracıdır: bir liste dosyasındaki sayfaları
kurulu Chrome'larla, işçilere bölerek okur ve sonucu tek zip olarak verir. 30A Studio onun kodunu içe aktarmaz; aradaki sözleşme
iki dosyadır (Veri Çekici `docs/ORTAK_VERI_CEKICI.md` 4.2):

- **Liste** (`liste_uret`): 30A'nın tarayıcı isteyen siteleri — yapılandırmada korumalı (`protected`) ya da yalnız eklentiyle okunan
  (`extension_only`) kiralama şirketleri, bir kez doğrulama göstermiş alan adları (`browser_hosts`; kiralama ve restoran/market
  siteleri). Doğrudan istekle okunan siteler 30A'nın kendi işçilerinde kalır. Her siteden `sayfa` kadar iş (deneme: 2–4): kiralama
  şirketinde son fiyat çekiminin şirkete bağlanan ilan sayfaları (Track, RealJoy, Streamline için ilk iki haftanın fiyat sorusuyla:
  bir işin birkaç sorgusu), Alys Beach'te kendi evleri, restoran sitelerinde restoranın sitesi ve menü sayfaları. JSON Lines; bir site
  en çok dört işçinin listesine konur (işçi = doğrudan bağlantı + Ayarlar → ABD proxy'sindeki her proxy). Liste
  `<veri>/veri_cekici/listeler/<zaman>/` altına yazılır (`liste.jsonl` bütünü, `isci_NN.jsonl` bölünmüşü).
- **Sonuç zip'i** (`ice_aktar`): zip **olduğu gibi** ham kopya olarak saklanır (`<veri>/veri_cekici/ice_aktarmalar/<zaman>/`),
  yanına SHA-256'sı ve çözümü (`sonuc.json`) yazılır. Her kayıt 30A'nın kendi okuyucusuyla çözülür: Track/RealJoy fiyat dökümü
  (`agency_adapters.Track.parse_quote`), Streamline fiyat cevabı, ev sayfasının fiyat formu (`parse_page`), restoran sayfasının başlığı
  ve menü bağlantıları. "Ham kopyadan yeniden kur" (`yeniden_kur`) aynı çözümü saklanan zip'ten yeniden yapar; siteye gidilmez.

Bu adım gerçek veritabanının satırlarını değiştirmez (deneme; fiyat sürümü kurulmaz). Uzantı (eklenti) kapalı bir yedek yol olarak
yerinde kalır (Ayarlar → Tarayıcı eklentisi).
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import shutil
import zipfile
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

FOLDER = "veri_cekici"
BICIM = "veri-cekici-sonuc"
SITE_BASINA_ISCI = 4
PLATFORM = {"track": "track", "realjoy": "realjoy", "streamline": "streamline", "vrp": "vrp"}
QUOTE_ADAPTERS = ("track", "realjoy", "streamline")
MENU_WORDS = re.compile(r"menu|menus|food|drinks|dinner|lunch|breakfast", re.I)


class VeriCekiciHatasi(ValueError):
    pass


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def host_of(url):
    return (urlsplit(url or "").hostname or "").lower().removeprefix("www.")


def _host_in(host, hosts):
    return any(host == h or host.endswith("." + h) for h in hosts)


def _safe(text):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(text)).strip("._") or "_"


# ---------------------------------------------------------------------------------------------------------------- liste

def tarayici_siteleri(con):
    """30A'nın tarayıcı isteyen siteleri: [{"site", "tur", "sebep", "adapter"?, "domain"?}] (yapılandırmadan)."""
    hosts = {h.removeprefix("www.") for (h,) in con.execute("SELECT host FROM browser_hosts")}
    out = OrderedDict()
    for domain, adapter, protected, inventory in con.execute(
            "SELECT domain, adapter, protected, inventory FROM destination_agency_sites WHERE enabled=1 ORDER BY sort_order, domain"):
        inv = json.loads(inventory) if inventory else {}
        reasons = [r for r, on in (("korumalı", protected), ("yalnız eklenti", inv.get("extension_only")),
                                   ("doğrulama gösterdi", _host_in(domain, hosts))) if on]
        if reasons:
            out[domain] = {"site": domain, "tur": "kiralama", "sebep": ", ".join(reasons), "adapter": adapter, "domain": domain,
                           "origin": inv.get("origin")}
    for host in sorted(hosts):
        if host not in out and not any(_host_in(host, [d]) for d in out):
            out[host] = {"site": host, "tur": "restoran", "sebep": "doğrulama gösterdi"}
    return list(out.values())


def _latest_rate_run(con):
    row = con.execute("SELECT run_id FROM agency_rate_companies ORDER BY rowid DESC LIMIT 1").fetchone()
    return row[0] if row else None


def _latest_restaurant_run(con):
    row = con.execute("SELECT run_id FROM restaurant_sites ORDER BY rowid DESC LIMIT 1").fetchone()
    return row[0] if row else None


def liste_satirlari(con, sayfa=3, hafta=2):
    """(satırlar, siteler, uyarılar). `sayfa`: her siteden en çok kaç iş (2–4); `hafta`: fiyat sorusu sorulan hafta sayısı."""
    if not 1 <= int(sayfa) <= 4:
        raise VeriCekiciHatasi("Deneme okumasında her siteden 1–4 sayfa okunur.")
    siteler = tarayici_siteleri(con)
    run = _latest_rate_run(con)
    windows = [{"giris": r[0], "cikis": r[1], "anahtar": r[2]} for r in con.execute(
        "SELECT checkin, checkout, window_key FROM agency_rate_windows WHERE run_id=? ORDER BY checkin", (run,))][:hafta] if run else []
    rows, uyarilar = [], []
    restaurant_run = _latest_restaurant_run(con)
    for site in siteler:
        found = []
        if site["tur"] == "kiralama" and run:
            for lodging_id, page_url in con.execute(
                    "SELECT lodging_id, page_url FROM agency_rate_listings WHERE run_id=? AND domain=? AND page_status='matched' "
                    "AND page_url IS NOT NULL ORDER BY lodging_id LIMIT ?", (run, site["domain"], sayfa)):
                found.append({"kimlik": str(lodging_id), "adres": page_url, "tur": "ilan"})
            if not found:
                for site_id, page_url in con.execute(
                        "SELECT site_listing_id, page_url FROM agency_rate_own_listings WHERE run_id=? AND domain=? AND page_url IS NOT NULL "
                        "ORDER BY site_listing_id LIMIT ?", (run, site["domain"], sayfa)):
                    found.append({"kimlik": f"kendi-{site_id}", "adres": page_url, "tur": "kendi evi"})
            platform = PLATFORM.get(site.get("adapter"), "sayfa")
            for item in found:
                row = {"site": host_of(item["adres"]) or site["site"], "kimlik": item["kimlik"], "adres": item["adres"],
                       "eklenti": platform, "proje_site": site["site"], "tur": item["tur"], "adapter": site.get("adapter")}
                if platform in QUOTE_ADAPTERS and windows:
                    row["haftalar"] = windows
                rows.append(row)
        elif site["tur"] == "restoran" and restaurant_run:
            seen = set()
            for external_id, name, site_url, final_url in con.execute(
                    "SELECT external_id, name, site_url, final_url FROM restaurant_sites WHERE run_id=? ORDER BY external_id", (restaurant_run,)):
                url = final_url or site_url
                if not url or not _host_in(host_of(url), [site["site"]]) or url in seen:
                    continue
                seen.add(url)
                found.append({"kimlik": _safe(external_id.strip("/").split("/")[-1]) + "-site", "adres": url, "ad": name})
                for (menu_url,) in con.execute("SELECT DISTINCT url FROM restaurant_menus WHERE run_id=? AND external_id=? AND url IS NOT NULL "
                                               "ORDER BY url", (restaurant_run, external_id)):
                    if menu_url not in seen and _host_in(host_of(menu_url), [site["site"]]) and len(found) < sayfa:
                        seen.add(menu_url)
                        found.append({"kimlik": _safe(external_id.strip("/").split("/")[-1]) + "-" + hashlib.sha256(menu_url.encode()).hexdigest()[:8],
                                      "adres": menu_url, "ad": name})
                if len(found) >= sayfa:
                    break
            if len(found) < sayfa:      # a platform or second host (menus, ordering pages): the pages that linked to it
                for external_id, url in con.execute(
                        "SELECT external_id, url FROM restaurant_menus WHERE run_id=? AND url IS NOT NULL UNION "
                        "SELECT external_id, COALESCE(link_url, source_url) FROM restaurant_facts WHERE run_id=? "
                        "AND COALESCE(link_url, source_url) IS NOT NULL ORDER BY 1, 2", (restaurant_run, restaurant_run)):
                    if len(found) >= sayfa:
                        break
                    if url not in seen and _host_in(host_of(url), [site["site"]]):
                        seen.add(url)
                        found.append({"kimlik": _safe(external_id.strip("/").split("/")[-1]) + "-" + hashlib.sha256(url.encode()).hexdigest()[:8],
                                      "adres": url})
            home = f"https://{site['site']}/"
            if len(found) < min(2, sayfa) and home not in seen and not site["site"].startswith(("order.", "toasttab.")):
                found.append({"kimlik": "ana-sayfa", "adres": home})      # the host's own front page (at least two pages a site)
            for item in found[:sayfa]:
                rows.append({"site": site["site"], "kimlik": item["kimlik"], "adres": item["adres"], "eklenti": "sayfa",
                             "proje_site": site["site"], "tur": "restoran sayfası", "ad": item.get("ad")})
        if not found:
            uyarilar.append(f"{site['site']}: okunacak sayfa bulunamadı (son çekimde bu siteye bağlı sayfa yok).")
    return rows, siteler, uyarilar


def bol(rows, isci_sayisi, site_basina=SITE_BASINA_ISCI):
    """Bir site en çok `site_basina` işçinin listesine konur (Veri Çekici'nin bölmesiyle aynı kural)."""
    parts = [[] for _ in range(max(1, isci_sayisi))]
    groups = OrderedDict()
    for row in rows:
        groups.setdefault(row["site"], []).append(row)
    for number, items in enumerate(groups.values()):
        n = min(site_basina, len(parts), len(items))
        workers = [(number + k) % len(parts) for k in range(n)]
        for i, row in enumerate(items):
            parts[workers[i % n]].append(row)
    return parts


def _write_jsonl(path, header, rows):
    path.write_text("\n".join([json.dumps(header, ensure_ascii=False)] + [json.dumps(r, ensure_ascii=False) for r in rows]) + "\n",
                    encoding="utf-8")


def liste_uret(db, data_dir, *, sayfa=3, isci_sayisi=1, destination_id=None):
    with db.connect() as con:
        rows, siteler, uyarilar = liste_satirlari(con, sayfa=sayfa)
    if not rows:
        raise VeriCekiciHatasi("Okunacak sayfa bulunamadı.")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    folder = Path(data_dir) / FOLDER / "listeler" / stamp
    folder.mkdir(parents=True, exist_ok=True)
    name = f"30a-tarayici-siteleri-{stamp}"
    header = {"liste": name, "proje": "30A Studio", "olusturuldu": now_iso(), "sayfa": sayfa}
    _write_jsonl(folder / "liste.jsonl", header, rows)
    parts = bol(rows, isci_sayisi)
    files = []
    for i, part in enumerate(parts, 1):
        if part:
            _write_jsonl(folder / f"isci_{i:02d}.jsonl", {**header, "isci": i, "isci_sayisi": len(parts)}, part)
            files.append(f"isci_{i:02d}.jsonl")
    counts = Counter(r["site"] for r in rows)
    summary = {"liste": name, "klasor": str(folder), "dosya": str(folder / "liste.jsonl"), "isci_dosyalari": files,
               "satir": len(rows), "site_sayisi": len(counts), "isci_sayisi": isci_sayisi, "uyarilar": uyarilar,
               "siteler": [{**s, "sayfa": sum(1 for r in rows if r["proje_site"] == s["site"])} for s in siteler],
               "olusturuldu": header["olusturuldu"]}
    (folder / "ozet.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    return summary


# ---------------------------------------------------------------------------------------------------------------- içe aktarma

def _read_zip(path):
    tanim, records, errors = None, [], []
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        if "paket.json" not in names:
            raise VeriCekiciHatasi("Bu zip bir Veri Çekici sonuç paketi değil (paket.json yok).")
        tanim = json.loads(zf.read("paket.json").decode("utf-8"))
        if tanim.get("bicim") != BICIM:
            raise VeriCekiciHatasi("Bu zip bir Veri Çekici sonuç paketi değil (biçim tanınmadı).")
        for name in sorted(names):
            if name.startswith("cikti/hatalar/") and name.endswith(".json"):
                errors.append(json.loads(zf.read(name).decode("utf-8")))
            elif name.startswith("cikti/") and name.endswith(".json.gz"):
                records.append(json.loads(gzip.decompress(zf.read(name)).decode("utf-8")))
    return tanim, records, errors


def _quote_of(adapter, reply):
    """Bir fiyat cevabının 30A okuyucusuyla çözümü: {"durum", "toplam"?, "kira"?, "mesaj"?}."""
    from .sources import agency_adapters as A

    text = (reply.get("govde") or "").strip()
    if reply.get("durum") != 200:
        return {"durum": "hata", "mesaj": f"HTTP {reply.get('durum')}"}
    if adapter in ("track", "realjoy"):
        if text == "No":
            return {"durum": "unavailable", "mesaj": "Site: bu tarihler müsait değil."}
        if "pdp-quote-list" in text:
            try:
                q = A.Track.parse_quote(text)
            except A.AdapterError as exc:
                return {"durum": "hata", "mesaj": str(exc)}
            return {"durum": "priced", "toplam": q.get("total"), "kira": q.get("rent")}
        return {"durum": "site_mesaji", "mesaj": A.plain_text(text)[:200]}
    if adapter == "streamline":
        try:
            data = json.loads(text)
        except ValueError:
            return {"durum": "hata", "mesaj": "JSON değil"}
        if isinstance(data.get("status"), dict):
            return {"durum": "site_mesaji", "mesaj": A.clean(data["status"].get("description"))}
        body = data.get("data") if isinstance(data.get("data"), dict) else {}
        if A.money(body.get("price")) is not None:
            return {"durum": "priced", "toplam": A.money(body.get("total")), "kira": A.money(body.get("price"))}
        return {"durum": "cevap", "mesaj": "müsaitlik cevabı"}
    return {"durum": "cevap"}


def _title(html):
    m = re.search(r"<title[^>]*>(.*?)</title>", html or "", re.S | re.I)
    from html import unescape

    return re.sub(r"\s+", " ", unescape(m.group(1))).strip()[:160] if m else ""


def kaydi_coz(record):
    """Bir Veri Çekici kaydının 30A'daki çözümü."""
    from .sources import agency_adapters as A

    row = record.get("satir") or {}
    page = next((c for c in record.get("cevaplar") or [] if c.get("tur") == "sayfa"), {})
    html = page.get("govde") or ""
    out = {"site": record.get("site"), "proje_site": row.get("proje_site") or record.get("site"), "kimlik": record.get("kimlik"),
           "adres": record.get("adres"), "tur": row.get("tur"), "isci": record.get("isci"), "okuma_zamani": record.get("okuma_zamani"),
           "sayfa_durumu": page.get("durum"), "baslik": _title(html) or page.get("baslik") or "", "uzunluk": len(html),
           "sorgu": 0, "fiyatli": 0, "fiyatlar": [], "not": ""}
    adapter = row.get("eklenti") or record.get("eklenti")
    if adapter in ("track", "realjoy"):
        info = A.Track().parse_page(html, record.get("adres") or "")
        out["ev_numarasi"] = info["site_id"] if info else None
        if not info:
            out["not"] = "Sayfada fiyat formu bulunamadı."
    elif adapter == "streamline":
        info = A.Streamline().parse_page(html, record.get("adres") or "")
        out["ev_numarasi"] = info["site_id"] if info else None
    elif adapter == "sayfa" and row.get("tur") == "restoran sayfası":
        links = sorted({h for h in re.findall(r'href="([^"]+)"', html) if MENU_WORDS.search(h)})[:10]
        out["menu_baglantilari"] = links
    for reply in record.get("cevaplar") or []:
        if reply.get("tur") != "sorgu":
            continue
        if adapter == "streamline" and "VerifyPropertyAvailability" in (reply.get("adres") or "") and reply.get("durum") == 200:
            q = _quote_of(adapter, reply)
            if q["durum"] != "site_mesaji":
                continue
        else:
            q = _quote_of(adapter, reply)
        out["sorgu"] += 1
        out["fiyatlar"].append({"not": reply.get("not"), **q})
        out["fiyatli"] += q["durum"] == "priced"
    return out


def _cozum(zip_path):
    tanim, records, errors = _read_zip(zip_path)
    rows = [kaydi_coz(r) for r in records]
    sites = OrderedDict()
    for r in rows:
        s = sites.setdefault(r["proje_site"], {"site": r["proje_site"], "okunan": 0, "hata": 0, "sorgu": 0, "fiyatli": 0, "isciler": set()})
        s["okunan"] += 1
        s["sorgu"] += r["sorgu"]
        s["fiyatli"] += r["fiyatli"]
        s["isciler"].add(r["isci"] or "")
    for e in errors:
        key = e.get("site") or "?"
        s = sites.setdefault(key, {"site": key, "okunan": 0, "hata": 0, "sorgu": 0, "fiyatli": 0, "isciler": set()})
        s["hata"] += 1
    return {"paket": {k: tanim.get(k) for k in ("arac_surumu", "liste", "isci", "isciler", "bilgisayar", "olusturuldu")},
            "siteler": [{**s, "isciler": sorted(x for x in s["isciler"] if x)} for s in sites.values()],
            "kayitlar": rows, "hatalar": [{k: e.get(k) for k in ("site", "kimlik", "adres", "sebep", "isci")} for e in errors],
            "okunan": len(rows), "hata": len(errors), "fiyatli": sum(r["fiyatli"] for r in rows)}


def ice_aktar(data_dir, zip_path, name=None):
    zip_path = Path(zip_path)
    try:
        _read_zip(zip_path)
    except zipfile.BadZipFile:
        raise VeriCekiciHatasi("Dosya bir zip değil.") from None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    folder = Path(data_dir) / FOLDER / "ice_aktarmalar" / stamp
    folder.mkdir(parents=True, exist_ok=False)
    target = folder / _safe(name or zip_path.name)
    shutil.copyfile(zip_path, target)                   # ham kopya: zip olduğu gibi
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    result = {"kimlik": stamp, "dosya": target.name, "sha256": digest, "ice_alindi": now_iso(), "yeniden_kuruldu": None,
              **_cozum(target)}
    (folder / "sonuc.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return result


def yeniden_kur(data_dir, kimlik):
    """"Ham kopyadan yeniden kur": saklanan zip'ten çözüm yeniden yapılır (siteye gidilmez); zip'in SHA-256'sı denetlenir."""
    folder = Path(data_dir) / FOLDER / "ice_aktarmalar" / _safe(kimlik)
    old = json.loads((folder / "sonuc.json").read_text(encoding="utf-8"))
    target = folder / old["dosya"]
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    if digest != old["sha256"]:
        raise VeriCekiciHatasi("Ham kopyanın SHA-256'sı içe alındığı günkünden farklı; yeniden kurulmadı.")
    result = {**old, **_cozum(target), "yeniden_kuruldu": now_iso()}
    (folder / "sonuc.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    return result


def gorunum(data_dir, limit=10):
    base = Path(data_dir) / FOLDER
    lists, imports = [], []
    for path in sorted((base / "listeler").glob("*/ozet.json"), reverse=True)[:limit]:
        lists.append(json.loads(path.read_text(encoding="utf-8")))
    for path in sorted((base / "ice_aktarmalar").glob("*/sonuc.json"), reverse=True)[:limit]:
        data = json.loads(path.read_text(encoding="utf-8"))
        imports.append({k: v for k, v in data.items() if k != "kayitlar"} | {"kayitlar": data.get("kayitlar", [])[:200]})
    return {"listeler": lists, "ice_aktarmalar": imports}
