"""GÖREV-15 Adım 8–9: every status of the Video metni step in the workflow, computed from the text runs, the versions and the choice:
bekliyor (no pack), hazır, çalışıyor (and the usage limit wait), duraklatıldı, hata, onay bekliyor, tamamlandı, eskidi (the data fetched
again and the pack changed after the chosen version; one of the two alone is not enough)."""
import time
import uuid
from datetime import datetime, timezone

from studio.text import store
from tests.text_helpers import FakeClock, add_video, app, open_app, start_text, text_env  # noqa: F401

ONE_TONE = [{"dosya": "arastirmaci_dost", "ad": "Araştırmacı dost"}]


def metin(client, video_id="v1"):
    steps = client.get("/api/workflow", params={"video_id": video_id}).json()["steps"]
    return next(s for s in steps if s["id"] == "metin")


def fetched_again(db):
    """A finished collector run of the destination now (only its finish time matters to the workflow)."""
    identifier, stamp = uuid.uuid4().hex, datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    with db.connect() as con:
        con.execute("""INSERT INTO jobs (id,kind,title,status,progress,message,created_at,finished_at,result,log,destination_id)
            VALUES (?,'source_collection','deneme','done',100,'',?,?,'{}','[]','30a')""", (identifier, stamp, stamp))
        con.execute("""INSERT INTO source_runs (id,job_id,status,started_at,finished_at,connector_name,connector_version,metadata,destination_id)
            VALUES (?,?,'done',?,?,'deneme','deneme/1','{}','30a')""", (identifier, identifier, stamp, stamp))


def test_every_status_of_the_video_text_step(app):
    db = app.app.state.db
    add_video(app, "v0", with_pack=False)
    step = metin(app, "v0")
    assert (step["status"], step["label"], step["planned"]) == ("waiting", "bekliyor", False)
    assert step["next"] == "Önce paket üretilmeli (3. adım: Veri paketi)."

    add_video(app)
    step = metin(app)
    assert (step["status"], step["label"], step["next"]) == ("ready", "hazır", "Ton seç ve “Metni yaz”a bas.")

    store.insert_run(db, run_id="t1", destination_id="30a", video_id="v1", job_id=None, tones=ONE_TONE, pack_id=None)
    step = metin(app)
    assert (step["status"], step["label"]) == ("running", "çalışıyor") and step["next"] == "Video metni yazılıyor; ilerlemesi İşler panelinde."
    waiting = "Claude kullanım sınırı: 03:00'te kendiliğinden sürecek."
    store.update_run(db, "t1", status="waiting_limit", reason_text=waiting)
    step = metin(app)
    assert (step["status"], step["next"], step["detail"]) == ("running", waiting, "kullanım sınırı bekleniyor")

    store.update_run(db, "t1", status="paused", reason_text="Durduruldu; “Devam” kalan adımları çalıştırır.")
    step = metin(app)
    assert (step["status"], step["label"]) == ("paused", "duraklatıldı")
    assert step["next"] == "Metin çalışması durdu: Durduruldu; “Devam” kalan adımları çalıştırır. “Devam” ile sürdürün."
    store.update_run(db, "t1", status="interrupted", reason_text="Program kapanırken yarıda kaldı; “Devam” kalan adımları çalıştırır.")
    assert metin(app)["status"] == "paused"
    store.update_run(db, "t1", status="error", reason_text="Plan: pakette olmayan kimlik (K9999).")
    step = metin(app)
    assert (step["status"], step["label"]) == ("error", "hata") and step["next"] == "Metin çalışması hata verdi: Plan: pakette olmayan kimlik (K9999)."
    store.update_run(db, "t1", status="awaiting_comparison")                    # a finished run without a version of its own
    assert metin(app)["status"] == "ready"

    view = start_text(app)
    step = metin(app)
    assert (step["status"], step["label"]) == ("awaiting_approval", "onay bekliyor")
    assert step["next"] == "Karşılaştırma ekranında tonları karşılaştır ve “Bu tonla devam et” de."

    assert app.post(f"/api/metin/surumler/{view['surumler'][0]['id']}/sec", json={}).status_code == 200
    step = metin(app)
    assert (step["status"], step["label"]) == ("done", "tamamlandı")
    assert step["next"] == "Seçilen metin: Araştırmacı dost (1. sürüm). Sonraki adım: Kontrol (henüz kurulmadı)."

    time.sleep(0.01)
    fetched_again(db)                                                            # the data fetched again, the pack not changed: done
    assert metin(app)["status"] == "done"
    assert app.post("/api/videos/v1/evidence-pack").status_code == 201        # and the pack changed: stale (information)
    step = metin(app)
    assert (step["status"], step["label"], step["detail"]) == ("stale", "eskidi", "veri yeniden çekildi ve paket seçilen sürümden sonra değişti")
    assert step["next"].startswith("Seçilen metin: Araştırmacı dost (1. sürüm). Seçilen sürümden sonra veri yeniden çekildi ve paket değişti")


def test_a_new_pack_without_new_data_does_not_make_the_chosen_text_stale(app):
    add_video(app)
    view = start_text(app)
    assert app.post(f"/api/metin/surumler/{view['surumler'][0]['id']}/sec", json={}).status_code == 200
    assert app.post("/api/videos/v1/evidence-pack").status_code == 201
    assert metin(app)["status"] == "done"
