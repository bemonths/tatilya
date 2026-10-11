"""GÖREV-16 Adım 4: a version's usage counts only its tone's sessions; the plan's and the critic's sessions (no tone) are shown once on
the run's "plan" line and above the comparison; a "Bu tonla da yaz" version does not carry the plan's cost; the chosen run says
"seçildi: <ton>" in the list."""
from tests.text_helpers import FakeClock, add_video, app, open_app, start_text, text_env, wait_run  # noqa: F401

TWO = ("arastirmaci_dost", "hikaye_anlaticisi")


def cost(sessions):
    return round(sum(s["maliyet_usd"] or 0 for s in sessions), 4)


def test_a_version_counts_its_tone_and_the_plan_is_counted_once(app):
    add_video(app)
    view = start_text(app, tones=TWO)
    sessions = view["oturumlar"]
    plan = [s for s in sessions if s["tone"] is None]
    assert {s["step"] for s in plan} == {"metin_plan", "metin_plan_elestiri"} and cost(plan) > 0
    for version in view["surumler"]:
        own = [s for s in sessions if s["tone"] == version["tone_file"]]
        assert version["cost_usd"] == cost(own) and version["cost_usd"] > 0
    usage = view["kullanim"]
    assert usage["plan"]["oturum"] == len(plan) and usage["plan"]["maliyet_usd"] == cost(plan)
    assert set(usage["tonlar"]) == set(TWO) and usage["oturum"] == len(sessions)
    assert round(usage["plan"]["maliyet_usd"] + sum(t["maliyet_usd"] for t in usage["tonlar"].values()), 4) == usage["maliyet_usd"]
    compare = app.get(f"/api/videos/v1/metin/karsilastirma?calisma={view['id']}").json()
    assert len(compare["planlar"]) == 1 and compare["planlar"][0]["kullanim"]["oturum"] == len(plan)
    assert compare["planlar"][0]["surumler"] == [v["number"] for v in view["surumler"]]
    assert {c["cost_usd"] for c in compare["sutunlar"]} == {v["cost_usd"] for v in view["surumler"]}

    added = app.post(f"/api/metin/calismalar/{view['id']}/ton", json={"ton": "pratik_planlayici"})
    assert added.status_code == 201
    again = wait_run(app, view["id"])
    third = next(v for v in again["surumler"] if v["tone_file"] == "pratik_planlayici")
    own = [s for s in again["oturumlar"] if s["tone"] == "pratik_planlayici"]
    assert third["cost_usd"] == cost(own)                                  # the plan made before is not counted again
    assert again["kullanim"]["plan"]["oturum"] == len(plan)


def test_the_chosen_run_says_secildi_in_the_list(app):
    add_video(app)
    view = start_text(app, tones=TWO)
    assert app.get("/api/videos/v1/metin").json()["calismalar"][0]["secildi"] is None
    second = next(v for v in view["surumler"] if v["tone_file"] == "hikaye_anlaticisi")
    assert app.post(f"/api/metin/surumler/{second['id']}/sec", json={}).status_code == 200
    runs = app.get("/api/videos/v1/metin").json()["calismalar"]
    assert runs[0]["secildi"] == "Hikâye anlatıcısı"
