"""
Unit and integration tests for Phase 9 Supervisor-Based Multimodal Multi-Agent Architecture.
Tests:
1. Direct tool invocation without LLM call.
2. Deterministic routing for single-agent requests (market, schemes, weather, disease).
3. Selective LLM usage for multi-tool or follow-up requests.
4. Programmatic safety boundaries: Rice model rejection on leaf disease classifier.
5. Context preservation across multi-turn follow-ups.
6. Missing context follow-up generation.
7. Fallback behavior when LLM is unavailable.
8. API endpoint /api/v1/supervisor/chat validation.
"""

import io
from PIL import Image
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.supervisor_service import supervisor_service, ChatTurn
from app.services.agents.tool_registry import tool_registry

client = TestClient(app)


@pytest.mark.anyio
async def test_supervisor_deterministic_market_routing_bypasses_llm():
    """Verify market inquiries route directly to Market Agent without invoking LLM."""
    with patch.object(supervisor_service.llm, "generate_grounded_response") as mock_llm:
        res = await supervisor_service.plan_and_execute(query="আজ বর্ধমানে আলুর বাজারদর কত?")

        # Market tool must be invoked
        assert "search_market_prices" in res.tools_invoked
        assert res.intent == "market"
        assert res.detected_crop == "potato"
        assert "AGMARKNET" in res.answer_bn or "আলু" in res.answer_bn
        assert len(res.citations) >= 1
        # LLM must NOT be called for simple deterministic market query
        mock_llm.assert_not_called()
        assert res.llm_used is False


@pytest.mark.anyio
async def test_supervisor_deterministic_schemes_routing_bypasses_llm():
    """Verify scheme inquiries route directly to Government Scheme Agent without invoking LLM."""
    with patch.object(supervisor_service.llm, "generate_grounded_response") as mock_llm:
        res = await supervisor_service.plan_and_execute(query="পশ্চিমবঙ্গে কৃষক বন্ধু প্রকল্পে কত টাকা দেয়?")

        assert "search_government_schemes" in res.tools_invoked
        assert res.intent == "schemes"
        assert "কৃষক বন্ধু" in res.answer_bn
        assert len(res.citations) >= 1
        mock_llm.assert_not_called()
        assert res.llm_used is False


@pytest.mark.anyio
async def test_supervisor_rice_disease_boundary_safety():
    """Verify that rice leaf images strictly trigger boundary warning and do NOT invoke 15-class classifier."""
    fake_image_bytes = b"fake_leaf_image_bytes"

    res = await supervisor_service.plan_and_execute(
        query="আমার ধান গাছের পাতা হলুদ হয়ে যাচ্ছে, রোগ কী?",
        image_bytes=fake_image_bytes,
        crop="rice"
    )

    # Must NOT invoke predict_plant_disease for rice
    assert "predict_plant_disease" not in res.tools_invoked
    assert res.detected_crop == "rice"
    # Must enforce safety boundary warning
    assert any("ধানের রোগ শনাক্তকরণে এই মডেলটি কার্যকর নয়" in w for w in res.safety_warnings)


@pytest.mark.anyio
async def test_supervisor_irrigation_query_no_irrelevant_disease_warning():
    """Verify that asking about irrigating paddy fields does NOT trigger rice disease classifier warnings and gives simple clear answer."""
    res_en = await supervisor_service.plan_and_execute(
        query="Will I irrigate the paddy field today?"
    )
    assert res_en.intent == "irrigation_weather"
    assert "get_weather" in res_en.tools_invoked
    assert "predict_plant_disease" not in res_en.tools_invoked
    # Must NOT have irrelevant rice disease warning
    assert not any("ধানের রোগ শনাক্তকরণে এই মডেলটি কার্যকর নয়" in w for w in res_en.safety_warnings)
    # Must give simple, clear decision and touch-and-feel guidance
    assert ("You can irrigate" in res_en.answer_bn) or ("সেচ" in res_en.answer_bn)
    assert ("touch and feel" in res_en.answer_bn.lower()) or ("হাত দিয়ে" in res_en.answer_bn)

    # Test with attached image predicting wet soil
    from app.services.agents.tool_registry import ToolResult
    mock_wet_soil = ToolResult(
        tool_name="predict_soil_moisture",
        success=True,
        data={
            "primary_prediction": {
                "raw_class_name": "wet",
                "display_name_en": "Moist / Wet Soil Condition",
                "display_name_bn": "আর্দ্র / ভেজা মাটির অবস্থা",
                "model_score": 0.95
            }
        }
    )

    with patch.object(tool_registry, "predict_soil_moisture", return_value=mock_wet_soil):
        res_wet = await supervisor_service.plan_and_execute(
            query="Will I irrigate the paddy field today?",
            image_bytes=b"wet_soil_bytes"
        )
        assert res_wet.intent == "irrigation_weather"
        assert "predict_plant_disease" not in res_wet.tools_invoked
        assert not any("ধানের রোগ শনাক্তকরণে এই মডেলটি কার্যকর নয়" in w for w in res_wet.safety_warnings)
        # Wet soil must instruct NOT to irrigate and to touch and feel
        assert ("do not need to irrigate" in res_wet.answer_bn.lower()) or ("সেচ দেওয়ার প্রয়োজন নেই" in res_wet.answer_bn)
        assert ("touch and feel" in res_wet.answer_bn.lower()) or ("হাত দিয়ে" in res_wet.answer_bn)


