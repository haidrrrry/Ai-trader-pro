"""Redis-backed rate limiting with database fallback."""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from typing import Optional

from cache import get_redis_client
from database import begin_write_transaction, get_db_connection
from routes_shared import utc_now_iso_z


def _redis_key(client_ip: str, action: str, window_seconds: int) -> str:
    window_id = int(time.time() // window_seconds)
    digest = hashlib.sha1(f"{client_ip}:{action}:{window_id}".encode("utf-8")).hexdigest()[:16]
    return f"rate_limit:{action}:{digest}"


def _check_rate_limit_db(
    client_ip: str,
    action: str,
    *,
    max_requests: int,
    window_seconds: int,
) -> tuple[bool, int]:
    now = datetime.now(timezone.utc)
    window_start = datetime.fromtimestamp(
        int(now.timestamp() // window_seconds) * window_seconds,
        tz=timezone.utc,
    ).isoformat().replace("+00:00", "Z")

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        begin_write_transaction(cursor)
        cursor.execute(
            """
            SELECT id, count, window_start
            FROM rate_limits
            WHERE client_ip = ? AND action = ?
            """,
            (client_ip, action),
        )
        row = cursor.fetchone()
        if row and row["window_start"] == window_start:
            count = int(row["count"] or 0) + 1
            if count > max_requests:
                conn.rollback()
                conn.close()
                return False, max_requests
            cursor.execute(
                "UPDATE rate_limits SET count = ? WHERE id = ?",
                (count, row["id"]),
            )
            conn.commit()
            conn.close()
            return True, count

        if row:
            cursor.execute(
                "UPDATE rate_limits SET count = 1, window_start = ? WHERE id = ?",
                (window_start, row["id"]),
            )
        else:
            cursor.execute(
                """
                INSERT INTO rate_limits (client_ip, action, count, window_start)
                VALUES (?, ?, 1, ?)
                """,
                (client_ip, action, window_start),
            )
        conn.commit()
        conn.close()
        return True, 1
    except Exception:
        conn.rollback()
        conn.close()
        raise


def check_rate_limit(
    client_ip: str,
    action: str,
    *,
    max_requests: int = 10,
    window_seconds: int = 3600,
) -> None:
    """Raise ValueError when the client exceeds the configured rate limit."""
    if not client_ip:
        client_ip = "unknown"

    client = get_redis_client()
    if client is not None:
        key = _redis_key(client_ip, action, window_seconds)
        count = client.incr(key)
        if count == 1:
            client.expire(key, window_seconds)
        if count > max_requests:
            raise ValueError(
                f"Rate limit exceeded for {action}: max {max_requests} per {window_seconds}s"
            )
        return

    allowed, count = _check_rate_limit_db(
        client_ip,
        action,
        max_requests=max_requests,
        window_seconds=window_seconds,
    )
    if not allowed:
        raise ValueError(
            f"Rate limit exceeded for {action}: max {max_requests} per {window_seconds}s (count={count})"
        )


def get_client_ip(request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host or "unknown"
    return "unknown"
