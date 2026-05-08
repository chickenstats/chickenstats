# Script for running mlflow experiments and logging them to mlflow on GCP #

# Import dependencies

import argparse
import functools
import os
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
from sklearn.model_selection import TimeSeriesSplit, cross_validate
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
MODELS = ["env_xg", "informed_xg"]
PASSTHROUGH_COLS = ["game_id", "player_1_api_id", "opp_goalie_api_id", "session", "home_on_api_id", "away_on_api_id"]

SHOT_TYPES = [
    "backhand",
    "bat",
    "between_legs",
    "cradle",
    "deflected",
    "poke",
    "slap",
    "snap",
    "tip_in",
    "wrap_around",
    "wrist",
]
POSITIONS = ["D", "F", "G"]
SESSIONS = ["R", "P"]
STRENGTH_STATE_CATS = {
    "even_strength": ["3v3", "4v4", "5v5"],
    "powerplay": ["4v3", "5v3", "5v4"],
    "shorthanded": ["3v4", "3v5", "4v5"],
    "empty_for": ["Ev3", "Ev4", "Ev5"],
    "empty_against": ["3vE", "4vE", "5vE"],
}


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
    model: str = "env_xg"


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


def _apply_fixed_categoricals(X: pd.DataFrame, model_name: str) -> pd.DataFrame:
    """Cast shot_type, position, and strength_state to pd.Categorical with fixed category lists."""
    cat_map = {
        "shot_type": SHOT_TYPES,
        "position": POSITIONS,
        "strength_state": STRENGTH_STATE_CATS[model_name],
        "session": SESSIONS,
    }
    for col, cats in cat_map.items():
        if col in X.columns:
            X[col] = pd.Categorical(X[col], categories=cats)
    return X


def load_data(
    model_name: str, study_name: str, model: str = "env_xg"
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, float, PandasDataset]:
    """Load and split processed data for a given strength state and model type."""
    folder = "train" if model == "env_xg" else "train"
    SAVE_FOLDER = Path(__file__).parent / "data" / model / folder
    filepath = SAVE_FOLDER / f"{model_name}.parquet"

    df = pd.read_parquet(filepath)
    df = df.sort_values("season").reset_index(drop=True)
    season = df.pop("season")

    # Drop passthrough columns — present in parquets for downstream joins, not training features
    passthrough = [c for c in PASSTHROUGH_COLS if c in df.columns]
    if passthrough:
        df = df.drop(passthrough, axis=1)

    pd_dataset = from_pandas(df, source=str(filepath), name=study_name, targets="goal")

    X = df.drop("goal", axis=1)
    y = df["goal"].copy()

    # Chronological split: train on 2010-11 through 2022-23, test on 2023-24
    train_mask = season <= 20222023
    X_train = X.loc[train_mask].reset_index(drop=True)
    X_test = X.loc[~train_mask].reset_index(drop=True)
    y_train = y.loc[train_mask].reset_index(drop=True)
    y_test = y.loc[~train_mask].reset_index(drop=True)

    X_train = _apply_fixed_categoricals(X_train, model_name)
    X_test = _apply_fixed_categoricals(X_test, model_name)

    if model_name == "empty_against":
        scale_pos_weight = 1.0
    else:
        scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()

    return X_train, X_test, y_train, y_test, scale_pos_weight, pd_dataset


def _build_model(params: dict[str, Any]) -> xgb.XGBClassifier:
    """Instantiate XGBClassifier from a params dict."""
    return xgb.XGBClassifier(**params)


