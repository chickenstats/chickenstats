import re
import os
from pathlib import Path
from dotenv import load_dotenv

import pandas as pd
import numpy as np

import mlflow
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split

import matplotlib.pyplot as plt
import seaborn as sns
import shap
from yellowbrick.classifier import (
    ClassificationReport,
    ClassPredictionError,
    ROCAUC,
    PrecisionRecallCurve,
    ConfusionMatrix,
)
from yellowbrick.model_selection import FeatureImportances

from chickenstats.chicken_nhl.validation import XGSchema


class ChickenModel:
    """Docstring for ChickenModel."""

    def __init__(self, run_id: str, client: mlflow.MlflowClient, data: pd.DataFrame):
        """Docstring for ChickenModel."""
        self.run_id = run_id
        self.client = client
        self.raw_data = data

        self.encoder = {0: "no goal", 1: "goal"}

        self._process_data()

        self._get_run()

        self._get_model()

    def _process_data(self):
        """Process data into X / y and test / train datasets."""
        self.X = self.raw_data.drop(["season", "goal"], axis=1)
        self.y = self.raw_data["goal"].copy(deep=True)

        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            self.X, self.y, random_state=615, shuffle=True, stratify=self.y
        )

    def _get_run(self):
        """Download MLFlow run information."""
        self.run = self.client.get_run(self.run_id)

        self.run_name = self.run.info.run_name

        self.experiment_name = self.run.data.tags["experiment_name"]

        experiment_split = self.experiment_name.split("-")

        self.experiment_strength = experiment_split[0]

        self.experiment_version = experiment_split[1]

    def _get_model(self):
        """Download MLFlow model information."""
        self.model = mlflow.xgboost.load_model(f"runs:/{self.run_id}/model")

    def save_model(self, filepath: Path | str) -> None:
        """Docstring."""
        if isinstance(filepath, str):
            filepath = Path(filepath)

        self.model.save_model(filepath)

    def _process_shap(self):
        """Generate SHAP explainer and SHAP values."""
        self.shap_explainer = shap.Explainer(self.model, self.X)

        self.shap_values = self.shap_explainer(self.X)

    def shap_swarm(
        self,
        max_display=30,
        suptitle=None,
        suptitle_xy=(0.35, 0.93),
        suptitle_fontsize=18,
        subtitle=None,
        subtitle_xy=(0.35, 0.912),
        subtitle_fontsize=13,
        save_img=False,
        dpi=750,
        figsize=(4, 6),
    ):
        """Generate SHAP beeswarm plot."""
        self._process_shap()

        fig, ax = plt.subplots(dpi=dpi, figsize=figsize)

        ax = shap.plots.beeswarm(
            self.shap_values, max_display=max_display, show=False, alpha=0.875
        )

        if not suptitle:
            suptitle = f"chickenstats.chicken_nhl xG feature performance"

        fig.suptitle(
            suptitle,
            x=suptitle_xy[0],
            y=suptitle_xy[1],
            size=suptitle_fontsize,
            weight="bold",
            ha="center",
            va="center",
        )

        if not subtitle:
            subtitle = f"SHAP values for {self.experiment_strength.replace('_', ' ')} xG model | {self.run_name} ({self.experiment_name})"

        fig.text(
            s=subtitle,
            x=subtitle_xy[0],
            y=subtitle_xy[1],
            size=subtitle_fontsize,
            ha="center",
            va="center",
        )

        if save_img:
            save_directory = Path(
                f"../charts/{self.experiment_strength}/{self.experiment_version}/{self.run_name}"
            )

            if not save_directory.exists():
                save_directory.mkdir(parents=True)

            savepath = save_directory / f"{self.run_name}_shap.png"

            fig.savefig(savepath, bbox_inches="tight", facecolor="white")

        return fig

    def class_report(
        self,
        suptitle=None,
        suptitle_xy=(0.5, 1.025),
        suptitle_fontsize=18,
        subtitle=None,
        subtitle_xy=(0.5, 0.985),
        subtitle_fontsize=13,
        save_img=False,
        dpi=750,
        figsize=(10, 6),
    ):
        """Generate classification report using YellowBrick."""
        fig, ax = plt.subplots(dpi=dpi, figsize=figsize)

        viz = ClassificationReport(
            self.model, encoder=self.encoder, support=True, cmap="RdPu", ax=ax
        )

        viz.fit(self.X, self.y)

        viz.score(self.X, self.y)

        viz.finalize()

        viz.set_title("")

        if not suptitle:
            suptitle = f"chickenstats.chicken_nhl xG model performance"

        fig.suptitle(
            suptitle,
            x=suptitle_xy[0],
            y=suptitle_xy[1],
            size=suptitle_fontsize,
            weight="bold",
            ha="center",
            va="center",
        )

        if not subtitle:
            subtitle = f"Classification report for {self.experiment_strength.replace('_', ' ')} xG model | {self.run_name} ({self.experiment_name})"

        fig.text(
            s=subtitle,
            x=subtitle_xy[0],
            y=subtitle_xy[1],
            size=subtitle_fontsize,
            ha="center",
            va="center",
        )

        if save_img:
            save_directory = Path(
                f"../charts/{self.experiment_strength}/{self.experiment_version}/{self.run_name}"
            )

            if not save_directory.exists():
                save_directory.mkdir(parents=True)

            savepath = save_directory / f"{self.run_name}_class_report.png"

            fig.savefig(savepath, bbox_inches="tight", facecolor="white")

        return fig

    def confusion_matrix(
        self,
        suptitle=None,
        suptitle_xy=(0.5, 1.025),
        suptitle_fontsize=18,
        subtitle=None,
        subtitle_xy=(0.5, 0.985),
        subtitle_fontsize=13,
        save_img=False,
        dpi=750,
        figsize=(10, 6),
    ):
        """Generate confusion matrix using YellowBrick."""
        fig, ax = plt.subplots(dpi=dpi, figsize=figsize)

        viz = ConfusionMatrix(self.model, cmap="RdPu", encoder=self.encoder)

        viz.fit(self.X, self.y)

        viz.score(self.X, self.y)

        viz.finalize()

        viz.set_title("")

        if not suptitle:
            suptitle = f"chickenstats.chicken_nhl xG model performance"

        fig.suptitle(
            suptitle,
            x=suptitle_xy[0],
            y=suptitle_xy[1],
            size=suptitle_fontsize,
            weight="bold",
            ha="center",
            va="center",
        )

        if not subtitle:
            subtitle = f"Confusion matrix for {self.experiment_strength.replace('_', ' ')} xG model | {self.run_name} ({self.experiment_name})"

        fig.text(
            s=subtitle,
            x=subtitle_xy[0],
            y=subtitle_xy[1],
            size=subtitle_fontsize,
            ha="center",
            va="center",
        )

        if save_img:
            save_directory = Path(
                f"../charts/{self.experiment_strength}/{self.experiment_version}/{self.run_name}"
            )

            if not save_directory.exists():
                save_directory.mkdir(parents=True)

            savepath = save_directory / f"{self.run_name}_confusion_matrix.png"

            fig.savefig(savepath, bbox_inches="tight", facecolor="white")

        return fig

    def feature_importance(
        self,
        topn=10,
        suptitle=None,
        suptitle_xy=(0.5, 1.025),
        suptitle_fontsize=18,
        subtitle=None,
        subtitle_xy=(0.5, 0.985),
        subtitle_fontsize=13,
        save_img=False,
        dpi=750,
        figsize=(10, 6),
    ):
        """Generate feature importance chart using YellowBrick."""
        fig, ax = plt.subplots(dpi=dpi, figsize=figsize)

        viz = FeatureImportances(self.model, relative=False, ax=ax, topn=topn)

        viz.fit(self.X, self.y)

        viz.score(self.X, self.y)  # Evaluate the model on the test data

        viz.finalize()

        viz.set_title("")

        if not suptitle:
            suptitle = f"chickenstats.chicken_nhl xG model performance"

        fig.suptitle(
            suptitle,
            x=suptitle_xy[0],
            y=suptitle_xy[1],
            size=suptitle_fontsize,
            weight="bold",
            ha="center",
            va="center",
        )

        if not subtitle:
            subtitle = f"Top-{topn} feature importances for {self.experiment_strength.replace('_', ' ')} xG model | {self.run_name} ({self.experiment_name})"

        fig.text(
            s=subtitle,
            x=subtitle_xy[0],
            y=subtitle_xy[1],
            size=subtitle_fontsize,
            ha="center",
            va="center",
        )

        if save_img:
            save_directory = Path(
                f"../charts/{self.experiment_strength}/{self.experiment_version}/{self.run_name}"
            )

            if not save_directory.exists():
                save_directory.mkdir(parents=True)

            savepath = save_directory / f"{self.run_name}_feature_importance.png"

            fig.savefig(savepath, bbox_inches="tight", facecolor="white")

        return fig

    def rel_feature_importance(
        self,
        topn=10,
        suptitle=None,
        suptitle_xy=(0.5, 1.025),
        suptitle_fontsize=18,
        subtitle=None,
        subtitle_xy=(0.5, 0.985),
        subtitle_fontsize=13,
        save_img=False,
        dpi=750,
        figsize=(10, 6),
    ):
        """Generate relative feature importances using YellowBrick."""
        fig, ax = plt.subplots(dpi=dpi, figsize=figsize)

        viz = FeatureImportances(self.model, relative=True, ax=ax, topn=topn)

        viz.fit(self.X, self.y)

        viz.score(self.X, self.y)  # Evaluate the model on the test data

        viz.finalize()

        viz.set_title("")

        if not suptitle:
            suptitle = f"chickenstats.chicken_nhl xG model performance"

        fig.suptitle(
            suptitle,
            x=suptitle_xy[0],
            y=suptitle_xy[1],
            size=suptitle_fontsize,
            weight="bold",
            ha="center",
            va="center",
        )

        if not subtitle:
            subtitle = f"Top-{topn} relative feature importances for {self.experiment_strength.replace('_', ' ')} xG model | {self.run_name} ({self.experiment_name})"

        fig.text(
            s=subtitle,
            x=subtitle_xy[0],
            y=subtitle_xy[1],
            size=subtitle_fontsize,
            ha="center",
            va="center",
        )

        if save_img:
            save_directory = Path(
                f"../charts/{self.experiment_strength}/{self.experiment_version}/{self.run_name}"
            )

            if not save_directory.exists():
                save_directory.mkdir(parents=True)

            savepath = save_directory / f"{self.run_name}_rel_feature_importance.png"

            fig.savefig(savepath, bbox_inches="tight", facecolor="white")

        return fig

    def roc_auc(
        self,
        suptitle=None,
        suptitle_xy=(0.5, 0.995),
        suptitle_fontsize=18,
        subtitle=None,
        subtitle_xy=(0.5, 0.945),
        subtitle_fontsize=13,
        save_img=False,
        dpi=750,
        figsize=(10, 6),
    ):
        """Generate ROC-AUC chart using YellowBrick."""
        fig, ax = plt.subplots(dpi=dpi, figsize=figsize)

        viz = ROCAUC(self.model, encoder=self.encoder)

        viz.fit(self.X, self.y)

        viz.score(self.X, self.y)  # Evaluate the model on the test data

        viz.finalize()

        viz.set_title("")

        if not suptitle:
            suptitle = f"chickenstats.chicken_nhl xG model performance"

        fig.suptitle(
            suptitle,
            x=suptitle_xy[0],
            y=suptitle_xy[1],
            size=suptitle_fontsize,
            weight="bold",
            ha="center",
            va="center",
        )

        if not subtitle:
            subtitle = f"ROC-AUC for {self.experiment_strength.replace('_', ' ')} xG model | {self.run_name} ({self.experiment_name})"

        fig.text(
            s=subtitle,
            x=subtitle_xy[0],
            y=subtitle_xy[1],
            size=subtitle_fontsize,
            ha="center",
            va="center",
        )

        if save_img:
            save_directory = Path(
                f"../charts/{self.experiment_strength}/{self.experiment_version}/{self.run_name}"
            )

            if not save_directory.exists():
                save_directory.mkdir(parents=True)

            savepath = save_directory / f"{self.run_name}_roc_auc.png"

            fig.savefig(savepath, bbox_inches="tight", facecolor="white")

        return fig

    def class_pred_errors(
        self,
        suptitle=None,
        suptitle_xy=(0.5, 1.025),
        suptitle_fontsize=18,
        subtitle=None,
        subtitle_xy=(0.5, 0.985),
        subtitle_fontsize=13,
        save_img=False,
        dpi=750,
        figsize=(10, 6),
    ):
        """Generate class prediction errors chart using YellowBrick."""
        fig, ax = plt.subplots(dpi=dpi, figsize=figsize)

        viz = ClassPredictionError(self.model, encoder=self.encoder)

        viz.fit(self.X, self.y)

        viz.score(self.X, self.y)  # Evaluate the model on the test data

        viz.finalize()

        viz.set_title("")

        if not suptitle:
            suptitle = f"chickenstats.chicken_nhl xG model performance"

        fig.suptitle(
            suptitle,
            x=suptitle_xy[0],
            y=suptitle_xy[1],
            size=suptitle_fontsize,
            weight="bold",
            ha="center",
            va="center",
        )

        if not subtitle:
            subtitle = f"Class prediction errors for {self.experiment_strength.replace('_', ' ')} xG model | {self.run_name} ({self.experiment_name})"

        fig.text(
            s=subtitle,
            x=subtitle_xy[0],
            y=subtitle_xy[1],
            size=subtitle_fontsize,
            ha="center",
            va="center",
        )

        if save_img:
            save_directory = Path(
                f"../charts/{self.experiment_strength}/{self.experiment_version}/{self.run_name}"
            )

            if not save_directory.exists():
                save_directory.mkdir(parents=True)

            savepath = save_directory / f"{self.run_name}_class_pred_errors.png"

            fig.savefig(savepath, bbox_inches="tight", facecolor="white")

        return fig

    def precision_recall_curves(
        self,
        suptitle=None,
        suptitle_xy=(0.5, 1.025),
        suptitle_fontsize=18,
        subtitle=None,
        subtitle_xy=(0.5, 0.985),
        subtitle_fontsize=13,
        save_img=False,
        dpi=750,
        figsize=(10, 6),
    ):
        """Generate precision recall curves chart using YellowBrick."""
        fig, ax = plt.subplots(dpi=dpi, figsize=figsize)

        viz = PrecisionRecallCurve(self.model, encoder=self.encoder)

        viz.fit(self.X, self.y)

        viz.score(self.X, self.y)  # Evaluate the model on the test data

        viz.finalize()

        viz.set_title("")

        if not suptitle:
            suptitle = f"chickenstats.chicken_nhl xG model performance"

        fig.suptitle(
            suptitle,
            x=suptitle_xy[0],
            y=suptitle_xy[1],
            size=suptitle_fontsize,
            weight="bold",
            ha="center",
            va="center",
        )

        if not subtitle:
            subtitle = f"Precision recall curves for {self.experiment_strength.replace('_', ' ')} xG model | {self.run_name} ({self.experiment_name})"

        fig.text(
            s=subtitle,
            x=subtitle_xy[0],
            y=subtitle_xy[1],
            size=subtitle_fontsize,
            ha="center",
            va="center",
        )

        if save_img:
            save_directory = Path(
                f"../charts/{self.experiment_strength}/{self.experiment_version}/{self.run_name}"
            )

            if not save_directory.exists():
                save_directory.mkdir(parents=True)

            savepath = save_directory / f"{self.run_name}_precision_recall_curves.png"

            fig.savefig(savepath, bbox_inches="tight", facecolor="white")

        return fig

    def full_viz(self, save_img=False):
        """Generate all visualizations / charts."""
        self.shap_swarm(save_img=save_img)

        self.class_report(save_img=save_img)

        self.confusion_matrix(save_img=save_img)

        self.feature_importance(save_img=save_img)

        self.rel_feature_importance(save_img=save_img)

        self.roc_auc(save_img=save_img)

        self.class_pred_errors(save_img=save_img)

        self.precision_recall_curves(save_img=save_img)


