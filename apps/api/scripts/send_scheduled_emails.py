"""Alert email periodici (Fase 7 — roadmap tecnica): trial in scadenza, scadenze
normative NIS2/CRA in avvicinamento, incidente aperto senza notifica 24h, fornitore con
questionario fermo da 6+ mesi, report mensile di conformità.

Non esiste ancora un vero scheduler (arriva in Fase 9 — infrastruttura e deploy): questo
script è pensato per essere eseguito manualmente per ora, e collegato a un vero cron
(una volta al giorno) quando l'infrastruttura sarà pronta. Ogni funzione è idempotente —
usa l'audit log come marcatore "già inviato" (un'action dedicata per tipo di alert, con
l'identificativo rilevante incorporato dove serve) — così eseguire lo script più volte lo
stesso giorno non manda email duplicate.

Uso:
    python -m scripts.send_scheduled_emails
"""

import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.api.v1.routes.compliance import _compute_score, _ensure_catalog_provisioned
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.audit_log import AuditLog
from app.models.incident import Incident, IncidentStatus, NotificationPhase
from app.models.organization import Organization, OrganizationMember, OrganizationRole
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.supplier import Supplier
from app.models.user import User
from app.services import email_service
from app.services.audit import record_audit_event
from app.services.email_templates import (
    incident_overdue_email,
    monthly_report_email,
    nis2_deadline_email,
    supplier_stale_email,
    trial_ending_email,
    trial_expired_email,
)
from app.services.entitlements import sync_trial_expiry
from app.services.incident_deadlines import compute_deadlines

# Stesse scadenze mostrate nella dashboard frontend
# (apps/web/app/(dashboard)/dashboard/page.tsx, REGULATORY_DEADLINES): non esiste oggi
# un'unica fonte condivisa tra frontend e backend per questo dato statico, va tenuta in
# sincronia manualmente se le date cambiano. L'"id" è solo la chiave di idempotenza
# dell'alert (vedi _already_sent), non è mostrato all'utente.
_REGULATORY_DEADLINES = [
    {
        "id": "cra_notifica_incidenti",
        "date": "2026-09-11",
        "label": "CRA: notifica vulnerabilità sfruttate e incidenti gravi (24h/72h)",
    },
    {
        "id": "nis2_adozione_misure",
        "date": "2026-10-01",
        "label": "NIS2: adozione misure tecniche e organizzative",
    },
    {
        "id": "nis2_nomina_responsabile",
        "date": "2026-10-01",
        "label": "NIS2: nomina responsabile e notifica ad ACN",
    },
    {
        "id": "cra_punto_contatto",
        "date": "2026-12-11",
        "label": "CRA: punto di contatto per segnalazione vulnerabilità",
    },
    {
        "id": "nis2_ispezioni",
        "date": "2026-12-31",
        "label": "NIS2: avvio ispezioni e verifiche sistematiche ACN",
    },
    {
        "id": "cra_piena_applicazione",
        "date": "2027-12-11",
        "label": "CRA: piena applicazione, marcatura CE obbligatoria",
    },
]
_NIS2_ALERT_WINDOWS_DAYS = (60, 30)
_SUPPLIER_STALE_THRESHOLD_DAYS = 180
_INCIDENT_PRE_WARNING_HOURS = 20


def _already_sent(db: Session, organization_id, action: str) -> bool:
    return (
        db.query(AuditLog)
        .filter(AuditLog.organization_id == organization_id, AuditLog.action == action)
        .first()
        is not None
    )


def _admin_emails(db: Session, organization_id) -> list[str]:
    rows = (
        db.query(User.email)
        .join(OrganizationMember, OrganizationMember.user_id == User.id)
        .filter(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.role == OrganizationRole.admin,
        )
        .all()
    )
    return [row[0] for row in rows]


def _notify_admins(db: Session, organization_id, subject: str, html: str) -> int:
    """Ritorna il numero di admin a cui si è tentato di inviare l'email (non garanzia di
    consegna: send_email non solleva mai eccezioni e ritorna False se Resend non è
    configurato o la chiamata fallisce — vedi email_service.py). Un tentativo con almeno
    un admin trovato è sufficiente per marcare l'alert come "già gestito", altrimenti si
    ritenta al prossimo giro (organizzazione senza admin registrato)."""
    emails = _admin_emails(db, organization_id)
    for address in emails:
        email_service.send_email(to=address, subject=subject, html=html)
    return len(emails)


