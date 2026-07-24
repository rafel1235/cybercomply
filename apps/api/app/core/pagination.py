"""Paginazione condivisa (Fase 10 — performance).

La roadmap tecnica chiede esplicitamente di "paginare tutte le liste (mai restituire
array illimitati)". Gli endpoint interessati sono quelli il cui numero di righe cresce nel
tempo con l'uso della piattaforma (documenti generati, incidenti, assessment eseguiti,
fornitori, storico dello score di conformità) — a differenza di endpoint come
`GET /compliance/measures`, intrinsecamente limitati alle ~15 misure del catalogo, che non
necessitano di paginazione.

Per non rompere il contratto esistente con il frontend (che consuma già `list[...]`
direttamente, non un involucro `{items, total}`), la forma scelta è la stessa già in uso
per `GET /audit-log` fin dalla Fase 4: parametri di query `limit`/`offset` applicati alla
query SQL con `LIMIT`/`OFFSET`, corpo della risposta invariato (una lista), conteggio
totale esposto in un header `X-Total-Count` per un'eventuale futura UI di paginazione senza
dover cambiare ancora il contratto della risposta."""

from fastapi import Response
from sqlalchemy.orm import Query

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def clamp_limit(limit: int, *, maximum: int = MAX_LIMIT) -> int:
    """Riporta `limit` in un intervallo sicuro [1, maximum]."""
    return max(1, min(limit, maximum))


def clamp_offset(offset: int) -> int:
    """Un offset negativo non ha senso: lo riporta a 0 invece di un errore 422, coerente
    con la tolleranza già usata altrove nell'API per input di poco valore."""
    return max(0, offset)


def apply_pagination(
    query: Query, response: Response, *, limit: int, offset: int
) -> Query:
    """Applica `LIMIT`/`OFFSET` alla query, imposta `X-Total-Count` sulla risposta (contato
    PRIMA di applicare `limit`/`offset`, quindi con un costo aggiuntivo di una sola query
    `COUNT` — accettabile per le liste di questa dimensione) e ritorna la query paginata,
    pronta per `.all()`."""
    total = query.order_by(None).count()
    response.headers["X-Total-Count"] = str(total)
    return query.offset(clamp_offset(offset)).limit(clamp_limit(limit))
