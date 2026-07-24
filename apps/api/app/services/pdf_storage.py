"""Storage dei PDF generati (Fase 5: generazione; Fase 9: persistenza in produzione).

Su un host con filesystem effimero (Render: il disco locale viene azzerato ad ogni deploy
o riavvio) salvare i PDF solo su disco locale significa perderli silenziosamente non
appena si effettua un secondo deploy — un bug reale, non solo teorico, per come questa
piattaforma era scritta prima di questa fase. Se Supabase Storage è configurato (stessa
service role key già usata per la Admin API di Fase 8), i PDF vengono caricati lì invece
che su disco: persistenti tra un deploy e l'altro, inclusi nei backup del progetto
Supabase.

Stesso principio di degradazione controllata di ogni altra integrazione esterna di questa
piattaforma: se Supabase Storage non è configurato — mai successo in questa sessione di
sviluppo, nessun progetto Supabase reale collegato — si ricade sul disco locale,
esattamente il comportamento che l'applicazione aveva prima di questa fase. Nessun
comportamento esistente cambia finché non si passa a un ambiente reale con Supabase
Storage configurato.

`pdf_url` (colonna `documents.pdf_url`) resta un riferimento opaco con prefisso
(`local://...` o `supabase://...`): il chiamante non deve mai sapere dove il file è
realmente salvato, solo passare questo riferimento a `load_pdf`.
"""

import logging

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 30.0

_LOCAL_PREFIX = "local://"
_SUPABASE_PREFIX = "supabase://"


def save_pdf(*, organization_id, filename: str, pdf_bytes: bytes) -> str:
    """Salva il PDF e ritorna il riferimento opaco da salvare in `documents.pdf_url`."""
    settings = get_settings()
    relative_path = f"documents/{organization_id}/{filename}"

    if settings.supabase_storage_configured:
        if _upload_to_supabase(settings, relative_path, pdf_bytes):
            return f"{_SUPABASE_PREFIX}{relative_path}"
        logger.warning(
            "Upload su Supabase Storage fallito: salvataggio di riserva su disco "
            "locale per %s (attenzione: su un host con filesystem effimero questo "
            "salvataggio non sarà persistente).",
            relative_path,
        )

    _save_local(settings, relative_path, pdf_bytes)
    return f"{_LOCAL_PREFIX}{relative_path}"


def load_pdf(pdf_url: str) -> bytes | None:
    """Legge i byte del PDF dal riferimento salvato in `documents.pdf_url`.

    Ritorna None se il file non esiste più (o non è mai stato salvato correttamente),
    mai un'eccezione: il chiamante trasforma questo in un 404 pulito."""
    settings = get_settings()
    if pdf_url.startswith(_SUPABASE_PREFIX):
        return _download_from_supabase(settings, pdf_url.removeprefix(_SUPABASE_PREFIX))
    if pdf_url.startswith(_LOCAL_PREFIX):
        return _load_local(settings, pdf_url.removeprefix(_LOCAL_PREFIX))
    logger.warning("Riferimento pdf_url non riconosciuto: %r", pdf_url)
    return None


def _save_local(settings: Settings, relative_path: str, pdf_bytes: bytes) -> None:
    file_path = settings.local_storage_path / relative_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(pdf_bytes)


def _load_local(settings: Settings, relative_path: str) -> bytes | None:
    file_path = settings.local_storage_path / relative_path
    if not file_path.exists():
        return None
    return file_path.read_bytes()


def _storage_object_url(settings: Settings, relative_path: str) -> str:
    return (
        f"{settings.supabase_url}/storage/v1/object/"
        f"{settings.supabase_storage_bucket}/{relative_path}"
    )


def _upload_to_supabase(
    settings: Settings, relative_path: str, pdf_bytes: bytes
) -> bool:
    try:
        response = httpx.post(
            _storage_object_url(settings, relative_path),
            headers={
                "Authorization": f"Bearer {settings.supabase_service_role_key}",
                "Content-Type": "application/pdf",
                # Consente di rigenerare un PDF con lo stesso nome (nuova versione dello
                # stesso documento) senza dover prima cancellare l'oggetto esistente.
                "x-upsert": "true",
            },
            content=pdf_bytes,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return True
    except httpx.HTTPError as exc:
        logger.warning(
            "Upload su Supabase Storage fallito (%s): %s", relative_path, exc
        )
        return False


def _download_from_supabase(settings: Settings, relative_path: str) -> bytes | None:
    try:
        response = httpx.get(
            _storage_object_url(settings, relative_path),
            headers={"Authorization": f"Bearer {settings.supabase_service_role_key}"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.content
    except httpx.HTTPError as exc:
        logger.warning(
            "Download da Supabase Storage fallito (%s): %s", relative_path, exc
        )
        return None