def send_trial_ending_reminders(db: Session, *, now: datetime | None = None) -> int:
    """7 giorni e 1 giorno prima della scadenza del trial Essential (roadmap Fase 6/7)."""
    now = now or datetime.now(timezone.utc)
    settings = get_settings()
    sent = 0

    subscriptions = (
        db.query(Subscription)
        .filter(Subscription.status == SubscriptionStatus.trialing)
        .all()
    )
    for subscription in subscriptions:
        if subscription.trial_ends_at is None:
            continue
        days_left = (subscription.trial_ends_at - now).days
        if days_left not in (7, 1):
            continue

        action = f"email.trial_ending_{days_left}d"
        if _already_sent(db, subscription.organization_id, action):
            continue

        organization = db.get(Organization, subscription.organization_id)
        subject, html = trial_ending_email(
            organization_name=organization.name if organization else "",
            days_left=days_left,
            billing_url=f"{settings.frontend_base_url}/settings/billing",
        )
        if _notify_admins(db, subscription.organization_id, subject, html):
            record_audit_event(
                db,
                action=action,
                organization_id=subscription.organization_id,
                entity="subscription",
            )
            sent += 1
    return sent


def send_trial_expired_notices(db: Session, *, now: datetime | None = None) -> int:
    """Il downgrade a Free è normalmente "lazy" (Fase 6: calcolato alla richiesta
    successiva), ma un'organizzazione che smette di usare la piattaforma dopo la
    scadenza del trial non farebbe più nessuna richiesta e non verrebbe mai degradata né
    avvisata. Questo alert forza il controllo per ogni trial scaduto: applica comunque il
    downgrade (idempotente, `sync_trial_expiry` non fa nulla se già a Free) e invia
    l'email solo la prima volta."""
    now = now or datetime.now(timezone.utc)
    settings = get_settings()
    sent = 0

    subscriptions = (
        db.query(Subscription)
        .filter(
            Subscription.status == SubscriptionStatus.trialing,
            Subscription.trial_ends_at <= now,
        )
        .all()
    )
    for subscription in subscriptions:
        action = "email.trial_expired"
        already = _already_sent(db, subscription.organization_id, action)
        sync_trial_expiry(db, subscription)
        if already:
            continue

        organization = db.get(Organization, subscription.organization_id)
        subject, html = trial_expired_email(
            organization_name=organization.name if organization else "",
            billing_url=f"{settings.frontend_base_url}/settings/billing",
        )
        if _notify_admins(db, subscription.organization_id, subject, html):
            record_audit_event(
                db,
                action=action,
                organization_id=subscription.organization_id,
                entity="subscription",
            )
            sent += 1
    return sent


