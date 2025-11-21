"""
Esquemas Pydantic para a API.
"""

from pydantic import BaseModel, Field, validator


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


