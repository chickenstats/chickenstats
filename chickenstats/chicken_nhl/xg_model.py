from xgboost import XGBClassifier
from pathlib import Path
import numpy as np
import pandas as pd


def load_model(model_name, model_version):
    file_name = Path(
        f"./chickenstats/chicken_nhl/xg_models/{model_name}-{model_version}.json"
    )

    model = XGBClassifier()
    model = model.load_model(file_name)

    return model


model_version = "0.1.0"

es_model = load_model("even-strength", model_version)
pp_model = load_model("powerplay", model_version)
sh_model = load_model("shorthanded", model_version)
ea_model = load_model("empty-against", model_version)
ef_model = load_model("empty-for", model_version)
