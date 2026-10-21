"""
API Endpoints for Phase 6: Crop Intelligence & Context-Aware Guidance.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Form, File, UploadFile, HTTPException, status
from pydantic import BaseModel, Field
from app.services.crop_intelligence_service import crop_intelligence_service
from app.services.disease_service import disease_model_service
from app.services.soil_type_service import soil_type_service
from app.core.logging import logger

router = APIRouter()


class CropIntelligenceTextRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500, description="Farmer question in Bengali or English")
    crop: Optional[str] = Field(None, max_length=50, description="Optional crop name")
    latitude: Optional[float] = Field(23.23, ge=-90.0, le=90.0, description="Latitude for local weather integration")
    longitude: Optional[float] = Field(87.86, ge=-180.0, le=180.0, description="Longitude for local weather integration")


@router.post("/ask")
async def ask_crop_intelligence(
    query: str = Form(..., min_length=2, max_length=500),
    crop: Optional[str] = Form(None),
    latitude: Optional[float] = Form(23.23),
    longitude: Optional[float] = Form(87.86),
    leaf_image: Optional[UploadFile] = File(None),
    soil_image: Optional[UploadFile] = File(None)
):
    """
    Unified multimodal crop intelligence endpoint.
    Orchestrates:
    - Context & Intent Extraction
    - Weather / Irrigation Check
    - Leaf Disease Model (if leaf image provided)
    - Soil Classifier (if soil image provided)
    - Phase 5 Verified Knowledge Base
    - Cohere Grounded Generation with Deterministic Fallback
    """
    leaf_disease_pred = None
    soil_type_pred = None

    # Process optional leaf image through Phase 2 disease classifier
    if leaf_image:
        try:
            image_bytes = await leaf_image.read()
            if len(image_bytes) > 0:
                leaf_disease_pred = disease_model_service.predict(image_bytes)
        except Exception as exc:
            logger.warning(f"Leaf image classification failed: {exc}")

    # Process optional soil image through Phase 3 soil classifier
    if soil_image:
        try:
            soil_bytes = await soil_image.read()
            if len(soil_bytes) > 0:
                soil_type_pred = soil_type_service.predict(soil_bytes)
        except Exception as exc:
            logger.warning(f"Soil image classification failed: {exc}")

    try:
        response = await crop_intelligence_service.orchestrate(
            query=query,
            crop=crop,
            latitude=latitude if latitude is not None else 23.23,
            longitude=longitude if longitude is not None else 87.86,
            leaf_disease_prediction=leaf_disease_pred,
            soil_type_prediction=soil_type_pred
        )
        return response
    except Exception as exc:
        logger.error(f"Crop intelligence error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"বুদ্ধিমান কৃষি পরামর্শ প্রদানে ত্রুটি: {str(exc)}"
        )
