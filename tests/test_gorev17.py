"""GÖREV-17: taking finished jobs off the job panel (hiding only; schema 19), one window for a job (the extension's and the program's
own browsers), the words for a region-blocked site read through the proxy, and a program folder that was moved."""
import json
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from studio import extension as ext
from studio import install_stamp
from studio import proxy as P
from studio.app import create_app
from studio.database import SCHEMA_VERSION, Conflict, Database
from studio.sources import browser_verification as bv
from studio.sources import region_reader as R
from tests.legacy import drop_v19
from tests.test_beaches import HEADERS
from tests.test_extension import as_extension, paired
from tests.test_extension_16 import SITES, ProxyRegion, run_trial

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path), headers=HEADERS) as client:
        client.data = tmp_path
        yield client


def finished_job(db, title, status="done", lines=3):
    job = db.add_job("eklenti_deneme", title)
    db.update_job(job, status="running", message="başladı")
    for number in range(lines):
        db.update_job(job, message=f"satır {number}")
    db.update_job(job, status=status, progress=100, result={"tamam": True}, message="bitti")
    return job


# --- Adım 2: the job panel --------------------------------------------------------------------------------------------------

def test_a_finished_job_is_hidden_and_brought_back_and_nothing_is_deleted(tmp_path):
    db = Database(tmp_path / "studio.sqlite3")
    db.initialize()
    job = finished_job(db, "Biten iş", lines=40)
    before = db.job(job)
    assert db.hide_job(job) is True and db.hide_job(job) is True               # hiding twice is the same
    listed = {j["id"]: j for j in db.jobs()}
    assert listed[job]["hidden_at"] and len(listed[job]["log"]) == len(before["log"]) == 42    # still there, with its whole log
    hidden = db.hidden_jobs()
    assert [h["id"] for h in hidden] == [job] and hidden[0]["log_count"] == 42 and "log" not in hidden[0]
    after = db.job(job)
    assert (after["log"], after["result"], after["status"], after["message"]) == (before["log"], before["result"], "done", "bitti")
    assert db.unhide_job(job) is True and db.hidden_jobs() == [] and {j["id"]: j for j in db.jobs()}[job]["hidden_at"] is None
    assert db.hide_job("yok") is None and db.unhide_job("yok") is None


def test_a_running_or_queued_job_cannot_be_hidden(tmp_path):
    db = Database(tmp_path / "studio.sqlite3")
    db.initialize()
    queued = db.add_job("eklenti_deneme", "Sırada")
    with pytest.raises(Conflict):
        db.hide_job(queued)
    db.update_job(queued, status="running", message="çalışıyor")
    with pytest.raises(Conflict):
        db.hide_job(queued)
    assert db.hidden_jobs() == []


def test_bitenleri_kaldir_takes_only_finished_jobs_and_leaves_the_ones_waiting_for_approval(tmp_path):
    db = Database(tmp_path / "studio.sqlite3")
    db.initialize()
    done, failed, canceled = (finished_job(db, f"iş {s}", s) for s in ("done", "failed", "canceled"))
    interrupted = finished_job(db, "yarıda", "interrupted")
    awaiting = finished_job(db, "Claude · onay bekliyor")
    with db.connect() as con:                     # a finished Claude run that still waits for the user's choice
        destination = con.execute("SELECT destination_id FROM jobs WHERE id=?", (awaiting,)).fetchone()[0]
        con.execute("""INSERT INTO claude_runs (id,destination_id,step,scope_id,job_id,status,params,folder,created_at)
            VALUES ('run-1',?,'baslik','bolge',?,'awaiting_approval','{}','claude/run-1','2026-11-11T10:00:00+00:00')""",
                    (destination, awaiting))
    running = db.add_job("catalog_audit", "Çalışan")
    db.update_job(running, status="running", message="çalışıyor")
    assert db.hide_finished_jobs() == 4
    state = {j["id"]: (bool(j["hidden_at"]), bool(j["awaiting_approval"])) for j in db.jobs()}
    assert state == {done: (True, False), failed: (True, False), canceled: (True, False), interrupted: (True, False),
                     awaiting: (False, True), running: (False, False)}
    assert db.hide_finished_jobs() == 0
    assert db.hide_job(awaiting) is True          # one by one the user may still take it off


