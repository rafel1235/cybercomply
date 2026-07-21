"""Logging strutturato in JSON, come richiesto dalla roadmap (Fase 3: 'logging strutturato
di ogni request: metodo, path, status, durata, user_id')."""

import json
import logging
import sys
import time
import uuid
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("cybercomplyit")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(message)s"))
if not logger.handlers:
    logger.addHandler(_handler)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        request_id = str(uuid.uuid4())
        user_id = "anonymous"

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        user_id = getattr(request.state, "user_id", user_id)

        logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                    "user_id": user_id,
                }
            )
        )
        response.headers["X-Request-ID"] = request_id
        return response
