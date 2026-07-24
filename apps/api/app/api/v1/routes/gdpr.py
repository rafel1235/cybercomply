from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.api.v1.routes.assessments import _to_out as _assessment_to_out
from app.api.v1.routes.compliance import _to_out as _compliance_to_out
from app.api.v1.routes.documents import _to_out as _document_to_out
from app.api.v1.routes.incidents import _to_out as _incident_to_out
from app.api.v1.routes.suppliers import _to_out as _supplier_to_out
from app.models.assessment import AssessmentResult
from app.models.audit_log import AuditLog
from app.models.compliance import ComplianceMeasure
from app.models.document import Document
from app.models.incident import Incident
from app.models.organization import (
    Organization,
    OrganizationMember,
    OrganizationRole,
)
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.audit import AuditLogEntryOut
from app.schemas.gdpr import (
    GdprAccountDeletionOut,
    GdprExportOut,
    GdprOrganizationExportOut,
    GdprUserProfileOut,
)
from app.schemas.organization import MemberOut
from app.services import supabase_admin
from app.services.audit import record_audit_event

router = APIRouter(prefix="/gdpr", tags=["gdpr"])


@router.get("/export", response_model=GdprExportOut)
def export_my_data(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GdprExportOut:
    """Diritto alla portabilità dei dati (GDPR Art. 20, roadmap Fase 8: "Esporta i miei
    dati"): un export completo, in formato strutturato e leggibile da macchina, di tutti i
    dati riconducibili all'utente autenticato — il proprio profilo e, per ciascuna
    organizzazione di cui è membro, tutto ciò che vi è registrato (membri, assessment,
    misure di compliance, documenti, incidenti, fornitori, audit log).

    Riusa le stesse funzioni `_to_out` dei rispettivi router invece di ricostruire la
    serializzazione qui: evita che l'export diverga silenziosamente dal formato mostrato
    nell'app se quei router cambiano in futuro."""
    memberships = (
        db.query(OrganizationMember).filter(OrganizationMember.user_id == user.id).all()
    )

    organizations_out: list[GdprOrganizationExportOut] = []
    for membership in memberships:
        org = db.get(Organization, membership.organization_id)
        if org is None:
            continue

        member_rows = (
            db.query(OrganizationMember, User)
            .join(User, User.id == OrganizationMember.user_id)
            .filter(OrganizationMember.organization_id == org.id)
            .all()
        )
        assessments = (
            db.query(AssessmentResult)
            .filter(AssessmentResult.organization_id == org.id)
            .order_by(AssessmentResult.created_at.desc())
            .all()
        )
        measures = (
            db.query(ComplianceMeasure)
            .filter(ComplianceMeasure.organization_id == org.id)
            .all()
        )
        documents = (
            db.query(Document)
            .filter(Document.organization_id == org.id)
            .order_by(Document.created_at.desc())
            .all()
        )
        incidents = (
            db.query(Incident)
            .filter(Incident.organization_id == org.id)
            .order_by(Incident.opened_at.desc())
            .all()
        )
        suppliers = (
            db.query(Supplier)
            .filter(Supplier.organization_id == org.id)
            .order_by(Supplier.created_at.desc())
            .all()
        )
        audit_entries = (
            db.query(AuditLog)
            .filter(AuditLog.organization_id == org.id)
            .order_by(AuditLog.created_at.desc())
            .all()
        )

        organizations_out.append(
            GdprOrganizationExportOut(
                id=org.id,
                name=org.name,
                vat_number=org.vat_number,
                sector=org.sector,
                employee_count=org.employee_count,
                annual_revenue_eur=(
                    float(org.annual_revenue_eur)
                    if org.annual_revenue_eur is not None
                    else None
                ),
                created_at=org.created_at,
                my_role=membership.role.value,
                members=[
                    MemberOut(
                        user_id=member_user.id,
                        email=member_user.email,
                        full_name=member_user.full_name,
                        role=member.role.value,
                        joined_at=member.joined_at,
                    )
                    for member, member_user in member_rows
                ],
                assessments=[_assessment_to_out(a) for a in assessments],
                compliance_measures=[_compliance_to_out(m) for m in measures],
                documents=[_document_to_out(d) for d in documents],
                incidents=[_incident_to_out(i) for i in incidents],
                suppliers=[_supplier_to_out(s) for s in suppliers],
                audit_log=[AuditLogEntryOut.model_validate(e) for e in audit_entries],
            )
        )

    # L'export stesso è un'azione rilevante da tracciare (non lega l'evento a una singola
    # organizzazione: riguarda l'utente nel suo complesso, potenzialmente più di una).
    record_audit_event(
        db,
        action="gdpr.data_exported",
        user_id=user.id,
        entity="user",
        ip_address=request.client.host if request.client else None,
    )

    return GdprExportOut(
        exported_at=datetime.now(timezone.utc),
        profile=GdprUserProfileOut(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            created_at=user.created_at,
        ),
        organizations=organizations_out,
    )


@router.delete("/account", response_model=GdprAccountDeletionOut)
def delete_my_account(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GdprAccountDeletionOut:
    """Diritto alla cancellazione (GDPR Art. 17, roadmap Fase 8: "Cancella il mio
    account"), eseguito subito e in modo sincrono — ben entro il termine di 30 giorni
    previsto dalla roadmap.

    Per ciascuna organizzazione di cui l'utente è membro:
    - se è l'unico membro, l'intera organizzazione viene cancellata (cascade: membri,
      assessment, misure di compliance, documenti, incidenti, fornitori, abbonamento —
      vedi le relazioni `cascade="all, delete-orphan"` su `Organization`);
    - se ci sono altri membri e l'utente è l'unico admin, l'operazione viene rifiutata:
      va prima promosso un altro membro ad admin (stessa regola già applicata da
      `DELETE /organization/members/{user_id}`, per non lasciare mai un'organizzazione
      senza amministratori);
    - altrimenti viene rimossa solo la sua iscrizione (`OrganizationMember`), l'
      organizzazione e i dati degli altri membri restano intatti.

    Tutte le organizzazioni vengono validate PRIMA di cancellare qualsiasi cosa, così
    un rifiuto su una di esse non lascia l'account a metà cancellato.

    L'audit log delle organizzazioni cancellate non viene perso: `AuditLog.organization_id`
    ha `ondelete="SET NULL"` (Fase 2), quindi i record restano nel registro (conservazione
    minima 12 mesi, Fase 8) ma senza più un riferimento a un'organizzazione che non esiste
    più.

    La cancellazione dell'account Supabase Auth vero e proprio è "best effort" (vedi
    `app/services/supabase_admin.py`): un suo fallimento non impedisce mai la cancellazione
    dello specchio locale, che è l'unica cosa sotto il controllo diretto di questa API.
    """
    memberships = (
        db.query(OrganizationMember).filter(OrganizationMember.user_id == user.id).all()
    )

    # Prima passata: valida senza modificare nulla, per non lasciare cancellazioni parziali
    # se una delle organizzazioni blocca l'operazione.
    for membership in memberships:
        if membership.role != OrganizationRole.admin:
            continue
        other_members_count = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == membership.organization_id,
                OrganizationMember.user_id != user.id,
            )
            .count()
        )
        if other_members_count == 0:
            continue  # unico membro: l'intera organizzazione verrà cancellata, ok
        other_admins_count = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == membership.organization_id,
                OrganizationMember.role == OrganizationRole.admin,
                OrganizationMember.user_id != user.id,
            )
            .count()
        )
        if other_admins_count == 0:
            org = db.get(Organization, membership.organization_id)
            org_name = org.name if org is not None else str(membership.organization_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Non puoi cancellare il tuo account: sei l'unico amministratore di "
                    f"'{org_name}', che ha altri membri. Promuovi prima un altro membro "
                    "ad amministratore, oppure rimuovi gli altri membri se vuoi "
                    "cancellare l'intera organizzazione."
                ),
            )

    # Seconda passata: nessun ostacolo trovato, si procede davvero.
    organizations_deleted: list[str] = []
    organizations_left: list[str] = []
    for membership in memberships:
        org = db.get(Organization, membership.organization_id)
        if org is None:
            continue
        other_members_count = (
            db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == org.id,
                OrganizationMember.user_id != user.id,
            )
            .count()
        )
        if other_members_count == 0:
            organizations_deleted.append(org.name)
            record_audit_event(
                db,
                action="organization.deleted",
                user_id=user.id,
                organization_id=org.id,
                entity="organization",
                details={"reason": "gdpr_account_deletion", "name": org.name},
                ip_address=request.client.host if request.client else None,
            )
            db.delete(org)
        else:
            organizations_left.append(org.name)
            record_audit_event(
                db,
                action="organization.member_removed",
                user_id=user.id,
                organization_id=org.id,
                entity="organization_member",
                details={
                    "reason": "gdpr_account_deletion",
                    "removed_user_id": str(user.id),
                },
                ip_address=request.client.host if request.client else None,
            )
            db.delete(membership)
    db.commit()

    record_audit_event(
        db,
        action="gdpr.account_deleted",
        user_id=user.id,
        entity="user",
        details={"email": user.email},
        ip_address=request.client.host if request.client else None,
    )

    auth_account_deleted = supabase_admin.delete_auth_user(str(user.id))

    db.delete(user)
    db.commit()

    return GdprAccountDeletionOut(
        deleted_at=datetime.now(timezone.utc),
        organizations_deleted=organizations_deleted,
        organizations_left=organizations_left,
        auth_account_deleted=auth_account_deleted,
    )
