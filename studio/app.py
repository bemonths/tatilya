import asyncio
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
from . import refresh
from .models import EvidencePackInput, JobInput, RunDecisionInput, SourceInput, SourceUpdate, TitleRunInput
from . import evidence
from .ai import settings as claude_settings
from .ai.service import ClaudeService
from .watchdog import Watchdog
from .sources import agency_rates, beaches, bookdirect_lodging, climate_normals, daily_needs, neighborhoods, restaurant_sites, storm_proximity, water_temperature, weather, windows
from .sources.registry import DEFAULT_REGISTRY
from .destinations import DEFAULT_DESTINATION_ID, PROFILES, beach_neighborhoods as beach_mapping, references as reference_table

WEB = Path(__file__).parent / "web"
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
        app.state.jobs = JobQueue(db)
        app.state.batches = refresh.BatchRunner(db, app.state.jobs)
        app.state.batches.recover()
        try:
            yield
        finally:
            app.state.batches.shutdown()
            app.state.claude.shutdown()
            app.state.jobs.shutdown()

    app = FastAPI(title="30A Studio", version=__version__, lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.db = db
    app.state.watchdog = watchdog or Watchdog.from_env(has_active_jobs=db.has_active_work, on_waiting=db.note_active_jobs)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])

    @app.middleware("http")
    async def local_requests(request: Request, call_next):
        if request.method not in ("GET", "HEAD", "OPTIONS"):
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
        return claude_run_or_404(identifier, lambda: claude().select(identifier, body.aday, body.not_))

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

    @app.get("/api/events")
    async def events(request: Request, destination_id: str = DEFAULT_DESTINATION_ID):
        selected(destination_id)
        guard = request.app.state.watchdog
        async def stream():
            previous = None
            guard.stream_opened()
            try:
                while not await request.is_disconnected():
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
