"""Mapa de bairros do site: polígonos do IBGE, agregados fora da amostra e um imóvel padrão.

Os polígonos vêm da malha de bairros do Censo 2022 (pública, baixada para `data/ibge/` e
conferida pelo SHA-256). São simplificados em conjunto (as divisas continuam encaixadas) e já
projetados em coordenadas de SVG, então o site só desenha `<path d>`, sem biblioteca de mapa.

Por bairro e negócio saem:
  - contagem de anúncios e imóveis (sempre);
  - R$/m² pedido mediano, erro e viés medianos e cobertura da faixa, fora da amostra, só com
    `MIN_AGREGADO` imóveis ou mais (`treino_final.por_bairro`);
  - até dois anúncios sorteados, só com `MIN_EXEMPLO` imóveis ou mais, descritos e arredondados:
    tipo, área em múltiplos de 5 m², quartos, preço pedido com 2 algarismos significativos e a
    faixa que o modelo deu sem ter visto o anúncio. Nada de rua, coordenada, URL ou anunciante;
  - a faixa de um imóvel padrão (`PADRAO`), calculada pelo modelo publicado, e a confiança que a
    API daria. Pré-calculada aqui porque o site não tem o modelo e a API limita consultas.

Anúncios cujo bairro não casa com a malha ficam fora do mapa e são contados em `fora_da_malha`.

Uso: chamado por `export_web` (make cifrar-modelo); sozinho, uv run python -m ml.pipeline.mapa_bairros
"""

from __future__ import annotations

import hashlib
import json
import math
import urllib.request
from typing import Any, cast

import geopandas as gpd
import joblib
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry

from config.paths import ARTIFACT_DIR, DATA_ROOT, PROJECT_ROOT
from ml.experiments.renda_ibge import COD_TERESINA, X_com, _chave, com_ibge
from ml.pipeline.treino_final import MIN_AGREGADO, MIN_EXEMPLO

MALHA = DATA_ROOT / "ibge" / "PI_bairros_CD2022.gpkg"
MALHA_URL = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/"
    "malhas_de_setores_censitarios__divisoes_intramunicipais/censo_2022/bairros/gpkg/UF/PI/"
    "PI_bairros_CD2022.gpkg"
)
MALHA_SHA256 = "cfd26ee37c8ca666e12eb5719ebdb2e0f7b108ded722cadc716e2ee82e347309"
SITE_MAPA = PROJECT_ROOT / "frontend" / "src" / "features" / "conteudo" / "mapa-bairros.json"
NEGOCIOS = ("venda", "aluguel")

CRS_METRICO = "EPSG:31983"  # SIRGAS 2000 / UTM 23S: Teresina inteira, distâncias em metros
TOLERANCIA_M = 25.0
LARGURA = 600
MIN_AMOSTRAS_BAIRRO = 15  # espelha deploy/worker/src/inferencia.js
PADRAO = {
    "Tipo_Imovel": "Apartamento",
    "Area_m2": 70,
    "Quartos": 2,
    "Banheiros": 2,
    "Vagas_Garagem": 1,
}


def baixar_malha() -> None:
    if not MALHA.exists():
        MALHA.parent.mkdir(parents=True, exist_ok=True)
        print(f"[..] baixando {MALHA.name} do IBGE")
        urllib.request.urlretrieve(MALHA_URL, MALHA)
    digest = hashlib.sha256(MALHA.read_bytes()).hexdigest()
    if digest != MALHA_SHA256:
        raise ValueError(f"{MALHA.name}: SHA-256 {digest} não confere com o publicado pelo IBGE")


def poligonos() -> gpd.GeoDataFrame:
    """Bairros de Teresina em metros, simplificados sem abrir frestas entre vizinhos."""
    baixar_malha()
    malha = gpd.read_file(MALHA)
    teresina = malha.loc[malha["CD_MUN"] == COD_TERESINA]
    ordem = np.argsort(teresina["CD_BAIRRO"].to_numpy(), kind="stable")
    g = gpd.GeoDataFrame(teresina.iloc[ordem], geometry="geometry").to_crs(CRS_METRICO)
    g = cast(gpd.GeoDataFrame, g.reset_index(drop=True))
    g["geometry"] = shapely.coverage_simplify(g.geometry.to_numpy(), TOLERANCIA_M)
    return g


