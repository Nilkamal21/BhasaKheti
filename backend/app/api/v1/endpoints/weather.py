from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from app.services.weather_service import weather_service
from app.core.logging import logger

router = APIRouter()


class CurrentConditions(BaseModel):
    observation_time: Optional[str]
    temperature_c: Optional[float]
    apparent_temperature_c: Optional[float]
    relative_humidity_pct: Optional[int]
    precipitation_mm: float
    wind_speed_kmh: Optional[float]
    wind_direction_deg: Optional[float]
    wind_direction_bn: str
    weather_code: Optional[int]
    weather_desc_en: str
    weather_desc_bn: str
    weather_type: str


class DailyForecastItem(BaseModel):
    date: str
    weather_code: Optional[int]
    weather_desc_en: str
    weather_desc_bn: str
    weather_type: str
    temperature_max_c: Optional[float]
    temperature_min_c: Optional[float]
    precipitation_sum_mm: float
    precipitation_probability_pct: int
    wind_speed_max_kmh: Optional[float]


class AgriculturalAdvisory(BaseModel):
    is_fieldwork_advisable: bool
    advisory_notes_bn: List[str]
    caution_notice_bn: str


class WeatherForecastResponse(BaseModel):
    provider: str
    provider_terms: str
    location_name: str
    latitude: float
    longitude: float
    timezone: str
    retrieved_at_unix: int
    is_cached: bool
    is_stale: bool
    cached_age_seconds: int
    stale_warning_bn: Optional[str] = None
    current_conditions: CurrentConditions
    daily_forecast: List[DailyForecastItem]
    agricultural_advisory: AgriculturalAdvisory


class LocationSearchResult(BaseModel):
    name: str
    admin1: str
    country: str
    display_label: str
    latitude: float
    longitude: float


@router.get(
    "/forecast",
    response_model=WeatherForecastResponse,
    summary="Get weather forecast and agricultural advisory",
    description="Fetches current weather observations and 5-day daily forecast from Open-Meteo with caching and agricultural field rules.",
)
async def get_weather_forecast(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees"),
    location_name: Optional[str] = Query("চিহ্নিত স্থান", description="Human-readable location title")
):
    try:
        data = await weather_service.get_forecast(
            latitude=latitude,
            longitude=longitude,
            location_name=location_name or "চিহ্নিত স্থান"
        )
        return data
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except TimeoutError as te:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(te)
        )
    except Exception as exc:
        logger.error(f"Weather endpoint error: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"আবহাওয়া তথ্য প্রাপ্তিতে ত্রুটি: {str(exc)}"
        )


@router.get(
    "/search",
    response_model=List[LocationSearchResult],
    summary="Search locations for weather forecasts",
    description="Searches towns and districts using Open-Meteo Geocoding.",
)
async def search_locations(
    query: str = Query(..., min_length=2, description="Town or district search keyword")
):
    try:
        results = await weather_service.search_locations(query)
        return results
    except Exception as exc:
        logger.error(f"Geocoding endpoint error: {exc}")
        return []
