"""
API Endpoints for Phase 7: Market Intelligence.
Provides access to AGMARKNET West Bengal mandi prices, district lists, and price summaries.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel
from app.services.market_service import market_service
from app.core.logging import logger

router = APIRouter()


@router.get("/commodities")
def get_commodities() -> List[Dict[str, str]]:
    """Returns list of distinct commodities available in market reporting."""
    return market_service.get_commodities()


@router.get("/districts")
def get_districts() -> List[Dict[str, str]]:
    """Returns list of reporting West Bengal districts."""
    return market_service.get_districts()


@router.get("/prices")
def get_market_prices(
    commodity: Optional[str] = Query(None, description="Commodity ID or name (e.g. paddy_common, potato_jyoti)"),
    district: Optional[str] = Query(None, description="District name in Bengali or English"),
    q: Optional[str] = Query(None, max_length=100, description="Free text search query"),
    limit: int = Query(20, ge=1, le=100, description="Max records to return")
) -> Dict[str, Any]:
    """
    Search and filter reported agricultural market prices.
    Returns modal price, min/max range, unit conversion (per kg), 
    reported timestamp, and educational farm-gate guidance.
    """
    try:
        return market_service.search_prices(
            commodity=commodity,
            district=district,
            query=q,
            limit=limit
        )
    except Exception as exc:
        logger.error(f"Market search failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="বাজারদর অনুসন্ধানে সাময়িক ত্রুটি ঘটেছে।"
        )


@router.get("/summary")
def get_market_summary() -> Dict[str, Any]:
    """Returns daily market highlights for key staple crops in West Bengal."""
    return market_service.get_market_summary()
