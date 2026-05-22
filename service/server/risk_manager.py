"""Pre-trade risk checks for agent operations."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from typing import Any, Optional, Sequence


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if math.isfinite(value) else default


MAX_POSITION_PCT = _env_float("MAX_POSITION_PCT", 0.25)
MAX_SINGLE_TRADE_PCT = _env_float("MAX_SINGLE_TRADE_PCT", 0.10)


@dataclass(frozen=True)
class RiskCheckResult:
    allowed: bool
    reason: Optional[str] = None
    details: Optional[dict[str, Any]] = None


def check_position_size_limit(
    *,
    trade_value: float,
    cash: float,
    open_positions: Sequence[dict[str, Any]],
    symbol: str,
    market: str,
    token_id: Optional[str] = None,
) -> RiskCheckResult:
    """Reject trades that breach max position or single-trade limits."""
    if trade_value <= 0 or not math.isfinite(trade_value):
        return RiskCheckResult(False, "Invalid trade value")

    portfolio = _safe_float(cash)
    existing_symbol_value = 0.0
    for pos in open_positions:
        qty = abs(_safe_float(pos.get("quantity")))
        price = _safe_float(pos.get("current_price") or pos.get("entry_price"))
        value = qty * price
        portfolio += value
        if _position_key(pos) == _position_key(
            {"symbol": symbol, "market": market, "token_id": token_id}
        ):
            existing_symbol_value += value

    if portfolio <= 0:
        return RiskCheckResult(True)

    projected_symbol_value = existing_symbol_value + trade_value
    symbol_pct = projected_symbol_value / portfolio
    trade_pct = trade_value / portfolio

    if trade_pct > MAX_SINGLE_TRADE_PCT:
        return RiskCheckResult(
            False,
            f"Single trade exceeds {MAX_SINGLE_TRADE_PCT:.0%} of portfolio",
            {
                "trade_pct": round(trade_pct, 4),
                "limit_pct": MAX_SINGLE_TRADE_PCT,
                "portfolio_value": round(portfolio, 2),
            },
        )

    if symbol_pct > MAX_POSITION_PCT:
        return RiskCheckResult(
            False,
            f"Position would exceed {MAX_POSITION_PCT:.0%} of portfolio",
            {
                "position_pct": round(symbol_pct, 4),
                "limit_pct": MAX_POSITION_PCT,
                "portfolio_value": round(portfolio, 2),
            },
        )

    return RiskCheckResult(True)


def _position_key(pos: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(pos.get("market") or "").strip().lower(),
        str(pos.get("symbol") or "").strip().upper(),
        str(pos.get("token_id") or "").strip(),
    )


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(parsed):
        return default
    return parsed
