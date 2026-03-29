import numpy as np
import pandas as pd


def convert_to_list(obj: str | list | float | int | pd.Series | np.ndarray, object_type: str) -> list:
    """If the object is not a list or list-like, converts the object to a list of length one."""
    if (
        isinstance(obj, str) is True
        or isinstance(obj, int | np.integer) is True
        or isinstance(obj, float | np.float64) is True
    ):
        try:
            obj = [int(obj)]

        except ValueError:
            obj = [obj]

    elif isinstance(obj, pd.Series) is True or isinstance(obj, np.ndarray) is True:
        obj = obj.tolist()

    elif isinstance(obj, tuple):
        obj = list(obj)

    elif isinstance(obj, list):
        pass

    else:
        raise Exception(f"'{obj}' not a supported {object_type} or range of {object_type}s")

    return obj
