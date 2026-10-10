"""The fake Claude's video text steps (GÖREV-15; used by `tests/fake_claude.py`). The tests never call Claude.

Every step (`Adım: metin_…` in the task) writes an output that fits its schema, with evidence marks taken from the run folder's files:
- metin_plan: 6 sections from `paket_ozeti.md`'s K ids (budgets 350 each, openings never the same twice in a row), one concept, two
  re-hooks (after sections 2 and 4), a promise check;
- metin_plan_elestiri: a short note, `yeniden_yap` false;
- metin_bolum: the section of `Bölüm: N` (its ids from `bolum.md`), about its budget in words; section 1 has "amazing" (a yellow voice
  warning), section 3 "within walking distance" (a red distance rule);
- metin_birlestirme: a transition between every two neighbouring sections and the plan's re-hooks;
- metin_giris_kapanis: one paragraph each, no suggested video;
- metin_son_okuma: one correction of sentence 2 that keeps its marks;
- metin_ceviri: "TR: <English>" for every numbered sentence (digits kept) and one term.

FAKE_CLAUDE_TEXT (comma-separated directives) brings trouble; a directive with a count acts on that many calls of its step (default 1):
- `plan_bad_id` (the first plan cites K9999), `plan_bad_id_always`, `critic_redo` (the first critique says `yeniden_yap`);
- `invalid:<step>[:n]` (an output that breaks the schema), `transient:<step>[:n]` (Claude's 529 "Overloaded"), `limit:<step>[:n]` (a usage
  limit: a refused `rate_limit_event` with its reset in FAKE_CLAUDE_LIMIT_RESET seconds, default 60, and Claude's limit message),
  `final_lose_mark` (the correction drops the sentence's marks), `translate_missing` (the first translation leaves out the last number).
Counts are kept in FAKE_CLAUDE_STATE (a JSON file); FAKE_CLAUDE_LOG (a JSONL file) gets {step, start, end} of every text session (for
the parallel sessions' test). FAKE_CLAUDE_SLEEP with the scenario "slow" makes every session wait.
"""
import json
import os
import re
import time
from pathlib import Path

OUTPUTS = {"metin_plan": "plan.json", "metin_plan_elestiri": "plan_elestirisi.json", "metin_bolum": "bolum.json",
           "metin_birlestirme": "birlestirme.json", "metin_giris_kapanis": "giris_kapanis.json", "metin_son_okuma": "son_okuma.json",
           "metin_ceviri": "ceviri.json"}
OPENINGS = ("rakam", "sahne", "soru", "gecmis", "karsilastirma", "diger")
FILLER = ("Here is what the record shows for this part of the coast", "That matters when you weigh one week against another",
          "The source says it plainly and we keep to its words", "You can read it as a guide rather than a promise",
          "It is the kind of detail that changes a plan", "Nothing here claims more than the evidence carries")


def directives():
    out = {}
    for item in filter(None, (os.environ.get("FAKE_CLAUDE_TEXT") or "").split(",")):
        parts = item.strip().split(":")
        name = parts[0]
        if name in ("invalid", "transient", "limit"):
            out[(name, parts[1])] = int(parts[2]) if len(parts) > 2 else 1
        else:
            out[(name, None)] = 1
    return out


def take(name, step=None):
    """True (and counted) when a directive still has calls left for this step."""
    wanted = directives().get((name, step))
    if not wanted:
        return False
    if name == "plan_bad_id_always":
        return True
    path = os.environ.get("FAKE_CLAUDE_STATE")
    state = {}
    if path and Path(path).is_file():
        state = json.loads(Path(path).read_text(encoding="utf-8") or "{}")
    key = f"{name}:{step}"
    used = state.get(key, 0)
    if used >= wanted:
        return False
    state[key] = used + 1
    if path:
        Path(path).write_text(json.dumps(state), encoding="utf-8")
    return True


