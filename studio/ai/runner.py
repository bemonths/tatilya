"""Claude Code runner (GÖREV-13), taken over from The Housing Atlas Stüdyo (`atlas/ai/runner.py`; its KARARLAR M5 and M5b record why).

Claude is not a coding agent here: the program calls it with its own instructions for one step and reads one JSON file it writes.

Command (Housing Atlas's): `claude -p --output-format stream-json --verbose --append-system-prompt-file <combined instructions> --tools <the step's
tools> [--allowedTools <rules…>] --permission-mode dontAsk --max-turns <n> --setting-sources "" --strict-mcp-config --disable-slash-commands
[--model <model>] [--effort <effort>]`. The task text goes to standard input; the working folder is the run's folder. `--allowedTools` is left
out when there is no rule (an empty option is an error in Claude Code); `--model` and `--effort` only when set ("" is Claude Code's own choice).

Program: `claude_info.find_claude`. npm's `claude.cmd` shim is resolved and the `claude.exe` inside it (older versions: `node cli.js`) runs
directly, without cmd.exe (its 8,191-character limit and quoting). A path ending in `.py` runs with the app's own Python (the tests' fake).

Isolation (verified by Housing Atlas with Claude Code 2.1.121): `--setting-sources ""` loads none of the user's, project's or local settings
(hooks, permissions, plugins, user skills, the user's and parent folders' CLAUDE.md files); managed settings always apply. `--strict-mcp-config`
(no `--mcp-config` given) loads no MCP server; `ENABLE_CLAUDEAI_MCP_SERVERS=0` turns off claude.ai connectors; `--disable-slash-commands` turns
off skills; `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` turns off auto memory; `DISABLE_AUTOUPDATER=1`: no self-update during a run. `--bare` is not
used: it accepts only an API key, so the subscription login would not work. If the app was started inside a Claude Code session (`CLAUDECODE`
set) that session's variables (`CLAUDE_CODE_*` except `CLAUDE_CODE_GIT_BASH_PATH` and `CLAUDE_CODE_OAUTH_TOKEN`, `CLAUDECODE`,
`ANTHROPIC_BASE_URL` …) do not pass to the child. `ANTHROPIC_API_KEY` passes (the user's choice; the screens warn that it bills the API).

Permissions (verified live by Housing Atlas): the `Write` tool is allowed only by an `Edit(./path)` rule; a lone `Write(./path)` rule is ignored
and the write is refused. The folders of the write rules are created before Claude runs.

Live stream (`--output-format stream-json --verbose`; event shapes as Housing Atlas recorded them from Claude Code 2.1.284): `system/init`
(session, model, version), one `assistant` event per content block (thinking, text, tool_use; an API error is an assistant event with `error` /
`api_error`), `system/permission_denied` then a `user` tool_result with `is_error`, `rate_limit_event`, `system/api_retry`, and the final `result`
envelope (`subtype`, `is_error`, `api_error_status`, `duration_ms`, `num_turns`, `session_id`, `total_cost_usd`, `usage`, `modelUsage`,
`permission_denials`). Every raw line goes to the run's stream file (JSONL, between the app's own `studio_run` and `studio_run_end` lines);
events become short Turkish lines for the job panel: "Tur 3/30 · Okuyor: veri_ozeti_30a.md", "Tur 4/30 · Yazıyor: baslik.json",
"Tur 4/30 · Reddedildi: …", "Tur 5/30 · Düşünüyor (12 sn)".

Turn: the only turn count shown is Claude's number of responses in the main session (each new `message.id`); `--max-turns` limits that. The
envelope's `num_turns` (tool calls + 1 in Housing Atlas's records) is kept as `cc_num_turns` only.

Measurement: elapsed and API time, thinking time, turns, tool calls by kind (okuma, yazma, web, diğer) and their time, tokens (input, cache
creation, cache read, output; from the envelope's `usage`, or summed from the stream when there is no envelope) and the cost equivalent.

Failures (Turkish message): usage limit (with the reset time; retryable), turn limit, not logged in, program not found, timeout, canceled, old
Claude Code version (`claude_code_version_too_old`, `cli_version_too_old`, an unknown `--effort` option), unsupported model or effort
(`model_not_found`, `effort_requires_thinking`; `claude update` is suggested), other (first line). On cancel and timeout the process tree is
closed. The version is read again before every run (no cache).

Changes from Housing Atlas (GÖREV-13): one Claude run at a time in the whole app (the service and the jobs table enforce it; Housing Atlas's
parallel slots are not taken over); no Bash tool, so the app's Python is not put on the child's PATH; instruction versions are SHA-256 hashes of
the files (`instruction_hashes`), not git blob hashes.
"""
import hashlib
import json
import logging
import os
import queue
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from . import claude_info
from .settings import effort_label, model_label

log = logging.getLogger(__name__)

REPO_DIR = Path(__file__).resolve().parents[2]
MIN_TIMEOUT = 45 * 60.0
SECONDS_PER_TURN = 90.0
POLL_INTERVAL = 0.2
TICK_INTERVAL = 5.0
KILL_WAIT = 15.0
VERSION_TIMEOUT = 10.0
MAX_RESULT_CHARS = 20_000
MAX_STDERR_CHARS = 4_000
MAX_DETAIL_CHARS = 160
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
PERMISSION_MODE = "dontAsk"
OUTPUT_ARGS = ("--output-format", "stream-json", "--verbose")
ISOLATION_ARGS = ("--setting-sources", "", "--strict-mcp-config", "--disable-slash-commands")
ISOLATION_ENV = {"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1", "ENABLE_CLAUDEAI_MCP_SERVERS": "0", "DISABLE_AUTOUPDATER": "1"}
SESSION_MARKER = "CLAUDECODE"
SESSION_KEEP = frozenset({"CLAUDE_CODE_GIT_BASH_PATH", "CLAUDE_CODE_OAUTH_TOKEN"})
SESSION_VARS = frozenset({"CLAUDECODE", "CLAUDE_AGENT_SDK_VERSION", "CLAUDE_PID", "CLAUDE_EFFORT", "CLAUDE_PREVIEW_CLASSIFIER_FLOOR",
                          "USE_LOCAL_OAUTH", "USE_STAGING_OAUTH", "MCP_CONNECTION_NONBLOCKING", "MCP_SERVER_CONNECTION_BATCH_SIZE",
                          "ANTHROPIC_BASE_URL"})

USAGE_LIMIT, MAX_TURNS, NOT_LOGGED_IN, NOT_FOUND = "usage_limit", "max_turns", "not_logged_in", "not_found"
TIMEOUT, CANCELED, VERSION_TOO_OLD, UNSUPPORTED, OTHER = "timeout", "canceled", "version_too_old", "unsupported", "other"

