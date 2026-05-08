# Script for running mlflow experiments and logging them to mlflow on GCP #

# Import dependencies

import argparse
import functools
import os
import socket
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mlflow
import mlflow.xgboost
from mlflow.data.pandas_dataset import PandasDataset, from_pandas
from mlflow.entities import LoggedModelInput, Metric, RunInfo
import numpy as np
import optuna
import pandas as pd
import seaborn as sns
import sklearn
import xgboost as xgb
from dotenv import load_dotenv
from matplotlib.figure import Figure
from mlflow.models.signature import infer_signature
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split
from yellowbrick.classifier import (
    ClassificationReport,
    ClassPredictionError,
    ConfusionMatrix,
    PrecisionRecallCurve,
    ROCAUC,
)
from yellowbrick.model_selection import FeatureImportances

# sklearn 1.6+ added a 4th return value to _check_targets; patch yellowbrick's local reference
# Can't use `import ... as` here — yellowbrick's __init__ exports a function with the same name
# that shadows the submodule, so we go through sys.modules instead
import sys as _sys

_cpe_module = _sys.modules["yellowbrick.classifier.class_prediction_error"]
_orig_check_targets = _cpe_module._check_targets
_cpe_module._check_targets = lambda y_true, y_pred: _orig_check_targets(y_true, y_pred)[:3]  # type: ignore

# Constants

SEED = 615
DPI = 100
FIGSIZE = (6, 4)

PERF_NONE = 0.5
PERF_LOW = 0.75
PERF_MEDIUM = 0.78
PERF_HIGH = 0.8

STRENGTHS = ["even_strength", "powerplay", "shorthanded", "empty_for", "empty_against"]


# Data container


@dataclass
class ExperimentData:
    """Container for experiment data passed to the optuna objective."""

    X_train: pd.DataFrame
    X_test: pd.DataFrame
    y_train: pd.Series
    y_test: pd.Series
    scale_pos_weight: float
    pd_dataset: PandasDataset
    study_name: str
    parent_info: RunInfo


# Functions


def model_metrics(y: pd.Series, y_pred: np.ndarray, y_pred_proba: np.ndarray) -> dict[str, float]:
    """Returns various model metrics for a tuned model."""
    metric_names = [
        "accuracy",
        "average_precision",
        "balanced_accuracy",
        "f1",
        "f1_weighted",
        "precision",
        "precision_weighted",
        "recall",
        "recall_weighted",
        "roc_auc",
        "log_loss",
    ]

    metrics = [
        sklearn.metrics.accuracy_score(y, y_pred),
        sklearn.metrics.average_precision_score(y, y_pred_proba),
        sklearn.metrics.balanced_accuracy_score(y, y_pred),
        sklearn.metrics.f1_score(y, y_pred, zero_division=0),
        sklearn.metrics.f1_score(y, y_pred, average="weighted", zero_division=0),
        sklearn.metrics.precision_score(y, y_pred, zero_division=0),
        sklearn.metrics.precision_score(y, y_pred, average="weighted", zero_division=0),
        sklearn.metrics.recall_score(y, y_pred, zero_division=0),
        sklearn.metrics.recall_score(y, y_pred, average="weighted", zero_division=0),
        sklearn.metrics.roc_auc_score(y, y_pred_proba),
        sklearn.metrics.log_loss(y, y_pred_proba),
    ]

    return dict(zip(metric_names, metrics, strict=False))


def _make_viz(viz_class, model, X_train, y_train, X_test, y_test, **kwargs) -> Figure | None:
    """Create, fit, score, and finalize a yellowbrick visualization."""
    try:
        fig, ax = plt.subplots(dpi=DPI, figsize=FIGSIZE)
        viz = viz_class(model, ax=ax, **kwargs)
        viz.fit(X_train, y_train)
        viz.score(X_test, y_test)
        viz.finalize()
        return fig
    except Exception:
        plt.close()
        return None


