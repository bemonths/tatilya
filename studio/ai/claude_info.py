"""Where Claude Code is, its version and the `ANTHROPIC_API_KEY` warning (taken over from The Housing Atlas Stüdyo, `atlas/claude_info.py`).

Search order: the path in Settings, `claude` on PATH, `%APPDATA%\\npm\\claude.cmd`, `%USERPROFILE%\\.local\\bin\\claude.exe` (outside Windows
finally `~/.local/bin/claude`). The version (`claude --version`, 10 s timeout) is read again on every call: no cache. Housing Atlas once cached
it by the path and the file's modification time; the npm shim (`claude.cmd`) does not change on an update, so an old version stayed on screen
after Claude Code was updated. When `ANTHROPIC_API_KEY` is set Claude Code bills the API instead of the subscription; the screens say so.
"""
import logging
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)

VERSION_TIMEOUT = 10.0
VERSION_PATTERN = re.compile(r"\d+\.\d+(?:\.\d+)?")
API_KEY_WARNING = ("ANTHROPIC_API_KEY ortam değişkeni tanımlı: Claude Code aboneliğiniz yerine API hesabınızdan ücretlendirilir. Abonelikle "
                   "çalışmak için bu değişkeni kaldırıp uygulamayı yeniden açın.")


def candidates(configured="", *, env=None, which=shutil.which):
    env = os.environ if env is None else env
    paths = [Path(configured)] if configured else []
    on_path = which("claude")
    if on_path:
        paths.append(Path(on_path))
    if env.get("APPDATA"):
        paths.append(Path(env["APPDATA"]) / "npm" / "claude.cmd")
    if env.get("USERPROFILE"):
        paths.append(Path(env["USERPROFILE"]) / ".local" / "bin" / "claude.exe")
    if sys.platform != "win32" and env.get("HOME"):
        # the native installer writes here; an app opened from the desktop may not have this folder on PATH
        paths.append(Path(env["HOME"]) / ".local" / "bin" / "claude")
    return paths


def find_claude(configured="", *, env=None, which=shutil.which):
    return next((path for path in candidates(configured, env=env, which=which) if path.is_file()), None)


def read_version(path, *, run=subprocess.run, timeout=VERSION_TIMEOUT):
    """The version in `claude --version`; None when it cannot be read (no file, timeout, no version). Read again on every call."""
    if not Path(path).is_file():
        return None
    # the tests' fake program (.py) runs with the app's own Python, as in the runner
    command = [sys.executable, str(path)] if Path(path).suffix.lower() == ".py" else [str(path)]
    try:
        result = run([*command, "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace",
                     timeout=timeout, stdin=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        log.warning("Claude Code sürümü %s saniyede okunamadı: %s", timeout, path)
        return None
    except (OSError, subprocess.SubprocessError) as exc:
        log.warning("Claude Code sürümü okunamadı (%s): %s", path, exc)
        return None
    match = VERSION_PATTERN.search(result.stdout or "")
    return match.group(0) if match else None


def api_key_in_env(env=None):
    return bool((os.environ if env is None else env).get("ANTHROPIC_API_KEY"))


def info(configured=""):
    path = find_claude(configured)
    api_key = api_key_in_env()
    return {"found": path is not None, "path": str(path) if path else None, "version": read_version(path) if path else None,
            "api_key_env": api_key, "api_key_warning": API_KEY_WARNING if api_key else None}
