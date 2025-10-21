"""
Ponto de entrada da API FastAPI modularizada.
"""

from fastapi import FastAPI
from especulai_sistema.api.routes.health import router as health_router
from especulai_sistema.api.routes.predict import router as predict_router
from especulai_sistema.api.routes.scrape import router as scrape_router


app = FastAPI(
    title="Especulai API",
    description="API para estimativa de preços de imóveis usando Machine Learning",
    version="1.0.0",
)


app.include_router(health_router)
app.include_router(predict_router)
app.include_router(scrape_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


