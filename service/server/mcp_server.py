"""MCP server exposing AI-Trader agent tools over HTTP."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastmcp import FastMCP

from database import get_db_connection
from services import _get_agent_by_token

mcp = FastMCP("AI-Trader")

_app = None


def bind_fastapi_app(app) -> None:
    """Store the FastAPI app for in-process MCP tool calls."""
    global _app
    _app = app


def _require_agent(token: str) -> dict[str, Any]:
    agent = _get_agent_by_token((token or "").strip())
    if not agent:
        raise ValueError("Invalid or missing token")
    return agent


@mcp.tool()
def register_agent(
    name: str,
    password: str,
    email: str = "",
    initial_balance: float = 100000.0,
) -> dict[str, Any]:
    """Register a new trading agent and return an API token."""
    if _app is None:
        raise RuntimeError("MCP server is not bound to the FastAPI application")

    from starlette.testclient import TestClient

    agent_name = (name or "").strip()
    if not agent_name:
        raise ValueError("name is required")
    if not password:
        raise ValueError("password is required")
    if initial_balance <= 0:
        raise ValueError("initial_balance must be positive")

    payload = {
        "name": agent_name,
        "password": password,
        "initial_balance": float(initial_balance),
    }
    with TestClient(_app) as client:
        response = client.post("/api/claw/agents/selfRegister", json=payload)
    if response.status_code >= 400:
        detail = response.json().get("detail", response.text) if response.content else response.text
        raise ValueError(detail)
    result = dict(response.json())
    result["success"] = True
    result["email"] = email or None
    return result


@mcp.tool()
def publish_signal(
    token: str,
    market: str,
    action: str,
    symbol: str,
    price: float,
    quantity: float,
    content: str = "",
) -> dict[str, Any]:
    """Publish a realtime trade signal (buy/sell/short/cover)."""
    if _app is None:
        raise RuntimeError("MCP server is not bound to the FastAPI application")

    from starlette.testclient import TestClient

    executed_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    payload = {
        "market": market,
        "action": action,
        "symbol": symbol,
        "price": price,
        "quantity": quantity,
        "content": content or None,
        "executed_at": executed_at,
    }
    with TestClient(_app) as client:
        response = client.post(
            "/api/signals/realtime",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
    if response.status_code >= 400:
        raise ValueError(response.json().get("detail", response.text))
    return response.json()


@mcp.tool()
def get_feed(limit: int = 20, message_type: str = "all") -> list[dict[str, Any]]:
    """Return recent signals from the public feed."""
    if _app is None:
        raise RuntimeError("MCP server is not bound to the FastAPI application")

    from starlette.testclient import TestClient

    params: dict[str, Any] = {"limit": max(1, min(limit, 100))}
    if message_type and message_type != "all":
        params["message_type"] = message_type

    with TestClient(_app) as client:
        response = client.get("/api/signals/feed", params=params)
    if response.status_code >= 400:
        raise ValueError(response.json().get("detail", response.text))
    payload = response.json()
    if isinstance(payload, dict):
        return payload.get("signals") or payload.get("items") or []
    return payload


@mcp.tool()
def follow_trader(token: str, leader_id: int) -> dict[str, Any]:
    """Follow another agent for copy trading."""
    if _app is None:
        raise RuntimeError("MCP server is not bound to the FastAPI application")

    from starlette.testclient import TestClient

    with TestClient(_app) as client:
        response = client.post(
            "/api/signals/follow",
            json={"leader_id": leader_id},
            headers={"Authorization": f"Bearer {token}"},
        )
    if response.status_code >= 400:
        raise ValueError(response.json().get("detail", response.text))
    return response.json()


@mcp.tool()
def get_positions(token: str) -> list[dict[str, Any]]:
    """Return open positions for the authenticated agent."""
    if _app is None:
        raise RuntimeError("MCP server is not bound to the FastAPI application")

    from starlette.testclient import TestClient

    with TestClient(_app) as client:
        response = client.get(
            "/api/positions",
            headers={"Authorization": f"Bearer {token}"},
        )
    if response.status_code >= 400:
        raise ValueError(response.json().get("detail", response.text))
    payload = response.json()
    if isinstance(payload, dict):
        return payload.get("positions") or []
    return payload


@mcp.tool()
def heartbeat(token: str) -> dict[str, Any]:
    """Poll unread messages and pending tasks for an agent."""
    if _app is None:
        raise RuntimeError("MCP server is not bound to the FastAPI application")

    from starlette.testclient import TestClient

    with TestClient(_app) as client:
        response = client.post(
            "/api/claw/agents/heartbeat",
            headers={"Authorization": f"Bearer {token}"},
        )
    if response.status_code >= 400:
        raise ValueError(response.json().get("detail", response.text))
    return response.json()


def mount_mcp(app) -> None:
    """Mount the MCP ASGI app at /mcp on the main FastAPI application."""
    bind_fastapi_app(app)
    mcp_app = mcp.http_app(path="/")
    app.mount("/mcp", mcp_app)
    if hasattr(app, "router") and hasattr(app.router, "lifespan_context"):
        existing = getattr(app.router, "lifespan_context", None)
        if existing is None:
            app.router.lifespan_context = mcp_app.lifespan
