"""Performance and risk metrics for agent analytics."""

from __future__ import annotations

import math
from typing import Any, Optional, Sequence

TRADING_DAYS = 252
RISK_FREE_RATE = 0.04
INITIAL_CAPITAL = 100_000.0


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(parsed):
        return default
    return parsed


def max_drawdown(equity: Sequence[float]) -> float:
    if len(equity) < 2:
        return 0.0
    peak = equity[0]
    worst = 0.0
    for value in equity:
        if value > peak:
            peak = value
        if peak > 0:
            drawdown = (value - peak) / peak
            worst = min(worst, drawdown)
    return float(worst)


def sharpe_ratio(daily_returns: Sequence[float], rf: float = RISK_FREE_RATE) -> float:
    if len(daily_returns) < 2:
        return 0.0
    excess = [_safe_float(r) - rf / TRADING_DAYS for r in daily_returns]
    mean = sum(excess) / len(excess)
    variance = sum((x - mean) ** 2 for x in excess) / (len(excess) - 1)
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    return float(math.sqrt(TRADING_DAYS) * mean / std)


def sortino_ratio(daily_returns: Sequence[float], rf: float = RISK_FREE_RATE) -> float:
    if len(daily_returns) < 2:
        return 0.0
    excess = [_safe_float(r) - rf / TRADING_DAYS for r in daily_returns]
    mean = sum(excess) / len(excess)
    downside = [x for x in excess if x < 0]
    if not downside:
        return 0.0
    variance = sum(x * x for x in downside) / len(downside)
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    return float(math.sqrt(TRADING_DAYS) * mean / std)


def profit_factor(trade_returns: Sequence[float]) -> float:
    gains = sum(r for r in trade_returns if r > 0)
    losses = abs(sum(r for r in trade_returns if r < 0))
    if losses == 0:
        return float("inf") if gains > 0 else 0.0
    return float(gains / losses)


def win_rate(trade_returns: Sequence[float]) -> float:
    if not trade_returns:
        return 0.0
    wins = sum(1 for r in trade_returns if r > 0)
    return float(wins / len(trade_returns))


def expectancy(trade_returns: Sequence[float]) -> float:
    if not trade_returns:
        return 0.0
    return float(sum(trade_returns) / len(trade_returns))


def calmar_ratio(daily_returns: Sequence[float], equity: Sequence[float]) -> float:
    if len(daily_returns) < 2 or len(equity) < 2:
        return 0.0
    ann_return = (1 + sum(daily_returns) / len(daily_returns)) ** TRADING_DAYS - 1
    mdd = abs(max_drawdown(equity))
    if mdd == 0:
        return 0.0
    return float(ann_return / mdd)


def historical_var(daily_returns: Sequence[float], confidence: float = 0.95) -> float:
    if len(daily_returns) < 5:
        return 0.0
    sorted_returns = sorted(_safe_float(r) for r in daily_returns)
    index = max(0, int((1 - confidence) * len(sorted_returns)) - 1)
    return float(sorted_returns[index])


def equity_curve_from_profit(
    profits: Sequence[float],
    *,
    initial_capital: float = INITIAL_CAPITAL,
    deposited: float = 0.0,
) -> list[float]:
    base = initial_capital + deposited
    curve = [base + _safe_float(p) for p in profits]
    if not curve:
        return [base]
    return curve


def daily_returns_from_equity(equity: Sequence[float]) -> list[float]:
    if len(equity) < 2:
        return []
    returns: list[float] = []
    for prev, curr in zip(equity[:-1], equity[1:]):
        if prev == 0:
            returns.append(0.0)
        else:
            returns.append((curr - prev) / prev)
    return returns


def compute_agent_metrics(
    *,
    profits: Sequence[float],
    deposited: float = 0.0,
    trade_count: int = 0,
    position_count: int = 0,
    cash: float = 0.0,
) -> dict[str, Any]:
    equity = equity_curve_from_profit(profits, deposited=deposited)
    daily = daily_returns_from_equity(equity)
    total_return = (equity[-1] / equity[0] - 1) if equity[0] else 0.0

    trade_returns: list[float] = []
    if len(profits) >= 2:
        for prev, curr in zip(profits[:-1], profits[1:]):
            trade_returns.append(_safe_float(curr) - _safe_float(prev))

    return {
        "total_return": round(total_return, 6),
        "total_return_pct": round(total_return * 100, 4),
        "sharpe_ratio": round(sharpe_ratio(daily), 4),
        "sortino_ratio": round(sortino_ratio(daily), 4),
        "calmar_ratio": round(calmar_ratio(daily, equity), 4),
        "max_drawdown": round(max_drawdown(equity), 6),
        "max_drawdown_pct": round(max_drawdown(equity) * 100, 4),
        "profit_factor": round(profit_factor(trade_returns), 4) if math.isfinite(profit_factor(trade_returns)) else None,
        "win_rate": round(win_rate(trade_returns), 4),
        "expectancy": round(expectancy(trade_returns), 4),
        "var_95": round(historical_var(daily, 0.95), 6),
        "trade_count": trade_count,
        "position_count": position_count,
        "cash": round(_safe_float(cash), 2),
        "equity": round(equity[-1], 2) if equity else round(INITIAL_CAPITAL + deposited, 2),
        "observations": len(profits),
    }


def portfolio_value(cash: float, positions: Sequence[dict[str, Any]]) -> float:
    total = _safe_float(cash)
    for pos in positions:
        qty = abs(_safe_float(pos.get("quantity")))
        price = _safe_float(pos.get("current_price") or pos.get("entry_price"))
        total += qty * price
    return total
