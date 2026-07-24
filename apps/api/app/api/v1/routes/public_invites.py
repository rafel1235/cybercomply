from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.organization import Organization, OrganizationInvite
from app.schemas.organization import InvitePublicOut

router = APIRouter(prefix="/public/invites", tags=["public-invites"])


@router.get("/{token}", response_model=InvitePublicOut)
def get_public_invite(token: str, db: Session = Depends(get_db)) -> InvitePublicOut:
    """Anteprima di un invito prima della registrazione (Fase 7): nessuna verifica di
    autenticazione, il possesso del token (ricevuto via email) è di per sé la
    credenziale, come per i questionari fornitori. Un token sconosciuto è un 404 vero e
    proprio; un invito trovato ma scaduto o già accettato torna 200 con `valid=False` e
    un motivo, così la pagina di registrazione può spiegare cosa è successo invece di
    mostrare un errore generico."""
    invite = (
        db.query(OrganizationInvite).filter(OrganizationInvite.token == token).first()
    )
    if invite is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invito non trovato"
        )

    organization = db.get(Organization, invite.organization_id)
    now = datetime.now(timezone.utc)

    reason = None
    if invite.accepted_at is not None:
        reason = "Questo invito è già stato accettato."
    elif invite.expires_at <= now:
        reason = (
            "Questo invito è scaduto: chiedi a un amministratore di inviarne uno nuovo."
        )

    return InvitePublicOut(
        organization_name=organization.name if organization else "",
        invited_email=invite.invited_email,
        role=invite.role.value,
        valid=reason is None,
        reason=reason,
    )
