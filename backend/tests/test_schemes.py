"""
Unit and API tests for Phase 7 Government Scheme Discovery.
"""

from fastapi.testclient import TestClient
from app.main import app
from app.services.scheme_service import scheme_service, PRELIMINARY_ASSESSMENT_NOTICE_BN

client = TestClient(app)


def test_scheme_service_get_categories():
    """Verify distinct categories are available with Bengali labels."""
    categories = scheme_service.get_categories()
    assert len(categories) >= 3
    cat_ids = [c["id"] for c in categories]
    assert "direct_financial_assistance" in cat_ids
    assert "crop_insurance" in cat_ids


def test_scheme_search_by_keyword():
    """Verify search returns matching schemes for Krishak Bandhu."""
    res = scheme_service.get_schemes(query="কৃষক বন্ধু")
    assert res["total_matches"] >= 1
    matched_ids = [s["id"] for s in res["schemes"]]
    assert "SCHEME-WB-001" in matched_ids
    kb_scheme = res["schemes"][0]
    assert "₹১০,০০০" in kb_scheme["benefits_bn"]
    assert "https://krishakbandhu.wb.gov.in" in kb_scheme["official_portal_url"]


def test_scheme_filter_by_sponsor():
    """Verify filtering by state and central government sponsors."""
    state_res = scheme_service.get_schemes(sponsor="state")
    assert state_res["total_matches"] >= 3
    for s in state_res["schemes"]:
        assert s["sponsor"] == "state"

    central_res = scheme_service.get_schemes(sponsor="central")
    assert central_res["total_matches"] >= 2
    for s in central_res["schemes"]:
        assert s["sponsor"] == "central"


def test_scheme_filter_by_category():
    """Verify filtering by crop insurance category."""
    res = scheme_service.get_schemes(category="crop_insurance")
    assert res["total_matches"] >= 1
    assert res["schemes"][0]["id"] == "SCHEME-WB-002"
    assert "বাংলা শস্য বিমা" in res["schemes"][0]["name_bn"]


def test_get_scheme_by_id_success():
    """Verify detailed retrieval of a scheme by ID."""
    scheme = scheme_service.get_scheme_by_id("SCHEME-WB-001")
    assert scheme is not None
    assert scheme["name_en"] == "Krishak Bandhu (Natun) Scheme"
    assert len(scheme["required_documents_bn"]) >= 3
    assert scheme["status"] == "current"


def test_get_scheme_by_id_not_found():
    """Verify 404 response for non-existent scheme ID."""
    response = client.get("/api/v1/schemes/INVALID_SCHEME_XYZ")
    assert response.status_code == 404
    assert "খুঁজে পাওয়া যায়নি" in response.json()["detail"]


def test_check_preliminary_eligibility_privacy():
    """Verify eligibility assessment returns matching schemes without asking for private data."""
    res = scheme_service.check_preliminary_eligibility(
        land_size_acres=1.5,
        is_sharecropper=False,
        is_owner=True
    )
    assert res["total_matched"] >= 3
    assert "privacy_statement" in res
    assert "আধার" in res["privacy_statement"]
    assert PRELIMINARY_ASSESSMENT_NOTICE_BN in res["statutory_notice"]


def test_check_preliminary_eligibility_sharecropper():
    """Verify sharecroppers get matched to schemes explicitly supporting bargadars."""
    res = scheme_service.check_preliminary_eligibility(
        is_sharecropper=True,
        is_owner=False
    )
    assert res["total_matched"] >= 2
    matched_ids = [m["scheme_id"] for m in res["matched_schemes"]]
    assert "SCHEME-WB-001" in matched_ids  # Krishak Bandhu supports bargadars
    assert "SCHEME-WB-002" in matched_ids  # BSB supports bargadars


def test_schemes_api_endpoints():
    """Verify API endpoints for categories, search, and eligibility."""
    # Categories
    cat_resp = client.get("/api/v1/schemes/categories")
    assert cat_resp.status_code == 200
    assert len(cat_resp.json()) >= 3

    # Search
    search_resp = client.get("/api/v1/schemes?q=বিমা")
    assert search_resp.status_code == 200
    assert search_resp.json()["total_matches"] >= 1

    # Detail
    detail_resp = client.get("/api/v1/schemes/SCHEME-CEN-001")
    assert detail_resp.status_code == 200
    assert "Kisan" in detail_resp.json()["name_en"]
    assert "PM-KISAN" in detail_resp.json()["name_bn"]

    # Eligibility POST
    elig_resp = client.post(
        "/api/v1/schemes/check-eligibility",
        json={"land_size_acres": 2.0, "is_sharecropper": False, "is_owner": True}
    )
    assert elig_resp.status_code == 200
    assert elig_resp.json()["total_matched"] >= 2
