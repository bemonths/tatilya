"""GÖREV-19: the two waste switches in every Claude child's environment (also when the app runs inside a Claude Code session), and the
estimate's side-call share falling to zero once the one-call records have no side call."""
from tests.test_claude_steps import FAKE, app, calls, finished, start  # noqa: F401


def test_every_claude_call_gets_the_title_and_caching_switches_even_inside_a_claude_code_session(app, monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")                                      # the app started from a Claude Code session …
    monkeypatch.setenv("CLAUDE_CODE_DISABLE_TERMINAL_TITLE", "0")              # … whose own value is not the program's
    monkeypatch.delenv("DISABLE_PROMPT_CACHING", raising=False)
    view = start(app)
    env = calls(app, view)[0]["env"]
    assert env["CLAUDE_CODE_DISABLE_TERMINAL_TITLE"] == "1" and env["DISABLE_PROMPT_CACHING"] == "1"
    assert env["CLAUDECODE"] is None and env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] == "1"


def test_side_call_share_falls_to_zero_when_the_one_call_records_have_none(app, monkeypatch):
    monkeypatch.setenv("FAKE_CLAUDE_TOKENS", "100000,4000")
    monkeypatch.setenv("FAKE_CLAUDE_SIDE", "claude-haiku-5-5,95000")
    start(app)                                                                 # one older call with Claude Code's side call
    with_side = app.post("/api/claude/title-runs/tahmin", json={"bolge": "30A geneli"}).json()["satirlar"][0]
    assert with_side["yan"] > 0
    monkeypatch.delenv("FAKE_CLAUDE_SIDE")
    for _ in range(2):                                                         # the switch on: no side call any more
        view = start(app)
        assert view["metrics"].get("side_tokens") is None
    after = app.post("/api/claude/title-runs/tahmin", json={"bolge": "30A geneli"}).json()["satirlar"][0]
    assert after["yan"] == 0 and "yan çağrısı" not in after["dayanak"]          # the median of [0.95, 0, 0]
    assert after["toplam"] == after["okunan"] + after["yazilan"]               # read = the task text alone (earlier proposals made it longer)
    assert with_side["dayanak"].count("yan çağrısı için okunanın %") == 1
