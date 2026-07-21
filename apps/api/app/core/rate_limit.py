"""Rate limiting su login e route sensibili (Fase 1: max tentativi login per IP)."""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
