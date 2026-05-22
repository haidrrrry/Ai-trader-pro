#!/usr/bin/env python3
"""RSI strategy grid search with vectorbt — research CLI."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

try:
    import vectorbt as vbt
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Install research deps: pip install -r research/requirements.txt") from exc

try:
    import yfinance as yf
except ImportError as exc:  # pragma: no cover
    raise SystemExit("yfinance required: pip install yfinance") from exc


TRADING_DAYS = 252
RISK_FREE = 0.04


@dataclass
class StrategyResult:
    window: int
    lower: float
    upper: float
    total_return: float
    sharpe: float
    sortino: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    trades: int


def load_close(symbol: str, start: str, end: str) -> pd.Series:
    raw = yf.download(symbol, start=start, end=end, auto_adjust=True, progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    close = raw["Close"].dropna().astype(float)
    if close.empty:
        raise ValueError(f"No price data for {symbol}")
    return close


def rsi_signals(close: pd.Series, window: int, lower: float, upper: float) -> tuple[pd.Series, pd.Series]:
    rsi = vbt.RSI.run(close, window=window).rsi
    entries = (rsi < lower).fillna(False)
    exits = (rsi > upper).fillna(False)
    return entries, exits


def _max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    dd = (equity - peak) / peak
    return float(dd.min()) if len(dd) else 0.0


def _sharpe(daily: pd.Series) -> float:
    if len(daily) < 2 or daily.std() == 0:
        return 0.0
    excess = daily - RISK_FREE / TRADING_DAYS
    return float(np.sqrt(TRADING_DAYS) * excess.mean() / excess.std())


def _sortino(daily: pd.Series) -> float:
    if len(daily) < 2:
        return 0.0
    excess = daily - RISK_FREE / TRADING_DAYS
    downside = excess[excess < 0]
    if downside.empty or downside.std() == 0:
        return 0.0
    return float(np.sqrt(TRADING_DAYS) * excess.mean() / downside.std())


def backtest_rsi(
    close: pd.Series,
    *,
    window: int,
    lower: float,
    upper: float,
    fees: float = 0.001,
) -> StrategyResult:
    entries, exits = rsi_signals(close, window, lower, upper)
    pf = vbt.Portfolio.from_signals(
        close,
        entries=entries,
        exits=exits,
        init_cash=100_000,
        fees=fees,
        freq="1D",
    )
    equity = pf.value()
    daily = pf.returns().dropna()
    trade_rets = pf.trades.returns.values if pf.trades.count() else np.array([])
    gains = trade_rets[trade_rets > 0].sum() if trade_rets.size else 0.0
    losses = abs(trade_rets[trade_rets < 0].sum()) if trade_rets.size else 0.0
    pf_ratio = float(gains / losses) if losses > 0 else (float("inf") if gains > 0 else 0.0)
    win_rate = float((trade_rets > 0).mean()) if trade_rets.size else 0.0
    total_return = float(equity.iloc[-1] / equity.iloc[0] - 1) if len(equity) > 1 else 0.0

    return StrategyResult(
        window=window,
        lower=lower,
        upper=upper,
        total_return=round(total_return, 6),
        sharpe=round(_sharpe(daily), 4),
        sortino=round(_sortino(daily), 4),
        max_drawdown=round(_max_drawdown(equity), 6),
        win_rate=round(win_rate, 4),
        profit_factor=round(pf_ratio, 4) if np.isfinite(pf_ratio) else 999.0,
        trades=int(pf.trades.count()),
    )


def grid_search(
    close: pd.Series,
    *,
    windows: Optional[list[int]] = None,
    lowers: Optional[list[float]] = None,
    uppers: Optional[list[float]] = None,
) -> pd.DataFrame:
    windows = windows or [10, 14, 20, 28]
    lowers = lowers or [25, 30, 35]
    uppers = uppers or [65, 70, 75]
    rows: list[dict[str, Any]] = []
    for window in windows:
        for lower in lowers:
            for upper in uppers:
                if lower >= upper:
                    continue
                result = backtest_rsi(close, window=window, lower=lower, upper=upper)
                rows.append(asdict(result))
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    return frame.sort_values("sharpe", ascending=False).reset_index(drop=True)


def walk_forward_grid(
    close: pd.Series,
    *,
    train_bars: int = 504,
    test_bars: int = 126,
    top_n: int = 3,
) -> pd.DataFrame:
    """Pick best in-sample params per fold, score out-of-sample Sharpe."""
    rows: list[dict[str, Any]] = []
    start = 0
    fold = 0
    while start + train_bars + test_bars <= len(close):
        train = close.iloc[start : start + train_bars]
        test = close.iloc[start + train_bars : start + train_bars + test_bars]
        in_sample = grid_search(train).head(top_n)
        if in_sample.empty:
            break
        best = in_sample.iloc[0]
        oos = backtest_rsi(
            test,
            window=int(best["window"]),
            lower=float(best["lower"]),
            upper=float(best["upper"]),
        )
        rows.append(
            {
                "fold": fold,
                "train_start": str(train.index[0].date()),
                "test_start": str(test.index[0].date()),
                "test_end": str(test.index[-1].date()),
                "window": oos.window,
                "lower": oos.lower,
                "upper": oos.upper,
                "oos_sharpe": oos.sharpe,
                "oos_return": oos.total_return,
                "oos_max_drawdown": oos.max_drawdown,
            }
        )
        start += test_bars
        fold += 1
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", default="SPY")
    parser.add_argument("--start", default="2018-01-01")
    parser.add_argument("--end", default="2024-12-31")
    parser.add_argument("--mode", choices=["grid", "walkforward"], default="grid")
    parser.add_argument("--top", type=int, default=10, help="Rows to print")
    parser.add_argument("--output", type=Path, default=None, help="Optional CSV output path")
    args = parser.parse_args()

    close = load_close(args.symbol, args.start, args.end)
    print(f"Loaded {args.symbol}: {len(close)} bars")

    if args.mode == "walkforward":
        results = walk_forward_grid(close)
        print(results.to_string(index=False))
    else:
        results = grid_search(close)
        print(results.head(args.top).to_string(index=False))

    if args.output and not results.empty:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        results.to_csv(args.output, index=False)
        print(f"Saved {args.output}")


if __name__ == "__main__":
    main()
