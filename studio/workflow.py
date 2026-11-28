"""The steps of a video and their stored statuses (GÖREV-21; after Rota Stüdyo `rota/state.py` and its TASARIM 6.2, kept in SQLite).

The program has two layers. The project layer (the destination) holds what is done once and used by every video: the data, the topic
bank, the channel's rules and the list of videos. The video layer holds one video's eight steps:

| No | key | Adım | Onay |
|---|---|---|---|
| 1 | baslik | Başlık ve vaat | evet |
| 2 | paket | Veri paketi | hayır (bitince tamamlandı) |
| 3 | plan | Plan | evet |
| 4 | yazim | Yazım | hayır |
| 5 | kontrol | Kontrol ve ton seçimi | evet |
| 6 | yayin | Yayın paketi | evet (HEDEF-04 A-6) |
| 7 | ses | Seslendirme | hayır (HEDEF-04 A-7) |
| 8 | kurgu | Kurgu paketi | hayır (HEDEF-04 A-8) |

Statuses (`video_steps.status`): waiting (bekliyor), ready (hazır), running (çalışıyor), awaiting_approval (onay bekliyor), approved
(onaylandı), done (tamamlandı), error (hata), stale (eskidi). Rules:
- The first step starts ready, the others waiting (a video opened from the topic bank starts with its first step awaiting approval).
- When a step is approved (a step without approval: done) the next step, if it waits, becomes ready; when the step leaves that state
  (run again, rejected) a next step that is ready waits again: nothing starts before the approval.
- When a step's approved output changes, the later steps that have an output (awaiting approval, approved, done) become stale with a
  Turkish reason ("Plan onayı değişti."); outputs are never deleted. The user runs the step again or says "Bu değişiklik etkilemiyor":
  the step returns to the status it had and the note goes to the status log.
- A step that looks running while no work of it runs (the program closed half way) becomes error and can be resumed.
Every change and every decision is a dated Turkish sentence in `video_step_log`.

Every step is built (HEDEF-04 A-8). 8 · Kurgu paketi waits only for 6 · Yayın paketi (the package is built without audio too): it is
ready when 6 is approved, whatever 7 · Seslendirme's stage; "Kurguya gönder" makes it done.
"""
import json
from datetime import datetime, timezone

from .evidence.pack import latest_done_run, moment

STATUS_LABELS = {"waiting": "bekliyor", "ready": "hazır", "running": "çalışıyor", "awaiting_approval": "onay bekliyor",
                 "approved": "onaylandı", "done": "tamamlandı", "error": "hata", "stale": "eskidi"}
# 7 · Seslendirme's stages: stored as "ready" with the stage in `ref` (the table's CHECK keeps the eight statuses)
VOICE = {"awaiting_audio": "ses bekliyor", "audio_ready": "ses yüklendi"}
STEPS = (
    ("baslik", "Başlık ve vaat"),
    ("paket", "Veri paketi"),
    ("plan", "Plan"),
    ("yazim", "Yazım"),
    ("kontrol", "Kontrol ve ton seçimi"),
    ("yayin", "Yayın paketi"),
    ("ses", "Seslendirme"),
    ("kurgu", "Kurgu paketi"),
)
KEYS = tuple(key for key, _ in STEPS)
TITLES = dict(STEPS)
APPROVAL = frozenset({"baslik", "plan", "kontrol", "yayin"})
PLANNED_NOTE = "Sonraki görevde gelecek"
PLANNED = {}                     # steps not built yet (none since HEDEF-04 A-8)
WITH_OUTPUT = frozenset({"awaiting_approval", "approved", "done"})
COMPLETE = frozenset({"approved", "done"})
INTERRUPTED = "Program kapanırken yarıda kaldı; kaldığı yerden sürdürebilirsiniz."
FIELDS = ("note", "error", "ref", "inputs")
REASONS = {"baslik": "Başlık onayı değişti.", "paket": "Veri paketi değişti.", "plan": "Plan onayı değişti.", "yazim": "Yazım değişti.", "kontrol": "Ton seçimi değişti.",
           "veri": "Veri paketten sonra yeniden çekildi."}


