"""Target diagnostics for TVT (log1p recommendation)."""

from __future__ import annotations

import numpy as np


def _skewness(y: np.ndarray) -> float:
    y = np.asarray(y, dtype=np.float64)
    y = y[np.isfinite(y)]
    if len(y) < 3:
        return 0.0
    m = y.mean()
    sd = y.std()
    if sd == 0:
        return 0.0
    return float(np.mean(((y - m) / sd) ** 3))


def recommend_log1p(y: np.ndarray, *, skew_threshold: float = 1.5) -> dict:
    y = np.asarray(y, dtype=np.float64)
    finite = y[np.isfinite(y)]
    strict_positive = bool(len(finite) > 0 and np.all(finite > 0))
    skew = _skewness(finite)
    use = strict_positive and skew > skew_threshold
    return {
        "use_log1p": use,
        "skewness": skew,
        "skew_threshold": skew_threshold,
        "strict_positivity": {"strict_positive": strict_positive},
    }