def _objective(trial: optuna.Trial, data: ExperimentData) -> tuple[float, float, float]:
    """Optuna objective function."""
    warnings.filterwarnings("ignore")

    with mlflow.start_run(run_id=data.parent_info.run_id):
        with mlflow.start_run(nested=True) as current_run:
            trial.set_user_attr("mlflow_run_id", current_run.info.run_id)
            params: dict[str, Any] = {
                "objective": "binary:logistic",
                "verbosity": 0,
                "random_state": SEED,
                "n_estimators": 500,
                "enable_categorical": True,
                "monotone_constraints": {"event_distance": -1, "event_angle": -1, "play_speed": 1}
                | ({"env_xg": 1} if data.model == "informed_xg" else {}),
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

            mlflow.log_params({**params, "monotone_constraints": str(params["monotone_constraints"])})
            model_params = dict(params)  # capture before eval_metric is added (list, not loggable as param)

            params["eval_metric"] = ["auc", "logloss"]

            model = _build_model(params)

            kfold = TimeSeriesSplit(n_splits=5)

            evals = cross_validate(
                model,
                data.X_train,
                data.y_train,
                scoring=["roc_auc", "average_precision", "precision", "recall", "f1", "accuracy", "neg_log_loss"],
                cv=kfold,
                n_jobs=1,
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

            prauc = test_metrics["test_average_precision"]
            log_loss_val = test_metrics["test_log_loss"]

            if log_loss_val >= 0.28 or prauc < 0.15:
                performance_tag = "none"
            elif prauc >= 0.45 and log_loss_val <= 0.20:
                performance_tag = "very high"
            elif prauc >= 0.35 and log_loss_val <= 0.23:
                performance_tag = "high"
            elif prauc >= 0.25 and log_loss_val <= 0.25:
                performance_tag = "medium"
            else:
                performance_tag = "low"

            tags = {
                "performance": performance_tag,
                "experiment_name": data.study_name,
                "experiment_id": experiment_id,
                "estimator_name": model.__class__.__name__,
                "estimator_class": model.__class__,
                "parent_id": data.parent_info.run_id,
                "parent_name": data.parent_info.run_name,
                "level": "child",
                "optuna_trial_num": str(trial.number),
            }

            mlflow.set_tags(tags)

            class_report = sklearn.metrics.classification_report(
                data.y_test, y_preds, labels=[0, 1], target_names=["no goal", "goal"], output_dict=True, zero_division=0
            )

            class_report_html = pd.DataFrame(class_report).to_html(na_rep="", float_format=lambda x: str(round(x, 3)))
            mlflow.log_text(class_report_html, "performance/test_classification_report.html")

            if not degenerate and performance_tag in ("medium", "high", "very high"):
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

            return (test_metrics["test_average_precision"], test_metrics["test_log_loss"], test_metrics["test_f1"])


def tune_model(
    model_name: str,
    version: str,
    storage: optuna.storages.RDBStorage,
    max_trials: int,
    run: str | None = None,
    model: str = "env_xg",
) -> optuna.Study:
    """Wraps all of the tuning functions into one."""
    study_name = f"{model_name}-{version}-{model}"

    mlflow.enable_system_metrics_logging()

    EXPERIMENT = mlflow.set_experiment(study_name)
    experiment_id = EXPERIMENT.experiment_id

    tags = {"experiment_name": study_name, "experiment_id": experiment_id, "level": "parent", "model": model}

    X_train, X_test, y_train, y_test, scale_pos_weight, pd_dataset = load_data(model_name, study_name, model=model)

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
        model=model,
    )

    try:
        study = optuna.create_study(
            study_name=study_name,
            load_if_exists=True,
            storage=storage,
            directions=["maximize", "minimize", "maximize"],
            pruner=optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=1),
        )
    except optuna.exceptions.StorageInternalError:
        study = optuna.load_study(study_name=study_name, storage=storage)

    study.set_metric_names(["average_precision", "log_loss", "f1"])

    study.optimize(functools.partial(_objective, data=data), n_trials=max_trials, show_progress_bar=True)

    # Log best-trial summary to parent run so it's visible without expanding child runs
    completed = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE and t.values]
    if completed:
        best = max(completed, key=lambda t: t.values[0])
        best_values = best.values or []
        with mlflow.start_run(run_id=parent_info.run_id):
            mlflow.log_metrics(
                {"best_pr_auc": best_values[0], "best_log_loss": best_values[1], "best_f1": best_values[2]}
            )
            mlflow.log_params({"best_" + k: str(v) for k, v in best.params.items()})
            mlflow.set_tag("best_trial_num", str(best.number))

    return study


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="xG Training", description="Python script for training xG model")
    parser.add_argument("--strength", "-s", type=str, required=True)
    parser.add_argument("--version", "-v", type=str, required=True)
    parser.add_argument("--model", "-m", type=str, required=False, default="env_xg")
    parser.add_argument("--run", "-r", type=str, required=False)
    parser.add_argument("--trials", "-t", type=int, required=False)
    parser.add_argument("--delete", "-d", action="store_true")
    args = parser.parse_args()

    if args.strength not in STRENGTHS:
        raise Exception(f"Strength name is not supported, try: {', '.join(STRENGTHS)}")

    if args.model not in MODELS:
        raise Exception(f"Model name is not supported, try: {', '.join(MODELS)}")

    sns.set_style("white")

    warnings.filterwarnings("ignore")

    load_dotenv()

    model_name = args.strength
    version = args.version
    model = args.model
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
        optuna.delete_study(study_name=f"{model_name}-{version}-{model}", storage=storage)

    study = tune_model(model_name=model_name, version=version, storage=storage, max_trials=trials, run=run, model=model)