@pytest.mark.anyio
async def test_supervisor_soil_image_tool_execution():
    """Verify that soil images invoke soil type and soil moisture tools and attach honest disclaimers."""
    # Create valid synthetic 224x224 RGB image bytes
    from PIL import Image
    import io
    img = Image.new("RGB", (224, 224), color=(120, 80, 50))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    soil_bytes = buf.getvalue()

    res = await supervisor_service.plan_and_execute(
        query="আমার জমির মাটির ধরন কেমন?",
        image_bytes=soil_bytes,
        image_type="soil"
    )

    assert "predict_soil_type" in res.tools_invoked
    assert "predict_soil_moisture" in res.tools_invoked
    assert any("মাটি পরীক্ষা (Soil Health Card)" in w for w in res.safety_warnings)
    assert any("শিকড়ের গভীরে প্রকৃত আর্দ্রতা" in w for w in res.safety_warnings)


@pytest.mark.anyio
async def test_supervisor_multi_tool_weather_and_knowledge():
    """Verify multi-tool coordination when farmer asks about rain and plant disease."""
    res = await supervisor_service.plan_and_execute(
        query="টমেটো গাছে বৃষ্টির কারণে কি পাতা ধসা হতে পারে?",
        crop="tomato"
    )

    assert "get_weather" in res.tools_invoked
    assert "retrieve_agricultural_knowledge" in res.tools_invoked
    assert res.detected_crop == "tomato"
    assert len(res.citations) >= 1


@pytest.mark.anyio
async def test_supervisor_multi_turn_context_and_follow_up():
    """Verify that conversation context preserves crop across turns for follow-ups like 'তাহলে এখন কী করব?'."""
    history = [
        ChatTurn(role="user", content="আমার ধান গাছের পাতা হলুদ হয়ে যাচ্ছে", detected_crop="rice"),
        ChatTurn(role="assistant", content="ধানের পাতায় নাইট্রোজেনের ঘাটতি হতে পারে।", detected_crop="rice")
    ]

    res = await supervisor_service.plan_and_execute(
        query="তাহলে এখন কী করব?",
        history=history
    )

    # Resolved crop from history
    assert res.detected_crop == "rice"
    assert "retrieve_agricultural_knowledge" in res.tools_invoked


@pytest.mark.anyio
async def test_supervisor_missing_context_generates_polite_follow_up():
    """Verify fertilizer query without crop generates a concise single follow-up prompt."""
    res = await supervisor_service.plan_and_execute(query="জমিতে সার কখন দেব?")

    assert res.follow_up_prompt_bn is not None
    assert "কোন ফসলে সার প্রয়োগের সঠিক নিয়ম জানতে চান" in res.follow_up_prompt_bn


def test_supervisor_api_endpoint_success():
    """Verify POST /api/v1/supervisor/chat returns 200 with structured response."""
    response = client.post(
        "/api/v1/supervisor/chat",
        data={"query": "আজ কি ধান জমিতে সেচ দেব?"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "answer_bn" in data
    assert "tools_invoked" in data
    assert "get_weather" in data["tools_invoked"]
    assert data["detected_crop"] == "rice"


def test_supervisor_api_endpoint_validation_error():
    """Verify POST /api/v1/supervisor/chat rejects empty query when no image is provided."""
    response = client.post(
        "/api/v1/supervisor/chat",
        data={"query": ""}
    )
    assert response.status_code == 400


@pytest.mark.anyio
async def test_supervisor_image_with_empty_or_generic_query():
    """Verify that uploading an image with empty query doesn't fail with NameError and invokes visual inspection."""
    img = Image.new("RGB", (128, 128), color="green")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    img_bytes = buf.getvalue()

    res = await supervisor_service.plan_and_execute(
        query="",
        image_bytes=img_bytes,
        image_type="auto"
    )

    assert "predict_plant_disease" in res.tools_invoked
    assert res.intent == "visual_inspection"
    assert res.answer_bn is not None

