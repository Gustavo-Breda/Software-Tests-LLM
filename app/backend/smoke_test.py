"""End-to-end smoke test for the PoC backend.

Exercises every business rule called out in the 5 user stories so we can
catch contract bugs before the frontend lands on top of the API.

Run from backend/:  python smoke_test.py
"""
import os
os.environ["DATABASE_URL"] = "sqlite:////tmp/smoke.db"
os.environ["RESET_DB_ON_STARTUP"] = "1"
os.environ["JWT_SECRET"] = "smoke-secret"

# Wipe the DB file before importing the app so lifespan reseeds cleanly.
if os.path.exists("/tmp/smoke.db"):
    os.remove("/tmp/smoke.db")

from fastapi.testclient import TestClient
from app.main import create_app


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def main() -> None:
    app = create_app()
    # `with` activates the lifespan; that runs reset_and_seed().
    with TestClient(app) as client:

        # ---------- US-01: Login ----------
        section("US-01 login: seed user logs in")
        r = client.post("/api/auth/login",
                        json={"email": "alice@example.com", "password": "Senha123"})
        assert r.status_code == 200, r.text
        print("OK login alice")

        section("US-01: invalid creds return generic message")
        r = client.post("/api/auth/login",
                        json={"email": "alice@example.com", "password": "wrong"})
        assert r.status_code == 401
        assert r.json()["detail"] == "E-mail ou senha inválidos."
        print("OK generic 401 message")

        section("US-01: non-existent email also returns 401 (no enumeration)")
        r = client.post("/api/auth/login",
                        json={"email": "ghost@example.com", "password": "whatever"})
        assert r.status_code == 401
        assert r.json()["detail"] == "E-mail ou senha inválidos."
        print("OK no user enumeration")

        section("US-01: lockout after 5 consecutive failures (60s)")
        # alice already has 1 failed attempt; 4 more to trip the lock
        for i in range(4):
            rr = client.post("/api/auth/login",
                             json={"email": "alice@example.com", "password": "wrong"})
            assert rr.status_code == 401, f"attempt {i}: {rr.status_code}"
        # Next attempt — even with correct password — should be locked
        r = client.post("/api/auth/login",
                        json={"email": "alice@example.com", "password": "Senha123"})
        assert r.status_code == 423, f"expected 423 got {r.status_code}: {r.text}"
        assert "bloqueada" in r.json()["detail"].lower()
        assert "Retry-After" in r.headers or "retry-after" in r.headers
        print(f"OK lockout fires: {r.json()['detail']}")

        # ---------- US-02: Register ----------
        section("US-02 register: happy path")
        r = client.post("/api/auth/register", json={
            "name": "Charlie Tester", "email": "charlie@example.com", "password": "Senha123"
        })
        assert r.status_code == 201, r.text
        print("OK register charlie")

        section("US-02: duplicate email rejected (409)")
        r = client.post("/api/auth/register", json={
            "name": "Charlie Dois", "email": "charlie@example.com", "password": "Senha123"
        })
        assert r.status_code == 409
        print("OK duplicate rejected")

        section("US-02: password without number rejected (422)")
        r = client.post("/api/auth/register", json={
            "name": "Daniela", "email": "dani@example.com", "password": "senhasenha"
        })
        assert r.status_code == 422
        print("OK password complexity enforced")

        section("US-02: name shorter than 3 rejected (422)")
        r = client.post("/api/auth/register", json={
            "name": "Eu", "email": "eu@example.com", "password": "Senha123"
        })
        assert r.status_code == 422
        print("OK name length enforced")

        # Log charlie in for the request tests (alice is still locked).
        r = client.post("/api/auth/login",
                        json={"email": "charlie@example.com", "password": "Senha123"})
        assert r.status_code == 200
        ctoken = r.json()["access_token"]
        auth = {"Authorization": f"Bearer {ctoken}"}

        # ---------- US-03: Create request ----------
        section("US-03: create request — happy path")
        r = client.post("/api/requests", headers=auth, json={
            "title": "Acesso ao sistema novo",
            "description": "Solicito acesso ao sistema novo de gestão de chamados.",
            "priority": "alta",
        })
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["status"] == "aberta"
        assert body["priority"] == "alta"
        assert body["cancelled_at"] is None
        new_id = body["id"]
        print(f"OK request created id={new_id} status=aberta")

        section("US-03: title too short rejected (422)")
        r = client.post("/api/requests", headers=auth, json={
            "title": "abc",
            "description": "Descrição válida com mais de dez caracteres.",
            "priority": "baixa",
        })
        assert r.status_code == 422
        print("OK title min-length enforced")

        section("US-03: invalid priority enum rejected (422)")
        r = client.post("/api/requests", headers=auth, json={
            "title": "Título válido",
            "description": "Descrição válida com tamanho suficiente.",
            "priority": "urgentíssima",
        })
        assert r.status_code == 422
        print("OK priority enum enforced")

        # ---------- US-04: List + filter ----------
        section("US-04: default returns own requests, newest first")
        r = client.get("/api/requests", headers=auth)
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) == 1  # charlie just created one
        print(f"OK own-only default ({len(items)} item)")

        section("US-04: empty filter returns 200 with empty list (not 404)")
        r = client.get("/api/requests?status=cancelada", headers=auth)
        assert r.status_code == 200
        assert r.json()["items"] == []
        print("OK empty result handled as data, not error")

        # Bob has richer seed data — log him in.
        rr = client.post("/api/auth/login",
                         json={"email": "bob@example.com", "password": "Senha123"})
        btoken = rr.json()["access_token"]
        bauth = {"Authorization": f"Bearer {btoken}"}

        section("US-04: combinable filters (status + priority)")
        r = client.get("/api/requests?status=aberta&priority=alta", headers=bauth)
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) == 1
        assert items[0]["status"] == "aberta" and items[0]["priority"] == "alta"
        print("OK combinable filters")

        # ---------- US-05: Cancel ----------
        section("US-05: cannot cancel another user's request (403)")
        # alice's first seeded request has id=1; bob can't cancel it
        r = client.post("/api/requests/1/cancel", headers=bauth)
        assert r.status_code == 403
        print("OK ownership enforced")

        section("US-05: cancel own 'aberta' request — happy path")
        r = client.get("/api/requests?status=aberta", headers=bauth)
        bob_open = r.json()["items"][0]
        r = client.post(f"/api/requests/{bob_open['id']}/cancel", headers=bauth)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "cancelada"
        assert r.json()["cancelled_at"] is not None
        print(f"OK request {bob_open['id']} cancelada")

        section("US-05: cannot cancel a non-cancellable status (409)")
        # The request charlie just created is 'aberta' — cancel once (200) then
        # try again, which should now hit the 'status not cancellable' branch.
        r = client.post(f"/api/requests/{new_id}/cancel", headers=auth)
        assert r.status_code == 200
        r2 = client.post(f"/api/requests/{new_id}/cancel", headers=auth)
        assert r2.status_code == 409
        print("OK cannot cancel a non-cancellable status")

    print("\nALL SMOKE TESTS PASSED ✅")


if __name__ == "__main__":
    main()
