from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold, learning_curve

from .model import TARGETS, make_pipeline

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def generate_learning_curves(
    dataset_path: str | Path,
    image_path: str | Path,
    csv_path: str | Path,
    seed: int = 20260816,
    max_samples: int = 12000,
) -> dict[str, Any]:
    """Export offline learning curves; the final model still uses every row.

    Cross-validation is capped because it fits every target repeatedly and is only
    intended to show whether additional data is improving validation scores.
    """
    source_frame = pd.read_json(dataset_path, lines=True)
    source_samples = len(source_frame)
    frame = (
        source_frame.sample(n=max_samples, random_state=seed).reset_index(drop=True)
        if source_samples > max_samples
        else source_frame
    )
    fractions = np.array([0.1, 0.35, 0.7, 1.0])
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=seed)
    rows: list[dict[str, Any]] = []
    figure, axes = plt.subplots(2, 2, figsize=(12, 8))
    figure.subplots_adjust(top=0.87, bottom=0.08, hspace=0.34, wspace=0.2)
    palette = {"train": "#315EFB", "validation": "#E08B2C"}

    for axis, target in zip(axes.flat, TARGETS):
        subset = frame[["question", target]].copy()
        if target != "intent":
            subset = subset[subset[target] != "__none__"]
        sizes, train_scores, validation_scores = learning_curve(
            make_pipeline(),
            subset["question"],
            subset[target],
            train_sizes=fractions,
            cv=cv,
            scoring="accuracy",
            n_jobs=1,
            shuffle=True,
            random_state=seed,
        )
        train_mean = train_scores.mean(axis=1)
        train_std = train_scores.std(axis=1)
        validation_mean = validation_scores.mean(axis=1)
        validation_std = validation_scores.std(axis=1)
        axis.plot(sizes, train_mean, marker="o", color=palette["train"], label="Training")
        axis.plot(sizes, validation_mean, marker="o", color=palette["validation"], label="Validation")
        axis.fill_between(sizes, train_mean - train_std, train_mean + train_std, color=palette["train"], alpha=0.12)
        axis.fill_between(sizes, validation_mean - validation_std, validation_mean + validation_std, color=palette["validation"], alpha=0.12)
        axis.set_title(target.replace("_", " ").title())
        axis.set_xlabel("Training samples")
        axis.set_ylabel("Accuracy")
        lower = max(0.0, float(min(train_mean.min(), validation_mean.min())) - 0.05)
        axis.set_ylim(lower, 1.01)
        axis.grid(axis="y", color="#D9DEE8", linewidth=0.8)
        axis.spines[["top", "right"]].set_visible(False)
        axis.legend(frameon=False, loc="lower right")
        for index, size in enumerate(sizes):
            rows.append(
                {
                    "target": target,
                    "train_size": int(size),
                    "train_accuracy_mean": float(train_mean[index]),
                    "train_accuracy_std": float(train_std[index]),
                    "validation_accuracy_mean": float(validation_mean[index]),
                    "validation_accuracy_std": float(validation_std[index]),
                }
            )

    figure.suptitle("NL2SQL Learning Curves", fontsize=16, color="#172033", y=0.975)
    figure.text(
        0.5,
        0.932,
        f"Per-panel focused axes - 3-fold CV on {len(frame):,} of {source_samples:,} synthetic questions",
        ha="center",
        color="#667085",
        fontsize=9,
    )
    image_output = Path(image_path)
    csv_output = Path(csv_path)
    image_output.parent.mkdir(parents=True, exist_ok=True)
    csv_output.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(image_output, dpi=160, facecolor="white", bbox_inches="tight")
    plt.close(figure)
    with csv_output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return {
        "image": str(image_output),
        "csv": str(csv_output),
        "source_samples": int(source_samples),
        "plot_samples": int(len(frame)),
        "points": len(rows),
    }
