"""Claude usage panel (GÖREV-14, Adım 4a; Housing Atlas's usage gauge, `atlas/claude_usage.py`, taken over in a simpler form).

Source: every `rate_limit_event` Claude Code streams after its answers. Shape (Claude Code, 10 October 2026, seen in this project's own runs):
`rate_limit_info.unifiedWindows.{five_hour,seven_day}.{utilization (0–1), resetsAt (epoch s)}`; the older shape has one window
(`rateLimitType` + `utilization` + `resetsAt`). Each one is stored with its time in `claude_usage` (schema 16): during a step's run by the
runner's `on_rate_limit`, and by the panel's "Yenile" call.

"Yenile" is the smallest call that makes Claude Code report usage: no tools, one turn, the cheapest model family (`haiku`, Claude Code's
newest Haiku) at low effort, a one-word answer; it runs in `<data>/claude/kullanim/` with its own instruction file. It is not made while
a step's Claude run is running or when ANTHROPIC_API_KEY is set (it would bill the API). Settings shows this call and its model.

The panel: the newest measurement's 5-hour and weekly percentages (halves up) and reset times, when it was measured (faded with
"eski ölçüm" after 5 hours; "henüz ölçüm yok" without one), and this week's Claude runs (their number and total duration). "This week" is
the current weekly window (its reset time minus seven days) when a measurement gives one, otherwise the last seven days.
"""
import json
import time
from datetime import datetime, timezone

WINDOWS = ("five_hour", "seven_day")
WINDOW_LABELS = {"five_hour": "5 saatlik", "seven_day": "Haftalık"}
STALE_AFTER_S = 5 * 3600
WEEK_S = 7 * 24 * 3600
REFRESH_MODEL, REFRESH_EFFORT = "haiku", "low"
REFRESH_DIR = ("claude", "kullanim")
REFRESH_PROMPT = "Yalnız şu kelimeyi yaz: tamam\n"
REFRESH_INSTRUCTION = ("Bu, Claude kullanım bilgisini tazelemek için yapılan küçük bir deneme sorgusudur. Hiçbir araç kullanma; yalnız "
                       "istenen tek kelimeyi yaz.\n")
REFRESH_TIMEOUT_S = 120.0
REFRESH_TEXT = ("“Yenile” düğmesi kullanımı en küçük bir Claude çağrısıyla tazeler: araçsız, tek tur, model “haiku” (Claude Code'un en yeni "
                "Haiku modeli), efor düşük, tek kelimelik cevap. Bir adımın Claude çalışması sürerken ve ANTHROPIC_API_KEY tanımlıyken yapılmaz. "
                "Çalışmaların kendisi de her cevaptan sonra kullanımı bildirir; panel o ölçümlerle de güncellenir.")


def number(value):
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def iso(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat(timespec="seconds") if epoch is not None else None


def windows_of(info):
    """{window: (utilization or None, reset epoch or None)} from a `rate_limit_info`."""
    found = {}
    unified = info.get("unifiedWindows") if isinstance(info.get("unifiedWindows"), dict) else None
    if unified:
        for name in WINDOWS:
            window = unified.get(name)
            if isinstance(window, dict):
                reset = number(window.get("resetsAt"))
                found[name] = (number(window.get("utilization")), int(reset) if reset is not None else None)
    elif info.get("rateLimitType") in WINDOWS:
        reset = number(info.get("resetsAt"))
        found[info["rateLimitType"]] = (number(info.get("utilization")), int(reset) if reset is not None else None)
    return found


def record(db, info, *, source, run_id=None):
    """Stores one measurement; an event without a 5-hour or weekly window is not stored (returns None)."""
    if not isinstance(info, dict):
        return None
    found = windows_of(info)
    if not found:
        return None
    seen = number(info.get("seen_at")) or time.time()
    five, week = found.get("five_hour", (None, None)), found.get("seven_day", (None, None))
    clean = {k: v for k, v in info.items() if k != "seen_at"}
    with db.connect() as con:
        cursor = con.execute("""INSERT INTO claude_usage (measured_at,source,run_id,five_hour,five_hour_resets_at,seven_day,seven_day_resets_at,
            status,info) VALUES (?,?,?,?,?,?,?,?,?)""", (iso(seen), source, run_id, five[0], five[1], week[0], week[1],
                                                     str(info.get("status") or "") or None, json.dumps(clean, ensure_ascii=False)))
        return cursor.lastrowid


def percent(utilization):
    return None if utilization is None else int(utilization * 100 + 0.5)


def latest(db):
    with db.connect() as con:
        row = con.execute("SELECT * FROM claude_usage ORDER BY measured_at DESC, id DESC LIMIT 1").fetchone()
    return dict(row) if row else None


def week_runs(db, since_epoch):
    """Claude runs of the steps started since then: their number and total duration (seconds; runs without a measurement add nothing)."""
    with db.connect() as con:
        count, total = con.execute("""SELECT COUNT(*), COALESCE(SUM(json_extract(metrics,'$.elapsed_s')),0) FROM claude_runs
            WHERE created_at >= ?""", (iso(since_epoch),)).fetchone()
    return {"count": count, "total_s": round(total or 0, 1)}


def view(db, now=None):
    now = time.time() if now is None else now
    row = latest(db)
    week_start = now - WEEK_S
    if row and row["seven_day_resets_at"] and row["seven_day_resets_at"] > now:
        week_start = row["seven_day_resets_at"] - WEEK_S
    result = {"measured": bool(row), "week": {**week_runs(db, week_start), "since": iso(week_start),
                                              "basis": "haftalık pencere" if week_start != now - WEEK_S else "son 7 gün"},
              "refresh": {"model": REFRESH_MODEL, "effort": REFRESH_EFFORT, "text": REFRESH_TEXT}}
    if not row:
        return {**result, "text": "henüz ölçüm yok"}
    measured = datetime.fromisoformat(row["measured_at"]).timestamp()
    windows = {}
    for name in WINDOWS:
        utilization, reset = row[name], row[f"{name}_resets_at"]
        passed = reset is not None and reset <= now
        windows[name] = {"label": WINDOW_LABELS[name], "percent": None if passed else percent(utilization), "resets_at": iso(reset),
                         "reset_passed": passed, "known": utilization is not None}
    return {**result, "measured_at": row["measured_at"], "age_s": round(now - measured), "stale": now - measured > STALE_AFTER_S,
            "source": row["source"], "windows": windows}