NOT_FOUND_MESSAGE = "Claude Code bulunamadı. Claude Code'u kurun ya da Ayarlar → Claude bölümünden claude.exe'nin yolunu yazın."
LOGIN_MESSAGE = ("Claude Code'da oturum açık değil ya da oturumun süresi dolmuş. Bir komut istemi açıp `claude` yazın, açılan ekranda /login "
                 "komutuyla Claude hesabınıza giriş yapın (ya da `claude auth login`); sonra adımı yeniden çalıştırın.")
API_KEY_LOGIN_MESSAGE = ("ANTHROPIC_API_KEY ortam değişkeni tanımlı ama Claude bu anahtarı kabul etmedi (geçersiz ya da süresi dolmuş). "
                         "Anahtarı düzeltin ya da değişkeni kaldırıp uygulamayı yeniden açın.")
CANCELED_MESSAGE = "İş iptal edildi; Claude durduruldu."
UPDATE_HINT = "Bir komut istemi açıp `claude update` yazın; güncelleme bitince adımı yeniden çalıştırın."
MONTHS_TR = ("", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık")
MONTHS_EN = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}

USAGE = re.compile(r"usage limit|you've hit your|you have hit your|out of extra usage|out of usage|rate limit|rate_limit", re.I)
EPOCH = re.compile(r"limit reached\|(\d{9,13})", re.I)
RESETS = re.compile(r"resets\s+(?:at\s+)?([^·•|\n]+)", re.I)
LOGIN = re.compile(r"not logged in|/login|invalid api key|oauth (?:access )?token|oauth token has expired|authentication_error|"
                   r"failed to authenticate|auth login|token revoked", re.I)
OVERLOADED = re.compile(r"overloaded", re.I)
VERSION_OLD = re.compile(r"claude_code_version_too_old|cli_version_too_old|version[_ ]too[_ ]old|below (?:the )?(?:required )?minimum(?: "
                         r"required)? version|requires? (?:a )?newer (?:version of )?claude code|please (?:update|upgrade) claude code|"
                         r"run [`'\"]?claude update", re.I)
UNKNOWN_EFFORT = re.compile(r"unknown option\s+'?--effort", re.I)
BAD_OPTION_VALUE = re.compile(r"option '--(effort|model)\b[^']*' argument '([^']*)' is invalid", re.I)
MODEL_UNAVAILABLE = re.compile(r"issue with the selected model|model_not_found|may not exist or you may not have access|is not available on "
                               r"your|not_found_error[^\n]{0,80}\bmodel\b", re.I)
EFFORT_UNSUPPORTED = re.compile(r"effort_requires_thinking|\beffort\b[^\n]{0,60}(?:not supported|unsupported|isn't supported|is not "
                                r"available)|(?:unsupported|invalid) effort", re.I)
DENIED = re.compile(r"has been denied|was denied|denied by (?:your )?(?:permission )?rule|don't ask mode", re.I)
SHIM_TOKEN = re.compile(r'"%~?dp0%?\\?([^"%]+)"', re.I)
SH_EXEC = re.compile(r'"\$basedir/([^"]+)"')
VERSION = re.compile(r"\d+\.\d+(?:\.\d+)?")
SECRET = re.compile(r"sk-ant-[A-Za-z0-9_\-]{8,}")
SCRIPT_SUFFIXES = (".js", ".cjs", ".mjs")
VERSION_CODES = frozenset({"claude_code_version_too_old", "cli_version_too_old"})
UNSUPPORTED_CODES = frozenset({"model_not_found", "effort_requires_thinking"})
DENIAL_KINDS = frozenset({"user-rejected", "permission-rule", "automode-blocked", "automode-unavailable", "automode-parsing-error"})


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def whole(value, digits=0):
    """Half up (the screen's rounding; Python's round() is banker's)."""
    return float(Decimal(str(value)).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP))


def mask(text):
    return SECRET.sub("sk-ant-…", text or "")


def duration_text(seconds):
    """"45 sn", "3 dk 5 sn", "1 sa 2 dk"."""
    total = max(0, int(whole(seconds)))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours} sa {minutes} dk"
    return f"{minutes} dk {secs} sn" if minutes else f"{secs} sn"


# ------------------------------------------------------------------------------------------------------------------- failures

@dataclass
class Failure:
    """Kind and Turkish message of a failed run; `detail` is the first line of Claude's own text, `reset` the usage limit's reset time."""
    kind: str
    message: str
    retryable: bool = False
    reset: str | None = None
    detail: str | None = None

    def to_dict(self):
        return {"kind": self.kind, "message": self.message, "retryable": self.retryable, "reset": self.reset, "detail": self.detail}


class ClaudeRunnerError(Exception):
    def __init__(self, failure):
        super().__init__(failure.message)
        self.failure = failure


def first_line(text, limit=300):
    for line in (text or "").splitlines():
        if line.strip():
            return line.strip()[:limit]
    return ""


def time24(match):
    hour, minute, half = int(match.group(1)), match.group(2) or "00", match.group(3).lower()
    if half == "pm" and hour != 12:
        hour += 12
    if half == "am" and hour == 12:
        hour = 0
    return f"{hour:02d}:{minute}"


