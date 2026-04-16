from __future__ import annotations

import numpy as np
import pandas as pd

from chickenstats.exceptions import InvalidInputError


def convert_to_list(obj: str | list | float | int | pd.Series | np.ndarray, object_type: str) -> list:
    """Normalize ``obj`` to a plain Python list.

    Scalar inputs (str, int, float) are wrapped in a single-element list.
    ``pd.Series`` and ``np.ndarray`` are converted via ``.tolist()``.
    Tuples are cast with ``list()``. Existing lists are returned unchanged.

    Parameters:
        obj: The value to normalize.
        object_type: Human-readable name for the input type, used in the error message.

    Raises:
        InvalidInputError: If ``obj`` is not a recognized type.
    """
    if (
        isinstance(obj, str) is True
        or isinstance(obj, int | np.integer) is True
        or isinstance(obj, float | np.float64) is True
    ):
        try:
            obj = [int(obj)]  # ty: ignore[invalid-argument-type]

        except ValueError:
            obj = [obj]

    elif isinstance(obj, pd.Series) is True or isinstance(obj, np.ndarray) is True:
        obj = obj.tolist()  # ty: ignore[unresolved-attribute]

    elif isinstance(obj, tuple):
        obj = list(obj)

    elif isinstance(obj, list):
        pass

    else:
        raise InvalidInputError(f"'{obj}' not a supported {object_type} or range of {object_type}s")

    return obj
