"""
Ponto de entrada da API FastAPI modularizada.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routes.health import router as health_router
from apps.api.routes.pipeline import router as pipeline_router
from apps.api.routes.predict import router as predict_router
from apps.api.routes.scrape import router as scrape_router

app = FastAPI(
    title="Especulai API",
    description="API para estimativa de preços de imóveis usando Machine Learning",
    version="1.0.0",
)

DEFAULT_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"

# CORS via ALLOWED_ORIGINS (csv) para não exigir alteração de código por ambiente.
allowed_origins = [
    origin.strip()
    for origin in os.environ.get("ALLOWED_ORIGINS", DEFAULT_ORIGINS).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos os métodos (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Permite todos os headers
)

app.include_router(health_router)
app.include_router(predict_router)
app.include_router(scrape_router)
app.include_router(pipeline_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


