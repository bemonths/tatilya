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
from .sources import beaches

WEB = Path(__file__).parent / "web"
DEFAULT_DATA = Path(__file__).resolve().parent.parent / "data"


def create_app(data_dir: Path | None = None):
    db = Database((data_dir or DEFAULT_DATA) / "studio.sqlite3")

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
                "sources": db.sources(), "jobs": db.jobs(), "data_path": str(db.path.parent),
                "collections": db.collections(),
                "beach_connector": {"source_url": beaches.SOURCE_URL, "method": "JSON", "scope": beaches.SCOPE,
                                    "feature_labels": beaches.FEATURE_LABELS}}

    @app.get("/api/sources")
    def sources():
        return db.sources()

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
        if body.kind == "beach_collection":
            if not body.source_id:
                raise HTTPException(422, "Veri toplamak için bir kaynak seçin.")
            return request.app.state.jobs.submit_beaches(body.source_id)
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
