"""
API REST para servir predições de preços de imóveis.
Construída com FastAPI para alta performance e validação automática.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator
import joblib
import numpy as np
from typing import Dict, Optional
import os


# Modelos Pydantic para validação de dados
class ImovelInput(BaseModel):
    """
    Modelo de entrada para predição de preço de imóvel.
    """
    area: float = Field(..., gt=0, description="Área do imóvel em metros quadrados")
    quartos: int = Field(..., ge=0, description="Número de quartos")
    banheiros: int = Field(..., ge=0, description="Número de banheiros")
    tipo: str = Field(..., description="Tipo do imóvel (apartamento/casa)")
    bairro: str = Field(..., description="Bairro do imóvel")
    cidade: str = Field(..., description="Cidade do imóvel")
    
    @validator('tipo')
    def validate_tipo(cls, v):
        """Valida o tipo de imóvel."""
        v = v.lower()
        if v not in ['apartamento', 'casa']:
            raise ValueError('Tipo deve ser "apartamento" ou "casa"')
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "area": 85.0,
                "quartos": 3,
                "banheiros": 2,
                "tipo": "apartamento",
                "bairro": "Jardins",
                "cidade": "São Paulo"
            }
        }


class PredictionOutput(BaseModel):
    """
    Modelo de saída para predição de preço.
    """
    preco_estimado: float = Field(..., description="Preço estimado do imóvel em reais")
    confianca: str = Field(..., description="Nível de confiança da predição")
    
    class Config:
        schema_extra = {
            "example": {
                "preco_estimado": 450000.00,
                "confianca": "alta"
            }
        }


class HealthCheck(BaseModel):
    """
    Modelo para verificação de saúde da API.
    """
    status: str
    message: str


# Inicializa aplicação FastAPI
app = FastAPI(
    title="Especulai API",
    description="API para estimativa de preços de imóveis usando Machine Learning",
    version="1.0.0"
)


# Variáveis globais para modelo e pré-processador
model = None
preprocessor = None


@app.on_event("startup")
async def load_model():
    """
    Carrega o modelo e pré-processador na inicialização da API.
    """
    global model, preprocessor
    
    try:
        # Caminhos dos artefatos
        model_path = "../ml_pipeline/model.joblib"
        preprocessor_path = "../ml_pipeline/preprocessor.joblib"
        
        # Verifica se os arquivos existem
        if not os.path.exists(model_path):
            print(f"⚠ Modelo não encontrado em {model_path}")
            return
        
        if not os.path.exists(preprocessor_path):
            print(f"⚠ Pré-processador não encontrado em {preprocessor_path}")
            return
        
        # Carrega artefatos
        model = joblib.load(model_path)
        preprocessor = joblib.load(preprocessor_path)
        
        print("✓ Modelo e pré-processador carregados com sucesso")
        
    except Exception as e:
        print(f"✗ Erro ao carregar modelo: {e}")


@app.get("/", response_model=HealthCheck)
async def root():
    """
    Endpoint raiz para verificação de saúde da API.
    """
    return {
        "status": "online",
        "message": "Especulai API está funcionando corretamente"
    }


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """
    Endpoint de health check para monitoramento.
    """
    if model is None or preprocessor is None:
        return {
            "status": "degraded",
            "message": "Modelo não carregado. Execute o pipeline de treinamento primeiro."
        }
    
    return {
        "status": "healthy",
        "message": "API operacional com modelo carregado"
    }


@app.post("/predict", response_model=PredictionOutput)
async def predict_price(imovel: ImovelInput) -> Dict:
    """
    Endpoint para predição de preço de imóvel.
    
    Args:
        imovel: Dados do imóvel para predição
        
    Returns:
        Predição de preço estimado
    """
    # Verifica se o modelo está carregado
    if model is None or preprocessor is None:
        raise HTTPException(
            status_code=503,
            detail="Modelo não disponível. Execute o pipeline de treinamento primeiro."
        )
    
    try:
        # Extrai pré-processadores
        scaler = preprocessor['scaler']
        label_encoders = preprocessor['label_encoders']
        feature_columns = preprocessor['feature_columns']
        
        # Calcula features derivadas
        preco_por_m2_estimado = 5000  # Valor médio para inicialização
        densidade_comodos = (imovel.quartos + imovel.banheiros) / imovel.area
        
        # Codifica variáveis categóricas
        try:
            tipo_encoded = label_encoders['tipo'].transform([imovel.tipo.lower()])[0]
        except ValueError:
            tipo_encoded = 0  # Valor padrão para tipos desconhecidos
        
        try:
            bairro_encoded = label_encoders['bairro'].transform([imovel.bairro])[0]
        except ValueError:
            bairro_encoded = 0  # Valor padrão para bairros desconhecidos
        
        try:
            cidade_encoded = label_encoders['cidade'].transform([imovel.cidade])[0]
        except ValueError:
            cidade_encoded = 0  # Valor padrão para cidades desconhecidas
        
        # Monta vetor de features
        features = np.array([[
            imovel.area,
            imovel.quartos,
            imovel.banheiros,
            preco_por_m2_estimado,
            densidade_comodos,
            tipo_encoded,
            bairro_encoded,
            cidade_encoded
        ]])
        
        # Normaliza features
        features_scaled = scaler.transform(features)
        
        # Faz predição
        prediction = model.predict(features_scaled)[0]
        
        # Determina nível de confiança baseado em features conhecidas
        confianca = "alta"
        if (tipo_encoded == 0 and imovel.tipo.lower() not in ['apartamento', 'casa']) or \
           bairro_encoded == 0 or cidade_encoded == 0:
            confianca = "média"
        
        return {
            "preco_estimado": float(prediction),
            "confianca": confianca
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao processar predição: {str(e)}"
        )


@app.get("/model-info")
async def model_info():
    """
    Endpoint para obter informações sobre o modelo carregado.
    """
    if model is None or preprocessor is None:
        raise HTTPException(
            status_code=503,
            detail="Modelo não disponível"
        )
    
    return {
        "model_type": type(model).__name__,
        "features": preprocessor['feature_columns'],
        "encoders": list(preprocessor['label_encoders'].keys())
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

