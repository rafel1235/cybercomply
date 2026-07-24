"""Test del modello dati completo introdotto in Fase 2: relazioni, vincoli di unicità e
comportamento a cascata quando un'organizzazione (o un incidente) viene eliminata."""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    AssessmentResult,
    ComplianceMeasure,
    Document,
    DocumentType,
    Incident,
    IncidentNotification,
    IncidentStatus,
    MeasureStatus,
    Nis2Category,
    NotificationPhase,
    Organization,
    Plan,
    Subscription,
    SubscriptionStatus,
    Supplier,
    SupplierCriticality,
    SupplierQuestionnaire,
    SupplierStatus,
)


def _make_org(db_session, name="Azienda di Test Srl") -> Organization:
    org = Organization(name=name, sector="Software", employee_count=25)
    db_session.add(org)
    db_session.flush()
    return org


def test_assessment_result_linked_to_organization(db_session):
    org = _make_org(db_session)
    db_session.add(
        AssessmentResult(
            organization_id=org.id,
            nis2_category=Nis2Category.importante,
            cra_in_scope=True,
            answers={"dipendenti": 25},
        )
    )
    db_session.commit()

    db_session.refresh(org)
    assert len(org.assessment_results) == 1
    assert org.assessment_results[0].nis2_category == Nis2Category.importante


def test_compliance_measure_unique_per_organization(db_session):
    org = _make_org(db_session)
    db_session.add(
        ComplianceMeasure(
            organization_id=org.id,
            measure_id="mfa_accessi_remoti",
            status=MeasureStatus.conforme,
        )
    )
    db_session.commit()

    db_session.add(
        ComplianceMeasure(
            organization_id=org.id,
            measure_id="mfa_accessi_remoti",
            status=MeasureStatus.parziale,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_document_versioning_fields(db_session):
    org = _make_org(db_session)
    doc = Document(
        organization_id=org.id,
        doc_type=DocumentType.registro_rischi,
        content={"sezioni": ["rischio1", "rischio2"]},
        version=1,
    )
    db_session.add(doc)
    db_session.commit()

    assert doc.pdf_url is None
    assert doc.version == 1


def test_incident_notifications_cascade_delete(db_session):
    org = _make_org(db_session)
    incident = Incident(
        organization_id=org.id,
        reference_code="INC-2026-001",
        incident_type="Ransomware",
        status=IncidentStatus.aperto,
        data={},
    )
    db_session.add(incident)
    db_session.flush()

    db_session.add(
        IncidentNotification(
            incident_id=incident.id,
            phase=NotificationPhase.early_warning_24h,
            recipient="CSIRT Italia",
        )
    )
    db_session.commit()

    incident_id = incident.id
    db_session.delete(incident)
    db_session.commit()

    remaining = (
        db_session.query(IncidentNotification)
        .filter(IncidentNotification.incident_id == incident_id)
        .count()
    )
    assert remaining == 0


def test_supplier_questionnaire_access_token_unique(db_session):
    org = _make_org(db_session)
    supplier = Supplier(
        organization_id=org.id,
        name="Cloud Provider SpA",
        criticality=SupplierCriticality.alta,
    )
    db_session.add(supplier)
    db_session.flush()

    token = uuid.uuid4().hex
    db_session.add(
        SupplierQuestionnaire(
            supplier_id=supplier.id,
            access_token=token,
            computed_status=SupplierStatus.non_valutato,
        )
    )
    db_session.commit()

    db_session.add(
        SupplierQuestionnaire(
            supplier_id=supplier.id,
            access_token=token,
            computed_status=SupplierStatus.conforme,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_subscription_one_per_organization(db_session):
    org = _make_org(db_session)
    db_session.add(
        Subscription(
            organization_id=org.id,
            plan=Plan.essential,
            status=SubscriptionStatus.trialing,
        )
    )
    db_session.commit()

    db_session.add(
        Subscription(
            organization_id=org.id, plan=Plan.business, status=SubscriptionStatus.active
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_deleting_organization_cascades_to_all_fase2_tables(db_session):
    org = _make_org(db_session, name="Azienda da Cancellare Srl")
    db_session.add(
        AssessmentResult(
            organization_id=org.id,
            nis2_category=Nis2Category.essenziale,
            cra_in_scope=False,
            answers={},
        )
    )
    db_session.add(
        ComplianceMeasure(organization_id=org.id, measure_id="backup_cifrati_testati")
    )
    db_session.add(
        Document(organization_id=org.id, doc_type=DocumentType.piano_bcp, content={})
    )
    supplier = Supplier(organization_id=org.id, name="Fornitore Test")
    db_session.add(supplier)
    db_session.add(Subscription(organization_id=org.id, plan=Plan.free))
    db_session.commit()

    org_id = org.id
    db_session.delete(org)
    db_session.commit()

    assert (
        db_session.query(AssessmentResult).filter_by(organization_id=org_id).count()
        == 0
    )
    assert (
        db_session.query(ComplianceMeasure).filter_by(organization_id=org_id).count()
        == 0
    )
    assert db_session.query(Document).filter_by(organization_id=org_id).count() == 0
    assert db_session.query(Supplier).filter_by(organization_id=org_id).count() == 0
    assert db_session.query(Subscription).filter_by(organization_id=org_id).count() == 0
