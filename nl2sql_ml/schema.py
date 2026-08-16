from __future__ import annotations

import hashlib
import json
import re
from collections import deque
from pathlib import Path
from typing import Any


NUMERIC_TYPE_RE = re.compile(r"^(?:tinyint|smallint|int|integer|bigint|float|double|decimal|numeric|money|real)", re.I)
DATE_TYPE_RE = re.compile(r"^(?:date|datetime|smalldatetime|time)", re.I)
TEXT_TYPE_RE = re.compile(r"^(?:n?varchar|n?char|text|ntext)", re.I)


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_catalog(path: str | Path | None = None) -> dict[str, Any]:
    catalog_path = Path(path) if path else project_root() / "config" / "schema_catalog.json"
    with catalog_path.open("r", encoding="utf-8") as handle:
        catalog = json.load(handle)
    validate_catalog(catalog)
    return catalog


def load_dictionary(path: str | Path | None = None) -> dict[str, Any]:
    dictionary_path = Path(path) if path else project_root() / "config" / "business_dictionary.json"
    with dictionary_path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def load_semantic_layer(path: str | Path | None = None) -> dict[str, Any]:
    semantic_path = Path(path) if path else project_root() / "config" / "semantic_layer.json"
    with semantic_path.open("r", encoding="utf-8-sig") as handle:
        layer = json.load(handle)
    if layer.get("version") != 1 or not isinstance(layer.get("facts"), dict):
        raise ValueError("业务语义层格式无效")
    return layer


