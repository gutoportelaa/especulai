"""Inferência sem sklearn: monta o vetor de features e soma as árvores exportadas.

Espelha `ml.experiments.baseline_atributos.matriz` e `ml.experiments.renda_ibge.X_com`, o código
que o treino usa. `tests/test_space_inferencia.py` trava essa paridade contra o sklearn.

Os pesos chegam cifrados (AES-256-GCM, formato em `ml/pipeline/cifrar_modelo.py`) e só existem
em claro na memória do processo.
"""

from __future__ import annotations

import gzip
import json
import math
import struct
import unicodedata
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"ESPC1"
AAD = b"especulai-modelo-v1"
TAM_NONCE = 12
MIN_AMOSTRAS_BAIRRO = 15

Modelo = dict[str, Any]


def decifrar(blob: bytes, chave: bytes) -> dict[str, Modelo]:
    if not blob.startswith(MAGIC):
        raise ValueError("arquivo de modelo inválido")
    nonce = blob[len(MAGIC) : len(MAGIC) + TAM_NONCE]
    claro = AESGCM(chave).decrypt(nonce, blob[len(MAGIC) + TAM_NONCE :], AAD)
    return json.loads(gzip.decompress(claro))


def chave_normalizada(valor: object) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or "")).encode("ascii", "ignore").decode()
    return "".join(c for c in texto.lower() if c.isalnum())


def resolver(valor: object, colunas: list[str], prefixo: str) -> str | None:
    alvo = chave_normalizada(valor)
    if not alvo:
        return None
    for col in colunas:
        if col.startswith(prefixo) and chave_normalizada(col[len(prefixo) :]) == alvo:
            return col[len(prefixo) :]
    return None


def montar_vetor(
    entrada: dict[str, Any], modelo: Modelo
) -> tuple[list[float], str | None, bool, int]:
    colunas: list[str] = modelo["feature_columns"]
    bairro = resolver(entrada["bairro"], colunas, "Bairro_")
    tipo = resolver(entrada["tipo"], colunas, "Tipo_Imovel_")
    info = modelo["bairro_info"].get(bairro) if bairro else None
    vagas = entrada.get("vagas")

    informado = {
        "Area_m2": max(float(entrada["area"]), 1.0),
        "Quartos": float(int(entrada["quartos"])),
        "Banheiros": float(int(entrada["banheiros"])),
        "Vagas_Garagem": float(vagas or 0),
        "Vagas_informado": 0.0 if vagas is None else 1.0,
        "Renda_bairro": info["renda"] if info else -1.0,
        "Densidade_bairro": info["densidade"] if info else -1.0,
        "IBGE_casou": info["casou"] if info else 0.0,
    }
    ativas = {f"Bairro_{bairro}" if bairro else "", f"Tipo_Imovel_{tipo}" if tipo else ""}
    vetor = [informado[c] if c in informado else float(c in ativas) for c in colunas]
    return vetor, bairro, tipo is not None, int(info["n"]) if info else 0


def _float32(valor: float) -> float:
    return struct.unpack("f", struct.pack("f", valor))[0]


def prever_log(vetor: list[float], modelo: Modelo) -> float:
    """As árvores do sklearn comparam X já em float32 contra threshold em float64."""
    x = [_float32(v) for v in vetor]
    t = modelo["trees"]
    soma = 0.0
    for raiz in t["roots"]:
        no = raiz
        while t["feature"][no] != -1:
            no = t["left"][no] if x[t["feature"][no]] <= t["threshold"][no] else t["right"][no]
        soma += t["value"][no]
    return modelo["init"] + modelo["learning_rate"] * soma


def intervalo(preco: float, cfg: dict[str, Any]) -> tuple[float, float]:
    """Meia-largura em log por terço de preço previsto; o corte pertence à faixa de baixo."""
    faixa = sum(1 for c in cfg["cortes"] if c < preco)
    w = cfg["meia_largura"][faixa]
    return preco * math.exp(-w), preco * math.exp(w)


def confianca(achou_bairro: bool, achou_tipo: bool, n: int, area: float) -> str:
    if not achou_bairro:
        return "baixa"
    if not achou_tipo or n < MIN_AMOSTRAS_BAIRRO or area < 15 or area > 1000:
        return "média"
    return "alta"


def arredondar(valor: float) -> int:
    """Faixa de preço pedido não precisa de centavos; arredondar também reduz o que uma
    sequência de consultas revelaria do modelo."""
    passo = 1000 if valor >= 10_000 else 10
    return int(round(valor / passo) * passo)


def estimar(negocio: str, entrada: dict[str, Any], modelos: dict[str, Modelo]) -> dict[str, Any]:
    modelo = modelos[negocio]
    vetor, bairro, achou_tipo, n = montar_vetor(entrada, modelo)
    preco = math.exp(prever_log(vetor, modelo))
    minimo, maximo = intervalo(preco, modelo["intervalo"])
    return {
        "negocio": negocio,
        "preco_estimado": arredondar(preco),
        "minimo": arredondar(minimo),
        "maximo": arredondar(maximo),
        "nivel": modelo["intervalo"]["nivel"],
        "confianca": confianca(bairro is not None, achou_tipo, n, max(float(entrada["area"]), 1.0)),
    }
