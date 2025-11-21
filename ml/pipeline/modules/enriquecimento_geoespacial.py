import math
import os
import random
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd
from geopy.distance import geodesic
from geopy.exc import GeocoderServiceError, GeocoderTimedOut
from geopy.geocoders import Nominatim

# Configurações
WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
DATA_DIR = WORKSPACE_ROOT / "dados_imoveis_teresina"
INPUT_FILE = DATA_DIR / "rocha_rocha_raw.csv"
OUTPUT_FILE = DATA_DIR / "enriched_geo_data.csv"
GEOCODE_CACHE_FILE = DATA_DIR / "geocode_cache.csv"
NOMINATIM_USER_AGENT = "ImovelTeresinaPredictor_v1"
CITY_CONTEXT = "Teresina, Piauí, Brasil"
CITY_DEFAULT_COORD = (-5.089205, -42.801637)  # Praça da Bandeira

POI_REFERENCE_POINTS = {
    "farmacias": (-5.082138, -42.806885),   # Av. Frei Serafim
    "escolas": (-5.068953, -42.783498),     # Região Ininga
    "mercados": (-5.083777, -42.772114),    # Riverside/Noivos
    "hospitais": (-5.059088, -42.80188),    # HBB / Zoobotânico
}

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


def is_valid_text(value) -> bool:
    if value is None:
        return False
    if isinstance(value, float) and math.isnan(value):
        return False
    text = str(value).strip()
    return text not in ("", "nan", "none")


def normalize_key(value) -> Optional[str]:
    if not is_valid_text(value):
        return None
    text = str(value).strip().lower()
    normalized = text.replace(" ", "_").replace("-", "")
    return normalized or None


def load_geocode_cache() -> Dict[str, Tuple[float, float]]:
    if not GEOCODE_CACHE_FILE.exists():
        return {}
    try:
        df_cache = pd.read_csv(GEOCODE_CACHE_FILE)
        cache = {
            row["key"]: (row["latitude"], row["longitude"])
            for _, row in df_cache.iterrows()
        }
        return cache
    except Exception:
        return {}


def save_geocode_cache(cache: Dict[str, Tuple[float, float]]):
    if not cache:
        return
    df_cache = pd.DataFrame(
        [
            {"key": key, "latitude": lat, "longitude": lon}
            for key, (lat, lon) in cache.items()
        ]
    )
    df_cache.to_csv(GEOCODE_CACHE_FILE, index=False)


def geocode_location_api(cep: str, bairro: str) -> Optional[Tuple[float, float]]:
    """
    Converte CEP ou Bairro em coordenadas (Latitude, Longitude) com fallback.
    Implementa delay para respeitar limites da API.
    """
    # 1. Tenta geocodificar pelo CEP
    if is_valid_text(cep):
        query_cep = f"{cep}, {CITY_CONTEXT}"
        try:
            location = geolocator.geocode(query_cep, timeout=10)
            if location:
                print(f"  -> Geocodificado por CEP: {cep}")
                return (location.latitude, location.longitude)
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            print(f"  -> Erro ao geocodificar CEP {cep}: {e}. Tentando Bairro...")
        except Exception as e:
            print(f"  -> Erro inesperado ao geocodificar CEP {cep}: {e}. Tentando Bairro...")

    # 2. Fallback: Tenta geocodificar pelo Bairro
    if is_valid_text(bairro):
        query_bairro = f"{bairro}, {CITY_CONTEXT}"
        try:
            location = geolocator.geocode(query_bairro, timeout=10)
            if location:
                print(f"  -> Geocodificado por Bairro (Fallback): {bairro}")
                return (location.latitude, location.longitude)
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            print(f"  -> Falha total na geocodificação para {cep}/{bairro}: {e}")
            return None
        except Exception as e:
            print(f"  -> Erro inesperado no fallback para {bairro}: {e}")
            return None
    
    return None


