"""API de inferência do Especulai (Hugging Face Space).

Recebe as características do imóvel e devolve só a faixa de preço: nunca o vetor de features, o
log-preço nem qualquer parte do modelo. Contra extração por consulta repetida: limite por IP e
global, validação estrita da entrada e resposta arredondada. Nenhuma entrada é registrada em log.
"""

from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from inferencia import Modelo, decifrar, estimar
from pydantic import BaseModel, Field

PASTA = Path(__file__).parent
ORIGENS = [
    o.strip()
    for o in os.environ.get(
        "ALLOWED_ORIGINS", "https://gutoportelaa.github.io,http://localhost:5173"
    ).split(",")
    if o.strip()
]
POR_MINUTO = int(os.environ.get("LIMITE_POR_MINUTO", "20"))
POR_HORA = int(os.environ.get("LIMITE_POR_HORA", "200"))
GLOBAL_POR_HORA = int(os.environ.get("LIMITE_GLOBAL_POR_HORA", "3000"))


def carregar_modelos() -> dict[str, Modelo]:
    chave = os.environ.get("MODEL_KEY", "")
    if not chave:
        raise RuntimeError("MODEL_KEY ausente: sem a chave não há como abrir os pesos")
    return decifrar((PASTA / "modelo.enc").read_bytes(), bytes.fromhex(chave))


class Limitador:
    """Janela deslizante por IP e global. Em memória: reinicia com o Space, o que basta aqui."""

    def __init__(self) -> None:
        self._por_ip: dict[str, deque[float]] = defaultdict(deque)
        self._global: deque[float] = deque()
        self._trava = threading.Lock()

    def liberar(self, ip: str, agora: float | None = None) -> int | None:
        """None se liberado; senão, segundos até poder tentar de novo."""
        agora = time.monotonic() if agora is None else agora
        with self._trava:
            fila = self._por_ip[ip]
            for f, janela in ((fila, 3600), (self._global, 3600)):
                while f and agora - f[0] > janela:
                    f.popleft()
            ultimo_minuto = sum(1 for t in fila if agora - t <= 60)
            if ultimo_minuto >= POR_MINUTO:
                return max(1, int(60 - (agora - next(t for t in fila if agora - t <= 60))))
            if len(fila) >= POR_HORA:
                return max(1, int(3600 - (agora - fila[0])))
            if len(self._global) >= GLOBAL_POR_HORA:
                return max(1, int(3600 - (agora - self._global[0])))
            fila.append(agora)
            self._global.append(agora)
            return None


class Entrada(BaseModel):
    negocio: Literal["venda", "aluguel"]
    area: float = Field(ge=10, le=2000)
    quartos: int = Field(ge=0, le=20)
    banheiros: int = Field(ge=0, le=20)
    vagas: int | None = Field(default=None, ge=0, le=20)
    tipo: str = Field(min_length=1, max_length=40)
    bairro: str = Field(min_length=1, max_length=80)


class Saida(BaseModel):
    negocio: str
    preco_estimado: int
    minimo: int
    maximo: int
    nivel: float
    confianca: str


def criar_app(modelos: dict[str, Modelo] | None = None) -> FastAPI:
    app = FastAPI(title="Especulai", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(
        CORSMiddleware, allow_origins=ORIGENS, allow_methods=["POST", "GET"], allow_headers=["*"]
    )
    carregados = modelos if modelos is not None else carregar_modelos()
    limitador = Limitador()

    def ip_do_cliente(req: Request) -> str:
        # O proxy do Hub acrescenta o IP real ao fim de X-Forwarded-For; o começo é do cliente.
        encaminhado = req.headers.get("x-forwarded-for", "")
        if encaminhado:
            return encaminhado.split(",")[-1].strip()
        return req.client.host if req.client else "desconhecido"

    @app.get("/saude")
    def saude() -> dict[str, object]:
        return {"ok": True, "modelos": sorted(carregados)}

    @app.post("/estimar", response_model=Saida)
    def estimar_preco(entrada: Entrada, req: Request) -> dict[str, object]:
        espera = limitador.liberar(ip_do_cliente(req))
        if espera is not None:
            raise HTTPException(
                status_code=429,
                detail="Muitas consultas. Tente de novo em instantes.",
                headers={"Retry-After": str(espera)},
            )
        dados = entrada.model_dump()
        return estimar(dados.pop("negocio"), dados, carregados)

    return app
