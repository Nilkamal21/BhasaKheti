"""
Supervisor Multi-Agent API Endpoint for Phase 9.
Unified entry point for voice transcripts, camera images, and natural text queries.
"""

from typing import Optional, List
import json
from fastapi import APIRouter, Form, File, UploadFile, HTTPException, status
from app.services.supervisor_service import supervisor_service, ChatTurn, SupervisorResponse
from app.core.logging import logger

router = APIRouter()


@router.post("/chat", response_model=SupervisorResponse)
async def supervisor_chat(
    query: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    image_type: Optional[str] = Form("auto"),  # 'leaf', 'soil', or 'auto'
    crop: Optional[str] = Form(None),
    latitude: Optional[float] = Form(23.23),
    longitude: Optional[float] = Form(87.86),
    history_json: Optional[str] = Form(None)
):
    """
    Unified Supervisor Multi-Agent Chat Endpoint.
    Coordinates:
    - Multimodal voice/camera/text input
    - Multi-turn conversation context
    - Selective specialized tools (disease, soil, weather, market, schemes, knowledge)
    - Programmatic safety boundary enforcement
    - Grounded Bengali synthesis
    """
    # Parse conversation history if provided
    history_turns: List[ChatTurn] = []
    if history_json:
        try:
            parsed = json.loads(history_json)
            if isinstance(parsed, list):
                history_turns = [ChatTurn(**turn) for turn in parsed]
        except Exception as e:
            logger.warning(f"Failed to parse history_json: {e}")

    # Read optional image bytes
    image_bytes = None
    if image:
        try:
            content = await image.read()
            if len(content) > 0:
                image_bytes = content
        except Exception as e:
            logger.warning(f"Error reading image: {e}")

    # Validation: at least query or image must be provided
    if not query and not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="দয়া করে একটি প্রশ্ন লিখুন, মুখে বলুন অথবা একটি ছবি নির্বাচন করুন।"
        )

    try:
        response = await supervisor_service.plan_and_execute(
            query=query or "",
            image_bytes=image_bytes,
            image_type=image_type,
            history=history_turns,
            crop=crop,
            latitude=latitude if latitude is not None else 23.23,
            longitude=longitude if longitude is not None else 87.86
        )
        return response
    except Exception as exc:
        logger.error(f"Supervisor orchestration failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"সুপারভাইজার প্রক্রিয়াকরণে ত্রুটি: {str(exc)}"
        )