def model_viz(
    model, X_train: pd.DataFrame, y_train: pd.Series, X_test: pd.DataFrame, y_test: pd.Series
) -> tuple[Figure | None, ...]:
    """Generate model visualizations."""
    encoder = {0: "no goal", 1: "goal"}

    classification_report = _make_viz(
        ClassificationReport, model, X_train, y_train, X_test, y_test, encoder=encoder, support=True, cmap="RdPu"
    )
    roc_auc = _make_viz(ROCAUC, model, X_train, y_train, X_test, y_test, encoder=encoder)
    class_prediction = _make_viz(ClassPredictionError, model, X_train, y_train, X_test, y_test, encoder=encoder)
    precision_recall = _make_viz(PrecisionRecallCurve, model, X_train, y_train, X_test, y_test, encoder=encoder)
    importance = _make_viz(FeatureImportances, model, X_train, y_train, X_test, y_test, relative=False, topn=10)
    relative_importance = _make_viz(FeatureImportances, model, X_train, y_train, X_test, y_test, relative=True, topn=10)
    confusion_matrix = _make_viz(ConfusionMatrix, model, X_train, y_train, X_test, y_test, cmap="RdPu", encoder=encoder)

    return (
        classification_report,
        roc_auc,
        class_prediction,
        precision_recall,
        importance,
        relative_importance,
        confusion_matrix,
    )


def log_viz(
    classification_report: Figure | None,
    roc_auc: Figure | None,
    class_prediction: Figure | None,
    precision_recall: Figure | None,
    importance: Figure | None,
    relative_importance: Figure | None,
    confusion_matrix: Figure | None,
) -> None:
    """Log visualization figures to mlflow."""
    figs = {
        "viz/classification_report.png": classification_report,
        "viz/roc_auc.png": roc_auc,
        "viz/class_prediction_error.png": class_prediction,
        "viz/precision_recall_curve.png": precision_recall,
        "viz/feature_importance.png": importance,
        "viz/relative_feature_importance.png": relative_importance,
        "viz/confusion_matrix.png": confusion_matrix,
    }
    for path, fig in figs.items():
        if fig is not None:
            mlflow.log_figure(fig, path)
            plt.close(fig)


def load_data(
    model_name: str, study_name: str
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, float, PandasDataset]:
    """Load and split processed data for a given model."""
    SAVE_FOLDER = Path(__file__).parent / "data" / "processed"
    filepath = SAVE_FOLDER / f"{model_name}.csv"

    df = pd.read_csv(filepath).drop("season", axis=1)

    pd_dataset = from_pandas(df, source=str(filepath), name=study_name, targets="goal")

    X = df.drop("goal", axis=1)
    y = df["goal"].copy()

    X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=SEED, shuffle=True, stratify=y)

    if model_name == "empty_against":
        scale_pos_weight = 1.0
    else:
        scale_pos_weight = y_train.loc[y_train == 0].count() / y_train.loc[y_train == 1].count()

    return X_train, X_test, y_train, y_test, scale_pos_weight, pd_dataset


