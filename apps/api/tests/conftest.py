import os
import tempfile

os.environ.setdefault("SUPABASE_JWT_SECRET", "test-secret-for-pytest-only")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")

# Fase 9: i test non devono MAI poter toccare un database reale, nemmeno per errore. Prima
# di questo fix, `engine()` si collegava a qualunque `DATABASE_URL` fosse presente in
# `.env` — se uno sviluppatore ci avesse per sbaglio lasciato l'URL di un progetto
# Supabase reale (è già capitato in questa stessa sessione di sviluppo), eseguire
# `pytest` avrebbe creato e poi CANCELLATO le tabelle di quel database reale
# (`Base.metadata.create_all` / `drop_all`). Si avvia invece sempre un Postgres
# incorporato isolato (`pgserver`, nessun Docker richiesto) e si forza `DATABASE_URL` su
# questa istanza usa e getta PRIMA di importare qualunque modulo dell'app — compreso
# `app.main`, che legge le impostazioni al momento dell'import. Questo rende anche la
# pipeline CI (GitHub Actions) banale: basta `pytest`, senza un servizio Postgres
# separato da configurare, esattamente come in locale.
import pgserver  # noqa: E402

_pg_data_dir = tempfile.mkdtemp(prefix="cybercomplyit_test_pg_")
_pg_server = pgserver.get_server(_pg_data_dir)
os.environ["DATABASE_URL"] = _pg_server.get_uri().replace(
    "postgresql://", "postgresql+psycopg2://"
)

import uuid  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from jose import jwt  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402

TEST_JWT_SECRET = os.environ["SUPABASE_JWT_SECRET"]


@pytest.fixture(scope="session")
def engine():
    settings = get_settings()
    eng = create_engine(settings.database_url)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()
    _pg_server.cleanup()


@pytest.fixture()
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def make_token(user_id: str | None = None, email: str = "founder@example.it") -> str:
    uid = user_id or str(uuid.uuid4())
    payload = {
        "sub": uid,
        "email": email,
        "role": "authenticated",
        "aud": "authenticated",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")
