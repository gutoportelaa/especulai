"""
Enriquecimento geoespacial de dados OLX.

Entrada: raw_olx.csv (dados brutos do scraper)
Saída: enriched_geo_olx.csv (com Latitude, Longitude, distâncias a POIs)

Responsabilidades:
  - Geocodificação de CEP/Bairro → Latitude/Longitude (Nominatim)
  - Cálculo de distâncias para POIs (farmácias, escolas, etc)
  - Cache local para evitar rate limiting
  - Fallback para coordenadas por bairro

Não faz: Validação de dados brutos, limpeza
"""

import math
import os
import random
import time
from pathlib import Path
from typing import Dict, Optional, Tuple
import logging

import pandas as pd
from geopy.distance import geodesic
from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
DATA_DIR = WORKSPACE_ROOT / "dados_imoveis_teresina"

# Entrada: dados brutos OLX
INPUT_FILE = DATA_DIR / "raw_olx.csv"

# Saída: dados geoespacialmente enriquecidos
OUTPUT_FILE = DATA_DIR / "enriched_geo_olx.csv"

# Cache de geocodificação
GEOCODE_CACHE_FILE = DATA_DIR / "geocode_cache.csv"

# Log do módulo
GEO_LOG_FILE = DATA_DIR / "enriquecimento_geo_log.txt"

# Configurações de geocodificação
NOMINATIM_USER_AGENT = "SpeculaiTeresina_v1"
CITY_CONTEXT = "Teresina, Piauí, Brasil"
CITY_DEFAULT_COORD = (-5.089205, -42.801637)  # Praça da Bandeira

# POIs de referência (localização central de Teresina)
POI_REFERENCE_POINTS = {
    "farmacias": (-5.082138, -42.806885),      # Av. Frei Serafim
    "escolas": (-5.068953, -42.783498),        # Região Ininga
    "mercados": (-5.083777, -42.772114),       # Riverside/Noivos
    "hospitais": (-5.059088, -42.80188),       # HBB / Zoobotânico
}

# Fallback de coordenadas por bairro (em caso de falha de geocodificação)
BAIRRO_FALLBACK_COORDS = {
    "Fátima": (-5.077965, -42.788315),
    "Jóquei Clube": (-5.057399, -42.793197),
    "Ininga": (-5.045485, -42.780154),
    "Morada do Sol": (-5.038217, -42.786225),
    "Ilhotas": (-5.080778, -42.818173),
    "Centro": (-5.090205, -42.812948),
    "Piçarra": (-5.105407, -42.805934),
    "Horto": (-5.037838, -42.802402),
    "Noivos": (-5.071928, -42.781216),
    "Santa Isabel": (-5.064422, -42.725183),
    "Uruguai": (-5.070633, -42.736927),
    "Socopo": (-5.062049, -42.703742),
}

# Inicializa o geocodificador Nominatim
geolocator = Nominatim(user_agent=NOMINATIM_USER_AGENT)

# ============================================================================
# LOGGING
# ============================================================================

