from concurrent.futures import ThreadPoolExecutor
import threading

from .database import Conflict, Database
from .destinations import DEFAULT_DESTINATION_ID
from .sources.base import SourceError, CollectionCanceled
from .diagnostics import diagnostic


class JobQueue:
    """Tek çalışanlı kuyruk. Durum ve sonuçlar SQLite'ta kalıcıdır."""

    def __init__(self, db: Database):
        self.db = db
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="30a-job")
        self.lock = threading.Lock()
        self.closing = False
        self.registry = db.registry

    def submit_audit(self, destination_id=DEFAULT_DESTINATION_ID):
        with self.lock:
            if self.closing:
                raise Conflict("Uygulama kapanıyor.")
            records = [row for row in self.db.sources(destination_id) if row["enabled"]]
            if not records:
                raise Conflict("Önce en az bir etkin kaynak ekleyin.")
            identifier = self.db.add_job(destination_id=destination_id)
            self.executor.submit(self._audit, identifier, records)
            return self.db.job(identifier)

    def _audit(self, identifier, records):
        try:
            if not self.db.update_job(identifier, status="running", message="Kaynak kayıtları kontrol ediliyor."):
                return
            findings = []
            for index, source in enumerate(records):
                issues = []
                if source["method"] == "Belirlenecek" and not self.registry.for_source(source):
                    issues.append("Veri toplama yöntemi belirlenmemiş.")
                if not source["notes"]:
                    issues.append("Toplanacak alanlar için açıklama eklenmemiş.")
                findings.append({"source_id": source["id"], "name": source["name"], "version": source["version"],
                                 "issues": issues})
                if not self.db.update_job(identifier, progress=int(90 * (index + 1) / len(records)),
                                          message=f"Kayıt incelendi: {source['name']}"):
                    return
            report = {"checked": len(records), "needs_attention": sum(bool(row["issues"]) for row in findings),
                      "findings": findings,
                      "scope": "Yalnızca kayıt bilgileri kontrol edildi. Sitelere bağlanılmadı ve içerik doğrulanmadı."}
            self.db.update_job(identifier, status="done", progress=100, result=report,
                               message=f"{len(records)} kaynak kaydı kontrol edildi.")
        except Exception as exc:
            self.db.update_job(identifier, status="failed", message="Katalog kontrolü tamamlanamadı. Yeniden deneyin.", diagnostic=diagnostic(exc))

    def cancel(self, identifier):
        self.db.update_job(identifier, status="canceled", message="İş iptal edildi.")
        return self.db.job(identifier)

    def submit_collection(self, source_id):
        with self.lock:
            if self.closing:
                raise Conflict("Uygulama kapanıyor.")
            source = self.db.source(source_id)
            if not source or not source["enabled"]:
                raise Conflict("Kaynak bulunamadı veya arşivlenmiş.")
            connector = self.registry.for_source(source)
            if connector is None:
                raise Conflict("Bu kaynak için henüz veri toplayıcı bağlanmadı.")
            identifier = self.db.add_job("source_collection", f"{source['name']} · Verileri topla", source_id, connector, source["version"])
            try:
                self.executor.submit(self._collect, identifier, source, connector)
            except Exception as exc:
                self.db.update_job(identifier, status="failed", message="İş başlatılamadı. Yeniden deneyin.", diagnostic=diagnostic(exc))
            return self.db.job(identifier)

    def _collect(self, identifier, source, connector):
        raw_path = self.db.path.parent / "raw" / identifier / connector.raw_filename
        def capture_raw():
            try:
                self.db.record_raw_artifact(identifier, raw_path)
            except Exception as exc:
                return diagnostic(exc)
        try:
            if not self.db.update_job(identifier, status="running", message="Kaynak verisi toplama başladı."):
                return
            def canceled():
                return self.db.job(identifier)["status"] not in ("queued", "running")
            def progress(percent, message):
                if not self.db.update_job(identifier, progress=percent, message=message):
                    raise CollectionCanceled()
            context = self.db.context(source["destination_id"], inputs=getattr(connector, "inputs", ()))
            extra = {}
            if getattr(connector, "uses_verification", False):
                def waiting(site):
                    message = (f"Kullanıcı doğrulaması bekleniyor: {site}. Açılan tarayıcı penceresinde doğrulamayı tamamlayın (en çok 15 dk)."
                               if site else "Doğrulama beklemesi bitti; toplama devam ediyor.")
                    if not self.db.update_job(identifier, message=message, waiting_for=site or ""):
                        raise CollectionCanceled()
                extra["waiting"] = waiting
            batch = connector.collect(source, raw_path, progress, canceled, context=context, **extra)
            self.db.record_raw_artifact(identifier, raw_path)
            self.db.complete_source_run(identifier, batch, connector)
        except CollectionCanceled:
            capture_raw()
            self.db.update_job(identifier, status="canceled", message="Veri toplama iptal edildi.")
        except SourceError as exc:
            info = diagnostic(exc)
            info["raw_artifact_error"] = capture_raw()
            self.db.update_job(identifier, status="failed", message=str(exc), diagnostic=info)
        except Exception as exc:
            info = diagnostic(exc)
            info["raw_artifact_error"] = capture_raw()
            self.db.update_job(identifier, status="failed", message="Veri toplama tamamlanamadı. Önceki başarılı sürümler korundu.", diagnostic=info)

    def shutdown(self):
        with self.lock:
            self.closing = True
            for job in self.db.jobs(None):
                if job["status"] in ("queued", "running"):
                    self.db.update_job(job["id"], status="interrupted", message="Uygulama kapanırken iş durdu.")
        self.executor.shutdown(wait=True, cancel_futures=True)
