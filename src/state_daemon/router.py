"""JSON-RPC 2.0 request router for the state daemon.

Parses JSON-RPC 2.0 requests, dispatches to registered method
handlers, and returns JSON-RPC 2.0 responses (or nothing for
notifications).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Awaitable
from typing import Any

import structlog

log = structlog.get_logger(__name__)

# JSON-RPC 2.0 error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INTERNAL_ERROR = -32603

# Handler signature: async fn(params: Any) -> Any
Handler = Callable[[Any], Awaitable[Any]]


class JsonRpcRouter:
    """Pluggable JSON-RPC 2.0 dispatcher.

    Usage::

        router = JsonRpcRouter()
        router.add_method("ping", lambda _: "pong")

        # Called by DaemonServer for each HTTP request:
        response_body = await router(method, path, headers, body)
    """

    def __init__(self) -> None:
        self._methods: dict[str, Handler] = {}

    def add_method(self, name: str, handler: Handler) -> None:
        """Register a JSON-RPC method handler.

        The handler receives ``params`` (any JSON-deserializable value)
        and must return a JSON-serializable result.
        """
        self._methods[name] = handler

    async def __call__(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        body: bytes,
    ) -> bytes:
        """Route an HTTP request through JSON-RPC 2.0 dispatch.

        Returns the JSON response body (empty bytes for notifications).

        This is the callable interface consumed by ``DaemonServer``.
        The server already handles Content-Type validation and GET
        /health, so this method focuses purely on JSON-RPC semantics.
        """
        # --- Parse JSON ---
        try:
            request = json.loads(body)
        except json.JSONDecodeError as e:
            log.warning(
                "daemon.router.parse_error",
                error=str(e),
            )
            return _jsonrpc_error(None, PARSE_ERROR, "Parse error: invalid JSON")

        # --- Validate JSON-RPC envelope ---
        if not isinstance(request, dict):
            return _jsonrpc_error(None, INVALID_REQUEST, "Invalid Request: not a JSON object")

        if request.get("jsonrpc") != "2.0":
            return _jsonrpc_error(
                request.get("id"),
                INVALID_REQUEST,
                "Invalid Request: jsonrpc must be '2.0'",
            )

        req_id = request.get("id")
        req_method = request.get("method", "")
        params = request.get("params", {})

        # --- Notification (no id) ---
        if req_id is None:
            handler = self._methods.get(req_method)
            if handler is not None:
                try:
                    await handler(params)
                except Exception:
                    log.exception(
                        "daemon.router.notification_handler_error",
                        method=req_method,
                    )
            # Notifications never send a response (JSON-RPC 2.0 §4.1)
            return b""

        # --- Method dispatch ---
        if not isinstance(req_method, str) or not req_method:
            return _jsonrpc_error(req_id, INVALID_REQUEST, "Invalid Request: method must be a non-empty string")

        handler = self._methods.get(req_method)
        if handler is None:
            return _jsonrpc_error(
                req_id,
                METHOD_NOT_FOUND,
                f"Method not found: {req_method}",
            )

        try:
            result = await handler(params)
            return _jsonrpc_success(req_id, result)
        except Exception as e:
            log.exception(
                "daemon.router.method_handler_error",
                method=req_method,
                error_type=type(e).__name__,
            )
            return _jsonrpc_error(
                req_id,
                INTERNAL_ERROR,
                f"Internal error: {e}",
            )


def _jsonrpc_success(req_id: Any, result: Any) -> bytes:
    """Build a JSON-RPC 2.0 success response."""
    return json.dumps(
        {"jsonrpc": "2.0", "result": result, "id": req_id}
    ).encode()


def _jsonrpc_error(req_id: Any, code: int, message: str) -> bytes:
    """Build a JSON-RPC 2.0 error response."""
    return json.dumps(
        {
            "jsonrpc": "2.0",
            "error": {"code": code, "message": message},
            "id": req_id,
        }
    ).encode()
