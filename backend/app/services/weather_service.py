import time
from typing import Dict, Any, List, Optional
import httpx
from app.core.config import settings
from app.core.logging import logger

# WMO Weather Interpretation Codes to Bengali & English labels and weather types
WMO_CODE_MAP = {
    0: {"en": "Clear sky", "bn": "পরিষ্কার আকাশ", "type": "clear"},
    1: {"en": "Mainly clear", "bn": "প্রধানত পরিষ্কার", "type": "partly_cloudy"},
    2: {"en": "Partly cloudy", "bn": "আংশিক মেঘলা", "type": "partly_cloudy"},
    3: {"en": "Overcast", "bn": "মেঘলা আকাশ", "type": "cloudy"},
    45: {"en": "Fog", "bn": "কুয়াশা", "type": "fog"},
    48: {"en": "Depositing rime fog", "bn": "ঘন কুয়াশা", "type": "fog"},
    51: {"en": "Light drizzle", "bn": "হালকা গুঁড়ি গুঁড়ি বৃষ্টি", "type": "drizzle"},
    53: {"en": "Moderate drizzle", "bn": "মাঝারি গুঁড়ি গুঁড়ি বৃষ্টি", "type": "drizzle"},
    55: {"en": "Dense drizzle", "bn": "ঘন গুঁড়ি গুঁড়ি বৃষ্টি", "type": "drizzle"},
    61: {"en": "Slight rain", "bn": "হালকা বৃষ্টি", "type": "rain"},
    63: {"en": "Moderate rain", "bn": "মাঝারি বৃষ্টি", "type": "rain"},
    65: {"en": "Heavy rain", "bn": "ভারী বৃষ্টি", "type": "heavy_rain"},
    71: {"en": "Slight snow fall", "bn": "হালকা তুষারপাত", "type": "snow"},
    73: {"en": "Moderate snow fall", "bn": "মাঝারি তুষারপাত", "type": "snow"},
    75: {"en": "Heavy snow fall", "bn": "ভারী তুষারপাত", "type": "snow"},
    80: {"en": "Slight rain showers", "bn": "হালকা বৃষ্টির ঝাপটা", "type": "rain"},
    81: {"en": "Moderate rain showers", "bn": "মাঝারি বৃষ্টির ঝাপটা", "type": "rain"},
    82: {"en": "Violent rain showers", "bn": "প্রবল বৃষ্টির ঝাপটা", "type": "heavy_rain"},
    95: {"en": "Thunderstorm", "bn": "বজ্রবিদ্যুৎসহ ঝড়-বৃষ্টি", "type": "thunderstorm"},
    96: {"en": "Thunderstorm with slight hail", "bn": "শিলাবৃষ্টিসহ বজ্রঝড়", "type": "thunderstorm"},
    99: {"en": "Thunderstorm with heavy hail", "bn": "ভারী শিলাবৃষ্টিসহ প্রবল বজ্রঝড়", "type": "thunderstorm"},
}

def get_wmo_description(code: Optional[int]) -> Dict[str, str]:
    if code is None or code not in WMO_CODE_MAP:
        return {"en": "Unknown weather condition", "bn": "অজানা আবহাওয়া", "type": "unknown"}
    return WMO_CODE_MAP[code]

def degrees_to_cardinal_bn(deg: Optional[float]) -> str:
    if deg is None:
        return "অজানা"
    val = int((deg / 22.5) + 0.5) % 16
    bn_directions = [
        "উত্তর", "উত্তর-উত্তর-পূর্ব", "উত্তর-পূর্ব", "পূর্ব-উত্তর-পূর্ব",
        "পূর্ব", "পূর্ব-দক্ষিণ-পূর্ব", "দক্ষিণ-পূর্ব", "দক্ষিণ-দক্ষিণ-পূর্ব",
        "দক্ষিণ", "দক্ষিণ-দক্ষিণ-পশ্চিম", "দক্ষিণ-পশ্চিম", "পশ্চিম-দক্ষিণ-পশ্চিম",
        "পশ্চিম", "পশ্চিম-উত্তর-পশ্চিম", "উত্তর-পশ্চিম", "উত্তর-উত্তর-পশ্চিম"
    ]
    return bn_directions[val]


