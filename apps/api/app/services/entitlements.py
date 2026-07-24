"""Limiti per piano (Fase 6, roadmap tecnica §Fase 6 + `NUOVI PIANI.pdf`).

Punto unico di verità sui limiti di ciascun piano: numero di utenti, documenti AI
generabili al mese, misure del Compliance Tracker visibili/editabili, e abilitazione dei
moduli Incident Reporting e Supply Chain. Ogni endpoint che deve applicare un limite lo fa
chiamando `get_entitlements()` invece di ripetere la logica dei piani in più posti.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.subscription import Plan, Subscription, SubscriptionStatus


@dataclass(frozen=True)
class PlanEntitlements:
    plan: Plan
    max_users: int | None  # None = illimitato
    max_ai_documents_per_month: int | None  # None = illimitato, 0 = nessuno consentito
    compliance_measures_limit: (
        int | None
    )  # None = tutte le 15, altrimenti solo le prime N
    compliance_measures_editable: bool
    incident_reporting_enabled: bool
    supply_chain_enabled: bool
    quarterly_reports_enabled: bool
    white_label_enabled: bool
    api_access_enabled: bool


# Le prime 3 misure del catalogo (app/services/compliance_catalog.py) sono quelle
# mostrate in sola lettura al piano Free: valutazione del rischio, MFA, backup — i tre
# controlli fondamentali su cui la Guida al Servizio insiste di più, scelti come "assaggio"
# del Compliance Tracker completo per motivare l'upgrade.
_FREE_COMPLIANCE_MEASURES_LIMIT = 3

PLAN_ENTITLEMENTS: dict[Plan, PlanEntitlements] = {
    Plan.free: PlanEntitlements(
        plan=Plan.free,
        max_users=1,
        max_ai_documents_per_month=0,
        compliance_measures_limit=_FREE_COMPLIANCE_MEASURES_LIMIT,
        compliance_measures_editable=False,
        incident_reporting_enabled=False,
        supply_chain_enabled=False,
        quarterly_reports_enabled=False,
        white_label_enabled=False,
        api_access_enabled=False,
    ),
    Plan.essential: PlanEntitlements(
        plan=Plan.essential,
        max_users=1,
        max_ai_documents_per_month=5,
        compliance_measures_limit=None,
        compliance_measures_editable=True,
        incident_reporting_enabled=True,
        supply_chain_enabled=False,
        quarterly_reports_enabled=False,
        white_label_enabled=False,
        api_access_enabled=False,
    ),
    Plan.business: PlanEntitlements(
        plan=Plan.business,
        max_users=5,
        max_ai_documents_per_month=None,
        compliance_measures_limit=None,
        compliance_measures_editable=True,
        incident_reporting_enabled=True,
        supply_chain_enabled=True,
        quarterly_reports_enabled=True,
        white_label_enabled=False,
        api_access_enabled=False,
    ),
    Plan.enterprise: PlanEntitlements(
        plan=Plan.enterprise,
        max_users=None,
        max_ai_documents_per_month=None,
        compliance_measures_limit=None,
        compliance_measures_editable=True,
        incident_reporting_enabled=True,
        supply_chain_enabled=True,
        quarterly_reports_enabled=True,
        white_label_enabled=True,
        api_access_enabled=True,
    ),
}


def get_or_create_subscription(db: Session, organization_id) -> Subscription:
    """Ogni organizzazione dovrebbe avere una Subscription creata alla registrazione
    (vedi routes/auth.py). Questo fallback esiste solo per dati preesistenti alla Fase 6
    (es. organizzazioni di test/seed create prima che questo modulo esistesse): niente
    errore 500, si crea silenziosamente una riga Free attiva."""
    subscription = (
        db.query(Subscription)
        .filter(Subscription.organization_id == organization_id)
        .first()
    )
    if subscription is None:
        subscription = Subscription(
            organization_id=organization_id,
            plan=Plan.free,
            status=SubscriptionStatus.active,
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
    return subscription


def sync_trial_expiry(db: Session, subscription: Subscription) -> Subscription:
    """Se il trial è scaduto, degrada a Free e persiste subito il cambiamento (downgrade
    "lazy": calcolato al primo utilizzo successivo alla scadenza, senza bisogno di un job
    schedulato — non ancora disponibile prima della Fase 9/infrastruttura). I dati esistenti
    non vengono toccati: passano solo in sola lettura, secondo i limiti del piano Free.
    """
    if (
        subscription.status == SubscriptionStatus.trialing
        and subscription.trial_ends_at is not None
        and datetime.now(timezone.utc) > subscription.trial_ends_at
    ):
        subscription.plan = Plan.free
        subscription.status = SubscriptionStatus.active
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
    return subscription


def get_entitlements(db: Session, organization_id) -> PlanEntitlements:
    subscription = get_or_create_subscription(db, organization_id)
    subscription = sync_trial_expiry(db, subscription)
    return PLAN_ENTITLEMENTS[subscription.plan]
