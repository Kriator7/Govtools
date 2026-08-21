def test_health_endpoints(client):
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/health/database").json()["status"] == "ok"
    assert client.get("/health/mls").json()["status"] == "ok"
    assert client.get("/health/telegram").json()["status"] == "ok"
    assert client.get("/health/twilio").json()["status"] == "ok"
    assert client.get("/health/email").json()["status"] == "ok"


def test_realtor_crud(client):
    created = client.post(
        "/api/v1/realtors",
        json={"name": "Second Demo Realtor", "license_state": "NV"},
    )
    assert created.status_code == 201
    realtor_id = created.json()["id"]
    fetched = client.get(f"/api/v1/realtors/{realtor_id}")
    assert fetched.json()["name"] == "Second Demo Realtor"
