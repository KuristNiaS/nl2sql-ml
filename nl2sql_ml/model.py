from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from .schema import schema_fingerprint, semantic_layer_fingerprint


TARGETS = ("intent", "domain", "table", "aggregation")


def make_pipeline() -> Pipeline:
    return Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    analyzer="char",
                    ngram_range=(1, 5),
                    min_df=2,
                    max_features=140000,
                    sublinear_tf=True,
                    lowercase=True,
                ),
            ),
            ("classifier", LinearSVC(class_weight="balanced", C=1.5)),
        ]
    )


def train_models(
    dataset_path: str | Path,
    model_path: str | Path,
    report_path: str | Path,
    catalog: dict[str, Any],
    seed: int = 20260816,
    semantic_layer: dict[str, Any] | None = None,
) -> dict[str, Any]:
    frame = pd.read_json(dataset_path, lines=True)
    if len(frame) < len(catalog["tables"]) * 20:
        raise ValueError("训练数据不足以覆盖全部表")
    models: dict[str, Pipeline] = {}
    reports: dict[str, Any] = {
        "samples": int(len(frame)),
        "schema_fingerprint": schema_fingerprint(catalog),
        "targets": {},
    }
    for target in TARGETS:
        subset = frame[["question", target]].copy()
        if target == "aggregation":
            subset = subset[subset[target] != "__none__"]
        counts = subset[target].value_counts()
        if len(counts) < 2 or counts.min() < 2:
            raise ValueError(f"标签 {target} 类别覆盖不足")
        train, test = train_test_split(
            subset,
            test_size=0.2,
            random_state=seed,
            stratify=subset[target],
        )
        model = make_pipeline()
        model.fit(train["question"], train[target])
        predictions = model.predict(test["question"])
        reports["targets"][target] = {
            "train_samples": int(len(train)),
            "test_samples": int(len(test)),
            "accuracy": float(accuracy_score(test[target], predictions)),
            "classes": {str(key): int(value) for key, value in counts.to_dict().items()},
            "classification_report": classification_report(
                test[target], predictions, output_dict=True, zero_division=0
            ),
        }
        models[target] = model
    bundle = {
        "format_version": 2,
        "models": models,
        "metadata": {
            "dataset_samples": int(len(frame)),
            "seed": seed,
            "schema_fingerprint": schema_fingerprint(catalog),
            "table_count": len(catalog["tables"]),
            "semantic_layer_fingerprint": (
                semantic_layer_fingerprint(semantic_layer) if semantic_layer else None
            ),
        },
    }
    output = Path(model_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, output, compress=3)
    report = Path(report_path)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    return reports


class ModelBundle:
    def __init__(
        self,
        path: str | Path,
        catalog: dict[str, Any] | None = None,
        semantic_layer: dict[str, Any] | None = None,
    ):
        bundle = joblib.load(path)
        if bundle.get("format_version") != 2:
            raise ValueError("模型版本与当前全Schema系统不兼容，请重新执行build")
        self.models: dict[str, Pipeline] = bundle["models"]
        self.metadata = bundle.get("metadata", {})
        if catalog is not None:
            expected = schema_fingerprint(catalog)
            actual = self.metadata.get("schema_fingerprint")
            if actual != expected:
                raise ValueError("数据库Schema已变化，当前模型已过期，请重新训练")
        stored_semantic = self.metadata.get("semantic_layer_fingerprint")
        if semantic_layer is not None and stored_semantic is not None:
            expected_semantic = semantic_layer_fingerprint(semantic_layer)
            if stored_semantic != expected_semantic:
                raise ValueError("业务语义层已变化，当前模型已过期，请重新训练")

    def predict(self, target: str, text: str) -> tuple[str, float, dict[str, float]]:
        model = self.models[target]
        classes = list(model.named_steps["classifier"].classes_)
        raw = np.asarray(model.decision_function([text]))
        if raw.ndim == 1:
            raw = np.array([[-raw[0], raw[0]]])
        scores = raw[0] - np.max(raw[0])
        probabilities = np.exp(scores) / np.exp(scores).sum()
        ranking = sorted(zip(classes, probabilities), key=lambda pair: pair[1], reverse=True)
        details = {str(label): float(probability) for label, probability in ranking}
        label, probability = ranking[0]
        if not math.isfinite(float(probability)):
            probability = 0.0
        return str(label), float(probability), details
