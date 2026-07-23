"""Rate limiting su login (Fase 1) e globale sull'intera API (Fase 3: 'rate limiting
globale sull'API, es. 100 req/min per utente')."""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.security import InvalidTokenError, decode_supabase_jwt


def rate_limit_key(request: Request) -> str:
    """Usa l'utente autenticato come chiave quando possibile, altrimenti l'IP.

    Il rate limit globale (Fase 3) deve valere 'per utente', ma prima dell'autenticazione
    (o per endpoint pubblici, es. login) l'unica chiave disponibile è l'indirizzo IP.
    """
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:]
        try:
            supabase_user = decode_supabase_jwt(token)
            return f"user:{supabase_user.id}"
        except InvalidTokenError:
            pass
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=rate_limit_key, default_limits=["100/minute"])
