"""Tests for research/strategy_optimizer.py"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

RESEARCH_DIR = Path(__file__).resolve().parents[1]
if str(RESEARCH_DIR) not in sys.path:
    sys.path.insert(0, str(RESEARCH_DIR))

from strategy_optimizer import backtest_rsi, grid_search


class StrategyOptimizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.close = pd.Series(
            100 * np.cumprod(1 + np.random.default_rng(42).normal(0, 0.008, 400)),
            index=pd.date_range("2020-01-01", periods=400, freq="B"),
        )

    def test_backtest_returns_metrics(self) -> None:
        result = backtest_rsi(self.close, window=14, lower=30, upper=70)
        self.assertGreaterEqual(result.trades, 0)
        self.assertIsInstance(result.sharpe, float)

    def test_grid_search_sorted_by_sharpe(self) -> None:
        frame = grid_search(
            self.close,
            windows=[10, 14],
            lowers=[30],
            uppers=[70],
        )
        self.assertFalse(frame.empty)
        if len(frame) > 1:
            self.assertGreaterEqual(frame.iloc[0]["sharpe"], frame.iloc[-1]["sharpe"])


if __name__ == "__main__":
    unittest.main()
