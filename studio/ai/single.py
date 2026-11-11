"""One Claude call per step (GÖREV-18): the material inside the task text, no tools, one turn, the answer is the output's JSON.

Housing Atlas's way (`atlas/article/service.py` `_session` / `_ask`, `atlas/article/prompts.py` `parse_json`, TASARIM 21, KARARLAR "Çeviri"
and "Uzun metin ve kesik cevap"): `--tools ""`, `--max-turns 1`, the combined instructions in `--append-system-prompt-file`, the task on
standard input; the program takes the JSON out of the answer (bare, in a code fence or with text around it), checks it and writes the output
file itself. Before GÖREV-18 every step read its input files one by one with `Read` and wrote its output with `Write`; a title run read its
~90 thousand tokens of material five or six times (once per turn), ~450 thousand in all.

The task text (`gorev.md`) is: the program's preface (fixed text, not an instruction file), the step's own task lines, then every input
file the step's preparation wrote into the run folder, each between `<<<DOSYA name>>>` and `<<<DOSYA SONU name>>>` lines with exactly the
file's text. The files stay in the folder for the record; Claude does not open them. Nothing is cut or summarised: a task text too large
for the call limit is not sent (the step says why).

Token estimate: characters ÷ `CHARS_PER_TOKEN` plus Claude Code's own system text (`OVERHEAD_TOKENS`; the usage panel's tool-less one-turn
calls on this computer read 4,038–4,166 input tokens for a two-line instruction and a one-line task). The divisor is calibrated on the one
real call of GÖREV-18 (see the report); it is a rough figure for the screens, the real count comes from Claude's answer.
"""
import json
import math
import re

PREFACE = ("Talimatta adı geçen dosyalar aşağıda, her biri kendi adıyla verilmiştir; başka dosya yoktur ve dosya açman gerekmez. "
           "Çıktını bir dosyaya yazma: cevabın yalnızca şemaya uyan JSON olsun, başına ya da sonuna başka bir şey ekleme.")
OPEN, CLOSE = "<<<DOSYA {name}>>>", "<<<DOSYA SONU {name}>>>"
SECTION = re.compile(r"^<<<DOSYA (?P<name>[^>\n]+)>>>\n(?P<body>.*?)\n<<<DOSYA SONU (?P=name)>>>$", re.S | re.M)
RETRY_HEADER = "DÖNÜŞ SEBEBİ"
PREVIOUS_ANSWER = "onceki_cevap.txt"
CHARS_PER_TOKEN = 2.3
OVERHEAD_TOKENS = 4_500
TRUNCATED = re.compile(r"output token maximum|exceeded the \d+ output token|max_output_tokens", re.I)
TRUNCATED_TEXT = "cevap uzunluk sınırında kesildi"
ANSWER_FILE = "cevap{n}.txt"


class AnswerError(ValueError):
    """Claude's answer cannot be used; the message is Turkish."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class TooLarge(ValueError):
    """The task text is over the call limit: the call is not made."""

    def __init__(self, message, estimate):
        super().__init__(message)
        self.message, self.estimate = message, estimate


# ------------------------------------------------------------------------------------------------------------------- the task text

def read_input(folder, name):
    """An input file as the step wrote it (UTF-8; a byte order mark of a copied file is not part of the text)."""
    return (folder / name).read_text(encoding="utf-8-sig")


def sections(folder, inputs):
    """[(name, text)] of the run's input files, in the order the preparation wrote them."""
    return [(item["dosya"], read_input(folder, item["dosya"])) for item in inputs]


def section_text(name, text):
    return "\n".join([OPEN.format(name=name), text.rstrip("\n"), CLOSE.format(name=name)])


def task_text(task, parts, *, retry=None):
    """The whole task text: preface, the step's task lines, the files; on a second try the reason and the previous answer at the end."""
    out = [PREFACE, "", task.rstrip("\n"), ""]
    for name, text in parts:
        out += [section_text(name, text), ""]
    if retry:
        out += [RETRY_HEADER, retry["reason"].strip(), ""]
        if retry.get("previous") is not None:
            out += ["Önceki cevabın aşağıda; bu sebebe göre baştan ve eksiksiz yeniden yaz.", "",
                    section_text(PREVIOUS_ANSWER, retry["previous"]), ""]
    return "\n".join(out)


def parsed_sections(text):
    """{name: text} of a task text's file sections (the tests and the fake Claude read the task text back with this)."""
    return {m.group("name"): m.group("body") for m in SECTION.finditer(text or "")}


# ------------------------------------------------------------------------------------------------------------------- size

def tokens_of(chars):
    return int(math.ceil(max(0, chars) / CHARS_PER_TOKEN))


def prompt_tokens(system_text, task):
    """Rough input tokens of one call: the combined instructions, the task text and Claude Code's own system text."""
    return tokens_of(len(system_text or "") + len(task or "")) + OVERHEAD_TOKENS


