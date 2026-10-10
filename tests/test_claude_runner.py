"""GÖREV-13 Claude runner and settings (taken over from The Housing Atlas Stüdyo): command, isolation, program lookup, failure messages,
stream lines, instruction hashes; settings defaults, inheritance, validation and storage. No real Claude is called."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

from studio.ai import claude_info, runner, settings

FAKE = Path(__file__).with_name("fake_claude.py")


def invocation(tmp_path, **changes):
    values = dict(cwd=tmp_path, prompt="Adım: baslik\n", system_prompt_file=tmp_path / "talimat.md", tools=("Read", "Glob", "Grep", "Write", "Edit"),
                  allowed=("Read(./**)", "Write(./baslik.json)", "Edit(./baslik.json)"), max_turns=30, model="claude-opus-5-5", effort="high")
    values.update(changes)
    return runner.Invocation(**values)


def test_command_has_the_isolation_flags_tools_rules_model_and_effort(tmp_path):
    args = runner.build_args(["claude"], invocation(tmp_path))
    assert args[:5] == ["claude", "-p", "--output-format", "stream-json", "--verbose"]
    assert args[args.index("--append-system-prompt-file") + 1] == str(tmp_path / "talimat.md")
    assert args[args.index("--tools") + 1] == "Read,Glob,Grep,Write,Edit"
    rules = args[args.index("--allowedTools") + 1:args.index("--permission-mode")]
    assert rules == ["Read(./**)", "Write(./baslik.json)", "Edit(./baslik.json)"]          # Write passes only with the Edit rule
    assert args[args.index("--permission-mode") + 1] == "dontAsk" and args[args.index("--max-turns") + 1] == "30"
    assert args[args.index("--setting-sources") + 1] == "" and "--strict-mcp-config" in args and "--disable-slash-commands" in args
    assert args[-4:] == ["--model", "claude-opus-5-5", "--effort", "high"]
    plain = runner.build_args(["claude"], invocation(tmp_path, model="", effort="", allowed=()))
    assert "--model" not in plain and "--effort" not in plain and "--allowedTools" not in plain   # "" is Claude Code's own choice


def test_environment_isolates_and_drops_a_parent_claude_session():
    env = runner.build_env({"PATH": "x", "CLAUDECODE": "1", "CLAUDE_CODE_ENTRYPOINT": "cli", "CLAUDE_CODE_GIT_BASH_PATH": "bash",
                            "CLAUDE_CODE_OAUTH_TOKEN": "t", "ANTHROPIC_BASE_URL": "u", "ANTHROPIC_API_KEY": "k"})
    assert env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] == "1" and env["ENABLE_CLAUDEAI_MCP_SERVERS"] == "0" and env["DISABLE_AUTOUPDATER"] == "1"
    assert "CLAUDECODE" not in env and "CLAUDE_CODE_ENTRYPOINT" not in env and "ANTHROPIC_BASE_URL" not in env
    assert env["CLAUDE_CODE_GIT_BASH_PATH"] == "bash" and env["CLAUDE_CODE_OAUTH_TOKEN"] == "t" and env["ANTHROPIC_API_KEY"] == "k"
    outside = runner.build_env({"PATH": "x", "CLAUDE_CODE_ENTRYPOINT": "cli"})          # not inside a session: nothing is removed
    assert outside["CLAUDE_CODE_ENTRYPOINT"] == "cli"


def test_program_lookup_resolves_the_npm_shim_and_runs_python_scripts(tmp_path, monkeypatch):
    assert runner.resolve_command(FAKE) == [sys.executable, str(FAKE)]
    exe = tmp_path / "node_modules" / "@anthropic-ai" / "claude-code" / "bin" / "claude.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"")
    shim = tmp_path / "claude.cmd"
    shim.write_text('@ECHO off\r\n"%dp0%\\node_modules\\@anthropic-ai\\claude-code\\bin\\claude.exe" %*\r\n', encoding="utf-8")
    assert runner.resolve_command(shim) == [str(exe)]
    broken = tmp_path / "other.cmd"
    broken.write_text('"%dp0%\\missing\\claude.exe" %*', encoding="utf-8")
    with pytest.raises(runner.ClaudeRunnerError) as found:
        runner.resolve_command(broken)
    assert found.value.failure.kind == runner.NOT_FOUND
    monkeypatch.setattr(claude_info, "find_claude", lambda configured="", env=None: None)
    with pytest.raises(runner.ClaudeRunnerError, match="Claude Code bulunamadı"):
        runner.find_command("")


def test_version_is_read_and_the_api_key_is_noticed(monkeypatch):
    assert claude_info.read_version(FAKE) == "0.0.0"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert claude_info.info(str(FAKE))["api_key_warning"].startswith("ANTHROPIC_API_KEY ortam değişkeni tanımlı")
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    assert claude_info.info(str(FAKE))["api_key_warning"] is None


@pytest.mark.parametrize("envelope, stderr, kind, words", [
    ({"subtype": "success", "is_error": False}, "", None, None),
    ({"subtype": "error_max_turns", "num_turns": 31}, "", runner.MAX_TURNS, "tur sınırına ulaştı (30 tur)"),
    ({"subtype": "success", "is_error": True, "api_error_status": 429, "result": "You've hit your session limit · resets 3pm (Europe/Istanbul)"}, "",
     runner.USAGE_LIMIT, "15:00 (Europe/Istanbul) sıfırlanıyor"),
    ({"subtype": "success", "is_error": True, "api_error_status": 401, "result": "OAuth access token is invalid"}, "", runner.NOT_LOGGED_IN, "/login"),
    ({"subtype": "success", "is_error": True, "result": "x", "api_error_code": "claude_code_version_too_old"}, "", runner.VERSION_TOO_OLD, "claude update"),
    (None, "error: unknown option '--effort'", runner.VERSION_TOO_OLD, "--effort"),
    ({"subtype": "success", "is_error": True, "result": "There's an issue with the selected model"}, "", runner.UNSUPPORTED, "başka bir model"),
])
def test_failures_have_turkish_messages(envelope, stderr, kind, words):
    failure = runner.classify(1, envelope, stderr, max_turns=30, model="claude-opus-5-5", effort="high")
    assert (failure.kind if failure else None) == kind
    if words:
        assert words in failure.message


def test_stream_lines_are_turkish(tmp_path):
    parser = runner.StreamParser(tmp_path, max_turns=30, model="claude-opus-5-5", version="2.1.284")
    lines = []
    for at, event in enumerate([
            {"type": "system", "subtype": "init", "session_id": "s", "model": "claude-opus-5-5", "claude_code_version": "2.1.284"},
            {"type": "assistant", "message": {"id": "m1", "content": [{"type": "thinking", "thinking": ""},
                                                                    {"type": "tool_use", "id": "t1", "name": "Read", "input": {"file_path": str(tmp_path / "secim.md")}}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "content": "x"}]}},
            {"type": "assistant", "message": {"id": "m2", "content": [{"type": "tool_use", "id": "t2", "name": "Bash", "input": {"command": "dir .."}}]}},
            {"type": "system", "subtype": "permission_denied", "tool_name": "Bash", "tool_use_id": "t2", "message": "denied"},
            {"type": "assistant", "message": {"id": "m3", "content": [{"type": "tool_use", "id": "t3", "name": "Write",
                                                                       "input": {"file_path": str(tmp_path / "baslik.json")}}]}}]):
        lines += [text for text, _ in parser.feed(json.dumps(event), float(at * 5))]
    assert lines == ["Tur 1/30 · Düşünüyor (5 sn)", "Tur 1/30 · Okuyor: secim.md", "Tur 2/30 · Komut: dir ..", "Tur 2/30 · Reddedildi: komut dir ..",
                     "Tur 3/30 · Yazıyor: baslik.json"]
    assert parser.turns == 3 and parser.kinds == {"okuma": 1, "yazma": 1, "web": 0, "diger": 1} and parser.denied == ["komut dir .."]


def test_a_run_streams_measures_and_stops_on_timeout(tmp_path, monkeypatch):
    (tmp_path / "talimat.md").write_text("talimat", encoding="utf-8")
    (tmp_path / "secim.md").write_text("- Bölge: 30A geneli (x)\n- İçerik ailesi: hepsi\n", encoding="utf-8")
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "missing_file")
    seen = []
    result = runner.run(invocation(tmp_path), runner.resolve_command(FAKE), stream_path=tmp_path / "akis.jsonl", on_log=lambda t, l: seen.append(t))
    assert result.ok and result.turns == 3 and result.session_id and result.metrics()["tokens"]["output"] == 800
    assert result.metrics()["cost_usd"] == 0.0123 and seen[0].startswith("Claude Code 0.0.0 · model: Opus 5.5 (claude-opus-5-5) · efor: Yüksek")
    stream = [json.loads(line) for line in (tmp_path / "akis.jsonl").read_text(encoding="utf-8").splitlines()]
    assert stream[0]["type"] == "studio_run" and stream[-1]["type"] == "studio_run_end" and any(e.get("type") == "result" for e in stream)
    assert "maliyet karşılığı 0,01 $" in runner.summary_line(result)
    monkeypatch.setenv("FAKE_CLAUDE_SCENARIO", "slow")
    monkeypatch.setenv("FAKE_CLAUDE_SLEEP", "30")
    slow = runner.run(invocation(tmp_path), runner.resolve_command(FAKE), timeout=1.5)
    assert slow.failure.kind == runner.TIMEOUT and "zaman aşımı" in slow.failure.message and slow.elapsed_s < 20
    assert runner.timeout_for(30) == 45 * 60 and runner.timeout_for(100) == 100 * 90


def test_instruction_hashes_are_sha256_of_the_files(tmp_path):
    path = tmp_path / "ortak.md"
    path.write_text("talimat", encoding="utf-8")
    found = runner.instruction_hashes([path])
    assert found["files"] == [{"path": "ortak.md", "sha256": hashlib.sha256(b"talimat").hexdigest()}]


# --- Settings ------------------------------------------------------------------------------------------------------------------

def test_settings_defaults_inheritance_validation_and_storage(tmp_path):
    values = settings.load(tmp_path)
    assert (values["claude_model_baslik"], values["claude_effort_baslik"], values["claude_max_turns_baslik"]) == ("claude-opus-5-5", "high", 30)
    assert settings.resolve_model_effort(values, "baslik") == ("claude-opus-5-5", "high")
    assert [v for v, _ in settings.MODEL_CHOICES] == ["", "claude-opus-5-5", "claude-fable-5-1", "claude-sonnet-5", "claude-haiku-4-5"]
    assert [v for v, _ in settings.EFFORT_CHOICES] == ["", "low", "medium", "high", "xhigh", "max"]
    saved = settings.save(tmp_path, {"claude_model": "claude-sonnet-5", "claude_effort": "", "claude_model_baslik": "inherit",
                                     "claude_effort_baslik": "inherit", "claude_max_turns_baslik": 12})
    assert settings.resolve_model_effort(saved, "baslik") == ("claude-sonnet-5", "") and settings.max_turns(saved, "baslik") == 12
    stored = json.loads((tmp_path / "ayarlar.json").read_text(encoding="utf-8"))
    assert stored["claude"]["claude_model"] == "claude-sonnet-5" and "key" not in json.dumps(stored).lower()
    for change, field in (({"claude_model": "inherit"}, "claude_model"), ({"claude_effort_baslik": "çok"}, "claude_effort_baslik"),
                          ({"claude_max_turns_baslik": 0}, "claude_max_turns_baslik"), ({"api_key": "x"}, "api_key")):
        with pytest.raises(settings.SettingsError) as found:
            settings.save(tmp_path, change)
        assert found.value.field == field
    assert settings.load(tmp_path)["claude_max_turns_baslik"] == 12                     # a refused change saves nothing
    (tmp_path / "ayarlar.json").write_text("{bozuk", encoding="utf-8")
    assert settings.load(tmp_path)["notes"] == ["Ayar dosyası okunamadı; varsayılan ayarlar kullanılıyor."]