def semantic_layer_fingerprint(layer: dict[str, Any]) -> str:
    payload = json.dumps(layer, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_catalog(catalog: dict[str, Any]) -> None:
    required = {"dialect", "domains", "tables", "relations", "query_joins"}
    missing = required - catalog.keys()
    if missing:
        raise ValueError(f"Schema目录缺少字段: {sorted(missing)}")
    seen: set[str] = set()
    for table in catalog["tables"]:
        name = table.get("name", "")
        if not safe_identifier(name):
            raise ValueError(f"不安全的表名: {name}")
        lowered = name.lower()
        if lowered in seen:
            raise ValueError(f"重复表名: {name}")
        seen.add(lowered)
        field_seen: set[str] = set()
        for field in table.get("fields", []):
            field_name = field.get("name", "")
            if not safe_identifier(field_name):
                raise ValueError(f"不安全的字段名: {name}.{field_name}")
            if field_name.lower() in field_seen:
                raise ValueError(f"重复字段名: {name}.{field_name}")
            field_seen.add(field_name.lower())
    tables = table_map(catalog)
    for rule in catalog.get("query_joins", []):
        for side in ("left", "right"):
            table_name = rule.get(f"{side}_table")
            field_name = rule.get(f"{side}_field")
            if table_name not in tables or field_name not in field_map(tables[table_name]):
                raise ValueError(f"无效查询关联: {rule}")


def schema_fingerprint(catalog: dict[str, Any]) -> str:
    stable = {
        "dialect": catalog["dialect"],
        "tables": [
            {
                "name": table["name"],
                "domain": table["domain"],
                "fields": [
                    {"name": field["name"], "type": field["type"]}
                    for field in table["fields"]
                ],
            }
            for table in catalog["tables"]
        ],
        "query_joins": catalog.get("query_joins", []),
    }
    payload = json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def table_map(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {table["name"]: table for table in catalog["tables"]}


def field_map(table: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {field["name"]: field for field in table["fields"]}


def safe_identifier(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", value or ""))


def quote_identifier(value: str, dialect: str = "sqlserver") -> str:
    if not safe_identifier(value):
        raise ValueError(f"不安全的标识符: {value}")
    if dialect == "sqlserver":
        return f"[{value}]"
    return f'"{value}"'


def is_numeric(field: dict[str, Any]) -> bool:
    return bool(NUMERIC_TYPE_RE.match(field.get("type", ""))) and not is_identifier_field(field)


def is_date(field: dict[str, Any]) -> bool:
    return bool(DATE_TYPE_RE.match(field.get("type", ""))) or bool(
        re.search(r"(?:date|time)$", field.get("name", ""), re.I)
    )


def is_text(field: dict[str, Any]) -> bool:
    return bool(TEXT_TYPE_RE.match(field.get("type", "")))


def is_identifier_field(field: dict[str, Any]) -> bool:
    name = field.get("name", "")
    return bool(
        re.search(r"(?:^id$|id$|serialno$|ordernumber$)", name, re.I)
        or re.search(r"\bPK\b|\bFK\b", field.get("key", ""), re.I)
    )


def primary_key(table: dict[str, Any]) -> dict[str, Any] | None:
    return next(
        (field for field in table["fields"] if re.search(r"\bPK\b|主键", field.get("key", "") + " " + field.get("description", ""), re.I)),
        None,
    )


def date_fields(table: dict[str, Any]) -> list[dict[str, Any]]:
    return [field for field in table["fields"] if is_date(field)]


def numeric_fields(table: dict[str, Any]) -> list[dict[str, Any]]:
    return [field for field in table["fields"] if is_numeric(field)]


def dimension_fields(table: dict[str, Any]) -> list[dict[str, Any]]:
    fields = []
    for field in table["fields"]:
        name = field.get("name", "")
        is_primary = bool(re.search(r"\bPK\b|主键", field.get("key", "") + " " + field.get("description", ""), re.I))
        if is_primary or re.search(r"^serialno$", name, re.I) or is_date(field):
            continue
        if re.match(r"^(?:image|binary|varbinary|text|ntext)", field.get("type", ""), re.I):
            continue
        if (
            re.search(r"(?:id|name|title|type|status|sex|source|level|category|department|duty)$", name, re.I)
            or is_text(field)
        ):
            fields.append(field)
    return fields


def join_rule_key(rule: dict[str, Any]) -> tuple[tuple[str, str], tuple[str, str]]:
    endpoints = sorted(
        [
            (rule["left_table"].lower(), rule["left_field"].lower()),
            (rule["right_table"].lower(), rule["right_field"].lower()),
        ]
    )
    return endpoints[0], endpoints[1]


def find_join_path(
    catalog: dict[str, Any],
    start_table: str,
    target_table: str,
    max_hops: int = 3,
) -> list[dict[str, Any]] | None:
    """Return the shortest whitelisted path between two tables."""
    if start_table == target_table:
        return []
    adjacency: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for rule in catalog.get("query_joins", []):
        left = rule["left_table"]
        right = rule["right_table"]
        adjacency.setdefault(left, []).append((right, rule))
        adjacency.setdefault(right, []).append((left, rule))
    preferred_bridges = {
        frozenset(("Student_Info", "Course_Info")): "Student_CourseInfo",
        frozenset(("Student_Info", "Study_Class_Info")): "Study_Class_Student_Info",
        frozenset(("Student_Info", "OffTrain_Info")): "Student_OffTrain_Info",
        frozenset(("Student_Info", "Role_Info")): "Student_Role_Info",
        frozenset(("Student_Info", "Skill_Info")): "Student_Skill_Info",
        frozenset(("Student_Info", "Certificate_Info")): "Student_Certificate_Info",
    }
    preferred = preferred_bridges.get(frozenset((start_table, target_table)))
    if preferred:
        for table_name, items in adjacency.items():
            adjacency[table_name] = sorted(
                items,
                key=lambda item: 0
                if preferred
                in {item[1]["left_table"], item[1]["right_table"]}
                else 1,
            )
    queue = deque([(start_table, [])])
    visited = {start_table}
    while queue:
        table, path = queue.popleft()
        if len(path) >= max_hops:
            continue
        for neighbor, rule in adjacency.get(table, []):
            if neighbor in visited:
                continue
            next_path = [*path, rule]
            if neighbor == target_table:
                return next_path
            visited.add(neighbor)
            queue.append((neighbor, next_path))
    return None


def reachable_tables(
    catalog: dict[str, Any], start_table: str, max_hops: int = 2
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {start_table: []}
    for table in catalog["tables"]:
        name = table["name"]
        if name == start_table:
            continue
        path = find_join_path(catalog, start_table, name, max_hops=max_hops)
        if path is not None:
            result[name] = path
    return result


def is_safe_entity_path(
    primary_table: str,
    target_table: str,
    path: list[dict[str, Any]],
) -> bool:
    """Reject paths that fan out through unrelated fact tables.

    Following foreign-key edges from left to right is many-to-one and safe for
    lookup filters.  A small set of intentional bridge-table routes is allowed
    in both directions for student membership questions.
    """
    current = primary_table
    forward_only = True
    for rule in path:
        if current == rule["left_table"]:
            current = rule["right_table"]
        elif current == rule["right_table"]:
            current = rule["left_table"]
            forward_only = False
        else:
            return False
    if current != target_table:
        return False
    if forward_only:
        return True
    intentional = {
        ("Student_Info", "Course_Info"),
        ("Course_Info", "Student_Info"),
        ("Student_Info", "Study_Class_Info"),
        ("Study_Class_Info", "Student_Info"),
        ("Student_Info", "OffTrain_Info"),
        ("OffTrain_Info", "Student_Info"),
        ("Student_Info", "Skill_Info"),
        ("Skill_Info", "Student_Info"),
        ("Role_Info", "Student_Info"),
        ("Certificate_Info", "Student_Info"),
    }
    return (primary_table, target_table) in intentional
