from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from nl2sql_ml.engine import NL2SQLEngine


def nested_value(value: Any, path: str) -> Any:
    current = value
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(path)
        current = current[part]
    return current


def validate(case: dict[str, Any], engine: NL2SQLEngine) -> dict[str, Any]:
    expected = case["expected"]
    try:
        result = engine.translate(case["question"])
    except Exception as exc:
        required = expected.get("error_contains")
        if required and required in str(exc):
            return {"status": "passed", "error": f"{type(exc).__name__}: {exc}"}
        raise AssertionError(f"出现非预期异常: {type(exc).__name__}: {exc}") from exc

    if "error_contains" in expected:
        raise AssertionError(f"预期异常包含“{expected['error_contains']}”，但实际生成了SQL")

    plan = result["plan"]
    for key, wanted in expected.get("plan", {}).items():
        actual = plan.get(key)
        if actual != wanted:
            raise AssertionError(f"plan.{key}: 期望 {wanted!r}，实际 {actual!r}")
    ast = plan.get("semantic_ast", {})
    for path, wanted in expected.get("ast", {}).items():
        try:
            actual = nested_value(ast, path)
        except KeyError as exc:
            raise AssertionError(f"semantic_ast缺少路径: {path}") from exc
        if actual != wanted:
            raise AssertionError(f"semantic_ast.{path}: 期望 {wanted!r}，实际 {actual!r}")
    if len(plan.get("joins", [])) < expected.get("min_joins", 0):
        raise AssertionError(
            f"关联数量不足: 期望至少{expected['min_joins']}，实际{len(plan.get('joins', []))}"
        )
    sql = result["sql"]
    for fragment in expected.get("sql_contains", []):
        if fragment not in sql:
            raise AssertionError(f"SQL缺少片段: {fragment}")
    for fragment in expected.get("sql_not_contains", []):
        if fragment in sql:
            raise AssertionError(f"SQL不应包含片段: {fragment}")
    if "params" in expected and result["params"] != expected["params"]:
        raise AssertionError(f"params: 期望 {expected['params']!r}，实际 {result['params']!r}")
    if sql.count("?") != len(result["params"]):
        raise AssertionError("SQL占位符数量与参数数量不一致")
    if not sql.upper().startswith("SELECT") or ";" in sql[:-1]:
        raise AssertionError("生成结果不是单条SELECT")
    return {
        "status": "passed",
        "table": plan.get("table"),
        "intent": plan.get("intent"),
        "report_type": plan.get("report_type"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="顺序运行200条NL2SQL对抗测试，首错即停")
    parser.add_argument("--cases", type=Path, default=ROOT / "data" / "adversarial_200.jsonl")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=200)
    args = parser.parse_args()
    cases = [json.loads(line) for line in args.cases.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(cases) != 200:
        raise SystemExit(f"测试集必须恰好包含200条，实际为{len(cases)}")
    if not 1 <= args.start <= args.end <= 200:
        raise SystemExit("start/end必须位于1至200且start<=end")

    engine = NL2SQLEngine()
    passed: list[dict[str, Any]] = []
    for number in range(args.start, args.end + 1):
        case = cases[number - 1]
        try:
            detail = validate(case, engine)
        except Exception as exc:
            failure = {
                "status": "failed",
                "number": number,
                "id": case["id"],
                "role": case["role"],
                "category": case["category"],
                "style": case["style"],
                "question": case["question"],
                "expected": case["expected"],
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(),
                "passed_in_this_run": len(passed),
            }
            print(f"FAIL {number:03d}/200 · {case['role']} · {case['question']}")
            print(json.dumps(failure, ensure_ascii=False, indent=2))
            (ROOT / "artifacts" / "adversarial_200_report.json").write_text(
                json.dumps(failure, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            sys.exit(1)
        passed.append({"number": number, "id": case["id"], **detail})
        print(f"PASS {number:03d}/200 · {case['role']} · {case['question']}")

    report = {
        "status": "passed",
        "range": [args.start, args.end],
        "passed_in_this_run": len(passed),
        "total_suite_cases": 200,
        "details": passed,
    }
    (ROOT / "artifacts" / "adversarial_200_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({key: report[key] for key in ("status", "range", "passed_in_this_run", "total_suite_cases")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
