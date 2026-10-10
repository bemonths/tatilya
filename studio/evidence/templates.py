"""Evidence-pack templates: JSON files on the destination side (one template per file), read and validated here.

A template has a key, version, title, the video's main question, optional dimensions for later combinations (region × decision ×
period × traveller type), parameters (only "region" for now: one of the destination's canonical regions) and sections. Each section
has a question and the data blocks it uses; a block spec may refer to a parameter as "{key}" (the region id) or "{key_adi}" (its
name), which is filled in when the pack is generated.
"""
import json
import re
from pathlib import Path

KEY = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
PARAMETER_KINDS = {"region": "Mahalle"}
DIMENSIONS = ("bolge", "karar", "donem", "gezgin_tipi")


class TemplateError(ValueError):
    """User-facing reason why a template file cannot be used."""


def read(path, blocks):
    """One validated template; `blocks` is the set of known data block keys."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise TemplateError(f"Şablon dosyası okunamadı: {Path(path).name}.") from exc
    name = Path(path).name
    if not isinstance(data, dict):
        raise TemplateError(f"Şablon bir nesne olmalı: {name}.")
    for field in ("key", "version", "title", "question", "sections"):
        if not data.get(field):
            raise TemplateError(f"Şablonda '{field}' eksik: {name}.")
    if not KEY.fullmatch(str(data["key"])):
        raise TemplateError(f"Şablon anahtarı yalnız küçük harf, rakam ve tire içerebilir: {name}.")
    dimensions = data.get("dimensions") or {}
    if not isinstance(dimensions, dict) or set(dimensions) - set(DIMENSIONS):
        raise TemplateError(f"Şablon boyutları yalnız {', '.join(DIMENSIONS)} olabilir: {name}.")
    parameters = data.get("parameters") or []
    keys = set()
    for parameter in parameters:
        if not isinstance(parameter, dict) or not KEY.fullmatch(str(parameter.get("key", ""))) or parameter.get("kind") not in PARAMETER_KINDS:
            raise TemplateError(f"Şablon parametresi geçersiz (anahtar ve tür 'region' olmalı): {name}.")
        keys.add(parameter["key"])
    sections, seen = data["sections"], set()
    if not isinstance(sections, list):
        raise TemplateError(f"Şablon bölümleri liste olmalı: {name}.")
    for section in sections:
        if not isinstance(section, dict) or not KEY.fullmatch(str(section.get("key", ""))) or not section.get("title") or not section.get("question"):
            raise TemplateError(f"Her bölümün anahtarı, başlığı ve sorusu olmalı: {name}.")
        if section["key"] in seen:
            raise TemplateError(f"Bölüm anahtarı iki kez kullanılmış: {section['key']} ({name}).")
        seen.add(section["key"])
        if not isinstance(section.get("blocks"), list) or not section["blocks"]:
            raise TemplateError(f"Bölümde veri bloğu yok: {section['key']} ({name}).")
        for spec in section["blocks"]:
            if not isinstance(spec, dict) or spec.get("block") not in blocks:
                raise TemplateError(f"Bilinmeyen veri bloğu: {spec.get('block') if isinstance(spec, dict) else spec} ({section['key']}, {name}).")
            for reference in re.findall(r"\{([a-z0-9_-]+?)(?:_adi)?\}", json.dumps(spec, ensure_ascii=False)):
                if reference not in keys:
                    raise TemplateError(f"Bölümde tanımlanmamış parametre: {{{reference}}} ({section['key']}, {name}).")
    return {"key": data["key"], "version": str(data["version"]), "title": data["title"], "question": data["question"],
            "dimensions": {k: dimensions[k] for k in DIMENSIONS if k in dimensions}, "parameters": parameters, "sections": sections,
            "file": name}


def read_all(folder, blocks):
    """Templates of a destination folder by key; a folder without templates gives an empty dict."""
    templates = {}
    for path in sorted(Path(folder).glob("*.json")) if folder and Path(folder).is_dir() else []:
        template = read(path, blocks)
        if template["key"] in templates:
            raise TemplateError(f"Aynı şablon anahtarı iki dosyada: {template['key']}.")
        templates[template["key"]] = template
    return templates


def resolve(template, values, regions):
    """Parameter values checked against the template: {key: {"id", "name"}}; a region must be one of the destination's regions."""
    names = {region["id"]: region["name"] for region in regions}
    resolved = {}
    for parameter in template["parameters"]:
        value = (values or {}).get(parameter["key"])
        if value not in names:
            raise TemplateError(f"'{parameter.get('label') or parameter['key']}' için bu destinasyonun mahallelerinden biri seçilmeli.")
        resolved[parameter["key"]] = {"id": value, "name": names[value]}
    return resolved


def fill(spec, resolved):
    """A block spec with "{key}" / "{key_adi}" replaced by the parameter's region id / name."""
    text = json.dumps(spec, ensure_ascii=False)
    for key, value in resolved.items():
        text = text.replace("{" + key + "_adi}", value["name"].replace('"', '\\"')).replace("{" + key + "}", value["id"])
    return json.loads(text)
