"""Token estimates and spending (GÖREV-18 Adım 4 and 5).

Estimate of one call: read = the call's task text and combined instructions (characters ÷ `single.CHARS_PER_TOKEN`, plus Claude Code's own
system text); written = the median written tokens of the step's last successful calls (title steps: runs; video text steps: sessions), or
the step's output guess in Settings → Claude when there is none. For video text calls whose task text cannot be built before the run (a
section needs the plan), the read side is the median read tokens of the step's earlier one-call sessions, or a size worked out from what
is known (see `studio/text/estimate.py`).

Spending: every call's tokens (read = input + cache creation + cache read; written = output), model, effort and duration are in its run
record and its `metrics` (DB). A call of the one-call way has `metrics.duzen = "tek_cagri"`; earlier (multi-turn) runs do not, and the
tables show them apart ("eski düzen") so the old cost does not pass as the new one.
"""
import json
import statistics

from . import settings as claude_settings, single

MEDIAN_OF = 9
ONE_CALL = "tek_cagri"
TITLE_STEPS = ("baslik", "baslik_degerlendirme")
DONE_RUNS = ("awaiting_approval", "approved", "rejected")


def _metrics(value):
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value) if value else None
    except ValueError:
        return None


def step_calls(db, step, *, new_only=False, limit=None):
    """The step's finished calls, newest first: [(metrics, created_at)]. Title steps: one run (its one or two calls summed); text steps: one
    session."""
    with db.connect() as con:
        if step in TITLE_STEPS:
            rows = con.execute(f"""SELECT metrics, created_at FROM claude_runs WHERE step=? AND metrics IS NOT NULL
                AND status IN ({",".join("?" * len(DONE_RUNS))}) ORDER BY created_at DESC""", (step, *DONE_RUNS)).fetchall()
        else:
            rows = con.execute("""SELECT metrics, created_at FROM text_sessions WHERE step=? AND status='done' AND metrics IS NOT NULL
                ORDER BY created_at DESC""", (step,)).fetchall()
    out = []
    for raw, created in rows:
        metrics = _metrics(raw)
        if not metrics or not metrics.get("tokens"):
            continue
        if new_only and metrics.get("duzen") != ONE_CALL:
            continue
        out.append((metrics, created))
    return out[:limit] if limit else out


def output_estimate(db, settings, step):
    """(written tokens, basis): the median of the step's last successful calls, or the output guess in Settings."""
    values = [single.token_total(m)[1] / max(1, int(m.get("cagri") or 1)) for m, _ in step_calls(db, step, limit=MEDIAN_OF)]
    values = [v for v in values if v > 0]
    if values:
        middle = int(statistics.median(values))
        return middle, f"önceki {len(values)} başarılı çalışmanın ortancası"
    return claude_settings.output_guess(settings, step), "önceki çalışma yok; Ayarlar'daki çıktı varsayımı"


def read_median(db, step):
    """Median read tokens of the step's earlier one-call sessions (None without any)."""
    values = [single.token_total(m)[0] / max(1, int(m.get("cagri") or 1)) for m, _ in step_calls(db, step, new_only=True, limit=MEDIAN_OF)]
    values = [v for v in values if v > 0]
    return int(statistics.median(values)) if values else None


def call_estimate(db, settings, step, read, *, read_basis="istemin boyutu"):
    written, basis = output_estimate(db, settings, step)
    return {"adim": step, "okunan": int(read), "yazilan": int(written), "toplam": int(read) + int(written),
            "dayanak": f"okunan: {read_basis}; yazılan: {basis}"}


def model_text(settings, step):
    model, effort = claude_settings.resolve_model_effort(settings, step)
    return {"model": model, "efor": effort, "model_adi": claude_settings.model_label(model) if model else "Claude Code varsayılanı",
            "efor_adi": claude_settings.effort_label(effort) if effort else "Otomatik"}


def summary(rows, settings, *, retries=0):
    """The estimate shown before a job starts: its lines, the total, the limits and what is over them."""
    call_limit, job_limit = claude_settings.limits(settings)
    total = {"cagri": sum(r["cagri"] for r in rows), "okunan": sum(r["okunan"] for r in rows), "yazilan": sum(r["yazilan"] for r in rows)}
    total["toplam"] = total["okunan"] + total["yazilan"]
    over = []
    for row in rows:
        if row.get("en_buyuk_cagri", 0) > call_limit:
            over.append(f"{row['baslik']}: en büyük çağrı yaklaşık {single.thousands(row['en_buyuk_cagri'])} token; tek çağrı sınırı "
                        f"{single.thousands(call_limit)}.")
    if total["toplam"] > job_limit:
        over.append(f"İşin toplam tahmini yaklaşık {single.thousands(total['toplam'])} token; iş başına sınır {single.thousands(job_limit)}.")
    text = " · ".join(f"{r['baslik']}: {r['cagri']} çağrı, yaklaşık {single.thousands(r['toplam'])} token" for r in rows)
    if len(rows) > 1:
        text += f" · Toplam: yaklaşık {single.thousands(total['toplam'])} token"
    return {"satirlar": rows, "toplam": total, "sinirlar": {"cagri": call_limit, "is": job_limit}, "asiyor": over, "baslatilabilir": not over,
            "metin": text, "yeniden_deneme": retries}


# ------------------------------------------------------------------------------------------------------------------- spending tables

def _row(values):
    if not values:
        return {"sayi": 0, "ortanca": None, "en_yuksek": None}
    return {"sayi": len(values), "ortanca": int(statistics.median(values)), "en_yuksek": max(values)}


def spending(db):
    """Per step: the one-call way's calls (count, median and highest total tokens, median read and written) and the old way's runs."""
    out = []
    for key, label in claude_settings.CLAUDE_STEPS:
        new, old = [], []
        reads, writes = [], []
        for metrics, _ in step_calls(db, key):
            read, written = single.token_total(metrics)
            if metrics.get("duzen") == ONE_CALL:
                new.append(read + written)
                reads.append(read)
                writes.append(written)
            else:
                old.append(read + written)
        row = {"adim": key, "baslik": label, "yeni": _row(new), "eski": _row(old)}
        row["yeni"]["okunan_ortanca"] = int(statistics.median(reads)) if reads else None
        row["yeni"]["yazilan_ortanca"] = int(statistics.median(writes)) if writes else None
        out.append(row)
    return out


def last_job(db):
    """The last finished Claude job's spending (the sidebar's usage box): title, estimate, actual, over."""
    with db.connect() as con:
        row = con.execute("""SELECT id, title, status, result, finished_at, created_at FROM jobs WHERE kind IN ('claude_run','claude_metin')
            AND status NOT IN ('queued','running') AND result IS NOT NULL AND json_valid(result) AND json_extract(result,'$.harcama') IS NOT NULL
            ORDER BY rowid DESC LIMIT 1""").fetchone()
    if row is None:
        return None
    result = _metrics(row["result"]) or {}
    spend = result.get("harcama") or {}
    return {"is": row["id"], "baslik": row["title"], "durum": row["status"], "zaman": row["finished_at"] or row["created_at"], **spend}