def parts_table(system_parts, task_preface, file_parts):
    """The measurement table of one call (GÖREV-18 Adım 3): every part's characters and estimated tokens."""
    rows = [{"parca": name, "karakter": len(text), "token": tokens_of(len(text))} for name, text in system_parts]
    rows.append({"parca": "görev metni (önsöz ve adımın satırları)", "karakter": len(task_preface), "token": tokens_of(len(task_preface))})
    rows += [{"parca": name, "karakter": len(text), "token": tokens_of(len(text))} for name, text in file_parts]
    rows.append({"parca": "Claude Code'un kendi sistem metni (ölçülen, yaklaşık)", "karakter": None, "token": OVERHEAD_TOKENS})
    return rows


def check_size(estimate, limit, label):
    """TooLarge when one call's estimate (read + written) is over the call limit."""
    if estimate["toplam"] > limit:
        raise TooLarge(f"{label}: tek çağrı tahmini yaklaşık {thousands(estimate['toplam'])} token (okunacak {thousands(estimate['okunan'])}, "
                       f"yazılacak {thousands(estimate['yazilan'])}); Ayarlar → Claude'daki tek çağrı sınırı {thousands(limit)}. Program "
                       "malzemeyi kendiliğinden kısaltmaz; çalışma başlatılmadı.", estimate)


def thousands(value):
    """"85 bin", "1,2 milyon"."""
    value = int(value or 0)
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}".replace(".", ",").replace(",0", "") + " milyon"
    return f"{max(0, round(value / 1000))} bin" if value >= 1000 else str(value)


# ------------------------------------------------------------------------------------------------------------------- the answer

_FENCED = re.compile(r"^```[^\n`]*\n(.*?)\n?```$", re.S)
_INNER_FENCE = re.compile(r"```[A-Za-z0-9_-]*[ \t]*\n(.*?)```", re.S)


def json_object(text):
    try:
        data = json.loads(text)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def parse_json(text):
    """The JSON object of an answer: bare, in a code fence, or with text before or after it (Housing Atlas's rule)."""
    value = (text or "").strip()
    if not value:
        raise AnswerError("Claude boş cevap verdi.")
    candidates = [value]
    fenced = _FENCED.match(value) or _INNER_FENCE.search(value)
    if fenced:
        candidates.append(fenced.group(1).strip())
    for candidate in list(candidates):
        start, end = candidate.find("{"), candidate.rfind("}")
        if 0 <= start < end:
            candidates.append(candidate[start:end + 1])
    for candidate in candidates:
        data = json_object(candidate)
        if data is not None:
            return data
    raise AnswerError("Cevap okunabilir bir JSON nesnesi değil (geçersiz cevap).")


def answer_text(result):
    envelope = getattr(result, "envelope", None) or {}
    text = envelope.get("result")
    return text if isinstance(text, str) else ""


def truncated(result):
    """Was the answer cut at the output limit? The envelope's `stop_reason` "max_tokens", or Claude Code's output-limit message."""
    if result is None:
        return False
    envelope = getattr(result, "envelope", None) or {}
    if envelope.get("stop_reason") == "max_tokens":
        return True
    texts = [str(envelope.get("result") or "")]
    failure = getattr(result, "failure", None)
    if failure is not None:
        texts += [failure.message or "", failure.detail or ""]
    return any(TRUNCATED.search(t) for t in texts if t)


def max_output(result):
    """The model's output limit Claude Code ran with (the envelope's `modelUsage.<model>.maxOutputTokens`), or None."""
    usage = ((getattr(result, "envelope", None) or {}).get("modelUsage") or {})
    values = [v.get("maxOutputTokens") for v in usage.values() if isinstance(v, dict) and isinstance(v.get("maxOutputTokens"), int)]
    return max(values) if values else None


# ------------------------------------------------------------------------------------------------------------------- spending

def token_total(metrics):
    """Read (input, cache creation, cache read) and written tokens of one call's metrics: (read, written)."""
    tokens = (metrics or {}).get("tokens") or {}
    read = sum(int(tokens.get(k) or 0) for k in ("input", "cache_creation", "cache_read"))
    return read, int(tokens.get("output") or 0)


def spent(metrics_list):
    """{"okunan", "yazilan", "toplam", "cagri", "maliyet_usd"} of several calls."""
    read = written = calls = 0
    cost = 0.0
    for metrics in metrics_list:
        if not metrics:
            continue
        r, w = token_total(metrics)
        read, written, calls = read + r, written + w, calls + 1
        cost += float(metrics.get("cost_usd") or 0)
    return {"okunan": read, "yazilan": written, "toplam": read + written, "cagri": calls, "maliyet_usd": round(cost, 4)}


OVER_FACTOR = 1.5


def comparison(estimate, actual):
    """Estimate and actual side by side; `fazla` when the actual is over 1.5 × the estimate (the red warning)."""
    if not estimate or not actual:
        return None
    over = actual["toplam"] > OVER_FACTOR * max(1, estimate["toplam"])
    text = f"tahmin {thousands(estimate['toplam'])}, gerçek {thousands(actual['toplam'])} token"
    return {"tahmin": estimate["toplam"], "gercek": actual["toplam"], "fazla": over, "metin": text,
            "uyari": f"Beklenenden fazla harcandı: {text}." if over else None}
