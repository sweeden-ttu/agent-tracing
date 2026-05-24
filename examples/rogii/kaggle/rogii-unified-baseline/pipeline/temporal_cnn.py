"""Temporal CNN baseline for per-depth regression on wellbore data.

Architecture
------------
Non-causal (bidirectional) 1D temporal convolutional network with dilated
convolutions and residual connections, after Bai et al. ("An Empirical
Evaluation of Generic Convolutional and Recurrent Networks for Sequence
Modeling", 2018), adapted to a sequence-to-sequence regression head.

The wellbore data is intrinsically a *depth series* (rows ordered by
measured depth within a well), so we:

1. Group rows by ``well_id``.
2. Sort each well by ``MD`` (measured depth).
3. Slice each well into overlapping fixed-length windows.
4. Train a per-position regressor on the window.
5. Reassemble overlapping window predictions back into a single per-row
   prediction by averaging the overlaps.

The module is GPU-aware but works fine on CPU for the 5 k-row-per-well
scale of this competition.

API surface
-----------
- ``TemporalCNN`` — the ``nn.Module``.
- ``make_sequences`` — DataFrame → windowed tensors + reassembly index.
- ``reassemble`` — per-window predictions → per-row predictions.
- ``train_one_fold`` — single-fold training loop with early stopping.
- ``predict_windows`` — batched inference helper.
- ``rmse`` — root mean squared error (matches the leaderboard metric).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

try:
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, TensorDataset
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "pipeline.temporal_cnn requires torch. Install via "
        "`pip install torch --index-url https://download.pytorch.org/whl/cpu`"
    ) from exc


# ----------------------------------------------------------------------
# Model
# ----------------------------------------------------------------------


class _TCNBlock(nn.Module):
    """Two-conv residual block with symmetric (non-causal) padding."""

    def __init__(
        self,
        in_ch: int,
        out_ch: int,
        kernel_size: int = 3,
        dilation: int = 1,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        pad = ((kernel_size - 1) * dilation) // 2
        self.conv1 = nn.Conv1d(in_ch, out_ch, kernel_size, padding=pad, dilation=dilation)
        self.conv2 = nn.Conv1d(out_ch, out_ch, kernel_size, padding=pad, dilation=dilation)
        self.bn1 = nn.BatchNorm1d(out_ch)
        self.bn2 = nn.BatchNorm1d(out_ch)
        self.dropout = nn.Dropout(dropout)
        self.skip = nn.Conv1d(in_ch, out_ch, 1) if in_ch != out_ch else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out = torch.relu(self.bn1(self.conv1(x)))
        out = self.dropout(out)
        out = torch.relu(self.bn2(self.conv2(out)))
        out = self.dropout(out)
        return torch.relu(out + self.skip(x))


class TemporalCNN(nn.Module):
    """Stacked dilated 1D-CNN producing one prediction per depth tick.

    Receptive field for the default config (4 blocks, kernel=3) is roughly
    ``2 * (kernel - 1) * (2^n_blocks - 1) + 1 = 2 * 2 * 15 + 1 = 61``
    depth ticks centered on the prediction position.
    """

    def __init__(
        self,
        n_features: int,
        hidden: int = 64,
        n_blocks: int = 4,
        kernel_size: int = 3,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        layers = []
        ch_in = n_features
        for i in range(n_blocks):
            layers.append(_TCNBlock(ch_in, hidden, kernel_size, 2**i, dropout))
            ch_in = hidden
        self.blocks = nn.Sequential(*layers)
        self.head = nn.Conv1d(hidden, 1, kernel_size=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """``x`` shape: ``(batch, n_features, window_len)``.

        Returns ``(batch, window_len)``.
        """
        h = self.blocks(x)
        return self.head(h).squeeze(1)


# ----------------------------------------------------------------------
# Sequence assembly
# ----------------------------------------------------------------------


@dataclass
class SequenceMap:
    """Bookkeeping needed to reassemble window predictions back to row order.

    Attributes
    ----------
    row_indices
        For each window, the original DataFrame row indices it covers.
        Shape: ``(n_windows, window_len)``.
    n_rows
        Total number of rows in the source DataFrame (so a result array of
        length ``n_rows`` can be allocated for reassembly).
    """

    row_indices: np.ndarray
    n_rows: int


def make_sequences(
    df: pd.DataFrame,
    *,
    well_col: str,
    depth_col: str,
    feature_cols: Sequence[str],
    target_col: str | None = None,
    window_len: int = 128,
    stride: int = 64,
    pad_value: float = 0.0,
) -> tuple[np.ndarray, np.ndarray | None, SequenceMap]:
    """Build overlapping windows of length ``window_len`` per well.

    The DataFrame is left intact; the returned ``SequenceMap.row_indices``
    array is keyed on the original DataFrame index after ``reset_index(drop=True)``
    has been applied to ``df`` prior to calling this function.

    Returns
    -------
    X
        ``(n_windows, n_features, window_len)`` float32.
    y
        ``(n_windows, window_len)`` float32, or ``None`` if ``target_col`` is None.
        Padded positions carry ``pad_value`` (and are masked out at loss-time;
        see :func:`train_one_fold`).
    seq_map
        :class:`SequenceMap` for reassembly.
    """
    if window_len <= 0 or stride <= 0:
        raise ValueError("window_len and stride must be positive")

    df = df.reset_index(drop=True)
    if well_col not in df.columns:
        raise ValueError(f"well_col {well_col!r} not in dataframe")
    if depth_col not in df.columns:
        raise ValueError(f"depth_col {depth_col!r} not in dataframe")

    X_windows: list[np.ndarray] = []
    y_windows: list[np.ndarray] = []
    row_idx_windows: list[np.ndarray] = []

    n_features = len(feature_cols)
    for _, well_df in df.groupby(well_col, sort=False):
        well_df = well_df.sort_values(depth_col, kind="mergesort")
        rows = well_df.index.to_numpy()
        n = len(rows)
        if n == 0:
            continue
        feat = well_df[list(feature_cols)].to_numpy(dtype=np.float32, copy=True)
        feat = np.nan_to_num(feat, nan=0.0, posinf=0.0, neginf=0.0)
        if target_col is not None:
            tgt = well_df[target_col].to_numpy(dtype=np.float32, copy=True)
        else:
            tgt = None

        # slide windows; pad the tail of the last window if needed
        starts = list(range(0, max(n - window_len, 0) + 1, stride))
        if not starts or starts[-1] + window_len < n:
            starts.append(max(n - window_len, 0))
        for s in starts:
            e = s + window_len
            x_block = np.full((window_len, n_features), pad_value, dtype=np.float32)
            r_block = np.full(window_len, -1, dtype=np.int64)
            actual = min(e, n) - s
            x_block[:actual] = feat[s : s + actual]
            r_block[:actual] = rows[s : s + actual]
            X_windows.append(x_block.T)  # (n_features, window_len)
            row_idx_windows.append(r_block)
            if tgt is not None:
                y_block = np.full(window_len, pad_value, dtype=np.float32)
                y_block[:actual] = tgt[s : s + actual]
                y_windows.append(y_block)

    if not X_windows:
        raise ValueError("no windows produced — check well_col / depth_col")

    X = np.stack(X_windows, axis=0)
    seq_map = SequenceMap(
        row_indices=np.stack(row_idx_windows, axis=0),
        n_rows=len(df),
    )
    y = np.stack(y_windows, axis=0) if y_windows else None
    return X, y, seq_map


def reassemble(window_preds: np.ndarray, seq_map: SequenceMap) -> np.ndarray:
    """Average overlapping window predictions back to per-row predictions.

    Returns a ``(seq_map.n_rows,)`` array. Rows not covered by any window
    (shouldn't happen if sequences cover every well) are returned as NaN.
    """
    if window_preds.shape != seq_map.row_indices.shape:
        raise ValueError(
            f"shape mismatch: preds {window_preds.shape} vs "
            f"row_indices {seq_map.row_indices.shape}"
        )
    sums = np.zeros(seq_map.n_rows, dtype=np.float64)
    counts = np.zeros(seq_map.n_rows, dtype=np.int64)
    flat_preds = window_preds.reshape(-1).astype(np.float64)
    flat_rows = seq_map.row_indices.reshape(-1)
    valid = flat_rows >= 0
    np.add.at(sums, flat_rows[valid], flat_preds[valid])
    np.add.at(counts, flat_rows[valid], 1)
    out = np.full(seq_map.n_rows, np.nan, dtype=np.float64)
    nz = counts > 0
    out[nz] = sums[nz] / counts[nz]
    return out


# ----------------------------------------------------------------------
# Training / inference
# ----------------------------------------------------------------------


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """RMSE on the original target scale (Kaggle definition)."""
    y_true = np.asarray(y_true, dtype=np.float64).ravel()
    y_pred = np.asarray(y_pred, dtype=np.float64).ravel()
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def _make_loader(X: np.ndarray, y: np.ndarray | None, batch_size: int, shuffle: bool) -> DataLoader:
    Xt = torch.from_numpy(X).float()
    if y is None:
        ds = TensorDataset(Xt)
    else:
        ds = TensorDataset(Xt, torch.from_numpy(y).float())
    return DataLoader(ds, batch_size=batch_size, shuffle=shuffle, drop_last=False)


def train_one_fold(
    X_tr: np.ndarray,
    y_tr: np.ndarray,
    X_va: np.ndarray,
    y_va: np.ndarray,
    *,
    n_features: int,
    hidden: int = 64,
    n_blocks: int = 4,
    kernel_size: int = 3,
    dropout: float = 0.1,
    lr: float = 1e-3,
    weight_decay: float = 1e-5,
    batch_size: int = 32,
    max_epochs: int = 60,
    patience: int = 8,
    pad_value: float = 0.0,
    device: str | None = None,
    verbose: bool = False,
) -> tuple[TemporalCNN, float, list[float]]:
    """Train one fold; return (best_model, best_val_rmse, history).

    The validation RMSE is computed on the **non-padded** positions only
    (positions whose corresponding row index is ``-1`` are masked out).
    """
    dev = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
    model = TemporalCNN(n_features, hidden=hidden, n_blocks=n_blocks,
                        kernel_size=kernel_size, dropout=dropout).to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)

    train_loader = _make_loader(X_tr, y_tr, batch_size, shuffle=True)
    val_loader = _make_loader(X_va, y_va, batch_size, shuffle=False)

    best_rmse = float("inf")
    best_state: dict | None = None
    history: list[float] = []
    bad_epochs = 0

    for epoch in range(max_epochs):
        model.train()
        train_loss = 0.0
        n_train = 0
        for xb, yb in train_loader:
            xb, yb = xb.to(dev), yb.to(dev)
            mask = (yb != pad_value).float()
            opt.zero_grad()
            pred = model(xb)
            sq = (pred - yb) ** 2 * mask
            loss = sq.sum() / mask.sum().clamp(min=1.0)
            loss.backward()
            opt.step()
            train_loss += float(loss.item()) * xb.size(0)
            n_train += xb.size(0)
        train_loss /= max(n_train, 1)

        model.eval()
        sq_sum = 0.0
        m_sum = 0.0
        with torch.no_grad():
            for xb, yb in val_loader:
                xb, yb = xb.to(dev), yb.to(dev)
                mask = (yb != pad_value).float()
                pred = model(xb)
                sq_sum += float(((pred - yb) ** 2 * mask).sum().item())
                m_sum += float(mask.sum().item())
        val_rmse = float(np.sqrt(sq_sum / max(m_sum, 1.0)))
        history.append(val_rmse)
        if verbose:
            print(f"  epoch {epoch:02d}  train_mse={train_loss:.6f}  val_rmse={val_rmse:.6f}")

        if val_rmse + 1e-9 < best_rmse:
            best_rmse = val_rmse
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            bad_epochs = 0
        else:
            bad_epochs += 1
            if bad_epochs >= patience:
                if verbose:
                    print(f"  early stop @ epoch {epoch}")
                break

    if best_state is not None:
        model.load_state_dict(best_state)
    return model, best_rmse, history


def predict_windows(
    model: TemporalCNN,
    X: np.ndarray,
    *,
    batch_size: int = 64,
    device: str | None = None,
) -> np.ndarray:
    """Run the model in eval mode; return ``(n_windows, window_len)``."""
    dev = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
    model = model.to(dev).eval()
    loader = _make_loader(X, None, batch_size, shuffle=False)
    out_chunks: list[np.ndarray] = []
    with torch.no_grad():
        for (xb,) in loader:
            xb = xb.to(dev)
            preds = model(xb).cpu().numpy()
            out_chunks.append(preds)
    return np.concatenate(out_chunks, axis=0)
