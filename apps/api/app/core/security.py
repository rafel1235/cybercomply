"""Verifica dei JWT emessi da Supabase Auth.

Non implementiamo login/password da zero (indicazione esplicita della roadmap): Supabase
gestisce la registrazione, il login e il reset password. Il backend si limita a verificare
la firma e la scadenza del token per proteggere le route autenticate.
"""

from dataclasses import dataclass

from jose import JWTError, jwt

from app.core.config import get_settings


class InvalidTokenError(Exception):
    pass


@dataclass
class SupabaseUser:
    id: str
    email: str | None
    role: str | None


def decode_supabase_jwt(token: str) -> SupabaseUser:
    settings = get_settings()
    if not settings.supabase_jwt_secret:
        raise InvalidTokenError(
            "SUPABASE_JWT_SECRET non configurato: impostalo in .env con la chiave reale "
            "del progetto Supabase (Fase 1, non ancora collegata a un progetto reale)."
        )
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    subject = payload.get("sub")
    if not subject:
        raise InvalidTokenError("Token senza subject valido")

    return SupabaseUser(
        id=subject,
        email=payload.get("email"),
        role=payload.get("role"),
    )