def resolve_coordinates(
    cep: str,
    bairro: str,
    cache: Dict[str, Tuple[float, float]]
) -> Tuple[Tuple[float, float], bool]:
    key_cep = normalize_key(cep) if isinstance(cep, str) else None
    key_bairro = normalize_key(bairro)
    updated = False

    for key in (key_cep, key_bairro):
        if key and key in cache:
            return cache[key], updated

    coords = geocode_location_api(cep, bairro)
    if not coords:
        coords = BAIRRO_FALLBACK_COORDS.get(bairro, CITY_DEFAULT_COORD)

    for key in (key_cep, key_bairro):
        if key:
            cache[key] = coords
            updated = True

    # Respeita limites de requisição apenas quando usamos a API
    if coords and coords != BAIRRO_FALLBACK_COORDS.get(bairro, CITY_DEFAULT_COORD) and coords != CITY_DEFAULT_COORD:
        time.sleep(random.uniform(1.0, 1.5))

    return coords, updated


def compute_poi_features(lat: float, lon: float) -> Dict[str, float]:
    features: Dict[str, float] = {}
    for key, ref_coord in POI_REFERENCE_POINTS.items():
        try:
            dist = geodesic((lat, lon), ref_coord).meters
        except ValueError:
            dist = 9999.0
        features[f"distancia_{key}"] = round(dist, 2)

    score = 0
    for key in ("farmacias", "mercados"):
        distance = features.get(f"distancia_{key}", 9999)
        if distance <= 800:
            score += 2
        elif distance <= 1500:
            score += 1
    features["score_comercial"] = score
    return features

def enrich_data(df: pd.DataFrame) -> pd.DataFrame:
    """Processa o DataFrame para enriquecimento geoespacial."""
    
    # Adiciona colunas de Lat/Long e POIs
    df['Latitude'] = None
    df['Longitude'] = None
    
    # Colunas de POIs (inicializadas para evitar KeyError)
    poi_cols = ['distancia_farmacias', 'distancia_escolas', 'distancia_mercados', 'distancia_hospitais', 'score_comercial']
    for col in poi_cols:
        df[col] = None
        
    cache = load_geocode_cache()
    cache_updated = False

    for index, row in df.iterrows():
        print(f"Processando imóvel {index + 1}/{len(df)}: CEP={row['CEP']}, Bairro={row['Bairro']}")
        
        # 1. Geocodificação
        coords, updated = resolve_coordinates(row.get('CEP', ''), row.get('Bairro', ''), cache)
        cache_updated = cache_updated or updated
        
        if coords:
            lat, lon = coords
            df.loc[index, 'Latitude'] = lat
            df.loc[index, 'Longitude'] = lon
            
            # 2. Busca de POIs aproximada
            pois_features = compute_poi_features(lat, lon)
            
            # 3. Adiciona features ao DataFrame
            for key, value in pois_features.items():
                df.loc[index, key] = value
        else:
            print(f"  -> Pulando POIs para {row['CEP']}/{row['Bairro']} devido à falha na geocodificação.")

    if cache_updated:
        save_geocode_cache(cache)
            
    return df

def main():
    """Função principal do módulo de enriquecimento."""
    if not INPUT_FILE.exists():
        print(f"Erro: Arquivo de entrada não encontrado em {INPUT_FILE}. Execute o Módulo 1 primeiro.")
        return

    print(f"Lendo dados brutos de: {INPUT_FILE}")
    df_raw = pd.read_csv(INPUT_FILE)
    
    # Garante que as colunas necessárias existam
    if 'CEP' not in df_raw.columns or 'Bairro' not in df_raw.columns:
        print("Erro: O arquivo CSV não contém as colunas 'CEP' e 'Bairro' necessárias.")
        return

    print(f"Iniciando enriquecimento geoespacial em {len(df_raw)} registros...")
    df_enriched = enrich_data(df_raw)
    
    # Salva o resultado
    df_enriched.to_csv(OUTPUT_FILE, index=False)
    print(f"\nEnriquecimento concluído. Dados salvos em: {OUTPUT_FILE}")
    print("\nPrimeiras 5 linhas do arquivo enriquecido:")
    print(df_enriched.head().to_markdown(index=False))

if __name__ == "__main__":
    # Adiciona o caminho de instalação local ao PATH do Python
    import sys
    sys.path.append(os.path.expanduser('~/.local/lib/python3.11/site-packages'))
    main()
