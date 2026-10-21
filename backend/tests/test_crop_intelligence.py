import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.crop_intelligence_service import CropIntelligenceService
from app.services.safety_validator import (
    RICE_MODEL_BOUNDARY_WARNING_BN,
    STATUTORY_CHEMICAL_DISCLAIMER_BN
)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_intent_and_context_extraction():
    svc = CropIntelligenceService()

    # Fertilizer without crop should detect missing context
    res1 = svc.analyze_intent_and_context("জমিতে কী সার প্রয়োগ করব?")
    assert res1["intent"] == "fertilizer_soil"
    assert "crop_name" in res1["missing_context"]
    assert res1["clarification_prompt_bn"] is not None

    # Irrigation query should detect irrigation intent
    res2 = svc.analyze_intent_and_context("আজ কি ধান জমিতে সেচ দেব?")
    assert res2["intent"] == "irrigation_weather"
    assert res2["crop"] == "rice"


@pytest.mark.anyio
async def test_irrigation_weather_integration():
    svc = CropIntelligenceService()

    # Mock weather where rain is expected
    mock_weather = {
        "available": True,
        "current_temp_c": 28.5,
        "current_humidity": 85,
        "current_rain_mm": 2.0,
        "weather_desc_bn": "হালকা বৃষ্টি",
        "rain_next_48h_mm": 18.0,
        "max_rain_probability_48h": 85,
        "advisory_notes_bn": ["ভারী বৃষ্টির সম্ভাবনা"]
    }

    with patch.object(svc, "get_weather_context", return_value=mock_weather):
        with patch.object(svc.llm, "is_available", return_value=False):
            res = await svc.orchestrate(query="আজ আলু জমিতে সেচ দেব কি?", crop="potato")
            assert res["intent"] == "irrigation_weather"
            assert res["weather_summary"] is not None
            # Must warn to withhold irrigation due to rain forecast
            assert any(term in res["answer_bn"] for term in ["সেচ দেওয়া বন্ধ রাখুন", "বিরত", "বৃষ্টি"])


@pytest.mark.anyio
async def test_rice_disease_boundary_safety():
    svc = CropIntelligenceService()
    # Question asking to diagnose rice with model
    res = await svc.orchestrate(query="ধান গাছের ছবি দেখে রোগ শনাক্ত করুন", crop="rice")
    assert any(RICE_MODEL_BOUNDARY_WARNING_BN in w for w in res["safety_warnings"])


@pytest.mark.anyio
async def test_cohere_llm_generation_mock():
    svc = CropIntelligenceService()

    mock_llm_response = {
        "text": "ধানের ব্লাস্ট রোগ প্রতিরোধে সুষম সার প্রয়োগ করুন। নাইট্রোজেন অতিরিক্ত দেবেন না।",
        "provider": "cohere",
        "model": "command-r-08-2024",
        "is_fallback": False,
        "tokens_used": 65
    }

    with patch.object(svc.llm, "is_available", return_value=True), \
         patch.object(svc.llm, "generate_grounded_response", return_value=mock_llm_response):
        res = await svc.orchestrate(query="ধানের ব্লাস্ট রোগের প্রতিকার কী?", crop="rice")
        assert res["llm_used"] is True
        assert res["provider"] == "Cohere"
        assert "ব্লাস্ট" in res["answer_bn"]
        assert len(res["citations"]) > 0


@pytest.mark.anyio
async def test_deterministic_fallback_when_cohere_not_configured():
    svc = CropIntelligenceService()

    with patch.object(svc.llm, "is_available", return_value=False):
        res = await svc.orchestrate(query="আলুর নাবি ধসা রোগ ব্যবস্থাপনা কী?", crop="potato")
        assert res["llm_used"] is False
        assert res["provider"] == "deterministic_fallback"
        assert "নাবি ধসা" in res["answer_bn"]
        assert len(res["citations"]) > 0


def test_api_ask_crop_intelligence_endpoint(client):
    response = client.post(
        "/api/v1/intelligence/ask",
        data={"query": "টমেটোর পাতা কোঁকড়ানো রোগের ক্ষেত্রে কী করব?", "crop": "tomato"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "answer_bn" in data
    assert data["intent"] in ["plant_health", "general_guidance"]
    assert "citations" in data


@pytest.mark.anyio
async def test_market_query_orchestration():
    svc = CropIntelligenceService()
    with patch.object(svc.llm, "is_available", return_value=False):
        res = await svc.orchestrate(query="আজ বর্ধমানে ধানের বাজারদর কত?", crop="rice")
        assert res["intent"] == "market_intelligence"
        assert "বাজারদর" in res["answer_bn"]
        assert any(c["source_org"] == "AGMARKNET - Directorate of Marketing & Inspection (DMI)" for c in res["citations"])


@pytest.mark.anyio
async def test_scheme_query_orchestration():
    svc = CropIntelligenceService()
    with patch.object(svc.llm, "is_available", return_value=False):
        res = await svc.orchestrate(query="কৃষক বন্ধু প্রকল্পে কত টাকা পাওয়া যায়?")
        assert res["intent"] == "government_schemes"
        assert "কৃষক বন্ধু" in res["answer_bn"]
        assert any("krishakbandhu" in c["source_url"] for c in res["citations"])

