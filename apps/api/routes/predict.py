from fastapi import APIRouter, HTTPException
from especulai.apps.api.models.schemas import ImovelInput, PredictionOutput
from especulai.apps.api.services.model_service import ModelService


router = APIRouter()
model_service = ModelService()

# Carrega o modelo na inicialização do módulo
model_service.load()


@router.post("/predict", response_model=PredictionOutput)
async def predict(imovel: ImovelInput):
    if not model_service.is_ready():
        raise HTTPException(status_code=503, detail="Modelo não disponível. Execute o pipeline de treinamento primeiro.")
    result = model_service.predict(imovel.dict())
    return result


