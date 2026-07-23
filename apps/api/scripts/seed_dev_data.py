"""Popola il database di sviluppo con dati fittizi ma realistici.

Uso:
    python -m scripts.seed_dev_data

Pensato per un ambiente di SVILUPPO locale, mai per produzione (lo script non controlla
`ENVIRONMENT` per bloccarsi da solo: la protezione è che va lanciato manualmente e non fa
parte di nessuna pipeline di deploy). Crea 3 organizzazioni con profili diversi (una PMI
essenziale NIS2, una importante, una fuori perimetro) ciascuna con utenti, assessment,
misure di conformità, documenti, un incidente con le sue notifiche, fornitori con
questionari e un abbonamento — così le pagine Fase 4 hanno dati veri da mostrare durante lo
sviluppo, invece di stati vuoti.
"""

import sys
import uuid
from datetime import datetime, timedelta, timezone

from faker import Faker

from app.db.session import SessionLocal
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
    OrganizationMember,
    OrganizationRole,
    Plan,
    Subscription,
    SubscriptionStatus,
    Supplier,
    SupplierCriticality,
    SupplierQuestionnaire,
    SupplierStatus,
    User,
)
from app.services.compliance_catalog import COMPLIANCE_MEASURE_IDS

fake = Faker("it_IT")
Faker.seed(42)

ORG_PROFILES = [
    {
        "name": "Meridiana Software Srl",
        "sector": "Sviluppo software gestionale",
        "employee_count": 38,
        "annual_revenue_eur": 4_200_000,
        "nis2_category": Nis2Category.importante,
        "cra_in_scope": True,
        "plan": Plan.essential,
    },
    {
        "name": "Ospedale San Ranieri SpA",
        "sector": "Sanità privata",
        "employee_count": 410,
        "annual_revenue_eur": 62_000_000,
        "nis2_category": Nis2Category.essenziale,
        "cra_in_scope": False,
        "plan": Plan.business,
    },
    {
        "name": "Bottega Digitale di Marco Ferraro",
        "sector": "Consulenza IT freelance",
        "employee_count": 3,
        "annual_revenue_eur": 180_000,
        "nis2_category": Nis2Category.non_in_perimetro,
        "cra_in_scope": False,
        "plan": Plan.free,
    },
]


def seed() -> None:
    db = SessionLocal()
    try:
        for profile in ORG_PROFILES:
            org = Organization(
                name=profile["name"],
                vat_number=(
                    fake.company_vat()
                    if hasattr(fake, "company_vat")
                    else fake.numerify("IT###########")
                ),
                sector=profile["sector"],
                employee_count=profile["employee_count"],
                annual_revenue_eur=profile["annual_revenue_eur"],
            )
            db.add(org)
            db.flush()

            admin_user = User(
                id=uuid.uuid4(), email=fake.company_email(), full_name=fake.name()
            )
            viewer_user = User(
                id=uuid.uuid4(), email=fake.company_email(), full_name=fake.name()
            )
            db.add_all([admin_user, viewer_user])
            db.flush()

            db.add_all(
                [
                    OrganizationMember(
                        user_id=admin_user.id,
                        organization_id=org.id,
                        role=OrganizationRole.admin,
                    ),
                    OrganizationMember(
                        user_id=viewer_user.id,
                        organization_id=org.id,
                        role=OrganizationRole.viewer,
                    ),
                ]
            )

            db.add(
                AssessmentResult(
                    organization_id=org.id,
                    nis2_category=profile["nis2_category"],
                    cra_in_scope=profile["cra_in_scope"],
                    answers={
                        "settore": profile["sector"],
                        "dipendenti": profile["employee_count"],
                        "fatturato_eur": profile["annual_revenue_eur"],
                        "fornisce_ict_a_soggetti_essenziali": fake.boolean(),
                    },
                    created_by=admin_user.id,
                )
            )

            for i, measure_id in enumerate(COMPLIANCE_MEASURE_IDS):
                status = [
                    MeasureStatus.conforme,
                    MeasureStatus.parziale,
                    MeasureStatus.non_conforme,
                    MeasureStatus.non_applicabile,
                ][i % 4]
                db.add(
                    ComplianceMeasure(
                        organization_id=org.id,
                        measure_id=measure_id,
                        status=status,
                        note=(
                            fake.sentence()
                            if status != MeasureStatus.non_applicabile
                            else None
                        ),
                        updated_by=admin_user.id,
                    )
                )

            for doc_type in [
                DocumentType.registro_rischi,
                DocumentType.procedura_incident_response,
                DocumentType.politica_controllo_accessi,
            ]:
                db.add(
                    Document(
                        organization_id=org.id,
                        doc_type=doc_type,
                        content={"generato_da": "seed", "settore": profile["sector"]},
                        version=1,
                        created_by=admin_user.id,
                    )
                )

            incident = Incident(
                organization_id=org.id,
                reference_code=f"INC-2026-{fake.unique.random_int(min=100, max=999)}",
                incident_type=fake.random_element(
                    ["Phishing mirato", "Ransomware", "Accesso non autorizzato", "DDoS"]
                ),
                status=IncidentStatus.chiuso,
                opened_at=datetime.now(timezone.utc) - timedelta(days=10),
                closed_at=datetime.now(timezone.utc) - timedelta(days=8),
                data={"descrizione": fake.sentence(nb_words=12)},
                created_by=admin_user.id,
            )
            db.add(incident)
            db.flush()

            db.add(
                IncidentNotification(
                    incident_id=incident.id,
                    phase=NotificationPhase.early_warning_24h,
                    recipient="CSIRT Italia",
                    content="Early warning inviato entro le 24 ore come da Art. 23 NIS2.",
                )
            )
            db.add(
                IncidentNotification(
                    incident_id=incident.id,
                    phase=NotificationPhase.notifica_72h,
                    recipient="CSIRT Italia",
                    content="Notifica completa inviata entro le 72 ore.",
                )
            )

            for _ in range(2):
                supplier = Supplier(
                    organization_id=org.id,
                    name=fake.company(),
                    category=fake.random_element(
                        ["Cloud provider", "MSP", "Sviluppo software"]
                    ),
                    criticality=fake.random_element(list(SupplierCriticality)),
                    status=fake.random_element(list(SupplierStatus)),
                    last_reviewed_at=datetime.now(timezone.utc)
                    - timedelta(days=fake.random_int(1, 300)),
                )
                db.add(supplier)
                db.flush()
                db.add(
                    SupplierQuestionnaire(
                        supplier_id=supplier.id,
                        answers={
                            "mfa_attivo": fake.boolean(),
                            "certificazione_iso27001": fake.boolean(),
                        },
                        computed_status=supplier.status,
                        access_token=uuid.uuid4().hex,
                        sent_at=datetime.now(timezone.utc) - timedelta(days=20),
                        completed_at=datetime.now(timezone.utc) - timedelta(days=15),
                    )
                )

            db.add(
                Subscription(
                    organization_id=org.id,
                    plan=profile["plan"],
                    status=SubscriptionStatus.active,
                )
            )

            db.commit()
            print(f"Creata organizzazione '{org.name}' (id={org.id})")

    finally:
        db.close()


if __name__ == "__main__":
    try:
        seed()
    except Exception as exc:  # noqa: BLE001
        print(f"Seed fallito: {exc}", file=sys.stderr)
        raise
