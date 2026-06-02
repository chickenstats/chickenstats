import pytest

try:
    import pandas  # noqa: F401

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    import pyarrow  # noqa: F401

    HAS_PYARROW = True
except ImportError:
    HAS_PYARROW = False

try:
    import matplotlib  # noqa: F401

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    from PIL import Image  # noqa: F401

    HAS_PIL = True
except ImportError:
    HAS_PIL = False

requires_pandas = pytest.mark.skipif(not HAS_PANDAS, reason="pandas not installed")
requires_pyarrow = pytest.mark.skipif(not HAS_PYARROW, reason="pyarrow not installed")
requires_matplotlib = pytest.mark.skipif(not HAS_MATPLOTLIB, reason="matplotlib not installed")
requires_pil = pytest.mark.skipif(not HAS_PIL, reason="pillow not installed")
