"""Retrain best base_xg model on all training data, score all historical PBP, and freeze.

Reads the best Optuna trial (by PR-AUC) from the given study, retrains on the full
training parquet, scores both train and hold_out shots, then writes:

  data/base_xg/scored/{strength}.parquet  — all shots with base_xg appended
  data/base_xg/models/{strength}.ubj      — frozen XGBoost booster

Usage:
    python finalize_base_xg.py --strength even_strength --version v1
"""

import argparse
import os
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import mlflow
import mlflow.xgboost
import optuna
import pandas as pd
import seaborn as sns
import xgboost as xgb
from dotenv import load_dotenv
from mlflow.models.signature import infer_signature

from experiments import PASSTHROUGH_COLS, SEED, STRENGTHS, _apply_fixed_categoricals, log_viz, model_metrics, model_viz

# Columns retained in parquets for downstream joins but excluded from the feature matrix
NON_FEATURE_COLS = ["goal", "season"] + PASSTHROUGH_COLS


def _split_df(df: pd.DataFrame, strength: str) -> tuple[pd.DataFrame, pd.Series]:
    """Return (X_features, y) from a parquet DataFrame."""
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
    parser = argparse.ArgumentParser(description="Retrain and freeze best base_xg model")
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

    study_name = f"{args.strength}-{args.version}-base_xg"
    study = optuna.load_study(study_name=study_name, storage=storage)
    best_params, best_trial_num = _best_params(study)

    data_dir = Path(__file__).parent / "data" / "base_xg"
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
        "monotone_constraints": {
            col: direction
            for col, direction in {"event_distance": -1, "event_angle": -1, "play_speed": 1}.items()
            if col in X_train.columns
        },
        **best_params,
    }

    model = xgb.XGBClassifier(**params)
    model.fit(X_train, y_train, eval_set=[(X_hold_out, y_hold_out)], early_stopping_rounds=50, verbose=False)

    # Score all shots (train + hold_out) for the informed_xg cascade
    all_df = (
        pd.concat([train_df, hold_out_df], ignore_index=True)
        .sort_values(["season", "game_id", "period", "period_seconds"])
        .reset_index(drop=True)
    )
    X_all, _ = _split_df(all_df, args.strength)
    all_df = all_df.assign(base_xg=model.predict_proba(X_all)[:, 1])

    scored_dir = data_dir / "scored"
    scored_dir.mkdir(parents=True, exist_ok=True)
    all_df.to_parquet(scored_dir / f"{args.strength}.parquet", index=False)

    models_dir = data_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    model.get_booster().save_model(str(models_dir / f"{args.strength}.ubj"))

    # Evaluate on hold_out and log to MLflow
    mlflow.enable_system_metrics_logging()
    mlflow.set_experiment(study_name)

    y_preds = model.predict(X_hold_out)
    y_probs = model.predict_proba(X_hold_out)[:, 1]
    hold_out_metrics = {f"hold_out_{k}": float(v) for k, v in model_metrics(y_hold_out, y_preds, y_probs).items()}

    signature = infer_signature(X_hold_out, y_preds)

    with mlflow.start_run(
        tags={"type": "finalize", "strength": args.strength, "version": args.version, "best_trial": str(best_trial_num)}
    ):
        mlflow.log_params({**params, "monotone_constraints": str(params["monotone_constraints"])})
        mlflow.log_metric("best_iteration", float(model.best_iteration or 0))
        mlflow.log_metrics(hold_out_metrics)

        model._estimator_type = "classifier"
        (
            classification_report,
            roc_auc,
            class_prediction,
            precision_recall,
            importance,
            relative_importance,
            confusion_matrix,
        ) = model_viz(model, X_train, y_train, X_hold_out, y_hold_out)

        log_viz(
            classification_report,
            roc_auc,
            class_prediction,
            precision_recall,
            importance,
            relative_importance,
            confusion_matrix,
        )

        mlflow.xgboost.log_model(model, name=f"base_xg-{args.strength}-final", signature=signature)


if __name__ == "__main__":
    main()
