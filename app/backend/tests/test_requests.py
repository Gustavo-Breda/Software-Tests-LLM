from .conftest import *


############################ US-03 — Create request ############################

def test_create_request_happy_path(client):
    auth = auth_header(client, "alice@example.com", "Senha123")
    r = client.post("/api/requests", headers=auth, json={
        "title": "Acesso ao sistema novo",
        "description": "Solicito acesso ao sistema novo de gestão de chamados.",
        "priority": "alta",
    })
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "aberta"
    assert body["priority"] == "alta"
    assert body["cancelled_at"] is None


def test_create_request_title_too_short_rejected(client):
    auth = auth_header(client, "alice@example.com", "Senha123")
    r = client.post("/api/requests", headers=auth, json={
        "title": "abc",
        "description": "Descrição válida com mais de dez caracteres.",
        "priority": "baixa",
    })
    assert r.status_code == 422


def test_create_request_description_too_short_rejected(client):
    auth = auth_header(client, "alice@example.com", "Senha123")
    r = client.post("/api/requests", headers=auth, json={
        "title": "Título válido",
        "description": "Curta",
        "priority": "baixa",
    })
    assert r.status_code == 422


def test_create_request_invalid_priority_rejected(client):
    auth = auth_header(client, "alice@example.com", "Senha123")
    r = client.post("/api/requests", headers=auth, json={
        "title": "Título válido",
        "description": "Descrição válida com tamanho suficiente.",
        "priority": "urgentíssima",
    })
    assert r.status_code == 422


def test_create_request_unauthenticated_rejected(client):
    r = client.post("/api/requests", json={
        "title": "Título válido",
        "description": "Descrição válida com tamanho suficiente.",
        "priority": "baixa",
    })
    assert r.status_code == 401




############################ US-04 — List + filter #############################

def test_list_returns_only_own_requests_by_default(client):
    # alice has 4 seed requests; bob has 2 — each sees only their own
    alice = auth_header(client, "alice@example.com", "Senha123")
    r = client.get("/api/requests", headers=alice)
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 4
    assert all(i["owner_id"] == r.json()["items"][0]["owner_id"] for i in items)


def test_list_newest_first(client):
    alice = auth_header(client, "alice@example.com", "Senha123")
    r = client.get("/api/requests", headers=alice)
    items = r.json()["items"]
    dates = [i["created_at"] for i in items]
    assert dates == sorted(dates, reverse=True)


def test_list_empty_filter_returns_200_not_404(client):
    alice = auth_header(client, "alice@example.com", "Senha123")
    # alice has no finalizada+alta combo in seed
    r = client.get("/api/requests?status=finalizada&priority=alta", headers=alice)
    assert r.status_code == 200
    assert r.json()["items"] == []


def test_list_filter_by_status(client):
    alice = auth_header(client, "alice@example.com", "Senha123")
    r = client.get("/api/requests?status=aberta", headers=alice)
    assert r.status_code == 200
    assert all(i["status"] == "aberta" for i in r.json()["items"])


def test_list_filter_by_priority(client):
    alice = auth_header(client, "alice@example.com", "Senha123")
    r = client.get("/api/requests?priority=alta", headers=alice)
    assert r.status_code == 200
    assert all(i["priority"] == "alta" for i in r.json()["items"])


def test_list_combinable_filters(client):
    bob = auth_header(client, "bob@example.com", "Senha123")
    r = client.get("/api/requests?status=aberta&priority=alta", headers=bob)
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1
    assert items[0]["status"] == "aberta"
    assert items[0]["priority"] == "alta"




################################ US-05 — Cancel ################################

def test_cancel_own_open_request(client):
    bob = auth_header(client, "bob@example.com", "Senha123")
    r = client.get("/api/requests?status=aberta", headers=bob)
    req_id = r.json()["items"][0]["id"]

    r = client.post(f"/api/requests/{req_id}/cancel", headers=bob)
    assert r.status_code == 200
    assert r.json()["status"] == "cancelada"
    assert r.json()["cancelled_at"] is not None


def test_cancel_ownership_enforced(client):
    # alice's requests have owner_id != bob's id
    alice = auth_header(client, "alice@example.com", "Senha123")
    bob = auth_header(client, "bob@example.com", "Senha123")

    r = client.get("/api/requests?status=aberta", headers=alice)
    alice_req_id = r.json()["items"][0]["id"]

    r = client.post(f"/api/requests/{alice_req_id}/cancel", headers=bob)
    assert r.status_code == 403


def test_cancel_non_cancellable_status_rejected(client):
    alice = auth_header(client, "alice@example.com", "Senha123")
    r = client.get("/api/requests?status=aberta", headers=alice)
    req_id = r.json()["items"][0]["id"]

    # First cancel succeeds
    client.post(f"/api/requests/{req_id}/cancel", headers=alice)
    # Second cancel on same (now cancelada) request must fail
    r = client.post(f"/api/requests/{req_id}/cancel", headers=alice)
    assert r.status_code == 409


def test_cancel_nonexistent_request_returns_404(client):
    alice = auth_header(client, "alice@example.com", "Senha123")
    r = client.post("/api/requests/99999/cancel", headers=alice)
    assert r.status_code == 404


def test_cancel_unauthenticated_rejected(client):
    r = client.post("/api/requests/1/cancel")
    assert r.status_code == 401
