"""Test del servizio entitlements (Fase 6): limiti per piano e downgrade automatico a
Free quando il trial scade. Nessuna chiamata HTTP: test diretti sulla sessione DB, più
veloci e mirati di un giro completo per l'API."""

import uuid
from datetime import datetime, timedelta, timezone

from app.models.organization import Organization
from app.models.subscription import Plan, Subscription, SubscriptionStatus
from app.services.entitlements import (
    PLAN_ENTITLEMENTS,
    get_entitlements,
    get_or_create_subscription,
    sync_trial_expiry,
)


def _make_org(db_session, name: str) -> Organization:
    org = Organization(id=uuid.uuid4(), name=name)
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


def test_get_or_create_subscription_creates_free_when_missing(db_session):
    org = _make_org(db_session, "Org Senza Subscription Srl")
    subscription = get_or_create_subscription(db_session, org.id)
    assert subscription.plan == Plan.free
    assert subscription.status == SubscriptionStatus.active


def test_get_or_create_subscription_reuses_existing(db_session):
    org = _make_org(db_session, "Org Con Subscription Srl")
    existing = Subscription(
        organization_id=org.id, plan=Plan.business, status=SubscriptionStatus.active
    )
    db_session.add(existing)
    db_session.commit()

    subscription = get_or_create_subscription(db_session, org.id)
    assert subscription.id == existing.id
    assert subscription.plan == Plan.business


def test_sync_trial_expiry_keeps_active_trial(db_session):
    org = _make_org(db_session, "Org Trial Attivo Srl")
    subscription = Subscription(
        organization_id=org.id,
        plan=Plan.essential,
        status=SubscriptionStatus.trialing,
        trial_ends_at=datetime.now(timezone.utc) + timedelta(days=5),
    )
    db_session.add(subscription)
    db_session.commit()

    result = sync_trial_expiry(db_session, subscription)
    assert result.plan == Plan.essential
    assert result.status == SubscriptionStatus.trialing


def test_sync_trial_expiry_downgrades_expired_trial(db_session):
    org = _make_org(db_session, "Org Trial Scaduto Srl")
    subscription = Subscription(
        organization_id=org.id,
        plan=Plan.essential,
        status=SubscriptionStatus.trialing,
        trial_ends_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(subscription)
    db_session.commit()

    result = sync_trial_expiry(db_session, subscription)
    assert result.plan == Plan.free
    assert result.status == SubscriptionStatus.active


def test_get_entitlements_matches_plan_table(db_session):
    org = _make_org(db_session, "Org Entitlements Srl")
    db_session.add(
        Subscription(
            organization_id=org.id, plan=Plan.free, status=SubscriptionStatus.active
        )
    )
    db_session.commit()

    entitlements = get_entitlements(db_session, org.id)
    assert entitlements == PLAN_ENTITLEMENTS[Plan.free]


def test_free_plan_entitlements_are_the_most_restrictive():
    free = PLAN_ENTITLEMENTS[Plan.free]
    assert free.max_ai_documents_per_month == 0
    assert free.compliance_measures_limit == 3
    assert free.compliance_measures_editable is False
    assert free.incident_reporting_enabled is False
    assert free.supply_chain_enabled is False


def test_essential_includes_incident_reporting_but_not_supply_chain():
    essential = PLAN_ENTITLEMENTS[Plan.essential]
    assert essential.incident_reporting_enabled is True
    assert essential.supply_chain_enabled is False
    assert essential.max_ai_documents_per_month == 5
    assert essential.max_users == 1


def test_business_unlocks_supply_chain_and_more_users():
    business = PLAN_ENTITLEMENTS[Plan.business]
    assert business.supply_chain_enabled is True
    assert business.max_users == 5
    assert business.max_ai_documents_per_month is None


def test_enterprise_is_fully_unlimited():
    enterprise = PLAN_ENTITLEMENTS[Plan.enterprise]
    assert enterprise.max_users is None
    assert enterprise.max_ai_documents_per_month is None
    assert enterprise.white_label_enabled is True
    assert enterprise.api_access_enabled is True
