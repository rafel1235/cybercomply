import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import (
    CurrentMembership,
    get_current_entitlements,
    get_current_membership,
    get_db,
    require_admin,
)
from app.core.config import get_settings
from app.models.organization import (
    OrganizationInvite,
    OrganizationMember,
    OrganizationRole,
)
from app.models.user import User
from app.schemas.organization import (
    InviteMemberRequest,
    InviteMemberResponse,
    MemberOut,
    OrganizationOut,
    OrganizationUpdateRequest,
)
from app.services import email_service
from app.services.audit import record_audit_event
from app.services.email_templates import invite_email
from app.services.entitlements import PlanEntitlements

router = APIRouter(prefix="/organization", tags=["organization"])

_ROLE_LABELS = {"admin": "Amministratore", "viewer": "Viewer"}


@router.get("", response_model=OrganizationOut)
def get_organization(
    membership: CurrentMembership = Depends(get_current_membership),
) -> OrganizationOut:
    return OrganizationOut.model_validate(membership.organization)


@router.put("", response_model=OrganizationOut)
def update_organization(
    payload: OrganizationUpdateRequest,
    request: Request,
    membership: CurrentMembership = Depends(require_admin),
    db: Session = Depends(get_db),
) -> OrganizationOut:
    org = membership.organization
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(org, field, value)
    db.add(org)
    db.commit()
    db.refresh(org)

    record_audit_event(
        db,
        action="organization.updated",
        user_id=membership.user.id,
        organization_id=org.id,
        entity="organization",
        details={"fields": list(updates.keys())},
        ip_address=request.client.host if request.client else None,
    )
    return OrganizationOut.model_validate(org)


@router.get("/members", response_model=list[MemberOut])
def list_members(
    membership: CurrentMembership = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> list[MemberOut]:
    rows = (
        db.query(OrganizationMember, User)
        .join(User, User.id == OrganizationMember.user_id)
        .filter(OrganizationMember.organization_id == membership.organization.id)
        .order_by(OrganizationMember.joined_at.asc())
        .all()
    )
    return [
        MemberOut(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=member.role.value,
            joined_at=member.joined_at,
        )
        for member, user in rows
    ]


@router.delete("/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    user_id: str,
    request: Request,
    membership: CurrentMembership = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    target = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.organization_id == membership.organization.id,
            OrganizationMember.user_id == user_id,
        )
        .first()
    )
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Membro non trovato"
        )

    if target.role == OrganizationRole.admin:
        remaining_admins = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == membership.organization.id,
                OrganizationMember.role == OrganizationRole.admin,
                OrganizationMember.user_id != user_id,
            )
            .count()
        )
        if remaining_admins == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Non puoi rimuovere l'unico amministratore rimasto: "
                "promuovi prima un altro membro ad admin",
            )

    db.delete(target)
    db.commit()

    record_audit_event(
        db,
        action="organization.member_removed",
        user_id=membership.user.id,
        organization_id=membership.organization.id,
        entity="organization_member",
        details={"removed_user_id": str(user_id)},
        ip_address=request.client.host if request.client else None,
    )


@router.post("/invites", response_model=InviteMemberResponse)
def invite_member(
    payload: InviteMemberRequest,
    request: Request,
    membership: CurrentMembership = Depends(require_admin),
    entitlements: PlanEntitlements = Depends(get_current_entitlements),
    db: Session = Depends(get_db),
) -> InviteMemberResponse:
    """Crea un invito per un collaboratore. L'invio effettivo dell'email arriva in Fase 7
    (provider email transazionale); per ora l'invito viene creato e loggato, pronto per
    essere collegato all'invio reale.

    Fase 6: il numero massimo di posti (membri già presenti + inviti non ancora scaduti,
    per non far bastare crearne molti in attesa per aggirare il limite) dipende dal piano.
    """
    if entitlements.max_users is not None:
        current_members = (
            db.query(OrganizationMember)
            .filter(OrganizationMember.organization_id == membership.organization.id)
            .count()
        )
        pending_invites = (
            db.query(OrganizationInvite)
            .filter(
                OrganizationInvite.organization_id == membership.organization.id,
                OrganizationInvite.accepted_at.is_(None),
                OrganizationInvite.expires_at > datetime.now(timezone.utc),
            )
            .count()
        )
        if current_members + pending_invites >= entitlements.max_users:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Il tuo piano attuale consente al massimo {entitlements.max_users} "
                    "utenti (membri + inviti in attesa). Passa a un piano superiore per "
                    "invitare altri collaboratori."
                ),
            )

    role = (
        OrganizationRole(payload.role)
        if payload.role in OrganizationRole._value2member_map_
        else OrganizationRole.viewer
    )
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    invite = OrganizationInvite(
        organization_id=membership.organization.id,
        invited_email=payload.email,
        role=role,
        invited_by=membership.user.id,
        token=token,
        expires_at=expires_at,
    )
    db.add(invite)
    db.commit()

    record_audit_event(
        db,
        action="organization.member_invited",
        user_id=membership.user.id,
        organization_id=membership.organization.id,
        entity="organization_invite",
        details={"invited_email": payload.email, "role": role.value},
        ip_address=request.client.host if request.client else None,
    )

    # Fase 7: invio dell'email di invito. Un problema di invio non deve mai far fallire
    # l'invito stesso (send_email non solleva mai eccezioni): l'invito resta comunque
    # creato e valido, consultabile/rigenerabile dall'admin anche se l'email non arriva.
    settings = get_settings()
    subject, html = invite_email(
        organization_name=membership.organization.name,
        inviter_name=membership.user.full_name or membership.user.email,
        role_label=_ROLE_LABELS.get(role.value, role.value),
        accept_url=f"{settings.frontend_base_url}/register?invite={token}",
    )
    email_service.send_email(to=payload.email, subject=subject, html=html)

    return InviteMemberResponse(
        invited_email=payload.email, invite_token=token, expires_at=expires_at
    )