class WeatherService:
    """Dedicated service for weather forecast & geocoding via Open-Meteo API.
    
    Features:
    - Coordinate validation (-90 to 90, -180 to 180).
    - Sensible network timeout (8.0s).
    - In-memory cache with explicit freshness and TTL (15 mins).
    - Conservative, evidence-backed rule-based agricultural advisory (no LLMs).
    - Preserves data provenance (Open-Meteo, WMO codes, ISO timestamps).
    """

    def __init__(self):
        # In-memory cache structure: key -> { "timestamp": float, "data": dict }
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=settings.WEATHER_REQUEST_TIMEOUT_SECONDS,
                headers={"User-Agent": "BhasaKheti-AgriApp/1.0"}
            )
        return self._client

    def _cache_key(self, lat: float, lon: float) -> str:
        return f"{round(lat, 3)}:{round(lon, 3)}"

    def _generate_advisory(self, current: Dict[str, Any], daily: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate transparent, conservative agricultural advisory based strictly on forecast metrics."""
        notices: List[str] = []
        is_fieldwork_advisable = True

        precip_current = current.get("precipitation_mm", 0.0)
        wind_speed_current = current.get("wind_speed_kmh", 0.0)
        
        # Check today and tomorrow's forecast
        today_rain_prob = daily[0].get("precipitation_probability_pct", 0) if len(daily) > 0 else 0
        today_rain_sum = daily[0].get("precipitation_sum_mm", 0.0) if len(daily) > 0 else 0.0
        today_wind_max = daily[0].get("wind_speed_max_kmh", 0.0) if len(daily) > 0 else 0.0

        if precip_current > 0.5 or today_rain_sum >= 5.0 or today_rain_prob >= 70:
            notices.append("আজ বৃষ্টিপাতের সম্ভাবনা রয়েছে। জমিতে কীটনাশক বা সারের তরল স্প্রে করা স্থগিত রাখুন, অন্যথায় বৃষ্টির জলে তা ধুয়ে যেতে পারে।")
            is_fieldwork_advisable = False
        elif today_rain_prob >= 40:
            notices.append("মাঝারি বৃষ্টির সম্ভাবনা (৪০%-৭০%)। সংবেদনশীল ফসল কাটার কাজ বা খোলা মাঠে শুকানোর পূর্বে স্থানীয় আকাশ পর্যবেক্ষণ করুন।")

        if wind_speed_current >= 25.0 or today_wind_max >= 35.0:
            notices.append(f"বাতাসের বেগ বেশি ({wind_speed_current} কিমি/ঘণ্টা)। বাতাসের কারণে স্প্রে উপাদান বাতাসে ভেসে অপচয় হতে পারে এবং লম্বা ফসলে ক্ষতির আশঙ্কা থাকে।")
            is_fieldwork_advisable = False

        if not notices:
            notices.append("আবহাওয়া শান্ত ও অনুকূল রয়েছে। সাধারণ সেচ ও পরিচর্যা কাজ চালিয়ে যেতে পারেন।")

        return {
            "is_fieldwork_advisable": is_fieldwork_advisable,
            "advisory_notes_bn": notices,
            "caution_notice_bn": "আবহাওয়ার পূর্বাভাস একটি পরিসংখ্যানগত ধারণা এবং এতে অনিশ্চয়তা থাকে। জরুরি কৃষিকাজের সিদ্ধান্ত নেওয়ার পূর্বে স্থানীয় আবহাওয়া ও আকাশ পর্যবেক্ষণ করুন।"
        }

    async def get_forecast(self, latitude: float, longitude: float, location_name: str = "চিহ্নিত স্থান") -> Dict[str, Any]:
        # 1. Validate coordinates
        if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
            raise ValueError(f"অবৈধ ভৌগোলিক স্থানাঙ্ক: latitude={latitude}, longitude={longitude}")

        cache_key = self._cache_key(latitude, longitude)
        now = time.time()

        # 2. Check Cache
        cached_entry = self._cache.get(cache_key)
        if cached_entry:
            age = now - cached_entry["cached_at"]
            if age < settings.WEATHER_CACHE_TTL_SECONDS:
                logger.info(f"Serving weather forecast from memory cache (age: {int(age)}s)")
                result = dict(cached_entry["data"])
                result["is_cached"] = True
                result["cached_age_seconds"] = int(age)
                return result

        # 3. Fetch from Open-Meteo
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,weather_code,wind_speed_10m,wind_direction_10m",
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max",
            "timezone": "Asia/Kolkata",
            "forecast_days": 5
        }

        client = await self.get_client()
        try:
            response = await client.get(settings.WEATHER_API_BASE_URL, params=params)
            response.raise_for_status()
            raw_data = response.json()
        except httpx.TimeoutException as exc:
            logger.error(f"Weather API timeout: {exc}")
            # If expired cache exists, return stale cache with explicit warning rather than hard crash
            if cached_entry:
                result = dict(cached_entry["data"])
                result["is_cached"] = True
                result["is_stale"] = True
                result["cached_age_seconds"] = int(now - cached_entry["cached_at"])
                result["stale_warning_bn"] = "আবহাওয়া সেবা থেকে নতুন তথ্য পেতে বিলম্ব হচ্ছে। পূর্বের সংরক্ষিত তথ্য প্রদর্শিত হচ্ছে।"
                return result
            raise TimeoutError("আবহাওয়া সেবা প্রদানকারীর সাথে সংযোগ সময়সীমা উত্তীর্ণ (Timeout) হয়েছে।") from exc
        except httpx.HTTPStatusError as exc:
            logger.error(f"Weather API HTTP error {exc.response.status_code}: {exc.response.text}")
            raise RuntimeError(f"আবহাওয়া সরবরাহকারী থেকে ত্রুটি সংকেত (HTTP {exc.response.status_code})") from exc
        except Exception as exc:
            logger.error(f"Weather API general error: {exc}")
            raise RuntimeError(f"আবহাওয়া তথ্য পুনরুদ্ধারে ত্রুটি ঘটেছে: {str(exc)}") from exc

        # 4. Normalize response
        current_raw = raw_data.get("current", {})
        daily_raw = raw_data.get("daily", {})

        wmo_curr = get_wmo_description(current_raw.get("weather_code"))
        current_norm = {
            "observation_time": current_raw.get("time"),
            "temperature_c": current_raw.get("temperature_2m"),
            "apparent_temperature_c": current_raw.get("apparent_temperature"),
            "relative_humidity_pct": current_raw.get("relative_humidity_2m"),
            "precipitation_mm": current_raw.get("precipitation", 0.0),
            "wind_speed_kmh": current_raw.get("wind_speed_10m"),
            "wind_direction_deg": current_raw.get("wind_direction_10m"),
            "wind_direction_bn": degrees_to_cardinal_bn(current_raw.get("wind_direction_10m")),
            "weather_code": current_raw.get("weather_code"),
            "weather_desc_en": wmo_curr["en"],
            "weather_desc_bn": wmo_curr["bn"],
            "weather_type": wmo_curr["type"]
        }

        # Daily forecast normalization
        daily_norm: List[Dict[str, Any]] = []
        times = daily_raw.get("time", [])
        w_codes = daily_raw.get("weather_code", [])
        t_max = daily_raw.get("temperature_2m_max", [])
        t_min = daily_raw.get("temperature_2m_min", [])
        p_sum = daily_raw.get("precipitation_sum", [])
        p_prob = daily_raw.get("precipitation_probability_max", [])
        w_max = daily_raw.get("wind_speed_10m_max", [])

        for i in range(len(times)):
            code_i = w_codes[i] if i < len(w_codes) else None
            desc_i = get_wmo_description(code_i)
            daily_norm.append({
                "date": times[i],
                "weather_code": code_i,
                "weather_desc_en": desc_i["en"],
                "weather_desc_bn": desc_i["bn"],
                "weather_type": desc_i["type"],
                "temperature_max_c": t_max[i] if i < len(t_max) else None,
                "temperature_min_c": t_min[i] if i < len(t_min) else None,
                "precipitation_sum_mm": p_sum[i] if i < len(p_sum) else 0.0,
                "precipitation_probability_pct": p_prob[i] if i < len(p_prob) else 0,
                "wind_speed_max_kmh": w_max[i] if i < len(w_max) else None,
            })

        advisory = self._generate_advisory(current_norm, daily_norm)

        normalized_result = {
            "provider": "Open-Meteo",
            "provider_terms": "Non-commercial Open-Meteo Free API (CC-BY 4.0)",
            "location_name": location_name,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": raw_data.get("timezone", "Asia/Kolkata"),
            "retrieved_at_unix": int(now),
            "is_cached": False,
            "is_stale": False,
            "cached_age_seconds": 0,
            "current_conditions": current_norm,
            "daily_forecast": daily_norm,
            "agricultural_advisory": advisory
        }

        # Save to memory cache
        self._cache[cache_key] = {
            "cached_at": now,
            "data": normalized_result
        }

        return normalized_result

    async def search_locations(self, query: str) -> List[Dict[str, Any]]:
        """Search locations in West Bengal / India via Open-Meteo Geocoding API."""
        if not query or len(query.strip()) < 2:
            return []

        client = await self.get_client()
        params = {
            "name": query.strip(),
            "count": 6,
            "language": "en",
            "format": "json"
        }
        try:
            resp = await client.get(settings.GEOCODING_API_BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            items = []
            for r in results:
                name = r.get("name")
                admin1 = r.get("admin1", "")
                country = r.get("country", "")
                lat = r.get("latitude")
                lon = r.get("longitude")
                display_label = f"{name}, {admin1}" if admin1 else f"{name}, {country}"
                items.append({
                    "name": name,
                    "admin1": admin1,
                    "country": country,
                    "display_label": display_label,
                    "latitude": lat,
                    "longitude": lon
                })
            return items
        except Exception as e:
            logger.warning(f"Geocoding search failed for query '{query}': {e}")
            return []


# Global singleton instance
weather_service = WeatherService()