def test_the_job_panel_api_hides_brings_back_and_refuses_a_running_job(client):
    db = client.app.state.db
    first, second = finished_job(db, "Birinci"), finished_job(db, "İkinci", "failed")
    running = db.add_job("catalog_audit", "Çalışan")
    db.update_job(running, status="running", message="çalışıyor")
    answer = client.post(f"/api/jobs/{first}/kaldir").json()
    assert [h["id"] for h in answer["gizlenen"]] == [first] and {j["id"]: bool(j["hidden_at"]) for j in answer["jobs"]}[first]
    assert client.post(f"/api/jobs/{running}/kaldir").status_code == 409 and client.post("/api/jobs/yok/kaldir").status_code == 404
    bulk = client.post("/api/jobs/bitenleri-kaldir").json()
    assert bulk["kaldirilan"] == 1 and {h["id"] for h in bulk["gizlenen"]} == {first, second}
    assert {h["id"] for h in client.get("/api/jobs/gizlenen").json()} == {first, second}
    back = client.post(f"/api/jobs/{second}/geri-getir").json()
    assert [h["id"] for h in back["gizlenen"]] == [first] and client.post("/api/jobs/yok/geri-getir").status_code == 404
    assert len(client.get("/api/jobs").json()) == 3                           # every job is still in the list the screens use
    assert db.job(running)["status"] == "running"


def test_v18_to_v19_adds_the_table_keeps_every_row_and_hides_nothing(tmp_path):
    path = tmp_path / "studio.sqlite3"
    db = Database(path)
    db.initialize()
    job = finished_job(db, "Eski iş", lines=5)
    with sqlite3.connect(path) as con:
        drop_v19(con)
        con.execute("PRAGMA user_version=18")
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        before = {t: con.execute(f'SELECT * FROM "{t}" ORDER BY rowid').fetchall() for t in tables}
    Database(path).initialize()
    with sqlite3.connect(path) as con:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 19 == SCHEMA_VERSION
        assert con.execute("PRAGMA foreign_key_check").fetchall() == [] and con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        after = {t: con.execute(f'SELECT * FROM "{t}" ORDER BY rowid').fetchall() for t in tables}
        assert after == before and con.execute("SELECT COUNT(*) FROM job_hidden").fetchone()[0] == 0
    assert list((tmp_path / "backups").glob("studio-v18-*.sqlite3"))
    assert Database(path).job(job)["status"] == "done" and Database(path).hidden_jobs() == []


# --- Adım 4: one window for a job -------------------------------------------------------------------------------------------

def test_the_extension_keeps_one_window_while_the_job_runs_and_is_told_to_close_it_when_it_ends(client):
    bridge, db = paired(client), client.app.state.db
    bridge.allowed = ["a.test", "b.test"]
    job = db.add_job("eklenti_deneme", "Deneme")
    db.update_job(job, status="running", message="başladı")
    access = ext.JobAccess(bridge, db, job)
    first = access.open("a.test")
    taken = as_extension(client, "/api/eklenti/sor", {"surum": ext.EXPECTED_VERSION, "izinli": ["a.test", "b.test"]}).json()
    assert taken["is"]["pencere"] == job and taken["acik_pencereler"] == [job]
    first.close()
    as_extension(client, f"/api/eklenti/is/{taken['is']['id']}/sonraki")
    as_extension(client, f"/api/eklenti/is/{taken['is']['id']}/bitti")
    # between two sites of the job nothing waits for the extension, but its window must stay for the next site
    idle = as_extension(client, "/api/eklenti/sor", {"surum": ext.EXPECTED_VERSION, "izinli": ["a.test", "b.test"]}).json()
    assert idle["is"] is None and idle["acik_pencereler"] == [job]
    assert db.job(job)["progress_info"]["asama"] == "sıradaki sayfa bekleniyor"
    second = access.open("b.test")
    again = as_extension(client, "/api/eklenti/sor", {"surum": ext.EXPECTED_VERSION, "izinli": ["a.test", "b.test"]}).json()
    assert again["is"]["pencere"] == job and again["is"]["id"] != taken["is"]["id"]      # the same window key for the next site
    second.close()
    db.update_job(job, status="canceled", message="İş iptal edildi.")
    ended = as_extension(client, "/api/eklenti/sor", {"surum": ext.EXPECTED_VERSION, "izinli": []}).json()
    assert ended["acik_pencereler"] == []                                             # finished or cancelled: the window closes


