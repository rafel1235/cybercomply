"""Tipi SQLAlchemy per colonne cifrate a riposo (Fase 8), trasparenti per il resto del
codice: si legge e si scrive un valore Python normale (str o dict), la cifratura e
decifratura avvengono solo nel driver, sotto `app/services/field_encryption.py`."""

import json
from typing import Any

from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from app.services.field_encryption import decrypt_value, encrypt_value


class EncryptedString(TypeDecorator):
    """Colonna stringa cifrata a riposo. Sostituisce `String(N)`: il testo cifrato è più
    lungo del valore originale, quindi la colonna nel database è `TEXT` (nessun limite).
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        return encrypt_value(value)

    def process_result_value(self, value: str | None, dialect) -> str | None:
        return decrypt_value(value)


class EncryptedJSON(TypeDecorator):
    """Colonna JSON cifrata a riposo. Sostituisce `JSONB`: il valore viene serializzato,
    cifrato, e salvato come `TEXT` — non è più interrogabile con operatori JSON lato SQL
    (compromesso accettato: nessun codice esistente filtra su questo campo, vedi
    ROADMAP_PROGRESS.md)."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: dict[str, Any] | None, dialect) -> str | None:
        if value is None:
            return None
        return encrypt_value(json.dumps(value))

    def process_result_value(self, value: str | None, dialect) -> dict[str, Any] | None:
        if value is None:
            return None
        decrypted = decrypt_value(value)
        if decrypted is None:
            return None
        return json.loads(decrypted)
