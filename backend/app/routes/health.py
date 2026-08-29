"""
Health endpoints.

Two distinct checks, because a container platform needs to tell two different
questions apart:

* `/api/health`       — liveness. Is the process up and serving? Never touches
                        a dependency, so a database blip cannot cause the
                        orchestrator to kill and restart an otherwise healthy
                        container.
* `/api/health/ready` — readiness. Can this instance actually serve a request?
                        Checks the database, and Redis when one is configured.
                        Returns 503 when a hard dependency is down so a load
                        balancer stops sending traffic without killing the app.

Both are unauthenticated and exempt from rate limiting: a probe runs on a fixed
interval and must never be throttled into a false failure. Neither reveals
version numbers, connection strings or error detail to an unauthenticated
caller — a failed dependency reports only which one, and the reason is logged.
"""

import logging

from flask import Blueprint, current_app, jsonify
from sqlalchemy import text

from .. import limiter
from ..database import db

logger = logging.getLogger(__name__)

bp = Blueprint('health', __name__)


@bp.get('')
@limiter.exempt
def live():
    """Liveness: the process is up. Deliberately checks nothing else."""
    return jsonify({"status": "ok"}), 200


@bp.get('/ready')
@limiter.exempt
def ready():
    """Readiness: every hard dependency answers."""
    checks = {"database": _check_database()}

    broker_url = current_app.config.get("CELERY_BROKER_URL") or ""
    if broker_url.startswith("redis://") or broker_url.startswith("rediss://"):
        checks["redis"] = _check_redis(broker_url)

    healthy = all(checks.values())
    return jsonify({
        "status": "ready" if healthy else "degraded",
        "checks": {name: ("ok" if ok else "failed") for name, ok in checks.items()},
    }), (200 if healthy else 503)


def _check_database() -> bool:
    try:
        db.session.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        # Logged, not returned: a readiness probe is unauthenticated, and a
        # driver error string can carry the host and user it failed to reach.
        logger.warning("Readiness check failed on database: %s", exc)
        db.session.rollback()
        return False


def _check_redis(url: str) -> bool:
    try:
        import redis

        client = redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
        client.ping()
        return True
    except Exception as exc:
        logger.warning("Readiness check failed on redis: %s", exc)
        return False