def setup_logging():
    """Configura logging para arquivo e console."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(GEO_LOG_FILE, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


logger = setup_logging()

# ============================================================================
# UTILITÁRIOS
# ============================================================================

def is_valid_text(value) -> bool:
    """Verifica se um valor é texto válido (não é None, NaN ou vazio)."""
    if value is None:
        return False
    if isinstance(value, float) and math.isnan(value):
        return False
    text = str(value).strip()
    return text not in ("", "nan", "none", "Nan")


def normalize_key(value) -> Optional[str]:
    """Normaliza texto para uso como chave de cache."""
    if not is_valid_text(value):
        return None
    text = str(value).strip().lower()
    normalized = text.replace(" ", "_").replace("-", "")
    return normalized or None


# ============================================================================
# CACHE DE GEOCODIFICAÇÃO
# ============================================================================

def load_geocode_cache() -> Dict[str, Tuple[float, float]]:
    """Carrega cache de geocodificação do disco."""
    if not GEOCODE_CACHE_FILE.exists():
        logger.info("[CACHE] Nenhum cache anterior encontrado")
        return {}
    
    try:
        df_cache = pd.read_csv(GEOCODE_CACHE_FILE)
        cache = {
            row["key"]: (row["latitude"], row["longitude"])
            for _, row in df_cache.iterrows()
        }
        logger.info(f"[CACHE] Carregadas {len(cache)} entradas do cache")
        return cache
    except Exception as e:
        logger.warning(f"[CACHE] Erro ao carregar cache: {e}")
        return {}


def save_geocode_cache(cache: Dict[str, Tuple[float, float]]):
    """Salva cache de geocodificação em disco."""
    if not cache:
        return
    
    df_cache = pd.DataFrame(
        [
            {"key": key, "latitude": lat, "longitude": lon}
            for key, (lat, lon) in cache.items()
        ]
    )
    
    try:
        df_cache.to_csv(GEOCODE_CACHE_FILE, index=False)
        logger.info(f"[CACHE] Cache salvo com {len(cache)} entradas")
    except Exception as e:
        logger.error(f"[CACHE] Erro ao salvar cache: {e}")


# ============================================================================
# GEOCODIFICAÇÃO (Nominatim/OpenStreetMap)
# ============================================================================

def geocode_location_api(cep: str, bairro: str) -> Optional[Tuple[float, float]]:
    """
    Converte CEP ou Bairro em coordenadas (Latitude, Longitude).
    
    Estratégia:
      1. Tenta CEP (mais específico)
      2. Fallback para Bairro (menos específico)
      3. Respeita rate limiting (~1 req/seg)
    
    Args:
        cep: CEP do imóvel
        bairro: Bairro do imóvel
    
    Returns:
        Tupla (lat, lon) ou None se falhar
    """
    # 1. Tenta geocodificar pelo CEP
    if is_valid_text(cep):
        query_cep = f"{cep}, {CITY_CONTEXT}"
        try:
            logger.debug(f"[GEOCODE] Geocodificando CEP: {cep}")
            location = geolocator.geocode(query_cep, timeout=10)
            if location:
                logger.debug(f"[GEOCODE] ✓ Sucesso com CEP: {cep}")
                return (location.latitude, location.longitude)
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.debug(f"[GEOCODE] Falha na API (CEP {cep}): {e}. Tentando Bairro...")
        except Exception as e:
            logger.debug(f"[GEOCODE] Erro inesperado (CEP {cep}): {e}. Tentando Bairro...")

    # 2. Fallback: Tenta geocodificar pelo Bairro
    if is_valid_text(bairro):
        query_bairro = f"{bairro}, {CITY_CONTEXT}"
        try:
            logger.debug(f"[GEOCODE] Geocodificando Bairro: {bairro}")
            location = geolocator.geocode(query_bairro, timeout=10)
            if location:
                logger.debug(f"[GEOCODE] ✓ Sucesso com Bairro: {bairro}")
                return (location.latitude, location.longitude)
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.warning(f"[GEOCODE] Falha na API (Bairro {bairro}): {e}")
            return None
        except Exception as e:
            logger.warning(f"[GEOCODE] Erro inesperado (Bairro {bairro}): {e}")
            return None
    
    return None


def resolve_coordinates(
    cep: str,
    bairro: str,
    cache: Dict[str, Tuple[float, float]],
    use_api: bool = True
) -> Tuple[Tuple[float, float], bool]:
    """
    Resolve coordenadas para um endereço (com cache e fallback).
    
    Args:
        cep: CEP
        bairro: Bairro
        cache: Cache de geocodificação
        use_api: Se True, usa API Nominatim; se False, usa apenas fallback
    
    Returns:
        Tupla (coordenadas, foi_atualizado_cache)
    """
    key_cep = normalize_key(cep) if isinstance(cep, str) else None
    key_bairro = normalize_key(bairro)
    updated = False

    # 1. Verifica cache primeiro
    for key in (key_cep, key_bairro):
        if key and key in cache:
            logger.debug(f"[RESOLVE] Cache hit: {key}")
            return cache[key], updated

    # 2. Tenta API se habilitada
    coords = None
    if use_api:
        coords = geocode_location_api(cep, bairro)
        if coords:
            for key in (key_cep, key_bairro):
                if key:
                    cache[key] = coords
                    updated = True
            # Delay para respeitar rate limit do Nominatim (~1 req/seg)
            time.sleep(random.uniform(1.0, 1.5))
            return coords, updated

    # 3. Fallback para coordenadas por bairro
    if bairro and bairro in BAIRRO_FALLBACK_COORDS:
        coords = BAIRRO_FALLBACK_COORDS[bairro]
        if key_bairro:
            cache[key_bairro] = coords
            updated = True
        logger.debug(f"[RESOLVE] Usando fallback bairro: {bairro}")
        return coords, updated

    # 4. Fallback final: coordenada padrão (Centro de Teresina)
    logger.debug(f"[RESOLVE] Usando fallback padrão (centro) para CEP={cep}, Bairro={bairro}")
    return CITY_DEFAULT_COORD, updated


# ============================================================================
# CÁLCULO DE FEATURES GEOESPACIAIS
# ============================================================================

def compute_poi_features(lat: float, lon: float) -> Dict[str, float]:
    """
    Calcula features geoespaciais baseadas em POIs.
    
    Features:
      - distancia_farmacias: Distância em metros até POI de farmácias
      - distancia_escolas: Distância em metros até POI de escolas
      - distancia_mercados: Distância em metros até POI de mercados
      - distancia_hospitais: Distância em metros até POI de hospitais
      - score_comercial: Score (0-4) que premia proximidade a comércios
    
    Args:
        lat: Latitude
        lon: Longitude
    
    Returns:
        Dicionário com features calculadas
    """
    features: Dict[str, float] = {}
    
    # Calcula distância para cada POI
    for key, ref_coord in POI_REFERENCE_POINTS.items():
        try:
            dist = geodesic((lat, lon), ref_coord).meters
        except ValueError:
            dist = 9999.0
        features[f"distancia_{key}"] = round(dist, 2)

    # Score comercial (0-4): premia proximidade a comércios
    score = 0
    for key in ("farmacias", "mercados"):
        distance = features.get(f"distancia_{key}", 9999)
        if distance <= 800:
            score += 2
        elif distance <= 1500:
            score += 1
    
    features["score_comercial"] = score
    
    return features


# ============================================================================
# ENRIQUECIMENTO
# ============================================================================

def enrich_data(df: pd.DataFrame, skip_api: bool = False) -> pd.DataFrame:
    """
    Enriquece dados com informações geoespaciais.
    
    Args:
        df: DataFrame com dados brutos
        skip_api: Se True, usa apenas cache e fallback (mais rápido, menos preciso)
    
    Returns:
        DataFrame enriquecido
    """
    logger.info(f"[ENRICH] Iniciando enriquecimento de {len(df)} registros")
    
    # Inicializa colunas de coordenadas e POIs
    df['Latitude'] = None
    df['Longitude'] = None
    
    poi_cols = [
        'distancia_farmacias',
        'distancia_escolas',
        'distancia_mercados',
        'distancia_hospitais',
        'score_comercial'
    ]
    for col in poi_cols:
        df[col] = None
    
    # Carrega cache anterior
    cache = load_geocode_cache()
    cache_updated = False

    # Processa cada registro
    for index, row in df.iterrows():
        if (index + 1) % 10 == 0:
            logger.info(f"[ENRICH] Processando imóvel {index + 1}/{len(df)}")
        
        # 1. Geocodificação
        coords, updated = resolve_coordinates(
            row.get('CEP', ''),
            row.get('Bairro', ''),
            cache,
            use_api=not skip_api
        )
        cache_updated = cache_updated or updated
        
        if coords:
            lat, lon = coords
            df.loc[index, 'Latitude'] = lat
            df.loc[index, 'Longitude'] = lon
            
            # 2. Cálculo de POIs
            pois_features = compute_poi_features(lat, lon)
            
            # 3. Adiciona features ao DataFrame
            for key, value in pois_features.items():
                df.loc[index, key] = value
        else:
            logger.warning(f"[ENRICH] Falha de geocodificação: CEP={row.get('CEP')}, Bairro={row.get('Bairro')}")

    # Salva cache atualizado
    if cache_updated:
        save_geocode_cache(cache)
    
    logger.info(f"[ENRICH] ✓ Enriquecimento concluído")
    
    return df


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Função principal do módulo de enriquecimento geoespacial."""
    print()
    print("=" * 80)
    print("=== ESPECULAI - ENRIQUECIMENTO GEOESPACIAL (OLX) ===")
    print("=" * 80)
    print()
    
    # Validação de entrada
    if not INPUT_FILE.exists():
        logger.error(f"Arquivo de entrada não encontrado: {INPUT_FILE}")
        logger.error("Execute o scraper OLX (scraper_olx.py) primeiro.")
        raise FileNotFoundError(f"Dataset {INPUT_FILE} não encontrado")

    logger.info(f"[MAIN] Lendo dados brutos de: {INPUT_FILE}")
    df_raw = pd.read_csv(INPUT_FILE)
    logger.info(f"[MAIN] {len(df_raw)} registros carregados")
    
    # Validação de schema
    required_cols = ['CEP', 'Bairro']
    missing_cols = [col for col in required_cols if col not in df_raw.columns]
    if missing_cols:
        logger.error(f"Colunas obrigatórias faltando: {missing_cols}")
        raise ValueError(f"Schema inválido: faltam colunas {missing_cols}")

    # Enriquecimento
    df_enriched = enrich_data(df_raw, skip_api=False)
    
    # Salva resultado
    df_enriched.to_csv(OUTPUT_FILE, index=False)
    logger.info(f"[MAIN] Dados enriquecidos salvos em: {OUTPUT_FILE}")
    
    print()
    print("=" * 80)
    print("[OK] Enriquecimento geoespacial concluído!")
    print(f"[OK] Arquivo: {OUTPUT_FILE}")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()
