from fastapi import APIRouter

from apps.api.models.schemas import HealthCheck

router = APIRouter()


@router.get("/", response_model=HealthCheck)
async def root():
    return {"status": "online", "message": "Especulai API está funcionando corretamente"}


@router.get("/health", response_model=HealthCheck)
async def health_check():
    return {"status": "healthy", "message": "API operacional"}