def ids_in(path):
    if not path.is_file():
        return []
    return list(dict.fromkeys(re.findall(r"\bK\d{4}\b", path.read_text(encoding="utf-8"))))


def task_value(prompt, name):
    found = re.search(rf"^{name}: (.+)$", prompt, re.M)
    return found.group(1).strip() if found else None


def plan(cwd, prompt):
    ids = ids_in(cwd / "paket_ozeti.md") or ["K0001"]
    sections = []
    for number in range(1, 7):
        cited = [ids[(number * 2 - 2) % len(ids)], ids[(number * 2 - 1) % len(ids)]]
        sections.append({"no": number, "ic_adi": f"Bölüm {number}", "tek_fikir": f"{number}. bölümün tek fikri.",
                         "en_carpici_an": f"{number}. bölümün en çarpıcı anı.", "kanitlar": list(dict.fromkeys(cited)), "kelime_butcesi": 350,
                         "acilis_bicimi": OPENINGS[(number - 1) % len(OPENINGS)], "acilis_notu": "Açılış notu."})
    retry = "DÖNÜŞ SEBEBİ" in prompt
    if take("plan_bad_id_always") or (not retry and take("plan_bad_id")):
        sections[0]["kanitlar"] = ["K9999"]
    return {"surum": 1, "adim": "metin_plan", "bolumler": sections, "kavramlar": [{"kavram": "customary use", "bolum": 2}],
            "yeniden_kancalar": [{"bolumden_sonra": 2, "uzerine": "kanca 1"}, {"bolumden_sonra": 4, "uzerine": "kanca 2"}],
            "vaat_kontrolu": {"karsilanan": [{"vaat": "Başlığın sorusu", "bolumler": [1, 6]}], "karsilanamayan": []},
            "notlar": ["Sahte plan" + (" (yeniden)" if retry else "") + "."]}


def critique(cwd, prompt):
    redo = take("critic_redo")
    return {"surum": 1, "adim": "metin_plan_elestiri", "notlar": ["Merak üçüncü bölümde kopuyor."] if redo else ["Plan iyi."], "yeniden_yap": redo}


def section(cwd, prompt):
    number = int(task_value(prompt, "Bölüm") or 1)
    text = (cwd / "bolum.md").read_text(encoding="utf-8") if (cwd / "bolum.md").is_file() else ""
    ids = re.findall(r"^- (K\d{4}) \(planın gösterdiği\)", text, re.M) or re.findall(r"^- (K\d{4})", text, re.M) or ["K0001"]
    budget = int((re.search(r"Kelime bütçesi: yaklaşık (\d+)", text) or [None, "350"])[1])
    tone = task_value(prompt, "Ton") or ""
    sentences, words, index = [], 0, sum(map(ord, tone)) % len(FILLER)      # each tone starts its filler elsewhere
    if number == 1:
        sentences.append(f"It is an amazing place to start the story [{ids[0]}].")
    if number == 3:
        sentences.append(f"Most homes sit within walking distance of the sand [{ids[0]}].")
    while words < budget - 12:
        mark = ids[index % len(ids)]
        sentence = f"{FILLER[index % len(FILLER)]} in this part [{mark}]."
        sentences.append(sentence)
        words += len(sentence.split()) - 1
        index += 1
    paragraphs = [" ".join(sentences[i:i + 6]) for i in range(0, len(sentences), 6)]
    return {"surum": 1, "adim": "metin_bolum", "bolum_no": number, "paragraflar": paragraphs, "yazici_notu": None}


def merge(cwd, prompt):
    data = json.loads((cwd / "plan.json").read_text(encoding="utf-8"))
    numbers = sorted(s["no"] for s in data["bolumler"])
    return {"surum": 1, "adim": "metin_birlestirme",
            "gecisler": [{"onceki_bolum": a, "sonraki_bolum": b, "metin": "From here we turn to what the next part shows."}
                         for a, b in zip(numbers, numbers[1:])],
            "yeniden_kancalar": [{"bolumden_sonra": h["bolumden_sonra"], "metin": "Stay with us, the next part answers the question you came with."}
                                 for h in data.get("yeniden_kancalar") or []],
            "notlar": []}


