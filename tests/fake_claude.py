"""Fake Claude Code for the tests (GÖREV-13; modelled on The Housing Atlas Stüdyo's `tests/fake_claude.py`): the tests never call Claude.

Settings' `claude_path` is this file; the runner runs a path ending in `.py` with the app's Python. It reads the options of `claude -p` (an
unknown option prints "error: unknown option" and exits 1), the task text from standard input and the combined instructions file; `--version`
prints "0.0.0 (Sahte Claude Code)" (or FAKE_CLAUDE_VERSION). It writes `stream-json` events like Claude Code (`system/init`, `assistant` blocks
with thinking and tool calls, `user` tool results, a final `result` envelope) and, for the title step (`Adım: baslik`), `baslik.json` built from
the run folder's files: the summaries' K identifiers, the schema's lists (families and regions, from the instructions), `secim.md`, and
`onceki_oneriler.md` (titles are never repeated unless the scenario asks).

Every call is appended to `.fake_claude_calls.jsonl` in the working folder (argv, prompt, model, effort, tools, rules, turn limit, the isolation
environment variables, the instructions file's head).

FAKE_CLAUDE_SCENARIO: ok (default) · schema_error (a candidate without `kapak_fikri`) · invalid_json · missing_file · bad_id (candidate 1's hook
cites K9999) · no_evidence_section (candidate 1's 2nd section has no evidence) · other_region (candidate 2 in another neighborhood) ·
wrong_family (candidate 2 of another family) · repeat_title (candidate 1 repeats the first earlier title) · denied (ok plus a refused Bash call)
· max_turns · usage_limit · not_logged_in · version_too_old · slow (sleeps FAKE_CLAUDE_SLEEP seconds, default 30, then ok).
FAKE_CLAUDE_COUNT: number of candidates (default 8).
"""
import json
import os
import re
import sys
import time
import uuid
from pathlib import Path

FLAGS = {"-p", "--verbose", "--strict-mcp-config", "--disable-slash-commands"}
VALUED = {"--output-format", "--append-system-prompt-file", "--tools", "--permission-mode", "--max-turns", "--setting-sources", "--model",
          "--effort"}
MULTI = {"--allowedTools", "--disallowedTools"}


def parse(argv):
    options, index = {}, 0
    while index < len(argv):
        arg = argv[index]
        if arg in FLAGS:
            options[arg] = True
            index += 1
        elif arg in VALUED:
            options[arg] = argv[index + 1]
            index += 2
        elif arg in MULTI:
            values, index = [], index + 1
            while index < len(argv) and not argv[index].startswith("--"):
                values.append(argv[index])
                index += 1
            options[arg] = values
        else:
            sys.stderr.write(f"error: unknown option '{arg}'\n")
            sys.exit(1)
    return options


