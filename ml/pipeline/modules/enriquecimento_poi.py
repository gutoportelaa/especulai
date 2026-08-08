"""Enriquecimento por pontos de interesse reais do OpenStreetMap.

Substitui o `enriquecimento_geoespacial.py`, que mede distância até quatro pontos
fixos escritos à mão e, por isso, não informa acesso a serviço nenhum — apenas
reencoda a posição.

Aqui as distâncias são até o equipamento **mais próximo de fato**, resolvidas por
KDTree sobre a extração do Overpass.

O snapshot de POIs é versionado em disco de propósito. O OSM muda todo dia; sem
congelar, `make train` deixa de ser reproduzível e as métricas publicadas mudam
sozinhas. Use `--refresh` para buscar uma extração nova, que vira um arquivo com
data própria.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from scipy.spatial import cKDTree

from config.paths import DATA_ROOT

logger = logging.getLogger(__name__)

POI_DIR = DATA_ROOT / "pois"
SNAPSHOT_GLOB = "pois_teresina_*.json"

# A instância principal do Overpass cai com frequência; a kumi costuma responder.
OVERPASS_ENDPOINTS = (
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
)
# Overpass devolve 406 sem User-Agent próprio.
OVERPASS_UA = {"User-Agent": "especulai/0.2 (https://github.com/gutoportelaa/especulai)"}

CATEGORIAS = {
    "farmacias": '["amenity"="pharmacy"]',
    "escolas": '["amenity"="school"]',
    "mercados": '["shop"="supermarket"]',
    "hospitais": '["amenity"="hospital"]',
    "shoppings": '["shop"="mall"]',
    "restaurantes": '["amenity"="restaurant"]',
    "bancos": '["amenity"="bank"]',
    "pracas": '["leisure"="park"]',
}

# Raios de contagem: densidade de equipamentos importa além da distância ao mais
# próximo — um imóvel com 8 mercados a 1 km não é como um com apenas 1.
RAIOS_CONTAGEM_M = (500, 1000, 2000)

# Projeção local equiretangular. Teresina tem ~15 km de extensão; o erro contra
# uma projeção métrica de verdade fica abaixo de 0,1%, e evita depender de pyproj.
LAT_REFERENCIA = -5.09
METROS_POR_GRAU_LAT = 111_320.0


def _projetar(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    metros_por_grau_lon = METROS_POR_GRAU_LAT * np.cos(np.radians(LAT_REFERENCIA))
    return np.c_[np.asarray(lon) * metros_por_grau_lon, np.asarray(lat) * METROS_POR_GRAU_LAT]


def _montar_consulta() -> str:
    blocos = []
    for filtro in CATEGORIAS.values():
        blocos.append(f"  node{filtro}(area.a);")
        blocos.append(f"  way{filtro}(area.a);")
    corpo = "\n".join(blocos)
    return (
        "[out:json][timeout:180];\n"
        'area["name"="Teresina"]["admin_level"="8"]->.a;\n'
        f"(\n{corpo}\n);\n"
        "out center tags;"
    )


def _categoria(tags: dict) -> str | None:
    for nome, filtro in CATEGORIAS.items():
        chave, valor = filtro.strip('[]').replace('"', "").split("=")
        if tags.get(chave) == valor:
            return nome
    return None


def baixar_pois() -> list[dict]:
    """Extrai POIs do Overpass, tentando os endpoints em ordem."""
    consulta = _montar_consulta()
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            resp = requests.post(endpoint, data={"data": consulta},
                                 headers=OVERPASS_UA, timeout=240)
            if resp.status_code != 200:
                logger.warning("[POI] %s -> HTTP %s", endpoint, resp.status_code)
                continue
            elementos = resp.json()["elements"]
            break
        except (requests.RequestException, ValueError, KeyError) as exc:
            logger.warning("[POI] %s falhou: %s", endpoint, exc)
    else:
        raise RuntimeError("Nenhum endpoint do Overpass respondeu.")

    pois = []
    for elemento in elementos:
        lat = elemento.get("lat") or (elemento.get("center") or {}).get("lat")
        lon = elemento.get("lon") or (elemento.get("center") or {}).get("lon")
        categoria = _categoria(elemento.get("tags", {}))
        if lat is None or lon is None or categoria is None:
            continue
        pois.append({
            "categoria": categoria, "lat": float(lat), "lon": float(lon),
            "nome": elemento.get("tags", {}).get("name", ""),
        })
    return pois


def snapshot_mais_recente() -> Path | None:
    candidatos = sorted(POI_DIR.glob(SNAPSHOT_GLOB))
    return candidatos[-1] if candidatos else None


def carregar_pois(refresh: bool = False) -> pd.DataFrame:
    """Devolve os POIs do snapshot mais recente, baixando se necessário."""
    caminho = snapshot_mais_recente()
    if refresh or caminho is None:
        pois = baixar_pois()
        POI_DIR.mkdir(parents=True, exist_ok=True)
        caminho = POI_DIR / f"pois_teresina_{date.today():%Y%m%d}.json"
        caminho.write_text(json.dumps(pois, ensure_ascii=False), encoding="utf-8")
        logger.info("[POI] Snapshot novo: %s (%d pontos)", caminho.name, len(pois))
    else:
        pois = json.loads(caminho.read_text(encoding="utf-8"))
        logger.info("[POI] Snapshot em uso: %s (%d pontos)", caminho.name, len(pois))
    return pd.DataFrame(pois)


def enriquecer(df: pd.DataFrame, refresh: bool = False) -> pd.DataFrame:
    """Acrescenta distância ao POI mais próximo e contagens por raio.

    Espera colunas `Latitude` e `Longitude`. Imóveis sem coordenada recebem NaN,
    para não fingir precisão que não existe.
    """
    pois = carregar_pois(refresh=refresh)
    resultado = df.copy()

    valido = df["Latitude"].notna() & df["Longitude"].notna()
    pontos = _projetar(df.loc[valido, "Latitude"].values, df.loc[valido, "Longitude"].values)

    for categoria, grupo in pois.groupby("categoria"):
        arvore = cKDTree(_projetar(grupo["lat"].values, grupo["lon"].values))

        distancia = np.full(len(df), np.nan)
        distancia[valido.values] = arvore.query(pontos, k=1)[0]
        resultado[f"poi_dist_{categoria}"] = distancia

        for raio in RAIOS_CONTAGEM_M:
            contagem = np.full(len(df), np.nan)
            contagem[valido.values] = [len(i) for i in arvore.query_ball_point(pontos, raio)]
            resultado[f"poi_n{raio}m_{categoria}"] = contagem

    logger.info("[POI] %d categorias x %d features por categoria",
                pois["categoria"].nunique(), 1 + len(RAIOS_CONTAGEM_M))
    return resultado


def main() -> None:
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    p = argparse.ArgumentParser(description="Snapshot e enriquecimento de POIs (OSM)")
    p.add_argument("--refresh", action="store_true", help="baixa extração nova do Overpass")
    args = p.parse_args()

    pois = carregar_pois(refresh=args.refresh)
    print(pois.groupby("categoria").size().to_string())
    print(f"\ntotal: {len(pois)} pontos")


if __name__ == "__main__":
    main()
