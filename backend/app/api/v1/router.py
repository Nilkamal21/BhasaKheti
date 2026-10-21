from fastapi import APIRouter
from app.api.v1.endpoints import health, disease, soil, weather, knowledge, crop_intelligence, market, schemes, supervisor

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(disease.router, prefix="/disease", tags=["disease"])
api_router.include_router(soil.router, prefix="/soil", tags=["soil"])
api_router.include_router(weather.router, prefix="/weather", tags=["weather"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(crop_intelligence.router, prefix="/intelligence", tags=["intelligence"])
api_router.include_router(market.router, prefix="/market", tags=["market"])
api_router.include_router(schemes.router, prefix="/schemes", tags=["schemes"])
api_router.include_router(supervisor.router, prefix="/supervisor", tags=["supervisor"])


