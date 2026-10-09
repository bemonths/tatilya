"""Read-time views over dated lodging price snapshots (GÖREV-10): days between the query and each window, our season groups and the
same-week comparison of two runs. Nothing here is stored; every figure is labelled as ours.

Same-week comparison: a listing counts only when it is priced in both runs for a window with the same check-in and check-out dates
(window keys may differ between runs; the dates decide). The change is (later - earlier) / earlier per listing; the region shows the
median change and how many listings were matched.
"""
import statistics

from .windows import SEASON_NOTE, SEASON_ORDER, lead_days, season_of

COMPARISON_NOTE = "aynı evlerin aynı hafta için {first} ve {second} tarihlerinde sorgulanan fiyatları; bizim hesabımız"


def annotate_windows(windows, queried_on):
    """Each window with its month, our season and the days from the query to its first night."""
    return [{**w, "lead_days": lead_days(w["checkin"], queried_on), "season": season_of(w["checkin"]), "month": w["checkin"][:7]} for w in windows]


def season_groups(regions, windows, prices):
    """prices: {(region_id, window_key): [price, ...]} of priced listings -> per region and season the window count, priced count and
    the median price over every priced listing-window pair of that season (our grouping)."""
    rows = []
    for region in regions:
        for season in SEASON_ORDER:
            members = [w for w in windows if w.get("season") == season and w.get("status") in ("queried", "searched")]
            if not members:
                continue
            values = [p for w in members for p in prices.get((region, w["window_key"]), [])]
            rows.append({"region_id": region, "season": season, "window_count": len(members), "priced_count": len(values),
                         "median": round(statistics.median(values), 2) if values else None})
    return {"rows": rows, "note": SEASON_NOTE}


def compare(regions, earlier, later, earlier_on, later_on):
    """earlier / later: {"windows": [...], "prices": {(lodging_id, window_key): price}, "members": {region_id: {lodging_id, ...}}}.
    Windows are matched by dates; returns per region x matched window the matched listing count and the median change."""
    by_dates = {(w["checkin"], w["checkout"]): w for w in earlier["windows"]}
    pairs = [(by_dates[(w["checkin"], w["checkout"])], w) for w in later["windows"] if (w["checkin"], w["checkout"]) in by_dates]
    rows = []
    for region in regions:
        members = later["members"].get(region, set())
        for old, new in pairs:
            changes, amounts = [], []
            for lodging_id in members:
                before = earlier["prices"].get((lodging_id, old["window_key"]))
                after = later["prices"].get((lodging_id, new["window_key"]))
                if before and after is not None:
                    changes.append((after - before) / before)
                    amounts.append(after - before)
            rows.append({"region_id": region, "window_key": new["window_key"], "earlier_window_key": old["window_key"],
                         "checkin": new["checkin"], "checkout": new["checkout"], "matched_count": len(changes),
                         "median_change": round(statistics.median(changes), 4) if changes else None,
                         "median_amount": round(statistics.median(amounts), 2) if amounts else None})
    return {"windows": [{"window_key": new["window_key"], "label": new.get("label"), "earlier_label": old.get("label"), "checkin": new["checkin"],
                         "checkout": new["checkout"]} for old, new in pairs],
            "rows": rows, "label": COMPARISON_NOTE.format(first=earlier_on, second=later_on)}
