"""
API integration tests using FastAPI TestClient.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check_endpoint():
    """Verify health check endpoint returns 200 and crypto info."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "RFC3526" in data["crypto_group"]


def test_exact_matching_api_endpoint():
    """Test POST /api/matching/exact with matching and non-matching elements."""
    payload = {
        "alice_data": ["Alice@domain.org", "Bob@domain.org", "Charlie@domain.org"],
        "bob_data": ["Bob@domain.org", "Charlie@domain.org", "David@domain.org"],
        "normalize": True,
    }
    response = client.post("/api/matching/exact", json=payload)
    assert response.status_code == 200
    result = response.json()

    assert set(result["matches"]) == {"bob@domain.org", "charlie@domain.org"}
    assert result["match_count"] == 2
    assert result["alice_dataset_size"] == 3
    assert result["bob_dataset_size"] == 3
    assert "2Hash-DH-OPRF-PSI" in result["protocol_name"]


def test_exact_matching_api_no_matches():
    """Test POST /api/matching/exact with completely disjoint inputs."""
    payload = {
        "alice_data": ["record_1", "record_2"],
        "bob_data": ["record_3", "record_4"],
        "normalize": True,
    }
    response = client.post("/api/matching/exact", json=payload)
    assert response.status_code == 200
    result = response.json()

    assert result["matches"] == []
    assert result["match_count"] == 0
    assert result["alice_dataset_size"] == 2
    assert result["bob_dataset_size"] == 2


def test_exact_matching_api_empty_payload():
    """Test POST /api/matching/exact with empty datasets."""
    payload = {
        "alice_data": [],
        "bob_data": [],
        "normalize": True,
    }
    response = client.post("/api/matching/exact", json=payload)
    assert response.status_code == 200
    result = response.json()

    assert result["matches"] == []
    assert result["match_count"] == 0


def test_fuzzy_matching_api_endpoint():
    """Test POST /api/matching/fuzzy with exact and approximate matches."""
    payload = {
        "alice_data": ["Madhav Kumar", "John Smith", "Rahul Sharma"],
        "bob_data": ["Madhav Kumer", "Alice Brown", "John Smith"],
        "threshold": 0.85,
        "normalize": True,
    }
    response = client.post("/api/matching/fuzzy", json=payload)
    assert response.status_code == 200
    result = response.json()

    assert result["match_count"] == 2
    assert result["alice_dataset_size"] == 3
    assert result["bob_dataset_size"] == 3
    assert result["threshold"] == 0.85

    # Check match pairs
    matches = result["matches"]
    pair_map = {(m["alice_record"], m["bob_record"]): m["similarity"] for m in matches}

    assert ("John Smith", "John Smith") in pair_map
    assert pair_map[("John Smith", "John Smith")] == 1.0

    assert ("Madhav Kumar", "Madhav Kumer") in pair_map
    assert pair_map[("Madhav Kumar", "Madhav Kumer")] > 0.90

    # Ensure non-matching items are NOT exposed
    all_output_names = [m["alice_record"] for m in matches] + [m["bob_record"] for m in matches]
    assert "Rahul Sharma" not in all_output_names
    assert "Alice Brown" not in all_output_names


def test_fuzzy_matching_api_empty_payload():
    """Test POST /api/matching/fuzzy with empty datasets."""
    payload = {
        "alice_data": [],
        "bob_data": [],
        "threshold": 0.85,
        "normalize": True,
    }
    response = client.post("/api/matching/fuzzy", json=payload)
    assert response.status_code == 200
    result = response.json()
    assert result["matches"] == []
    assert result["match_count"] == 0


def test_fuzzy_matching_api_invalid_threshold():
    """Test POST /api/matching/fuzzy with invalid threshold returns 422."""
    # Negative threshold
    resp_neg = client.post(
        "/api/matching/fuzzy",
        json={"alice_data": ["item"], "bob_data": ["item"], "threshold": -0.1},
    )
    assert resp_neg.status_code == 422

    # Threshold > 1.0
    resp_over = client.post(
        "/api/matching/fuzzy",
        json={"alice_data": ["item"], "bob_data": ["item"], "threshold": 1.5},
    )
    assert resp_over.status_code == 422


def test_threshold_crypto_api_endpoint():
    """Test POST /api/matching/threshold-crypto with exact and typo records."""
    payload = {
        "alice_data": ["Madhav Kumar", "John Smith", "Rahul Sharma"],
        "bob_data": ["Madhav Kumer", "Alice Brown", "John Smith"],
        "threshold": 0.80,
    }
    response = client.post("/api/matching/threshold-crypto", json=payload)
    assert response.status_code == 200
    result = response.json()

    assert result["match_count"] == 2
    assert result["alice_dataset_size"] == 3
    assert result["bob_dataset_size"] == 3
    assert result["threshold"] == 0.80
    assert "FuzzyCrypt" in result["protocol_name"]

    matches = result["matches"]
    pair_map = {(m["alice_record"], m["bob_record"]): (m["dice_similarity"], m["intersection_count"]) for m in matches}

    assert ("John Smith", "John Smith") in pair_map
    assert pair_map[("John Smith", "John Smith")][0] == 1.0

    assert ("Madhav Kumar", "Madhav Kumer") in pair_map
    assert pair_map[("Madhav Kumar", "Madhav Kumer")][0] == 0.84615
    assert pair_map[("Madhav Kumar", "Madhav Kumer")][1] == 11

    # Ensure non-matching items are NOT exposed
    all_names = [m["alice_record"] for m in matches] + [m["bob_record"] for m in matches]
    assert "Rahul Sharma" not in all_names
    assert "Alice Brown" not in all_names


def test_threshold_crypto_api_rejection_at_90():
    """Test POST /api/matching/threshold-crypto at threshold 0.90 rejects typo match."""
    payload = {
        "alice_data": ["Madhav Kumar"],
        "bob_data": ["Madhav Kumer"],
        "threshold": 0.90,
    }
    response = client.post("/api/matching/threshold-crypto", json=payload)
    assert response.status_code == 200
    result = response.json()
    assert result["match_count"] == 0
    assert result["matches"] == []


def test_threshold_crypto_api_empty_payload():
    """Test POST /api/matching/threshold-crypto with empty datasets."""
    payload = {
        "alice_data": [],
        "bob_data": [],
        "threshold": 0.80,
    }
    response = client.post("/api/matching/threshold-crypto", json=payload)
    assert response.status_code == 200
    result = response.json()
    assert result["match_count"] == 0
    assert result["matches"] == []


def test_threshold_crypto_api_invalid_threshold():
    """Test POST /api/matching/threshold-crypto with invalid threshold values returns 422."""
    # Threshold 0.0 (must be > 0.0)
    resp_zero = client.post(
        "/api/matching/threshold-crypto",
        json={"alice_data": ["item"], "bob_data": ["item"], "threshold": 0.0},
    )
    assert resp_zero.status_code == 422

    # Threshold > 1.0
    resp_high = client.post(
        "/api/matching/threshold-crypto",
        json={"alice_data": ["item"], "bob_data": ["item"], "threshold": 1.2},
    )
    assert resp_high.status_code == 422


