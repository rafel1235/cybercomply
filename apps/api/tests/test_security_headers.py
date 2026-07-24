"""Test degli header di sicurezza HTTP (Fase 8): verificano che il middleware li imposti
davvero su ogni risposta, non solo che il codice esista."""


def test_root_response_has_security_headers(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert (
        resp.headers["content-security-policy"]
        == "default-src 'none'; frame-ancestors 'none'"
    )
    assert "camera=()" in resp.headers["permissions-policy"]
    assert resp.headers["cross-origin-opener-policy"] == "same-origin"
    assert resp.headers["cross-origin-resource-policy"] == "same-origin"


def test_server_header_does_not_expose_library_version(client):
    resp = client.get("/")
    assert resp.headers["server"] == "cybercomplyit"
    assert "uvicorn" not in resp.headers["server"].lower()


def test_hsts_absent_outside_production(client):
    """In sviluppo/test non forziamo HTTPS (Strict-Transport-Security assente):
    imporlo fuori produzione romperebbe l'uso locale su http://localhost."""
    resp = client.get("/")
    assert "strict-transport-security" not in resp.headers
