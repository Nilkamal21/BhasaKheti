"""
Unit and API tests for Phase 7 Market Intelligence.
"""

from fastapi.testclient import TestClient
from app.main import app
from app.services.market_service import market_service, DISCLAIMER_FARM_GATE_BN

client = TestClient(app)


def test_market_service_get_commodities():
    """Verify distinct commodities are returned with Bengali and English names."""
    commodities = market_service.get_commodities()
    assert len(commodities) >= 5
    ids = [c["id"] for c in commodities]
    assert "paddy_common" in ids
    assert "potato_jyoti" in ids
    for c in commodities:
        assert "name_bn" in c
        assert "name_en" in c


def test_market_service_get_districts():
    """Verify reporting districts in West Bengal are correctly populated."""
    districts = market_service.get_districts()
    assert len(districts) >= 5
    d_ens = [d["district_en"] for d in districts]
    assert "Purba Bardhaman" in d_ens
    assert "Hooghly" in d_ens
    assert "Darjeeling" in d_ens


def test_market_price_search_by_commodity():
    """Test price retrieval for paddy across mandis."""
    res = market_service.search_prices(commodity="paddy_common")
    assert res["total_matches"] >= 1
    for p in res["prices"]:
        assert p["commodity_id"] == "paddy_common"
        assert p["min_price"] <= p["modal_price"] <= p["max_price"]
        assert p["modal_price_per_kg"] == round(p["modal_price"] / 100.0, 2)
        assert "₹/Quintal" in p["unit"] or "কুইন্টাল" in p["unit"]
        assert p["source_url"] == "https://agmarknet.gov.in"


def test_market_price_search_by_district():
    """Test price retrieval for a specific West Bengal district."""
    res = market_service.search_prices(district="Purba Bardhaman")
    assert res["total_matches"] >= 2
    for p in res["prices"]:
        assert p["district_en"] == "Purba Bardhaman"


def test_market_unit_conversion_accuracy():
    """Verify conversion from ₹/Quintal to ₹/kg is mathematically correct."""
    res = market_service.search_prices(commodity="potato_jyoti")
    assert res["total_matches"] >= 1
    sample = res["prices"][0]
    expected_kg = round(sample["modal_price"] / 100.0, 2)
    assert sample["modal_price_per_kg"] == expected_kg


def test_market_historical_data_flag():
    """Verify historical prices older than threshold are flagged accurately."""
    res = market_service.search_prices(commodity="potato_chandramukhi")
    assert res["total_matches"] >= 1
    hist_record = res["prices"][0]
    assert hist_record["is_historical"] is True
    assert hist_record["data_status"] == "historical"


def test_market_farm_gate_disclaimer():
    """Verify educational disclaimer distinguishing mandi and farm-gate price is present."""
    res = market_service.search_prices(commodity="tomato")
    assert len(res["disclaimers"]) >= 1
    assert any("Farm-gate" in d or "খামারে" in d for d in res["disclaimers"])


def test_market_summary_endpoint():
    """Verify market summary returns highlights for staple crops."""
    response = client.get("/api/v1/market/summary")
    assert response.status_code == 200
    data = response.json()
    assert "summary_highlights" in data
    assert len(data["summary_highlights"]) >= 3
    crop_ids = [c["commodity_id"] for c in data["summary_highlights"]]
    assert "paddy_common" in crop_ids
    assert "disclaimer_bn" in data


def test_market_prices_api_endpoint():
    """Verify GET /api/v1/market/prices handles queries and pagination."""
    response = client.get("/api/v1/market/prices?commodity=jute&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "prices" in data
    assert len(data["prices"]) >= 1
    assert data["prices"][0]["commodity_id"] == "jute"
    assert data["data_source"] is not None


def test_market_empty_search_no_fabrication():
    """Verify non-existent search returns 0 results gracefully without inventing prices."""
    res = market_service.search_prices(query="xyznonexistentcrop12345")
    assert res["total_matches"] == 0
    assert len(res["prices"]) == 0
