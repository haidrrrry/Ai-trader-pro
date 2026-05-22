import os
import sys
import tempfile
import unittest
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parents[1]
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from analytics_metrics import (
    compute_agent_metrics,
    max_drawdown,
    sharpe_ratio,
    sortino_ratio,
)


class AnalyticsMetricsTests(unittest.TestCase):
    def test_max_drawdown_detects_peak_to_trough(self) -> None:
        equity = [100.0, 110.0, 105.0, 90.0, 95.0]
        self.assertLess(max_drawdown(equity), -0.1)

    def test_sharpe_positive_for_upward_drift(self) -> None:
        daily = [0.001 + (i * 0.00001) for i in range(30)]
        self.assertGreater(sharpe_ratio(daily), 0)

    def test_sortino_handles_no_downside(self) -> None:
        daily = [0.002] * 20
        self.assertGreaterEqual(sortino_ratio(daily), 0)

    def test_compute_agent_metrics_shape(self) -> None:
        metrics = compute_agent_metrics(
            profits=[1000, 1500, 1200, 2000],
            deposited=0,
            trade_count=4,
            position_count=1,
            cash=50000,
        )
        self.assertIn("sharpe_ratio", metrics)
        self.assertIn("max_drawdown", metrics)
        self.assertEqual(metrics["trade_count"], 4)
        self.assertGreater(metrics["equity"], 0)


if __name__ == "__main__":
    unittest.main()
