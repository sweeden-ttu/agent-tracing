"""OOF blending utilities (hill-climbing + Ridge meta-learner)."""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_squared_error


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true, dtype=np.float64).ravel()
    y_pred = np.asarray(y_pred, dtype=np.float64).ravel()
    mask = np.isfinite(y_true) & np.isfinite(y_pred)
    if not mask.any():
        return float("nan")
    return float(np.sqrt(mean_squared_error(y_true[mask], y_pred[mask])))


def _normalize_weights(w: np.ndarray) -> np.ndarray:
    w = np.clip(w, 0.0, None)
    s = w.sum()
    return w / s if s > 0 else np.ones_like(w) / len(w)


def coordinate_descent_blend(
    oof_matrix: np.ndarray,
    y_true: np.ndarray,
    *,
    n_iter: int = 400,
    step: float = 0.02,
    seed: int = 42,
) -> tuple[np.ndarray, float]:
    """Hill-climbing style weight search (karnak/Raunak pattern, no external wheel)."""
    rng = np.random.default_rng(seed)
    n_models = oof_matrix.shape[1]
    w = np.ones(n_models, dtype=np.float64) / n_models
    best_rmse = rmse(y_true, oof_matrix @ w)

    for _ in range(n_iter):
        improved = False
        for j in range(n_models):
            for delta in (-step, step):
                trial = w.copy()
                trial[j] = max(0.0, trial[j] + delta)
                trial = _normalize_weights(trial)
                score = rmse(y_true, oof_matrix @ trial)
                if score < best_rmse - 1e-9:
                    best_rmse = score
                    w = trial
                    improved = True
        if not improved:
            # random jitter restart
            jitter = rng.dirichlet(np.ones(n_models))
            score = rmse(y_true, oof_matrix @ jitter)
            if score < best_rmse:
                best_rmse = score
                w = jitter

    return w, best_rmse


def ridge_stack_oof(
    oof_matrix: np.ndarray,
    y_true: np.ndarray,
    *,
    alpha: float = 1.0,
) -> tuple[np.ndarray, Ridge, float]:
    """Fit Ridge meta-learner on OOF predictions."""
    mask = np.all(np.isfinite(oof_matrix), axis=1) & np.isfinite(y_true)
    X = oof_matrix[mask]
    y = y_true[mask]
    model = Ridge(alpha=alpha, positive=True, fit_intercept=True)
    model.fit(X, y)
    pred = model.predict(oof_matrix)
    return pred, model, rmse(y_true, pred)


def apply_savgol_safe(y: np.ndarray, *, window: int = 17, poly: int = 3) -> np.ndarray:
    """Per-well Savgol smoothing when scipy available; else return input."""
    try:
        from scipy.signal import savgol_filter
    except ImportError:
        return y
    w = window if window % 2 == 1 else window + 1
    w = min(w, max(5, len(y) - (1 - len(y) % 2)))
    if len(y) < w:
        return y
    return savgol_filter(y, w, poly, mode="interp")
