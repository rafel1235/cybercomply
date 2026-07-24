from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import InvalidTokenError, SupabaseUser, decode_supabase_jwt
from app.db.session import get_db
from app.models.organization import Organization, OrganizationMember, OrganizationRole
from app.models.user import User
from app.services.entitlements import PlanEntitlements, get_entitlements

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_supabase_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> SupabaseUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token mancante"
        )
    try:
        supabase_user = decode_supabase_jwt(credentials.credentials)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc

    request.state.user_id = supabase_user.id
    return supabase_user


def get_current_user(
    supabase_user: SupabaseUser = Depends(get_current_supabase_user),
    db: Session = Depends(get_db),
) -> User:
    user = db.get(User, supabase_user.id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utente autenticato su Supabase ma non ancora sincronizzato: "
            "chiamare prima POST /api/v1/auth/sync",
        )
    return user


@dataclass
class CurrentMembership:
    """L'organizzazione 'corrente' dell'utente autenticato, con il suo ruolo.

    L'MVP assume un'organizzazione principale per utente (quella creata alla
    registrazione, vedi Fase 1): se in futuro un utente potrà appartenere a più
    organizzazioni (multi-tenant switch), qui si aggiungerà la lettura di un header
    esplicito (es. `X-Organization-Id`) invece di prendere sempre la prima iscrizione.
    """

    organization: Organization
    role: OrganizationRole
    user: User


def get_current_membership(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CurrentMembership:
    membership = (
        db.query(OrganizationMember)
        .filter(OrganizationMember.user_id == user.id)
        .order_by(OrganizationMember.joined_at.asc())
        .first()
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nessuna organizzazione associata a questo utente",
        )
    organization = db.get(Organization, membership.organization_id)
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organizzazione non trovata"
        )
    return CurrentMembership(organization=organization, role=membership.role, user=user)


def require_admin(
    membership: CurrentMembership = Depends(get_current_membership),
) -> CurrentMembership:
    """Dipendenza da usare sulle route riservate al ruolo Admin (i Viewer sono in sola
    lettura, come definito in Fase 1)."""
    if membership.role != OrganizationRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operazione riservata agli amministratori dell'organizzazione",
        )
    return membership


def get_current_entitlements(
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> PlanEntitlements:
    """Limiti del piano attivo dell'organizzazione corrente (Fase 6)."""
    return get_entitlements(db, membership.organization.id)


def require_incident_reporting(
    entitlements: PlanEntitlements = Depends(get_current_entitlements),
) -> PlanEntitlements:
    if not entitlements.incident_reporting_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Il modulo Incident Reporting non è incluso nel piano Free. Passa a "
            "Essential o superiore per sbloccarlo.",
        )
    return entitlements


def require_supply_chain(
    entitlements: PlanEntitlements = Depends(get_current_entitlements),
) -> PlanEntitlements:
    if not entitlements.supply_chain_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Il modulo Supply Chain Risk non è incluso nel tuo piano attuale. "
            "Passa a Business o superiore per sbloccarlo.",
        )
    return entitlements


__all__ = [
    "get_db",
    "get_current_supabase_user",
    "get_current_user",
    "CurrentMembership",
    "get_current_membership",
    "require_admin",
    "get_current_entitlements",
    "require_incident_reporting",
    "require_supply_chain",
]
