"""
Market Intelligence Service for BhashaKheti (Phase 7).
Provides discovery of agricultural market/mandi prices across West Bengal.
Integrates with official AGMARKNET datasets with freshness tracking, 
unit conversion, and mandi vs farm-gate price transparency.
"""

import json
import os
import time
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from app.core.config import settings
from app.core.logging import logger

DISCLAIMER_FARM_GATE_BN = (
    "মন্ডির দর হলো পাইকারি বাজারমূল্য (Wholesale Mandi Price)। "
    "পরিবহন খরচ, ফসলের গ্রেডিং, আর্দ্রতার পরিমাণ এবং স্থানীয় মধ্যস্বত্বভোগীর কমিশনের কারণে "
    "কৃষকের মাঠে বা খামারে সরাসরি বিক্রয়মূল্য (Farm-gate Price) মণ্ডি দরের চেয়ে কিছুটা কম হতে পারে।"
)

DISCLAIMER_NOT_PROMISED_BN = (
    "বাজারদর পরিবর্তনশীল এবং এটি কেবল নির্দেশক তথ্য। "
    "ভাষাখেতি কোনো নির্দিষ্ট লাভ বা বিক্রয়মূল্যের নিশ্চয়তা প্রদান করে না।"
)


COMMODITY_ALIASES = {
    "rice": "paddy",
    "paddy": "paddy",
    "ধান": "paddy",
    "potato": "potato",
    "আলু": "potato",
    "tomato": "tomato",
    "টমেটো": "tomato",
    "bell_pepper": "chilli",
    "chilli": "chilli",
    "লঙ্কা": "chilli",
    "onion": "onion",
    "পেঁয়াজ": "onion",
    "mustard": "mustard",
    "সরিষা": "mustard",
    "jute": "jute",
    "পাট": "jute"
}


