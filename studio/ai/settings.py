"""Claude settings (GÖREV-13): Claude Code's path, the general default model and effort, and per step the model, the effort ("Genel varsayılan"
inherits the general default) and (GÖREV-18) the output guess of the token estimate; the token limits of one call and of one job. The lists and the inheritance rule are The Housing Atlas Stüdyo's (`atlas/config.py`:
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
# GÖREV-14: the family aliases (Claude Code runs that family's newest model, as in Housing Atlas) and claude-sonnet-5-5. Only verified
# full model ids are listed.
MODEL_CHOICES = (
    ("", "Claude Code varsayılanı"),
    ("opus", "Opus (en yeni sürüm)"),
    ("sonnet", "Sonnet (en yeni sürüm)"),
    ("haiku", "Haiku (en yeni sürüm)"),
    ("claude-opus-5-5", "Opus 5.5"),
    ("claude-fable-5-1", "Fable 5.1"),
    ("claude-sonnet-5-5", "Sonnet 5.5"),
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
CLAUDE_STEPS = (("baslik", "Konu ve başlık"), ("baslik_degerlendirme", "Başlık değerlendirme"),
                # GÖREV-15: the video text's seven steps (Ek N gives their starting model and effort; family aliases)
                ("metin_plan", "Video metni · plan"), ("metin_plan_elestiri", "Video metni · plan eleştirisi"),
                ("metin_bolum", "Video metni · bölüm"), ("metin_birlestirme", "Video metni · birleştirme"),
                ("metin_giris_kapanis", "Video metni · giriş ve kapanış"), ("metin_son_okuma", "Video metni · son okuma"),
                ("metin_ceviri", "Video metni · çeviri"))
# GÖREV-18: every step is one call without tools (`--tools ""`, `--max-turns 1`); the turn limit is no longer a setting (old
# `claude_max_turns_<step>` keys in a settings file are ignored). Model and effort are as before (GÖREV-18 Adım 5 keeps them).
STEP_DEFAULTS = {"baslik": {"model": "claude-opus-5-5", "effort": "high"},
                 "baslik_degerlendirme": {"model": "claude-opus-5-5", "effort": "high"},
                 "metin_plan": {"model": "opus", "effort": "high"},
                 "metin_plan_elestiri": {"model": "opus", "effort": "medium"},
                 "metin_bolum": {"model": "opus", "effort": "high"},
                 "metin_birlestirme": {"model": "opus", "effort": "medium"},
                 "metin_giris_kapanis": {"model": "opus", "effort": "high"},
                 "metin_son_okuma": {"model": "opus", "effort": "medium"},
                 "metin_ceviri": {"model": "sonnet", "effort": "medium"}}
# GÖREV-15 (Adım 5): the video text chain's own settings. Sessions at once (the section writers run side by side), the usage thresholds
# at which no new session opens (5-hour and weekly window, percent) and "Plandan sonra dur" (the run stops after the plan for the user).
TEXT_FIELDS = {"claude_max_sessions": (1, 8, 6), "claude_limit_five_hour": (1, 100, 90), "claude_limit_week": (1, 100, 95)}
STOP_AFTER_PLAN = "claude_stop_after_plan"
TEXT_HELP = {"claude_max_sessions": "Video metninin bölüm yazıcıları aynı anda çalışır; aynı anda en çok bu kadar Claude oturumu açılır (1–8).",
             "claude_limit_five_hour": "5 saatlik kullanım bu yüzdeye gelince yeni oturum açılmaz; çalışma sıfırlanmayı bekleyip kendiliğinden sürer.",
             "claude_limit_week": "Haftalık kullanım bu yüzdeye gelince yeni oturum açılmaz; çalışma sıfırlanmayı bekleyip kendiliğinden sürer.",
             STOP_AFTER_PLAN: "Açıksa video metni çalışması plandan sonra durur; planı görüp “Devam” ile sürdürürsünüz."}
# GÖREV-18: token limits (Settings → Claude). A call is one step's single Claude call (read and written tokens together); the job limit
# is the safety catch of one job (a title run, or a video text run with all its tones). The output guess is the estimate's written
# tokens (thinking included) for a step with no earlier run to take a median from.
LIMIT_FIELDS = {"claude_call_limit": (20_000, 1_000_000, 250_000), "claude_job_limit": (100_000, 10_000_000, 1_500_000)}
LIMIT_HELP = {"claude_call_limit": "Tek bir Claude çağrısının en çok okuyup yazabileceği token (okunan ve yazılan toplam). Tahmini bunu aşan "
                                   "çağrı başlatılmaz; program neyin büyük olduğunu söyler.",
              "claude_job_limit": "Bir işin (başlık çalışması ya da bütün tonlarıyla bir video metni) en çok token'ı. Tahmin aşarsa iş "
                                  "başlamaz; çalışırken gerçek toplam buraya gelirse zincir durur ve “Devam”ı bekler."}
OUTPUT_GUESS_DEFAULTS = {"baslik": 60_000, "baslik_degerlendirme": 15_000, "metin_plan": 20_000, "metin_plan_elestiri": 6_000,
                         "metin_bolum": 8_000, "metin_birlestirme": 6_000, "metin_giris_kapanis": 6_000, "metin_son_okuma": 10_000,
                         "metin_ceviri": 12_000}
OUTPUT_GUESS_RANGE = (500, 128_000)
OUTPUT_GUESS_HELP = ("Çıktı varsayımı: adımın daha önce hiç başarılı çalışması yokken tahminde kullanılan yazılan token (düşünme dahil). "
                     "Önceki çalışmalar varsa onların ortancası kullanılır.")
# GÖREV-18: save() writes every field, so a value equal to an old default in a file saved before this version was not the user's choice;
# it gives way to the new default. A file saved from now on carries `ayar_surumu` and keeps whatever it holds.
SETTINGS_VERSION = 18
OLD_DEFAULTS = {"claude_max_sessions": 3}


class SettingsError(ValueError):
    def __init__(self, field, message):
        super().__init__(message)
        self.field = field
        self.message = message


def defaults():
    values = {"claude_path": "", "claude_model": "", "claude_effort": ""}
    values.update({field: default for field, (_, _, default) in TEXT_FIELDS.items()})
    values.update({field: default for field, (_, _, default) in LIMIT_FIELDS.items()})
    values[STOP_AFTER_PLAN] = False
    for key, _ in CLAUDE_STEPS:
        step = STEP_DEFAULTS.get(key, {})
        values[f"claude_model_{key}"] = step.get("model", INHERIT)
        values[f"claude_effort_{key}"] = step.get("effort", INHERIT)
        values[f"claude_output_guess_{key}"] = OUTPUT_GUESS_DEFAULTS.get(key, 10_000)
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
    if field in TEXT_FIELDS:
        low, high, _ = TEXT_FIELDS[field]
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            raise SettingsError(field, f"{low} ile {high} arasında bir tam sayı olmalı.")
        return value
    if field == STOP_AFTER_PLAN:
        if not isinstance(value, bool):
            raise SettingsError(field, "Açık ya da kapalı olmalı.")
        return value
    if field in LIMIT_FIELDS:
        low, high, _ = LIMIT_FIELDS[field]
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            raise SettingsError(field, f"{low:,} ile {high:,} arasında bir tam sayı olmalı.".replace(",", "."))
        return value
    if field.startswith("claude_output_guess_"):
        low, high = OUTPUT_GUESS_RANGE
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            raise SettingsError(field, f"Çıktı varsayımı {low:,} ile {high:,} token arasında bir tam sayı olmalı.".replace(",", "."))
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
        section = stored.get("claude") if isinstance(stored, dict) and isinstance(stored.get("claude"), dict) else {}
        version = section.get("ayar_surumu")
        before = not (isinstance(version, int) and version >= SETTINGS_VERSION)
        for field, value in section.items():
            if field not in values:
                continue                                    # e.g. the old turn limits (GÖREV-18)
            if before and field in OLD_DEFAULTS and value == OLD_DEFAULTS[field]:
                continue                                    # an old default save() wrote, not a choice: the new default holds
            try:
                values[field] = check(field, value)
            except SettingsError:
                notes.append(f"'{field}' ayarı geçersizdi; varsayılanı kullanılıyor.")
    return {**values, "notes": notes}


def stored_settings(data_dir):
    path = path_of(data_dir)
    if not path.is_file():
        return {}
    try:
        stored = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return stored if isinstance(stored, dict) else {}


def write_settings(data_dir, stored):
    path = path_of(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=".ayarlar-", suffix=".json")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            json.dump(stored, out, ensure_ascii=False, indent=1)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def save(data_dir, changes):
    """Checks every changed field (all or nothing) and writes the whole Claude section atomically; returns the new settings."""
    current = {k: v for k, v in load(data_dir).items() if k != "notes"}
    for field, value in (changes or {}).items():
        if field not in current:
            raise SettingsError(field, "Bilinmeyen ayar.")
        current[field] = check(field, value)
    stored = stored_settings(data_dir)
    stored["claude"] = {**current, "ayar_surumu": SETTINGS_VERSION}
    write_settings(data_dir, stored)
    return load(data_dir)


# ---- title suffixes (GÖREV-14, Adım 4e): per destination, defaults from the destination profile (`CHANNEL["title_suffix"]`) ----------

SUFFIX_SECTION, SUFFIX_MAX = "baslik_ekleri", 40
SUFFIX_LANGUAGES = (("en", "İngilizce başlık eki"), ("tr", "Türkçe başlık eki"))


def suffix_defaults(profile):
    found = (getattr(profile, "CHANNEL", None) or {}).get("title_suffix") or {}
    return {lang: found.get(lang, "") for lang, _ in SUFFIX_LANGUAGES}


def check_suffix(lang, value):
    label = dict(SUFFIX_LANGUAGES)[lang]
    if not isinstance(value, str) or len(value) > SUFFIX_MAX or "\n" in value or "\r" in value:
        raise SettingsError(f"baslik_eki_{lang}", f"{label} en çok {SUFFIX_MAX} karakterlik tek satır bir metin olmalı.")
    return value


def title_suffixes(data_dir, destination_id, profile):
    """{"en", "tr", "defaults"}: the stored suffixes of the destination, or the profile's defaults. Spaces are kept as written (the suffix
    usually starts with a space: " | 30A Florida Vacation")."""
    defaults = suffix_defaults(profile)
    stored = (stored_settings(data_dir).get(SUFFIX_SECTION) or {}).get(destination_id) or {}
    values = {}
    for lang, _ in SUFFIX_LANGUAGES:
        try:
            values[lang] = check_suffix(lang, stored[lang]) if lang in stored else defaults[lang]
        except SettingsError:
            values[lang] = defaults[lang]
    return {**values, "defaults": defaults}


def save_title_suffixes(data_dir, destination_id, profile, changes):
    current = {k: v for k, v in title_suffixes(data_dir, destination_id, profile).items() if k != "defaults"}
    for lang, value in (changes or {}).items():
        if lang not in current:
            raise SettingsError(lang, "Bilinmeyen ayar.")
        current[lang] = check_suffix(lang, value)
    stored = stored_settings(data_dir)
    section = stored.get(SUFFIX_SECTION) if isinstance(stored.get(SUFFIX_SECTION), dict) else {}
    section[destination_id] = current
    stored[SUFFIX_SECTION] = section
    write_settings(data_dir, stored)
    return title_suffixes(data_dir, destination_id, profile)


def resolve_model_effort(settings, step):
    """(model, effort) a step runs with: its own setting, or the general default for "Genel varsayılan". "" leaves the choice to Claude Code
    (`--model` / `--effort` are not given)."""
    model = settings.get(f"claude_model_{step}", INHERIT)
    effort = settings.get(f"claude_effort_{step}", INHERIT)
    return (settings.get("claude_model", "") if model == INHERIT else model,
            settings.get("claude_effort", "") if effort == INHERIT else effort)


def limits(settings):
    """(call limit, job limit) in tokens (GÖREV-18)."""
    call = settings.get("claude_call_limit")
    job = settings.get("claude_job_limit")
    return (call if isinstance(call, int) and not isinstance(call, bool) else LIMIT_FIELDS["claude_call_limit"][2],
            job if isinstance(job, int) and not isinstance(job, bool) else LIMIT_FIELDS["claude_job_limit"][2])


def output_guess(settings, step):
    value = settings.get(f"claude_output_guess_{step}")
    return value if isinstance(value, int) and not isinstance(value, bool) else OUTPUT_GUESS_DEFAULTS.get(step, 10_000)


def model_label(model):
    return INHERIT_LABEL if model == INHERIT else MODEL_LABELS.get(model, model)


def effort_label(effort):
    return INHERIT_LABEL if effort == INHERIT else EFFORT_LABELS.get(effort, effort)


def options():
    """The Settings screen's lists."""
    return {"models": [{"value": v, "label": l} for v, l in MODEL_CHOICES], "efforts": [{"value": v, "label": l} for v, l in EFFORT_CHOICES],
            "inherit": {"value": INHERIT, "label": INHERIT_LABEL},
            "steps": [{"key": key, "label": title, "model_field": f"claude_model_{key}", "effort_field": f"claude_effort_{key}",
                       "output_guess_field": f"claude_output_guess_{key}"} for key, title in CLAUDE_STEPS],
            "output_guess": {"min": OUTPUT_GUESS_RANGE[0], "max": OUTPUT_GUESS_RANGE[1], "help": OUTPUT_GUESS_HELP},
            "limits": [{"field": field, "min": low, "max": high, "default": default, "help": LIMIT_HELP[field]}
                       for field, (low, high, default) in LIMIT_FIELDS.items()],
            "text": {"fields": [{"field": field, "min": low, "max": high, "default": default, "help": TEXT_HELP[field]}
                                for field, (low, high, default) in TEXT_FIELDS.items()],
                     "stop_after_plan": {"field": STOP_AFTER_PLAN, "help": TEXT_HELP[STOP_AFTER_PLAN]}}}
