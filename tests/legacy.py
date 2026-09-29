"""v0.2 gerçek tablo sözleşmesiyle oluşturulan sentetik migration girdisi."""
import json
import sqlite3
from pathlib import Path

from studio.sources.beaches import SOURCE_URL


def make_legacy_db(path, version=2):
    with sqlite3.connect(path) as con:
        con.executescript((Path(__file__).parent / "fixtures/v02-schema.sql").read_text(encoding="utf-8"))
        con.execute("INSERT INTO metadata VALUES ('seeded','2026-09-01')")
        con.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
            "source-a", "Kullanıcının değiştirdiği ad", SOURCE_URL, "Plaj", "Tüm 30A", "JSON", "Gerektiğinde",
            "Kullanıcı notu korunmalı", 0, 4, "2026-09-01", "2026-09-02"))
        con.execute("INSERT INTO source_history(source_id,saved_at,snapshot) VALUES (?,?,?)", (
            "source-a", "2026-09-02", json.dumps({"name": "Kullanıcının değiştirdiği ad", "version": 4})))
        for identifier, status in (("old-success", "done"), ("old-failed", "failed"), ("old-canceled", "canceled")):
            con.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?)", (
                identifier, "beach_collection", "Eski toplama", status, 100 if status == "done" else 10,
                "Eski iş mesajı", "2026-09-01", "2026-09-02", '{"included":1}' if status == "done" else None,
                '[{"at":"2026-09-01","text":"Eski günlük"}]'))
        con.execute("INSERT INTO collections VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
            "old-success", "source-a", SOURCE_URL, "2026-09-02", "Kaynak zamanı", "south-walton-beaches/1",
            2, 1, 1, "raw/old-success/source.html", "abc123", "Eski kapsam kuralı"))
        con.execute("INSERT INTO beach_records VALUES (?,?,?,?,?,?,?,?,?)", (
            "old-success", "external-1", "Eski plaj", "Santa Rosa Beach", "Kaynak adresi", 30.35, -86.14,
            "regional", '["Parking"]'))
        if version == 1:
            con.execute("DROP TABLE beach_records")
            con.execute("DROP TABLE collections")
        con.execute(f"PRAGMA user_version={version}")
    raw = path.parent / "raw/old-success/source.html"
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_text("Sentetik eski ham kaynak", encoding="utf-8")