def turkish_reset(text):
    """"3pm (Europe/Istanbul)" -> "15:00 (Europe/Istanbul)", "Oct 3, 2pm" -> "3 Ekim 14:00"."""
    text = re.sub(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", time24, text.strip(), flags=re.I)
    text = re.sub(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(\d{1,2}),?",
                  lambda m: f"{int(m.group(2))} {MONTHS_TR[MONTHS_EN[m.group(1).lower()[:3]]]}", text, flags=re.I)
    return text.strip().rstrip(".")


def epoch_text(value):
    text = str(int(value))
    moment = datetime.fromtimestamp(int(text) / (1000 if len(text) > 11 else 1)).astimezone()
    return f"{moment.day} {MONTHS_TR[moment.month]} {moment.year} {moment:%H:%M}"


def usage_limit_failure(text):
    reset = None
    found = EPOCH.search(text)
    if found:
        reset = epoch_text(found.group(1))
    elif RESETS.search(text):
        reset = turkish_reset(RESETS.search(text).group(1))
    message = (f"Claude kullanım sınırına ulaşıldı; sınır {reset} sıfırlanıyor, o zamandan sonra yeniden deneyin." if reset else
               "Claude kullanım sınırına ulaşıldı; bir süre sonra yeniden deneyin.")
    return Failure(USAGE_LIMIT, message, retryable=True, reset=reset, detail=first_line(text))


def version_too_old_failure(detail, *, version=None, option=None, value=None):
    """Old Claude Code: `claude update` is suggested. With `option` ("effort"/"model") the version does not know that option (or value)."""
    running = f"Claude Code'un sürümü{f' ({version})' if version else ''}"
    if option == "effort" and value is None:
        message = (f"{running} efor seçeneğini (--effort) tanımıyor; eski bir sürüm. {UPDATE_HINT} Güncelleyemiyorsanız Ayarlar → Claude'dan "
                   "eforu Otomatik yapın.")
    elif option:
        what = "efor" if option == "effort" else "model"
        message = (f"{running} '{value}' {what} değerini tanımıyor; eski bir sürüm. {UPDATE_HINT} Güncelleyemiyorsanız Ayarlar → Claude'dan "
                   f"başka bir {what} seçin.")
    else:
        message = (f"{running} bu çalışma için eski: seçilen model ya da ayar daha yeni bir Claude Code sürümü istiyor. {UPDATE_HINT}")
    return Failure(VERSION_TOO_OLD, message, detail=first_line(detail) or None)


def unsupported_failure(detail, *, model="", effort=""):
    message = (f"Seçilen model ya da efor bu Claude Code sürümünde ya da hesabınızda kullanılamıyor (model: {model or model_label('')}, efor: "
               f"{effort_label(effort)}). Önce bir komut istemi açıp `claude update` yazarak Claude Code'u güncelleyin; sorun sürerse Ayarlar → "
               "Claude'dan bu adım için başka bir model ya da efor seçin.")
    return Failure(UNSUPPORTED, message, detail=first_line(detail) or None)


def classify_text(text, status, *, api_key):
    if status == 429 or USAGE.search(text):
        return usage_limit_failure(text)
    if status in (401, 403) or LOGIN.search(text):
        use_key = api_key and re.search(r"api key", text, re.I)
        return Failure(NOT_LOGGED_IN, API_KEY_LOGIN_MESSAGE if use_key else LOGIN_MESSAGE, detail=first_line(text))
    if status == 529 or OVERLOADED.search(text):
        return Failure(OTHER, "Claude'un sunucuları şu anda yoğun; biraz sonra yeniden deneyin.", retryable=True, detail=first_line(text))
    return None


def classify_codes(codes, text, *, model, effort, version):
    if codes & VERSION_CODES:
        return version_too_old_failure(text or next(iter(codes & VERSION_CODES)), version=version)
    if codes & UNSUPPORTED_CODES:
        return unsupported_failure(text or next(iter(codes & UNSUPPORTED_CODES)), model=model, effort=effort)
    return None


def classify_version_text(text, *, model, effort, version):
    if VERSION_OLD.search(text):
        return version_too_old_failure(text, version=version)
    if MODEL_UNAVAILABLE.search(text) or EFFORT_UNSUPPORTED.search(text):
        return unsupported_failure(text, model=model, effort=effort)
    return None


def classify(returncode, envelope, stderr="", *, max_turns=0, api_key=False, model="", effort="", version=None, api_errors=()):
    """The failure from the result envelope (else from standard error); None when the run succeeded."""
    codes = {str(e.get(k)) for e in api_errors for k in ("error", "api_error", "api_error_code") if e.get(k)}
    error_text = "\n".join(str(e.get("text") or "") for e in api_errors if e.get("text"))
    if envelope is not None:
        subtype = envelope.get("subtype")
        if subtype == "error_max_turns":
            limit = f"{max_turns} tur" if max_turns else f"{envelope.get('num_turns')} tur"
            return Failure(MAX_TURNS, f"Claude tur sınırına ulaştı ({limit}) ve işi bitirmeden durdu. Ayarlar → Claude'dan bu adımın en fazla tur "
                                      "sayısını artırıp yeniden deneyin ya da \"Düzeltme iste\" ile yeni bir çalışma açın.",
                           retryable=True, detail=first_line("\n".join(map(str, envelope.get("errors") or []))))
        if subtype == "success" and not envelope.get("is_error"):
            return None
        errors = envelope.get("errors")
        text = str(envelope.get("result") or "") or "\n".join(str(e) for e in errors or [] if e)
        codes |= {str(envelope.get(k)) for k in ("api_error_code", "startup_failure_reason") if envelope.get(k)}
        found = (classify_codes(codes, text or error_text, model=model, effort=effort, version=version)
                 or classify_text(text, envelope.get("api_error_status"), api_key=api_key)
                 or classify_version_text(f"{text}\n{error_text}", model=model, effort=effort, version=version))
        if found is not None:
            return found
        detail = first_line(text) or first_line(error_text) or str(subtype or "")
        return Failure(OTHER, f"Claude hata verdi: {detail}" if detail else
                       f"Claude beklenmedik biçimde bitti (çıkış kodu {returncode}). Ayrıntı iş günlüğünde.", detail=detail or None)
    text = stderr or ""
    if UNKNOWN_EFFORT.search(text):
        return version_too_old_failure(text, version=version, option="effort")
    bad = BAD_OPTION_VALUE.search(text)
    if bad:
        return version_too_old_failure(text, version=version, option=bad.group(1).lower(), value=bad.group(2))
    found = (classify_codes(codes, error_text, model=model, effort=effort, version=version) or classify_text(text, None, api_key=api_key)
             or classify_version_text(f"{text}\n{error_text}", model=model, effort=effort, version=version))
    if found is not None:
        return found
    detail = first_line(text)
    if detail:
        return Failure(OTHER, f"Claude Code hata verdi (çıkış kodu {returncode}): {detail}", detail=detail)
    return Failure(OTHER, f"Claude Code sonuç vermeden bitti (çıkış kodu {returncode}). Ayrıntı iş günlüğünde.")


# ------------------------------------------------------------------------------------------------------------------- program

def shim_targets(text, folder):
    return [Path(os.path.normpath(folder / m.group(1).replace("\\", "/").lstrip("/"))) for m in SHIM_TOKEN.finditer(text)]


def from_targets(shim, targets, which):
    exes = [t for t in targets if t.suffix.lower() == ".exe" and t.name.lower() != "node.exe" and t.is_file()]
    if exes:
        return [str(exes[0])]
    scripts = [t for t in targets if t.suffix.lower() in SCRIPT_SUFFIXES and t.is_file()]
    if scripts:
        local = next((shim.parent / n for n in ("node.exe", "node") if (shim.parent / n).is_file()), None)
        node = str(local) if local else which("node")
        if node:
            return [node, str(scripts[0])]
    return None


def resolve_command(path, *, python=None, which=shutil.which):
    """The head of the command that runs Claude Code. `.py`: the app's Python + the script (tests). `.cmd`/`.bat` (npm shim): the `claude.exe`
    inside it or `node <cli.js>`. Extensionless or `.ps1` npm shim: the `.cmd` next to it or the program in the sh script. Otherwise the path."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".py":
        return [python or sys.executable, str(path)]
    if suffix in (".cmd", ".bat"):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            raise ClaudeRunnerError(Failure(NOT_FOUND, f"{NOT_FOUND_MESSAGE} ({path} okunamadı: {exc.strerror or type(exc).__name__})")) from exc
        found = from_targets(path, shim_targets(text, path.parent), which)
        if found is None:
            raise ClaudeRunnerError(Failure(NOT_FOUND, f"Claude Code'un npm kabuğu ({path.name}) çözülemedi: içinde çalıştırılacak claude.exe "
                                                       "bulunamadı. Ayarlar → Claude bölümünden claude.exe'nin yolunu yazın."))
        return found
    if sys.platform == "win32" and suffix in ("", ".ps1"):
        shim = path.with_name(path.stem + ".cmd")
        if shim.is_file():
            return resolve_command(shim, python=python, which=which)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        found = from_targets(path, [Path(os.path.normpath(path.parent / m.group(1))) for m in SH_EXEC.finditer(text)], which)
        if found is not None:
            return found
    return [str(path)]


def find_command(configured="", *, env=None):
    path = claude_info.find_claude(configured, env=env)
    if path is None:
        raise ClaudeRunnerError(Failure(NOT_FOUND, NOT_FOUND_MESSAGE))
    return path, resolve_command(path)


def read_version(command, *, run=subprocess.run, timeout=VERSION_TIMEOUT):
    """The version in `<command> --version`; None when it cannot be read. Read before every run (no cache)."""
    try:
        result = run([*command, "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
                     stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
    except (OSError, subprocess.SubprocessError) as exc:
        log.warning("Claude Code sürümü okunamadı (%s): %s", command[-1] if command else "?", exc)
        return None
    found = VERSION.search(result.stdout or "")
    return found.group(0) if found else None


# ------------------------------------------------------------------------------------------------------------------- command and environment

@dataclass(frozen=True)
class Invocation:
    """One Claude run: working folder, task text (standard input), combined instruction file, tools and permission rules, turn limit, model
    and effort ("" = Claude Code's own choice)."""
    cwd: Path
    prompt: str
    system_prompt_file: Path
    tools: tuple
    allowed: tuple
    max_turns: int
    model: str = ""
    effort: str = ""


def build_args(command, inv):
    args = [*command, "-p", *OUTPUT_ARGS, "--append-system-prompt-file", str(inv.system_prompt_file), "--tools", ",".join(inv.tools),
            *(("--allowedTools", *inv.allowed) if inv.allowed else ()), "--permission-mode", PERMISSION_MODE,
            "--max-turns", str(int(inv.max_turns)), *ISOLATION_ARGS]
    if inv.model:
        args += ["--model", inv.model]
    if inv.effort:
        args += ["--effort", inv.effort]
    return args


def env_key(env, name):
    """Windows environment names ignore case: the spelling already present."""
    return next((k for k in env if k.upper() == name.upper()), name)


def build_env(base=None):
    """The child's environment: the isolation variables; a parent Claude Code session's variables are removed."""
    env = dict(os.environ if base is None else base)
    if any(k.upper() == SESSION_MARKER and v for k, v in env.items()):
        for name in list(env):
            upper = name.upper()
            if upper in SESSION_KEEP:
                continue
            if upper in SESSION_VARS or upper.startswith("CLAUDE_CODE_"):
                env.pop(name)
    for name, value in ISOLATION_ENV.items():
        env[env_key(env, name)] = value
    return env


WRITE_RULE = re.compile(r"^(?:Write|Edit|MultiEdit|NotebookEdit)\((.+)\)$")


def output_dirs(inv):
    """Folders of the files in the write rules (`Edit(./baslik.json)`), inside the working folder only; created before Claude runs."""
    out = []
    for rule in inv.allowed:
        found = WRITE_RULE.match(str(rule).strip())
        if not found:
            continue
        rel = found.group(1).strip().replace("\\", "/")
        rel = rel[2:] if rel.startswith("./") else rel
        if not rel or rel.startswith(("/", "~")) or os.path.isabs(rel):
            continue
        parts = []
        for part in rel.split("/")[:-1]:
            if any(ch in part for ch in "*?[{"):
                break
            parts.append(part)
        if parts and ".." not in parts and "." not in parts:
            out.append(Path(inv.cwd, *parts))
    return list(dict.fromkeys(out))


def display_args(args):
    """The command for the log: program name and options (empty values as "")."""
    shown = [Path(args[0]).name if args else ""] + [a if a else '""' for a in args[1:]]
    return " ".join(f'"{a}"' if " " in a else a for a in shown)


def start_line(version, model, effort):
    """"Claude Code 2.1.284 · model: Opus 5.5 (claude-opus-5-5) · efor: Yüksek"."""
    label = model_label(model)
    shown = f"{label} ({model})" if model and label != model else label
    return f"Claude Code {version or '(sürüm okunamadı)'} · model: {shown} · efor: {effort_label(effort)}"


def timeout_for(max_turns):
    """45 minutes or turn limit × 90 s, the larger (Housing Atlas's rule; not a setting)."""
    return max(MIN_TIMEOUT, max_turns * SECONDS_PER_TURN)


# ------------------------------------------------------------------------------------------------------------------- live stream

def short_path(text, cwd):
    """A path for the log: relative to the run folder when inside it, else as it is (with /)."""
    raw = str(text or "").strip()
    if not raw:
        return "?"
    try:
        if not os.path.isabs(raw):
            return os.path.normpath(raw).replace("\\", "/")
        rel = os.path.relpath(raw, str(cwd))
    except ValueError:
        return raw.replace("\\", "/")
    if rel == os.pardir or rel.startswith(os.pardir + os.sep):
        return raw.replace("\\", "/")
    return rel.replace("\\", "/")


def clip(text, limit=MAX_DETAIL_CHARS):
    lines = [line.strip() for line in str(text or "").strip().splitlines() if line.strip()]
    first = (lines[0] + (" …" if len(lines) > 1 else "")) if lines else ""
    return first if len(first) <= limit else first[:limit - 1].rstrip() + "…"


TOOL_WORDS = {"Read": ("Okuyor", "okuma"), "Write": ("Yazıyor", "yazma"), "Edit": ("Düzenliyor", "düzenleme"),
              "MultiEdit": ("Düzenliyor", "düzenleme"), "NotebookEdit": ("Düzenliyor", "düzenleme"), "Glob": ("Dosya arıyor", "dosya arama"),
              "Grep": ("Metin arıyor", "metin arama"), "WebSearch": ("Web'de arıyor", "web araması"), "WebFetch": ("Sayfa okuyor", "sayfa okuma"),
              "Bash": ("Komut", "komut"), "Task": ("Alt görev", "alt görev"), "Agent": ("Alt görev", "alt görev")}
QUIET_TOOLS = frozenset({"TodoWrite", "TaskCreate", "TaskUpdate", "TaskList", "TaskGet"})
TOOL_KINDS = ("okuma", "yazma", "web", "diger")
TOOL_KIND_WORDS = {"okuma": "okuma", "yazma": "yazma", "web": "web", "diger": "diğer"}
KIND_OF_TOOL = {"Read": "okuma", "Glob": "okuma", "Grep": "okuma", "Write": "yazma", "Edit": "yazma", "MultiEdit": "yazma",
                "NotebookEdit": "yazma", "WebSearch": "web", "WebFetch": "web"}
THINKING = "düşünme"
TOKEN_FIELDS = (("input", "input_tokens"), ("cache_creation", "cache_creation_input_tokens"), ("cache_read", "cache_read_input_tokens"),
                ("output", "output_tokens"))
RATE_WINDOWS = {"five_hour": "5 saatlik", "seven_day": "haftalık", "seven_day_opus": "haftalık Opus", "seven_day_sonnet": "haftalık Sonnet",
                "overage": "ek kullanım"}
ANCHOR_SUBTYPES = frozenset({"init", "api_retry", "compact_boundary"})


def tool_action(name, data, cwd):
    """(verb, noun, detail): ("Okuyor", "okuma", "veri_ozeti_30a.md"). None for quiet tools (to-do lists)."""
    if name in QUIET_TOOLS:
        return None
    verb, noun = TOOL_WORDS.get(name, (name or "Araç", name or "araç"))
    if name in ("Read", "Write", "Edit", "MultiEdit", "NotebookEdit"):
        detail = short_path(data.get("file_path") or data.get("notebook_path") or data.get("path"), cwd)
    elif name in ("Glob", "Grep"):
        detail = clip(data.get("pattern")) + (f" ({short_path(data.get('path'), cwd)})" if data.get("path") else "")
    elif name == "Bash":
        detail = clip(data.get("command")) or "?"
    elif name == "WebSearch":
        detail = clip(data.get("query"))
    elif name == "WebFetch":
        detail = clip(data.get("url"))
    elif name in ("Task", "Agent"):
        detail = clip(data.get("description") or data.get("prompt"))
    else:
        detail = clip(next((v for v in data.values() if isinstance(v, str) and v.strip()), ""))
    return verb, noun, detail


def count(value):
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def token_counts(usage):
    if not isinstance(usage, dict):
        return None
    found = {key: count(usage.get(name)) for key, name in TOKEN_FIELDS}
    return {k: v for k, v in found.items() if v is not None} or None


def input_tokens(tokens):
    """Input tokens: new input, written to and read from the cache (all the text Claude read)."""
    return sum(count(tokens.get(key)) or 0 for key in ("input", "cache_creation", "cache_read"))


def amount_text(value):
    """950 -> "950", 3100 -> "3 bin", 1234567 -> "1,2 milyon"."""
    if value < 1000:
        return str(value)
    thousands = int(whole(value / 1000))
    if thousands < 1000:
        return f"{thousands} bin"
    millions = whole(value / 1_000_000, 1)
    return f"{int(millions) if millions.is_integer() else str(millions).replace('.', ',')} milyon"


def tools_text(tools):
    if not isinstance(tools, dict):
        return ""
    return ", ".join(f"{n} {TOOL_KIND_WORDS[kind]}" for kind in TOOL_KINDS if (n := count(tools.get(kind))))


def tokens_text(tokens):
    if not isinstance(tokens, dict):
        return ""
    output = count(tokens.get("output"))
    has_input = any(count(tokens.get(k)) is not None for k in ("input", "cache_creation", "cache_read"))
    parts = [f"{amount_text(input_tokens(tokens))} girdi" if has_input else None, f"{amount_text(output)} çıktı" if output is not None else None]
    shown = " / ".join(p for p in parts if p)
    return f"{shown} token" if shown else ""


@dataclass(frozen=True)
class LiveProgress:
    turn: int
    max_turns: int
    activity: str | None
    elapsed_s: float = 0.0
    tool_calls: int = 0

    @property
    def fraction(self):
        return min(1.0, self.turn / self.max_turns) if self.max_turns > 0 else 0.0

    def text(self, label=""):
        turn = f"tur {self.turn}/{self.max_turns}" if self.max_turns > 0 else f"tur {self.turn}"
        return " · ".join(p for p in (label, turn, self.activity) if p)


def content_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(b.get("text") or "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return ""


class StreamParser:
    """Turns `stream-json` events into short Turkish log lines and collects the run's live facts: turns (responses in the main session),
    tool calls by kind and their time, thinking time, tokens of the responses, the current turn and last activity, the `init` event, the
    result envelope, API error events and denied calls. `feed(line, at)` returns (text, level) pairs; `at` is when the line came (monotonic)."""

    def __init__(self, cwd, *, max_turns=0, model="", version=None):
        self.cwd, self.max_turns, self.model, self.version = Path(cwd), max_turns, model, version
        self.turns = self.tool_calls = self.events = 0
        self.thinking_s = 0.0
        self.kinds = dict.fromkeys(TOOL_KINDS, 0)
        self.tool_seconds = dict.fromkeys(TOOL_KINDS, 0.0)
        self.activity = None
        self.init = self.result = None
        self.api_errors, self.denied, self.rate_limits = [], [], []
        self._messages, self._pending, self._started, self._usage = set(), {}, {}, {}
        self._awaiting, self._denied_ids, self._last_at, self._rate_warned = False, set(), None, set()

    @property
    def current_turn(self):
        turn = self.turns + (1 if self._awaiting else 0)
        return min(turn, self.max_turns) if self.max_turns > 0 else turn

    def progress(self, elapsed=0.0):
        return LiveProgress(self.current_turn, self.max_turns, self.activity, elapsed, self.tool_calls)

    def stream_tokens(self):
        if not self._usage:
            return None
        keys = [key for key, _ in TOKEN_FIELDS if any(key in u for u in self._usage.values())]
        return {key: sum(u.get(key, 0) for u in self._usage.values()) for key in keys} or None

    def prefix(self):
        if not self.turns:
            return ""
        return f"Tur {self.turns}/{self.max_turns} · " if self.max_turns else f"Tur {self.turns} · "

    def feed(self, raw, now):
        line = raw.strip()
        if not line.startswith("{"):
            return []
        try:
            event = json.loads(line)
        except ValueError:
            return []
        if not isinstance(event, dict):
            return []
        self.events += 1
        kind = event.get("type")
        before = self._last_at  # thinking is measured from when the request started; side events do not move that moment
        if kind in ("assistant", "user") or (kind == "system" and event.get("subtype") in ANCHOR_SUBTYPES):
            self._last_at = now
        if kind == "system":
            return self.system(event)
        if kind == "assistant":
            return self.assistant(event, now - before if before is not None else None, now)
        if kind == "user":
            return self.user(event, now)
        if kind == "rate_limit_event":
            return self.rate_limit(event)
        if kind == "result":
            self.result = event
        return []

    def denial(self, tool_id, name, data):
        self._denied_ids.add(tool_id)
        action = tool_action(name, data, self.cwd) if name else None
        what = f"{action[1]} {action[2]}".strip() if action else (name or "araç")
        self.denied.append(what)
        return f"{self.prefix()}Reddedildi: {what}", "warning"

    def system(self, event):
        subtype = event.get("subtype")
        if subtype == "permission_denied":
            tool_id = str(event.get("tool_use_id") or "")
            if tool_id in self._denied_ids:
                return []
            name, data = self._pending.get(tool_id, (str(event.get("tool_name") or ""), {}))
            return [self.denial(tool_id, name, data)]
        if subtype == "thinking_tokens":
            self.activity = THINKING
            return []
        if subtype == "init":
            self.init = dict(event)
            self._awaiting = True
            out = []
            used = str(event.get("model") or "")
            if used and used != self.model:
                out.append((f"Kullanılan model: {used}" + (f" (istenen: {self.model})" if self.model else ""), "info"))
            running = str(event.get("claude_code_version") or "")
            if running and running != self.version:
                out.append((f"Çalışan Claude Code sürümü: {running}", "info"))
            return out
        if subtype == "api_retry":
            status = event.get("error_status")
            return [(f"Claude'un sunucusu cevap vermedi{f' (HTTP {status})' if status else ''}; yeniden deneniyor ({event.get('attempt')}/"
                     f"{event.get('max_retries')}).", "warning")]
        if subtype == "compact_boundary":
            return [(f"{self.prefix()}Bağlam özetlendi (uzun oturum).", "info")]
        return []

    def assistant(self, event, gap, now=0.0):
        if event.get("parent_tool_use_id"):
            return []  # a subagent's events are not the main session's turns
        message = event.get("message") if isinstance(event.get("message"), dict) else {}
        content = [b for b in message.get("content") or [] if isinstance(b, dict)]
        if event.get("error") or event.get("is_api_error_message") or event.get("api_error"):
            text = content_text(content)
            self.api_errors.append({k: event.get(k) for k in ("error", "api_error", "api_error_status", "api_error_code")} | {"text": text})
            return [(f"Claude hata bildirdi: {clip(text) or event.get('error') or event.get('api_error')}", "warning")]
        message_id = str(message.get("id") or event.get("uuid") or "")
        if message_id and message_id not in self._messages:
            self._messages.add(message_id)
            self.turns += 1
        self._awaiting = False
        tokens = token_counts(message.get("usage"))
        if tokens and message_id:  # every block of a response repeats its usage: keep the largest
            seen = self._usage.setdefault(message_id, {})
            for key, value in tokens.items():
                seen[key] = max(seen.get(key, 0), value)
        out = []
        for block in content:
            kind = block.get("type")
            if kind in ("thinking", "redacted_thinking"):
                self.activity = THINKING
                seconds = gap or 0.0
                self.thinking_s += seconds
                if seconds >= 1:
                    out.append((f"{self.prefix()}Düşünüyor ({duration_text(seconds)})", "info"))
            elif kind == "tool_use":
                self.tool_calls += 1
                name = str(block.get("name") or "")
                data = dict(block.get("input")) if isinstance(block.get("input"), dict) else {}
                tool_id = str(block.get("id") or "")
                self._pending[tool_id] = (name, data)
                group = KIND_OF_TOOL.get(name, "diger")
                self.kinds[group] += 1
                self._started[tool_id] = (group, now)
                action = tool_action(name, data, self.cwd)
                if action is not None:
                    self.activity = group if group != "diger" else action[1]
                    out.append((f"{self.prefix()}{action[0]}: {action[2]}", "info"))
        return out

    def user(self, event, now=0.0):
        if event.get("parent_tool_use_id"):
            return []
        message = event.get("message") if isinstance(event.get("message"), dict) else {}
        content = message.get("content")
        if not isinstance(content, list):
            return []
        meta = {str(m.get("id")): m for m in event.get("tool_result_meta") or [] if isinstance(m, dict)}
        out, answered = [], False
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            answered = True
            tool_id = str(block.get("tool_use_id") or "")
            name, data = self._pending.pop(tool_id, ("", {}))
            started = self._started.pop(tool_id, None)
            if started is not None:
                self.tool_seconds[started[0]] += max(0.0, now - started[1])
            if tool_id in self._denied_ids:
                continue
            text = content_text(block.get("content"))
            denied = (meta.get(tool_id) or {}).get("non_execution_kind") in DENIAL_KINDS or (bool(block.get("is_error")) and bool(DENIED.search(text)))
            if denied:
                out.append(self.denial(tool_id, name, data))
            elif block.get("is_error"):
                action = tool_action(name, data, self.cwd) if name else None
                what = f"{action[1]} {action[2]}".strip() if action else (name or "araç")
                out.append((f"{self.prefix()}Başarısız: {what} — {clip(text) or 'hata'}", "warning"))
        if answered and not self._pending:
            self._awaiting = True
            self.activity = THINKING
        return out

    def rate_limit(self, event):
        info = event.get("rate_limit_info") if isinstance(event.get("rate_limit_info"), dict) else {}
        if info:
            self.rate_limits.append({**info, "seen_at": time.time()})
        status = str(info.get("status") or "")
        if status not in ("allowed_warning", "rejected") or status in self._rate_warned:
            return []
        self._rate_warned.add(status)
        window = RATE_WINDOWS.get(str(info.get("rateLimitType") or ""), str(info.get("rateLimitType") or "kullanım"))
        try:
            reset_text = f" · sıfırlanma {epoch_text(info['resetsAt'])}" if info.get("resetsAt") else ""
        except (TypeError, ValueError, OverflowError, OSError):
            reset_text = ""
        if status == "rejected":
            return [(f"Claude kullanım sınırına ulaşıldı ({window} sınır){reset_text}.", "warning")]
        used = info.get("utilization")
        share = f": %{int(whole(float(used) * 100))} kullanıldı" if isinstance(used, (int, float)) else ""
        return [(f"Uyarı: Claude kullanım sınırına yaklaşılıyor · {window} sınır{share}{reset_text}.", "warning")]


# ------------------------------------------------------------------------------------------------------------------- result

def parse_envelope(stdout):
    """The result envelope (`type: "result"`) in the output; None without one."""
    text = (stdout or "").strip()
    if not text:
        return None

    def pick(data):
        if isinstance(data, dict) and data.get("type") == "result":
            return data
        if isinstance(data, list):
            return next((d for d in reversed(data) if isinstance(d, dict) and d.get("type") == "result"), None)
        return None

    try:
        found = pick(json.loads(text))
        if found is not None:
            return found
    except ValueError:
        pass
    for line in reversed(text.splitlines()):
        if line.strip().startswith(("{", "[")):
            try:
                found = pick(json.loads(line.strip()))
            except ValueError:
                continue
            if found is not None:
                return found
    return None


@dataclass
class RunResult:
    argv: list
    returncode: int | None
    stdout: str
    stderr: str
    envelope: dict | None
    failure: Failure | None
    started_at: str
    finished_at: str
    elapsed_s: float
    model: str = ""
    effort: str = ""
    claude_version: str | None = None
    init: dict | None = None
    stream_file: str | None = None
    turns: int = 0
    tool_calls: int = 0
    thinking_s: float = 0.0
    api_errors: list = field(default_factory=list)
    tool_kinds: dict = field(default_factory=dict)
    tool_seconds: dict = field(default_factory=dict)
    stream_tokens: dict | None = None
    rate_limits: list = field(default_factory=list)
    denied: list = field(default_factory=list)

    @property
    def ok(self):
        return self.failure is None

    @property
    def session_id(self):
        value = (self.envelope or {}).get("session_id") or (self.init or {}).get("session_id")
        return value if isinstance(value, str) and value else None

    @property
    def model_used(self):
        value = (self.init or {}).get("model")
        return value if isinstance(value, str) and value else None

    @property
    def permission_denials(self):
        value = (self.envelope or {}).get("permission_denials")
        return [d for d in value if isinstance(d, dict)] if isinstance(value, list) else []

    def metrics(self):
        env = self.envelope or {}
        tokens, source = token_counts(env.get("usage")), "result"
        if tokens is None and self.stream_tokens:
            tokens, source = dict(self.stream_tokens), "stream"
        api_ms = env.get("duration_api_ms")
        api_s = whole(api_ms / 1000, 1) if isinstance(api_ms, (int, float)) and not isinstance(api_ms, bool) else None
        cost = env.get("total_cost_usd")
        return {"elapsed_s": self.elapsed_s, "api_s": api_s, "thinking_s": self.thinking_s, "turns": self.turns, "tool_calls": self.tool_calls,
                "tools": {k: int(self.tool_kinds.get(k, 0)) for k in TOOL_KINDS},
                "tool_s": {k: whole(self.tool_seconds.get(k, 0.0), 1) for k in TOOL_KINDS},
                "tokens": {**tokens, "source": source} if tokens else None,
                "cost_usd": cost if isinstance(cost, (int, float)) and not isinstance(cost, bool) else None}

    def summary(self):
        """The run record's envelope fields; model, effort, Claude Code version, stream file, measurement."""
        env = self.envelope or {}
        result = env.get("result")
        return {"session_id": self.session_id, "subtype": env.get("subtype"), "is_error": env.get("is_error"),
                "api_error_status": env.get("api_error_status"), "num_turns": self.turns, "tool_calls": self.tool_calls,
                "cc_num_turns": env.get("num_turns"), "duration_ms": env.get("duration_ms"), "duration_api_ms": env.get("duration_api_ms"),
                "total_cost_usd": env.get("total_cost_usd"), "usage": env.get("usage"), "model_usage": env.get("modelUsage"),
                "permission_denials": self.permission_denials, "denied": list(self.denied), "stop_reason": env.get("stop_reason"),
                "result": mask(result[:MAX_RESULT_CHARS]) if isinstance(result, str) else None,
                "errors": [mask(str(e)) for e in env.get("errors")] if isinstance(env.get("errors"), list) else [],
                "returncode": self.returncode, "elapsed_s": self.elapsed_s,
                "stderr": mask(self.stderr[-MAX_STDERR_CHARS:]) if self.stderr else "", "model": self.model or None,
                "effort": self.effort or None, "model_used": self.model_used, "claude_version": self.claude_version,
                "stream_file": self.stream_file, "thinking_s": self.thinking_s, "metrics": self.metrics()}


def summary_line(result):
    """"Claude bitti: 14 tur · 22 araç çağrısı (20 okuma, 2 yazma) · 6 dk 12 sn · düşünme 2 dk 5 sn · 410 bin girdi / 62 bin çıktı token ·
    maliyet karşılığı 1,23 $ · 1 reddedilen çağrı"."""
    metrics = result.metrics()
    kinds = tools_text(metrics["tools"])
    parts = [f"{result.turns} tur", (f"{result.tool_calls} araç çağrısı" + (f" ({kinds})" if kinds else "")) if result.tool_calls else None,
             duration_text(result.elapsed_s), f"düşünme {duration_text(result.thinking_s)}" if result.thinking_s >= 1 else None,
             tokens_text(metrics["tokens"]) or None]
    cost = metrics["cost_usd"]
    if cost:
        cents = int(whole(cost * 100))
        parts.append(f"maliyet karşılığı {cents // 100},{cents % 100:02d} $")
    if result.permission_denials:
        parts.append(f"{len(result.permission_denials)} reddedilen çağrı")
    return "Claude bitti: " + " · ".join(p for p in parts if p)


def kill_tree(process):
    if process.poll() is not None:
        return
    if sys.platform == "win32":
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True, timeout=KILL_WAIT, creationflags=NO_WINDOW)
        except (OSError, subprocess.SubprocessError):
            pass
        if process.poll() is None:
            process.kill()
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (OSError, AttributeError):
        process.kill()


def open_stream(path, header):
    if path is None:
        return None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handle = path.open("a", encoding="utf-8", newline="\n")
        handle.write(json.dumps(header, ensure_ascii=False) + "\n")
        handle.flush()
        return handle
    except OSError as exc:
        log.warning("Claude'un akış dosyası açılamadı (%s): %s", path, exc)
        return None


def write_stream(handle, line):
    if handle is None:
        return
    text = line.rstrip("\r\n")
    if not text.strip():
        return
    if not text.lstrip().startswith(("{", "[")):
        text = json.dumps({"type": "studio_raw_text", "text": text}, ensure_ascii=False)
    try:
        handle.write(mask(text) + "\n")
        handle.flush()
    except (OSError, ValueError) as exc:
        log.warning("Claude'un akış dosyasına yazılamadı: %s", exc)


def run(inv, command, *, env=None, timeout=None, on_start=None, is_canceled=None, on_tick=None, popen=subprocess.Popen, clock=time.monotonic,
        poll=POLL_INTERVAL, tick=TICK_INTERVAL, stream_path=None, on_log=None, on_progress=None):
    """Runs Claude, waits for it (checking cancel and timeout) and classifies the result. `on_log(text, level)`: live Turkish lines;
    `on_progress(LiveProgress)`: when the current turn or last activity changes; both in the calling thread."""
    argv = build_args(command, inv)
    timeout = timeout_for(inv.max_turns) if timeout is None else timeout

    def say(text, level="info"):
        if on_log is None:
            return
        try:
            on_log(text, level)
        except Exception:  # a log that cannot be written must not leave Claude unattended
            log.exception("Claude'un canlı satırı iş günlüğüne yazılamadı.")

    env = dict(build_env() if env is None else env)
    api_key = claude_info.api_key_in_env(env)
    for folder in output_dirs(inv):
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            log.warning("Claude'un çıktı klasörü oluşturulamadı (%s): %s", folder, exc)
    version = read_version(command)
    say(start_line(version, inv.model, inv.effort))
    started_at = now_iso()
    stream_file = short_path(stream_path, inv.cwd) if stream_path is not None else None
    handle = open_stream(Path(stream_path) if stream_path is not None else None,
                         {"type": "studio_run", "started_at": started_at, "command": display_args(argv), "model": inv.model or None,
                          "effort": inv.effort or None, "claude_version": version})
    parser = StreamParser(inv.cwd, max_turns=inv.max_turns, model=inv.model, version=version)
    start = clock()

    def finish(returncode, stdout, stderr, envelope, failure):
        elapsed = whole(clock() - start, 1)
        running = (parser.init or {}).get("claude_code_version")
        result = RunResult(argv, returncode, stdout, stderr, envelope, failure, started_at, now_iso(), elapsed, model=inv.model,
                           effort=inv.effort, claude_version=running if isinstance(running, str) and running else version, init=parser.init,
                           stream_file=stream_file, turns=parser.turns, tool_calls=parser.tool_calls, thinking_s=whole(parser.thinking_s, 1),
                           api_errors=list(parser.api_errors), tool_kinds=dict(parser.kinds), tool_seconds=dict(parser.tool_seconds),
                           stream_tokens=parser.stream_tokens(), rate_limits=list(parser.rate_limits), denied=list(parser.denied))
        if handle is not None:
            write_stream(handle, json.dumps({"type": "studio_run_end", "finished_at": result.finished_at, "returncode": returncode,
                                             "elapsed_s": elapsed, "turns": parser.turns, "tool_calls": parser.tool_calls,
                                             "metrics": result.metrics(), "failure": failure.to_dict() if failure else None}, ensure_ascii=False))
            try:
                handle.close()
            except OSError:
                pass
        return result

    kwargs = {"creationflags": NO_WINDOW} if sys.platform == "win32" else {"start_new_session": True}
    try:
        process = popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(inv.cwd), env=env, text=True,
                        encoding="utf-8", errors="replace", **kwargs)
    except OSError as exc:
        return finish(None, "", "", None, Failure(NOT_FOUND, f"Claude Code çalıştırılamadı ({exc.strerror or type(exc).__name__}): "
                                                             f"{command[-1] if command else '?'}. {NOT_FOUND_MESSAGE}"))
    try:
        return watch(process, inv, timeout=timeout, on_start=on_start, is_canceled=is_canceled, on_tick=on_tick, clock=clock, poll=poll,
                     tick=tick, say=say, handle=handle, parser=parser, start=start, version=version, api_key=api_key, finish=finish,
                     on_progress=on_progress)
    except BaseException:  # an unexpected error: Claude must not keep running in the background
        kill_tree(process)
        if handle is not None:
            try:
                handle.close()
            except OSError:
                pass
        raise


def watch(process, inv, *, timeout, on_start, is_canceled, on_tick, clock, poll, tick, say, handle, parser, start, version, api_key, finish,
          on_progress=None):
    """Writes the task text, reads the stream line by line (stream file, live lines, progress), checks cancel and timeout; then classifies."""
    if on_start is not None:
        on_start(process)
    out, err = [], []
    lines = queue.SimpleQueue()
    reported = []

    def report():
        if on_progress is None or not parser.events:
            return
        key = (parser.current_turn, parser.activity)
        if reported and reported[-1] == key:
            return
        reported[:] = [key]
        try:
            on_progress(parser.progress(clock() - start))
        except Exception:
            log.exception("Claude'un ilerlemesi iş paneline yazılamadı.")

    def read_out(stream):
        try:
            for line in iter(stream.readline, ""):
                out.append(line)
                lines.put((line, clock()))
        except (OSError, ValueError):
            pass

    def read_err(stream):
        try:
            for chunk in iter(lambda: stream.read(65536), ""):
                err.append(chunk)
        except (OSError, ValueError):
            pass

    def write():
        try:
            process.stdin.write(inv.prompt)
        except (OSError, ValueError):
            pass
        finally:
            try:
                process.stdin.close()
            except (OSError, ValueError):
                pass

    def drain():
        while True:
            try:
                line, at = lines.get_nowait()
            except queue.Empty:
                report()
                return
            write_stream(handle, line)
            try:
                produced = parser.feed(line, at)
            except Exception:
                log.exception("Claude akış satırı çözümlenemedi.")
                continue
            for text, level in produced:
                say(text, level)

    threads = [threading.Thread(target=read_out, args=(process.stdout,), daemon=True),
               threading.Thread(target=read_err, args=(process.stderr,), daemon=True), threading.Thread(target=write, daemon=True)]
    for thread in threads:
        thread.start()
    stopped, last_tick = None, start
    while True:
        try:
            process.wait(timeout=poll)
            break
        except subprocess.TimeoutExpired:
            pass
        drain()
        now = clock()
        if is_canceled is not None and is_canceled():
            stopped = CANCELED
        elif now - start > timeout:
            stopped = TIMEOUT
        if stopped:
            kill_tree(process)
            try:
                process.wait(timeout=KILL_WAIT)
            except subprocess.TimeoutExpired:
                process.kill()
            break
        if on_tick is not None and now - last_tick >= tick:
            last_tick = now
            on_tick(now - start)
    for thread in threads:
        thread.join(KILL_WAIT if not stopped else 2.0)
    drain()
    stdout, stderr = "".join(out), "".join(err)
    envelope = parser.result or parse_envelope(stdout)
    if stopped == CANCELED:
        failure = Failure(CANCELED, CANCELED_MESSAGE)
    elif stopped == TIMEOUT:
        failure = Failure(TIMEOUT, f"Claude {max(1, int(whole(timeout / 60)))} dakika içinde bitmedi; iş durduruldu (zaman aşımı).",
                          retryable=True)
    else:
        failure = classify(process.returncode, envelope, stderr, max_turns=inv.max_turns, api_key=api_key, model=inv.model,
                           effort=inv.effort, version=version, api_errors=parser.api_errors)
    return finish(process.returncode, stdout, stderr, envelope, failure)


# ------------------------------------------------------------------------------------------------------------------- instruction versions

def instruction_hashes(files, *, repo=REPO_DIR):
    """SHA-256 of every instruction and schema file a run used (repository paths), so a result is always tied to the instructions that made
    it; plus the repository commit when git is at hand (None otherwise)."""
    items = []
    for path in files:
        path = Path(path)
        try:
            rel = path.resolve().relative_to(Path(repo).resolve()).as_posix()
        except ValueError:
            rel = path.name
        items.append({"path": rel, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    commit = None
    git = shutil.which("git")
    if git:
        try:
            done = subprocess.run([git, "rev-parse", "HEAD"], cwd=str(repo), capture_output=True, text=True, timeout=10,
                                  stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
            commit = done.stdout.strip() or None if done.returncode == 0 else None
        except (OSError, subprocess.SubprocessError):
            commit = None
    return {"commit": commit, "files": items}


def result_dict(result):
    """For the run record: the command (log form), times, envelope fields, model, effort, version and failure."""
    return {"command": display_args(result.argv), "started_at": result.started_at, "finished_at": result.finished_at, **result.summary(),
            "failure": result.failure.to_dict() if result.failure else None}
