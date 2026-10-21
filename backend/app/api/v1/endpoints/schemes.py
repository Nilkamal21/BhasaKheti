"""
API Endpoints for Phase 7: Government Scheme Discovery.
Provides access to verified West Bengal and Central government agricultural schemes,
benefits, eligibility, and preliminary guidance without collecting sensitive credentials.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel, Field
from app.services.scheme_service import scheme_service
from app.core.logging import logger

router = APIRouter()


class EligibilityCheckRequest(BaseModel):
    land_size_acres: Optional[float] = Field(None, ge=0.0, le=500.0, description="Cultivable land size in acres")
    is_sharecropper: bool = Field(False, description="Whether the applicant is a recorded sharecropper (ভাগচাষী)")
    is_owner: bool = Field(True, description="Whether the applicant owns agricultural land")
    interests: Optional[List[str]] = Field(None, description="Optional areas of interest (e.g. machinery, loan, insurance)")


@router.get("/categories")
def get_scheme_categories() -> List[Dict[str, str]]:
    """Returns list of agricultural scheme categories."""
    return scheme_service.get_categories()


@router.get("")
def get_schemes(
    q: Optional[str] = Query(None, max_length=100, description="Search query in Bengali or English"),
    category: Optional[str] = Query(None, description="Category filter"),
    sponsor: Optional[str] = Query(None, description="Sponsor filter ('state', 'central', 'joint', 'all')"),
    beneficiary_type: Optional[str] = Query(None, description="Beneficiary type filter"),
    limit: int = Query(20, ge=1, le=50, description="Max results")
) -> Dict[str, Any]:
    """Search and discover agricultural schemes and assistance programmes."""
    try:
        return scheme_service.get_schemes(
            query=q,
            category=category,
            sponsor=sponsor,
            beneficiary_type=beneficiary_type,
            limit=limit
        )
    except Exception as exc:
        logger.error(f"Schemes search failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="সরকারি প্রকল্প অনুসন্ধানে ত্রুটি ঘটেছে।"
        )


@router.get("/{scheme_id}")
def get_scheme_details(scheme_id: str) -> Dict[str, Any]:
    """Returns full details of a specific scheme."""
    scheme = scheme_service.get_scheme_by_id(scheme_id)
    if not scheme:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="নির্দিষ্ট সরকারি প্রকল্পের তথ্য খুঁজে পাওয়া যায়নি।"
        )
    return scheme


@router.post("/check-eligibility")
def check_eligibility(req: EligibilityCheckRequest) -> Dict[str, Any]:
    """
    Evaluates preliminary scheme eligibility based on generalized criteria.
    Guarantees privacy: No Aadhaar, bank details, or passwords collected.
    """
    try:
        return scheme_service.check_preliminary_eligibility(
            land_size_acres=req.land_size_acres,
            is_sharecropper=req.is_sharecropper,
            is_owner=req.is_owner,
            interests=req.interests
        )
    except Exception as exc:
        logger.error(f"Eligibility evaluation failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="যোগ্যতা মূল্যায়নে ত্রুটি ঘটেছে।"
        )
