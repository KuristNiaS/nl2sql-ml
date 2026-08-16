from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import NL2SQLEngine
from .evaluation import evaluate_acceptance
from .generator import generate_dataset
from .model import train_models
from .plots import generate_learning_curves
from .reports import generate_acceptance_report, generate_model_report
from .schema import load_catalog, load_dictionary, load_semantic_layer, project_root, schema_fingerprint


def build_parser() -> argparse.ArgumentParser:
    root = project_root()
    parser = argparse.ArgumentParser(description="培训系统传统机器学习 NL2SQL")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="基于设计书Schema生成数据、训练并评估")
    build.add_argument("--samples", type=int, default=72000)
    build.add_argument("--seed", type=int, default=20260816)
    build.add_argument("--skip-plots", action="store_true")

    generate = sub.add_parser("generate", help="生成覆盖全部表的训练数据")
    generate.add_argument("--samples", type=int, default=72000)
    generate.add_argument("--output", type=Path, default=root / "data" / "dataset.jsonl")
    generate.add_argument("--seed", type=int, default=20260816)

    train = sub.add_parser("train", help="训练意图、业务域、数据表和聚合分类器")
    train.add_argument("--dataset", type=Path, default=root / "data" / "dataset.jsonl")
    train.add_argument("--model", type=Path, default=root / "artifacts" / "model.joblib")
    train.add_argument("--report", type=Path, default=root / "artifacts" / "evaluation.json")

    ask = sub.add_parser("ask", help="把自然语言翻译成SQL Server查询")
    ask.add_argument("question")
    ask.add_argument("--pretty", action="store_true")

    evaluate = sub.add_parser("evaluate", help="运行设计书业务验收语句")
    evaluate.add_argument("--cases", type=Path, default=root / "data" / "acceptance.jsonl")
    evaluate.add_argument("--dataset", type=Path, default=root / "data" / "dataset.jsonl")

    plots = sub.add_parser("plots", help="导出离线学习曲线PNG和CSV")
    plots.add_argument("--dataset", type=Path, default=root / "data" / "dataset.jsonl")
    plots.add_argument("--image", type=Path, default=root / "artifacts" / "learning_curves.png")
    plots.add_argument("--csv", type=Path, default=root / "artifacts" / "learning_curves.csv")

    sub.add_parser("schema", help="显示从设计书提取的Schema摘要")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    root = project_root()
    catalog = load_catalog()
    dictionary = load_dictionary()
    semantic_layer = load_semantic_layer()
    if args.command == "generate":
        summary = generate_dataset(catalog, dictionary, args.output, args.samples, args.seed)
        _write_json(root / "artifacts" / "dataset_summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    elif args.command == "train":
        report = train_models(args.dataset, args.model, args.report, catalog, semantic_layer=semantic_layer)
        print(json.dumps(_accuracy_summary(report), ensure_ascii=False, indent=2))
    elif args.command == "build":
        dataset = root / "data" / "dataset.jsonl"
        model = root / "artifacts" / "model.joblib"
        evaluation_file = root / "artifacts" / "evaluation.json"
        dataset_summary_file = root / "artifacts" / "dataset_summary.json"
        acceptance_file = root / "artifacts" / "acceptance_report.json"
        summary = generate_dataset(catalog, dictionary, dataset, args.samples, args.seed)
        _write_json(dataset_summary_file, summary)
        report = train_models(dataset, model, evaluation_file, catalog, args.seed, semantic_layer)
        acceptance = evaluate_acceptance(NL2SQLEngine(), root / "data" / "acceptance.jsonl", dataset)
        _write_json(acceptance_file, acceptance)
        if not args.skip_plots:
            generate_learning_curves(
                dataset,
                root / "artifacts" / "learning_curves.png",
                root / "artifacts" / "learning_curves.csv",
            )
        generate_model_report(
            root / "config" / "schema_catalog.json",
            dataset_summary_file,
            evaluation_file,
            acceptance_file,
            root / "reports" / "model_report.md",
        )
        generate_acceptance_report(
            root / "data" / "acceptance.jsonl",
            acceptance_file,
            root / "reports" / "acceptance_report.md",
        )
        print(json.dumps({"dataset": summary, "accuracy": _accuracy_summary(report), "acceptance": {"passed": acceptance["passed"], "cases": acceptance["cases"]}}, ensure_ascii=False, indent=2))
    elif args.command == "ask":
        try:
            result = NL2SQLEngine().translate(args.question)
        except (ValueError, FileNotFoundError) as exc:
            print(json.dumps({"question": args.question, "error": str(exc)}, ensure_ascii=False, indent=2))
            raise SystemExit(2) from None
        if args.pretty:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result["sql"])
            print(json.dumps(result["params"], ensure_ascii=False))
    elif args.command == "evaluate":
        result = evaluate_acceptance(NL2SQLEngine(), args.cases, args.dataset)
        _write_json(root / "artifacts" / "acceptance_report.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "plots":
        result = generate_learning_curves(args.dataset, args.image, args.csv)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "schema":
        print(json.dumps({
            "name": catalog["name"],
            "dialect": catalog["dialect"],
            "domains": len(catalog["domains"]),
            "tables": len(catalog["tables"]),
            "fields": sum(len(table["fields"]) for table in catalog["tables"]),
            "relations": len(catalog["relations"]),
            "query_joins": len(catalog.get("query_joins", [])),
            "semantic_facts": len(semantic_layer.get("facts", {})),
            "fingerprint": schema_fingerprint(catalog),
        }, ensure_ascii=False, indent=2))


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _accuracy_summary(report: dict) -> dict[str, float]:
    return {name: values["accuracy"] for name, values in report["targets"].items()}
