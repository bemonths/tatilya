"""Shared pieces of the video text tests (GÖREV-15): an app with the fake Claude and a copy of the tones, a video record with its pack,
waiting for a text run and a clock that skips waiting."""
import json
import shutil
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from studio import evidence
from studio.app import create_app
from studio.destinations import thirty_a
from studio.evidence import video as V
from tests.test_beaches import HEADERS

FAKE = Path(__file__).resolve().parent / "fake_claude.py"


class FakeClock:
    """The chain's clock: waiting moves it forward at once (the usage limit and transient waits in tests)."""

    def __init__(self):
        self.offset = 0.0
        self.slept = []

    def time(self):
        return time.time() + self.offset

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.offset += seconds
        time.sleep(0.001)


@pytest.fixture
def text_env(tmp_path, monkeypatch):
    folder = tmp_path / "tonlar"
    shutil.copytree(thirty_a.TEXT["tones"], folder)
    phrases = tmp_path / "uyari_ifadeleri.txt"
    shutil.copyfile(thirty_a.TEXT["warning_phrases"], phrases)
    monkeypatch.setitem(thirty_a.TEXT, "tones", folder)
    monkeypatch.setitem(thirty_a.TEXT, "warning_phrases", phrases)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "ok")
    monkeypatch.delenv("FAKE_CLAUDE_TEXT", raising=False)
    monkeypatch.setenv("FAKE_CLAUDE_STATE", str(tmp_path / "sahte_durum.json"))
    monkeypatch.setenv("FAKE_CLAUDE_LOG", str(tmp_path / "sahte_oturumlar.jsonl"))
    return tmp_path


def open_app(data, clock=None):
    client = TestClient(create_app(data), headers=HEADERS)
    client.__enter__()
    client.data = data
    if clock is not None:
        client.app.state.text.clock = clock
    assert client.put("/api/settings/claude", json={"claude_path": str(FAKE)}).status_code == 200
    return client


@pytest.fixture
def app(text_env):
    clock = FakeClock()
    client = open_app(text_env / "data", clock)
    client.clock = clock
    client.env = text_env
    try:
        yield client
    finally:
        client.__exit__(None, None, None)


def add_video(client, video_id="v1", with_pack=True):
    """A video record whose content plan cites five rows of the general pack (and a hook row the plan does not cite)."""
    db = client.app.state.db
    record, _ = evidence.fresh_pack(db, "30a", thirty_a, "ilk-video", {})
    path, _ = evidence.stored_file(db, record["id"], "json")
    pack = json.loads(path.read_text(encoding="utf-8"))
    rows = [r for s in pack["sections"] for r in s["rows"] if r.get("durum") == "var"]
    cite = lambda row: V.cited(row, dosya="veri_ozeti_30a.md", pack_id=record["id"])
    analysis = {"paketler": {"veri_ozeti_30a.md": record["id"]}, "izleyici_sorusu": "Ne zaman gitmeli?", "neden_onerildi": "Deneme.",
                "kanca": {"metin": "Kanca.", "kanitlar": [cite(rows[-1])]}, "eksik_veri": ["Bir eksik."], "kapak_fikri": "Kapak.",
                "icerik_plani": [{"bolum": f"Bölüm {n}", "ne_anlatir": f"Soru {n}?", "kanitlar": [cite(rows[n * 3])]} for n in range(1, 6)]}
    with db.connect() as con:
        if not con.execute("SELECT 1 FROM claude_runs WHERE id='r1'").fetchone():
            con.execute("""INSERT INTO claude_runs (id,destination_id,step,scope_id,status,params,folder,created_at)
                VALUES ('r1','30a','baslik','r1','approved','{}','claude/r1/baslik/r1','2026-10-10T10:00:00+00:00')""")
        candidate = con.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
        con.execute("""INSERT INTO videos (id,destination_id,region_name,title_en,title_tr,family,analysis,params,status,created_at,run_id,
            candidate,proposed_title_en,proposed_title_tr,user_edited) VALUES (?,'30a','30A geneli','Deneme | 30A Florida Vacation',
            'Deneme | 30A Florida Tatili','Deneyim',?,'{}','baslik_secildi','2026-10-10T10:01:00+00:00','r1',?,'Deneme | 30A Florida Vacation',
            'Deneme | 30A Florida Tatili',0)""", (video_id, json.dumps(analysis, ensure_ascii=False), candidate))
    if with_pack:
        made = client.post(f"/api/videos/{video_id}/evidence-pack")
        assert made.status_code == 201, made.json()
    return video_id


