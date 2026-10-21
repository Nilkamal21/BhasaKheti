"""
Tool definitions and registry for BhashaKheti Multi-Agent Supervisor.
Wraps all existing Phase 1-8 ML models and services as callable tools
with strict parameter validation, crop applicability checks, and structured outputs.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.core.logging import logger
from app.services.disease_service import disease_model_service
from app.services.soil_type_service import soil_type_service
from app.services.soil_moisture_service import soil_moisture_service
from app.services.weather_service import weather_service
from app.services.knowledge_service import knowledge_service
from app.services.market_service import market_service
from app.services.scheme_service import scheme_service
from app.services.safety_validator import (
    safety_validator,
    RICE_MODEL_BOUNDARY_WARNING_BN,
    SOIL_MODEL_BOUNDARY_DISCLAIMER_BN,
    MOISTURE_MODEL_BOUNDARY_DISCLAIMER_BN,
    STATUTORY_CHEMICAL_DISCLAIMER_BN
)


# Supported disease model crops
DISEASE_SUPPORTED_CROPS = {"tomato", "potato", "bell_pepper"}


class ToolResult(BaseModel):
    tool_name: str
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None
    disclaimer_bn: Optional[str] = None
    citations: List[Dict[str, Any]] = Field(default_factory=list)


class AgentToolRegistry:
    """Central registry and executor of specialized tools."""

    @staticmethod
    def predict_plant_disease(image_bytes: bytes, crop: Optional[str] = None) -> ToolResult:
        """
        Crop Health Agent Tool:
        Runs MobileNetV2 PyTorch disease model on leaf image.
        Strict boundary: Only runs if crop is None, unknown, or in tomato/potato/bell_pepper.
        Explicitly rejects rice and other unsupported crops.
        """
        if crop and crop.lower() == "rice":
            return ToolResult(
                tool_name="predict_plant_disease",
                success=False,
                data={"supported": False, "crop": "rice"},
                error="রোগ শনাক্তকরণ মডেলটি ধানের ক্ষেত্রে প্রযোজ্য নয়।",
                disclaimer_bn=RICE_MODEL_BOUNDARY_WARNING_BN
            )

        if not image_bytes or len(image_bytes) == 0:
            return ToolResult(
                tool_name="predict_plant_disease",
                success=False,
                data={},
                error="কোনো পাতার ছবি পাওয়া যায়নি।"
            )

        try:
            pred = disease_model_service.predict(image_bytes)
            primary = pred.get("primary_prediction", {})
            return ToolResult(
                tool_name="predict_plant_disease",
                success=True,
                data=pred,
                disclaimer_bn=pred.get("warning") or STATUTORY_CHEMICAL_DISCLAIMER_BN
            )
        except Exception as e:
            logger.error(f"Error in predict_plant_disease tool: {e}")
            return ToolResult(
                tool_name="predict_plant_disease",
                success=False,
                data={},
                error=f"পাতা বিশ্লেষণ ত্রুটি: {str(e)}"
            )

    @staticmethod
    def predict_soil_type(image_bytes: bytes) -> ToolResult:
        """
        Soil Agent Tool:
        Runs MobileNetV2 LiteRT 7-class soil type classifier.
        Honest disclaimer: Superficial visual classification only; does not replace laboratory Soil Health Card.
        """
        if not image_bytes or len(image_bytes) == 0:
            return ToolResult(
                tool_name="predict_soil_type",
                success=False,
                data={},
                error="কোনো মাটির ছবি পাওয়া যায়নি।"
            )

        try:
            pred = soil_type_service.predict(image_bytes)
            return ToolResult(
                tool_name="predict_soil_type",
                success=True,
                data=pred,
                disclaimer_bn=SOIL_MODEL_BOUNDARY_DISCLAIMER_BN
            )
        except Exception as e:
            logger.error(f"Error in predict_soil_type tool: {e}")
            return ToolResult(
                tool_name="predict_soil_type",
                success=False,
                data={},
                error=f"মাটির ধরন বিশ্লেষণ ত্রুটি: {str(e)}"
            )

    @staticmethod
    def predict_soil_moisture(image_bytes: bytes) -> ToolResult:
        """
        Soil Agent Tool:
        Runs MobileNetV2 LiteRT 2-class soil moisture classifier.
        Honest disclaimer: Topsoil appearance only; does not measure root-zone moisture or replace tensiometer.
        """
        if not image_bytes or len(image_bytes) == 0:
            return ToolResult(
                tool_name="predict_soil_moisture",
                success=False,
                data={},
                error="কোনো মাটির ছবি পাওয়া যায়নি।"
            )

        try:
            pred = soil_moisture_service.predict(image_bytes)
            return ToolResult(
                tool_name="predict_soil_moisture",
                success=True,
                data=pred,
                disclaimer_bn=MOISTURE_MODEL_BOUNDARY_DISCLAIMER_BN
            )
        except Exception as e:
            logger.error(f"Error in predict_soil_moisture tool: {e}")
            return ToolResult(
                tool_name="predict_soil_moisture",
                success=False,
                data={},
                error=f"মাটির আর্দ্রতা বিশ্লেষণ ত্রুটি: {str(e)}"
            )

    @staticmethod
    async def get_weather(latitude: float = 23.23, longitude: float = 87.86) -> ToolResult:
        """
        Weather Agent Tool:
        Calls Open-Meteo for live conditions and 5-day forecast.
        Computes 48-hour rainfall volume and probability to prevent overwatering.
        """
        try:
            res = await weather_service.get_forecast(latitude=latitude, longitude=longitude)
            curr = res.get("current_conditions", {})
            daily = res.get("daily_forecast", [])

            rain_next_48h_mm = 0.0
            max_prob_48h = 0
            if len(daily) >= 2:
                rain_next_48h_mm = (daily[0].get("precipitation_sum_mm") or 0.0) + (daily[1].get("precipitation_sum_mm") or 0.0)
                max_prob_48h = max(daily[0].get("precipitation_probability_pct") or 0, daily[1].get("precipitation_probability_pct") or 0)

            summary = {
                "location_name": res.get("location_name"),
                "current_temp_c": curr.get("temperature_c"),
                "current_humidity": curr.get("relative_humidity_pct"),
                "weather_desc_bn": curr.get("weather_desc_bn"),
                "rain_next_48h_mm": round(rain_next_48h_mm, 1),
                "max_rain_probability_48h": max_prob_48h,
                "advisory_notes_bn": res.get("agricultural_advisory", {}).get("advisory_notes_bn", [])
            }

            return ToolResult(
                tool_name="get_weather",
                success=True,
                data=summary,
                citations=[{
                    "id": "SRC-WEATHER-OPENMETEO",
                    "source_org": "Open-Meteo (IMD-aligned)",
                    "source_url": "https://open-meteo.com"
                }]
            )
        except Exception as e:
            logger.error(f"Error in get_weather tool: {e}")
            return ToolResult(
                tool_name="get_weather",
                success=False,
                data={},
                error=f"আবহাওয়া উপাত্ত সংগ্রহে ত্রুটি: {str(e)}"
            )

    @staticmethod
    def retrieve_agricultural_knowledge(query: str, crop: Optional[str] = None, limit: int = 3) -> ToolResult:
        """
        Agricultural Knowledge Agent Tool:
        Retrieves verified ICAR / KVK knowledge records with safety boundary warnings.
        """
        try:
            res = knowledge_service.search(query=query, crop=crop, limit=limit)
            docs = res.get("results", [])
            citations = [
                {
                    "id": d.get("id"),
                    "title_bn": d.get("title_bn"),
                    "source_org": d.get("source_org"),
                    "source_url": d.get("source_url")
                }
                for d in docs
            ]
            return ToolResult(
                tool_name="retrieve_agricultural_knowledge",
                success=True,
                data={"results": docs, "total_matches": res.get("total_matches", 0)},
                citations=citations,
                disclaimer_bn=STATUTORY_CHEMICAL_DISCLAIMER_BN
            )
        except Exception as e:
            logger.error(f"Error in retrieve_agricultural_knowledge tool: {e}")
            return ToolResult(
                tool_name="retrieve_agricultural_knowledge",
                success=False,
                data={},
                error=f"কৃষি জ্ঞানভাণ্ডার অনুসন্ধানে ত্রুটি: {str(e)}"
            )

    @staticmethod
    def search_market_prices(commodity: Optional[str] = None, district: Optional[str] = None, query: Optional[str] = None, limit: int = 3) -> ToolResult:
        """
        Market Agent Tool:
        Searches AGMARKNET mandi prices in West Bengal.
        Preserves modal price, per-kg price, date, and farm-gate notice.
        """
        try:
            res = market_service.search_prices(commodity=commodity, district=district, query=query, limit=limit)
            prices = res.get("prices", [])
            citations = [{
                "id": "SRC-MKT-AGMARKNET",
                "source_org": "AGMARKNET (agmarknet.gov.in)",
                "source_url": "https://agmarknet.gov.in"
            }]
            return ToolResult(
                tool_name="search_market_prices",
                success=True,
                data={"prices": prices, "total_matches": res.get("total_matches", 0)},
                citations=citations,
                disclaimer_bn=res.get("disclaimers", [None])[0]
            )
        except Exception as e:
            logger.error(f"Error in search_market_prices tool: {e}")
            return ToolResult(
                tool_name="search_market_prices",
                success=False,
                data={},
                error=f"বাজারদর অনুসন্ধানে ত্রুটি: {str(e)}"
            )

    @staticmethod
    def search_government_schemes(query: Optional[str] = None, category: Optional[str] = None, limit: int = 3) -> ToolResult:
        """
        Government Scheme Agent Tool:
        Retrieves official West Bengal & Central agricultural schemes.
        Preserves verified benefits, document criteria, and official portals.
        """
        try:
            res = scheme_service.get_schemes(query=query, category=category, limit=limit)
            schemes = res.get("schemes", [])
            citations = [
                {
                    "id": s.get("id"),
                    "title_bn": s.get("name_bn"),
                    "source_org": s.get("authority_bn"),
                    "source_url": s.get("official_portal_url")
                }
                for s in schemes
            ]
            return ToolResult(
                tool_name="search_government_schemes",
                success=True,
                data={"schemes": schemes, "total_matches": res.get("total_matches", 0)},
                citations=citations,
                disclaimer_bn="প্রকল্পের চূড়ান্ত যোগ্যতা ও সুবিধা সরকারি দপ্তর বা বাংলা সহায়তা কেন্দ্র (BSK) কর্তৃক অনুমোদনের ওপর নির্ভরশীল।"
            )
        except Exception as e:
            logger.error(f"Error in search_government_schemes tool: {e}")
            return ToolResult(
                tool_name="search_government_schemes",
                success=False,
                data={},
                error=f"সরকারি প্রকল্প অনুসন্ধানে ত্রুটি: {str(e)}"
            )


tool_registry = AgentToolRegistry()
