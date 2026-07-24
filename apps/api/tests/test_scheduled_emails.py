"""Test dello script di alert schedulati (Fase 7): niente rete reale (`email_service.
send_email` sempre mockato), e verifica esplicita dell'idempotenza — ogni funzione deve
inviare l'alert una sola volta anche se lo script viene eseguito più volte di seguito con
lo stesso stato del database, così collegarlo a un vero cron in Fase 9 non rischia di
spammare gli utenti."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models.compliance import ComplianceMeasure, MeasureStatus
from app.models.incident import (
    Incident,
    IncidentNotification,
    IncidentStatus,
    NotificationPhase,
)
from app.models.organization import Organization, OrganizationMember, OrganizationRole
from app.models.subscription import Plan, Subscription, SubscriptionStatus
from app.models.supplier import Supplier, SupplierCriticality, SupplierStatus
from app.models.user import User
from app.services import email_service
from scripts import send_scheduled_emails as script


def _make_org_with_admin(db_session, name: str, admin_email: str) -> Organization:
    org = Organization(id=uuid.uuid4(), name=name)
    db_session.add(org)
    db_session.commit()

    user = User(id=uuid.uuid4(), email=admin_email)
    db_session.add(user)
    db_session.commit()
    db_session.add(
        OrganizationMember(
            user_id=user.id, organization_id=org.id, role=OrganizationRole.admin
        )
    )
    db_session.commit()
    return org


@pytest.fixture(autouse=True)
def _capture_emails(monkeypatch):
    """Cattura tutte le email "inviate" in una lista condivisa, invece di chiamare
    davvero Resend, in tutti i test di questo file."""
    sent = []
    monkeypatch.setattr(
        email_service,
        "send_email",
        lambda **kwargs: sent.append(kwargs) or True,
    )
    return sent


def test_trial_ending_reminder_sent_at_7_and_1_days(db_session, _capture_emails):
    now = datetime.now(timezone.utc)
    org7 = _make_org_with_admin(
        db_session, "Org Trial 7gg Srl", "admin7@cybercomplyit.it"
    )
    db_session.add(
        Subscription(
            organization_id=org7.id,
            plan=Plan.essential,
            status=SubscriptionStatus.trialing,
            trial_ends_at=now + timedelta(days=7),
        )
    )
    org1 = _make_org_with_admin(
        db_session, "Org Trial 1gg Srl", "admin1@cybercomplyit.it"
    )
    db_session.add(
        Subscription(
            organization_id=org1.id,
            plan=Plan.essential,
            status=SubscriptionStatus.trialing,
            trial_ends_at=now + timedelta(days=1),
        )
    )
    org_far = _make_org_with_admin(
        db_session, "Org Trial Lontano Srl", "adminfar@cybercomplyit.it"
    )
    db_session.add(
        Subscription(
            organization_id=org_far.id,
            plan=Plan.essential,
            status=SubscriptionStatus.trialing,
            trial_ends_at=now + timedelta(days=13),
        )
    )
    db_session.commit()

    sent_count = script.send_trial_ending_reminders(db_session, now=now)

    assert sent_count == 2
    recipients = {e["to"] for e in _capture_emails}
    assert recipients == {"admin7@cybercomplyit.it", "admin1@cybercomplyit.it"}


def test_trial_ending_reminder_is_idempotent(db_session, _capture_emails):
    now = datetime.now(timezone.utc)
    org = _make_org_with_admin(
        db_session, "Org Trial Idempotente Srl", "admin-idem@cybercomplyit.it"
    )
    db_session.add(
        Subscription(
            organization_id=org.id,
            plan=Plan.essential,
            status=SubscriptionStatus.trialing,
            trial_ends_at=now + timedelta(days=7),
        )
    )
    db_session.commit()

    first = script.send_trial_ending_reminders(db_session, now=now)
    second = script.send_trial_ending_reminders(db_session, now=now)

    assert first == 1
    assert second == 0
    assert len(_capture_emails) == 1


def test_trial_expired_notice_downgrades_and_emails_once(db_session, _capture_emails):
    now = datetime.now(timezone.utc)
    org = _make_org_with_admin(
        db_session, "Org Trial Scaduto Srl", "admin-exp@cybercomplyit.it"
    )
    subscription = Subscription(
        organization_id=org.id,
        plan=Plan.essential,
        status=SubscriptionStatus.trialing,
        trial_ends_at=now - timedelta(days=1),
    )
    db_session.add(subscription)
    db_session.commit()

    first = script.send_trial_expired_notices(db_session, now=now)
    db_session.refresh(subscription)
    assert first == 1
    assert subscription.plan == Plan.free
    assert subscription.status == SubscriptionStatus.active
    assert len(_capture_emails) == 1

    second = script.send_trial_expired_notices(db_session, now=now)
    assert second == 0
    assert len(_capture_emails) == 1


def test_nis2_deadline_reminder_sent_30_days_before(db_session, _capture_emails):
    # "cra_notifica_incidenti" (2026-09-11) è l'unica scadenza con questa data: a
    # differenza di "nis2_adozione_misure"/"nis2_nomina_responsabile" (entrambe il
    # 2026-10-01, quindi generano 2 email quel giorno), qui ne basta una per verificare
    # il comportamento base.
    deadline = next(
        d for d in script._REGULATORY_DEADLINES if d["id"] == "cra_notifica_incidenti"
    )
    deadline_date = datetime.strptime(deadline["date"], "%Y-%m-%d").replace(
        tzinfo=timezone.utc
    )
    now = deadline_date - timedelta(days=30)

    _make_org_with_admin(
        db_session, "Org NIS2 Deadline Srl", "admin-nis2@cybercomplyit.it"
    )
    db_session.commit()

    first = script.send_nis2_deadline_reminders(db_session, now=now)
    assert first == 1
    assert _capture_emails[0]["to"] == "admin-nis2@cybercomplyit.it"
    assert deadline["label"] in _capture_emails[0]["html"]

    second = script.send_nis2_deadline_reminders(db_session, now=now)
    assert second == 0
    assert len(_capture_emails) == 1


def test_nis2_deadline_reminder_sends_one_email_per_obligation_on_shared_date(
    db_session, _capture_emails
):
    """ "nis2_adozione_misure" e "nis2_nomina_responsabile" cadono entrambe il 2026-10-01:
    sono due obblighi distinti, quindi devono generare due email separate (una per
    obligation, non una sola per data)."""
    deadline = next(
        d for d in script._REGULATORY_DEADLINES if d["id"] == "nis2_adozione_misure"
    )
    deadline_date = datetime.strptime(deadline["date"], "%Y-%m-%d").replace(
        tzinfo=timezone.utc
    )
    now = deadline_date - timedelta(days=30)

    _make_org_with_admin(
        db_session, "Org NIS2 Doppia Scadenza Srl", "admin-nis2c@cybercomplyit.it"
    )

    sent = script.send_nis2_deadline_reminders(db_session, now=now)
    assert sent == 2


def test_nis2_deadline_reminder_not_sent_outside_windows(db_session, _capture_emails):
    deadline = next(
        d for d in script._REGULATORY_DEADLINES if d["id"] == "nis2_adozione_misure"
    )
    deadline_date = datetime.strptime(deadline["date"], "%Y-%m-%d").replace(
        tzinfo=timezone.utc
    )
    now = deadline_date - timedelta(days=45)

    _make_org_with_admin(
        db_session, "Org NIS2 Fuori Finestra Srl", "admin-nis2b@cybercomplyit.it"
    )

    sent = script.send_nis2_deadline_reminders(db_session, now=now)
    assert sent == 0
    assert len(_capture_emails) == 0


def test_incident_overdue_alert_sent_after_20_hours_without_notification(
    db_session, _capture_emails
):
    now = datetime.now(timezone.utc)
    org = _make_org_with_admin(
        db_session, "Org Incident Overdue Srl", "admin-inc@cybercomplyit.it"
    )
    incident = Incident(
        organization_id=org.id,
        reference_code="INC-TEST-001",
        incident_type="ransomware",
        status=IncidentStatus.aperto,
        opened_at=now - timedelta(hours=21),
    )
    db_session.add(incident)
    db_session.commit()

    sent = script.send_incident_overdue_alerts(db_session, now=now)
    assert sent == 1
    assert _capture_emails[0]["to"] == "admin-inc@cybercomplyit.it"
    assert "INC-TEST-001" in _capture_emails[0]["subject"]

    # Idempotente: una seconda esecuzione non deve reinviare.
    sent_again = script.send_incident_overdue_alerts(db_session, now=now)
    assert sent_again == 0
    assert len(_capture_emails) == 1


def test_incident_overdue_alert_skipped_if_notification_already_sent(
    db_session, _capture_emails
):
    now = datetime.now(timezone.utc)
    org = _make_org_with_admin(
        db_session, "Org Incident Notificato Srl", "admin-inc2@cybercomplyit.it"
    )
    incident = Incident(
        organization_id=org.id,
        reference_code="INC-TEST-002",
        incident_type="data breach",
        status=IncidentStatus.aperto,
        opened_at=now - timedelta(hours=21),
    )
    db_session.add(incident)
    db_session.commit()
    db_session.add(
        IncidentNotification(
            incident_id=incident.id,
            phase=NotificationPhase.early_warning_24h,
            recipient="csirt@acn.gov.it",
        )
    )
    db_session.commit()

    sent = script.send_incident_overdue_alerts(db_session, now=now)
    assert sent == 0
    assert len(_capture_emails) == 0


def test_incident_overdue_alert_skipped_for_closed_incident(
    db_session, _capture_emails
):
    now = datetime.now(timezone.utc)
    org = _make_org_with_admin(
        db_session, "Org Incident Chiuso Srl", "admin-inc3@cybercomplyit.it"
    )
    incident = Incident(
        organization_id=org.id,
        reference_code="INC-TEST-003",
        incident_type="phishing",
        status=IncidentStatus.chiuso,
        opened_at=now - timedelta(hours=30),
        closed_at=now - timedelta(hours=1),
    )
    db_session.add(incident)
    db_session.commit()

    sent = script.send_incident_overdue_alerts(db_session, now=now)
    assert sent == 0
    assert len(_capture_emails) == 0


def test_supplier_stale_alert_sent_for_never_reviewed_supplier(
    db_session, _capture_emails
):
    now = datetime.now(timezone.utc)
    org = _make_org_with_admin(
        db_session, "Org Supplier Mai Valutato Srl", "admin-sup@cybercomplyit.it"
    )
    supplier = Supplier(
        organization_id=org.id,
        name="Hosting Provider Srl",
        criticality=SupplierCriticality.alta,
        status=SupplierStatus.non_valutato,
    )
    db_session.add(supplier)
    db_session.commit()
    # created_at è impostato dal default del DB (server_default=func.now()): per
    # simulare un fornitore creato mesi fa, lo si aggiorna esplicitamente dopo l'insert.
    supplier.created_at = now - timedelta(days=200)
    db_session.commit()

    sent = script.send_supplier_stale_alerts(db_session, now=now)
    assert sent == 1
    assert "Hosting Provider Srl" in _capture_emails[0]["subject"]

    sent_again = script.send_supplier_stale_alerts(db_session, now=now)
    assert sent_again == 0
    assert len(_capture_emails) == 1


def test_supplier_stale_alert_not_sent_for_recently_reviewed_supplier(
    db_session, _capture_emails
):
    now = datetime.now(timezone.utc)
    org = _make_org_with_admin(
        db_session, "Org Supplier Recente Srl", "admin-sup2@cybercomplyit.it"
    )
    supplier = Supplier(
        organization_id=org.id,
        name="Fornitore Recente Srl",
        criticality=SupplierCriticality.media,
        status=SupplierStatus.conforme,
        last_reviewed_at=now - timedelta(days=10),
    )
    db_session.add(supplier)
    db_session.commit()

    sent = script.send_supplier_stale_alerts(db_session, now=now)
    assert sent == 0
    assert len(_capture_emails) == 0


def test_monthly_compliance_report_sent_once_per_month(db_session, _capture_emails):
    now = datetime.now(timezone.utc)
    org = _make_org_with_admin(
        db_session, "Org Report Mensile Srl", "admin-report@cybercomplyit.it"
    )
    db_session.add(
        ComplianceMeasure(
            organization_id=org.id,
            measure_id="mfa_accessi_remoti",
            status=MeasureStatus.conforme,
        )
    )
    db_session.commit()

    first = script.send_monthly_compliance_reports(db_session, now=now)
    assert first == 1
    assert _capture_emails[0]["to"] == "admin-report@cybercomplyit.it"

    second = script.send_monthly_compliance_reports(db_session, now=now)
    assert second == 0
    assert len(_capture_emails) == 1


def test_run_all_aggregates_every_alert_type(db_session, monkeypatch):
    function_names = (
        "send_trial_ending_reminders",
        "send_trial_expired_notices",
        "send_nis2_deadline_reminders",
        "send_incident_overdue_alerts",
        "send_supplier_stale_alerts",
        "send_monthly_compliance_reports",
    )
    calls = []
    for name in function_names:
        monkeypatch.setattr(
            script, name, lambda db, now=None, _n=name: calls.append(_n) or 1
        )

    results = script.run_all(db_session)

    # run_all espone chiavi brevi e leggibili ("trial_ending", non il nome della
    # funzione): qui si verifica solo che ogni funzione sia stata chiamata esattamente
    # una volta e che il totale rifletta i valori di ritorno mockati (1 ciascuna).
    assert sorted(calls) == sorted(function_names)
    assert sum(results.values()) == 6
    assert len(results) == 6
