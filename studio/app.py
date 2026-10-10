import asyncio
import threading
import csv
import io
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import __version__
from .catalog import CADENCES, CATEGORIES, METHODS, STEPS
from .database import Conflict, Database
from .jobs import JobQueue
from . import refresh, workflow
from .models import (EvidencePackInput, JobInput, ReviewRunInput, RunDecisionInput, SourceInput, SourceUpdate, TextRunInput, TextSelectInput,
                     TextToneInput, TitleRunInput, ToneInput, ToneRestoreInput, TranslateInput)
from . import evidence
from .ai import settings as claude_settings
from .ai.service import ClaudeService
from .text.engine import TextService
from .watchdog import Watchdog
from . import extension as ext
from .sources import agency_rates, beaches, bookdirect_lodging, climate_normals, daily_needs, neighborhoods, restaurant_sites, storm_proximity, water_temperature, weather, windows
from .sources.registry import DEFAULT_REGISTRY
from .destinations import DEFAULT_DESTINATION_ID, PROFILES, beach_neighborhoods as beach_mapping, references as reference_table

WEB = Path(__file__).parent / "web"
EXTENSION_PREFIX = "/api/eklenti/"
EXTENSION_DIR = Path(__file__).resolve().parent.parent / "eklenti"
EXTENSION_STEPS = [
    "Chrome'da adres çubuğuna chrome://extensions yazıp açın.",
    "Sağ üstteki “Geliştirici modu” anahtarını açın.",
    "“Paketlenmemiş öğe yükle” düğmesine basın ve bu klasörü seçin: programın klasöründeki eklenti klasörü.",
    "Araç çubuğundaki yapboz simgesine tıklayıp “30A Studio Yardımcısı”nı sabitleyin (raptiye).",
    "Eklenti simgesine tıklayın; açılan pencereye bu ekrandaki eşleşme kodunu yazıp “Eşleştir”e basın.",
    "Bu ekrandaki “Deneme” düğmesine basın; programın kendi deneme sayfası eklentiyle açılır ve sonucu burada görünür.",
]
EXTENSION_TRIAL_PAGE = """<!doctype html><html lang="tr"><head><meta charset="utf-8"><title>30A Studio · eklenti deneme sayfası</title></head>
<body><h1>30A Studio eklenti deneme sayfası</h1><p>Bu sayfa programın kendi yerel sayfasıdır; gerçek bir site değildir.</p>
<p id="bekleniyor">Sayfanın bir bölümü JavaScript ile çiziliyor…</p>
<script>setTimeout(() => { const p = document.createElement('p'); p.id = 'deneme-sonuc'; p.textContent = 'JavaScript ile çizilen bölüm hazır.';
document.body.appendChild(p); document.getElementById('bekleniyor').remove(); }, 1500);</script></body></html>"""
DEFAULT_DATA = Path(__file__).resolve().parent.parent / "data"


