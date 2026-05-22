"""
Routes Module

所有 API 路由定义入口。
"""

import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from config import CORS_ORIGINS
from rate_limit import check_rate_limit, get_client_ip
from routes_agent import register_agent_routes
from routes_challenges import register_challenge_routes
from routes_experiments import register_experiment_routes
from routes_market import register_market_routes
from routes_misc import register_misc_routes
from routes_research import register_research_routes
from routes_shared import RouteContext
from routes_signals import register_signal_routes
from routes_team_missions import register_team_mission_routes
from routes_trading import register_trading_routes
from routes_users import register_user_routes


PUBLIC_POST_RATE_LIMITS: dict[str, tuple[int, int]] = {
    "/api/claw/agents/selfregister": (10, 3600),
    "/api/claw/agents/login": (30, 3600),
    "/api/users/send-code": (5, 3600),
    "/api/users/register": (10, 3600),
    "/api/users/login": (30, 3600),
}


def create_app() -> FastAPI:
    app = FastAPI(title='AI-Trader API')

    @app.middleware("http")
    async def public_post_rate_limit(request: Request, call_next):
        if request.method == "POST":
            path_key = request.url.path.rstrip("/").lower()
            limits = PUBLIC_POST_RATE_LIMITS.get(path_key)
            if limits:
                max_requests, window_seconds = limits
                try:
                    check_rate_limit(
                        get_client_ip(request),
                        f"public:{path_key}",
                        max_requests=max_requests,
                        window_seconds=window_seconds,
                    )
                except ValueError as exc:
                    raise HTTPException(status_code=429, detail=str(exc)) from exc
        return await call_next(request)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    @app.middleware('http')
    async def add_process_time_header(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        response.headers['X-Process-Time'] = str(time.time() - start_time)
        return response

    ctx = RouteContext()
    register_market_routes(app, ctx)
    register_agent_routes(app, ctx)
    register_signal_routes(app, ctx)
    register_trading_routes(app, ctx)
    register_experiment_routes(app, ctx)
    register_research_routes(app, ctx)
    register_challenge_routes(app, ctx)
    register_team_mission_routes(app, ctx)
    register_user_routes(app, ctx)
    register_misc_routes(app)
    return app
