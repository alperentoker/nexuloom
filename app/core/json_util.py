"""JSON serialization utilities for converting complex types (NumPy, Pandas, NaNs) to standard JSON primitives."""

import math
from datetime import datetime, date
from typing import Any
import numpy as np
import pandas as pd


def sanitize_for_json(obj: Any) -> Any:
    """Recursively converts NumPy scalars, arrays, Pandas Timestamps, NaNs, and Infs

    into Python standard native primitives (int, float, str, bool, list, dict, None)
    so that FastAPI jsonable_encoder and standard json.dumps never fail.
    """
    if isinstance(obj, dict):
        return {str(k): sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, (np.integer, int)):
        return int(obj)
    elif isinstance(obj, (np.floating, float)):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return [sanitize_for_json(x) for x in obj.tolist()]
    elif isinstance(obj, (pd.Timestamp, datetime, date)):
        return obj.isoformat()
    elif hasattr(obj, "item") and callable(getattr(obj, "item")):
        try:
            return sanitize_for_json(obj.item())
        except Exception:
            return str(obj)
    elif pd.isna(obj):
        return None
    return obj