def create_app(data_dir: Path | None = None, registry=None, watchdog: Watchdog | None = None):
    registry = registry or DEFAULT_REGISTRY
    db = Database((data_dir or DEFAULT_DATA) / "studio.sqlite3", registry)

    @asynccontextmanager
    async def lifespan(app):
        db.initialize()
        db.recover_jobs()
        app.state.claude = ClaudeService(db, db.path.parent)
        app.state.claude.recover()
        app.state.text = TextService(db, db.path.parent, app.state.claude)      # GÖREV-15: the video text's chain
        app.state.text.recover()
        app.state.claude.text = app.state.text
        app.state.jobs = JobQueue(db, extension=app.state.extension)
        app.state.batches = refresh.BatchRunner(db, app.state.jobs)
        app.state.batches.recover()
        try:
            yield
        finally:
            app.state.batches.shutdown()
            app.state.text.shutdown()
            app.state.claude.shutdown()
            app.state.jobs.shutdown()

    app = FastAPI(title="30A Studio", version=__version__, lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.db = db
    app.state.watchdog = watchdog or Watchdog.from_env(has_active_jobs=db.has_active_work, on_waiting=db.note_active_jobs)
    app.state.extension = ext.ExtensionBridge(db.path.parent)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])

    def extension_cors(response, origin):
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
        return response

    @app.middleware("http")
    async def local_requests(request: Request, call_next):
        if request.url.path.startswith(EXTENSION_PREFIX):
            # GÖREV-14: the extension's API answers only the paired extension's origin with the pairing code; CORS only for it
            origin, bridge = request.headers.get("origin") or "", request.app.state.extension
            pairing = request.url.path == EXTENSION_PREFIX + "eslestir"
            allowed = origin.startswith(ext.ORIGIN_PREFIX) and (pairing or origin == bridge.config.get("koken"))
            if request.method == "OPTIONS":
                if not allowed:
                    return JSONResponse({"detail": "Bu köken eklenti API'sine erişemez."}, status_code=403)
                response = Response(status_code=204)
                response.headers["Access-Control-Allow-Methods"] = "POST"
                response.headers["Access-Control-Allow-Headers"] = f"content-type, {ext.HEADER}"
                response.headers["Access-Control-Max-Age"] = "600"
                return extension_cors(response, origin)
            if request.method != "POST" or not allowed:
                return JSONResponse({"detail": "Bu köken eklenti API'sine erişemez."}, status_code=403)
            if not pairing and not bridge.authorized(origin, request.headers.get(ext.HEADER)):
                return extension_cors(JSONResponse({"detail": "Eşleşme kodu geçersiz; Ayarlar → Tarayıcı eklentisi ekranındaki kodu yeniden yazın."},
                                                   status_code=403), origin)
            return extension_cors(await call_next(request), origin)
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            # GÖREV-14: the user's browser now talks to the program; a state-changing request from another site is refused
            if request.headers.get("sec-fetch-site") not in (None, "same-origin", "none"):
                return JSONResponse({"detail": "Bu istek uygulama penceresinden gelmiyor."}, status_code=403)
            origin = request.headers.get("origin")
            if origin and urlsplit(origin).netloc != request.headers.get("host"):
                return JSONResponse({"detail": "Bu istek uygulama penceresinden gelmiyor."}, status_code=403)
            if request.headers.get("x-studio-request") != "1":
                return JSONResponse({"detail": "Uygulama isteği doğrulanamadı."}, status_code=403)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.exception_handler(Conflict)
    async def conflict_handler(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.get("/")
    def index():
        return FileResponse(WEB / "index.html")

    @app.get("/api/health")
    def health():
        return {"app": "thirtya-studio", "version": __version__, "pid": os.getpid()}

    @app.post("/api/heartbeat", status_code=204)
    def heartbeat(request: Request):
        request.app.state.watchdog.heartbeat()
        return Response(status_code=204)

    def selected(identifier):
        try: return db.destination(identifier)
        except KeyError: raise HTTPException(404, "Destinasyon bulunamadı veya etkin değil.") from None

    @app.get("/api/destinations")
    def destinations():
        return db.destinations()

    @app.get("/api/bootstrap")
    def bootstrap(destination_id: str = DEFAULT_DESTINATION_ID):
        destination=selected(destination_id)
        context=db.context(destination_id)
        source_list=sources(destination_id)
        ready_count=sum(bool(source["enabled"] and source["connector"]) for source in source_list)
        return {"version": __version__, "destinations":db.destinations(), "selected_destination":destination,
                "categories": CATEGORIES, "regions": [f"Tüm {destination['name']}",*[r['name'] for r in context.canonical_regions]], "methods": METHODS,
                "cadences": CADENCES, "steps": [dict(id=id_, title=title, subtitle=f"{ready_count} kaynak hazır" if id_=="collect" else subtitle, state=state)
                                               for id_, title, subtitle, state in STEPS],
                "sources": source_list, "jobs": db.jobs(destination_id), "data_path": str(db.path.parent),
                "canonical_regions": context.canonical_regions,
                "collections": db.collections(destination_id), "weather_runs": weather_runs(destination_id),
                "restaurant_runs": restaurant_runs(destination_id),
                "restaurant_connector": {"name": "south-walton-restaurants", "method": "HTML"},
                "restaurant_site_runs": restaurant_site_runs(destination_id),
                "restaurant_site_connector": {"name": restaurant_sites.RestaurantSitesConnector.name, "method": "HTML/PDF"},
                "neighborhood_runs": neighborhood_runs(destination_id),
                "neighborhood_connector": {"name": neighborhoods.NeighborhoodsConnector.name, "method": "HTML",
                                           "source_url": neighborhoods.SOURCE_URL, "scope": neighborhoods.SCOPE},
                "beach_neighborhoods": beach_neighborhoods(destination_id),
                "climate_runs": climate_runs(destination_id),
                "lodging_runs": lodging_runs(destination_id),
                "lodging_connector": {"name": bookdirect_lodging.BookDirectLodgingConnector.name, "method": "JSON",
                                      "scope": bookdirect_lodging.SCOPE, "config": context.lodging,
                                      "window_rule_text": windows.rule_text((context.lodging or {}).get("window_rule")) if (context.lodging or {}).get("window_rule") else None},
                "refresh": refresh.status(db, destination_id),
                "daily_needs_runs": daily_needs_runs(destination_id),
                "daily_needs_connector": {"name": daily_needs.DailyNeedsConnector.name, "method": "API", "attribution": daily_needs.ATTRIBUTION,
                                          "config": context.daily_needs and {k: context.daily_needs[k] for k in ("area", "categories")}},
                "agency_runs": agency_runs(destination_id),
                "agency_connector": {"name": agency_rates.AgencyRatesConnector.name, "method": "HTML/JSON", "scope": agency_rates.SCOPE,
                                     "sites": (context.agency or {}).get("sites", [])},
                "climate_connectors": {"normals": climate_normals.ClimateNormalsConnector.name,
                                       "water": water_temperature.WaterTemperatureConnector.name,
                                       "storms": storm_proximity.StormProximityConnector.name},
                "weather_connector": {"name": "nws-weather", "method": "API", "anchors": context.weather_anchors,
                                      "provenance": {"scope":"Destinasyonda yapılandırılmış hava örnek noktaları."}},
                "beach_connector": {"name": "south-walton-beaches", "source_url": beaches.SOURCE_URL, "method": "JSON", "scope": beaches.SCOPE,
                                    "feature_labels": beaches.FEATURE_LABELS}}

    # --- Browser extension (GÖREV-14, Adım 7) ------------------------------------------------------------------------------------

    def bridge():
        return app.state.extension

    async def json_body(request):
        try:
            body = await request.json()
        except ValueError:
            raise HTTPException(422, "İstek okunamadı.") from None
        if not isinstance(body, dict):
            raise HTTPException(422, "İstek okunamadı.")
        return body

    @app.post("/api/eklenti/eslestir")
    async def extension_pair(request: Request):
        body = await json_body(request)
        if not bridge().pair(request.headers.get("origin"), request.headers.get(ext.HEADER), body.get("surum")):
            raise HTTPException(403, "Eşleşme kodu yanlış ya da program başka bir eklentiyle eşleşmiş. Ayarlar → Tarayıcı eklentisi ekranındaki "
                                     "kodu yazın; gerekirse “Kodu yenile” ile yeni kod alın.")
        return {"eslesti": True, "program": "thirtya-studio", "surum": __version__, "aralik_saniye": bridge().gap()}

    @app.post("/api/eklenti/sor")
    async def extension_ask(request: Request):
        body = await json_body(request)
        bridge().touch(body.get("surum"), body.get("izinli"))
        return {"is": bridge().take(), "aralik_saniye": bridge().gap(), "sorma_araligi_saniye": 3,
                "izin_bekleyen": sorted(bridge().pending)}

    @app.post("/api/eklenti/is/{session_id}/sonraki")
    def extension_next(session_id: str):
        bridge().last_seen = bridge().clock()
        return bridge().next_item(session_id)

    @app.post("/api/eklenti/is/{session_id}/sonuc")
    async def extension_result(session_id: str, request: Request):
        body = await json_body(request)
        if not bridge().deliver(session_id, str(body.get("oge_id") or ""), body):
            raise HTTPException(404, "Bu iş ya da sayfa beklenmiyor.")
        return {"alindi": True}

    @app.post("/api/eklenti/is/{session_id}/durum")
    async def extension_state(session_id: str, request: Request):
        body = await json_body(request)
        found = bridge().report(session_id, verifying=body.get("dogrulama") if isinstance(body.get("dogrulama"), str) else None,
                                missing=body.get("izin_yok") if isinstance(body.get("izin_yok"), str) else None)
        if not found:
            raise HTTPException(404, "Bu iş bulunamadı.")
        return {"alindi": True}

    @app.post("/api/eklenti/is/{session_id}/bitti")
    async def extension_done(session_id: str, request: Request):
        body = await json_body(request)
        bridge().finished(session_id, body.get("hata") if isinstance(body.get("hata"), str) else None)
        return {"alindi": True}

    @app.get("/api/tarayici-eklentisi")
    def extension_settings(destination_id: str = DEFAULT_DESTINATION_ID):
        """Settings → Tarayıcı eklentisi: connection, pairing code, domains, speed, install steps, the trial sites."""
        selected(destination_id)
        profile = PROFILES.get(destination_id)
        pictures = sorted(p.name for p in (EXTENSION_DIR / "kurulum").glob("*.png")) if (EXTENSION_DIR / "kurulum").is_dir() else []
        return {**bridge().status(), "klasor": str(EXTENSION_DIR), "kurulum": EXTENSION_STEPS, "kurulum_resimleri": pictures,
                "sorunlu_siteler": [{"alan_adi": d, "adres": u, "aciklama": n} for d, u, n in getattr(profile, "EXTENSION_TRIAL_SITES", ())]}

    @app.post("/api/tarayici-eklentisi/kod-yenile")
    def extension_renew():
        bridge().renew()
        return bridge().status()

    @app.put("/api/tarayici-eklentisi/ayarlar")
    async def extension_speed(request: Request):
        body = await json_body(request)
        try:
            bridge().set_gap(body.get("aralik_saniye"))
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return bridge().status()

    def trial_read(url, label, *, wait=None, timeout=240):
        if not bridge().paired:
            raise Conflict("Eklenti eşleşmemiş: önce kurulum adımlarını izleyip eşleşme kodunu eklentiye yazın.")
        if not bridge().connected:
            raise Conflict("Eklenti bağlı değil: Chrome'u açın (eklenti açıkken birkaç saniyede bir programa bağlanır).")
        session = bridge().open(ext.domain_of(url), purpose=label)
        try:
            result = session.page(url, wait or {"saniye": 3}, timeout=timeout)
        except ext.ExtensionError as exc:
            raise Conflict(str(exc)) from exc
        finally:
            session.close()
        return bridge().save_raw(result, label)

    @app.post("/api/tarayici-eklentisi/deneme")
    async def extension_trial(request: Request):
        """"Deneme": the extension opens the program's own local trial page (not a real site) and the result is shown."""
        url = str(request.base_url).rstrip("/") + "/eklenti-deneme"
        return await asyncio.to_thread(trial_read, url, "deneme", wait={"oge": "#deneme-sonuc"}, timeout=120)

    @app.post("/api/tarayici-eklentisi/sorunlu-siteler", status_code=201)
    def extension_problem_sites(destination_id: str = DEFAULT_DESTINATION_ID):
        """"Sorunlu sitelerden birer sayfa dene": one page of each site, read by the extension in a background job (the user presses it)."""
        selected(destination_id)
        profile = PROFILES.get(destination_id)
        sites = list(getattr(profile, "EXTENSION_TRIAL_SITES", ()))
        if not sites:
            raise HTTPException(404, "Bu destinasyon için sorunlu site listesi yok.")
        if not bridge().paired:
            raise Conflict("Eklenti eşleşmemiş: önce eşleşme kodunu eklentiye yazın.")
        job_id = db.add_job("eklenti_deneme", "Tarayıcı eklentisi · sorunlu sitelerden birer sayfa", destination_id=destination_id)

        def work():
            access = ext.JobAccess(bridge(), db, job_id)
            rows = []
            db.update_job(job_id, status="running", progress=1, message=f"{len(sites)} site eklentiyle okunacak.")
            for number, (domain, url, note) in enumerate(sites, 1):
                job = db.job(job_id)
                if not job or job["status"] not in ("queued", "running"):
                    return
                try:
                    session = access.open(domain, purpose="sorunlu site denemesi")
                    try:
                        result = session.page(url, {"saniye": 5}, canceled=lambda: (db.job(job_id) or {}).get("status") not in ("queued", "running"))
                    finally:
                        session.close()
                    record = bridge().save_raw(result, f"sorunlu site · {domain}")
                    rows.append({"alan_adi": domain, "aciklama": note, "durum": result["durum"], "baslik": result.get("baslik"),
                                 "http_durumu": result.get("http_durumu"), "bayt": record["bayt"], "sha256": record["sha256"], "dosya": record["dosya"],
                                 "not": result.get("not")})
                except Exception as exc:
                    rows.append({"alan_adi": domain, "aciklama": note, "durum": "hata", "not": f"{type(exc).__name__}: {str(exc)[:160]}"})
                db.update_job(job_id, progress=int(100 * number / len(sites)), message=f"{number}/{len(sites)} · {domain}: {rows[-1]['durum']}")
            db.update_job(job_id, status="done", progress=100, result={"siteler": rows},
                          message=f"{sum(r['durum'] == 'tamam' for r in rows)}/{len(rows)} site eklentiyle okundu.")

        threading.Thread(target=work, name="eklenti-deneme", daemon=True).start()
        return db.job(job_id)

    @app.post("/api/tarayici-eklentisi/devret/{job_id}")
    def extension_hand_over(job_id: str):
        """The job panel's "Programın tarayıcısına devret": the job's pages go to the program's own browser."""
        if db.job(job_id) is None:
            raise HTTPException(404, "İş bulunamadı.")
        reason = bridge().hand_over(job_id)
        db.update_job(job_id, message=reason, progress_info={"tur": "eklenti", "bekliyor": False, "devredildi": True})
        return db.job(job_id)

    @app.get("/eklenti-kurulum/{name}")
    def extension_guide_image(name: str):
        """The install guide's pictures (eklenti/kurulum/*.png) for Settings → Tarayıcı eklentisi."""
        path = (EXTENSION_DIR / "kurulum" / name).resolve()
        if path.parent != (EXTENSION_DIR / "kurulum").resolve() or path.suffix != ".png" or not path.is_file():
            raise HTTPException(404, "Resim bulunamadı.")
        return FileResponse(path, media_type="image/png")

    @app.get("/eklenti-deneme")
    def extension_trial_page():
        return Response(EXTENSION_TRIAL_PAGE, media_type="text/html; charset=utf-8")

    @app.get("/api/workflow")
    def workflow_view(destination_id: str = DEFAULT_DESTINATION_ID, video_id: str | None = None):
        """The eight steps of the selected video with live statuses, computed from the records (GÖREV-14)."""
        selected(destination_id)
        return workflow.compute(db, destination_id, video_id)

    @app.get("/api/sources")
    def sources(destination_id: str = DEFAULT_DESTINATION_ID):
        selected(destination_id)
        result = []
        for source in db.sources(destination_id):
            connector = registry.for_source(source)
            result.append({**source, "connector": {"name": connector.name, "version": connector.version, "method": getattr(connector, "method", None)} if connector else None})
        return result

    @app.post("/api/sources", status_code=201)
    def add_source(body: SourceInput):
        destination=selected(body.destination_id)
        record=body.record()
        if not record["region"]: record["region"]=f"Tüm {destination['name']}"
        return db.save_source(record)

    @app.put("/api/sources/{identifier}")
    def update_source(identifier: str, body: SourceUpdate):
        try:
            existing=db.source(identifier)
            if not existing: raise KeyError(identifier)
            record=body.record()
            record["destination_id"]=body.destination_id or existing["destination_id"]
            selected(record["destination_id"])
            return db.save_source(record, identifier, body.expected_version)
        except KeyError:
            raise HTTPException(404, "Kaynak bulunamadı.") from None

    @app.get("/api/jobs")
    def jobs(destination_id: str = DEFAULT_DESTINATION_ID):
        selected(destination_id)
        return db.jobs(destination_id)

    @app.post("/api/jobs", status_code=202)
    def start_job(body: JobInput, request: Request):
        if body.kind in ("source_collection", "beach_collection"):
            if not body.source_id:
                raise HTTPException(422, "Veri toplamak için bir kaynak seçin.")
            source=db.source(body.source_id)
            if not source: raise HTTPException(409,"Kaynak bulunamadı.")
            selected(source["destination_id"])
            if body.destination_id and body.destination_id != source["destination_id"]:
                raise HTTPException(409,"Kaynak seçili destinasyona ait değil.")
            return request.app.state.jobs.submit_collection(body.source_id)
        destination_id=body.destination_id or DEFAULT_DESTINATION_ID
        selected(destination_id)
        return request.app.state.jobs.submit_audit(destination_id)

    @app.get("/api/refresh")
    def refresh_status(destination_id: str = DEFAULT_DESTINATION_ID):
        selected(destination_id)
        return refresh.status(db, destination_id)

    @app.post("/api/refresh-batches", status_code=202)
    def start_refresh(body: JobInput, request: Request):
        destination_id = body.destination_id or DEFAULT_DESTINATION_ID
        selected(destination_id)
        return request.app.state.batches.start(destination_id)

    @app.post("/api/refresh-batches/{identifier}/cancel")
    def cancel_refresh(identifier: str, request: Request):
        result = request.app.state.batches.cancel(identifier)
        if result is None:
            raise HTTPException(404, "Toplu çalıştırma bulunamadı.")
        return result

    @app.post("/api/jobs/{identifier}/cancel")
    def cancel_job(identifier: str, request: Request):
        result = request.app.state.jobs.cancel(identifier)
        if result is None:
            raise HTTPException(404, "İş bulunamadı.")
        return result

    @app.get("/api/collections")
    def collections(destination_id: str = DEFAULT_DESTINATION_ID):
        selected(destination_id)
        return db.collections(destination_id)

    @app.get("/api/source-runs")
    def source_runs(source_id: str | None = None, destination_id: str = DEFAULT_DESTINATION_ID):
        selected(destination_id)
        return db.source_runs(source_id,destination_id)

    @app.get("/api/source-runs/{identifier}")
    def source_run(identifier: str):
        run = db.source_run(identifier)
        if not run:
            raise HTTPException(404, "Kaynak çekimi bulunamadı.")
        return {"run": run, "records": db.run_records(identifier), "diff": db.run_diff(identifier)}

    @app.get("/api/source-runs/{identifier}/diff")
    def source_run_diff(identifier: str):
        result = db.run_diff(identifier)
        if result is None:
            raise HTTPException(404, "Kaynak çekimi bulunamadı.")
        return result

    def find_collection(identifier):
        result = db.collection(identifier)
        if result is None:
            raise HTTPException(404, "Bu veri sürümü bulunamadı.")
        return result

    @app.get("/api/collections/{identifier}")
    def collection(identifier: str):
        return find_collection(identifier)

    @app.get("/api/collections/{identifier}/export.csv")
    def export_collection(identifier: str):
        snapshot = find_collection(identifier)
        output = io.StringIO(newline="")
        writer = csv.writer(output, delimiter=";")
        writer.writerow(["Kaynak kimliği", "Ad", "Kaynakta yerleşim", "Adres", "Tür", "Enlem", "Boylam",
                         "Kaynakta listelenen olanaklar", "Kaynak adresi", "Çekim zamanı (UTC)", "Kaynak güncelleme metni"])
        def cell(value):
            value = str(value or "")
            return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value
        for record in snapshot["records"]:
            writer.writerow([cell(record["external_id"]), cell(record["name"]), cell(record["city"]), cell(record["address"]),
                             "Bölgesel" if record["access_type"] == "regional" else "Mahalle", record["latitude"], record["longitude"],
                             cell(", ".join(beaches.FEATURE_LABELS.get(feature, feature) for feature in record["features"])),
                             snapshot["run"]["source_url"], snapshot["run"]["fetched_at"], cell(snapshot["run"]["source_updated"])])
        return Response(output.getvalue().encode("utf-8-sig"), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="30a-plaj-{identifier[:8]}.csv"'})

    @app.get("/api/collections/{identifier}/raw")
    def raw_collection(identifier: str):
        snapshot = find_collection(identifier)
        path = (db.path.parent / snapshot["run"]["raw_path"]).resolve()
        if not path.is_relative_to(db.path.parent.resolve()) or not path.is_file():
            raise HTTPException(404, "Ham kaynak dosyası bulunamadı.")
        return FileResponse(path, media_type="text/plain", filename=f"30a-ham-kaynak-{identifier[:8]}.html.txt")

    @app.get("/api/beach-neighborhoods")
    def beach_neighborhoods(destination_id: str = DEFAULT_DESTINATION_ID):
        """Committed, reviewable mapping layer from the destination profile; never recomputed here."""
        selected(destination_id)
        path = getattr(PROFILES.get(destination_id), "BEACH_NEIGHBORHOOD_MAPPING", None)
        if path is None:
            return {"available": False, "reason": "Bu destinasyon için plaj–mahalle eşleme dosyası yok.", "rows": []}
        try:
            rows = beach_mapping.load(path, db.context(destination_id).canonical_regions)
        except beach_mapping.MappingError as exc:
            return {"available": False, "reason": str(exc), "rows": []}
        return {"available": True, "file": path.name, "methods": beach_mapping.METHOD_LABELS, "rows": rows}

    @app.get("/api/references")
    def references(destination_id: str = DEFAULT_DESTINATION_ID):
        """Committed, manually verified reference table of the destination profile; read-only."""
        selected(destination_id)
        path = getattr(PROFILES.get(destination_id), "REFERENCE_TABLE", None)
        if path is None:
            return {"available": False, "reason": "Bu destinasyon için referans tablosu yok.", "rows": []}
        try:
            return reference_table.snapshot(path)
        except reference_table.ReferenceError as exc:
            return {"available": False, "reason": str(exc), "rows": []}

    @app.get("/api/weather-runs")
    def weather_runs(destination_id: str = DEFAULT_DESTINATION_ID):
        selected(destination_id)
        return [run for run in db.source_runs(destination_id=destination_id) if run["connector_name"] == "nws-weather" and run["status"] == "done"]

    def find_weather_run(identifier):
        run = db.source_run(identifier)
        if not run or run["connector_name"] != "nws-weather" or run["status"] != "done":
            raise HTTPException(404, "Bu hava veri sürümü bulunamadı.")
        return run

    @app.get("/api/weather-runs/{identifier}")
    def weather_run(identifier: str):
        run = find_weather_run(identifier)
        with db.connect() as con:
            snapshot = weather.WeatherConnector().read_snapshot(con, identifier)
        return {"run": run, **snapshot, "diff": db.run_diff(identifier)}

    @app.get("/api/weather-runs/{identifier}/raw")
    def raw_weather_run(identifier: str):
        run = find_weather_run(identifier)
        path = (db.path.parent / (run["raw_path"] or "")).resolve()
        if not path.is_relative_to((db.path.parent / "raw").resolve()) or not path.is_file():
            raise HTTPException(404, "Ham hava kaynağı bulunamadı.")
        return FileResponse(path, media_type="application/json", filename=f"30a-hava-{identifier[:8]}.json")

    @app.get("/api/restaurant-runs")
    def restaurant_runs(destination_id: str = DEFAULT_DESTINATION_ID):
        selected(destination_id)
        return [run for run in db.source_runs(destination_id=destination_id) if run["connector_name"] == "south-walton-restaurants" and run["status"] == "done"]

    def find_restaurant_run(identifier):
        run = db.source_run(identifier)
        if not run or run["connector_name"] != "south-walton-restaurants" or run["status"] != "done":
            raise HTTPException(404, "Bu restoran veri sürümü bulunamadı.")
        return run

    @app.get("/api/restaurant-runs/{identifier}")
    def restaurant_run(identifier: str):
        run = find_restaurant_run(identifier)
        return {"run": run, "records": db.run_records(identifier), "diff": db.run_diff(identifier)}

    @app.get("/api/restaurant-runs/{identifier}/raw")
    def raw_restaurant_run(identifier: str):
        run = find_restaurant_run(identifier)
        path = (db.path.parent / (run["raw_path"] or "")).resolve()
        root = (db.path.parent / "raw" / identifier).resolve()
        if not path.is_relative_to(root) or path.name != "manifest.json" or not path.is_file():
            raise HTTPException(404, "Ham restoran manifesti bulunamadı.")
        return FileResponse(path, media_type="application/json", filename=f"30a-restoran-{identifier[:8]}.json")

    SITES = restaurant_sites.RestaurantSitesConnector.name

    @app.get("/api/restaurant-site-runs")
    def restaurant_site_runs(destination_id: str = DEFAULT_DESTINATION_ID):
        selected(destination_id)
        return [run for run in db.source_runs(destination_id=destination_id) if run["connector_name"] == SITES and run["status"] == "done"]

    def find_restaurant_site_run(identifier):
        run = db.source_run(identifier)
        if not run or run["connector_name"] != SITES or run["status"] != "done":
            raise HTTPException(404, "Bu işletme sitesi veri sürümü bulunamadı.")
        return run

    @app.get("/api/restaurant-site-runs/{identifier}")
    def restaurant_site_run(identifier: str):
        """Per restaurant price level, main-dish median, reservation and kids menu, and the neighborhood summary; computed when read."""
        run = find_restaurant_site_run(identifier)
        regions = db.context(run["destination_id"]).canonical_regions
        with db.connect() as con:
            summary = restaurant_sites.summarize(con, identifier, [r["id"] for r in regions], {r["id"]: r["name"] for r in regions})
        if summary is None:
            raise HTTPException(404, "Bu sürümün özeti bulunamadı.")
        return {"run": run, **summary}

    @app.get("/api/restaurant-site-runs/{identifier}/restaurant")
    def restaurant_site_detail(identifier: str, external_id: str):
        find_restaurant_site_run(identifier)
        with db.connect() as con:
            detail = restaurant_sites.restaurant_detail(con, identifier, external_id)
        if detail is None:
            raise HTTPException(404, "Bu restoran bu sürümde yok.")
        return detail

    @app.get("/api/restaurant-site-runs/{identifier}/raw")
    def raw_restaurant_site_run(identifier: str):
        run = find_restaurant_site_run(identifier)
        path = (db.path.parent / (run["raw_path"] or "")).resolve()
        root = (db.path.parent / "raw" / identifier).resolve()
        if not path.is_relative_to(root) or path.name != "manifest.json" or not path.is_file():
            raise HTTPException(404, "Ham işletme sitesi manifesti bulunamadı.")
        return FileResponse(path, media_type="application/json", filename=f"30a-isletme-siteleri-{identifier[:8]}.json")

    @app.get("/api/daily-needs-runs")
    def daily_needs_runs(destination_id: str = DEFAULT_DESTINATION_ID):
        selected(destination_id)
        return [run for run in db.source_runs(destination_id=destination_id)
                if run["connector_name"] == daily_needs.DailyNeedsConnector.name and run["status"] == "done"]

    def find_daily_needs_run(identifier):
        run = db.source_run(identifier)
        if not run or run["connector_name"] != daily_needs.DailyNeedsConnector.name or run["status"] != "done":
            raise HTTPException(404, "Bu günlük ihtiyaç sürümü bulunamadı.")
        return run

    @app.get("/api/daily-needs-runs/{identifier}")
    def daily_needs_run(identifier: str):
        """Points of the run and per neighborhood the great-circle distances of the latest lodging run's listings; computed when read."""
        run = find_daily_needs_run(identifier)
        regions = db.context(run["destination_id"]).canonical_regions
        with db.connect() as con:
            summary = daily_needs.summarize(con, identifier, [r["id"] for r in regions], {r["id"]: r["name"] for r in regions})
        if summary is None:
            raise HTTPException(404, "Bu sürümün özeti bulunamadı.")
        return {"run": run, **summary}

    @app.get("/api/daily-needs-runs/{identifier}/raw")
    def raw_daily_needs_run(identifier: str):
        run = find_daily_needs_run(identifier)
        path = (db.path.parent / (run["raw_path"] or "")).resolve()
        root = (db.path.parent / "raw" / identifier).resolve()
        if not path.is_relative_to(root) or path.name != "manifest.json" or not path.is_file():
            raise HTTPException(404, "Ham OpenStreetMap manifesti bulunamadı.")
        return FileResponse(path, media_type="application/json", filename=f"30a-gunluk-ihtiyac-{identifier[:8]}.json")

    @app.get("/api/neighborhood-runs")
    def neighborhood_runs(destination_id: str = DEFAULT_DESTINATION_ID):
        selected(destination_id)
        return [run for run in db.source_runs(destination_id=destination_id)
                if run["connector_name"] == neighborhoods.NeighborhoodsConnector.name and run["status"] == "done"]

    def find_neighborhood_run(identifier):
        run = db.source_run(identifier)
        if not run or run["connector_name"] != neighborhoods.NeighborhoodsConnector.name or run["status"] != "done":
            raise HTTPException(404, "Bu mahalle veri sürümü bulunamadı.")
        return run

    @app.get("/api/neighborhood-runs/{identifier}")
    def neighborhood_run(identifier: str):
        run = find_neighborhood_run(identifier)
        return {"run": run, "records": db.run_records(identifier), "diff": db.run_diff(identifier)}

    @app.get("/api/neighborhood-runs/{identifier}/raw")
    def raw_neighborhood_run(identifier: str):
        run = find_neighborhood_run(identifier)
        path = (db.path.parent / (run["raw_path"] or "")).resolve()
        root = (db.path.parent / "raw" / identifier).resolve()
        if not path.is_relative_to(root) or path.name != "manifest.json" or not path.is_file():
            raise HTTPException(404, "Ham mahalle manifesti bulunamadı.")
        return FileResponse(path, media_type="application/json", filename=f"30a-mahalle-{identifier[:8]}.json")

    CLIMATE = {climate_normals.ClimateNormalsConnector.name: "normals", water_temperature.WaterTemperatureConnector.name: "water",
               storm_proximity.StormProximityConnector.name: "storms"}

    @app.get("/api/climate-runs")
    def climate_runs(destination_id: str = DEFAULT_DESTINATION_ID):
        selected(destination_id)
        return [run for run in db.source_runs(destination_id=destination_id) if run["connector_name"] in CLIMATE and run["status"] == "done"]

    @app.get("/api/climate")
    def climate(destination_id: str = DEFAULT_DESTINATION_ID):
        """Configuration and the latest successful snapshot of each climate connector for one destination."""
        selected(destination_id)
        context = db.context(destination_id)
        result = {"config": {"stations": list(context.climate_stations), "corridor": context.storm_corridor},
                  "normals": None, "water": None, "storms": None}
        for run in climate_runs(destination_id):
            key = CLIMATE[run["connector_name"]]
            if result[key] is None:
                with db.connect() as con:
                    result[key] = {"run": run, **registry.by_name(run["connector_name"]).read_snapshot(con, run["id"])}
        return result

    @app.get("/api/climate-runs/{identifier}/raw")
    def raw_climate_run(identifier: str):
        run = db.source_run(identifier)
        if not run or run["connector_name"] not in CLIMATE or run["status"] != "done":
            raise HTTPException(404, "Bu iklim veri sürümü bulunamadı.")
        path = (db.path.parent / (run["raw_path"] or "")).resolve()
        root = (db.path.parent / "raw" / identifier).resolve()
        if not path.is_relative_to(root) or path.name != "manifest.json" or not path.is_file():
            raise HTTPException(404, "Ham iklim manifesti bulunamadı.")
        return FileResponse(path, media_type="application/json", filename=f"30a-iklim-{identifier[:8]}.json")

    LODGING = bookdirect_lodging.BookDirectLodgingConnector.name

    @app.get("/api/lodging-runs")
    def lodging_runs(destination_id: str = DEFAULT_DESTINATION_ID):
        selected(destination_id)
        return [run for run in db.source_runs(destination_id=destination_id) if run["connector_name"] == LODGING and run["status"] == "done"]

    def find_lodging_run(identifier):
        run = db.source_run(identifier)
        if not run or run["connector_name"] != LODGING or run["status"] != "done":
            raise HTTPException(404, "Bu konaklama veri sürümü bulunamadı.")
        return run

    @app.get("/api/lodging-runs/{identifier}")
    def lodging_run(identifier: str):
        """Region x window summary and monthly calendar medians, computed when read; nothing derived is stored."""
        run = find_lodging_run(identifier)
        order = [region["id"] for region in db.context(run["destination_id"]).canonical_regions]
        with db.connect() as con:
            summary = bookdirect_lodging.summarize(con, identifier, order)
        if summary is None:
            raise HTTPException(404, "Bu konaklama veri sürümünün özeti bulunamadı.")
        return {"run": run, **summary}

    @app.get("/api/lodging-runs/{identifier}/listings")
    def lodging_listings(identifier: str, region_id: str):
        find_lodging_run(identifier)
        with db.connect() as con:
            listings = bookdirect_lodging.region_listings(con, identifier, region_id)
        if listings is None:
            raise HTTPException(404, "Bu mahalle için konaklama araması yok.")
        return {"region_id": region_id, "listings": listings}

    @app.get("/api/lodging-runs/{identifier}/raw")
    def raw_lodging_run(identifier: str):
        run = find_lodging_run(identifier)
        path = (db.path.parent / (run["raw_path"] or "")).resolve()
        root = (db.path.parent / "raw" / identifier).resolve()
        if not path.is_relative_to(root) or path.name != "manifest.json" or not path.is_file():
            raise HTTPException(404, "Ham konaklama manifesti bulunamadı.")
        return FileResponse(path, media_type="application/json", filename=f"konaklama-{identifier[:8]}.json")

    AGENCY = agency_rates.AgencyRatesConnector.name

    @app.get("/api/agency-rate-runs")
    def agency_runs(destination_id: str = DEFAULT_DESTINATION_ID):
        selected(destination_id)
        return [run for run in db.source_runs(destination_id=destination_id) if run["connector_name"] == AGENCY and run["status"] == "done"]

    def find_agency_run(identifier):
        run = db.source_run(identifier)
        if not run or run["connector_name"] != AGENCY or run["status"] != "done":
            raise HTTPException(404, "Bu kiralama şirketi fiyat sürümü bulunamadı.")
        return run

    @app.get("/api/agency-rate-runs/{identifier}")
    def agency_run(identifier: str):
        """Region x window price summary and bedroom medians, computed when read; nothing derived is stored."""
        run = find_agency_run(identifier)
        regions = db.context(run["destination_id"]).canonical_regions
        with db.connect() as con:
            summary = agency_rates.summarize(con, identifier, [r["id"] for r in regions], {r["id"]: r["name"] for r in regions})
        if summary is None:
            raise HTTPException(404, "Bu fiyat sürümünün özeti bulunamadı.")
        return {"run": run, **summary}

    @app.get("/api/agency-rate-runs/{identifier}/listings")
    def agency_listings(identifier: str, region_id: str):
        find_agency_run(identifier)
        with db.connect() as con:
            found = agency_rates.region_listings(con, identifier, region_id) or {}
        return {"region_id": region_id, "listings": found.get("listings", []), "own": found.get("own", [])}

    @app.get("/api/agency-rate-runs/{identifier}/raw")
    def raw_agency_run(identifier: str):
        run = find_agency_run(identifier)
        path = (db.path.parent / (run["raw_path"] or "")).resolve()
        root = (db.path.parent / "raw" / identifier).resolve()
        if not path.is_relative_to(root) or path.name != "manifest.json" or not path.is_file():
            raise HTTPException(404, "Ham fiyat manifesti bulunamadı.")
        return FileResponse(path, media_type="application/json", filename=f"kiralama-fiyat-{identifier[:8]}.json")

    def evidence_templates_of(destination_id):
        try:
            return evidence.destination_templates(PROFILES.get(destination_id))
        except evidence.TemplateError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/api/evidence-templates")
    def evidence_templates(destination_id: str = DEFAULT_DESTINATION_ID):
        """Templates of the destination with their sections and parameter choices (a region parameter offers the canonical regions)."""
        selected(destination_id)
        regions = [{"id": r["id"], "name": r["name"]} for r in db.context(destination_id).canonical_regions]
        return {"templates": [{**{k: t[k] for k in ("key", "version", "title", "question", "dimensions")},
                               "parameters": [{**p, "choices": regions} for p in t["parameters"]],
                               "sections": [{k: s[k] for k in ("key", "title", "question")} for s in t["sections"]]}
                              for t in evidence_templates_of(destination_id).values()]}

    @app.get("/api/evidence-packs")
    def evidence_packs(destination_id: str = DEFAULT_DESTINATION_ID):
        selected(destination_id)
        return evidence.stored(db, destination_id)

    @app.post("/api/evidence-packs", status_code=201)
    async def create_evidence_pack(body: EvidencePackInput):
        """Generate a pack from the latest successful runs and store its Markdown and JSON (dated, with SHA-256) under the data folder."""
        destination_id = body.destination_id or DEFAULT_DESTINATION_ID
        selected(destination_id)
        evidence_templates_of(destination_id)
        def build():
            pack = evidence.generate(db, destination_id, PROFILES.get(destination_id), body.template_key, body.params)
            return evidence.store(db, pack)
        try:
            return await asyncio.to_thread(build)
        except evidence.PackError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/evidence-packs/{identifier}/{kind}")
    def evidence_pack_file(identifier: str, kind: str):
        """The full pack (markdown, json) or a file attached to it (sayilar: number checklist CSV, yazar-ozeti: writer's summary)."""
        kinds = {"markdown": ("md", "text/markdown; charset=utf-8"), "json": ("json", "application/json"),
                 "sayilar": ("sayilar", "text/csv; charset=utf-8"), "yazar-ozeti": ("yazar_ozeti", "text/markdown; charset=utf-8")}
        if kind not in kinds:
            raise HTTPException(404, "Bilinmeyen dosya türü.")
        try:
            path, record = evidence.stored_file(db, identifier, kinds[kind][0])
        except evidence.PackError as exc:
            raise HTTPException(404, str(exc)) from exc
        return FileResponse(path, media_type=kinds[kind][1], filename=path.name)

    # --- Claude (GÖREV-13): settings, runs of the steps, approval, video records -----------------------------------------------------

    def claude():
        return app.state.claude

    @app.get("/api/settings/claude")
    def claude_settings_view():
        values = claude_settings.load(db.path.parent)
        from .ai import claude_info
        return {"settings": {k: v for k, v in values.items() if k != "notes"}, "notes": values["notes"], "options": claude_settings.options(),
                "info": claude_info.info(values["claude_path"])}

    @app.put("/api/settings/claude")
    async def claude_settings_save(request: Request):
        try:
            body = await request.json()
        except ValueError:
            raise HTTPException(422, "Ayarlar okunamadı.") from None
        if not isinstance(body, dict):
            raise HTTPException(422, "Ayarlar okunamadı.")
        try:
            claude_settings.save(db.path.parent, body)
        except claude_settings.SettingsError as exc:
            raise HTTPException(422, f"{exc.field}: {exc.message}") from exc
        return claude_settings_view()

    @app.get("/api/settings/title-suffix")
    def title_suffix_view(destination_id: str = DEFAULT_DESTINATION_ID):
        """The destination's title suffixes (GÖREV-14): written into every title and evaluation run's secim.md and checked on every title."""
        selected(destination_id)
        return claude_settings.title_suffixes(db.path.parent, destination_id, PROFILES.get(destination_id))

    @app.put("/api/settings/title-suffix")
    async def title_suffix_save(request: Request, destination_id: str = DEFAULT_DESTINATION_ID):
        selected(destination_id)
        try:
            body = await request.json()
        except ValueError:
            raise HTTPException(422, "Ayarlar okunamadı.") from None
        if not isinstance(body, dict):
            raise HTTPException(422, "Ayarlar okunamadı.")
        try:
            return claude_settings.save_title_suffixes(db.path.parent, destination_id, PROFILES.get(destination_id), body)
        except claude_settings.SettingsError as exc:
            raise HTTPException(422, exc.message) from exc

    @app.get("/api/claude/usage")
    def claude_usage():
        """The usage panel (GÖREV-14): the newest measurement, its age and this week's runs."""
        return claude().usage()

    @app.post("/api/claude/usage/refresh")
    def claude_usage_refresh():
        return claude().refresh_usage()

    def instruction_or_404(action):
        from .ai import instructions
        try:
            return action(instructions)
        except KeyError:
            raise HTTPException(404, "Talimat dosyası ya da sürümü bulunamadı.") from None
        except instructions.InstructionError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/claude/instructions")
    def claude_instructions(destination_id: str = DEFAULT_DESTINATION_ID):
        """Settings → Talimatlar (GÖREV-14): the destination's instruction files; the repository file is the single source."""
        selected(destination_id)
        return instruction_or_404(lambda m: [m.summary(item) for item in m.files(PROFILES.get(destination_id))])

    @app.get("/api/claude/instructions/{key}")
    def claude_instruction(key: str, destination_id: str = DEFAULT_DESTINATION_ID):
        selected(destination_id)
        return instruction_or_404(lambda m: m.read(db.path.parent, PROFILES.get(destination_id), key))

    @app.put("/api/claude/instructions/{key}")
    async def claude_instruction_save(key: str, request: Request, destination_id: str = DEFAULT_DESTINATION_ID):
        selected(destination_id)
        try:
            body = await request.json()
        except ValueError:
            raise HTTPException(422, "Talimat okunamadı.") from None
        if not isinstance(body, dict) or not isinstance(body.get("text"), str) or not isinstance(body.get("base_sha256"), str):
            raise HTTPException(422, "Talimat metni ve açıldığı hâlin karması gerekir.")
        return instruction_or_404(lambda m: m.write(db.path.parent, PROFILES.get(destination_id), key, body["text"], body["base_sha256"]))

    @app.get("/api/claude/instructions/{key}/versions/{version}")
    def claude_instruction_version(key: str, version: str, destination_id: str = DEFAULT_DESTINATION_ID):
        selected(destination_id)
        return {"id": version, "text": instruction_or_404(lambda m: m.version_text(db.path.parent, PROFILES.get(destination_id), key, version))}

    @app.post("/api/claude/instructions/{key}/versions/{version}/restore")
    async def claude_instruction_restore(key: str, version: str, request: Request, destination_id: str = DEFAULT_DESTINATION_ID):
        selected(destination_id)
        try:
            body = await request.json()
        except ValueError:
            raise HTTPException(422, "İstek okunamadı.") from None
        if not isinstance(body, dict) or not isinstance(body.get("base_sha256"), str):
            raise HTTPException(422, "Dosyanın açıldığı hâlin karması gerekir.")
        return instruction_or_404(lambda m: m.restore(db.path.parent, PROFILES.get(destination_id), key, version, body["base_sha256"]))

    @app.get("/api/claude/options")
    def claude_options(destination_id: str = DEFAULT_DESTINATION_ID):
        selected(destination_id)
        return claude().options(destination_id)

    @app.get("/api/claude/runs")
    def claude_runs(destination_id: str = DEFAULT_DESTINATION_ID):
        selected(destination_id)
        return claude().runs(destination_id)

    @app.post("/api/claude/title-runs", status_code=201)
    def start_title_run(body: TitleRunInput):
        destination_id = body.destination_id or DEFAULT_DESTINATION_ID
        selected(destination_id)
        return claude().start_title(destination_id, body.bolge, body.aile, body.not_)

    @app.post("/api/claude/review-runs", status_code=201)
    def start_review_run(body: ReviewRunInput):
        """GÖREV-14: Claude evaluates the user's own title or idea."""
        destination_id = body.destination_id or DEFAULT_DESTINATION_ID
        selected(destination_id)
        return claude().start_review(destination_id, body.bolge, body.baslik, body.not_)

    def claude_run_or_404(identifier, action):
        try:
            return action()
        except KeyError:
            raise HTTPException(404, "Claude çalışması ya da video kaydı bulunamadı.") from None

    @app.get("/api/claude/runs/{identifier}")
    def claude_run(identifier: str):
        return claude_run_or_404(identifier, lambda: claude().view(identifier))

    @app.post("/api/claude/runs/{identifier}/select", status_code=201)
    def claude_select(identifier: str, body: RunDecisionInput):
        if body.aday is None:
            raise HTTPException(422, "Seçilecek aday belirtilmedi.")
        return claude_run_or_404(identifier, lambda: claude().select(identifier, body.aday, body.not_, body.baslik_en, body.baslik_tr))

    @app.post("/api/claude/runs/{identifier}/translate", status_code=201)
    def claude_translate(identifier: str, body: TranslateInput):
        """GÖREV-14: "İngilizcesini Claude yazsın" — an evaluation run with the edited Turkish title."""
        return claude_run_or_404(identifier, lambda: claude().translate(identifier, body.aday, body.baslik_tr))

    @app.post("/api/claude/runs/{identifier}/reject")
    def claude_reject(identifier: str, body: RunDecisionInput):
        return claude_run_or_404(identifier, lambda: claude().reject(identifier, body.not_))

    @app.post("/api/claude/runs/{identifier}/correct", status_code=201)
    def claude_correct(identifier: str, body: RunDecisionInput):
        return claude_run_or_404(identifier, lambda: claude().correct(identifier, body.not_))

    @app.get("/api/claude/runs/{identifier}/files/{name}")
    def claude_run_file(identifier: str, name: str):
        """A file of a run's folder (inputs, task text, output, Markdown, run record); the stream only by name."""
        record = claude_run_or_404(identifier, lambda: claude().view(identifier))
        folder = (db.path.parent / record["folder"]).resolve()
        path = (folder / name).resolve()
        if path.parent != folder or not path.is_file():
            raise HTTPException(404, "Dosya bulunamadı.")
        media = "application/json" if path.suffix == ".json" else "text/markdown; charset=utf-8" if path.suffix == ".md" else "text/plain; charset=utf-8"
        return FileResponse(path, media_type=media, filename=path.name)

    @app.get("/api/videos")
    def videos(destination_id: str = DEFAULT_DESTINATION_ID):
        selected(destination_id)
        return claude().videos(destination_id)

    @app.post("/api/videos/{identifier}/evidence-pack", status_code=201)
    async def video_evidence_pack(identifier: str):
        try:
            return await asyncio.to_thread(claude().video_pack, identifier)
        except KeyError:
            raise HTTPException(404, "Video kaydı bulunamadı.") from None

    # --- Video metni (GÖREV-15): the writing chain, its runs, the comparison of tones, versions and the choice; Settings → Tonlar ----------

    def text():
        return app.state.text

    def text_or_404(action):
        from .ai import tones
        try:
            return action()
        except KeyError:
            raise HTTPException(404, "Video, metin çalışması, sürüm ya da ton bulunamadı.") from None
        except tones.ToneError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/videos/{video_id}/metin")
    def text_options(video_id: str):
        return text_or_404(lambda: text().options(video_id))

    @app.post("/api/videos/{video_id}/metin", status_code=201)
    def text_start(video_id: str, body: TextRunInput):
        return text_or_404(lambda: text().start(video_id, body.tonlar))

    @app.get("/api/videos/{video_id}/metin/karsilastirma")
    def text_compare(video_id: str, calisma: str | None = None):
        return text_or_404(lambda: text().compare(video_id, calisma))

    @app.get("/api/metin/calismalar/{run_id}")
    def text_run(run_id: str):
        return text_or_404(lambda: text().view(run_id))

    @app.post("/api/metin/calismalar/{run_id}/devam")
    def text_resume(run_id: str):
        return text_or_404(lambda: text().resume(run_id))

    @app.post("/api/metin/calismalar/{run_id}/durdur")
    def text_stop(run_id: str):
        return text_or_404(lambda: text().stop(run_id))

    @app.post("/api/metin/calismalar/{run_id}/ton", status_code=201)
    def text_add_tone(run_id: str, body: TextToneInput):
        return text_or_404(lambda: text().add_tone(run_id, body.ton))

    @app.post("/api/metin/calismalar/{run_id}/yeniden-planla", status_code=201)
    async def text_replan(run_id: str, request: Request):
        try:
            body = await request.json()
        except ValueError:
            body = {}
        chosen = body.get("tonlar") if isinstance(body, dict) else None
        if chosen is not None and (not isinstance(chosen, list) or not all(isinstance(i, str) for i in chosen)):
            raise HTTPException(422, "Tonlar bir liste olmalı.")
        return text_or_404(lambda: text().replan(run_id, chosen))

    @app.get("/api/metin/surumler/{version_id}")
    def text_version(version_id: str):
        return text_or_404(lambda: text().version_view(version_id))

    @app.get("/api/metin/surumler/{version_id}/dosya/{kind}")
    def text_version_file(version_id: str, kind: str):
        path, media, name = text_or_404(lambda: text().file(version_id, kind))
        return FileResponse(path, media_type=f"{media}; charset=utf-8", filename=name)

    @app.post("/api/metin/surumler/{version_id}/sec")
    def text_select(version_id: str, body: TextSelectInput):
        return text_or_404(lambda: text().select(version_id, body.not_))

    def tone_profile(destination_id):
        selected(destination_id)
        profile = PROFILES.get(destination_id)
        if not (getattr(profile, "TEXT", None) or {}).get("tones"):
            raise HTTPException(404, "Bu destinasyonun tonları yok.")
        return profile

    @app.get("/api/tonlar")
    def tones_list(destination_id: str = DEFAULT_DESTINATION_ID):
        from .ai import tones
        from .text import store as text_store
        return tones.listing(db.path.parent, destination_id, tone_profile(destination_id), text_store.tone_usage(db))

    @app.post("/api/tonlar", status_code=201)
    def tones_create(body: ToneInput, destination_id: str = DEFAULT_DESTINATION_ID):
        from .ai import tones
        profile = tone_profile(destination_id)
        return text_or_404(lambda: tones.create(db.path.parent, profile, body.ad, body.metin))

    @app.get("/api/tonlar/{stem}")
    def tones_read(stem: str, destination_id: str = DEFAULT_DESTINATION_ID):
        from .ai import tones
        profile = tone_profile(destination_id)
        return text_or_404(lambda: tones.read(db.path.parent, profile, stem))

    @app.put("/api/tonlar/{stem}")
    def tones_update(stem: str, body: ToneInput, destination_id: str = DEFAULT_DESTINATION_ID):
        from .ai import tones
        profile = tone_profile(destination_id)
        if not body.base_sha256:
            raise HTTPException(422, "Dosyanın açıldığı hâlin karması gerekir.")
        return text_or_404(lambda: tones.update(db.path.parent, profile, stem, body.ad, body.metin, body.base_sha256))

    @app.delete("/api/tonlar/{stem}")
    def tones_delete(stem: str, destination_id: str = DEFAULT_DESTINATION_ID):
        from .ai import tones
        profile = tone_profile(destination_id)
        return text_or_404(lambda: tones.delete(db.path.parent, destination_id, profile, stem))

    @app.post("/api/tonlar/{stem}/varsayilan")
    def tones_default(stem: str, destination_id: str = DEFAULT_DESTINATION_ID):
        from .ai import tones
        profile = tone_profile(destination_id)
        return text_or_404(lambda: {"varsayilan": tones.set_default(db.path.parent, destination_id, profile, stem)})

    @app.get("/api/tonlar/{stem}/surumler/{version}")
    def tones_version(stem: str, version: str, destination_id: str = DEFAULT_DESTINATION_ID):
        from .ai import tones
        tone_profile(destination_id)
        return text_or_404(lambda: tones.version_text(db.path.parent, stem, version))

    @app.post("/api/tonlar/{stem}/surumler/{version}/geri-don")
    def tones_restore_version(stem: str, version: str, body: ToneRestoreInput, destination_id: str = DEFAULT_DESTINATION_ID):
        from .ai import tones
        profile = tone_profile(destination_id)
        return text_or_404(lambda: tones.restore_version(db.path.parent, profile, stem, version, body.base_sha256))

    @app.post("/api/ton-arsivi/{archive_id}/geri-al")
    def tones_unarchive(archive_id: str, destination_id: str = DEFAULT_DESTINATION_ID):
        from .ai import tones
        profile = tone_profile(destination_id)
        return text_or_404(lambda: tones.restore_archived(db.path.parent, profile, archive_id))

    @app.get("/api/events")
    async def events(request: Request, destination_id: str = DEFAULT_DESTINATION_ID):
        selected(destination_id)
        guard = request.app.state.watchdog
        stopping = getattr(request.app.state, "should_stop", lambda: False)   # set by the launcher (GÖREV-14)
        async def stream():
            previous = None
            guard.stream_opened()
            try:
                while not stopping() and not await request.is_disconnected():
                    data = json.dumps(await asyncio.to_thread(db.jobs,destination_id), ensure_ascii=False)
                    if data != previous:
                        yield f"event: jobs\ndata: {data}\n\n"
                        previous = data
                    else:
                        yield ": ping\n\n"
                    await asyncio.sleep(1)
            finally:
                guard.stream_closed()
        return StreamingResponse(stream(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"})

    app.mount("/static", StaticFiles(directory=WEB), name="static")
    return app