def _arredondar(valor: float) -> int:
    """Mesmo arredondamento da API (deploy/worker/src/inferencia.js)."""
    passo = 1000 if valor >= 10_000 else 10
    return int(round(valor / passo) * passo)


def _significativos(valor: float, algarismos: int = 2) -> int:
    casas = algarismos - 1 - math.floor(math.log10(abs(valor)))
    return int(round(valor, casas))


def _m2(valor: float) -> float:
    return float(int(round(valor, -1))) if valor >= 100 else round(valor, 1)


class Projecao:
    """Metros (UTM) para coordenadas de SVG com y para baixo, na largura `LARGURA`."""

    def __init__(self, limites: np.ndarray) -> None:
        self.x0, self.y0, x1, self.y1 = (float(v) for v in limites)
        self.escala = LARGURA / (x1 - self.x0)
        self.altura = int(math.ceil((self.y1 - self.y0) * self.escala))

    def ponto(self, x: float, y: float) -> tuple[float, float]:
        return round((x - self.x0) * self.escala, 1), round((self.y1 - y) * self.escala, 1)

    def caminho(self, geom: BaseGeometry) -> str:
        if not isinstance(geom, Polygon | MultiPolygon):
            raise TypeError(f"bairro com geometria {geom.geom_type}, esperado polígono")
        partes = geom.geoms if isinstance(geom, MultiPolygon) else [geom]
        aneis = [a for p in partes for a in (p.exterior, *p.interiors)]
        trechos = []
        for anel in aneis:
            pts = [self.ponto(x, y) for x, y in anel.coords[:-1]]
            corpo = " ".join(f"{x:g} {y:g}" for x, y in pts)
            trechos.append(f"M{corpo}Z")
        return "".join(trechos)


def _confianca(achou_bairro: bool, achou_tipo: bool, n: int, area: float) -> str:
    """Espelha confianca() em deploy/worker/src/inferencia.js."""
    if not achou_bairro:
        return "baixa"
    if not achou_tipo or n < MIN_AMOSTRAS_BAIRRO or area < 15 or area > 1000:
        return "média"
    return "alta"


def _nome_no_modelo(
    chaves: list[str], nomes_ibge: list[str], contagem: dict[str, int]
) -> list[str]:
    """Nome do bairro como o modelo o conhece (o mais anunciado com a mesma chave), ou o do IBGE."""
    melhor: dict[str, tuple[int, str]] = {}
    for nome, n in contagem.items():
        k = _chave(nome)
        if k not in melhor or n > melhor[k][0]:
            melhor[k] = (n, nome)
    return [
        melhor[k][1] if k in melhor else nome for k, nome in zip(chaves, nomes_ibge, strict=True)
    ]


def imovel_padrao(artefato: dict[str, Any], nomes: list[str]) -> list[dict[str, object]]:
    colunas: list[str] = list(artefato["columns"])
    df = pd.DataFrame([{**PADRAO, "Bairro": nome} for nome in nomes])
    pred = np.exp(artefato["model"].predict(X_com(com_ibge(df), colunas, True)))
    iv = artefato["intervalos"]
    w = np.asarray(iv["meia_largura"])[np.searchsorted(iv["cortes"], pred)]
    contagem = artefato["contagem_bairro"]
    achou_tipo = f"Tipo_Imovel_{PADRAO['Tipo_Imovel']}" in colunas
    return [
        {
            "central": _arredondar(p),
            "minimo": _arredondar(p * math.exp(-wi)),
            "maximo": _arredondar(p * math.exp(wi)),
            "confianca": _confianca(
                f"Bairro_{nome}" in colunas, achou_tipo, contagem.get(nome, 0), PADRAO["Area_m2"]
            ),
        }
        for nome, p, wi in zip(nomes, pred, w, strict=True)
    ]


