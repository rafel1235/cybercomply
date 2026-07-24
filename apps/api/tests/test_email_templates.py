"""Test dei template email (Fase 7): funzioni pure, nessuna configurazione o rete
necessaria. Verificano solo che ogni template produca un subject non vuoto e un HTML che
contenga i dati passati e il link di call-to-action, non lo stile esatto."""

from app.services import email_templates as t


def test_welcome_email_contains_org_and_cta():
    subject, html = t.welcome_email(
        organization_name="Acme Srl",
        trial_days=14,
        dashboard_url="https://app/dashboard",
    )
    assert "Acme Srl" in subject or "Acme Srl" in html
    assert "14" in html
    assert "https://app/dashboard" in html


def test_invite_email_contains_inviter_and_role():
    subject, html = t.invite_email(
        organization_name="Acme Srl",
        inviter_name="Mario Rossi",
        role_label="Viewer",
        accept_url="https://app/register?invite=tok123",
    )
    assert "Mario Rossi" in subject
    assert "Acme Srl" in html
    assert "Viewer" in html
    assert "tok123" in html


def test_payment_succeeded_email_includes_invoice_link_when_present():
    _subject, html = t.payment_succeeded_email(
        organization_name="Acme Srl",
        plan_label="Business",
        invoice_url="https://stripe.example/invoice/123",
        billing_url="https://app/settings/billing",
    )
    assert "https://stripe.example/invoice/123" in html
    assert "Business" in html


def test_payment_succeeded_email_omits_invoice_link_when_absent():
    _subject, html = t.payment_succeeded_email(
        organization_name="Acme Srl",
        plan_label="Business",
        invoice_url=None,
        billing_url="https://app/billing",
    )
    assert "Scarica la fattura" not in html


def test_payment_failed_email_mentions_plan_and_cta():
    subject, html = t.payment_failed_email(
        organization_name="Acme Srl",
        plan_label="Essential",
        billing_url="https://app/billing",
    )
    assert "non riuscito" in subject.lower()
    assert "Essential" in html
    assert "https://app/billing" in html


def test_subscription_canceled_email_reassures_about_data():
    _subject, html = t.subscription_canceled_email(
        organization_name="Acme Srl", billing_url="https://app/billing"
    )
    assert "nessun dato" in html.lower() or "non è stato cancellato" in html.lower()


def test_trial_ending_email_singular_for_one_day():
    subject, html = t.trial_ending_email(
        organization_name="Acme Srl", days_left=1, billing_url="https://app/billing"
    )
    assert "domani" in subject
    assert "domani" in html


def test_trial_ending_email_plural_for_multiple_days():
    subject, _html = t.trial_ending_email(
        organization_name="Acme Srl", days_left=7, billing_url="https://app/billing"
    )
    assert "7 giorni" in subject


def test_trial_expired_email_explains_free_plan_limits():
    _subject, html = t.trial_expired_email(
        organization_name="Acme Srl", billing_url="https://app/billing"
    )
    assert "Free" in html


def test_nis2_deadline_email_contains_deadline_details():
    subject, html = t.nis2_deadline_email(
        organization_name="Acme Srl",
        deadline_label="Adozione misure NIS2",
        deadline_date="1 ottobre 2026",
        days_left=30,
        dashboard_url="https://app/dashboard/compliance",
    )
    assert "30" in subject
    assert "Adozione misure NIS2" in html
    assert "1 ottobre 2026" in html


def test_incident_overdue_email_contains_reference_code():
    subject, html = t.incident_overdue_email(
        organization_name="Acme Srl",
        reference_code="INC-2026-003",
        incident_url="https://app/dashboard/incidents/abc",
    )
    assert "INC-2026-003" in subject
    assert "https://app/dashboard/incidents/abc" in html


def test_supplier_stale_email_contains_supplier_name():
    subject, html = t.supplier_stale_email(
        organization_name="Acme Srl",
        supplier_name="Hosting Provider Srl",
        supplier_url="https://app/dashboard/suppliers",
    )
    assert "Hosting Provider Srl" in subject
    assert "Hosting Provider Srl" in html


def test_monthly_report_email_contains_score():
    subject, html = t.monthly_report_email(
        organization_name="Acme Srl",
        score_percent=73.4,
        measures_conformi=11,
        measures_total=15,
        dashboard_url="https://app/dashboard/compliance",
    )
    assert "Acme Srl" in subject
    assert "73%" in html
    assert "11 misure conformi su 15" in html