def _objective(trial: optuna.Trial, data: ExperimentData) -> tuple[float, float, float]:
    """Optuna objective function."""
    warnings.filterwarnings("ignore")

    with mlflow.start_run(run_id=data.parent_info.run_id):
        with mlflow.start_run(nested=True) as current_run:
            params: dict[str, Any] = {
                "objective": "binary:logistic",
                "verbosity": 0,
                "random_state": SEED,
                "max_depth": trial.suggest_int("max_depth", 3, 15),
                "min_child_weight": trial.suggest_int("min_child_weight", 2, 10),
                "max_delta_step": trial.suggest_int("max_delta_step", 1, 10),
                "scale_pos_weight": trial.suggest_float("scale_pos_weight", 1.0, data.scale_pos_weight),
                "learning_rate": trial.suggest_float("learning_rate", 1e-8, 1.0, log=True),
                "gamma": trial.suggest_float("gamma", 1e-8, 1.0, log=True),
                "lambda": trial.suggest_float("lambda", 1e-8, 1.0, log=True),
                "alpha": trial.suggest_float("alpha", 1e-8, 1.0, log=True),
                "subsample": trial.suggest_float("subsample", 0.4, 1.0, step=0.05),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.4, 1.0, step=0.05),
            }

            run_data = current_run.info

            experiment_id = run_data.experiment_id

            mlflow.log_params(params)
            model_params = dict(params)  # capture before eval_metric is added (list, not loggable as param)

            params["eval_metric"] = ["auc", "logloss"]

            model = xgb.XGBClassifier(**params)

            kfold = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)

            evals = cross_validate(
                model,
                data.X_train,
                data.y_train,
                scoring=["roc_auc", "precision", "recall", "f1", "accuracy", "neg_log_loss"],
                cv=kfold,
                n_jobs=-1,
            )

            train_metrics: dict[str, float] = {}

            for metric, results in evals.items():
                metric = metric.replace("test_", "")

                if metric == "neg_log_loss":
                    metric = metric.replace("neg_", "")
                    results = [x * -1 for x in results]

                train_metrics.update({f"train_{metric}_mean": np.mean(results), f"train_{metric}_std": np.std(results)})

            mlflow.log_metrics(train_metrics)

            evals_df = pd.DataFrame(evals)
            evals_df["kfold"] = evals_df.index + 1
            evals_df = evals_df.set_index("kfold")
            evals_html = evals_df.to_html(na_rep="", float_format=lambda x: str(round(x, 3)))
            mlflow.log_text(evals_html, "performance/train_cross_validation.html")

            model.fit(data.X_train, data.y_train, eval_set=[(data.X_test, data.y_test)], verbose=False)

            # Log all effective XGBoost params (including defaults) to the run entity
            all_xgb_params = model.get_xgb_params()
            extra_params = {k: str(v) for k, v in all_xgb_params.items() if k not in model_params}
            if extra_params:
                mlflow.log_params(extra_params)

            ts = int(pd.Timestamp.now().timestamp() * 1000)
            boosting_metrics = [
                Metric(f"boosting_{metric_name}", value, ts, step)
                for metric_name, values in model.evals_result()["validation_0"].items()
                for step, value in enumerate(values)
            ]
            client = mlflow.tracking.MlflowClient()
            for i in range(0, len(boosting_metrics), 1000):
                client.log_batch(current_run.info.run_id, metrics=boosting_metrics[i : i + 1000])

            mlflow.log_dict(model.get_booster().get_fscore(), "artifacts/feature_importance.json")

            y_preds = model.predict(data.X_test)
            y_probs = model.predict_proba(data.X_test)[:, 1]

            degenerate = len(np.unique(y_preds)) < 2

            run_name = current_run.info.run_name
            signature = infer_signature(data.X_test, y_preds)
            model_info = mlflow.xgboost.log_model(model, name=run_name, signature=signature)
            logged_model = LoggedModelInput(model_id=model_info.model_id) if model_info.model_id else None
            mlflow.log_input(data.pd_dataset, context="training", model=logged_model)

            test_metrics = {f"test_{k}": float(v) for k, v in model_metrics(data.y_test, y_preds, y_probs).items()}

            mlflow.log_metrics(test_metrics)

            roc = test_metrics["test_roc_auc"]
            precision = test_metrics["test_precision"]

            if roc < PERF_NONE or precision == 0:
                performance_tag = "none"
            elif roc < PERF_LOW:
                performance_tag = "low"
            elif roc < PERF_MEDIUM:
                performance_tag = "medium"
            elif roc <= PERF_HIGH:
                performance_tag = "high"
            else:
                performance_tag = "very high"

            tags = {
                "performance": performance_tag,
                "experiment_name": data.study_name,
                "experiment_id": experiment_id,
                "estimator_name": model.__class__.__name__,
                "estimator_class": model.__class__,
                "parent_id": data.parent_info.run_id,
                "parent_name": data.parent_info.run_name,
                "level": "child",
            }

            mlflow.set_tags(tags)

            class_report = sklearn.metrics.classification_report(
                data.y_test, y_preds, labels=[0, 1], target_names=["no goal", "goal"], output_dict=True, zero_division=0
            )

            class_report_html = pd.DataFrame(class_report).to_html(na_rep="", float_format=lambda x: str(round(x, 3)))
            mlflow.log_text(class_report_html, "performance/test_classification_report.html")

            if not degenerate:
                model._estimator_type = "classifier"  # XGBoost 3.x dropped this attribute; yellowbrick requires it
                (
                    classification_report,
                    roc_auc,
                    class_prediction,
                    precision_recall,
                    importance,
                    relative_importance,
                    confusion_matrix,
                ) = model_viz(model, data.X_train, data.y_train, data.X_test, data.y_test)

                log_viz(
                    classification_report,
                    roc_auc,
                    class_prediction,
                    precision_recall,
                    importance,
                    relative_importance,
                    confusion_matrix,
                )

            return (test_metrics["test_roc_auc"], test_metrics["test_log_loss"], test_metrics["test_f1"])


