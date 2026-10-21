from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pydantic import BaseModel
from typing import List
from app.core.config import settings
from app.core.logging import logger
from app.services.soil_type_service import soil_type_service
from app.services.soil_moisture_service import soil_moisture_service


router = APIRouter()


class SoilClassCandidate(BaseModel):
    rank: int
    class_index: int
    raw_class_name: str
    display_name_en: str
    display_name_bn: str
    model_score: float
    is_verified: bool


class SoilPredictionResponse(BaseModel):
    success: bool
    model_identifier: str
    verification_status: str
    verification_source: str
    primary_prediction: SoilClassCandidate
    all_classes: List[SoilClassCandidate]
    disclaimer_bn: str
    disclaimer_en: str


async def _validate_and_read_image(file: UploadFile) -> bytes:
    content_type = file.content_type or ""
    if content_type.lower() not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"অসমর্থিত ফাইল ফরম্যাট ({content_type})। অনুগ্রহ করে JPEG, PNG বা WEBP ফরম্যাটের ছবি আপলোড করুন।"
        )

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

    return image_bytes


@router.post(
    "/type/predict",
    response_model=SoilPredictionResponse,
    summary="Predict soil type from soil image",
    description="Takes an uploaded RGB image of soil and classifies into one of 7 soil categories using MobileNetV2 TFLite on CPU.",
)
async def predict_soil_type(
    file: UploadFile = File(..., description="Soil image (JPEG, PNG, WEBP, max 10MB)")
):
    image_bytes = await _validate_and_read_image(file)

    try:
        result = soil_type_service.predict(image_bytes)
        return SoilPredictionResponse(
            success=True,
            model_identifier=result["model_identifier"],
            verification_status=result["verification_status"],
            verification_source=result["verification_source"],
            primary_prediction=result["primary_prediction"],
            all_classes=result["all_classes"],
            disclaimer_bn=result["disclaimer_bn"],
            disclaimer_en=result["disclaimer_en"],
        )
    except ValueError as val_err:
        logger.warning(f"Soil type image rejected: {val_err}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ছবি প্রক্রিয়াকরণে ব্যর্থ: {str(val_err)}"
        )
    except FileNotFoundError as fnf_err:
        logger.error(f"Soil type model missing: {fnf_err}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="মাটির ধরন মডেল ফাইল সার্ভারে অনুপস্থিত।"
        )
    except Exception as exc:
        logger.error(f"Soil type inference error: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="মাটির ধরন মডেলে একটি অপ্রত্যাশিত ত্রুটি ঘটেছে।"
        )


@router.post(
    "/moisture/predict",
    response_model=SoilPredictionResponse,
    summary="Predict soil moisture condition from soil image",
    description="Takes an uploaded RGB image of soil and estimates moisture condition (Dry vs Moist/Wet) using MobileNetV2 TFLite on CPU.",
)
async def predict_soil_moisture(
    file: UploadFile = File(..., description="Soil image (JPEG, PNG, WEBP, max 10MB)")
):
    image_bytes = await _validate_and_read_image(file)

    try:
        result = soil_moisture_service.predict(image_bytes)
        return SoilPredictionResponse(
            success=True,
            model_identifier=result["model_identifier"],
            verification_status=result["verification_status"],
            verification_source=result["verification_source"],
            primary_prediction=result["primary_prediction"],
            all_classes=result["all_classes"],
            disclaimer_bn=result["disclaimer_bn"],
            disclaimer_en=result["disclaimer_en"],
        )
    except ValueError as val_err:
        logger.warning(f"Soil moisture image rejected: {val_err}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ছবি প্রক্রিয়াকরণে ব্যর্থ: {str(val_err)}"
        )
    except FileNotFoundError as fnf_err:
        logger.error(f"Soil moisture model missing: {fnf_err}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="মাটির আর্দ্রতা মডেল ফাইল সার্ভারে অনুপস্থিত।"
        )
    except Exception as exc:
        logger.error(f"Soil moisture inference error: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="মাটির আর্দ্রতা মডেলে একটি অপ্রত্যাশিত ত্রুটি ঘটেছে।"
        )
