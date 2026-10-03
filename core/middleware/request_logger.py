"""Middleware que registra cada request HTTP em ``LogRequest``.

Diferenças em relação ao padrão do Noclaf:

- ``path`` guarda **somente** a URL (sem querystring) — facilita agregação.
- A querystring é serializada como JSON em ``params``.
- Body é parseado quando JSON e tem chaves sensíveis (password, token, hash,
  authorization, secret, key) **redatadas** antes de gravar.

Configuração (todas opcionais, com defaults sãos):

- ``LOG_REQUESTS_ENABLED`` (bool, default ``True``) — desliga o middleware.
- ``LOG_REQUESTS_EXCLUDE_PATHS`` (list[str], default lista abaixo) —
  prefixos de URL que **não** são logados (admin, static, health, schema).
- ``LOG_REQUESTS_SKIP_READ_PATHS`` (list[str], default vazio) — prefixos cujos
  GET/HEAD não são logados (escritas continuam).

Cada log grava ``cache_status`` (HIT/MISS do cache público) e a resposta leva o
header ``X-Cache``. A gravação vai para ``core.services.deferred_writes``.
- ``LOG_REQUESTS_MAX_BODY`` (int, default ``10_000``) — bytes máximos do body
  parseado. Acima disso o body vira ``"<truncated>"``.
- ``LOG_REQUESTS_RETENTION_DAYS`` (int, default ``30``) — usado pelo cron
  ``purge_old_request_logs``.
"""

from __future__ import annotations

import json
import logging
import shlex
import time
from typing import Any

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.utils.timezone import now

logger = logging.getLogger(__name__)

_DEFAULT_EXCLUDES = (
    "/admin/",
    "/static/",
    "/media/",
    "/favicon.ico",
    "/api/v1/health",
    "/api/schema",
    "/api/docs",
    "/api/redoc",
)

_REDACT_KEYS = {
    "password",
    "old_password",
    "new_password",
    "forgot_password_hash",
    "email_verification_code",
    "token",
    "access",
    "refresh",
    "secret",
    "authorization",
    "api_key",
    "apikey",
}

_REDACT_HEADER_PREFIXES = ("HTTP_AUTHORIZATION", "HTTP_COOKIE", "HTTP_X_API_KEY")


def _redact(value: Any) -> Any:
    """Recursivamente substitui valores de chaves sensíveis por ``"***"``."""
    if isinstance(value, dict):
        return {k: ("***" if k.lower() in _REDACT_KEYS else _redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


def _client_ip(request) -> str:
    fwd = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "") or ""


def _build_curl(request, body) -> str | None:
    """Monta um cURL aproximado do request (útil para reproduzir bug)."""
    try:
        scheme = "https" if request.is_secure() else "http"
        host = request.get_host()
        full_url = f"{scheme}://{host}{request.get_full_path()}"
        parts = [f"curl -X {request.method} {shlex.quote(full_url)}"]
        for key, value in request.META.items():
            if key in _REDACT_HEADER_PREFIXES:
                value = "***"
            if key.startswith("HTTP_"):
                header_name = key[5:].replace("_", "-").title()
                parts.append(f"  -H {shlex.quote(f'{header_name}: {value}')}")
            elif key == "CONTENT_TYPE" and value:
                parts.append(f"  -H {shlex.quote(f'Content-Type: {value}')}")
        if body not in (None, "", b""):
            body_str = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)
            parts.append(f"  -d {shlex.quote(body_str)}")
        return " \\\n".join(parts)
    except Exception:  # noqa: BLE001 - cURL é best-effort
        return None


def _is_excluded(path: str, method: str = "GET") -> bool:
    excludes = getattr(settings, "LOG_REQUESTS_EXCLUDE_PATHS", _DEFAULT_EXCLUDES)
    if any(path.startswith(prefix) for prefix in excludes):
        return True
    if method in ("GET", "HEAD"):
        return any(path.startswith(prefix) for prefix in getattr(settings, "LOG_REQUESTS_SKIP_READ_PATHS", ()))
    return False


class RequestLoggerMiddleware(MiddlewareMixin):
    """Persiste cada request em ``LogRequest`` (best-effort, nunca derruba a
    response em caso de erro)."""

    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, "LOG_REQUESTS_ENABLED", True):
            return self.get_response(request)

        path_only = request.path
        if _is_excluded(path_only, request.method):
            return self.get_response(request)

        from core.services import public_cache

        tracking = public_cache.start_tracking()
        start_time = time.monotonic()
        max_body = int(getattr(settings, "LOG_REQUESTS_MAX_BODY", 10_000))
        body_payload: Any = None

        try:
            content_type = request.content_type or ""
            if "multipart" not in content_type:
                raw_body = request.body
                if raw_body and len(raw_body) <= max_body:
                    try:
                        parsed = json.loads(raw_body.decode("utf-8"))
                        body_payload = _redact(parsed)
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        body_payload = None
                elif raw_body:
                    body_payload = "<truncated>"
        except Exception:  # noqa: BLE001 - leitura de body é best-effort
            body_payload = None

        curl_command = _build_curl(request, body_payload)

        try:
            response = self.get_response(request)
        finally:
            cache_status = public_cache.stop_tracking(tracking)
        if cache_status:
            response["X-Cache"] = cache_status

        try:
            from core.models import LogRequest
            from core.services.deferred_writes import defer

            params_json = ""
            try:
                if request.GET:
                    params_json = json.dumps(request.GET.dict(), ensure_ascii=False)
            except Exception:  # noqa: BLE001
                params_json = ""

            data_json: str | None = None
            if body_payload is not None:
                try:
                    data_json = (
                        body_payload
                        if isinstance(body_payload, str)
                        else json.dumps(body_payload, ensure_ascii=False)
                    )
                except Exception:  # noqa: BLE001
                    data_json = None

            user_obj = getattr(request, "user", None)
            if user_obj is not None and getattr(user_obj, "is_authenticated", False):
                user_fk = user_obj
                user_email = (getattr(user_obj, "email", "") or "")[:255]
            else:
                user_fk = None
                user_email = ""

            # Gravado na thread de fundo: o log não pode deixar a resposta esperando o banco.
            defer(
                LogRequest.objects.create,
                timestamp=now(),
                method=request.method,
                path=path_only,
                execution_time=time.monotonic() - start_time,
                status_code=getattr(response, "status_code", None),
                data=data_json,
                params=params_json,
                ip=_client_ip(request)[:45],
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                curl=curl_command,
                user=user_fk,
                user_email=user_email,
                cache_status=cache_status,
            )
        except Exception:  # noqa: BLE001 - log nunca pode quebrar a request
            logger.exception("RequestLoggerMiddleware falhou ao persistir log")

        return response
