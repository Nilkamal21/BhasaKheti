import pytest
import time
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.services.weather_service import WeatherService, get_wmo_description, degrees_to_cardinal_bn


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


MOCK_OPEN_METEO_RESPONSE = {
    "latitude": 22.57,
    "longitude": 88.36,
    "timezone": "Asia/Kolkata",
    "current": {
        "time": "2026-10-15T12:00",
        "interval": 900,
        "temperature_2m": 31.5,
        "relative_humidity_2m": 68,
        "apparent_temperature": 36.2,
        "precipitation": 0.0,
        "rain": 0.0,
        "weather_code": 1,
        "wind_speed_10m": 12.4,
        "wind_direction_10m": 180.0
    },
    "daily": {
        "time": ["2026-10-15", "2026-10-16", "2026-10-17", "2026-10-18", "2026-10-19"],
        "weather_code": [1, 2, 61, 80, 0],
        "temperature_2m_max": [33.0, 32.5, 30.0, 29.5, 31.0],
        "temperature_2m_min": [24.0, 24.5, 23.0, 22.5, 23.0],
        "precipitation_sum": [0.0, 1.2, 12.5, 6.0, 0.0],
        "precipitation_probability_max": [10, 35, 85, 60, 5],
        "wind_speed_10m_max": [15.0, 18.0, 28.0, 20.0, 12.0]
    }
}


def test_wmo_code_mapping():
    desc_clear = get_wmo_description(0)
    assert desc_clear["type"] == "clear"
    assert "পরিষ্কার" in desc_clear["bn"]

    desc_rain = get_wmo_description(63)
    assert desc_rain["type"] == "rain"
    assert "বৃষ্টি" in desc_rain["bn"]

    desc_unknown = get_wmo_description(999)
    assert desc_unknown["type"] == "unknown"


def test_degrees_to_cardinal_bn():
    assert degrees_to_cardinal_bn(0) == "উত্তর"
    assert degrees_to_cardinal_bn(90) == "পূর্ব"
    assert degrees_to_cardinal_bn(180) == "দক্ষিণ"
    assert degrees_to_cardinal_bn(270) == "পশ্চিম"


@pytest.mark.anyio
async def test_weather_service_normalization_and_caching():
    svc = WeatherService()
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_OPEN_METEO_RESPONSE
    mock_resp.raise_for_status.return_value = None

    with patch.object(svc, "get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_resp
        mock_get_client.return_value = mock_client

        res1 = await svc.get_forecast(22.57, 88.36, "Kolkata")
        assert res1["provider"] == "Open-Meteo"
        assert res1["is_cached"] is False
        assert res1["current_conditions"]["temperature_c"] == 31.5
        assert res1["current_conditions"]["wind_direction_bn"] == "দক্ষিণ"
        assert len(res1["daily_forecast"]) == 5
        assert "advisory_notes_bn" in res1["agricultural_advisory"]

        # Second call within TTL should return cached
        res2 = await svc.get_forecast(22.57, 88.36, "Kolkata")
        assert res2["is_cached"] is True
        assert res2["cached_age_seconds"] >= 0


def test_api_weather_forecast_valid(client):
    with patch("app.services.weather_service.weather_service.get_forecast") as mock_get:
        mock_get.return_value = {
            "provider": "Open-Meteo",
            "provider_terms": "Non-commercial Open-Meteo Free API",
            "location_name": "বর্ধমান (Bardhaman)",
            "latitude": 23.23,
            "longitude": 87.86,
            "timezone": "Asia/Kolkata",
            "retrieved_at_unix": int(time.time()),
            "is_cached": False,
            "is_stale": False,
            "cached_age_seconds": 0,
            "current_conditions": {
                "observation_time": "2026-10-15T12:00",
                "temperature_c": 30.2,
                "apparent_temperature_c": 34.5,
                "relative_humidity_pct": 72,
                "precipitation_mm": 0.0,
                "wind_speed_kmh": 10.5,
                "wind_direction_deg": 180.0,
                "wind_direction_bn": "দক্ষিণ",
                "weather_code": 1,
                "weather_desc_en": "Mainly clear",
                "weather_desc_bn": "প্রধানত পরিষ্কার",
                "weather_type": "partly_cloudy"
            },
            "daily_forecast": [
                {
                    "date": "2026-10-15",
                    "weather_code": 1,
                    "weather_desc_en": "Mainly clear",
                    "weather_desc_bn": "প্রধানত পরিষ্কার",
                    "weather_type": "partly_cloudy",
                    "temperature_max_c": 32.0,
                    "temperature_min_c": 23.0,
                    "precipitation_sum_mm": 0.0,
                    "precipitation_probability_pct": 10,
                    "wind_speed_max_kmh": 15.0
                }
            ],
            "agricultural_advisory": {
                "is_fieldwork_advisable": True,
                "advisory_notes_bn": ["আবহাওয়া শান্ত ও অনুকূল রয়েছে।"],
                "caution_notice_bn": "পূর্বাভাসে অনিশ্চয়তা থাকতে পারে।"
            }
        }
        
        response = client.get("/api/v1/weather/forecast?latitude=23.23&longitude=87.86&location_name=Bardhaman")
        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == "Open-Meteo"
        assert data["current_conditions"]["temperature_c"] == 30.2
        assert data["agricultural_advisory"]["is_fieldwork_advisable"] is True


def test_api_weather_forecast_invalid_coords(client):
    response = client.get("/api/v1/weather/forecast?latitude=150.0&longitude=88.0")
    assert response.status_code == 422  # Pydantic Query le=90 validation


def test_api_weather_search(client):
    with patch("app.services.weather_service.weather_service.search_locations") as mock_search:
        mock_search.return_value = [
            {
                "name": "Kolkata",
                "admin1": "West Bengal",
                "country": "India",
                "display_label": "Kolkata, West Bengal",
                "latitude": 22.5726,
                "longitude": 88.3639
            }
        ]
        response = client.get("/api/v1/weather/search?query=Kolkata")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Kolkata"


# Genuine live integration test with actual Open-Meteo API
def test_live_open_meteo_integration():
    import urllib.request
    import json
    url = "https://api.open-meteo.com/v1/forecast?latitude=22.57&longitude=88.36&current=temperature_2m,relative_humidity_2m&daily=weather_code,temperature_2m_max&timezone=Asia%2FKolkata&forecast_days=3"
    req = urllib.request.Request(url, headers={"User-Agent": "BhasaKheti-Test/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert "current" in data
        assert "temperature_2m" in data["current"]
        assert "daily" in data