def tune_model(
    model_name: str, version: str, storage: optuna.storages.RDBStorage, max_trials: int, run: str | None = None
) -> optuna.Study:
    """Wraps all of the tuning functions into one."""
    study_name = f"{model_name}-{version}"

    mlflow.enable_system_metrics_logging()

    EXPERIMENT = mlflow.set_experiment(study_name)
    experiment_id = EXPERIMENT.experiment_id

    tags = {"experiment_name": study_name, "experiment_id": experiment_id, "level": "parent"}

    X_train, X_test, y_train, y_test, scale_pos_weight, pd_dataset = load_data(model_name, study_name)

    run_id = run

    if run_id is None:
        with mlflow.start_run(tags=tags) as parent_run:
            parent_info = parent_run.info
    else:
        with mlflow.start_run(run_id=run_id) as parent_run:
            parent_info = parent_run.info

    data = ExperimentData(
        X_train=X_train,
        X_test=X_test,
        y_train=y_train,
        y_test=y_test,
        scale_pos_weight=scale_pos_weight,
        pd_dataset=pd_dataset,
        study_name=study_name,
        parent_info=parent_info,
    )

    try:
        study = optuna.create_study(
            study_name=study_name, load_if_exists=True, storage=storage, directions=["maximize", "minimize", "maximize"]
        )
    except optuna.exceptions.StorageInternalError:
        study = optuna.load_study(study_name=study_name, storage=storage)

    study.set_metric_names(["roc_auc", "log_loss", "f1"])

    study.optimize(functools.partial(_objective, data=data), n_trials=max_trials, show_progress_bar=True)

    return study


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="xG Training", description="Python script for training xG model")
    parser.add_argument("--strength", "-s", type=str, required=True)
    parser.add_argument("--version", "-v", type=str, required=True)
    parser.add_argument("--run", "-r", type=str, required=False)
    parser.add_argument("--trials", "-t", type=int, required=False)
    parser.add_argument("--delete", "-d", action="store_true")
    args = parser.parse_args()

    if args.strength not in STRENGTHS:
        raise Exception(f"Strength name is not supported, try: {', '.join(STRENGTHS)}")

    sns.set_style("white")

    warnings.filterwarnings("ignore")

    load_dotenv()

    model_name = args.strength
    version = args.version
    trials = args.trials if args.trials is not None else 100
    run = args.run if args.run is not None else None

    db_host = os.environ.get("DB_HOST")
    db_user = os.environ["DB_USER"]
    db_password = os.environ["DB_PASSWORD"]
    db_name = os.environ["DB_NAME"]
    db_port = os.environ["DB_PORT"]

    optuna_postgres_url = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    storage = optuna.storages.RDBStorage(url=optuna_postgres_url, skip_compatibility_check=True)

    if args.delete:
        optuna.delete_study(study_name=f"{model_name}-{version}", storage=storage)

    study = tune_model(model_name=model_name, version=version, storage=storage, max_trials=trials, run=run)