def _exemplo(e: dict[str, Any]) -> dict[str, object]:
    pedido = _significativos(e["pedido"])
    minimo, maximo = _arredondar(e["minimo"]), _arredondar(e["maximo"])
    return {
        "tipo": e["tipo"],
        "area": int(5 * round(e["area"] / 5)),
        "quartos": e["quartos"],
        "pedido": pedido,
        "central": _arredondar(e["previsto"]),
        "minimo": minimo,
        "maximo": maximo,
        # Pelo valor que o leitor vê: arredondado, um pedido na borda não pode parecer o contrário.
        "dentro": minimo <= pedido <= maximo,
    }


def _negocio(agregado: dict[str, Any] | None, padrao: dict[str, object]) -> dict[str, object]:
    a = agregado or {"anuncios": 0, "imoveis": 0}
    saida: dict[str, object] = {"anuncios": a["anuncios"], "imoveis": a["imoveis"]}
    if a["imoveis"] >= MIN_AGREGADO and "m2" in a:
        saida |= {
            "m2": _m2(a["m2"]),
            "erro": round(a["erro"], 3),
            "vies": round(a["vies"], 3),
            "cobertura": round(a["cobertura"], 3),
        }
    if a["imoveis"] >= MIN_EXEMPLO and "exemplos" in a:
        saida["exemplos"] = [_exemplo(e) for e in a["exemplos"]]
    saida["padrao"] = padrao
    return saida


def gerar(artefatos: dict[str, dict[str, Any]]) -> dict[str, Any]:
    g = poligonos()
    proj = Projecao(g.total_bounds)
    chaves = [_chave(n) for n in g["NM_BAIRRO"]]
    nomes_ibge = [str(n) for n in g["NM_BAIRRO"]]

    por_negocio: dict[str, list[dict[str, object]]] = {}
    fora: dict[str, int] = {}
    for n in NEGOCIOS:
        art = artefatos[n]
        nomes = _nome_no_modelo(chaves, nomes_ibge, art["contagem_bairro"])
        padroes = imovel_padrao(art, nomes)
        agregados: dict[str, dict[str, Any]] = art["por_bairro"]
        por_negocio[n] = [
            _negocio(agregados.get(k), p) for k, p in zip(chaves, padroes, strict=True)
        ]
        fora[n] = sum(v["anuncios"] for k, v in agregados.items() if k not in set(chaves))

    bairros = []
    geometrias: list[BaseGeometry] = list(g.geometry)
    for i, (codigo, geom) in enumerate(zip(g["CD_BAIRRO"], geometrias, strict=True)):
        ponto = geom.representative_point()
        x, y = proj.ponto(ponto.x, ponto.y)
        bairros.append(
            {
                "id": str(codigo),
                "nome": nomes_ibge[i],
                "d": proj.caminho(geom),
                "x": x,
                "y": y,
                **{n: por_negocio[n][i] for n in NEGOCIOS},
            }
        )

    return {
        "fonte": "IBGE, malha de bairros do Censo 2022",
        "modelo": {n: artefatos[n]["impressao"] for n in NEGOCIOS},
        "largura": LARGURA,
        "altura": proj.altura,
        "contorno": proj.caminho(shapely.union_all(g.geometry.to_numpy())),
        "padrao": {
            "tipo": PADRAO["Tipo_Imovel"],
            "area": PADRAO["Area_m2"],
            "quartos": PADRAO["Quartos"],
            "banheiros": PADRAO["Banheiros"],
            "vagas": PADRAO["Vagas_Garagem"],
        },
        "minimos": {"agregado": MIN_AGREGADO, "exemplo": MIN_EXEMPLO},
        "fora_da_malha": fora,
        "bairros": bairros,
    }


def carregar_artefatos() -> dict[str, dict[str, Any]]:
    return {n: joblib.load(ARTIFACT_DIR / f"final_{n}.joblib") for n in NEGOCIOS}


def main() -> None:
    mapa = gerar(carregar_artefatos())
    SITE_MAPA.write_text(
        json.dumps(mapa, ensure_ascii=False, separators=(",", ":")) + "\n", "utf-8"
    )
    kb = SITE_MAPA.stat().st_size / 1024
    print(
        f"[OK] {SITE_MAPA.relative_to(PROJECT_ROOT)}: {len(mapa['bairros'])} bairros, {kb:.0f} KB"
    )


if __name__ == "__main__":
    main()