def wait_run(client, run_id, limit=120, until=("running", "waiting_limit")):
    end = time.monotonic() + limit
    while time.monotonic() < end:
        view = client.get(f"/api/metin/calismalar/{run_id}").json()
        if view["status"] not in until:
            return view
        time.sleep(0.2)
    raise AssertionError(f"metin çalışması bitmedi: {view['status']}")


def start_plan(client, video_id="v1", wait=True, note=None):
    """3 · Plan: "Planı çıkar" (GÖREV-21). The run writes the plan and stops for the user's approval (paused, "plan_hazir")."""
    started = client.post(f"/api/videos/{video_id}/plan", json={"not": note} if note else {})
    assert started.status_code == 201, started.json()
    if not wait:
        return started.json()
    view = wait_run(client, started.json()["id"])
    # The run stops for the approval a moment before its job ends, and the step leaves "running" only when the job has ended
    # (GÖREV-23): the plan is ready for a decision when the step says so; wait for the step itself, not for the clock.
    end = time.monotonic() + 120
    while step_status(client, "plan", video_id) == "running":
        assert time.monotonic() < end, "3 · Plan adımı 120 saniyede 'çalışıyor' durumundan çıkmadı"
        time.sleep(0.05)
    return view


def decide(client, step, action="onayla", video_id="v1", **body):
    """The approval component: onayla, duzeltme, reddet, etkilemiyor."""
    return client.post(f"/api/videos/{video_id}/adimlar/{step}/{action}", json=body)


def step_status(client, step, video_id="v1"):
    return client.get(f"/api/videos/{video_id}/adimlar/{step}").json()["adim"]["status"]


def start_writing(client, tones=("arastirmaci_dost",), video_id="v1", wait=True):
    """4 · Yazım: "Yazımı başlat" with the approved plan."""
    started = client.post(f"/api/videos/{video_id}/yazim", json={"tonlar": list(tones)})
    assert started.status_code == 201, started.json()
    return wait_run(client, started.json()["id"]) if wait else started.json()


def start_text(client, tones=("arastirmaci_dost",), video_id="v1", wait=True, plan_env=None):
    """The whole text of a video as the user gets it since GÖREV-21: the plan, its approval, then the writing (the same text run goes
    on). `plan_env`: (monkeypatch, {name: value}) set only after the plan is approved (troubles meant for the writing)."""
    plan = start_plan(client, video_id)
    if not (plan["status"] == "paused" and plan["reason"] == "plan_hazir"):
        return plan                                  # the plan itself did not finish (an error, a pause): the test looks at that
    approved = decide(client, "plan", video_id=video_id)
    assert approved.status_code == 200, approved.json()
    if plan_env:
        patcher, values = plan_env
        for name, value in values.items():
            patcher.setenv(name, value)
    return start_writing(client, tones, video_id, wait)


def sessions(view, step=None, tone=None):
    return [s for s in view["oturumlar"] if (step is None or s["step"] == step) and (tone is None or s["tone"] == tone)]


def text_job(client, settled=False, limit=120):
    """The text run's job; settled=True waits until it has ended (the run changes its state a moment before its job's last message).
    The wait ends when the job has ended, never by the clock: a job still running at the limit is a failure, not an answer."""
    import time
    end = time.monotonic() + limit
    while True:
        job = next(j for j in client.get("/api/jobs").json() if j["kind"] == "claude_metin")
        if not settled or job["status"] not in ("queued", "running"):
            return job
        if time.monotonic() >= end:
            raise AssertionError(f"metin işi {limit} saniyede bitmedi: {job['status']}")
        time.sleep(0.05)
