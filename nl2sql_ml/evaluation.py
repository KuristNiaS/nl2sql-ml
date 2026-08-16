from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .engine import NL2SQLEngine


def evaluate_acceptance(
    engine: NL2SQLEngine,
    cases_path: str | Path,
    dataset_path: str | Path | None = None,
) -> dict[str, Any]:
    cases = [
        json.loads(line)
        for line in Path(cases_path).read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    passed = field_total = field_passed = 0
    details: list[dict[str, Any]] = []
    for case in cases:
        expected = case["expected"]
        try:
            translation = engine.translate(case["question"])
            plan = translation["plan"]
            error = None
        except Exception as exc:
            translation = None
            plan = {}
            error = f"{type(exc).__name__}: {exc}"
        mismatches: dict[str, dict[str, Any]] = {}
        for field, expected_value in expected.items():
            field_total += 1
            if field == "filters":
                qualified = {
                    f"{item.get('table', plan.get('table'))}.{item['field']}": item.get("value")
                    for item in plan.get("filters", [])
                }
                actual_value = {
                    key: (
                        qualified.get(key)
                        if "." in key
                        else next(
                            (
                                item.get("value")
                                for item in plan.get("filters", [])
                                if item["field"] == key
                            ),
                            None,
                        )
                    )
                    for key in expected_value
                }
            elif field == "join_tables":
                tables = {
                    endpoint
                    for join in plan.get("joins", [])
                    for endpoint in (join["left_table"], join["right_table"])
                    if endpoint != plan.get("table")
                }
                actual_value = sorted(tables)
            elif field == "join_count":
                actual_value = len(plan.get("joins", []))
            elif field == "sql_contains":
                actual_value = all(token in (translation or {}).get("sql", "") for token in expected_value)
                expected_value = True
            elif field == "error_contains":
                actual_value = bool(error and expected_value in error)
                expected_value = True
            else:
                actual_value = plan.get(field)
            if actual_value == expected_value:
                field_passed += 1
            else:
                mismatches[field] = {"expected": expected_value, "actual": actual_value}
        expects_error = "error_contains" in expected
        case_passed = (error is not None if expects_error else error is None) and not mismatches
        passed += int(case_passed)
        details.append(
            {
                "question": case["question"],
                "passed": case_passed,
                "mismatches": mismatches,
                "error": error,
                "sql": translation["sql"] if translation else None,
            }
        )

    coverage: dict[str, Any] | None = None
    if dataset_path:
        frame = pd.read_json(dataset_path, lines=True)
        expected_tables = {table["name"] for table in engine.catalog["tables"]}
        actual_tables = set(frame["table"].unique())
        coverage = {
            "catalog_tables": len(expected_tables),
            "dataset_tables": len(actual_tables),
            "coverage": len(expected_tables & actual_tables) / len(expected_tables),
            "missing_tables": sorted(expected_tables - actual_tables),
            "min_samples_per_table": int(frame["table"].value_counts().min()),
            "max_samples_per_table": int(frame["table"].value_counts().max()),
        }
    return {
        "cases": len(cases),
        "passed": passed,
        "case_accuracy": passed / len(cases) if cases else 0.0,
        "field_accuracy": field_passed / field_total if field_total else 0.0,
        "schema_coverage": coverage,
        "details": details,
    }
