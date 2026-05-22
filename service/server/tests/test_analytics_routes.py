import os
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

SERVER_DIR = Path(__file__).resolve().parents[1]
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

import database
from routes import create_app
from routes_shared import utc_now_iso_z


class AnalyticsRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        database.DATABASE_URL = ""
        database._SQLITE_DB_PATH = os.path.join(self.tmp.name, "test.db")
        database.init_database()
        self.client = TestClient(create_app())

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _create_agent(self, name: str) -> int:
        now = utc_now_iso_z()
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO agents (name, token, points, cash, created_at, updated_at)
            VALUES (?, ?, 0, 100000, ?, ?)
            """,
            (name, f"token-{name}", now, now),
        )
        agent_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return agent_id

    def test_platform_summary(self) -> None:
        self._create_agent("Alpha")
        response = self.client.get("/api/analytics/summary")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["agent_count"], 1)
        self.assertIn("operation_signals", payload)

    def test_agent_rankings(self) -> None:
        agent_id = self._create_agent("Beta")
        now = utc_now_iso_z()
        conn = database.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO profit_history
            (agent_id, total_value, cash, position_value, profit, recorded_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (agent_id, 101000, 100000, 1000, 1000, now),
        )
        conn.commit()
        conn.close()

        response = self.client.get("/api/analytics/agents?limit=5")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(len(payload["agents"]), 1)
        self.assertIn("metrics", payload["agents"][0])

    def test_agent_performance_detail(self) -> None:
        agent_id = self._create_agent("Gamma")
        response = self.client.get(f"/api/analytics/agents/{agent_id}")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["agent_id"], agent_id)
        self.assertEqual(payload["name"], "Gamma")
        self.assertIn("sharpe_ratio", payload["metrics"])


if __name__ == "__main__":
    unittest.main()