def emit(event):
    sys.stdout.write(json.dumps(event, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def schema_lists(system_text):
    found = re.search(r"```json\n(.*?)\n```", system_text, re.S)
    schema = json.loads(found.group(1)) if found else {}
    defs = schema.get("$defs", {})
    return defs.get("aile", {}).get("enum", []), defs.get("bolge", {}).get("enum", []), defs.get("kanit", {}).get("properties", {}).get(
        "dosya", {}).get("enum", [])


def summary_ids(path):
    if not path.is_file():
        return []
    return list(dict.fromkeys(re.findall(r"\bK\d{4}\b", path.read_text(encoding="utf-8"))))


def earlier_titles(path):
    if not path.is_file():
        return []
    return [line.split(" | ")[3] for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("| 20")]


def selection(cwd):
    text = (cwd / "secim.md").read_text(encoding="utf-8")
    region = re.search(r"- Bölge: (.+?) \(", text).group(1)
    region_id = re.search(r"mahalle kimliği: `([^`]+)`", text)
    family = re.search(r"- İçerik ailesi: (.+)", text).group(1).strip()
    return region, region_id.group(1) if region_id else None, family


def build(cwd, system_text, scenario, prompt):
    families, regions, files = schema_lists(system_text)
    region, region_id, family = selection(cwd)
    general = summary_ids(cwd / "veri_ozeti_30a.md")
    local = summary_ids(cwd / "veri_ozeti_mahalle.md")
    earlier = earlier_titles(cwd / "onceki_oneriler.md")
    count = int(os.environ.get("FAKE_CLAUDE_COUNT", "8"))
    chosen_families = [family] * count if family != "hepsi" else [families[i % max(1, min(5, len(families)))] for i in range(count)]
    taken = {t.casefold() for t in earlier}
    titles, number = [], 1
    while len(titles) < count:
        title = f"{region} question number {number} for a first visit"
        if title.casefold() not in taken:
            titles.append(title)
            taken.add(title.casefold())
        number += 1

    def evidence(position):
        if local and position % 2:
            return {"dosya": "veri_ozeti_mahalle.md", "kimlik": local[position % len(local)]}
        return {"dosya": "veri_ozeti_30a.md", "kimlik": general[position % len(general)]}

    candidates = []
    for index in range(count):
        template, params = ("mahalle-rehberi", {"mahalle": region_id}) if region_id else ("ilk-video", {})
        candidates.append({
            "baslik_en": titles[index], "baslik_tr": f"{region} için {index + 1}. soru", "bolge": region, "aile": chosen_families[index],
            "neden_onerildi": "Sahte Claude'un önerisi.", "izleyici_sorusu": "Burada tatil yapmak doğru mu?",
            "kanca": {"metin": "Kanca metni.", "kanitlar": [evidence(index)]},
            "icerik_plani": [{"bolum": f"Bölüm {n}", "ne_anlatir": "Anlatılan.", "kanitlar": [evidence(index + n)]} for n in range(1, 6)],
            "eksik_veri": [], "sablon": template, "parametreler": params, "yeni_sablon_gerekir": False, "kapak_fikri": "Kapak."})
    if count > 2 and not region_id:
        candidates[-1].update({"sablon": None, "parametreler": {}, "yeni_sablon_gerekir": True, "eksik_veri": ["Yeni şablon gerekir."]})
    if "Tür: düzeltme" in prompt and (cwd / "onceki_cikti.json").is_file():
        previous = json.loads((cwd / "onceki_cikti.json").read_text(encoding="utf-8"))
        if previous.get("adaylar"):
            candidates = previous["adaylar"]
            candidates[0] = {**candidates[0], "baslik_en": candidates[0]["baslik_en"] + " (revised)"}
    note = re.search(r"--- not başı ---\n(.*?)\n--- not sonu ---", prompt, re.S)
    data = {"surum": 1, "adim": "baslik", "notlar": [f"Düzeltme notu: {note.group(1)}"] if note else [], "adaylar": candidates}
    if scenario == "schema_error":
        del data["adaylar"][0]["kapak_fikri"]
    elif scenario == "bad_id":
        data["adaylar"][0]["kanca"]["kanitlar"] = [{"dosya": "veri_ozeti_30a.md", "kimlik": "K9999"}]
    elif scenario == "no_evidence_section":
        data["adaylar"][0]["icerik_plani"][1]["kanitlar"] = []
    elif scenario == "other_region":
        other = next(r for r in regions[1:] if r != region)
        data["adaylar"][1]["bolge"] = other
    elif scenario == "wrong_family":
        data["adaylar"][1]["aile"] = next(f for f in families if f != data["adaylar"][1]["aile"])
    elif scenario == "repeat_title" and earlier:
        data["adaylar"][0]["baslik_en"] = earlier[0].upper() + "!"
    return data


def main():
    sys.stdin.reconfigure(encoding="utf-8")      # the runner writes and reads UTF-8, as Claude Code does
    sys.stdout.reconfigure(encoding="utf-8")
    argv = sys.argv[1:]
    if "--version" in argv:
        print(os.environ.get("FAKE_CLAUDE_VERSION", "0.0.0 (Sahte Claude Code)"))
        return 0
    options = parse(argv)
    prompt = sys.stdin.read()
    cwd = Path.cwd()
    scenario = os.environ.get("FAKE_CLAUDE_SCENARIO", "ok")
    system_text = Path(options["--append-system-prompt-file"]).read_text(encoding="utf-8")
    with open(cwd / ".fake_claude_calls.jsonl", "a", encoding="utf-8") as handle:
        handle.write(json.dumps({"argv": argv, "prompt": prompt, "scenario": scenario, "model": options.get("--model"), "effort": options.get("--effort"),
                                 "tools": options.get("--tools"), "allowed": options.get("--allowedTools"), "max_turns": options.get("--max-turns"),
                                 "setting_sources": options.get("--setting-sources"), "system_prompt_head": system_text[:200],
                                 "env": {k: os.environ.get(k) for k in ("CLAUDE_CODE_DISABLE_AUTO_MEMORY", "ENABLE_CLAUDEAI_MCP_SERVERS",
                                                                          "DISABLE_AUTOUPDATER", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")},
                                 "api_key_set": bool(os.environ.get("ANTHROPIC_API_KEY"))}, ensure_ascii=False) + "\n")
    session = str(uuid.uuid4())
    emit({"type": "system", "subtype": "init", "session_id": session, "cwd": str(cwd), "model": options.get("--model") or "claude-fake",
          "claude_code_version": "0.0.0", "permissionMode": options.get("--permission-mode"), "tools": (options.get("--tools") or "").split(",")})
    if scenario == "slow":
        time.sleep(float(os.environ.get("FAKE_CLAUDE_SLEEP", "30")))
    if scenario in ("usage_limit", "not_logged_in", "version_too_old"):
        text = {"usage_limit": "You've hit your session limit · resets 3pm (Europe/Istanbul)",
                "not_logged_in": "Failed to authenticate. API Error: 401 OAuth access token is invalid.",
                "version_too_old": "Claude Code version is too old"}[scenario]
        if scenario == "version_too_old":
            emit({"type": "assistant", "message": {"id": "msg_err", "content": [{"type": "text", "text": text}]}, "error": "unknown",
                  "api_error": "claude_code_version_too_old", "is_api_error_message": True})
        emit({"type": "result", "subtype": "success", "is_error": True, "api_error_status": {"usage_limit": 429, "not_logged_in": 401}.get(scenario),
              "result": text, "session_id": session, "num_turns": 1, "duration_ms": 10,
              **({"api_error_code": "claude_code_version_too_old"} if scenario == "version_too_old" else {})})
        return 1
    usage = {"input_tokens": 1200, "cache_creation_input_tokens": 300, "cache_read_input_tokens": 5000, "output_tokens": 800}
    emit({"type": "assistant", "message": {"id": "msg_1", "content": [{"type": "thinking", "thinking": ""},
          {"type": "tool_use", "id": "toolu_1", "name": "Read", "input": {"file_path": str(cwd / "secim.md")}}], "usage": usage}})
    emit({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "toolu_1", "content": "..."}]}})
    if scenario == "denied":
        emit({"type": "assistant", "message": {"id": "msg_2", "content": [{"type": "tool_use", "id": "toolu_2", "name": "Bash",
              "input": {"command": "dir .."}}], "usage": usage}})
        emit({"type": "system", "subtype": "permission_denied", "tool_name": "Bash", "tool_use_id": "toolu_2",
              "message": "Permission to use Bash has been denied because Claude Code is running in don't ask mode."})
        emit({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "toolu_2", "content": "denied", "is_error": True}]}})
    if scenario == "max_turns":
        emit({"type": "result", "subtype": "error_max_turns", "is_error": True, "session_id": session, "num_turns": int(options["--max-turns"]) + 1,
              "errors": ["Reached maximum number of turns"]})
        return 1
    output = cwd / "baslik.json"
    if scenario == "invalid_json":
        output.write_text("{", encoding="utf-8")
    elif scenario != "missing_file":
        output.write_text(json.dumps(build(cwd, system_text, scenario, prompt), ensure_ascii=False, indent=1), encoding="utf-8")
    emit({"type": "assistant", "message": {"id": "msg_3", "content": [{"type": "tool_use", "id": "toolu_3", "name": "Write",
          "input": {"file_path": str(output), "content": "..."}}], "usage": usage}})
    emit({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "toolu_3", "content": "ok"}]}})
    emit({"type": "assistant", "message": {"id": "msg_4", "content": [{"type": "text", "text": "Sekiz aday yazdım."}], "usage": usage}})
    emit({"type": "result", "subtype": "success", "is_error": False, "result": "Sekiz aday yazdım.", "session_id": session, "num_turns": 4,
          "duration_ms": 1500, "duration_api_ms": 1200, "total_cost_usd": 0.0123, "usage": usage, "modelUsage": {},
          "permission_denials": [{"tool_name": "Bash", "tool_use_id": "toolu_2", "tool_input": {"command": "dir .."}}] if scenario == "denied" else []})
    return 0


if __name__ == "__main__":
    sys.exit(main())
