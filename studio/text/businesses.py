"""Business-name check (GÖREV-18 Adım 6a; the user's decision of 11 November 2026): no brand, restaurant, hotel or other business is named
in a video; they are spoken of in general. The check stops nobody: it shows a red finding.

The list is built again from the data at every check (`names`):
- restaurants (`restaurant_records`),
- rental companies (the destination's agency sites and the companies of the rate runs),
- lodging businesses: listings of the hotel, bed & breakfast inn and rental agency categories (`lodging_listings`; beach homes and
  condominiums are single properties, not businesses, and are not taken),
- daily-needs businesses: markets, pharmacies, private health points and the other points of the daily-needs runs (`poi_points`, their
  names and brands).
Left out: community and place names (the destination's regions and neighborhood records, the destination's own name), public bodies and
official sources (a name with County, State Park, State Forest, City of, Department, Sheriff, Post Office, Library, "Visit South Walton",
NOAA, FDOT …), parks and beach accesses, events. A business whose name is a place name ("Rosemary Beach®" the rental company) is not taken:
the place name itself is never marked. A business whose name only contains a place name ("Rosemary Beach Realty") is marked only for its
whole name. Variants: without ® and ™, without a leading "The", the part before " - " or " at " ("The Perfect Pig - Gulf Place" → "The
Perfect Pig"). Names under four letters are not taken (too many false hits).

Settings → Uyarı ifadeleri → "İşletme adları: ekle / hariç tut" edits `isletme_adlari.txt` (lines "+ Ad" and "- Ad").
"""
import re
import unicodedata

MIN_LETTERS = 4
PUBLIC = re.compile(r"\b(?:county|state park|state forest|national|city of|department|sheriff|post office|library|visit south walton|"
                    r"tourist development|noaa|fdot|beach access|regional|public|school|university|church|chamber of commerce)\b", re.I)
LODGING_CATEGORIES = ("Hotels", "Bed & Breakfast Inns", "Rental Agencies")
APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "`": "'", "´": "'"})
MARKS = re.compile(r"[®™©]")


def clean(name):
    text = MARKS.sub("", unicodedata.normalize("NFKC", name or "")).translate(APOSTROPHES)
    return " ".join(text.split()).strip(" -–—,.;:")


def key(name):
    return clean(name).casefold()


def variants(name):
    """The forms a name is searched in."""
    base = clean(name)
    found = {base}
    for separator in (" - ", " – ", " — ", " at "):
        if separator in base:
            found.add(base.split(separator)[0].strip())
    for item in list(found):
        if item.lower().startswith("the "):
            found.add(item[4:])
    return {v for v in found if sum(ch.isalpha() for ch in v) >= MIN_LETTERS}


def read_overrides(path):
    """(added, excluded) names of `isletme_adlari.txt`."""
    added, excluded = [], set()
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines() if path else []
    except OSError:
        lines = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("+"):
            if clean(line[1:]):
                added.append(clean(line[1:]))
        elif line.startswith("-"):
            if clean(line[1:]):
                excluded.add(key(line[1:]))
    return added, excluded


def place_names(db, destination_id):
    with db.connect() as con:
        regions = [r[0] for r in con.execute("SELECT name FROM regions WHERE destination_id=?", (destination_id,))]
        hoods = [r[0] for r in con.execute("""SELECT DISTINCT n.name FROM neighborhood_records n JOIN source_runs r ON r.id=n.run_id
            WHERE r.destination_id=?""", (destination_id,))]
        own = [r[0] for r in con.execute("SELECT name FROM destinations WHERE id=?", (destination_id,))]
    return {key(n) for n in [*regions, *hoods, *own, "30A", "South Walton", "Florida", "Walton County"] if n}


def data_names(db, destination_id):
    """[(name, kind)] of the businesses in the data."""
    out = []
    with db.connect() as con:
        def rows(sql, *args):
            try:
                return con.execute(sql, args).fetchall()
            except Exception:                              # a table an older schema does not have
                return []
        out += [(r[0], "restoran") for r in rows("""SELECT DISTINCT x.name FROM restaurant_records x JOIN source_runs r ON r.id=x.run_id
            WHERE r.destination_id=?""", destination_id)]
        out += [(r[0], "kiralama şirketi") for r in rows("SELECT company FROM destination_agency_sites WHERE destination_id=?", destination_id)]
        out += [(r[0], "kiralama şirketi") for r in rows("""SELECT DISTINCT x.company FROM agency_rate_companies x JOIN source_runs r
            ON r.id=x.run_id WHERE r.destination_id=?""", destination_id)]
        for title, categories in rows("""SELECT DISTINCT x.title, x.category_names FROM lodging_listings x JOIN source_runs r ON r.id=x.run_id
            WHERE r.destination_id=?""", destination_id):
            names = categories or ""
            if any(f'"{c}"' in names for c in LODGING_CATEGORIES):
                out.append((title, "konaklama işletmesi"))
        for name, brand, category in rows("""SELECT DISTINCT x.name, x.brand, x.category_key FROM poi_points x JOIN source_runs r
            ON r.id=x.run_id WHERE r.destination_id=?""", destination_id):
            out += [(n, "günlük ihtiyaç") for n in (name, brand) if n]
    return [(n, kind) for n, kind in out if n]


def names(db, destination_id, overrides_path=None):
    """{search form (casefolded): display name} of the business names the check looks for, built from the data now."""
    places = place_names(db, destination_id)
    added, excluded = read_overrides(overrides_path)
    found = {}
    for name, _kind in [*data_names(db, destination_id), *((n, "elle eklenen") for n in added)]:
        display = clean(name)
        if not display or key(display) in places or key(display) in excluded or PUBLIC.search(display):
            continue
        for form in variants(display):
            if key(form) in places or key(form) in excluded:
                continue
            found.setdefault(key(form), display)
    return found


class Matcher:
    """Names of two or more words match without regard to case; a one-word name ("Target", "Lookout", "Citizen" …, often also an
    ordinary English word) only with its capital letter as the data writes it."""

    def __init__(self, table):
        self.table = table
        many = sorted((f for f in table if " " in f), key=len, reverse=True)
        one = sorted({clean(table[f]) if key(table[f]) == f else self.spelled(f) for f in table if " " not in f}, key=len, reverse=True)
        body = lambda forms: "|".join(re.escape(f).replace(r"\ ", r"\s+") for f in forms)
        self.many = re.compile(r"(?<![\w'])(" + body(many) + r")(?![\w])", re.I) if many else None
        self.one = re.compile(r"(?<![\w'])(" + body(one) + r")(?![\w])") if one else None

    def spelled(self, form):
        """A one-word variant as written in its display name ("Lookout" of "The Lookout")."""
        display = clean(self.table[form])
        found = next((w for w in display.split() if w.casefold() == form), None)
        return found or form.capitalize()

    def find(self, text):
        """The business names in a text, each once, in order of appearance: [display name]."""
        text = clean(text)
        hits = []
        for pattern in (self.many, self.one):
            if pattern is None or not text:
                continue
            for match in pattern.finditer(text):
                name = self.table.get(" ".join(match.group(1).split()).casefold())
                if name:
                    hits.append((match.start(), name))
        out = []
        for _, name in sorted(hits):
            if name not in out:
                out.append(name)
        return out


def matcher(db, destination_id, profile=None):
    path = ((getattr(profile, "TEXT", None) or {}).get("business_names")) if profile is not None else None
    return Matcher(names(db, destination_id, path))
