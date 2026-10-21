"""
Agricultural Knowledge & Safety API Endpoints for BhashaKheti.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel, Field
from app.services.knowledge_service import knowledge_service

router = APIRouter()


class AskQuestionRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500, description="Farmer's question or symptom inquiry")
    crop: Optional[str] = Field(None, max_length=50, description="Optional crop filter: rice, potato, tomato, bell_pepper, soil_general")
    growth_stage: Optional[str] = Field(None, max_length=100, description="Optional crop growth stage")


class KnowledgeRecordModel(BaseModel):
    id: str
    title_bn: str
    title_en: str
    crop: str
    category: str
    topic: str
    growth_stage: Optional[str] = None
    content_bn: str
    content_en: str
    source_org: str
    source_url: str
    publication_date: str
    last_verified_date: str
    geographic_scope: str
    evidence_status: str
    safety_notes_bn: str
    safety_notes_en: str
    keywords: List[str]
    chemical_control_permitted: bool
    search_relevance_score: Optional[float] = None


@router.get("/categories")
def get_categories():
    """Returns available categories and supported crop tags in the knowledge base."""
    return knowledge_service.get_categories_and_crops()


@router.get("/search")
def search_knowledge(
    query: str = Query(..., min_length=2, max_length=200, description="Search query string"),
    crop: Optional[str] = Query(None, description="Optional crop tag"),
    category: Optional[str] = Query(None, description="Optional category tag"),
    limit: int = Query(5, ge=1, le=20, description="Maximum number of records to return")
):
    """
    Searches verified agricultural knowledge base with multi-field scoring.
    Returns matching records, evidence status, and safety boundary warnings.
    """
    try:
        return knowledge_service.search(query=query, crop=crop, category=category, limit=limit)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"জ্ঞানভাণ্ডার অনুসন্ধানে ত্রুটি ঘটেছে: {str(e)}"
        )


@router.get("/records/{record_id}")
def get_record(record_id: str):
    """Fetches a specific knowledge record by its unique ID."""
    record = knowledge_service.get_record_by_id(record_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"'{record_id}' আইডি বিশিষ্ট কোনো কৃষি নির্দেশিকা রেকর্ড পাওয়া যায়নি।"
        )
    return record


@router.post("/ask")
def ask_question(payload: AskQuestionRequest):
    """
    Answers a farmer's question backed strictly by verified agricultural sources.
    Enforces evidence verification, crop boundaries, and mandatory chemical disclaimers.
    """
    try:
        return knowledge_service.ask(
            query=payload.query,
            crop=payload.crop,
            growth_stage=payload.growth_stage
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"প্রশ্ন প্রক্রিয়াকরণে ত্রুটি ঘটেছে: {str(e)}"
        )
