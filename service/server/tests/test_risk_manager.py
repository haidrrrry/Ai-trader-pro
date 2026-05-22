import sys
import unittest
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parents[1]
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from risk_manager import check_position_size_limit


class RiskManagerTests(unittest.TestCase):
    def test_allows_small_trade(self) -> None:
        result = check_position_size_limit(
            trade_value=5_000,
            cash=100_000,
            open_positions=[],
            symbol="AAPL",
            market="us-stock",
        )
        self.assertTrue(result.allowed)

    def test_blocks_oversized_single_trade(self) -> None:
        result = check_position_size_limit(
            trade_value=50_000,
            cash=100_000,
            open_positions=[],
            symbol="AAPL",
            market="us-stock",
        )
        self.assertFalse(result.allowed)
        self.assertIn("Single trade exceeds", result.reason or "")

    def test_blocks_position_concentration(self) -> None:
        result = check_position_size_limit(
            trade_value=5_000,
            cash=50_000,
            open_positions=[
                {
                    "symbol": "AAPL",
                    "market": "us-stock",
                    "token_id": "",
                    "quantity": 400,
                    "entry_price": 200,
                    "current_price": 200,
                }
            ],
            symbol="AAPL",
            market="us-stock",
        )
        self.assertFalse(result.allowed)
        self.assertIn("Position would exceed", result.reason or "")


if __name__ == "__main__":
    unittest.main()
