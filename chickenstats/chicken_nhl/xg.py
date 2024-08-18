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

        viz = FeatureImportances(
            self.model,
            relative=False,
            ax=ax,
            topn=topn,
        )

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

        viz = FeatureImportances(
            self.model,
            relative=True,
            ax=ax,
            topn=topn,
        )

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
