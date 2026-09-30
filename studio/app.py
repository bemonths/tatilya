import asyncio
import csv
import io
import json
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import __version__
from .catalog import CADENCES, CATEGORIES, METHODS, REGIONS, STEPS
from .database import Conflict, Database
from .jobs import JobQueue
from .models import JobInput, SourceInput, SourceUpdate
from .sources import beaches, weather
from .sources.registry import DEFAULT_REGISTRY
from .regions import REGIONS as CANONICAL_REGIONS

WEB = Path(__file__).parent / "web"
DEFAULT_DATA = Path(__file__).resolve().parent.parent / "data"


def create_app(data_dir: Path | None = None, registry=None):
    registry = registry or DEFAULT_REGISTRY
    db = Database((data_dir or DEFAULT_DATA) / "studio.sqlite3", registry)

    @asynccontextmanager
    async def lifespan(app):
        db.initialize()
        db.recover_jobs()
        app.state.jobs = JobQueue(db)
        try:
            yield
        finally:
            app.state.jobs.shutdown()

    app = FastAPI(title="30A Studio", version=__version__, lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.db = db
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
        return {"app": "thirtya-studio", "version": __version__}

    @app.get("/api/bootstrap")
    def bootstrap():
        return {"version": __version__, "categories": CATEGORIES, "regions": REGIONS, "methods": METHODS,
                "cadences": CADENCES, "steps": [dict(id=id_, title=title, subtitle=subtitle, state=state)
                                               for id_, title, subtitle, state in STEPS],
                "sources": sources(), "jobs": db.jobs(), "data_path": str(db.path.parent),
                "canonical_regions": [{"id": id_, "name": name} for id_, name in CANONICAL_REGIONS],
                "collections": db.collections(), "weather_runs": weather_runs(),
                "restaurant_runs": restaurant_runs(),
                "restaurant_connector": {"name": "south-walton-restaurants", "method": "HTML"},
                "weather_connector": {"name": "nws-weather", "method": "API", "anchors": weather.ANCHORS, "provenance": weather.ANCHOR_PROVENANCE},
                "beach_connector": {"name": "south-walton-beaches", "source_url": beaches.SOURCE_URL, "method": "JSON", "scope": beaches.SCOPE,
                                    "feature_labels": beaches.FEATURE_LABELS}}

    @app.get("/api/sources")
    def sources():
        result = []
        for source in db.sources():
            connector = registry.for_source(source)
            result.append({**source, "connector": {"name": connector.name, "version": connector.version, "method": getattr(connector, "method", None)} if connector else None})
        return result

    @app.post("/api/sources", status_code=201)
    def add_source(body: SourceInput):
        return db.save_source(body.record())

    @app.put("/api/sources/{identifier}")
    def update_source(identifier: str, body: SourceUpdate):
        try:
            return db.save_source(body.record(), identifier, body.expected_version)
        except KeyError:
            raise HTTPException(404, "Kaynak bulunamadı.") from None

    @app.get("/api/jobs")
    def jobs():
        return db.jobs()

    @app.post("/api/jobs", status_code=202)
    def start_job(body: JobInput, request: Request):
        if body.kind in ("source_collection", "beach_collection"):
            if not body.source_id:
                raise HTTPException(422, "Veri toplamak için bir kaynak seçin.")
            return request.app.state.jobs.submit_collection(body.source_id)
        return request.app.state.jobs.submit_audit()

    @app.post("/api/jobs/{identifier}/cancel")
    def cancel_job(identifier: str, request: Request):
        result = request.app.state.jobs.cancel(identifier)
        if result is None:
            raise HTTPException(404, "İş bulunamadı.")
        return result

    @app.get("/api/collections")
    def collections():
        return db.collections()

    @app.get("/api/source-runs")
    def source_runs(source_id: str | None = None):
        return db.source_runs(source_id)

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

    @app.get("/api/weather-runs")
    def weather_runs():
        return [run for run in db.source_runs() if run["connector_name"] == "nws-weather" and run["status"] == "done"]

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
    def restaurant_runs():
        return [run for run in db.source_runs() if run["connector_name"] == "south-walton-restaurants" and run["status"] == "done"]

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

    @app.get("/api/events")
    async def events(request: Request):
        async def stream():
            previous = None
            while not await request.is_disconnected():
                data = json.dumps(await asyncio.to_thread(db.jobs), ensure_ascii=False)
                if data != previous:
                    yield f"event: jobs\ndata: {data}\n\n"
                    previous = data
                else:
                    yield ": ping\n\n"
                await asyncio.sleep(1)
        return StreamingResponse(stream(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"})

    app.mount("/static", StaticFiles(directory=WEB), name="static")
    return app
