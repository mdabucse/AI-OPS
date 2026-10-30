from app.rag import retrieve_context
from app.main import app
from fastapi.testclient import TestClient


def test_pool_saturation_query_retrieves_database_runbook():
    results = retrieve_context("login latency database connection pool waiting requests")

    assert results
    assert results[0]["document_id"] == "runbook-db-pool-saturation"
    assert "connection pool" in results[0]["content"].lower()


def test_retrieval_honors_top_k_and_returns_scores():
    results = retrieve_context("login latency", top_k=2)

    assert len(results) <= 2
    assert all("score" in result for result in results)
    assert all(result["score"] > 0 for result in results)


def test_unrelated_query_returns_no_context():
    assert retrieve_context("weather forecast for tomorrow") == []


def test_rag_search_requires_login_and_returns_runbook():
    client = TestClient(app)
    assert client.get("/api/rag/search?q=database+pool").status_code == 401

    client.post("/login", data={"username": "admin", "password": "admin"})
    response = client.get("/api/rag/search?q=database+pool&top_k=1")
    assert response.status_code == 200
    assert response.json()["results"][0]["document_id"] == "runbook-db-pool-saturation"
