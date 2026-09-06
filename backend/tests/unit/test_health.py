from fastapi.testclient import TestClient


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["status"] == "ok"


def test_health_endpoint_versioned(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"


def test_response_has_trace_id_header(client: TestClient) -> None:
    response = client.get("/api/health")
    assert "X-Trace-Id" in response.headers
    assert "X-Request-Id" in response.headers
