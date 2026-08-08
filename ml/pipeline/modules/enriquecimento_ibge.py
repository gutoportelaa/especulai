"""
Enriquecimento socioeconômico via malha censitária do IBGE (Censo 2022).

Substitui os centroides/fatores de bairro hardcoded por dados reais por
setor censitário, resolvidos por point-in-polygon (lat/lon → CD_SETOR).

Entrada: CSV com colunas Latitude/Longitude (ex.: data/raw_rocha.csv).
Saída:   CSV enriquecido com features por setor censitário.

Insumos IBGE (baixados em data/ibge/, município 2211001 = Teresina):
  - Malha de setores Censo 2022 (PI_setores_CD2022.shp) → geometria, AREA_KM2,
    NM_BAIRRO (nome oficial), CD_SETOR.
  - Agregados básicos (Agregados_por_setores_basico_BR.csv):
        v0001 = total de pessoas | v0005 = média de moradores/domicílio
  - Rendimento do responsável (Agregados_por_setores_renda_responsavel_BR.csv):
        V06004 = rendimento médio mensal do responsável (R$)

Features geradas por imóvel:
  cd_setor, ibge_bairro, area_setor_km2, populacao_setor,
  densidade_populacional (hab/km²), media_moradores, renda_media_responsavel.

CRS de trabalho: EPSG:31983 (SIRGAS 2000 / UTM 23S) para operações métricas.
A malha vem em EPSG:4674; os pontos chegam em EPSG:4326 (lat/lon).
"""

from __future__ import annotations

import logging
from pathlib import Path

import geopandas as gpd
import pandas as pd

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]  # .../especulai
DATA_DIR = PROJECT_ROOT / "data"
IBGE_DIR = DATA_DIR / "ibge"

# Insumos brutos do IBGE
MALHA_SHP = IBGE_DIR / "PI_setores_CD2022.shp"
BASICO_CSV = IBGE_DIR / "Agregados_por_setores_basico_BR.csv"
RENDA_CSV = IBGE_DIR / "Agregados_por_setores_renda_responsavel_BR.csv"

# Cache enriquecido (construído uma vez)
SETORES_CACHE = IBGE_DIR / "teresina_setores_enriquecido.gpkg"

CD_MUN_TERESINA = "2211001"
CRS_METRICO = "EPSG:31983"  # UTM 23S
CRS_PONTOS = "EPSG:4326"    # lat/lon

# Colunas de features anexadas a cada imóvel
FEATURE_COLS = [
    "cd_setor", "ibge_bairro", "area_setor_km2", "populacao_setor",
    "densidade_populacional", "media_moradores", "renda_media_responsavel",
]

logger = logging.getLogger("enriquecimento_ibge")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# ============================================================================
# CONSTRUÇÃO DO CACHE DE SETORES (malha + agregados)
# ============================================================================

def _to_float(series: pd.Series, decimal: str = ".") -> pd.Series:
    """Converte série textual em float, tratando separador decimal do IBGE."""
    s = series.astype(str).str.strip()
    if decimal == ",":
        s = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(s, errors="coerce")


