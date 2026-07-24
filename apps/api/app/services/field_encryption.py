"""Cifratura simmetrica dei campi sensibili a riposo (Fase 8 — roadmap tecnica: "cifrare
dati sensibili a riposo nel database, almeno P.IVA e dati incidenti").

Usa Fernet (AES-128-CBC + HMAC, dalla libreria `cryptography` — già una dipendenza
transitiva di `python-jose[cryptography]`, nessun pacchetto nuovo) con una singola chiave
simmetrica da `FIELD_ENCRYPTION_KEY`. Fernet include già autenticazione (HMAC): un
attaccante con accesso al database non può né leggere né manomettere silenziosamente il
valore cifrato.

Se la chiave non è configurata, il valore viene salvato in chiaro con un avviso nei log
ad ogni scrittura — non un'eccezione, e mai una chiave effimera generata al volo: una
chiave che cambia ad ogni riavvio del processo renderebbe illeggibili per sempre i dati
già cifrati, un rischio di perdita dati inaccettabile solo per evitare un errore di
configurazione. Lo stesso principio di degradazione controllata di AI/Stripe/Resend, ma
applicato con più cautela perché qui l'alternativa "peggiore" possibile (perdere la
capacità di decifrare) è irreversibile.

Il prefisso `enc::` distingue un valore cifrato da uno salvato in chiaro (perché la
chiave non era ancora configurata, o perché la cifratura è stata introdotta dopo che
righe esistenti erano già state scritte): permette una migrazione incrementale, senza
dover ricifrare tutto il database in un'unica operazione."""

import logging

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_ENCRYPTED_PREFIX = "enc::"


def is_encryption_configured() -> bool:
    return get_settings().field_encryption_configured


def _fernet() -> Fernet | None:
    settings = get_settings()
    if not settings.field_encryption_configured:
        return None
    return Fernet(settings.field_encryption_key.encode())


def encrypt_value(value: str | None) -> str | None:
    """Cifra una stringa per la persistenza. None resta None (colonna nullable)."""
    if value is None:
        return None

    fernet = _fernet()
    if fernet is None:
        logger.warning(
            "FIELD_ENCRYPTION_KEY non configurata: valore salvato in chiaro, non "
            "protetto a riposo. Da impostare prima del lancio commerciale."
        )
        return value

    token = fernet.encrypt(value.encode("utf-8")).decode("ascii")
    return _ENCRYPTED_PREFIX + token


def decrypt_value(value: str | None) -> str | None:
    """Decifra un valore letto dal database. Riconosce e restituisce invariati i valori
    mai stati cifrati (nessun prefisso `enc::`), per compatibilità con righe scritte
    prima che la chiave fosse configurata."""
    if value is None:
        return None

    if not value.startswith(_ENCRYPTED_PREFIX):
        return value

    fernet = _fernet()
    if fernet is None:
        logger.error(
            "Trovato un valore cifrato ma FIELD_ENCRYPTION_KEY non è configurata: "
            "impossibile decifrarlo."
        )
        return None

    token = value[len(_ENCRYPTED_PREFIX) :]
    try:
        return fernet.decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken:
        logger.error(
            "Token cifrato non valido o chiave errata: valore non decifrabile."
        )
        return None
