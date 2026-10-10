"""The workflow of a video (GÖREV-14): eight steps with live statuses for the sidebar.

The unit of the workflow is a video record (Housing Atlas uses a state). Statuses are not kept in a file; they are computed from the records
every time (the video record, Claude runs, evidence packs, collector runs), so what the sidebar shows cannot drift from what is stored.

Status codes follow Housing Atlas (TASARIM 6.2): waiting, ready, running, awaiting_approval, approved, done, error, stale; and two of
our own: `due` (Veri: a collector's suggested interval passed) and `planned` (the step is not built yet). Each step carries the "Sıradaki
iş" line its screen starts with: what has to be done and which button does it.
"""
from . import refresh
from .ai import store, title_review
from .evidence.pack import latest_done_run, moment
from .text import store as text_store

STATUS_LABELS = {"waiting": "bekliyor", "ready": "hazır", "running": "çalışıyor", "awaiting_approval": "onay bekliyor",
                 "approved": "onaylandı", "done": "tamamlandı", "error": "hata", "stale": "eskidi", "due": "güncelleme zamanı geldi",
                 "planned": "planlanan", "paused": "duraklatıldı"}
COMPLETE = ("approved", "done")
TITLE_STEPS = ("baslik", "baslik_degerlendirme")
STEPS = (
    ("veri", "Veri"),
    ("baslik", "Konu ve başlık"),
    ("paket", "Veri paketi"),
    ("metin", "Video metni"),
    ("kontrol", "Kontrol"),
    ("gorsel", "Görsel plan"),
    ("uretim", "Video üretimi"),
    ("yayin", "Yayın hazırlığı"),
)
PLANNED = {"kontrol", "gorsel", "uretim", "yayin"}
HREFS = {"baslik": "#videos"}   # the topic and title step is the Videolar screen (proposals, approval, video records)
PLANNED_NEXT = "Bu adım henüz kurulmadı (planlanan). Şimdilik yapılacak iş yok."


def step(key, title, number, status, next_text, label=None, detail=None):
    return {"id": key, "number": number, "title": title, "status": status, "label": label or STATUS_LABELS[status],
            "next": next_text, "detail": detail, "planned": key in PLANNED, "href": HREFS.get(key, f"#adim/{key}")}


def data_step(db, destination_id, jobs, today=None):
    if any(j["kind"] == "source_collection" and j["status"] in ("queued", "running") for j in jobs):
        return "running", "Veri toplanıyor. İş bitince durum kendiliğinden güncellenir; ilerlemesi İşler panelinde.", None
    current = refresh.status(db, destination_id, today)
    if current["batch"] and current["batch"]["status"] == "running":
        return "running", "Zamanı gelen kaynaklar sırayla çekiliyor; ilerlemesi İşler panelinde.", None
    if current["due_count"]:
        names = ", ".join(i["source_name"] for i in current["items"] if i["due"])
        return ("due", f"Güncelleme zamanı gelen {current['due_count']} kaynak var: aşağıdaki 'Zamanı gelenleri başlat' düğmesine bas.",
                names)
    if latest_done_run(db, destination_id) is None:
        return "waiting", "Henüz veri çekilmedi: Veri toplama ekranından kaynakları çek.", None
    return "done", "Veri güncel; yapılacak iş yok. Sonraki adım: Konu ve başlık.", None


def title_step(db, destination_id, video, has_data):
    if video:
        return "approved", f"Başlık seçildi: “{video['title_en']}”. Sonraki adım: Veri paketi.", None
    runs = [r for r in store.runs(db, destination_id) if r["step"] in TITLE_STEPS]
    if any(r["status"] == "running" for r in runs):
        return "running", "Claude çalışıyor. Bitince öneriler bu ekranda onay için görünür; ilerlemesi İşler panelinde.", None
    # GÖREV-15 Adım 1d: an evaluation without candidates ("veriyle dolmuyor") has nothing to approve; it is information, not waiting
    waiting = [r for r in runs if r["status"] == "awaiting_approval" and not title_review.without_candidates(db.path.parent, r)]
    if waiting:
        return ("awaiting_approval", "Başlık seçilmedi: onay bekleyen öneriden bir başlık seç (“Bu başlığı seç”) ya da yeni öneri al.",
                f"{len(waiting)} çalışma onay bekliyor")
    if runs and runs[0]["status"] == "error":
        return ("error", "Son Claude çalışması hata verdi: sebebini çalışmanın ekranında oku, sonra yeniden çalıştır.",
                runs[0].get("error"))
    if not has_data:
        return "waiting", "Önce veri gerekiyor: 1. adımdan (Veri) kaynakları çek.", None
    if runs and title_review.without_candidates(db.path.parent, runs[0]):
        return ("ready", "Son değerlendirme: fikir veriyle dolmuyor (bilgi). Yeni öneri al ya da başka bir başlık yaz; değerlendirmeyi "
                "“Reddet” ile kapatabilirsin.", title_review.NO_CANDIDATES_TEXT)
    chosen = [r for r in runs if r["status"] == "approved"]
    if chosen:
        return ("ready", "Üst çubuktan bir video seç ya da yeni öneri al (“Öneri al”) veya kendi başlığını yaz.", None)
    return "ready", "Henüz başlık önerisi yok: bölgeyi seçip “Öneri al” düğmesine bas ya da kendi başlığını yaz.", None