class MarketService:
    """Manages West Bengal mandi price data retrieval, search, caching, and unit conversion."""

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path or settings.MARKET_DATA_PATH
        self._cached_records: List[Dict[str, Any]] = []
        self._last_loaded_time: float = 0
        self.cache_ttl = settings.MARKET_CACHE_TTL_SECONDS
        self._load_data()

    def _load_data(self) -> None:
        """Loads market data from file or provider cache."""
        now = time.time()
        if self._cached_records and (now - self._last_loaded_time < self.cache_ttl):
            return

        resolved_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", self.data_path))
        if not os.path.exists(resolved_path):
            alt_path = os.path.abspath(self.data_path)
            if os.path.exists(alt_path):
                resolved_path = alt_path
            else:
                logger.error(f"Market data file not found at: {resolved_path}")
                self._cached_records = []
                return

        try:
            with open(resolved_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                self._cached_records = self._normalize_records(raw_data)
                self._last_loaded_time = now
                logger.info(f"Loaded {len(self._cached_records)} market price records from {resolved_path}")
        except Exception as exc:
            logger.error(f"Failed to load market data: {exc}")
            self._cached_records = []

    def _normalize_records(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalizes and validates price records, tagging historical data and calculating per-kg values."""
        normalized = []
        today = date.today()

        for item in raw_data:
            rec = dict(item)
            rep_date_str = rec.get("reported_date", "")
            is_historical = rec.get("is_historical", False)

            # Check if reported date is older than 2 days
            if rep_date_str:
                try:
                    rep_date = datetime.strptime(rep_date_str, "%Y-%m-%d").date()
                    if (today - rep_date).days > 2:
                        is_historical = True
                except ValueError:
                    pass

            rec["is_historical"] = is_historical
            rec["data_status"] = "historical" if is_historical else "verified_recent"

            # Unit conversion (Quintal = 100 kg)
            unit = rec.get("unit", "₹/Quintal")
            modal_price = float(rec.get("modal_price", 0))
            min_price = float(rec.get("min_price", 0))
            max_price = float(rec.get("max_price", 0))

            if "quintal" in unit.lower() or "কুইন্টাল" in unit:
                rec["modal_price_per_kg"] = round(modal_price / 100.0, 2)
                rec["min_price_per_kg"] = round(min_price / 100.0, 2)
                rec["max_price_per_kg"] = round(max_price / 100.0, 2)
            else:
                rec["modal_price_per_kg"] = modal_price
                rec["min_price_per_kg"] = min_price
                rec["max_price_per_kg"] = max_price

            normalized.append(rec)
        return normalized

    def get_commodities(self) -> List[Dict[str, str]]:
        """Returns distinct commodities available in the dataset."""
        self._load_data()
        seen = set()
        commodities = []
        for r in self._cached_records:
            cid = r.get("commodity_id", "")
            if cid and cid not in seen:
                seen.add(cid)
                commodities.append({
                    "id": cid,
                    "name_bn": r.get("commodity_name_bn", cid),
                    "name_en": r.get("commodity_name_en", cid)
                })
        return sorted(commodities, key=lambda x: x["name_bn"])

    def get_districts(self) -> List[Dict[str, str]]:
        """Returns distinct West Bengal districts with reporting mandis."""
        self._load_data()
        seen = set()
        districts = []
        for r in self._cached_records:
            den = r.get("district_en", "")
            if den and den not in seen:
                seen.add(den)
                districts.append({
                    "district_en": den,
                    "district_bn": r.get("district_bn", den)
                })
        return sorted(districts, key=lambda x: x["district_bn"])

    def search_prices(
        self,
        commodity: Optional[str] = None,
        district: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Searches for market prices by commodity, district, or free text in Bengali/English.
        """
        self._load_data()
        results = list(self._cached_records)

        # Commodity filtering
        if commodity and commodity.lower() != "all":
            c_lower = commodity.lower().strip()
            alias = COMMODITY_ALIASES.get(c_lower, c_lower)
            results = [
                r for r in results
                if c_lower in r.get("commodity_id", "").lower()
                or alias in r.get("commodity_id", "").lower()
                or c_lower in r.get("commodity_name_en", "").lower()
                or alias in r.get("commodity_name_en", "").lower()
                or c_lower in r.get("commodity_name_bn", "")
                or alias in r.get("commodity_name_bn", "")
            ]

        # District filtering
        if district and district.lower() != "all":
            d_lower = district.lower().strip()
            results = [
                r for r in results
                if d_lower in r.get("district_en", "").lower()
                or d_lower in r.get("district_bn", "").lower()
            ]

        # Free-text search matching
        if query and query.strip():
            raw_tokens = query.lower().strip().replace("?", "").replace("।", "").replace(",", "").split()
            tokens = []
            for t in raw_tokens:
                tokens.append(t)
                # Expand with commodity aliases (e.g. 'rice' -> 'paddy')
                if t in COMMODITY_ALIASES:
                    tokens.append(COMMODITY_ALIASES[t])
                for suffix in ["ের", "ে", "র", "তে", "টি", "টা"]:
                    if t.endswith(suffix) and len(t) > len(suffix) + 1:
                        tokens.append(t[:-len(suffix)])

            filtered = []
            for r in results:
                searchable = (
                    f"{r.get('commodity_name_bn', '')} {r.get('commodity_name_en', '')} "
                    f"{r.get('commodity_id', '')} "
                    f"{r.get('market_name_bn', '')} {r.get('market_name_en', '')} "
                    f"{r.get('district_bn', '')} {r.get('district_en', '')} "
                    f"{r.get('variety', '')}"
                ).lower()
                if any(t in searchable for t in tokens if len(t) >= 2):
                    filtered.append(r)

            # If a commodity was already matched, keep results even if query words are conversational
            if filtered or not commodity:
                results = filtered

        # Sort: recent first, then highest modal price
        results.sort(key=lambda x: (not x.get("is_historical", False), x.get("reported_date", "")), reverse=True)
        paginated = results[:limit]

        return {
            "total_matches": len(results),
            "results_count": len(paginated),
            "prices": paginated,
            "disclaimers": [
                DISCLAIMER_FARM_GATE_BN,
                DISCLAIMER_NOT_PROMISED_BN
            ],
            "data_source": "AGMARKNET - Directorate of Marketing & Inspection, Ministry of Agriculture & Farmers Welfare, GoI",
            "source_url": "https://agmarknet.gov.in"
        }

    def get_market_summary(self) -> Dict[str, Any]:
        """Returns staple crop price highlights in West Bengal."""
        self._load_data()
        key_crops = ["paddy_common", "potato_jyoti", "tomato", "jute", "mustard"]
        summary_cards = []

        for crop_id in key_crops:
            crop_matches = [r for r in self._cached_records if r.get("commodity_id") == crop_id]
            if crop_matches:
                avg_modal = round(sum(r["modal_price"] for r in crop_matches) / len(crop_matches))
                avg_per_kg = round(sum(r["modal_price_per_kg"] for r in crop_matches) / len(crop_matches), 1)
                latest_date = max(r.get("reported_date", "") for r in crop_matches)
                first = crop_matches[0]
                summary_cards.append({
                    "commodity_id": crop_id,
                    "commodity_name_bn": first.get("commodity_name_bn"),
                    "commodity_name_en": first.get("commodity_name_en"),
                    "average_modal_price": avg_modal,
                    "average_modal_per_kg": avg_per_kg,
                    "unit": first.get("unit", "₹/Quintal"),
                    "latest_date": latest_date,
                    "mandis_reporting": len(crop_matches)
                })

        return {
            "report_date": date.today().isoformat(),
            "summary_highlights": summary_cards,
            "disclaimer_bn": DISCLAIMER_FARM_GATE_BN,
            "source_name": "AGMARKNET"
        }


market_service = MarketService()