STYLES = {"Araştırmacı dost": "a friend who did the reading", "Hikâye anlatıcısı": "a story told in order", "Pratik planlayıcı": "a plan with the numbers first",
          "Belgesel anlatıcı": "a slow documentary", "Vlogger": "a quick chat"}


def ends(cwd, prompt):
    ids = ids_in(cwd / "metin.md") or ["K0001"]
    style = STYLES.get(task_value(prompt, "Ton") or "", "a plain text")
    intro = " ".join(["You came here with one question and this text, told as {}, answers it with the records we found [{}].".format(style, ids[0]),
                      "We go through it part by part and keep to what the sources say [{}].".format(ids[-1])] + [
        "Every claim you hear rests on a record you could open yourself."] * 4)
    closing = " ".join(["That is what the records show and the choice is yours [{}].".format(ids[0]),
                        "If this helped, subscribing is the simplest way to see the next one."] + ["Take the parts that fit your trip."] * 6)
    return {"surum": 1, "adim": "metin_giris_kapanis", "giris": [intro], "kapanis": [closing], "onerilen_video": None}


def final_read(cwd, prompt):
    text = (cwd / "metin.md").read_text(encoding="utf-8") if (cwd / "metin.md").is_file() else ""
    line = re.search(r"^\[2\] (.+)$", text, re.M)
    if not line:
        return {"surum": 1, "adim": "metin_son_okuma", "duzeltmeler": []}
    sentence = line.group(1)
    new = "Indeed, " + sentence[0].lower() + sentence[1:]
    if take("final_lose_mark"):
        new = re.sub(r"\s*\[K\d{4}(?:, K\d{4})*\]", "", new)
    return {"surum": 1, "adim": "metin_son_okuma", "duzeltmeler": [{"no": 2, "yeni": new, "gerekce": "Açılış daha doğal."}]}


def translate(cwd, prompt):
    text = (cwd / "cumleler.md").read_text(encoding="utf-8") if (cwd / "cumleler.md").is_file() else ""
    items = [{"no": int(n), "tr": f"TR: {s}", "uyari": None} for n, s in re.findall(r"^\[(\d+)\] (.+)$", text, re.M)]
    if items and "DÖNÜŞ SEBEBİ" not in prompt and take("translate_missing"):
        items = items[:-1]
    if items:
        items[0]["uyari"] = "Sahte çevirmen uyarısı."
    return {"surum": 1, "adim": "metin_ceviri", "cumleler": items, "terimler": [{"en": "walkover", "tr": "walkover",
                                                                               "aciklama": "Kumulun üstünden plaja geçen yol."}]}


BUILDERS = {"metin_plan": plan, "metin_plan_elestiri": critique, "metin_bolum": section, "metin_birlestirme": merge, "metin_giris_kapanis": ends,
            "metin_son_okuma": final_read, "metin_ceviri": translate}


def step_of(prompt):
    found = re.search(r"^Adım: (metin_[a-z_]+)$", prompt, re.M)
    return found.group(1) if found else None


def trouble(step, prompt):
    """("transient"|"limit"|None) for this call."""
    if take("transient", step):
        return "transient"
    if take("limit", step):
        return "limit"
    return None


def output(step, cwd, prompt):
    data = BUILDERS[step](cwd, prompt)
    if take("invalid", step):                          # counted calls: the retry is invalid too while the count lasts
        data = {"surum": 1, "adim": step}            # misses the required fields: the schema refuses it
    return data


def log_session(step, start, end):
    path = os.environ.get("FAKE_CLAUDE_LOG")
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"step": step, "start": start, "end": end}) + "\n")


def now():
    return time.time()
