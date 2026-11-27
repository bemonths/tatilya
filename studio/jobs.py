from concurrent.futures import ThreadPoolExecutor
import json
import threading

from .database import Conflict, Database
from .destinations import DEFAULT_DESTINATION_ID
from .sources.base import SourceError, CollectionCanceled
from .diagnostics import diagnostic


class JobQueue:
    """Tek çalışanlı kuyruk. Durum ve sonuçlar SQLite'ta kalıcıdır."""

    def __init__(self, db: Database, extension=None, region=None):
        self.db = db
        self.extension = extension          # GÖREV-14: the browser extension bridge (studio.extension), when the app has one
        self.region = region                # GÖREV-16: () -> RegionAccess (the US proxy and the region-blocked list)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="30a-job")
        self.lock = threading.Lock()
        self.selections = {}            # HEDEF-03: job id -> the chosen rental companies (until the job starts)
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

    def submit_collection(self, source_id, companies=None):
        """A collection job. HEDEF-03: `companies` (rental price collector only): "Seçili şirketleri yeniden oku" — only these companies
        are asked; the new version carries every other company from the last successful version."""
        with self.lock:
            if self.closing:
                raise Conflict("Uygulama kapanıyor.")
            source = self.db.source(source_id)
            if not source or not source["enabled"]:
                raise Conflict("Kaynak bulunamadı veya arşivlenmiş.")
            connector = self.registry.for_source(source)
            if connector is None:
                raise Conflict("Bu kaynak için henüz veri toplayıcı bağlanmadı.")
            title = f"{source['name']} · Verileri topla"
            if companies is not None:
                if not getattr(connector, "selectable", False):
                    raise Conflict("Bu veri toplayıcısında şirket seçilemez.")
                companies = sorted({str(c).strip().lower() for c in companies if str(c).strip()})
                if not companies:
                    raise Conflict("Yeniden okunacak en az bir şirket seçin.")
                configured = {s["domain"] for s in (self.db.context(source["destination_id"]).agency or {}).get("sites", []) if s.get("enabled", 1)}
                unknown = [c for c in companies if c not in configured]
                if unknown:
                    raise Conflict(f"Yapılandırmada olmayan ya da kapalı şirket: {', '.join(unknown)}.")
                with self.db.connect() as con:
                    from .sources.agency_rates import latest_version
                    if latest_version(con, source["destination_id"]) is None:
                        raise Conflict("Önce bütün şirketlerle bir kiralama fiyat sürümü olmalı; seçili şirketler o sürümü tamamlar.")
                title = f"{source['name']} · Seçili şirketleri yeniden oku ({len(companies)} şirket)"
            identifier = self.db.add_job("source_collection", title, source_id, connector, source["version"])
            if companies is not None:
                self.selections[identifier] = companies
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
            chosen = self.selections.pop(identifier, None)
            if chosen is not None:          # HEDEF-03: the chosen companies and the version they complete (written beside the raw copy)
                from .sources.agency_rates import SELECTION_FILE, selection_context
                import dataclasses
                with self.db.connect() as con:
                    context = dataclasses.replace(context, selected=selection_context(con, source["destination_id"], chosen))
                raw_path.parent.mkdir(parents=True, exist_ok=True)
                (raw_path.parent / SELECTION_FILE).write_text(json.dumps({"sirketler": context.selected["domains"],
                                                                          "taban_surum": context.selected["base"]["run_id"]},
                                                                         ensure_ascii=False, indent=1), encoding="utf-8")
                self.db.update_job(identifier, message=f"Seçili şirketler: {', '.join(chosen)}; öbür şirketler "
                                                       f"{context.selected['base']['run_id'][:8]} sürümünden olduğu gibi taşınacak.")
            extra = {}
            if getattr(connector, "uses_extension", False) and self.extension is not None:
                from .extension import JobAccess
                extra["extension"] = JobAccess(self.extension, self.db, identifier)   # GÖREV-14: the user's Chrome, when paired
            if getattr(connector, "uses_region", False) and self.region is not None:
                extra["region"] = self.region()        # GÖREV-16: region-blocked domains only through the user's US proxy
            if getattr(connector, "uses_workers", False):
                from .workers import BOARDS
                extra["board"] = BOARDS.open(identifier)     # HEDEF-01: the workers on the job panel while the job runs
            if getattr(connector, "uses_verification", False):
                def waiting(site):
                    message = (f"Kullanıcı doğrulaması bekleniyor: {site}. Açılan tarayıcı penceresinde doğrulamayı tamamlayın "
                               f"(en çok {getattr(connector, 'verify_minutes', 15)} dk)."
                               if site else "Doğrulama beklemesi bitti; toplama devam ediyor.")
                    if not self.db.update_job(identifier, message=message, waiting_for=site or ""):
                        raise CollectionCanceled()
                extra["waiting"] = waiting
            if extra:
                # GÖREV-17: a browser this job starts is closed when the job ends or is cancelled; the panel names the open window
                from .sources.browser_verification import JobWindows
                with JobWindows(lambda key, text: self.db.set_job_window(identifier, key, text)):
                    batch = connector.collect(source, raw_path, progress, canceled, context=context, **extra)
            else:
                batch = connector.collect(source, raw_path, progress, canceled, context=context)
            self.db.record_raw_artifact(identifier, raw_path)
            self.store(identifier, source, connector, batch)
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
            message = "Veri toplama tamamlanamadı. Önceki başarılı sürümler korundu."
            if getattr(exc, "recovery_saved", False):     # HEDEF-02: only the storing failed; the result waits in the recovery folder
                info["recovery"] = True
                message = ("Toplanan sonuç kaydedilemedi; önceki başarılı sürümler korundu. Sonuç kurtarma dosyasına yazıldı: düzeltmeden "
                           "sonra İşler panelinde bu işin kartındaki \"Kurtarılan sonucu kaydet\" ile yeniden çekmeden kaydedilebilir.")
            self.db.update_job(identifier, status="failed", message=message, diagnostic=info)
        finally:
            from .workers import BOARDS
            BOARDS.close(identifier)

    def store(self, identifier, source, connector, batch):
        """The storing step; when it fails the collected result is kept in the recovery folder (HEDEF-02, studio/recovery.py) and the
        error goes on as before (the job fails, the earlier versions stay)."""
        try:
            self.db.complete_source_run(identifier, batch, connector)
        except Exception as exc:
            from . import recovery
            try:
                job = self.db.job(identifier) or {"id": identifier}
                recovery.save(self.db.path.parent, job, source, connector, batch,
                              error={"tur": type(exc).__name__, "metin": str(exc)[:500]})
                exc.recovery_saved = True
            except Exception:
                import logging
                logging.getLogger(__name__).exception("Kurtarma dosyası yazılamadı.")
            raise

    # --- HEDEF-02: a result that could not be stored -------------------------------------------------------------------

    def recovery_info(self, job):
        """What the Jobs panel offers on this job (studio/recovery.py): a stored result to save, a raw copy to rebuild, or nothing."""
        from . import recovery
        connector = None
        if job.get("source_id"):
            source = self.db.source(job["source_id"])
            connector = self.registry.for_source(source) if source else None
        return recovery.describe(self.db.path.parent, job, connector)

    def _recovery_source(self, job_id):
        job = self.db.job(job_id)
        if not job:
            raise Conflict("İş bulunamadı.")
        source = self.db.source(job["source_id"]) if job.get("source_id") else None
        connector = self.registry.for_source(source) if source else None
        if not source or connector is None:
            raise Conflict("Bu işin kaynağı ya da veri toplayıcısı artık yok.")
        return job, source, connector

    def submit_recovery_save(self, job_id):
        """"Kurtarılan sonucu kaydet": the result in the job's recovery folder becomes a new version (a new job and run, the same
        raw copy); nothing is collected."""
        from . import recovery
        with self.lock:
            if self.closing:
                raise Conflict("Uygulama kapanıyor.")
            job, source, connector = self._recovery_source(job_id)
            info = recovery.state(self.db.path.parent, job_id)
            if not info:
                raise Conflict("Bu işin kurtarma dosyası yok.")
            if info.get("kaydedildi"):
                raise Conflict("Bu sonuç zaten kaydedildi.")
            if info.get("toplayici") != connector.name:
                raise Conflict("Kurtarma dosyası başka bir veri toplayıcısına ait.")
            identifier = self.db.add_job("source_collection", f"{source['name']} · Kurtarılan sonucu kaydet", source["id"], connector,
                                         source["version"])
            self.executor.submit(self._recovery_save, identifier, job_id, source, connector, info)
            return self.db.job(identifier)

    def _recovery_save(self, identifier, job_id, source, connector, info):
        from . import recovery
        try:
            if not self.db.update_job(identifier, status="running", progress=10,
                                      message="Kurtarma dosyası okunuyor (sitelere gidilmiyor)."):
                return
            batch = recovery.load(self.db.path.parent, job_id)
            batch.metadata = {**batch.metadata, "kurtarma": {"kaynak_is": job_id, "nasil": info.get("nasil"), "dosya_yazildi": info.get("yazildi"),
                                                             "toplayici_surumu": info.get("toplayici_surumu")}}
            self.db.update_job(identifier, progress=50, message=f"{len(batch.records)} kayıt kaydediliyor.")
            raw = self.db.path.parent / (info.get("ham_kopya") or f"raw/{job_id}/{connector.raw_filename}")
            self.db.record_raw_artifact(identifier, raw)
            if self.db.complete_source_run(identifier, batch, connector):
                recovery.mark_saved(self.db.path.parent, job_id, identifier)
        except Exception as exc:
            self.db.update_job(identifier, status="failed", message="Kurtarılan sonuç kaydedilemedi; kurtarma dosyası yerinde duruyor.",
                               diagnostic=diagnostic(exc))

    def submit_rebuild(self, job_id):
        """"Ham kopyadan yeniden kur": a failed run's result rebuilt from its own raw copy (the connector's `rebuild`); the result is
        written to the recovery folder with the comparison, and saved only with "Kurtarılan sonucu kaydet"."""
        with self.lock:
            if self.closing:
                raise Conflict("Uygulama kapanıyor.")
            job, source, connector = self._recovery_source(job_id)
            if not hasattr(connector, "rebuild"):
                raise Conflict("Bu veri toplayıcısının sonucu ham kopyadan kurulamaz.")
            info = self.recovery_info(job)
            if not info or info["durum"] != "kur":
                raise Conflict("Bu iş için ham kopyadan kurma yapılamaz (kurtarma dosyası zaten var ya da ham kopya yok).")
            identifier = self.db.add_job("kurtarma", f"{source['name']} · Ham kopyadan yeniden kur", destination_id=source["destination_id"])
            self.executor.submit(self._rebuild, identifier, job, source, connector)
            return self.db.job(identifier)

    def _rebuild(self, identifier, job, source, connector):
        from . import recovery
        try:
            if not self.db.update_job(identifier, status="running", progress=1,
                                      message="Çekim ham kopyasından yeniden kuruluyor (sitelere gidilmiyor)."):
                return
            def canceled():
                return self.db.job(identifier)["status"] not in ("queued", "running")
            def progress(percent, message):
                if not self.db.update_job(identifier, progress=min(95, percent), message=message):
                    raise CollectionCanceled()
            batch, report, comparison = connector.rebuild(self.db, job, source, progress, canceled)
            recovery.save(self.db.path.parent, job, source, connector, batch, rebuild={"rapor": report, "karsilastirma": comparison})
            same = comparison.get("ayni")
            message = (f"Ham kopyadan kuruldu: {len(batch.records)} kayıt; sayılar çekim kaydıyla {'aynı' if same else 'aynı değil'}. "
                       "Kaydetmek için çekimin kartındaki \"Kurtarılan sonucu kaydet\"e basın.")
            self.db.update_job(identifier, status="done", progress=100, message=message,
                               result={"kaynak_is": job["id"], "rapor": {k: v for k, v in report.items() if not k.endswith("_ornek")},
                                       "karsilastirma": comparison})
        except CollectionCanceled:
            self.db.update_job(identifier, status="canceled", message="Yeniden kurma iptal edildi.")
        except Exception as exc:
            self.db.update_job(identifier, status="failed", message=f"Ham kopyadan kurulamadı: {str(exc)[:200]}", diagnostic=diagnostic(exc))

    def shutdown(self):
        with self.lock:
            self.closing = True
            for job in self.db.jobs(None):
                if job["status"] in ("queued", "running"):
                    self.db.update_job(job["id"], status="interrupted", message="Uygulama kapanırken iş durdu.")
        self.executor.shutdown(wait=True, cancel_futures=True)
