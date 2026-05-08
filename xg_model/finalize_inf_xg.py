"""Retrain best informed_xg model, calibrate, generate SHAP, and freeze.

Reads the best Optuna trial (by PR-AUC) from the given study, retrains on the full
training parquet, wraps in CalibratedClassifierCV (isotonic, cv=5), then writes:

  data/informed_xg/models/{strength}.joblib  — calibrated model (sklearn wrapper)
  data/informed_xg/models/{strength}_base.ubj — base XGBoost booster (for inspection)

Usage:
    python finalize_inf_xg.py --strength even_strength --version v1
"""

import argparse
import os
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import joblib
import mlflow
import mlflow.sklearn
import mlflow.xgboost
import numpy as np
import optuna
import pandas as pd
import seaborn as sns
import shap
import xgboost as xgb
from dotenv import load_dotenv
from mlflow.models.signature import infer_signature
from sklearn.calibration import CalibratedClassifierCV

from experiments import PASSTHROUGH_COLS, SEED, STRENGTHS, _apply_fixed_categoricals, log_viz, model_metrics, model_viz

# Columns excluded from the feature matrix
NON_FEATURE_COLS = ["goal", "season"] + PASSTHROUGH_COLS


def _split_df(df: pd.DataFrame, strength: str) -> tuple[pd.DataFrame, pd.Series]:
    """Return (X_features, y) dropping all non-feature columns."""
    y = df["goal"].copy()
    drop = [c for c in NON_FEATURE_COLS if c in df.columns]
    X = _apply_fixed_categoricals(df.drop(columns=drop), strength)
    return X, y


def _best_params(study: optuna.Study) -> tuple[dict, int]:
    """Select best completed trial by PR-AUC (multi-objective values[0])."""
    completed = [t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE]
    if not completed:
        raise RuntimeError("No completed trials in study — run experiments.py first.")
    best = max(completed, key=lambda t: t.values[0])
    return best.params, best.number


def main() -> None:
    """Docstring."""
    parser = argparse.ArgumentParser(description="Retrain and freeze best informed_xg model")
    parser.add_argument("--strength", "-s", type=str, required=True)
    parser.add_argument("--version", "-v", type=str, required=True)
    args = parser.parse_args()

    if args.strength not in STRENGTHS:
        raise ValueError(f"Unknown strength: {args.strength}. Choose from: {', '.join(STRENGTHS)}")

    warnings.filterwarnings("ignore")
    sns.set_style("white")
    load_dotenv()

    db_user = os.environ["DB_USER"]
    db_password = os.environ["DB_PASSWORD"]
    db_host = os.environ.get("DB_HOST")
    db_name = os.environ["DB_NAME"]
    db_port = os.environ["DB_PORT"]
    storage = optuna.storages.RDBStorage(
        url=f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}",
        skip_compatibility_check=True,
    )

    study_name = f"{args.strength}-{args.version}-informed_xg"
    study = optuna.load_study(study_name=study_name, storage=storage)
    best_params, best_trial_num = _best_params(study)

    data_dir = Path(__file__).parent / "data" / "informed_xg"
    train_df = pd.read_parquet(data_dir / "train" / f"{args.strength}.parquet")
    hold_out_df = pd.read_parquet(data_dir / "hold_out" / f"{args.strength}.parquet")

    X_train, y_train = _split_df(train_df, args.strength)
    X_hold_out, y_hold_out = _split_df(hold_out_df, args.strength)

    params = {
        "objective": "binary:logistic",
        "verbosity": 0,
        "random_state": SEED,
        "n_estimators": 500,
        "enable_categorical": True,
        "eval_metric": ["auc", "logloss"],
        "monotone_constraints": {"event_distance": -1, "event_angle": -1, "play_speed": 1, "env_xg": 1},
        **best_params,
    }

    base_model = xgb.XGBClassifier(**params)
    base_model.fit(X_train, y_train, eval_set=[(X_hold_out, y_hold_out)], early_stopping_rounds=50, verbose=False)

    # Calibrate with isotonic regression (5-fold CV on training data)
    calibrated_model = CalibratedClassifierCV(base_model, method="isotonic", cv=5)
    calibrated_model.fit(X_train, y_train)

    # SHAP summary on a sample of hold-out data (TreeExplainer uses the base booster)
    explainer = shap.TreeExplainer(base_model)
    shap_sample = X_hold_out.sample(min(2000, len(X_hold_out)), random_state=SEED)
    shap_values = explainer.shap_values(shap_sample)

    models_dir = data_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    joblib.dump(calibrated_model, models_dir / f"{args.strength}.joblib")
    base_model.get_booster().save_model(str(models_dir / f"{args.strength}_base.ubj"))

    # Evaluate on hold_out and log to MLflow
    mlflow.enable_system_metrics_logging()
    mlflow.set_experiment(study_name)

    y_preds = calibrated_model.predict(X_hold_out)
    y_probs = calibrated_model.predict_proba(X_hold_out)[:, 1]
    hold_out_metrics = {f"hold_out_{k}": float(v) for k, v in model_metrics(y_hold_out, y_preds, y_probs).items()}

    signature = infer_signature(X_hold_out, y_probs)

    with mlflow.start_run(
        tags={"type": "finalize", "strength": args.strength, "version": args.version, "best_trial": str(best_trial_num)}
    ):
        mlflow.log_params({**params, "monotone_constraints": str(params["monotone_constraints"])})
        mlflow.log_metric("best_iteration", float(base_model.best_iteration or 0))
        mlflow.log_metrics(hold_out_metrics)

        # SHAP summary plot
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(dpi=100, figsize=(8, 6))
        shap.summary_plot(shap_values, shap_sample, show=False, max_display=20)
        mlflow.log_figure(plt.gcf(), "viz/shap_summary.png")
        plt.close()

        base_model._estimator_type = "classifier"
        (
            classification_report,
            roc_auc,
            class_prediction,
            precision_recall,
            importance,
            relative_importance,
            confusion_matrix,
        ) = model_viz(base_model, X_train, y_train, X_hold_out, y_hold_out)

        log_viz(
            classification_report,
            roc_auc,
            class_prediction,
            precision_recall,
            importance,
            relative_importance,
            confusion_matrix,
        )

        mlflow.sklearn.log_model(calibrated_model, name=f"informed_xg-{args.strength}-calibrated", signature=signature)


if __name__ == "__main__":
    main()
