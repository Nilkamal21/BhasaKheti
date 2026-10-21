import os
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel
from app.core.config import settings
from app.db.session import check_db_health


router = APIRouter()


class ModelStatus(BaseModel):
    artifact_exists: bool
    status: str
    note: str


class HealthResponse(BaseModel):
    status: str
    environment: str
    phase: str
    database_connected: bool
    models: Dict[str, ModelStatus]


def _check_artifact(path_str: str, model_name: str) -> ModelStatus:
    # Resolve relative path from backend directory or root
    path = Path(path_str)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    
    exists = path.exists()
    return ModelStatus(
        artifact_exists=exists,
        status="not_integrated",
        note="Model inference is not integrated in Phase 1. Scheduled for subsequent phases."
    )


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    db_ok = check_db_health()
    
    models_status = {
        "plant_disease_classifier": ModelStatus(
            artifact_exists=Path(settings.PLANT_DISEASE_MODEL_PATH).exists() or (Path.cwd().parent / "plant_disease_classifier.pth").exists(),
            status="integrated",
            note="Phase 2: MobileNetV2 disease model integrated on CPU with verified class labels."
        ),
        "soil_type_classifier": ModelStatus(
            artifact_exists=Path(settings.SOIL_TYPE_MODEL_PATH).exists() or (Path.cwd().parent / "soil_type_classifier.tflite").exists(),
            status="integrated",
            note="Phase 3: MobileNetV2 TFLite soil type model integrated on CPU with verified 7 class labels."
        ),
        "soil_moisture_classifier": ModelStatus(
            artifact_exists=Path(settings.SOIL_MOISTURE_MODEL_PATH).exists() or (Path.cwd().parent / "soil_moisture_classifier.tflite").exists(),
            status="integrated",
            note="Phase 3: MobileNetV2 TFLite soil moisture model integrated on CPU with verified binary class labels."
        ),
    }

    overall_status = "ok" if db_ok else "degraded"

    return HealthResponse(
        status=overall_status,
        environment=settings.ENVIRONMENT,
        phase="Phase 1: Application Foundation",
        database_connected=db_ok,
        models=models_status
    )