class StateError(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def label(step):
    return f"{KEYS.index(step) + 1} · {TITLES[step]}"


def check_step(step):
    if step not in KEYS:
        raise StateError(f"Bilinmeyen adım: {step}.")


# ---- rows (inside the caller's transaction) -----------------------------------------------------------------------------------

def _rows(con, video_id):
    return {r["step"]: dict(r) for r in con.execute("SELECT * FROM video_steps WHERE video_id=?", (video_id,))}


def _log(con, video_id, step, text):
    con.execute("INSERT INTO video_step_log (video_id,step,at,text) VALUES (?,?,?,?)", (video_id, step, now(), text))


def _update(con, video_id, step, **fields):
    fields["updated_at"] = now()
    con.execute(f"UPDATE video_steps SET {', '.join(f'{k}=?' for k in fields)} WHERE video_id=? AND step=?", (*fields.values(), video_id, step))


def init(con, video_id, statuses=None, note="Video açıldı."):
    """The step rows of a new video: the first step ready, the others waiting (`statuses` overrides: {step: status or (status, ref)})."""
    statuses = statuses or {}
    for index, key in enumerate(KEYS):
        given = statuses.get(key, "ready" if index == 0 else "waiting")
        status, ref = given if isinstance(given, tuple) else (given, None)
        con.execute("INSERT INTO video_steps (video_id,step,status,ref,updated_at) VALUES (?,?,?,?,?)", (video_id, key, status, ref, now()))
    _log(con, video_id, None, note)


def seed(con, video_id, note="Adım durumları videonun kayıtlarından çıkarıldı."):
    """The steps of a video that has none yet (a video made before schema 21), from its records."""
    video = con.execute("SELECT * FROM videos WHERE id=?", (video_id,)).fetchone()
    if video is None:
        raise KeyError(video_id)
    titled = bool(video["title_en"])
    pack = con.execute("SELECT id FROM evidence_packs WHERE video_id=? ORDER BY created_at DESC, rowid DESC LIMIT 1", (video_id,)).fetchone()
    runs = [dict(r) for r in con.execute("SELECT id,status,reason,plan,state FROM text_runs WHERE video_id=? ORDER BY created_at DESC, rowid DESC",
                                         (video_id,))]
    versions = con.execute("SELECT COUNT(*) FROM text_versions WHERE video_id=?", (video_id,)).fetchone()[0]
    chosen = con.execute("SELECT 1 FROM text_selections WHERE video_id=? LIMIT 1", (video_id,)).fetchone()
    found = {"baslik": "approved" if titled else "ready",
             "paket": ("done", pack["id"]) if pack else "ready" if titled else "waiting"}
    planned = next((r for r in runs if r["plan"]), None)
    latest = runs[0] if runs else None
    active = ("running", "waiting_limit")
    plan_done = False
    if planned:
        waiting = planned["status"] == "paused" and planned["reason"] == "plan_hazir" and not versions
        approved = bool(json.loads(planned["state"] or "{}").get("plan_onaylandi"))
        if waiting and not approved:
            found["plan"] = ("awaiting_approval", planned["id"])
        else:
            plan_done = True
            found["plan"] = ("approved", planned["id"])
            if not approved:      # the old chain wrote on without an approval: its plans count as approved
                con.execute("UPDATE text_runs SET state=json_set(state,'$.plan_onaylandi',json('true')) WHERE id=?", (planned["id"],))
    elif latest:
        found["plan"] = ("running" if latest["status"] in active else "error", latest["id"])
    else:
        found["plan"] = "ready" if pack else "waiting"
    if versions:
        found["yazim"] = ("done", (planned or latest or {}).get("id"))
    elif plan_done:
        found["yazim"] = (("running" if latest["status"] in active else "error" if latest["status"] in ("paused", "interrupted", "error")
                           else "ready"), planned["id"])
    else:
        found["yazim"] = "waiting"
    found["kontrol"] = "approved" if chosen and versions else "awaiting_approval" if versions else "waiting"
    init(con, video_id, found, note)


def ensure(con, video_id):
    rows = _rows(con, video_id)
    if len(rows) < len(KEYS):
        if rows:
            for index, key in enumerate(KEYS):       # a step added by a later version: its starting status
                if key not in rows:
                    con.execute("INSERT INTO video_steps (video_id,step,status,updated_at) VALUES (?,?,?,?)", (video_id, key, "waiting", now()))
        else:
            seed(con, video_id)
        rows = _rows(con, video_id)
    if rows["kontrol"]["status"] in COMPLETE and rows["yayin"]["status"] == "waiting":
        # HEDEF-04 A-6: 6 · Yayın paketi is built now; a video whose check was approved before waited there for good
        _update(con, video_id, "yayin", status="ready")
        _log(con, video_id, "yayin", f"{label('yayin')}: bekliyor → hazır (adım kuruldu; ton seçimi onaylı).")
        rows = _rows(con, video_id)
    if rows["yayin"]["status"] in COMPLETE and rows["ses"]["status"] == "waiting":
        # HEDEF-04 A-7: 7 · Seslendirme is built now; a video whose publish package was approved before waited there for good
        _update(con, video_id, "ses", status="ready")
        _log(con, video_id, "ses", f"{label('ses')}: bekliyor → hazır (adım kuruldu; yayın paketi onaylı).")
        rows = _rows(con, video_id)
    if rows["yayin"]["status"] in COMPLETE and rows["kurgu"]["status"] == "waiting":
        # HEDEF-04 A-8: 8 · Kurgu paketi needs only the approved publish package (it is built without audio too)
        _update(con, video_id, "kurgu", status="ready")
        _log(con, video_id, "kurgu", f"{label('kurgu')}: bekliyor → hazır (yayın paketi onaylı).")
        rows = _rows(con, video_id)
    return rows


def _check_set(step, status):
    check_step(step)
    if status not in STATUS_LABELS and status not in VOICE:
        raise StateError(f"Bilinmeyen adım durumu: {status}.")
    if status in VOICE and step != "ses":
        raise StateError(f"{label(step)} adımında ses yok; '{VOICE[status]}' durumuna geçemez.")
    if status in VOICE:
        return
    if status == "stale":
        raise StateError("Eskime yalnızca girdiler değişince işaretlenir.")
    if step in PLANNED and status != "waiting":
        raise StateError(f"{label(step)} adımı henüz kurulmadı.")
    if status in ("awaiting_approval", "approved") and step not in APPROVAL:
        raise StateError(f"{label(step)} adımında onay yok; '{STATUS_LABELS[status]}' durumuna geçemez.")
    if status == "done" and step in APPROVAL:
        raise StateError(f"{label(step)} adımı onaylıdır; bitince 'onay bekliyor' durumuna geçer.")


def _apply_set(con, video_id, step, status, values):
    rows = ensure(con, video_id)
    old = rows[step]["status"]
    fields = {k: v for k, v in values.items() if k in FIELDS}
    if status != "error" and "error" not in fields:
        fields["error"] = None
    shown_old = voice_status(rows[step]) if step == "ses" else old
    if status in VOICE:
        fields["ref"], shown_new, status = status, VOICE[status], "ready"
    else:
        shown_new = STATUS_LABELS[status]
    _update(con, video_id, step, status=status, stale_reason=None, status_before_stale=None, **fields)
    old_label = VOICE.get(shown_old) or STATUS_LABELS[shown_old]
    if old_label != shown_new:
        _log(con, video_id, step, f"{label(step)}: {old_label} → {shown_new}.")
    index = KEYS.index(step)
    if step == "yayin":                 # 8 · Kurgu paketi follows 6 (not 7): it is built without audio too
        current = _rows(con, video_id)["kurgu"]["status"]
        if status in COMPLETE and current == "waiting":
            _update(con, video_id, "kurgu", status="ready")
            _log(con, video_id, "kurgu", f"{label('kurgu')}: bekliyor → hazır.")
        elif status not in COMPLETE and current == "ready":
            _update(con, video_id, "kurgu", status="waiting")
            _log(con, video_id, "kurgu", f"{label('kurgu')}: hazır → bekliyor.")
    if index + 1 < len(KEYS) and KEYS[index + 1] not in PLANNED and step != "ses":
        following = KEYS[index + 1]
        current = rows[following]["status"]
        if status in COMPLETE and current == "waiting":
            _update(con, video_id, following, status="ready")
            _log(con, video_id, following, f"{label(following)}: bekliyor → hazır.")
        elif status not in COMPLETE and current == "ready":
            _update(con, video_id, following, status="waiting")
            _log(con, video_id, following, f"{label(following)}: hazır → bekliyor.")


def _apply_stale(con, video_id, step, reason, only=False):
    rows = ensure(con, video_id)
    staled = []
    for later in ((step,) if only else KEYS[KEYS.index(step):]):
        row = rows[later]
        if row["status"] in WITH_OUTPUT or (later == "ses" and voice_status(row) in VOICE):
            _update(con, video_id, later, status="stale", status_before_stale=row["status"], stale_reason=reason)
            staled.append(label(later))
        elif row["status"] == "stale":
            previous = row["stale_reason"]
            if not previous:
                _update(con, video_id, later, stale_reason=reason)
            elif reason not in previous:
                _update(con, video_id, later, stale_reason=f"{previous} {reason}")
            staled.append(label(later))
    if staled:
        _log(con, video_id, step, f"Girdiler değişti ({reason}) Eskiyen adımlar: {', '.join(staled)}.")
    return staled


# ---- the public functions (each is one transaction) -------------------------------------------------------------------------------

def steps(db, video_id):
    with db.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        return ensure(con, video_id)


def step(db, video_id, key):
    check_step(key)
    return steps(db, video_id)[key]


def set_step(db, video_id, key, status, *, stale_from=None, reason="", log=None, **values):
    """Sets a step's status (and the next step's by the rules); `stale_from`: the later steps with an output become stale with
    `reason`; `log`: one more sentence for the status log (a decision with its note)."""
    _check_set(key, status)
    if stale_from is not None:
        check_step(stale_from)
        if KEYS.index(stale_from) <= KEYS.index(key):
            raise StateError(f"Eskime {label(key)} adımından sonraki bir adımdan başlamalı.")
        if not reason:
            raise StateError("Eskime sebebi gerekli.")
    with db.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        _apply_set(con, video_id, key, status, values)
        if stale_from is not None:
            _apply_stale(con, video_id, stale_from, reason)
        if log:
            _log(con, video_id, key, log)
        return _rows(con, video_id)


def mark_stale(db, video_id, key, reason, *, only=False):
    check_step(key)
    with db.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        _apply_stale(con, video_id, key, reason, only)
        return _rows(con, video_id)


def clear_stale(db, video_id, key, note="", inputs=None):
    """"Bu değişiklik etkilemiyor": the step returns to the status it had; the decision and the note go to the status log."""
    check_step(key)
    with db.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        row = ensure(con, video_id)[key]
        if row["status"] != "stale":
            raise StateError(f"{label(key)} adımı eskimiş değil; eskimeyi kaldırmaya gerek yok.")
        fields = {"inputs": inputs} if inputs is not None else {}
        _update(con, video_id, key, status=row["status_before_stale"] or "ready", status_before_stale=None, stale_reason=None, **fields)
        _log(con, video_id, key, f"{label(key)}: eskime kaldırıldı (“Bu değişiklik etkilemiyor”). Sebep: {row['stale_reason'] or '—'} "
                                 f"Not: {(note or '').strip() or 'yok'}")
        return _rows(con, video_id)


def log(db, video_id, key, text):
    with db.connect() as con:
        _log(con, video_id, key, text)


def history(db, video_id, limit=200):
    with db.connect() as con:
        return [dict(r) for r in con.execute("SELECT id,step,at,text FROM video_step_log WHERE video_id=? ORDER BY id DESC LIMIT ?",
                                             (video_id, limit))]


def active_steps(db):
    """(video id, step) of the work that runs now: a text run (its plan or its writing) and a title run started from a video."""
    with db.connect() as con:
        found = set()
        for row in con.execute("SELECT video_id, state FROM text_runs WHERE status IN ('running','waiting_limit')"):
            approved = bool(json.loads(row["state"] or "{}").get("plan_onaylandi"))
            found.add((row["video_id"], "yazim" if approved else "plan"))
        for row in con.execute("SELECT json_extract(params,'$.video_id'), json_extract(params,'$.video_adimi') FROM claude_runs "
                               "WHERE status='running'"):
            if row[0]:
                found.add((row[0], row[1] or "baslik"))
    return found


def recover(db, video_id=None):
    """A step that looks running while none of its work runs becomes error (the program closed half way)."""
    with db.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        active = active_steps(db)      # read under the write lock: a run started just before it would look like a step with no work
        rows = con.execute("SELECT video_id, step FROM video_steps WHERE status='running' AND (? IS NULL OR video_id=?)",
                           (video_id, video_id)).fetchall()
        for row in rows:
            if (row["video_id"], row["step"]) in active:
                continue
            _update(con, row["video_id"], row["step"], status="error", error=INTERRUPTED)
            _log(con, row["video_id"], row["step"], f"{label(row['step'])} adımı çalışıyor görünüyordu ama çalışan işi yoktu; durumu hata "
                                                    f"yapıldı: {INTERRUPTED}")


def pack_built(db, video_id, pack_id):
    """The video's pack was made (again): the pack step is done and the later steps that have an output are stale."""
    return set_step(db, video_id, "paket", "done", ref=pack_id, inputs=None, stale_from="plan", reason=REASONS["paket"])


def writing_done(db, video_id, run_id):
    """Every chosen tone is written: the writing is done and the check opens for approval (an approved check becomes stale)."""
    with db.connect() as con:
        con.execute("BEGIN IMMEDIATE")
        _apply_set(con, video_id, "yazim", "done", {"ref": run_id, "note": None})
        check = _rows(con, video_id)["kontrol"]
        if check["status"] == "approved" or (check["status"] == "stale" and check["status_before_stale"] == "approved"):
            _apply_stale(con, video_id, "kontrol", REASONS["yazim"])
        else:
            _apply_set(con, video_id, "kontrol", "awaiting_approval", {"ref": run_id})


def choice_valid(db, video_id):
    """Is the chosen text (the tone picked with the check's approval) still the video's choice?"""
    row = step(db, video_id, "kontrol")
    return row["status"] == "approved" or (row["status"] == "stale" and row["status_before_stale"] == "approved")


def check_data(db, destination_id, video_id, rows):
    """The pack step becomes stale when the data was collected again after the video's pack was made (once per collection: a cleared
    staleness remembers the collection it was cleared for)."""
    row = rows["paket"]
    if row["status"] != "done" or not row["ref"]:
        return rows
    latest = latest_done_run(db, destination_id)
    if not latest:
        return rows
    with db.connect() as con:
        pack = con.execute("SELECT created_at FROM evidence_packs WHERE id=?", (row["ref"],)).fetchone()
    made = moment(pack["created_at"]) if pack else None
    seen = moment(row["inputs"]) if row["inputs"] else None
    newest = moment(latest)
    if made is None or newest is None or newest <= made or (seen is not None and newest <= seen):
        return rows
    return mark_stale(db, video_id, "paket", REASONS["veri"], only=True)


# ---- what the sidebar and the step screens read ---------------------------------------------------------------------------------------

NEXT = {
    ("baslik", "ready"): "Bu videonun başlığını seç: konu bankasından bir aday al ya da kendi başlığını yazıp Claude'a değerlendirt.",
    ("baslik", "running"): "Claude başlığı değerlendiriyor; bitince adaylar bu ekranda görünür.",
    ("baslik", "awaiting_approval"): "Başlığı ve vaadi oku; uygunsa “Onayla”, değişmesi gerekiyorsa notunu yazıp “Düzeltme iste”.",
    ("baslik", "approved"): "Başlık onaylandı. Sonraki adım: 2 · Veri paketi.",
    ("baslik", "error"): "Son Claude çalışması hata verdi; sebebi aşağıda. Yeniden deneyebilir ya da bankadan bir başlık seçebilirsin.",
    ("paket", "waiting"): "Önce 1 · Başlık ve vaat adımı onaylanmalı.",
    ("paket", "ready"): "“Veri paketini üret” düğmesine bas; Claude çalışmaz.",
    ("paket", "done"): "Veri paketi hazır. Sonraki adım: 3 · Plan.",
    ("paket", "error"): "Veri paketi üretilemedi; sebebi aşağıda. “Veri paketini üret” ile yeniden dene.",
    ("plan", "waiting"): "Önce 2 · Veri paketi adımı bitmeli.",
    ("plan", "ready"): "“Planı çıkar” düğmesine bas; tahmin düğmenin üstünde yazar.",
    ("plan", "running"): "Claude planı yazıyor; harcama ve “İptal” aşağıda.",
    ("plan", "awaiting_approval"): "Planı oku; uygunsa “Onayla”. Onaylanmadan yazım başlamaz.",
    ("plan", "approved"): "Plan onaylandı. Sonraki adım: 4 · Yazım.",
    ("plan", "error"): "Plan çalışması yarıda kaldı ya da hata verdi; “Kaldığı yerden sürdür” ile devam et ya da “Planı çıkar” ile yeniden başlat.",
    ("yazim", "waiting"): "Önce 3 · Plan adımı onaylanmalı; plan onaylanmadan yazım başlamaz.",
    ("yazim", "ready"): "Tonları seç ve “Yazımı başlat” düğmesine bas; tahmin düğmenin üstünde yazar.",
    ("yazim", "running"): "Metin yazılıyor; halka tablosu ve “İptal” aşağıda.",
    ("yazim", "done"): "Metin yazıldı. Sonraki adım: 5 · Kontrol ve ton seçimi.",
    ("yazim", "error"): "Yazım yarıda kaldı ya da hata verdi; “Kaldığı yerden sürdür” biten halkaları yeniden çalıştırmadan devam eder.",
    ("kontrol", "waiting"): "Önce 4 · Yazım adımı bitmeli.",
    ("kontrol", "ready"): "“Kontrolü yeniden aç” ile karşılaştırmaya dön ya da 4 · Yazım adımında metni yeniden yazdır.",
    ("kontrol", "awaiting_approval"): "Denetim bulgularına ve tonların karşılaştırmasına bak; devam edilecek tonu seçip “Onayla”.",
    ("kontrol", "approved"): "Ton seçildi. Sonraki adım: 6 · Yayın paketi.",
    ("yayin", "waiting"): "Önce 5 · Kontrol ve ton seçimi onaylanmalı; yayın paketi onaylı metinden yazılır.",
    ("yayin", "ready"): "“Yayın paketini çıkar” düğmesine bas; tahmin düğmenin üstünde yazar.",
    ("yayin", "running"): "Claude yayın paketini yazıyor; harcama ve “İptal” aşağıda.",
    ("yayin", "awaiting_approval"): "Bölümleri, açıklamayı, sorguları, etiketleri ve kapağı oku; uygunsa “Onayla”. Bölüm zamanları tahminidir.",
    ("yayin", "approved"): "Yayın paketi onaylandı. Sonraki adım: 7 · Seslendirme.",
    ("yayin", "error"): "Yayın paketi çalışması hata verdi; sebebi aşağıda. “Yayın paketini çıkar” ile yeniden dene.",
    ("ses", "waiting"): "Önce 6 · Yayın paketi onaylanmalı; seslendirme metni onaylı metinden hazırlanır.",
    ("ses", "ready"): "Seslendirme metni ekran açılınca hazırlanır.",
    ("ses", "awaiting_audio"): "Metin dosyaları hazır. Sesi bu dosyalarla üretip “Sesi yükle” ile yükle (mp3 ya da wav; tek dosya ya da _01, _02… parçalar).",
    ("ses", "audio_ready"): "Ses yüklendi. “Sesi cümlelerle eşleştir” düğmesine bas.",
    ("ses", "done"): "Ses cümlelerle eşleşti. Sonraki adım: 8 · Kurgu paketi (paketi yeniden kurun; zamanlar pakete girer).",
    ("ses", "error"): "Seslendirme hata verdi; sebebi aşağıda. “Metni yeniden hazırla” ile yeniden dene.",
    ("kurgu", "waiting"): "Önce 6 · Yayın paketi onaylanmalı; kurgu paketi onaylı metinden kurulur.",
    ("kurgu", "ready"): "Paket ekran açılınca kurulur (ses yoksa zamanlar boş). Uygunsa “Kurguya gönder” düğmesine bas.",
    ("kurgu", "done"): "Paket Kurgu Motoru'na gönderildi; kurgu motorda yapılır. Ses ya da metin değişirse “Paketi yeniden kur” ve yeniden gönder.",
    ("kurgu", "error"): "Kurguya gönderim hata verdi; motorun çıktısı aşağıda. Düzeltip “Kurguya gönder” ile yeniden dene.",
}
STALE_NEXT = "Bu adım eskidi. Yeniden çalıştır ya da değişiklik bu adımı etkilemiyorsa “Bu değişiklik etkilemiyor” de."


def voice_status(row):
    """A row's status; for 7 · Seslendirme "ready" with a stage in `ref` is that stage (awaiting_audio, audio_ready)."""
    return row["ref"] if row["step"] == "ses" and row["status"] == "ready" and row["ref"] in VOICE else row["status"]


def step_view(row, number):
    key = row["step"]
    planned = key in PLANNED
    status = voice_status(row)
    if planned:
        next_text = f"{PLANNED_NOTE}. {PLANNED[key]}"
    elif status == "stale":
        next_text = STALE_NEXT
    else:
        next_text = NEXT.get((key, status), "")
    return {"id": key, "number": number, "title": TITLES[key], "status": status,
            "label": PLANNED_NOTE.lower() if planned else STATUS_LABELS.get(status) or VOICE[status], "next": next_text,
            "detail": row["stale_reason"] if status == "stale" else row["error"] if status == "error" else None,
            "planned": planned, "approval": key in APPROVAL, "stale_reason": row["stale_reason"],
            "status_before_stale": row["status_before_stale"], "note": row["note"], "error": row["error"], "ref": row["ref"],
            "updated_at": row["updated_at"]}


def progress(rows):
    return {"completed": sum(1 for key in KEYS if rows[key]["status"] in COMPLETE), "total": len(KEYS)}


def compute(db, destination_id, video_id):
    """The open video's eight steps for the sidebar and the screens (None: no video). An unknown or foreign video counts as none."""
    from .ai import store
    video = store.video(db, video_id) if video_id else None
    if video is None or video["destination_id"] != destination_id:
        return {"video": None, "steps": [], "completed": 0, "total": len(KEYS)}
    recover(db, video_id)
    rows = check_data(db, destination_id, video_id, steps(db, video_id))
    return {"video": {k: video.get(k) for k in ("id", "name", "title_en", "title_tr", "region_name", "created_at", "archived_at")}
            | {"display_name": display_name(video)},
            "steps": [step_view(rows[key], number) for number, key in enumerate(KEYS, 1)], **progress(rows)}


def display_name(video):
    """The name a video is shown with: its Turkish title, else its working name."""
    return video.get("title_tr") or video.get("name") or "Adsız video"
