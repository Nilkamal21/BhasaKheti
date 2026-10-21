from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from app.core.config import settings
from app.core.logging import logger
from app.services.disease_service import disease_model_service


router = APIRouter()


class PredictionCandidate(BaseModel):
    rank: int
    class_index: int
    raw_class_name: str
    crop: str
    disease: str
    is_healthy: bool
    display_name_en: str
    display_name_bn: str
    model_score: float
    is_verified: bool


class DiseasePredictionResponse(BaseModel):
    success: bool
    model_identifier: str
    verification_status: str
    verification_source: str
    primary_prediction: PredictionCandidate
    top_candidates: List[PredictionCandidate]
    disclaimer_bn: str
    disclaimer_en: str


@router.post(
    "/predict",
    response_model=DiseasePredictionResponse,
    summary="Predict plant disease from leaf image",
    description="Takes an uploaded RGB image of a crop leaf and runs CPU inference using the MobileNetV2 disease classifier.",
)
async def predict_disease(
    file: UploadFile = File(..., description="Plant leaf image (JPEG, PNG, WEBP, max 10MB)")
):
    # 1. Validate content type header
    content_type = file.content_type or ""
    if content_type.lower() not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"অসমর্থিত ফাইল ফরম্যাট ({content_type})। অনুগ্রহ করে JPEG, PNG বা WEBP ফরম্যাটের ছবি আপলোড করুন।"
        )

    # 2. Read image content with size limitation
    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="খালি বা ত্রুটিপূর্ণ ফাইল প্রদান করা হয়েছে।"
        )

    if len(image_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"ফাইলের আকার অতিরিক্ত বড় (সর্বোচ্চ {settings.MAX_UPLOAD_SIZE_BYTES // (1024*1024)}MB অনুমোদিত)।"
        )

    # 3. Perform inference through isolated adapter
    try:
        result = disease_model_service.predict(image_bytes)
        return DiseasePredictionResponse(
            success=True,
            model_identifier=result["model_identifier"],
            verification_status=result["verification_status"],
            verification_source=result["verification_source"],
            primary_prediction=result["primary_prediction"],
            top_candidates=result["top_candidates"],
            disclaimer_bn=result["disclaimer_bn"],
            disclaimer_en=result["disclaimer_en"],
        )
    except ValueError as val_err:
        logger.warning(f"Image validation rejected: {val_err}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ছবি প্রক্রিয়াকরণে ব্যর্থ: {str(val_err)}"
        )
    except FileNotFoundError as fnf_err:
        logger.error(f"Disease model weights missing: {fnf_err}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="মডেল ফাইল সার্ভারে অনুপস্থিত। অনুগ্রহ করে সিস্টেম অ্যাডমিনের সাথে যোগাযোগ করুন।"
        )
    except Exception as exc:
        logger.error(f"Inference execution failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="মডেল অনুমান পরিচালনায় একটি অপ্রত্যাশিত ত্রুটি ঘটেছে।"
        )