def test_a_handed_over_job_and_a_finished_trial_do_not_keep_the_window(client):
    bridge, db = paired(client), client.app.state.db
    job = db.add_job("eklenti_deneme", "Deneme")
    db.update_job(job, status="running", message="başladı")
    ext.JobAccess(bridge, db, job).open("a.test")
    trial = bridge.open("127.0.0.1", purpose="deneme")
    assert sorted(bridge.open_windows()) == sorted([job, trial.id]) and trial.view()["pencere"] == trial.id
    bridge.hand_over(job)
    assert bridge.open_windows() == [trial.id]
    trial.close()
    assert bridge.open_windows() == []


def test_the_extension_files_open_one_unfocused_window_and_never_close_it_per_site():
    background = (ROOT / "eklenti" / "background.js").read_text(encoding="utf-8")
    logic = (ROOT / "eklenti" / "logic.js").read_text(encoding="utf-8")
    manifest = json.loads((ROOT / "eklenti" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == ext.EXPECTED_VERSION == "0.19.0"
    assert background.count("chrome.windows.create(") == 1 and "chrome.windows.create({...L.WINDOW_OPTIONS})" in background
    assert 'focused: false, type: "normal"' in logic and "minimized" not in logic.split("WINDOW_OPTIONS = ")[1].split("\n")[0]
    run_job = background.split("async function runJob")[1].split("/** Open an address")[0]
    assert "chrome.windows.remove" not in run_job and "ensureWindow(L.windowKey(job))" in run_job    # no window per site
    assert background.count("chrome.windows.remove(") == 1                                         # only closeWindow closes it
    assert "syncWindow(answer.acik_pencereler)" in background
    assert 'chrome.windows.update(windowId, {focused: true, state: "normal"})' in background           # forward only for a verification


class FakeBrowser:
    def __init__(self):
        self.closed = []

    def close(self, endpoint, profile):
        self.closed.append((endpoint, Path(profile)))


def test_a_browser_the_job_started_is_closed_when_the_job_ends_and_the_panel_names_the_window(tmp_path, monkeypatch):
    db = Database(tmp_path / "studio.sqlite3")
    db.initialize()
    job = db.add_job("eklenti_deneme", "Deneme")
    db.update_job(job, status="running", message="başladı", progress_info={"tur": "eklenti", "bekliyor": False})
    fake = FakeBrowser()
    monkeypatch.setattr(bv, "running_endpoint", lambda profile, check=None: f"http://127.0.0.1:9/{Path(profile).name}")
    with bv.JobWindows(lambda key, text: db.set_job_window(job, key, text), close=fake.close) as windows:
        assert bv.JobWindows.current() is windows
        first, second = bv.window_opened("program"), bv.window_opened("program")
        bv.window_note("program", "oversee.us okunuyor")
        bv.browser_started(tmp_path / "profil")
        bv.browser_started(tmp_path / "profil")
        assert db.job(job)["progress_info"]["pencereler"] == {"program": "oversee.us okunuyor"}
        db.update_job(job, progress_info={"tur": "eklenti", "bekliyor": False, "asama": "a.test · sayfa okunuyor"})
        assert db.job(job)["progress_info"]["pencereler"] == {"program": "oversee.us okunuyor"}      # the extension's word keeps it
        first.closed("program")
        assert db.job(job)["progress_info"]["pencereler"] == {"program": "oversee.us okunuyor"}      # another tab is still open
        second.closed("program")
        assert db.job(job)["progress_info"]["pencereler"] == {}
        assert fake.closed == []                                                                      # not before the job ends
    assert fake.closed == [("http://127.0.0.1:9/profil", tmp_path / "profil")] and bv.JobWindows.current() is None
    bv.window_note("program", "iş yokken not")                                                        # without a job: nothing happens
    bv.browser_started(tmp_path / "profil")


def test_a_browser_stays_while_another_job_still_reads_and_one_already_running_is_never_closed(tmp_path, monkeypatch):
    fake = FakeBrowser()
    monkeypatch.setattr(bv, "running_endpoint", lambda profile, check=None: "http://127.0.0.1:9")
    with bv.JobWindows(close=fake.close) as outer:
        with bv.JobWindows(close=fake.close):
            bv.browser_started(tmp_path / "profil")
        assert fake.closed == [] and outer.launched == [tmp_path / "profil"]         # handed to the job still at work
    assert len(fake.closed) == 1
    # ensure_browser: a browser that was already running (the user's warm-up tabs) is not this job's to close
    profile = tmp_path / "acik-profil"
    profile.mkdir()
    (profile / "DevToolsActivePort").write_text("9222\n", encoding="utf-8")
    monkeypatch.undo()
    with bv.JobWindows(close=fake.close) as windows:
        endpoint, launched = bv.ensure_browser(profile, check=lambda endpoint: True)
        assert (endpoint, launched) == ("http://127.0.0.1:9222", False) and windows.launched == []


def test_the_browser_starts_without_taking_the_focus_and_its_command_line_is_unchanged(tmp_path):
    calls = []
    command = bv.launch_command("chrome.exe", tmp_path)
    assert command == ["chrome.exe", f"--user-data-dir={tmp_path}", "--remote-debugging-port=0"]      # no flag was added
    bv.start_browser(command, popen=lambda *args, **kwargs: calls.append((args, kwargs)))
    (args, kwargs), = calls
    assert args == (command,)
    if sys.platform == "win32":
        startup = kwargs["startupinfo"]
        assert startup.dwFlags & subprocess.STARTF_USESHOWWINDOW and startup.wShowWindow == bv.SW_SHOWNOACTIVATE == 4
        assert kwargs["creationflags"] == subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    proxy_command = R.launch_command("chrome.exe", tmp_path, "function FindProxyForURL(u,h){return 'DIRECT';}")
    assert not [part for part in proxy_command if "minimized" in part or "headless" in part]
    assert "bv.start_browser(command)" in (ROOT / "studio" / "sources" / "region_reader.py").read_text(encoding="utf-8")


class Page:
    def __init__(self, pages):
        self.pages, self.forward = list(pages), 0
        self.url = "https://ornek.test/"

    def content(self):
        return self.pages[0] if len(self.pages) == 1 else self.pages.pop(0)

    def title(self):
        return "Just a moment..." if "cf_chl_opt" in self.pages[0] else "Tamam"

    def bring_to_front(self):
        self.forward += 1


def test_the_window_comes_forward_only_for_a_verification_the_user_has_to_pass():
    challenge, normal = "<title>Just a moment...</title> cf_chl_opt", "<h1>içerik</h1>"
    page, notes = Page([challenge, normal]), []
    with bv.JobWindows(lambda key, text: notes.append((key, text))):
        cleared = bv.wait_for_user({"a.test": page}, lambda: False, 900, lambda site: None, sleep=lambda s: None)
    assert cleared == {"a.test"} and page.forward == 1
    assert notes[0] == ("program", "doğrulama bekleniyor: a.test") and notes[1] == ("program", "açık")
    assert bv.wait_for_user({}, lambda: False, 900, None, sleep=lambda s: None) == set()            # nothing to verify: nothing forward
    # the reading paths never bring a window forward
    for name in ("browser_verification.py", "region_reader.py", "restaurant_sites.py"):
        source = (ROOT / "studio" / "sources" / name).read_text(encoding="utf-8")
        assert "bring_to_front" not in source.replace("page.bring_to_front()", "", 1 if name == "browser_verification.py" else 0)
    reader = (ROOT / "studio" / "sources" / "region_reader.py").read_text(encoding="utf-8")
    assert reader.count("bv.bring_forward(page)") == 1 and reader.index('if kind == "dogrulama":') < reader.index("bv.bring_forward(page)")


def test_the_collectors_job_runs_inside_job_windows(tmp_path):
    source = (ROOT / "studio" / "jobs.py").read_text(encoding="utf-8")
    assert "with JobWindows(lambda key, text: self.db.set_job_window(identifier, key, text)):" in source
    app = (ROOT / "studio" / "app.py").read_text(encoding="utf-8")
    assert "windows.__enter__()" in app and "windows.__exit__(None, None, None)" in app


# --- Adım 5: small fixes -----------------------------------------------------------------------------------------------------

def test_the_words_for_a_region_blocked_site():
    assert P.region_outcome("tamam", None, True) == "bölge engeli · proxy'yle okundu"
    assert P.region_outcome("bolge_engeli", P.NO_PROXY_SKIP) == "bölge engeli · ABD proxy'si tanımlı değil (Ayarlar)"
    failed = P.region_outcome("bolge_engeli", f"{P.PROXY_FAILED_SKIP} (proxy'yle doğrudan istek: bölge engeli, HTTP 403)")
    assert failed == "bölge engeli · proxy'yle de okunamadı (proxy'yle doğrudan istek: bölge engeli, HTTP 403)"
    assert P.region_outcome("bolge_engeli", None) == "bölge engeli"


def test_the_trial_log_says_a_region_blocked_site_was_read_through_the_proxy(client, monkeypatch):
    import httpx
    paired(client)
    handler = lambda request: httpx.Response(200, html="<html><title>Publix locations</title><body>" + "Store list. " * 60 + "</body></html>")
    db = client.app.state.db
    client.app.state.region_access = lambda: ProxyRegion(db, client.data, handler)
    job, _ = run_trial(client, monkeypatch, SITES[:2])
    log = " ".join(entry["text"] for entry in job["log"])
    assert "2/2 · publix.com: bölge engeli · proxy'yle okundu" in log
    assert job["message"] == "2/2 site okundu (1 bölge engelli site proxy'yle)."
    row = {r["alan_adi"]: r for r in job["result"]["siteler"]}["publix.com"]
    assert row["proxy"] is True and row["durum"] == "tamam" and row["tur"] == "bolge_engeli"


def test_a_moved_program_folder_is_noticed(tmp_path):
    root = tmp_path / "yeni-yer"
    venv = root / ".venv"
    venv.mkdir(parents=True)
    assert install_stamp.moved(root) is False                                  # no record: not moved
    (venv / "pyvenv.cfg").write_text("home = C:\\Python312\nversion = 3.12.4\ncommand = C:\\Python312\\python.exe -m venv --clear "
                                     "C:\\Eski Yer\\30a-studio\\.venv\n", encoding="utf-8")
    assert install_stamp.recorded_location(root) == "C:\\Eski Yer\\30a-studio\\.venv" and install_stamp.moved(root) is True
    (venv / "pyvenv.cfg").write_text(f"home = C:\\Python312\ncommand = C:\\Python312\\python.exe -m venv {venv}\n", encoding="utf-8")
    assert install_stamp.moved(root) is False
    install_stamp.write_location(root)                                          # the program's own record wins over pyvenv.cfg
    (venv / "pyvenv.cfg").write_text("command = C:\\Python312\\python.exe -m venv C:\\Baska\\.venv\n", encoding="utf-8")
    assert install_stamp.moved(root) is False
    moved_to = tmp_path / "tasindi"
    root.rename(moved_to)
    assert install_stamp.moved(moved_to) is True
    install_stamp.write_location(moved_to)
    assert install_stamp.moved(moved_to) is False


def test_baslat_bat_renews_the_install_and_the_shortcut_after_a_move():
    text = (ROOT / "baslat.bat").read_bytes().decode("ascii")
    assert "-m studio.install_stamp moved" in text and text.index("install_stamp moved") < text.index("install_stamp check")
    moved = text.split(":moved")[1].split(":create_venv")[0]
    assert 'set "MOVED=1"' in moved and '-m venv "%ROOT%.venv"' in moved and "--clear" not in moved and "goto packages" in moved
    assert "if defined MOVED call :shortcut" in text