def build_setores_cache(force: bool = False) -> gpd.GeoDataFrame:
    """Constrói (ou carrega) a malha de Teresina enriquecida com agregados."""
    if SETORES_CACHE.exists() and not force:
        logger.info("[IBGE] Carregando cache: %s", SETORES_CACHE.name)
        return gpd.read_file(SETORES_CACHE)

    if not MALHA_SHP.exists():
        raise FileNotFoundError(
            f"Malha IBGE não encontrada em {MALHA_SHP}. "
            "Baixe PI_setores_CD2022.zip do geoftp.ibge.gov.br (censo_2022/setores/shp/UF/)."
        )

    # 1. Malha → filtra Teresina
    logger.info("[IBGE] Lendo malha de setores (PI)...")
    malha = gpd.read_file(MALHA_SHP)
    tere = malha[malha["CD_MUN"] == CD_MUN_TERESINA].copy()
    tere["CD_SETOR"] = tere["CD_SETOR"].astype(str)
    # AREA_KM2 na malha já é float64 (ponto decimal); só os CSVs de agregados usam vírgula.
    tere["area_setor_km2"] = pd.to_numeric(tere["AREA_KM2"], errors="coerce")
    setores_teresina = set(tere["CD_SETOR"])
    logger.info("[IBGE] Teresina: %d setores censitários", len(tere))

    # 2. Agregados básicos (filtra só Teresina)
    logger.info("[IBGE] Lendo agregados básicos...")
    basico = pd.read_csv(
        BASICO_CSV, sep=";", dtype=str, encoding="latin-1",
        usecols=["CD_SETOR", "v0001", "v0005"],
    )
    basico = basico[basico["CD_SETOR"].isin(setores_teresina)].copy()
    basico["populacao_setor"] = _to_float(basico["v0001"], decimal=",")
    basico["media_moradores"] = _to_float(basico["v0005"], decimal=",")

    # 3. Rendimento do responsável (filtra só Teresina; decimal '.')
    logger.info("[IBGE] Lendo rendimento do responsável...")
    renda = pd.read_csv(
        RENDA_CSV, sep=";", dtype=str, encoding="latin-1",
        usecols=["CD_SETOR", "V06004"],
    )
    renda = renda[renda["CD_SETOR"].isin(setores_teresina)].copy()
    renda["renda_media_responsavel"] = _to_float(renda["V06004"], decimal=".")

    # 4. Merge na malha
    out = tere.merge(
        basico[["CD_SETOR", "populacao_setor", "media_moradores"]], on="CD_SETOR", how="left"
    ).merge(
        renda[["CD_SETOR", "renda_media_responsavel"]], on="CD_SETOR", how="left"
    )

    # 5. Densidade populacional (hab/km²)
    out["densidade_populacional"] = (
        out["populacao_setor"] / out["area_setor_km2"].replace(0, pd.NA)
    )

    # 6. Renomeia e projeta para CRS métrico
    out = out.rename(columns={"CD_SETOR": "cd_setor", "NM_BAIRRO": "ibge_bairro"})
    keep = FEATURE_COLS + ["geometry"]
    out = out[[c for c in keep if c in out.columns]].to_crs(CRS_METRICO)

    IBGE_DIR.mkdir(parents=True, exist_ok=True)
    out.to_file(SETORES_CACHE, driver="GPKG")
    logger.info("[IBGE] ✓ Cache construído: %s (%d setores)", SETORES_CACHE.name, len(out))
    return out


# ============================================================================
# ENRIQUECIMENTO (point-in-polygon)
# ============================================================================

def enrich_with_ibge(
    df: pd.DataFrame,
    lat_col: str = "Latitude",
    lon_col: str = "Longitude",
    setores: gpd.GeoDataFrame | None = None,
) -> pd.DataFrame:
    """
    Anexa features socioeconômicas por setor censitário via point-in-polygon.

    Imóveis sem lat/lon (ou fora da malha) recebem NaN nas features —
    a coluna `geo_precision` (gerada no scraper) sinaliza a confiança.
    """
    if setores is None:
        setores = build_setores_cache()

    result = df.copy()
    mask = result[lat_col].notna() & result[lon_col].notna()
    if not mask.any():
        logger.warning("[IBGE] Nenhum imóvel com coordenadas — nada a enriquecer.")
        for col in FEATURE_COLS:
            result[col] = pd.NA
        return result

    pts = gpd.GeoDataFrame(
        result.loc[mask],
        geometry=gpd.points_from_xy(result.loc[mask, lon_col], result.loc[mask, lat_col]),
        crs=CRS_PONTOS,
    ).to_crs(setores.crs)

    joined = gpd.sjoin(pts, setores, how="left", predicate="within")
    # sjoin pode duplicar em fronteiras; mantém o primeiro match por índice
    joined = joined[~joined.index.duplicated(keep="first")]

    for col in FEATURE_COLS:
        result.loc[mask, col] = joined[col]

    encontrados = int(result["cd_setor"].notna().sum())
    logger.info("[IBGE] %d/%d imóveis associados a um setor censitário", encontrados, len(result))
    return result


# ============================================================================
# MAIN
# ============================================================================

def main(
    input_csv: Path = DATA_DIR / "raw_rocha.csv",
    output_csv: Path = DATA_DIR / "enriched_ibge_rocha.csv",
) -> Path:
    """Lê CSV geocodificado, enriquece com IBGE e grava resultado."""
    if not input_csv.exists():
        raise FileNotFoundError(f"Entrada não encontrada: {input_csv}")

    df = pd.read_csv(input_csv)
    logger.info("[IBGE] Enriquecendo %d imóveis de %s", len(df), input_csv.name)

    enriched = enrich_with_ibge(df)
    enriched.to_csv(output_csv, index=False)
    logger.info("[IBGE] ✓ Gravado: %s", output_csv)
    return output_csv


if __name__ == "__main__":
    main()
