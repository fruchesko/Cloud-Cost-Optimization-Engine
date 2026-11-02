"""Request-size cap and security headers for every response (pure ASGI, so
streaming bodies are counted too, not just Content-Length)."""

from __future__ import annotations

import json

# The page's own script and styles only; inline style attributes are used for
# the result bars. /docs and /redoc load Swagger/ReDoc from a CDN, so they get
# every header except the CSP.
CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; "
       "form-action 'self'; frame-ancestors 'none'")
HEADERS = [
    (b"strict-transport-security", b"max-age=31536000"),
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"strict-origin-when-cross-origin"),
    (b"permissions-policy", b"camera=(), microphone=(), geolocation=(), payment=()"),
    (b"cross-origin-opener-policy", b"same-origin"),
]
NO_CSP = ("/docs", "/redoc")


class SecurityMiddleware:
    def __init__(self, app, max_body: int = 64 * 1024):
        self.app, self.max_body = app, max_body

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        extra = list(HEADERS)
        if not scope["path"].startswith(NO_CSP):
            extra.append((b"content-security-policy", CSP.encode()))

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                names = {k for k, _ in extra}
                message["headers"] = [h for h in message.get("headers", []) if h[0] not in names] + extra
            await send(message)

        too_big = json.dumps({"error": "too_large",
                              "message": f"Request body over {self.max_body // 1024} KB."}).encode()

        async def reject():
            await send_with_headers({"type": "http.response.start", "status": 413,
                                     "headers": [(b"content-type", b"application/json"),
                                                 (b"content-length", str(len(too_big)).encode())]})
            await send_with_headers({"type": "http.response.body", "body": too_big})

        length = dict(scope.get("headers") or []).get(b"content-length")
        if length is not None and (not length.isdigit() or int(length) > self.max_body):
            return await reject()

        received = 0
        exceeded = False

        async def counted_receive():
            nonlocal received, exceeded
            if exceeded:
                return {"type": "http.request", "body": b"", "more_body": False}
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_body:
                    # Stop reading; whatever the app answers is replaced by a 413.
                    exceeded = True
                    return {"type": "http.request", "body": b"", "more_body": False}
            return message

        replaced = False

        async def guarded_send(message):
            nonlocal replaced
            if exceeded:
                if not replaced:
                    replaced = True
                    await reject()
                return
            await send_with_headers(message)

        await self.app(scope, counted_receive, guarded_send)
