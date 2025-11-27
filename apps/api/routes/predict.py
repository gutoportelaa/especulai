from fastapi import APIRouter
from especulai.apps.api.models.schemas import ImovelInput, PredictionOutput
from especulai.apps.api.services.model_service import ModelService


router = APIRouter()
model_service = ModelService()

# Carrega o modelo na inicialização do módulo
model_service.load()


@router.post("/predict", response_model=PredictionOutput)
async def predict(imovel: ImovelInput):
    """Endpoint de predição com fallback seguro para demonstração frontend.

    - Tenta usar o `ModelService.predict`.
    - Se ocorrer qualquer erro ou se o preço estimado for inválido (<= 0),
      usa uma estimativa fallback: `area * preco_por_m2_median`.
    """
    # Se o model service não estiver pronto, devolve um fallback simples
    if not model_service.is_ready():
        preco_ref = getattr(model_service, 'reference_values', {}).get('preco_por_m2_median', 5000.0)
        preco = float(imovel.area) * float(preco_ref)
        return {"preco_estimado": round(preco, 2), "confianca": "baixa"}

    try:
        result = model_service.predict(imovel.dict())
    except Exception as e:
        try:
            print(f"[WARN] Erro na predição do modelo: {e}")
        except Exception:
            pass
        preco_ref = getattr(model_service, 'reference_values', {}).get('preco_por_m2_median', 5000.0)
        preco = float(imovel.area) * float(preco_ref)
        return {"preco_estimado": round(preco, 2), "confianca": "baixa"}

    preco = float(result.get('preco_estimado', 0.0))
    if preco <= 0:
        preco_ref = getattr(model_service, 'reference_values', {}).get('preco_por_m2_median', 5000.0)
        preco = float(imovel.area) * float(preco_ref)
        return {"preco_estimado": round(preco, 2), "confianca": "média"}

    return {"preco_estimado": round(preco, 2), "confianca": result.get('confianca', 'média')}


