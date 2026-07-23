from tests.conftest import make_token


def test_sync_creates_user_and_organization(client):
    token = make_token(email="founder@cybercomplyit.it")
    response = client.post(
        "/api/v1/auth/sync",
        json={"full_name": "Mario Rossi", "organization_name": "Rossi SRL"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "founder@cybercomplyit.it"
    assert len(body["organizations"]) == 1
    assert body["organizations"][0]["name"] == "Rossi SRL"


def test_sync_is_idempotent_and_does_not_duplicate_org(client):
    token = make_token(email="same-user@cybercomplyit.it")
    first = client.post(
        "/api/v1/auth/sync",
        json={"organization_name": "Prima Org"},
        headers={"Authorization": f"Bearer {token}"},
    )
    second = client.post(
        "/api/v1/auth/sync",
        json={"organization_name": "Non deve crearsi"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert len(second.json()["organizations"]) == 1
    assert second.json()["organizations"][0]["name"] == "Prima Org"


def test_me_requires_prior_sync(client):
    token = make_token(email="never-synced@cybercomplyit.it")
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404


def test_me_returns_data_after_sync(client):
    token = make_token(email="synced@cybercomplyit.it")
    client.post(
        "/api/v1/auth/sync",
        json={"organization_name": "Synced Org"},
        headers={"Authorization": f"Bearer {token}"},
    )
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "synced@cybercomplyit.it"


def test_missing_token_is_rejected(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_invalid_token_is_rejected(client):
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_login_event_locks_account_after_repeated_failures(client):
    token = make_token(email="target@cybercomplyit.it")
    client.post(
        "/api/v1/auth/sync",
        json={"organization_name": "Target Org"},
        headers={"Authorization": f"Bearer {token}"},
    )

    last_response = None
    for _ in range(5):
        last_response = client.post(
            "/api/v1/auth/login-events",
            json={"email": "target@cybercomplyit.it", "success": False},
        )

    assert last_response.status_code == 200

    locked_response = client.post(
        "/api/v1/auth/login-events",
        json={"email": "target@cybercomplyit.it", "success": False},
    )
    assert locked_response.status_code == 423
