from concurrent.futures import ThreadPoolExecutor
import threading

from .database import Conflict, Database
from .sources import beaches


class JobQueue:
    """Tek çalışanlı kuyruk. Durum ve sonuçlar SQLite'ta kalıcıdır."""

    def __init__(self, db: Database):
        self.db = db
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="30a-job")
        self.lock = threading.Lock()
        self.closing = False

    def submit_audit(self):
        with self.lock:
            if self.closing:
                raise Conflict("Uygulama kapanıyor.")
            records = [row for row in self.db.sources() if row["enabled"]]
            if not records:
                raise Conflict("Önce en az bir etkin kaynak ekleyin.")
            identifier = self.db.add_job()
            self.executor.submit(self._audit, identifier, records)
            return self.db.job(identifier)

    def _audit(self, identifier, records):
        try:
            if not self.db.update_job(identifier, status="running", message="Kaynak kayıtları kontrol ediliyor."):
                return
            findings = []
            for index, source in enumerate(records):
                issues = []
                if source["method"] == "Belirlenecek" and source["url"] != beaches.SOURCE_URL:
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
        except Exception:
            self.db.update_job(identifier, status="failed", message="Katalog kontrolü tamamlanamadı. Yeniden deneyin.")

    def cancel(self, identifier):
        self.db.update_job(identifier, status="canceled", message="İş iptal edildi.")
        return self.db.job(identifier)

    def submit_beaches(self, source_id):
        with self.lock:
            if self.closing:
                raise Conflict("Uygulama kapanıyor.")
            source = self.db.source(source_id)
            if not source or not source["enabled"]:
                raise Conflict("Plaj erişim kaynağı bulunamadı veya arşivlenmiş.")
            if source["url"] != beaches.SOURCE_URL:
                raise Conflict("Bu kaynak için henüz veri toplayıcı bağlanmadı.")
            identifier = self.db.add_job("beach_collection", "South Walton · Plaj erişimlerini topla")
            self.executor.submit(self._collect_beaches, identifier, source_id)
            return self.db.job(identifier)

    def _collect_beaches(self, identifier, source_id):
        try:
            if not self.db.update_job(identifier, status="running", message="Plaj verisi toplama başladı."):
                return
            def canceled():
                return self.db.job(identifier)["status"] not in ("queued", "running")
            def progress(percent, message):
                if not self.db.update_job(identifier, progress=percent, message=message):
                    raise beaches.CollectionCanceled()
            relative = f"raw/{identifier}/source.html"
            batch = beaches.collect(self.db.path.parent / relative, progress, canceled)
            self.db.store_collection(identifier, source_id, batch, source_url=beaches.SOURCE_URL,
                                     parser_version=beaches.PARSER_VERSION, raw_path=relative, scope=beaches.SCOPE)
        except beaches.CollectionCanceled:
            self.db.update_job(identifier, status="canceled", message="Veri toplama iptal edildi.")
        except beaches.SourceError as exc:
            self.db.update_job(identifier, status="failed", message=str(exc))
        except Exception:
            self.db.update_job(identifier, status="failed", message="Veri toplama tamamlanamadı. Önceki başarılı sürümler korundu.")

    def shutdown(self):
        with self.lock:
            self.closing = True
            for job in self.db.jobs():
                if job["status"] in ("queued", "running"):
                    self.db.update_job(job["id"], status="interrupted", message="Uygulama kapanırken iş durdu.")
        self.executor.shutdown(wait=True, cancel_futures=True)
