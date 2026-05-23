import os
import sys
import tempfile
import unittest
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parents[1]
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

import database
from mcp_server import bind_fastapi_app, register_agent
from routes import create_app


class McpRegistrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["ALLOW_SQLITE"] = "true"
        database.DATABASE_URL = ""
        database._SQLITE_DB_PATH = os.path.join(self.tmp.name, "test.db")
        database.init_database()
        bind_fastapi_app(create_app())

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_register_agent_uses_rest_path(self) -> None:
        result = register_agent("mcp_agent_alpha", "secret-pass-123")
        self.assertTrue(result.get("success"))
        self.assertIn("token", result)
        self.assertIn("experiment_assignments", result)
        self.assertEqual(result.get("name"), "mcp_agent_alpha")

    def test_register_agent_rejects_duplicate_name(self) -> None:
        register_agent("mcp_agent_beta", "secret-pass-123")
        with self.assertRaises(ValueError):
            register_agent("mcp_agent_beta", "another-pass-456")


if __name__ == "__main__":
    unittest.main()
