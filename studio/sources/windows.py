"""Date windows for lodging price snapshots from a destination's window rule (an assumption of ours, not a fact of any source).

Monthly rule (GÖREV-10): for each of the months after the run month, the Saturday-to-Saturday week that contains the anchor day
(the 15th): it starts on the Saturday on or before the 15th, so it always lies between the 9th and the 22nd of that month. A week
that starts fewer than min_lead_days days after the run date is skipped and the next month is added, so every run asks the same
number of windows. The key names the month ("ay-2027-07"), so the same week of two runs can be compared.
"""
from datetime import date, timedelta

TR_MONTHS = ("Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık")
SEASONS = {12: "kış", 1: "kış", 2: "kış", 3: "ilkbahar", 4: "ilkbahar", 5: "ilkbahar", 6: "yaz", 7: "yaz", 8: "yaz",
           9: "sonbahar", 10: "sonbahar", 11: "sonbahar"}
SEASON_ORDER = ("kış", "ilkbahar", "yaz", "sonbahar")
SEASON_NOTE = "Mevsim grupları bizim gruplamamızdır: Aralık–Şubat kış, Mart–Mayıs ilkbahar, Haziran–Ağustos yaz, Eylül–Kasım sonbahar."
DEFAULT_RULE = {"kind": "monthly", "months": 12, "anchor_day": 15, "weekday": 5, "nights": 7, "min_lead_days": 21}


def add_months(year, month, count):
    index = year * 12 + (month - 1) + count
    return index // 12, index % 12 + 1


def monthly_windows(today, rule=None):
    """[{'window_key', 'label', 'checkin', 'checkout', 'month'}] for the rule's number of months after today's month."""
    rule = {**DEFAULT_RULE, **(rule or {})}
    if rule["kind"] != "monthly":
        raise ValueError(f"Bilinmeyen pencere kuralı: {rule['kind']}")
    windows, offset = [], 0
    while len(windows) < rule["months"]:
        offset += 1
        if offset > rule["months"] + 24:
            break
        year, month = add_months(today.year, today.month, offset)
        anchor = date(year, month, rule["anchor_day"])
        checkin = anchor - timedelta(days=(anchor.weekday() - rule["weekday"]) % 7)
        checkout = checkin + timedelta(days=rule["nights"])
        if (checkin - today).days < rule["min_lead_days"]:
            continue
        name = TR_MONTHS[month - 1]
        span = (f"{checkin.day}–{checkout.day} {name}" if checkin.month == checkout.month else
                f"{checkin.day} {TR_MONTHS[checkin.month - 1]}–{checkout.day} {TR_MONTHS[checkout.month - 1]}")
        windows.append({"window_key": f"ay-{year}-{month:02d}", "label": f"{name} {year} · {span}", "checkin": checkin.isoformat(),
                        "checkout": checkout.isoformat(), "month": f"{year}-{month:02d}"})
    return windows


def rule_text(rule):
    rule = {**DEFAULT_RULE, **(rule or {})}
    return (f"Pencere kuralı (bizim varsayımımız, kaynak gerçeği değil): çekim ayından sonraki {rule['months']} ayın her biri için ayın "
            f"{rule['anchor_day']}'ini içeren Cumartesi–Cumartesi haftası ({rule['nights']} gece); başlangıcı çekim tarihine "
            f"{rule['min_lead_days']} günden yakın olan pencere atlanır ve yerine bir sonraki ay eklenir.")


def season_of(checkin):
    return SEASONS[date.fromisoformat(checkin).month]


def lead_days(checkin, queried_on):
    """Days between the query date and the window's first night (None when either is unknown)."""
    try:
        return (date.fromisoformat(checkin) - date.fromisoformat(str(queried_on)[:10])).days
    except (TypeError, ValueError):
        return None
