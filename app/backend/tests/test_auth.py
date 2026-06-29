from .conftest import *


################################ US-01 — Login #################################

def test_login_valid_credentials(client):
    r = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "Senha123"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_invalid_password_returns_generic_message(client):
    r = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "wrong"})
    assert r.status_code == 401
    assert r.json()["detail"] == "E-mail ou senha inválidos."


def test_login_nonexistent_email_no_enumeration(client):
    r = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "whatever"})
    assert r.status_code == 401
    assert r.json()["detail"] == "E-mail ou senha inválidos."


def test_login_lockout_after_5_consecutive_failures(client):
    for _ in range(5):
        r = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "wrong"})
        assert r.status_code == 401

    # 6th attempt — even with the correct password — must be rejected while locked
    r = client.post("/api/auth/login", json={"email": "alice@example.com", "password": "Senha123"})
    assert r.status_code == 423
    assert "bloqueada" in r.json()["detail"].lower()
    assert "retry-after" in {k.lower() for k in r.headers}


def test_me_returns_authenticated_user(client):
    auth = auth_header(client, "alice@example.com", "Senha123")
    r = client.get("/api/auth/me", headers=auth)
    assert r.status_code == 200
    assert r.json()["email"] == "alice@example.com"


def test_me_without_token_returns_401(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


############################### US-02 — Register ###############################

def test_register_happy_path(client):
    r = client.post("/api/auth/register", json={
        "name": "Charlie Tester", "email": "charlie@example.com", "password": "Senha123",
    })
    assert r.status_code == 201
    assert r.json()["email"] == "charlie@example.com"


def test_register_duplicate_email_rejected(client):
    payload = {"name": "Charlie One", "email": "charlie@example.com", "password": "Senha123"}
    client.post("/api/auth/register", json=payload)
    r = client.post("/api/auth/register", json={**payload, "name": "Charlie Two"})
    assert r.status_code == 409


def test_register_password_without_number_rejected(client):
    r = client.post("/api/auth/register", json={
        "name": "Daniela", "email": "dani@example.com", "password": "senhasenha",
    })
    assert r.status_code == 422


def test_register_password_without_letter_rejected(client):
    r = client.post("/api/auth/register", json={
        "name": "Daniela", "email": "dani@example.com", "password": "12345678",
    })
    assert r.status_code == 422


def test_register_name_too_short_rejected(client):
    r = client.post("/api/auth/register", json={
        "name": "Eu", "email": "eu@example.com", "password": "Senha123",
    })
    assert r.status_code == 422


def test_register_name_too_long_rejected(client):
    r = client.post("/api/auth/register", json={
        "name": "A" * 81, "email": "long@example.com", "password": "Senha123",
    })
    assert r.status_code == 422
