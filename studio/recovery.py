"""HEDEF-02: a collected result that could not be stored is not lost.

When a collector has gathered everything and only the storing step fails (the night of 27 November 2026: a value outside the schema),
the result is written to the program's own folder, `<data>/kurtarma/<job id>/`:

- `sonuc.json`: the result as the collector gave it (records, counts, metadata, related rows), dates kept as dates;
- `durum.json`: where it came from and what happened to it: the job, the source, the connector and its version, the raw copy, the
  error, and once saved the new run (`kaydedildi`);
- `yeniden-kurma.json` (a result rebuilt from the raw copy, `agency_replay`): how faithful the rebuild was and the comparison with the
  run's own log line.

The Jobs panel shows "Kurtarılan sonucu kaydet" on such a job: after the fix the result is stored as a new version (a new job and run,
the same raw copy), without collecting again. A failed rental price run with a raw copy and no saved result also gets "Ham kopyadan
yeniden kur" (the run rebuilt from its own answers, nothing asked from the sites). Nothing here is deleted.
"""
import dataclasses
import json
from datetime import date, datetime, timezone
from pathlib import Path

FOLDER = "kurtarma"
RESULT = "sonuc.json"
STATE = "durum.json"
REBUILD = "yeniden-kurma.json"


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class _Encoder(json.JSONEncoder):
    def default(self, value):
        if isinstance(value, datetime):
            return {"__datetime__": value.isoformat()}
        if isinstance(value, date):
            return {"__date__": value.isoformat()}
        if isinstance(value, (set, frozenset, tuple)):
            return list(value)
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return super().default(value)


def _decode(value):
    if "__datetime__" in value and len(value) == 1:
        return datetime.fromisoformat(value["__datetime__"])
    if "__date__" in value and len(value) == 1:
        return date.fromisoformat(value["__date__"])
    return value


def folder(data_dir, job_id):
    return Path(data_dir) / FOLDER / job_id


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=1, cls=_Encoder), encoding="utf-8")
    temporary.replace(path)


def save(data_dir, job, source, connector, batch, error=None, rebuild=None):
    """Write the result of `job` to its recovery folder; returns the folder."""
    target = folder(data_dir, job["id"])
    raw = f"raw/{job['id']}/{connector.raw_filename}"
    write_json(target / RESULT, {"records": batch.records, "total_count": batch.total_count, "excluded_count": batch.excluded_count,
                                 "source_updated": batch.source_updated, "metadata": batch.metadata, "related": batch.related})
    write_json(target / STATE, {"is": job["id"], "kaynak_id": source["id"], "kaynak": source["name"], "toplayici": connector.name,
                                "toplayici_surumu": connector.version, "ham_kopya": raw, "yazildi": now_iso(),
                                "hata": error, "nasil": "yeniden_kurma" if rebuild is not None else "kaydetme_dustu",
                                "kayit": len(batch.records), "kaydedildi": None})
    if rebuild is not None:
        write_json(target / REBUILD, rebuild)
    return target


def state(data_dir, job_id):
    path = folder(data_dir, job_id) / STATE
    if not path.is_file():
        return None
    try:
        info = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    rebuilt = folder(data_dir, job_id) / REBUILD
    if rebuilt.is_file():
        try:
            info["yeniden_kurma"] = json.loads(rebuilt.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    return info


def load(data_dir, job_id):
    """The stored result as a CollectionResult."""
    from .sources.base import CollectionResult
    value = json.loads((folder(data_dir, job_id) / RESULT).read_text(encoding="utf-8"), object_hook=_decode)
    return CollectionResult(value["records"], value["total_count"], value["excluded_count"], value["source_updated"],
                            value.get("metadata") or {}, value.get("related") or {})


def mark_saved(data_dir, job_id, run_id):
    info = state(data_dir, job_id) or {}
    info.pop("yeniden_kurma", None)
    info["kaydedildi"] = {"surum": run_id, "zaman": now_iso()}
    write_json(folder(data_dir, job_id) / STATE, info)


def describe(data_dir, job, connector):
    """What the Jobs panel offers on a job: None, or {durum, metin, ...}. `kaydet`: a stored result waits; `kur`: the raw copy can be
    replayed; `kaydedildi`: done."""
    info = state(data_dir, job["id"])
    if info:
        if info.get("kaydedildi"):
            return {"durum": "kaydedildi", "surum": info["kaydedildi"]["surum"], "zaman": info["kaydedildi"]["zaman"],
                    "metin": "Kurtarılan sonuç yeni bir veri sürümü olarak kaydedildi."}
        # the error's technical text stays in durum.json (the job's diagnostic is internal too); the panel says only what to do
        out = {"durum": "kaydet", "kayit": info.get("kayit"), "nasil": info.get("nasil"),
               "metin": "Toplanan sonuç kurtarma dosyasında duruyor; yeniden çekmeden kaydedilebilir."}
        rebuilt = info.get("yeniden_kurma")
        if rebuilt:
            out["karsilastirma"] = rebuilt.get("karsilastirma")
            out["rapor"] = {k: v for k, v in (rebuilt.get("rapor") or {}).items() if not k.endswith("_ornek")}
        return out
    if job.get("status") != "failed" or job.get("kind") != "source_collection" or not job.get("source_id"):
        return None
    if connector is None or not hasattr(connector, "rebuild"):
        return None
    raw = Path(data_dir) / "raw" / job["id"] / connector.raw_filename
    if not raw.is_file():
        return None
    return {"durum": "kur", "metin": "Sonuç kaydedilemedi ama çekimin ham kopyası duruyor; sitelere gitmeden yeniden kurulabilir."}
