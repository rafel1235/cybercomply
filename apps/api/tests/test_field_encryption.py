"""Test della cifratura a riposo (Fase 8): sia il servizio puro (encrypt/decrypt_value)
sia l'integrazione end-to-end via ORM su Organization.vat_number e Incident.data,
verificando che il valore grezzo nel database non sia mai in chiaro quando la chiave è
configurata."""

import uuid

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import text

from app.core.config import get_settings
from app.models.incident import Incident, IncidentStatus
from app.models.organization import Organization
from app.services import field_encryption as fe

_TEST_KEY = Fernet.generate_key().decode()


@pytest.fixture(autouse=True)
def _configure_encryption(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "field_encryption_key", _TEST_KEY)
    yield


def test_is_encryption_configured_false_with_placeholder(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(
        settings, "field_encryption_key", "replace-with-real-fernet-key"
    )
    assert fe.is_encryption_configured() is False


def test_is_encryption_configured_true_with_real_key():
    assert fe.is_encryption_configured() is True


def test_encrypt_decrypt_round_trip():
    encrypted = fe.encrypt_value("IT12345678901")
    assert encrypted is not None
    assert encrypted.startswith("enc::")
    assert "12345678901" not in encrypted
    assert fe.decrypt_value(encrypted) == "IT12345678901"


def test_encrypt_none_stays_none():
    assert fe.encrypt_value(None) is None
    assert fe.decrypt_value(None) is None


def test_encrypt_without_key_stores_plaintext(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "field_encryption_key", "")

    value = fe.encrypt_value("IT12345678901")
    assert value == "IT12345678901"  # non cifrato: nessuna chiave configurata


def test_decrypt_plaintext_value_passes_through_unchanged():
    """Un valore mai stato cifrato (nessun prefisso enc::) va restituito invariato,
    anche con la chiave configurata: compatibilità con righe scritte prima di questa
    fase o mentre la chiave non era ancora impostata."""
    assert fe.decrypt_value("IT99999999999") == "IT99999999999"


def test_decrypt_encrypted_value_without_key_returns_none(monkeypatch):
    encrypted = fe.encrypt_value("segreto")
    settings = get_settings()
    monkeypatch.setattr(settings, "field_encryption_key", "")

    assert fe.decrypt_value(encrypted) is None


def test_decrypt_corrupted_token_returns_none():
    assert fe.decrypt_value("enc::not-a-valid-fernet-token") is None


def test_organization_vat_number_encrypted_at_rest(db_session):
    org = Organization(
        id=uuid.uuid4(), name="Org Cifratura Srl", vat_number="IT01234567890"
    )
    db_session.add(org)
    db_session.commit()

    # L'ORM deve restituire il valore in chiaro (decifrato in modo trasparente).
    db_session.refresh(org)
    assert org.vat_number == "IT01234567890"

    # Ma il valore grezzo nella tabella non deve mai contenere la P.IVA in chiaro.
    raw = db_session.execute(
        text("SELECT vat_number FROM organizations WHERE id = :id"), {"id": org.id}
    ).scalar_one()
    assert raw.startswith("enc::")
    assert "01234567890" not in raw


def test_incident_data_encrypted_at_rest(db_session):
    org = Organization(id=uuid.uuid4(), name="Org Incidente Cifrato Srl")
    db_session.add(org)
    db_session.commit()

    incident = Incident(
        organization_id=org.id,
        reference_code="INC-TEST-ENC-001",
        incident_type="data breach",
        status=IncidentStatus.aperto,
        data={"descrizione": "Accesso non autorizzato al database clienti"},
    )
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    assert incident.data == {
        "descrizione": "Accesso non autorizzato al database clienti"
    }

    raw = db_session.execute(
        text("SELECT data FROM incidents WHERE id = :id"), {"id": incident.id}
    ).scalar_one()
    assert raw.startswith("enc::")
    assert "non autorizzato" not in raw
