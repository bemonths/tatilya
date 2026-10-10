"""Claude settings (GÖREV-13): Claude Code's path, the general default model and effort, and per step the model, the effort ("Genel varsayılan"
inherits the general default) and the turn limit. The lists and the inheritance rule are The Housing Atlas Stüdyo's (`atlas/config.py`:
`MODEL_CHOICES`, `EFFORT_CHOICES`, `resolve_model_effort`).

Settings are the user's data, not the repository's: `<data folder>/ayarlar.json`, written atomically. Nothing secret is stored (no API key;
Claude Code keeps its own login). A missing key takes its default; a value outside the lists is refused when saved and replaced by its default
(with a note) when read.
"""
import json
import os
import tempfile
from pathlib import Path

SETTINGS_FILE = "ayarlar.json"
INHERIT = "inherit"
INHERIT_LABEL = "Genel varsayılan"
MODEL_CHOICES = (
    ("", "Claude Code varsayılanı"),
    ("claude-opus-5-5", "Opus 5.5"),
    ("claude-fable-5-1", "Fable 5.1"),
    ("claude-sonnet-5", "Sonnet 5"),
    ("claude-haiku-4-5", "Haiku 4.5"),
)
EFFORT_CHOICES = (
    ("", "Otomatik"),
    ("low", "Düşük"),
    ("medium", "Orta"),
    ("high", "Yüksek"),
    ("xhigh", "Çok yüksek"),
    ("max", "En yüksek"),
)
MODELS = tuple(value for value, _ in MODEL_CHOICES)
EFFORTS = tuple(value for value, _ in EFFORT_CHOICES)
MODEL_LABELS = dict(MODEL_CHOICES)
EFFORT_LABELS = dict(EFFORT_CHOICES)
# Claude steps whose model, effort and turn limit are set apart (order of the Settings screen); later steps join this list.
CLAUDE_STEPS = (("baslik", "Konu ve başlık"),)
STEP_DEFAULTS = {"baslik": {"model": "claude-opus-5-5", "effort": "high", "max_turns": 30}}
MAX_TURNS_MIN, MAX_TURNS_MAX, MAX_TURNS_DEFAULT = 1, 200, 30
MAX_TURNS_HELP = ("Tur, Claude'un bir cevabıdır: Claude her turda düşünür ve bir ya da birkaç iş ister (dosya okur ya da dosya yazar). Bu "
                  "sınır bir Claude çalışmasının en çok kaç cevap verebileceğidir; araç çağrılarını değil cevapları sayar. İş panelindeki "
                  "\"Tur 12/30\" ve bitişteki \"30 tur\" aynı sayıdır. Sınıra ulaşan çalışma yarıda durur. "
                  f"{MAX_TURNS_MIN} ile {MAX_TURNS_MAX} arasında bir sayı.")


class SettingsError(ValueError):
    def __init__(self, field, message):
        super().__init__(message)
        self.field = field
        self.message = message


def defaults():
    values = {"claude_path": "", "claude_model": "", "claude_effort": ""}
    for key, _ in CLAUDE_STEPS:
        step = STEP_DEFAULTS.get(key, {})
        values[f"claude_model_{key}"] = step.get("model", INHERIT)
        values[f"claude_effort_{key}"] = step.get("effort", INHERIT)
        values[f"claude_max_turns_{key}"] = step.get("max_turns", MAX_TURNS_DEFAULT)
    return values


def check(field, value):
    """The value when it is valid for the field, else SettingsError with a Turkish reason."""
    if field == "claude_path":
        if not isinstance(value, str) or len(value) > 500:
            raise SettingsError(field, "Claude Code yolu bir metin olmalı.")
        return value.strip()
    if field in ("claude_model", "claude_effort") or field.startswith(("claude_model_", "claude_effort_")):
        allowed = MODELS if field.startswith("claude_model") else EFFORTS
        step_field = field not in ("claude_model", "claude_effort")
        if not isinstance(value, str) or value not in allowed and not (step_field and value == INHERIT):
            raise SettingsError(field, "Seçim listede yok.")
        return value
    if field.startswith("claude_max_turns_"):
        if isinstance(value, bool) or not isinstance(value, int) or not MAX_TURNS_MIN <= value <= MAX_TURNS_MAX:
            raise SettingsError(field, f"Tur sınırı {MAX_TURNS_MIN} ile {MAX_TURNS_MAX} arasında bir tam sayı olmalı.")
        return value
    raise SettingsError(field, "Bilinmeyen ayar.")


def path_of(data_dir):
    return Path(data_dir) / SETTINGS_FILE


def load(data_dir):
    """Settings with defaults for missing keys; an unreadable file or a value outside the lists falls back to the default (`notes` say so)."""
    values, notes = defaults(), []
    path = path_of(data_dir)
    if path.is_file():
        try:
            stored = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            stored, notes = {}, ["Ayar dosyası okunamadı; varsayılan ayarlar kullanılıyor."]
        for field, value in (stored.get("claude") or {}).items() if isinstance(stored, dict) else ():
            if field not in values:
                continue
            try:
                values[field] = check(field, value)
            except SettingsError:
                notes.append(f"'{field}' ayarı geçersizdi; varsayılanı kullanılıyor.")
    return {**values, "notes": notes}


def save(data_dir, changes):
    """Checks every changed field (all or nothing) and writes the whole Claude section atomically; returns the new settings."""
    current = {k: v for k, v in load(data_dir).items() if k != "notes"}
    for field, value in (changes or {}).items():
        if field not in current:
            raise SettingsError(field, "Bilinmeyen ayar.")
        current[field] = check(field, value)
    path = path_of(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    stored = {}
    if path.is_file():
        try:
            stored = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            stored = {}
    stored = stored if isinstance(stored, dict) else {}
    stored["claude"] = current
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=".ayarlar-", suffix=".json")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            json.dump(stored, out, ensure_ascii=False, indent=1)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    return load(data_dir)


def resolve_model_effort(settings, step):
    """(model, effort) a step runs with: its own setting, or the general default for "Genel varsayılan". "" leaves the choice to Claude Code
    (`--model` / `--effort` are not given)."""
    model = settings.get(f"claude_model_{step}", INHERIT)
    effort = settings.get(f"claude_effort_{step}", INHERIT)
    return (settings.get("claude_model", "") if model == INHERIT else model,
            settings.get("claude_effort", "") if effort == INHERIT else effort)


def max_turns(settings, step):
    value = settings.get(f"claude_max_turns_{step}")
    return value if isinstance(value, int) and not isinstance(value, bool) else MAX_TURNS_DEFAULT


def model_label(model):
    return INHERIT_LABEL if model == INHERIT else MODEL_LABELS.get(model, model)


def effort_label(effort):
    return INHERIT_LABEL if effort == INHERIT else EFFORT_LABELS.get(effort, effort)


def options():
    """The Settings screen's lists."""
    return {"models": [{"value": v, "label": l} for v, l in MODEL_CHOICES], "efforts": [{"value": v, "label": l} for v, l in EFFORT_CHOICES],
            "inherit": {"value": INHERIT, "label": INHERIT_LABEL},
            "steps": [{"key": key, "label": title, "model_field": f"claude_model_{key}", "effort_field": f"claude_effort_{key}",
                       "max_turns_field": f"claude_max_turns_{key}"} for key, title in CLAUDE_STEPS],
            "max_turns": {"min": MAX_TURNS_MIN, "max": MAX_TURNS_MAX, "help": MAX_TURNS_HELP}}