def send_nis2_deadline_reminders(db: Session, *, now: datetime | None = None) -> int:
    """60 e 30 giorni prima di ciascuna scadenza normativa NIS2/CRA, per ogni
    organizzazione registrata (le scadenze sono le stesse per tutti, non dipendono dai
    dati dell'organizzazione)."""
    now = now or datetime.now(timezone.utc)
    settings = get_settings()
    sent = 0
    organizations = db.query(Organization).all()

    for deadline in _REGULATORY_DEADLINES:
        deadline_date = datetime.strptime(deadline["date"], "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
        days_left = (deadline_date - now).days
        if days_left not in _NIS2_ALERT_WINDOWS_DAYS:
            continue

        action = f"email.nis2_deadline_{days_left}d:{deadline['id']}"
        for organization in organizations:
            if _already_sent(db, organization.id, action):
                continue
            subject, html = nis2_deadline_email(
                organization_name=organization.name,
                deadline_label=deadline["label"],
                deadline_date=deadline_date.strftime("%d/%m/%Y"),
                days_left=days_left,
                dashboard_url=f"{settings.frontend_base_url}/dashboard/compliance",
            )
            if _notify_admins(db, organization.id, subject, html):
                record_audit_event(
                    db,
                    action=action,
                    organization_id=organization.id,
                    entity="regulatory_deadline",
                )
                sent += 1
    return sent


def send_incident_overdue_alerts(db: Session, *, now: datetime | None = None) -> int:
    """Incidente aperto da più di 20 ore senza che la notifica 24h (NIS2 Art. 23 /
    CRA-ENISA) risulti ancora registrata come inviata."""
    now = now or datetime.now(timezone.utc)
    settings = get_settings()
    sent = 0

    incidents = (
        db.query(Incident).filter(Incident.status != IncidentStatus.chiuso).all()
    )
    for incident in incidents:
        hours_open = (now - incident.opened_at).total_seconds() / 3600
        if hours_open < _INCIDENT_PRE_WARNING_HOURS:
            continue

        deadlines = compute_deadlines(
            incident.opened_at, incident.notifications, now=now
        )
        early_warning = next(
            (d for d in deadlines if d.phase == NotificationPhase.early_warning_24h),
            None,
        )
        if early_warning is None or early_warning.sent:
            continue

        action = f"email.incident_overdue:{incident.id}"
        if _already_sent(db, incident.organization_id, action):
            continue

        organization = db.get(Organization, incident.organization_id)
        subject, html = incident_overdue_email(
            organization_name=organization.name if organization else "",
            reference_code=incident.reference_code,
            incident_url=f"{settings.frontend_base_url}/dashboard/incidents/{incident.id}",
        )
        if _notify_admins(db, incident.organization_id, subject, html):
            record_audit_event(
                db,
                action=action,
                organization_id=incident.organization_id,
                entity="incident",
                details={"incident_id": str(incident.id)},
            )
            sent += 1
    return sent


def send_supplier_stale_alerts(db: Session, *, now: datetime | None = None) -> int:
    """Fornitore mai valutato o non rivalutato da 6+ mesi. Ri-avvisa una volta al mese
    finché resta fermo (marcatore di idempotenza per mese, non "per sempre"), a
    differenza degli altri alert one-shot di questo script."""
    now = now or datetime.now(timezone.utc)
    settings = get_settings()
    sent = 0
    threshold = now - timedelta(days=_SUPPLIER_STALE_THRESHOLD_DAYS)
    month_key = now.strftime("%Y-%m")

    suppliers = db.query(Supplier).all()
    for supplier in suppliers:
        reference_date = supplier.last_reviewed_at or supplier.created_at
        if reference_date is None or reference_date > threshold:
            continue

        action = f"email.supplier_stale:{supplier.id}:{month_key}"
        if _already_sent(db, supplier.organization_id, action):
            continue

        organization = db.get(Organization, supplier.organization_id)
        subject, html = supplier_stale_email(
            organization_name=organization.name if organization else "",
            supplier_name=supplier.name,
            supplier_url=f"{settings.frontend_base_url}/dashboard/suppliers",
        )
        if _notify_admins(db, supplier.organization_id, subject, html):
            record_audit_event(
                db,
                action=action,
                organization_id=supplier.organization_id,
                entity="supplier",
                details={"supplier_id": str(supplier.id)},
            )
            sent += 1
    return sent


def send_monthly_compliance_reports(db: Session, *, now: datetime | None = None) -> int:
    """Un report al mese per organizzazione, con lo stesso calcolo dello score usato da
    `GET /compliance/score` (riusato direttamente, non riscritto, per non rischiare che i
    due finiscano per divergere)."""
    now = now or datetime.now(timezone.utc)
    settings = get_settings()
    sent = 0
    month_key = now.strftime("%Y-%m")

    organizations = db.query(Organization).all()
    for organization in organizations:
        action = f"email.monthly_report:{month_key}"
        if _already_sent(db, organization.id, action):
            continue

        measures = _ensure_catalog_provisioned(db, organization.id)
        score = _compute_score(measures)
        subject, html = monthly_report_email(
            organization_name=organization.name,
            score_percent=score.score_percent,
            measures_conformi=score.measures_conformi,
            measures_total=score.measures_total,
            dashboard_url=f"{settings.frontend_base_url}/dashboard/compliance",
        )
        if _notify_admins(db, organization.id, subject, html):
            record_audit_event(
                db,
                action=action,
                organization_id=organization.id,
                entity="compliance_score",
            )
            sent += 1
    return sent


def run_all(db: Session, *, now: datetime | None = None) -> dict[str, int]:
    return {
        "trial_ending": send_trial_ending_reminders(db, now=now),
        "trial_expired": send_trial_expired_notices(db, now=now),
        "nis2_deadlines": send_nis2_deadline_reminders(db, now=now),
        "incident_overdue": send_incident_overdue_alerts(db, now=now),
        "supplier_stale": send_supplier_stale_alerts(db, now=now),
        "monthly_report": send_monthly_compliance_reports(db, now=now),
    }


def main() -> None:
    db = SessionLocal()
    try:
        results = run_all(db)
        total = sum(results.values())
        print(f"Alert inviati: {total} — dettaglio: {results}")
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
