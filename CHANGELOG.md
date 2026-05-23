# Changelog

All notable changes to this fork are documented here.

## [1.1.0] - 2026-05-22

### Added

- Agent Analytics API: `/api/analytics/summary`, `/api/analytics/agents`, `/api/analytics/agents/{id}`
- Analytics metrics module: Sharpe, Sortino, Calmar, Max Drawdown, VaR, Win Rate, Profit Factor, Expectancy
- Risk management pre-trade checks: max position % and max single-trade % limits
- Agent Analytics Dashboard frontend page at `/analytics`
- Research notebooks: `Agent_Backtesting_Engine.ipynb`, `Multi_Agent_Collaboration_Experiments.ipynb`
- `research/strategy_optimizer.py` — RSI grid search + walk-forward CLI (vectorbt)
- Prometheus metrics at `GET /metrics` via `prometheus-fastapi-instrumentator`
- Docker Compose services: `prometheus` (9090), `grafana` (3001)
- Database backup/restore scripts: `scripts/backup.sh`, `scripts/restore.sh`
- `ARCHITECTURE.md` — full system design documentation with Mermaid diagrams
- Professional README rewrite with comparison table, academic use cases, skills demonstrated

### Changed

- README research section updated with all three notebooks
- `research/requirements.txt` expanded with vectorbt, plotly, jupyter

### Fixed (upstream issue parity)

- HKUDS #186: short position add-to uses weighted average entry price (with regression test)
- HKUDS #188: market-intel stock quotes fall back to yfinance when Alpha Vantage unavailable
- HKUDS #141: selfRegister position quantity/entry_price validated via Pydantic; short qty stored negative
- MCP `register_agent` routes through REST selfRegister (rate limits + experiment assignment)
- `MAX_PARALLEL_PRICE_FETCH` default aligned with `.env.example` (5)

## [1.0.0] - 2026-05-22

Maintained by [haidrrrry](https://github.com/haidrrrry). Forked from [HKUDS/AI-Trader](https://github.com/HKUDS/AI-Trader) (MIT).

Repository: https://github.com/haidrrrry/Ai-trader-pro

### Added

- `.gitattributes` for consistent filename casing on Windows
- Redis-backed rate limiting on `POST /api/claw/agents/selfRegister` and other public endpoints
- MCP server at `/mcp` via `fastmcp` with tools: register, publish signal, feed, follow, positions, heartbeat
- Docker Compose stack: `api`, `worker`, `postgres`, `redis`
- `Dockerfile` and `Dockerfile.worker` for containerized deployment
- Free US stock quotes via `yfinance` and crypto quotes via Binance public REST API
- Pydantic validators on trade and numeric request fields (422 instead of 500)
- Engagement-based leaderboard quality score with 50 points/day discussion cap
- Mobile-responsive frontend (hamburger nav, 375px layouts)
- Complete `.env.example` with all documented environment variables
- Startup validation for required configuration (`DATABASE_URL`, `REDIS_URL` when enabled)
- Self-hosting guide in README

### Changed

- PostgreSQL required for production (`DATABASE_URL`); SQLite only for tests via `ALLOW_SQLITE` / pytest
- API process no longer runs background tasks by default (`AI_TRADER_API_BACKGROUND_TASKS=false`)
- Alpha Vantage is optional override when `ALPHA_VANTAGE_API_KEY` is set (non-demo)

### Fixed

- Windows filename casing compatibility via `.gitattributes`
- Background worker separation from FastAPI web server (with deprecation warning if re-enabled in API)
- Input validation on price/quantity fields (issue #141 class of bugs)
- Unprotected agent self-registration endpoint
