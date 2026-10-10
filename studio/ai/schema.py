"""A small JSON Schema (2020-12) checker for the step schemas (GÖREV-13), with Turkish messages.

Housing Atlas validates with the `jsonschema` package; 30A Studio checks the subset its schemas use instead of adding a dependency: `type`
(also a list), `const`, `enum`, `required`, `properties`, `additionalProperties` (false or a schema), `items`, `minItems`, `maxItems`,
`minLength`, `maxLength`, `pattern`, `minimum`, `maximum` (GÖREV-15) and local `$ref` (`#/$defs/<name>`). A keyword outside this subset is refused when the schema is loaded,
so a schema cannot silently ask for more than is checked.
"""
import json
import re
from pathlib import Path

SUPPORTED = {"$schema", "$id", "title", "description", "$defs", "type", "const", "enum", "required", "properties", "additionalProperties",
             "items", "minItems", "maxItems", "minLength", "maxLength", "pattern", "$ref", "minimum", "maximum"}
TYPE_NAMES = {"string": "metin", "number": "sayı", "integer": "tam sayı", "boolean": "true ya da false", "array": "liste", "object": "nesne",
              "null": "null"}
MAX_ERRORS = 20


class SchemaError(ValueError):
    pass


def load(path):
    schema = json.loads(Path(path).read_text(encoding="utf-8"))
    check_keywords(schema)
    return schema


def check_keywords(node, where="kök"):
    if isinstance(node, dict):
        unknown = set(node) - SUPPORTED
        if unknown:
            raise SchemaError(f"Şemada denetlenmeyen anahtar var ({where}): {', '.join(sorted(unknown))}")
        for key, value in node.items():
            if key in ("properties", "$defs"):
                for name, child in value.items():
                    check_keywords(child, f"{where}/{name}")
            elif key in ("items", "additionalProperties") and isinstance(value, dict):
                check_keywords(value, f"{where}/{key}")


def is_type(value, name):
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name == "boolean":
        return isinstance(value, bool)
    if name == "null":
        return value is None
    return isinstance(value, {"string": str, "array": list, "object": dict}[name])


def place(path):
    parts = [f"{p + 1}. öğe" if isinstance(p, int) else str(p) for p in path]
    return " → ".join(parts) if parts else "dosyanın kökü"


def resolve(root, node):
    while isinstance(node, dict) and "$ref" in node:
        ref = node["$ref"]
        if not ref.startswith("#/$defs/"):
            raise SchemaError(f"Desteklenmeyen başvuru: {ref}")
        node = root["$defs"][ref[len("#/$defs/"):]]
    return node


def errors(schema, data, limit=MAX_ERRORS):
    """Turkish messages of every place the data breaks the schema (at most `limit`); empty when it fits."""
    found = []

    def walk(node, value, path):
        if len(found) >= limit:
            return
        node = resolve(schema, node)
        where = place(path)
        if "type" in node:
            names = node["type"] if isinstance(node["type"], list) else [node["type"]]
            if not any(is_type(value, n) for n in names):
                found.append(f"{where}: {' ya da '.join(TYPE_NAMES[n] for n in names)} olmalı.")
                return
        if "const" in node and value != node["const"]:
            found.append(f"{where}: değer {json.dumps(node['const'], ensure_ascii=False)} olmalı.")
        if "enum" in node and value not in node["enum"]:
            choices = ", ".join(json.dumps(v, ensure_ascii=False) for v in node["enum"])
            found.append(f"{where}: değer listede yok ({json.dumps(value, ensure_ascii=False)}); şunlardan biri olmalı: {choices}.")
        if isinstance(value, str):
            if len(value.strip()) < node.get("minLength", 0):
                found.append(f"{where}: boş olamaz." if node.get("minLength") == 1 else f"{where}: en az {node['minLength']} karakter olmalı.")
            if "maxLength" in node and len(value) > node["maxLength"]:
                found.append(f"{where}: en çok {node['maxLength']} karakter olmalı ({len(value)} karakter).")
            if "pattern" in node and not re.search(node["pattern"], value):
                found.append(f"{where}: biçimi uygun değil ({value!r}; beklenen biçim {node['pattern']}).")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in node and value < node["minimum"]:
                found.append(f"{where}: en az {node['minimum']} olmalı ({value}).")
            if "maximum" in node and value > node["maximum"]:
                found.append(f"{where}: en çok {node['maximum']} olmalı ({value}).")
        if isinstance(value, list):
            if len(value) < node.get("minItems", 0):
                found.append(f"{where}: en az {node['minItems']} öğe olmalı.")
            if "maxItems" in node and len(value) > node["maxItems"]:
                found.append(f"{where}: en çok {node['maxItems']} öğe olmalı.")
            if "items" in node:
                for index, item in enumerate(value):
                    walk(node["items"], item, [*path, index])
        if isinstance(value, dict):
            for name in node.get("required", []):
                if name not in value:
                    found.append(f"{where}: '{name}' alanı eksik.")
            properties = node.get("properties", {})
            extra = node.get("additionalProperties", True)
            for name, item in value.items():
                if name in properties:
                    walk(properties[name], item, [*path, name])
                elif extra is False:
                    found.append(f"{where}: '{name}' alanı şemada yok (bilinmeyen alan).")
                elif isinstance(extra, dict):
                    walk(extra, item, [*path, name])

    walk(schema, data, [])
    return found[:limit]
