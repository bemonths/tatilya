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

GÖREV-14: after `system/init` a `rate_limit_event` like Claude Code's (`unifiedWindows.five_hour/seven_day`; FAKE_CLAUDE_USAGE "0.43,0.38"
sets the utilizations, "none" leaves the event out). A task without "Adım:" (the usage panel's "Yenile" call) is answered with one word.
FAKE_CLAUDE_NO_EFFORT: a model name that refuses `--effort` (the call ends with Claude Code's unsupported-effort error).
The evaluation step (`Adım: baslik_degerlendirme`) writes `baslik_degerlendirme.json`: the user's text verbatim from `kullanici_basligi.md`,
FAKE_CLAUDE_REVIEW_COUNT candidates (default 2; an "edited candidate" run gets the user's Turkish title as its Turkish title).
Scenarios: dolmuyor (the idea does not fill a video: no candidates, missing data written) · too_many (4 candidates) · changed_idea
(`kullanici_fikri` differs from what the user wrote) · no_missing (does not fill but no missing data).

GÖREV-15: the video text's seven steps (`Adım: metin_…`) are answered by `tests/fake_claude_text.py` (outputs with evidence marks; invalid
answers, transient failures, the usage limit and slow answers on request through FAKE_CLAUDE_TEXT and FAKE_CLAUDE_SCENARIO=slow).

GÖREV-18: the new way. A step's call must come without tools (`--tools ""`, no `--allowedTools`) and with `--max-turns 1`; otherwise the
fake ends with an error (so no test can pass with the old way). It opens no file of the run folder: the input files are read from the
task text's `<<<DOSYA name>>>` sections (standard input), and the output is the answer's text (one `assistant` text block and the
`result` envelope), never a file. Scenarios: invalid_json (the answer is "{") · missing_file / no_json (an answer without JSON) ·
prose (the JSON with a sentence before and after) · fenced (the JSON in a ```json fence) · truncated (the answer is cut: `stop_reason`
"max_tokens", half of the JSON) · truncated_once / invalid_once (only the first call of a run folder; the second is ok).
FAKE_CLAUDE_TITLE_BUSINESS="<name>": candidate 1's title names that business and its cover idea has a long big text (the marks of
GÖREV-18 Adım 6). FAKE_CLAUDE_SIDE="model,read" adds Claude Code's side call to `modelUsage` (as the real one-call run showed: Haiku reading the task text).
FAKE_CLAUDE_TOKENS="read,written" sets the answer's usage (default: read = the task text's and the instructions' characters ÷ 1.85 plus
4,500, written 800); the per-step override FAKE_CLAUDE_TOKENS_<STEP> (e.g. FAKE_CLAUDE_TOKENS_METIN_BOLUM) wins.
"""
import json
import os
import re
import sys
import time
import uuid
from pathlib import Path

import fake_claude_text  # noqa: E402  (GÖREV-15: the video text steps; this file runs as a script from tests/)

SECTION = re.compile(r"^<<<DOSYA (?P<name>[^>\n]+)>>>\n(?P<body>.*?)\n<<<DOSYA SONU (?P=name)>>>$", re.S | re.M)


class GivenFile:
    """One input file as the task text gives it (GÖREV-18: the fake reads nothing from the run folder)."""

    def __init__(self, files, name):
        self.files, self.name = files, name

    def is_file(self):
        return self.name in self.files

    def read_text(self, encoding=None):
        if self.name not in self.files:
            raise FileNotFoundError(self.name)
        return self.files[self.name]


class Given:
    def __init__(self, prompt):
        self.files = {m.group("name"): m.group("body") for m in SECTION.finditer(prompt)}

    def __truediv__(self, name):
        return GivenFile(self.files, name)

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
    return [line.split(" | ")[3].replace("\\|", "|") for line in path.read_text(encoding="utf-8").splitlines() if line.startswith("| 20")]


def selection(cwd):
    text = (cwd / "secim.md").read_text(encoding="utf-8")
    region = re.search(r"- Bölge: (.+?) \(", text).group(1)
    region_id = re.search(r"mahalle kimliği: `([^`]+)`", text)
    family = re.search(r"- İçerik ailesi: (.+)", text).group(1).strip()
    return region, region_id.group(1) if region_id else None, family


def suffixes(cwd):
    """The title suffixes the program wrote into secim.md (GÖREV-14); FAKE_CLAUDE_NO_SUFFIX leaves them off."""
    text = (cwd / "secim.md").read_text(encoding="utf-8")
    found = {lang: re.search(rf'- {label} başlık eki: "([^"]*)"', text) for lang, label in (("en", "İngilizce"), ("tr", "Türkçe"))}
    if os.environ.get("FAKE_CLAUDE_NO_SUFFIX"):
        return {"en": "", "tr": ""}
    return {lang: match.group(1) if match else "" for lang, match in found.items()}


def build(cwd, system_text, scenario, prompt):
    families, regions, files = schema_lists(system_text)
    region, region_id, family = selection(cwd)
    suffix = suffixes(cwd)
    general = summary_ids(cwd / "veri_ozeti_30a.md")
    local = summary_ids(cwd / "veri_ozeti_mahalle.md")
    earlier = earlier_titles(cwd / "onceki_oneriler.md")
    count = int(os.environ.get("FAKE_CLAUDE_COUNT", "8"))
    chosen_families = [family] * count if family != "hepsi" else [families[i % max(1, min(5, len(families)))] for i in range(count)]
    taken = {t.casefold() for t in earlier}
    titles, number = [], 1
    while len(titles) < count:
        title = f"{region} question number {number} for a first visit{suffix['en']}"
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
            "baslik_en": titles[index], "baslik_tr": f"{region} için {index + 1}. soru{suffix['tr']}", "bolge": region, "aile": chosen_families[index],
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
    business = os.environ.get("FAKE_CLAUDE_TITLE_BUSINESS")
    if business and candidates:
        candidates[0]["baslik_en"] = f"Is {business} Worth the Drive? A Long Look at What {region} Offers{suffix['en']}"[:100]
        candidates[0]["kapak_fikri"] = f"{business} vitrini; büyük yazı 'IS IT WORTH THE DRIVE?'"
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
        base = earlier[0][:-len(suffix["en"])] if suffix["en"] and earlier[0].endswith(suffix["en"]) else earlier[0]
        data["adaylar"][0]["baslik_en"] = base.upper() + "!" + suffix["en"]
    return data


def user_title(cwd):
    text = (cwd / "kullanici_basligi.md").read_text(encoding="utf-8")
    return re.search(r"--- başlık başı ---\n(.*?)\n--- başlık sonu ---", text, re.S).group(1)


def build_review(cwd, system_text, scenario, prompt):
    idea = user_title(cwd)
    count = 4 if scenario == "too_many" else int(os.environ.get("FAKE_CLAUDE_REVIEW_COUNT", "2"))
    os.environ["FAKE_CLAUDE_COUNT"] = str(max(count, 1))
    candidates = build(cwd, system_text, "ok", prompt)["adaylar"][:count]
    for item in candidates:
        if item.get("sablon") is None:
            item.update({"sablon": "ilk-video", "parametreler": {}, "yeni_sablon_gerekir": False, "eksik_veri": []})
    selection_text = (cwd / "secim.md").read_text(encoding="utf-8")
    if "Bu aday düzenlendi" in selection_text and candidates:
        candidates[0]["baslik_tr"] = idea
        candidates[0]["baslik_en"] = candidates[0]["baslik_en"].replace("question number", "edited question")
    fills = scenario not in ("dolmuyor", "no_missing")
    data = {"surum": 1, "adim": "baslik_degerlendirme", "notlar": ["Sahte değerlendirme."],
            "kullanici_fikri": idea + (" (değişti)" if scenario == "changed_idea" else ""),
            "doluluk": {"dolar_mi": fills, "aciklama": "Veri bu fikri taşıyor." if fills else "Bu fikre özgü kural verisi yok.",
                        "eksik_veri": [] if fills or scenario == "no_missing" else ["Mahalleye özgü köpek kuralı kaydı yok."]},
            "sorunlar": ["Başlık eki yok."] if " | " not in idea else [],
            "adaylar": candidates if fills else []}
    return data


def text_session(step, cwd, prompt, scenario, session):
    """GÖREV-15: a video text step (`tests/fake_claude_text.py`): its output, or the trouble FAKE_CLAUDE_TEXT asks for."""
    start = time.time()
    if scenario == "slow":
        time.sleep(float(os.environ.get("FAKE_CLAUDE_SLEEP", "30")))
    trouble = fake_claude_text.trouble(step, prompt)
    if trouble == "transient":
        emit({"type": "result", "subtype": "success", "is_error": True, "api_error_status": 529, "result": "API Error: 529 Overloaded",
              "session_id": session, "num_turns": 1, "duration_ms": 10})
        fake_claude_text.log_session(step, start, time.time())
        return 1
    if trouble == "limit":
        reset = int(time.time() + float(os.environ.get("FAKE_CLAUDE_LIMIT_RESET", "60")))
        emit({"type": "rate_limit_event", "rate_limit_info": {"status": "rejected", "resetsAt": reset, "rateLimitType": "five_hour",
              "unifiedWindows": {"five_hour": {"utilization": 1.0, "resetsAt": reset}, "seven_day": {"utilization": 0.5, "resetsAt": reset + 86400}}},
              "session_id": session})
        emit({"type": "result", "subtype": "success", "is_error": True, "api_error_status": 429, "session_id": session, "num_turns": 1,
              "duration_ms": 10, "result": "You've hit your session limit · resets 3pm (Europe/Istanbul)"})
        fake_claude_text.log_session(step, start, time.time())
        return 1
    data = fake_claude_text.output(step, cwd, prompt)
    answer(json.dumps(data, ensure_ascii=False, indent=1), session, prompt, step=step, scenario=scenario)
    fake_claude_text.log_session(step, start, time.time())
    return 0


SYSTEM_CHARS = [0]


def usage_of(prompt, step=None):
    """The answer's usage: FAKE_CLAUDE_TOKENS(_<STEP>) "read,written", else the task text's size (GÖREV-18)."""
    wanted = os.environ.get(f"FAKE_CLAUDE_TOKENS_{(step or '').upper()}") or os.environ.get("FAKE_CLAUDE_TOKENS")
    if wanted:
        read, written = (int(v) for v in wanted.split(","))
    else:
        read, written = int((len(prompt) + SYSTEM_CHARS[0]) / 1.85) + 4500, 800
    return {"input_tokens": 10, "cache_creation_input_tokens": max(0, read - 10), "cache_read_input_tokens": 0, "output_tokens": written}


def first_call(prompt):
    """True for the first call of a run (its task text has no "DÖNÜŞ SEBEBİ"): the *_once scenarios act on it only."""
    return "DÖNÜŞ SEBEBİ" not in prompt


def answer(text, session, prompt, *, step=None, scenario="ok"):
    """One answer of a one-turn call: a thinking block and a text block, then the envelope (GÖREV-18). The scenarios change the text."""
    stop = "end_turn"
    once = first_call(prompt)
    if scenario == "invalid_json" or (scenario == "invalid_once" and once):
        text = "{"
    elif scenario in ("missing_file", "no_json"):
        text = "Bitti; çıktıyı yazdım."
    elif scenario == "prose":
        text = "İşte cevabım:\n" + text + "\nUmarım işe yarar."
    elif scenario == "fenced":
        text = "```json\n" + text + "\n```"
    elif scenario == "truncated" or (scenario == "truncated_once" and once):
        text, stop = text[: len(text) // 2], "max_tokens"
    usage = usage_of(prompt, step)
    emit({"type": "assistant", "message": {"id": "msg_1", "content": [{"type": "thinking", "thinking": ""}, {"type": "text", "text": text}],
          "usage": usage}})
    models = {"claude-fake": {"inputTokens": usage["input_tokens"], "cacheCreationInputTokens": usage["cache_creation_input_tokens"],
                              "cacheReadInputTokens": 0, "outputTokens": usage["output_tokens"], "maxOutputTokens": 128000}}
    side = os.environ.get("FAKE_CLAUDE_SIDE")
    if side:
        name, read = side.split(",")
        models[name] = {"inputTokens": int(read), "cacheCreationInputTokens": 0, "cacheReadInputTokens": 0, "outputTokens": 24}
    emit({"type": "result", "subtype": "success", "is_error": False, "result": text, "session_id": session, "num_turns": 1,
          "stop_reason": stop, "duration_ms": 900, "duration_api_ms": 700, "total_cost_usd": 0.0071, "usage": usage,
          "modelUsage": models, "permission_denials": []})


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
    SYSTEM_CHARS[0] = len(system_text)
    with open(cwd / ".fake_claude_calls.jsonl", "a", encoding="utf-8") as handle:
        handle.write(json.dumps({"argv": argv, "prompt": prompt, "scenario": scenario, "model": options.get("--model"), "effort": options.get("--effort"),
                                 "tools": options.get("--tools"), "allowed": options.get("--allowedTools"), "max_turns": options.get("--max-turns"),
                                 "setting_sources": options.get("--setting-sources"), "system_prompt_head": system_text[:200],
                                 "env": {k: os.environ.get(k) for k in ("CLAUDE_CODE_DISABLE_AUTO_MEMORY", "ENABLE_CLAUDEAI_MCP_SERVERS",
                                                                          "DISABLE_AUTOUPDATER", "CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT",
                                                                          "CLAUDE_CODE_DISABLE_TERMINAL_TITLE", "DISABLE_PROMPT_CACHING")},
                                 "api_key_set": bool(os.environ.get("ANTHROPIC_API_KEY"))}, ensure_ascii=False) + "\n")
    session = str(uuid.uuid4())
    emit({"type": "system", "subtype": "init", "session_id": session, "cwd": str(cwd), "model": options.get("--model") or "claude-fake",
          "claude_code_version": "0.0.0", "permissionMode": options.get("--permission-mode"), "tools": (options.get("--tools") or "").split(",")})
    refuses = os.environ.get("FAKE_CLAUDE_NO_EFFORT")
    if refuses and options.get("--model") == refuses and options.get("--effort"):
        emit({"type": "result", "subtype": "success", "is_error": True, "result": "API Error: 400 effort_requires_thinking: effort is not "
              "supported for this model", "session_id": session, "num_turns": 1, "duration_ms": 5, "api_error_code": "effort_requires_thinking"})
        return 1
    measured = os.environ.get("FAKE_CLAUDE_USAGE", "0.43,0.38")
    if measured != "none":
        five, week = (float(v) for v in measured.split(","))
        now = int(time.time())
        emit({"type": "rate_limit_event", "rate_limit_info": {"status": "allowed", "resetsAt": now + 3600, "rateLimitType": "five_hour",
              "unifiedWindows": {"five_hour": {"utilization": five, "resetsAt": now + 3600},
                                 "seven_day": {"utilization": week, "resetsAt": now + 4 * 86400}}}, "session_id": session})
    if "Adım:" not in prompt:
        emit({"type": "assistant", "message": {"id": "msg_1", "content": [{"type": "text", "text": "tamam"}],
              "usage": {"input_tokens": 20, "output_tokens": 2}}})
        emit({"type": "result", "subtype": "success", "is_error": False, "result": "tamam", "session_id": session, "num_turns": 1,
              "duration_ms": 300, "total_cost_usd": 0.0004, "usage": {"input_tokens": 20, "output_tokens": 2}})
        return 0
    if options.get("--tools") not in ("", None) or options.get("--allowedTools") or options.get("--max-turns") != "1":
        text = (f"Sahte Claude: GÖREV-18'den sonra bir adım araçsız ve tek turlu çağrılır (gelen: --tools {options.get('--tools')!r}, "
                f"--allowedTools {options.get('--allowedTools')!r}, --max-turns {options.get('--max-turns')!r}).")
        emit({"type": "result", "subtype": "success", "is_error": True, "result": text, "session_id": session, "num_turns": 1, "duration_ms": 5})
        return 1
    given = Given(prompt)
    text_step = fake_claude_text.step_of(prompt)
    if text_step:
        return text_session(text_step, given, prompt, scenario, session)
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
    if scenario == "max_turns":
        emit({"type": "result", "subtype": "error_max_turns", "is_error": True, "session_id": session, "num_turns": 2,
              "errors": ["Reached maximum number of turns"]})
        return 1
    review = "Adım: baslik_degerlendirme" in prompt
    if scenario in ("invalid_json", "missing_file", "no_json"):
        text = "{}"                                          # the answer is replaced by the scenario anyway
    else:
        data = build_review(given, system_text, scenario, prompt) if review else build(given, system_text, scenario, prompt)
        text = json.dumps(data, ensure_ascii=False, indent=1)
    answer(text, session, prompt, step="baslik_degerlendirme" if review else "baslik", scenario=scenario)
    return 0


if __name__ == "__main__":
    sys.exit(main())
