from fastapi.testclient import TestClient
import pytest

from app.main import app

client = TestClient(app)
VALID = {"base_amount": "100.00", "current_rate_percent": "10", "proposed_rate_percent": "15"}


def test_health_and_documented_contract():
    assert client.get("/health").json()["rag_status"] in {"not_configured", "configured"}
    schema = client.get("/openapi.json").json()
    assert {"/health", "/simulate"} <= schema["paths"].keys()
    assert client.get("/docs").status_code == 200


def test_hypothetical_comparison():
    response = client.post("/simulate", json=VALID)
    assert response.status_code == 200
    body = response.json()
    assert body["current"]["tax_amount"] == "10.00"
    assert body["proposed"]["total_amount"] == "115.00"
    assert body["tax_difference"] == "5.00"
    assert body["currency"] == "BRL"
    assert "hipotético" in body["disclaimer"]


@pytest.mark.parametrize("field,value", [
    ("base_amount", "-0.01"), ("base_amount", "100.001"),
    ("base_amount", "1000000000001"), ("base_amount", "NaN"),
    ("base_amount", "Infinity"), ("base_amount", None),
    ("current_rate_percent", "-1"), ("proposed_rate_percent", "101"),
    ("proposed_rate_percent", "0.00001"), ("proposed_rate_percent", "abc"),
])
def test_invalid_inputs_return_422(field, value):
    response = client.post("/simulate", json={**VALID, field: value})
    assert response.status_code == 422


def test_missing_and_unknown_inputs_are_rejected():
    assert client.post("/simulate", json={"base_amount": "100"}).status_code == 422
    assert client.post("/simulate", json={**VALID, "company": "fixture"}).status_code == 422


@pytest.mark.parametrize("base,current,proposed,tax,difference", [
    ("0", "0", "100", "0.00", "0.00"),
    ("0.05", "0", "10", "0.01", "0.01"),
    ("100", "20", "10", "10.00", "-10.00"),
    ("1000000000000", "0", "100", "1000000000000.00", "1000000000000.00"),
])
def test_rounding_zero_decrease_and_upper_bound(base, current, proposed, tax, difference):
    result = client.post("/simulate", json={
        "base_amount": base, "current_rate_percent": current, "proposed_rate_percent": proposed,
    }).json()
    assert result["proposed"]["tax_amount"] == tax
    assert result["tax_difference"] == difference
