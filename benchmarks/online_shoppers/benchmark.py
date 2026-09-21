"""Reproducible structured baselines for the UCI Online Shoppers dataset."""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

DATASET_URL = (
    "https://archive.ics.uci.edu/static/public/468/"
    "online%2Bshoppers%2Bpurchasing%2Bintention%2Bdataset.zip"
)
EXPECTED_ROWS = 12_330
TARGET = "Revenue"
EXCLUDED_FEATURES = ["PageValues"]
NUMERIC_FEATURES = [
    "Administrative",
    "Administrative_Duration",
    "Informational",
    "Informational_Duration",
    "ProductRelated",
    "ProductRelated_Duration",
    "BounceRates",
    "ExitRates",
    "SpecialDay",
]
CATEGORICAL_FEATURES = [
    "Month",
    "OperatingSystems",
    "Browser",
    "Region",
    "TrafficType",
    "VisitorType",
    "Weekend",
]
SELECTED_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
REQUIRED_COLUMNS = set(SELECTED_FEATURES + EXCLUDED_FEATURES + [TARGET])


def download_dataset(destination: Path) -> None:
    """Download and extract the canonical UCI CSV."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(DATASET_URL, timeout=60) as response:
        archive = BytesIO(response.read())
    with zipfile.ZipFile(archive) as zipped:
        member = next(
            (name for name in zipped.namelist() if name.endswith("online_shoppers_intention.csv")),
            None,
        )
        if member is None:
            raise ValueError("The UCI archive did not contain online_shoppers_intention.csv")
        destination.write_bytes(zipped.read(member))


def load_dataset(path: Path, allow_download: bool = True) -> pd.DataFrame:
    if not path.exists():
        if not allow_download:
            raise FileNotFoundError(f"Dataset not found: {path}")
        print(f"Downloading the UCI dataset to {path}")
        download_dataset(path)

    frame = pd.read_csv(path)
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing)}")
    if len(frame) != EXPECTED_ROWS:
        raise ValueError(f"Expected {EXPECTED_ROWS} rows, found {len(frame)}")

    frame = frame.copy()
    frame[TARGET] = frame[TARGET].map(
        lambda value: value if isinstance(value, bool) else str(value).strip().lower() == "true"
    ).astype(int)
    return frame


def split_dataset(
    frame: pd.DataFrame, test_size: float = 0.25, seed: int = 42
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    features = frame[SELECTED_FEATURES].copy()
    target = frame[TARGET].astype(int)
    return train_test_split(
        features,
        target,
        test_size=test_size,
        random_state=seed,
        stratify=target,
    )


def simple_rule_predict(features: pd.DataFrame) -> np.ndarray:
    """An intentionally transparent, fixed heuristic with no fitted parameters."""
    score = (
        (features["ProductRelated"] >= 10).astype(int)
        + (features["ProductRelated_Duration"] >= 600).astype(int)
        + (features["BounceRates"] <= 0.02).astype(int)
        + (features["ExitRates"] <= 0.05).astype(int)
        + (features["VisitorType"].astype(str) == "Returning_Visitor").astype(int)
    )
    return (score >= 4).astype(int).to_numpy()


def expected_calibration_error(
    labels: np.ndarray, probabilities: np.ndarray, bins: int = 10
) -> float:
    """Return equal-width expected calibration error."""
    edges = np.linspace(0.0, 1.0, bins + 1)
    assignments = np.minimum(np.digitize(probabilities, edges[1:-1]), bins - 1)
    error = 0.0
    for index in range(bins):
        mask = assignments == index
        if not np.any(mask):
            continue
        error += float(np.mean(mask)) * abs(
            float(np.mean(labels[mask])) - float(np.mean(probabilities[mask]))
        )
    return error


def classification_metrics(
    labels: pd.Series | np.ndarray,
    predictions: np.ndarray,
    probabilities: np.ndarray | None = None,
) -> dict[str, float | str]:
    y_true = np.asarray(labels, dtype=int)
    output: dict[str, float | str] = {
        "accuracy": float(accuracy_score(y_true, predictions)),
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
    }
    if probabilities is None:
        output["brier_score"] = "unavailable"
        output["ece_10_bin"] = "unavailable"
    else:
        output["brier_score"] = float(brier_score_loss(y_true, probabilities))
        output["ece_10_bin"] = expected_calibration_error(y_true, probabilities)
    return output


def logistic_pipeline() -> Pipeline:
    numeric = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("one_hot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    preprocessing = ColumnTransformer(
        [
            ("numeric", numeric, NUMERIC_FEATURES),
            ("categorical", categorical, CATEGORICAL_FEATURES),
        ]
    )
    return Pipeline(
        [
            ("preprocess", preprocessing),
            (
                "classifier",
                LogisticRegression(
                    max_iter=2_000,
                    random_state=42,
                    class_weight="balanced",
                ),
            ),
        ]
    )


def timed_rule(features: pd.DataFrame) -> tuple[np.ndarray, float]:
    started = time.perf_counter()
    prediction = simple_rule_predict(features)
    return prediction, (time.perf_counter() - started) * 1_000


def run_baselines(
    frame: pd.DataFrame, test_size: float = 0.25, seed: int = 42
) -> dict[str, Any]:
    train_x, test_x, train_y, test_y = split_dataset(frame, test_size, seed)

    rule_predictions, rule_latency = timed_rule(test_x)

    model = logistic_pipeline()
    started = time.perf_counter()
    model.fit(train_x, train_y)
    fit_latency = (time.perf_counter() - started) * 1_000
    started = time.perf_counter()
    logistic_probabilities = model.predict_proba(test_x)[:, 1]
    logistic_predictions = (logistic_probabilities >= 0.5).astype(int)
    predict_latency = (time.perf_counter() - started) * 1_000

    return {
        "dataset": {
            "name": "Online Shoppers Purchasing Intention",
            "source": DATASET_URL,
            "rows": len(frame),
            "positive_rows": int(frame[TARGET].sum()),
        },
        "feature_policy": {
            "target_only": [TARGET],
            "selected": SELECTED_FEATURES,
            "excluded": EXCLUDED_FEATURES,
            "exclusion_reason": {
                "PageValues": (
                    "Google Analytics page value is computed from pages visited before a "
                    "transaction. It is late-session and too outcome-adjacent for this comparison."
                )
            },
        },
        "split": {
            "seed": seed,
            "test_size": test_size,
            "train_rows": len(train_x),
            "test_rows": len(test_x),
            "stratified": True,
        },
        "baselines": {
            "simple_rule": {
                "definition": (
                    "At least four of: >=10 product pages, >=600 product seconds, "
                    "bounce rate <=0.02, exit rate <=0.05, returning visitor."
                ),
                "metrics": classification_metrics(test_y, rule_predictions),
                "latency_ms": rule_latency,
                "api_cost_usd": 0.0,
            },
            "logistic_regression": {
                "definition": (
                    "Scaled numeric features plus one-hot categorical features and balanced "
                    "class weights."
                ),
                "metrics": classification_metrics(
                    test_y, logistic_predictions, logistic_probabilities
                ),
                "fit_latency_ms": fit_latency,
                "prediction_latency_ms": predict_latency,
                "api_cost_usd": 0.0,
            },
        },
        "limitations": [
            "Rows summarize completed sessions, so this is retrospective prediction.",
            "A deployable early-session policy needs timestamped snapshots and prospective evaluation.",
            "The dataset has no ground-truth hero or UI-component label.",
        ],
    }


def parse_args() -> argparse.Namespace:
    directory = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data", type=Path, default=directory / "data" / "online_shoppers_intention.csv"
    )
    parser.add_argument(
        "--output", type=Path, default=directory / "results" / "baseline_results.json"
    )
    parser.add_argument("--test-size", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-download", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    frame = load_dataset(args.data, allow_download=not args.no_download)
    results = run_baselines(frame, test_size=args.test_size, seed=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))
    print(f"\nWrote {args.output}")


if __name__ == "__main__":
    main()
