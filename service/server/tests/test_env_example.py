import os
import sys
import unittest
from pathlib import Path

from dotenv import dotenv_values


SERVER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)


ROOT_DIR = Path(__file__).resolve().parents[3]


class EnvExampleTests(unittest.TestCase):
    def test_env_example_is_parseable_by_dotenv(self) -> None:
        values = dotenv_values(ROOT_DIR / ".env.example")

        self.assertEqual(values["ENVIRONMENT"], "development")
        self.assertIn("postgresql://", values["DATABASE_URL"])
        self.assertEqual(values["REDIS_ENABLED"], "true")
        self.assertEqual(values["ADANOS_API_BASE_URL"], "https://api.adanos.org")
        self.assertEqual(values["ALPHA_VANTAGE_BASE_URL"], "https://www.alphavantage.co/query")
        self.assertEqual(values["BINANCE_API_BASE_URL"], "https://api.binance.com")
        self.assertEqual(values["AI_TRADER_API_BACKGROUND_TASKS"], "false")
