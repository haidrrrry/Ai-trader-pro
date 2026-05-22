"""Analytics API — agent performance and platform summary."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI, HTTPException

from analytics_metrics import INITIAL_CAPITAL, compute_agent_metrics
from database import get_db_connection
from routes_shared import RouteContext, clamp_profit_for_display


def _fetch_agent_row(cursor: Any, agent_id: int) -> Optional[dict[str, Any]]:
    cursor.execute(
        """
        SELECT id, name, cash, deposited, points, reputation_score, created_at
        FROM agents
        WHERE id = ?
        """,
        (agent_id,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def _fetch_profit_series(cursor: Any, agent_id: int, limit: int = 500) -> list[float]:
    cursor.execute(
        """
        SELECT profit
        FROM profit_history
        WHERE agent_id = ?
        ORDER BY recorded_at ASC
        LIMIT ?
        """,
        (agent_id, limit),
    )
    return [clamp_profit_for_display(row["profit"]) for row in cursor.fetchall()]


def _fetch_open_positions(cursor: Any, agent_id: int) -> list[dict[str, Any]]:
    cursor.execute(
        """
        SELECT symbol, market, token_id, side, quantity, entry_price, current_price
        FROM positions
        WHERE agent_id = ?
        """,
        (agent_id,),
    )
    return [dict(row) for row in cursor.fetchall()]


def _agent_performance_payload(cursor: Any, agent_id: int) -> dict[str, Any]:
    agent = _fetch_agent_row(cursor, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    profits = _fetch_profit_series(cursor, agent_id)
    positions = _fetch_open_positions(cursor, agent_id)

    cursor.execute(
        """
        SELECT COUNT(*) AS count
        FROM signals
        WHERE agent_id = ? AND message_type = 'operation'
        """,
        (agent_id,),
    )
    trade_count = int(cursor.fetchone()["count"] or 0)

    metrics = compute_agent_metrics(
        profits=profits,
        deposited=float(agent.get("deposited") or 0),
        trade_count=trade_count,
        position_count=len(positions),
        cash=float(agent.get("cash") or 0),
    )

    return {
        "agent_id": agent_id,
        "name": agent["name"],
        "points": agent.get("points", 0),
        "reputation_score": agent.get("reputation_score", 0),
        "created_at": agent.get("created_at"),
        "metrics": metrics,
        "positions": positions,
    }


def register_analytics_routes(app: FastAPI, ctx: RouteContext) -> None:
    del ctx

    @app.get("/api/analytics/summary")
    async def platform_summary():
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) AS count FROM agents")
        agent_count = int(cursor.fetchone()["count"] or 0)

        cursor.execute(
            """
            SELECT COUNT(*) AS count
            FROM signals
            WHERE message_type = 'operation'
            """
        )
        operation_count = int(cursor.fetchone()["count"] or 0)

        cursor.execute("SELECT COUNT(*) AS count FROM positions")
        open_positions = int(cursor.fetchone()["count"] or 0)

        cursor.execute("SELECT COALESCE(SUM(cash), 0) AS total_cash FROM agents")
        total_cash = float(cursor.fetchone()["total_cash"] or 0)

        cursor.execute(
            """
            SELECT COUNT(DISTINCT leader_id) AS count
            FROM subscriptions
            WHERE status = 'active'
            """
        )
        active_follows = int(cursor.fetchone()["count"] or 0)

        conn.close()
        return {
            "agent_count": agent_count,
            "operation_signals": operation_count,
            "open_positions": open_positions,
            "total_cash": round(total_cash, 2),
            "active_copy_relationships": active_follows,
            "initial_capital_per_agent": INITIAL_CAPITAL,
        }

    @app.get("/api/analytics/agents")
    async def agent_rankings(limit: int = 20, metric: str = "sharpe_ratio"):
        limit = max(1, min(limit, 100))
        metric = (metric or "sharpe_ratio").strip().lower()
        allowed = {
            "sharpe_ratio",
            "sortino_ratio",
            "total_return",
            "max_drawdown",
            "trade_count",
            "equity",
        }
        if metric not in allowed:
            metric = "sharpe_ratio"

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM agents ORDER BY id ASC")
        agent_ids = [row["id"] for row in cursor.fetchall()]

        rankings: list[dict[str, Any]] = []
        for agent_id in agent_ids:
            try:
                payload = _agent_performance_payload(cursor, agent_id)
            except HTTPException:
                continue
            rankings.append(
                {
                    "agent_id": payload["agent_id"],
                    "name": payload["name"],
                    "metrics": payload["metrics"],
                }
            )

        conn.close()

        reverse = metric != "max_drawdown"
        rankings.sort(
            key=lambda item: (item["metrics"].get(metric) is None, item["metrics"].get(metric, 0)),
            reverse=reverse,
        )
        return {"metric": metric, "agents": rankings[:limit], "total": len(rankings)}

    @app.get("/api/analytics/agents/{agent_id}")
    async def agent_performance(agent_id: int):
        conn = get_db_connection()
        cursor = conn.cursor()
        payload = _agent_performance_payload(cursor, agent_id)
        conn.close()
        return payload
