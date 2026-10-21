import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.knowledge_service import KnowledgeService, tokenize
from app.services.safety_validator import (
    safety_validator,
    STATUTORY_CHEMICAL_DISCLAIMER_BN,
    RICE_MODEL_BOUNDARY_WARNING_BN,
    INSUFFICIENT_EVIDENCE_NOTICE_BN
)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_tokenize():
    tokens = tokenize("ধানের ব্লাস্ট রোগ হলে কী করণীয়?")
    assert "ধানের" in tokens or "ব্লাস্ট" in tokens
    # Noise words like কী should be filtered
    assert "কী" not in tokens


def test_safety_validator_record_validation():
    # Record with chemical control permitted must include statutory disclaimer
    record_with_chemical = {
        "id": "TEST-01",
        "title_bn": "টেস্ট রোগ",
        "title_en": "Test Disease",
        "chemical_control_permitted": True,
        "source_org": "ICAR-NRRI",
        "source_url": "https://nrri.nic.in",
        "safety_notes_bn": "সাধারণ সতর্কতা।"
    }
    validated = safety_validator.validate_record_safety(record_with_chemical)
    assert validated["chemical_control_permitted"] is True
    assert STATUTORY_CHEMICAL_DISCLAIMER_BN in validated["safety_notes_bn"]

    # Record lacking complete provenance gets flagged as provisional
    record_no_url = {
        "id": "TEST-02",
        "title_bn": "টেস্ট",
        "chemical_control_permitted": False,
        "source_org": "Unknown",
        "source_url": ""
    }
    validated_no_url = safety_validator.validate_record_safety(record_no_url)
    assert validated_no_url["evidence_status"] == "provisional"


def test_safety_validator_rice_boundary_detection():
    # If a query attempts to diagnose rice via image model, boundary warning must trigger
    warnings = safety_validator.check_query_boundaries("ধানের পাতার ছবি দিয়ে রোগ শনাক্ত করুন", crop="rice")
    assert any(RICE_MODEL_BOUNDARY_WARNING_BN in w for w in warnings)

    # For tomato, rice boundary warning should NOT trigger
    warnings_tomato = safety_validator.check_query_boundaries("টমেটোর পাতা কোঁকড়ানো রোগ", crop="tomato")
    assert not any(RICE_MODEL_BOUNDARY_WARNING_BN in w for w in warnings_tomato)


def test_safety_validator_insufficient_evidence():
    response = safety_validator.build_insufficient_evidence_response("অজানা বিষাক্ত উদ্ভিদ", crop="unknown")
    assert response["has_sufficient_evidence"] is False
    assert INSUFFICIENT_EVIDENCE_NOTICE_BN in response["answer_bn"]
    assert len(response["records"]) == 0


def test_api_get_categories(client):
    response = client.get("/api/v1/knowledge/categories")
    assert response.status_code == 200
    data = response.json()
    assert data["total_records"] >= 10
    crops = [c["id"] for c in data["crops"]]
    assert "rice" in crops
    assert "potato" in crops
    assert "tomato" in crops
    assert "bell_pepper" in crops


def test_api_search_relevant_query(client):
    # Query for potato late blight in Bengali
    response = client.get("/api/v1/knowledge/search?query=আলুর নাবি ধসা রোগ")
    assert response.status_code == 200
    data = response.json()
    assert data["has_sufficient_evidence"] is True
    assert data["total_matches"] >= 1
    top = data["results"][0]
    assert "আলু" in top["title_bn"] or "নাবি ধসা" in top["title_bn"]
    assert top["source_org"] != ""
    assert top["source_url"].startswith("http")
    assert top["evidence_status"] == "verified"


def test_api_search_crop_filter(client):
    # Query for rice diseases specifically
    response = client.get("/api/v1/knowledge/search?query=ব্লাস্ট রোগ&crop=rice")
    assert response.status_code == 200
    data = response.json()
    assert data["has_sufficient_evidence"] is True
    for item in data["results"]:
        assert item["crop"] in ["rice", "all"]


def test_api_search_insufficient_evidence(client):
    # Completely unrelated or imaginary crop query
    response = client.get("/api/v1/knowledge/search?query=চাঁদের মাটিতে আপেল গাছের চাষ পদ্ধতি")
    assert response.status_code == 200
    data = response.json()
    assert data["has_sufficient_evidence"] is False
    assert data["total_matches"] == 0
    assert data["insufficient_evidence_notice_bn"] is not None


def test_api_get_record_by_id(client):
    response = client.get("/api/v1/knowledge/records/KB-RICE-001")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "KB-RICE-001"
    assert "ব্লাস্ট" in data["title_bn"]
    assert data["source_org"] == "ICAR-National Rice Research Institute (NRRI)"
    assert data["source_url"] != ""
    assert data["publication_date"] != ""
    assert data["last_verified_date"] != ""


def test_api_get_record_not_found(client):
    response = client.get("/api/v1/knowledge/records/KB-NONEXISTENT-999")
    assert response.status_code == 404
    assert "কোনো কৃষি নির্দেশিকা রেকর্ড পাওয়া যায়নি" in response.json()["detail"]


def test_api_ask_question_valid(client):
    payload = {
        "query": "টমেটোর পাতা কোঁকড়ানো ভাইরাসের লক্ষণ ও সাদা মাছি দমন কীভাবে করব?",
        "crop": "tomato"
    }
    response = client.post("/api/v1/knowledge/ask", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["has_sufficient_evidence"] is True
    assert "পাতা কোঁকড়ানো" in data["answer_bn"]
    assert "ICAR-Indian Institute of Vegetable Research" in data["source_org"]
    assert data["source_url"] != ""
    assert data["evidence_status"] == "verified"


def test_api_ask_question_rice_model_caveat(client):
    # Query asking to diagnose rice with model
    payload = {
        "query": "আমার ধানের জমিতে রোগ হয়েছে, ছবি দেখে মডেল দিয়ে শনাক্ত করুন",
        "crop": "rice"
    }
    response = client.post("/api/v1/knowledge/ask", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Boundary warning for rice model limitation must be present
    assert any(RICE_MODEL_BOUNDARY_WARNING_BN in w for w in data["safety_warnings"])
