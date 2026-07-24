"""Verifica che le liste paginate non degenerino in query N+1 (Fase 10 — performance).

Bug reale scoperto in questa fase: `list_incidents`/`list_suppliers` serializzano ogni
riga leggendo una relazione (`incident.notifications` / `supplier.questionnaires`) senza
eager loading — con SQLAlchemy, questo esegue una query SQL separata per ogni riga della
pagina invece di una sola query aggiuntiva per l'intera pagina (con `selectinload`).

Invece di assumere un numero assoluto di query (fragile: dipende da dettagli interni come
quante query fa la dependency di autenticazione), questi test confrontano il numero di
query eseguite per la STESSA richiesta con un numero di righe diverso (2 vs 8): se il
conteggio resta identico, il costo è indipendente dal numero di righe (O(1)); se cresce
in proporzione, è tornata la regressione N+1."""

from sqlalchemy import event

from tests.conftest import make_token


def _sync(client, email, org_name):
    token = make_token(email=email)
    resp = client.post(
        "/api/v1/auth/sync",
        json={"organization_name": org_name},
        headers={"Authorization": f"Bearer {token}"},
    )
    return token, resp.json()["organizations"][0]["id"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


class _QueryCounter:
    def __init__(self, connection):
        self.count = 0
        self._connection = connection

    def __enter__(self):
        event.listen(self._connection, "before_cursor_execute", self._on_execute)
        return self

    def __exit__(self, *exc_info):
        event.remove(self._connection, "before_cursor_execute", self._on_execute)

    def _on_execute(self, *args, **kwargs):
        self.count += 1


def _count_queries_for_get(client, db_session, url, headers):
    connection = db_session.connection()
    with _QueryCounter(connection) as counter:
        resp = client.get(url, headers=headers)
    assert resp.status_code == 200
    return resp, counter.count


def test_list_incidents_query_count_is_independent_of_row_count(client, db_session):
    token, _ = _sync(client, "n1-inc@cybercomplyit.it", "Org N+1 Incidenti Srl")

    def _create_incident_with_notification():
        resp = client.post(
            "/api/v1/incidents",
            json={"incident_type": "malware", "data": {"nota": "caso"}},
            headers=_auth(token),
        )
        incident_id = resp.json()["id"]
        # Almeno una notifica per incidente, così `incident.notifications` non è mai una
        # collezione vuota (il bug N+1 si manifesta comunque anche a vuoto, ma con dati
        # reali il costo è più rappresentativo).
        client.post(
            f"/api/v1/incidents/{incident_id}/notifications",
            json={"phase": "early_warning_24h", "recipient": "csirt@interno.it"},
            headers=_auth(token),
        )

    for _ in range(2):
        _create_incident_with_notification()
    resp_small, count_small = _count_queries_for_get(
        client, db_session, "/api/v1/incidents", _auth(token)
    )
    assert len(resp_small.json()) == 2

    for _ in range(6):
        _create_incident_with_notification()
    resp_large, count_large = _count_queries_for_get(
        client, db_session, "/api/v1/incidents", _auth(token)
    )
    assert len(resp_large.json()) == 8

    assert count_large == count_small, (
        f"Query eseguite con 2 incidenti: {count_small}; con 8 incidenti: {count_large}. "
        "Dovrebbero essere identiche (costo indipendente dal numero di righe): possibile "
        "regressione N+1 su GET /incidents"
    )


def test_list_suppliers_query_count_is_independent_of_row_count(client, db_session):
    from app.models.subscription import Plan, Subscription

    token, org_id = _sync(client, "n1-sup@cybercomplyit.it", "Org N+1 Fornitori Srl")
    subscription = (
        db_session.query(Subscription)
        .filter(Subscription.organization_id == org_id)
        .first()
    )
    subscription.plan = Plan.business
    db_session.commit()

    def _create_supplier_with_questionnaire(name):
        resp = client.post(
            "/api/v1/suppliers",
            json={"name": name, "category": "Cloud provider", "criticality": "media"},
            headers=_auth(token),
        )
        supplier_id = resp.json()["id"]
        client.post(
            f"/api/v1/suppliers/{supplier_id}/questionnaires", headers=_auth(token)
        )

    for i in range(2):
        _create_supplier_with_questionnaire(f"Fornitore piccolo {i}")
    resp_small, count_small = _count_queries_for_get(
        client, db_session, "/api/v1/suppliers", _auth(token)
    )
    assert len(resp_small.json()) == 2

    for i in range(6):
        _create_supplier_with_questionnaire(f"Fornitore grande {i}")
    resp_large, count_large = _count_queries_for_get(
        client, db_session, "/api/v1/suppliers", _auth(token)
    )
    assert len(resp_large.json()) == 8

    assert count_large == count_small, (
        f"Query eseguite con 2 fornitori: {count_small}; con 8 fornitori: {count_large}. "
        "Dovrebbero essere identiche (costo indipendente dal numero di righe): possibile "
        "regressione N+1 su GET /suppliers"
    )
