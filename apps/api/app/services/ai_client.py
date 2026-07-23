"""Wrapper interno per tutte le chiamate all'API Claude (Fase 5 — Generazione documenti
con AI, roadmap tecnica §Fase 5).

Centralizza in un unico posto: gestione errori, retry con backoff esponenziale sugli
errori transitori (429 rate limit, 503/529 sovraccarico), timeout per chiamata, e i dati
necessari per loggare ogni chiamata (token usati, costo stimato, durata) a fini di
monitoraggio spesa, come richiesto esplicitamente dalla roadmap.

Usa `httpx` direttamente (già una dipendenza del progetto) invece dell'SDK ufficiale
`anthropic`, per non introdurre un nuovo pacchetto da installare: l'ambiente di sviluppo di
questo progetto ha già avuto problemi seri con installazioni di dipendenze (vedi incidente
node_modules in Fase 4), quindi si preferisce ridurre al minimo le nuove dipendenze finché
non si lavora su un'infrastruttura più stabile.
"""

import time
from dataclasses import dataclass

import httpx

from app.core.config import get_settings

_ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"
_TIMEOUT_SECONDS = 30.0
_MAX_RETRIES = 3
_RETRYABLE_STATUS_CODES = {429, 500, 503, 529}


class AiGenerationError(Exception):
    """Sollevata quando la chiamata AI fallisce in modo non recuperabile (dopo i retry, o
    per un errore non transitorio come una chiave API non valida)."""


@dataclass
class AiCallResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    duration_ms: int

    def estimated_cost_usd(self) -> float | None:
        settings = get_settings()
        if (
            settings.anthropic_input_cost_per_mtok <= 0
            and settings.anthropic_output_cost_per_mtok <= 0
        ):
            return None
        cost = (
            self.input_tokens / 1_000_000 * settings.anthropic_input_cost_per_mtok
            + self.output_tokens / 1_000_000 * settings.anthropic_output_cost_per_mtok
        )
        return round(cost, 6)


def is_ai_configured() -> bool:
    """Vero solo se è stata impostata una vera chiave API (non il placeholder di
    `.env.example`), così il sistema può distinguere "AI non ancora attivata" da "AI
    attivata ma temporaneamente non raggiungibile"."""
    key = get_settings().anthropic_api_key
    return bool(key) and not key.startswith("replace-with")


def call_claude(
    system_prompt: str, user_prompt: str, *, max_tokens: int = 4096
) -> AiCallResult:
    """Chiama l'API Messages di Claude con retry automatico e backoff esponenziale sugli
    errori transitori. Solleva `AiGenerationError` se non configurata o se tutti i
    tentativi falliscono."""
    settings = get_settings()
    if not is_ai_configured():
        raise AiGenerationError("ANTHROPIC_API_KEY non configurata")

    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": _ANTHROPIC_VERSION,
        "content-type": "application/json",
    }
    body = {
        "model": settings.anthropic_model,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }

    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        started = time.monotonic()
        try:
            # trust_env=False: ignora eventuali proxy configurati nell'ambiente (utile sia
            # in questo sandbox di sviluppo sia in produzione, per non dipendere da
            # variabili d'ambiente non previste per una chiamata verso un'API esterna).
            with httpx.Client(timeout=_TIMEOUT_SECONDS, trust_env=False) as client:
                response = client.post(_ANTHROPIC_API_URL, headers=headers, json=body)
        except httpx.TimeoutException as exc:
            last_error = AiGenerationError(f"Timeout dopo {_TIMEOUT_SECONDS}s: {exc}")
            _sleep_backoff(attempt)
            continue
        except httpx.HTTPError as exc:
            last_error = AiGenerationError(f"Errore di rete verso l'API Claude: {exc}")
            _sleep_backoff(attempt)
            continue

        duration_ms = int((time.monotonic() - started) * 1000)

        if response.status_code in _RETRYABLE_STATUS_CODES:
            last_error = AiGenerationError(
                f"API Claude ha risposto {response.status_code} (tentativo "
                f"{attempt + 1}/{_MAX_RETRIES}): {response.text[:300]}"
            )
            _sleep_backoff(attempt)
            continue

        if response.status_code != 200:
            # Errore non transitorio (es. 401 chiave non valida, 400 richiesta malformata):
            # non ha senso ritentare.
            raise AiGenerationError(
                f"API Claude ha risposto {response.status_code}: {response.text[:300]}"
            )

        data = response.json()
        text = "".join(
            block.get("text", "")
            for block in data.get("content", [])
            if block.get("type") == "text"
        )
        usage = data.get("usage", {})
        return AiCallResult(
            text=text,
            model=data.get("model", settings.anthropic_model),
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            duration_ms=duration_ms,
        )

    raise last_error or AiGenerationError("Chiamata AI fallita dopo tutti i tentativi")


def _sleep_backoff(attempt: int) -> None:
    """Backoff esponenziale: 1s, 2s, 4s tra i tentativi."""
    time.sleep(2**attempt)