def pack_step(db, destination_id, video):
    if not video:
        return "waiting", "Önce bir başlık seç (2. adım: Konu ve başlık); paket seçilen başlığın içerik planından kurulur.", None
    packs = video.get("packs") or []
    if not packs:
        return "ready", "Bu videonun veri paketi yok: “Kanıt paketi üret” düğmesine bas.", None
    latest = latest_done_run(db, destination_id)
    made = moment(packs[0]["created_at"])
    if latest and (made is None or made < moment(latest)):
        return "stale", "Paket verinin son çekiminden eski: “Kanıt paketi üret” ile yeniden üret.", "veri paketten sonra yeniden çekildi"
    return "done", "Paket hazır. Sonraki adım: Video metni.", None


def text_step(db, destination_id, video):
    """GÖREV-15 (Adım 8): the video text's status from its runs, versions and the choice."""
    if not video:
        return "waiting", "Önce bir başlık seç ve paketini üret (2. ve 3. adım).", None
    if not (video.get("packs") or []):
        return "waiting", "Önce paket üretilmeli (3. adım: Veri paketi).", None
    runs = text_store.runs(db, video["id"])
    active = [r for r in runs if r["status"] in text_store.ACTIVE]
    if active:
        run = active[0]
        if run["status"] == "waiting_limit":
            return "running", run.get("reason_text") or "Claude kullanım sınırı bekleniyor; çalışma kendiliğinden sürecek.", "kullanım sınırı bekleniyor"
        return "running", "Video metni yazılıyor; ilerlemesi İşler panelinde.", None
    chosen = text_store.selection(db, video["id"])
    if chosen:
        version = text_store.version(db, chosen["version_id"])
        latest = latest_done_run(db, destination_id)
        newest_pack = (video.get("packs") or [{}])[0].get("id")
        made = moment(version["created_at"])
        if latest and made is not None and moment(latest) > made and newest_pack and newest_pack != version.get("pack_id"):
            return ("stale", f"Seçilen metin: {version['tone_name']} ({version['number']}. sürüm). Seçilen sürümden sonra veri yeniden çekildi ve "
                    "paket değişti (bilgi).", "veri yeniden çekildi ve paket seçilen sürümden sonra değişti")
        return ("done", f"Seçilen metin: {version['tone_name']} ({version['number']}. sürüm). Sonraki adım: Kontrol (henüz kurulmadı).", None)
    if runs and runs[0]["status"] in ("paused", "interrupted", "error"):
        run = runs[0]
        reason = run.get("reason_text") or run["status_label"]
        if run["status"] == "error":
            return "error", f"Metin çalışması hata verdi: {reason}", reason
        return "paused", f"Metin çalışması durdu: {reason} “Devam” ile sürdürün.", reason
    if text_store.versions(db, video_id=video["id"]):
        return ("awaiting_approval", "Karşılaştırma ekranında tonları karşılaştır ve “Bu tonla devam et” de.", None)
    return "ready", "Ton seç ve “Metni yaz”a bas.", None


def compute(db, destination_id, video_id=None, today=None):
    """The workflow of the selected video (None: no video selected). Unknown video ids count as no selection."""
    videos = store.videos(db, destination_id)
    video = next((v for v in videos if v["id"] == video_id), None) if video_id else None
    jobs = db.jobs(destination_id)
    data_status, data_next, data_detail = data_step(db, destination_id, jobs, today)
    has_data = latest_done_run(db, destination_id) is not None
    computed = {"veri": (data_status, data_next, data_detail), "baslik": title_step(db, destination_id, video, has_data),
                "paket": pack_step(db, destination_id, video), "metin": text_step(db, destination_id, video)}
    steps = []
    for number, (key, title) in enumerate(STEPS, 1):
        if key in computed:
            status, next_text, detail = computed[key]
            label = "güncel" if key == "veri" and status == "done" else None
            steps.append(step(key, title, number, status, next_text, label, detail))
        else:
            steps.append(step(key, title, number, "planned", PLANNED_NEXT))
    completed = sum(1 for s in steps if s["status"] in COMPLETE)
    return {"video": video and {k: video[k] for k in ("id", "title_en", "title_tr", "region_name", "status", "status_label")},
            "videos": [{"id": v["id"], "title_en": v["title_en"], "title_tr": v["title_tr"], "region_name": v["region_name"]} for v in videos],
            "steps": steps, "completed": completed, "total": len(steps),
            "dots": "".join("●" if s["status"] in COMPLETE else "○" for s in steps)}