def prep_data(data: pd.DataFrame, strengths: str) -> pd.DataFrame:
    """Function for prepping play-by-play data for xG experiments.

    Data are play-by-play data from the chickenstats function.

    Strengths can be: even, powerplay, shorthanded, empty_for, empty_against
    """
    df = data.copy()

    events = [
        "SHOT",
        "FAC",
        "HIT",
        "BLOCK",
        "MISS",
        "GIVE",
        "TAKE",
        # "PENL",
        "GOAL",
    ]

    conds = np.logical_and.reduce(
        [
            df.event.isin(events),
            df.strength_state != "1v0",
            pd.notnull(df.coords_x),
            pd.notnull(df.coords_y),
        ]
    )

    df = df.loc[conds]

    conds = np.logical_and.reduce(
        [
            df.season == df.season.shift(1),
            df.game_id == df.game_id.shift(1),
            df.period == df.period.shift(1),
        ]
    )
    df["seconds_since_last"] = np.where(
        conds, df.game_seconds - df.game_seconds.shift(1), np.nan
    )
    df["event_type_last"] = np.where(conds, df.event.shift(1), np.nan)
    df["event_team_last"] = np.where(conds, df.event_team.shift(1), np.nan)
    df["event_strength_last"] = np.where(conds, df.strength_state.shift(1), np.nan)
    df["coords_x_last"] = np.where(conds, df.coords_x.shift(1), np.nan)
    df["coords_y_last"] = np.where(conds, df.coords_y.shift(1), np.nan)
    df["zone_last"] = np.where(conds, df.zone.shift(1), np.nan)

    df["same_team_last"] = np.where(np.equal(df.event_team, df.event_team_last), 1, 0)

    df["distance_from_last"] = (
        (df.coords_x - df.coords_x_last) ** 2 + (df.coords_y - df.coords_y_last) ** 2
    ) ** (1 / 2)

    last_is_shot = np.equal(df.event_type_last, "SHOT")
    last_is_miss = np.equal(df.event_type_last, "MISS")
    last_is_block = np.equal(df.event_type_last, "BLOCK")
    last_is_give = np.equal(df.event_type_last, "GIVE")
    last_is_take = np.equal(df.event_type_last, "TAKE")
    last_is_hit = np.equal(df.event_type_last, "HIT")
    last_is_fac = np.equal(df.event_type_last, "FAC")

    same_team_as_last = np.equal(df.same_team_last, 1)
    not_same_team_as_last = np.equal(df.same_team_last, 0)

    df["prior_shot_same"] = np.where((last_is_shot & same_team_as_last), 1, 0)
    df["prior_miss_same"] = np.where((last_is_miss & same_team_as_last), 1, 0)
    df["prior_block_same"] = np.where((last_is_block & same_team_as_last), 1, 0)
    df["prior_give_same"] = np.where((last_is_give & same_team_as_last), 1, 0)
    df["prior_take_same"] = np.where((last_is_take & same_team_as_last), 1, 0)
    df["prior_hit_same"] = np.where((last_is_hit & same_team_as_last), 1, 0)

    df["prior_shot_opp"] = np.where((last_is_shot & not_same_team_as_last), 1, 0)
    df["prior_miss_opp"] = np.where((last_is_miss & not_same_team_as_last), 1, 0)
    df["prior_block_opp"] = np.where((last_is_block & not_same_team_as_last), 1, 0)
    df["prior_give_opp"] = np.where((last_is_give & not_same_team_as_last), 1, 0)
    df["prior_take_opp"] = np.where((last_is_take & not_same_team_as_last), 1, 0)
    df["prior_hit_opp"] = np.where((last_is_hit & not_same_team_as_last), 1, 0)

    df["prior_face"] = np.where(last_is_fac, 1, 0)

    shot_types = pd.get_dummies(df.shot_type, dtype=int)

    shot_types = shot_types.rename(
        columns={
            x: x.lower().replace("-", "_").replace(" ", "_") for x in shot_types.columns
        }
    )

    df = df.copy().merge(shot_types, left_index=True, right_index=True, how="outer")

    conds = [df.score_diff > 4, df.score_diff < -4]

    values = [4, -4]

    df.score_diff = np.select(conds, values, df.score_diff)

    conds = [
        df.player_1_position.isin(["F", "L", "R", "C"]),
        df.player_1_position == "D",
        df.player_1_position == "G",
    ]

    values = ["F", "D", "G"]

    df["position_group"] = np.select(conds, values)

    position_dummies = pd.get_dummies(df.position_group, dtype=int)

    new_cols = {x: f"position_{x.lower()}" for x in values}

    position_dummies = position_dummies.rename(columns=new_cols)

    df = df.merge(position_dummies, left_index=True, right_index=True)

    conds = [
        np.logical_and.reduce(
            [
                df.event.isin(["GOAL", "SHOT", "BLOCK", "MISS"]),
                df.event_type_last.isin(["SHOT", "MISS"]),
                df.event_team_last == df.event_team,
                df.game_id == df.game_id.shift(1),
                df.period == df.period.shift(1),
                df.seconds_since_last <= 3,
            ]
        ),
        np.logical_and.reduce(
            [
                df.event.isin(["GOAL", "SHOT", "BLOCK", "MISS"]),
                df.event_type_last == "BLOCK",
                df.event_team_last == df.opp_team,
                df.game_id == df.game_id.shift(1),
                df.period == df.period.shift(1),
                df.seconds_since_last <= 3,
            ]
        ),
    ]

    values = [1, 1]

    df["is_rebound"] = np.select(conds, values, 0)

    conds = np.logical_and.reduce(
        [
            df.event.isin(["GOAL", "SHOT", "BLOCK", "MISS"]),
            df.seconds_since_last <= 4,
            df.zone_last == "NEU",
            df.game_id == df.game_id.shift(1),
            df.period == df.period.shift(1),
            df.event != "FAC",
        ]
    )

    df["rush_attempt"] = np.where(conds, 1, 0)

    cat_cols = ["strength_state", "position_group", "event_type_last"]

    for col in cat_cols:
        dummies = pd.get_dummies(df[col], dtype=int)

        new_cols = {x: f"{col}_{x}" for x in dummies.columns}

        dummies = dummies.rename(columns=new_cols)

        df = df.copy().merge(dummies, left_index=True, right_index=True)

    if strengths.lower() == "even":
        strengths_list = ["5v5", "4v4", "3v3"]

    if strengths.lower() == "powerplay" or strengths.lower() == "pp":
        strengths_list = ["5v4", "4v3", "5v3"]

    if strengths.lower() == "shorthanded" or strengths.lower() == "ss":
        strengths_list = ["4v5", "3v4", "3v5"]

    if strengths.lower() == "empty_for":
        strengths_list = ["Ev5", "Ev4", "Ev3"]

    if strengths.lower() == "empty_against":
        strengths_list = ["5vE", "4vE", "3vE"]

    conds = np.logical_and.reduce(
        [
            df.event.isin(["GOAL", "SHOT", "MISS"]),
            df.strength_state.isin(strengths_list),
        ]
    )

    df = df.loc[conds]

    drop_cols = [
        x
        for x in df.columns
        if "strength_state_" in x
        and x not in [f"strength_state_{x}" for x in strengths_list]
    ] + cat_cols

    df = df.drop(drop_cols, axis=1, errors="ignore")

    df = XGSchema.validate(df[[x for x in XGSchema.dtypes.keys() if x in df.columns]])

    return df
