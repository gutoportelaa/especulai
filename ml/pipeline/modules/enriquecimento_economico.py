"""
Enriquecimento econômico de dados OLX.

Entrada: enriched_geo_olx.csv (dados com geolocalização)
Saída: enriched_economic_olx.csv (com dados FipeZap)

Responsabilidades:
  - Enriquecer com dados econômicos (FipeZap)
  - Calcular preço por m² (referência e anúncio)
  - Calcular diferença entre preço anunciado e FipeZap
  - Aplicar fatores por bairro

Não faz: Limpeza, validação de dados brutos
"""

from pathlib import Path
from typing import Dict, Optional
import logging

import pandas as pd
import numpy as np

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
DATA_DIR = WORKSPACE_ROOT / "dados_imoveis_teresina"

# Entrada: dados com geolocalização
INPUT_FILE = DATA_DIR / "enriched_geo_olx.csv"

# Saída: dados com enriquecimento econômico
OUTPUT_FILE = DATA_DIR / "enriched_economic_olx.csv"

# Referência FipeZap (dados reais de mercado)
FIPEZAP_FILE = WORKSPACE_ROOT / "fipezap-teresina.csv"

# Log do módulo
ECO_LOG_FILE = DATA_DIR / "enriquecimento_economico_log.txt"

# Fatores de ajuste por bairro (multiplicadores do valor base FipeZap)
# Valores > 1.0 = mais premium, Valores < 1.0 = mais popular
BAIRRO_FACTORS: Dict[str, float] = {
    'Fátima': 1.18,
    'Jóquei Clube': 1.12,
    'Morada do Sol': 1.08,
    'Ininga': 1.05,
    'Horto': 1.05,
    'Noivos': 1.04,
    'Horto Florestal': 1.06,
    'Centro': 0.95,
    'Ilhotas': 1.02,
    'Piçarra': 0.98
}

# ============================================================================
# LOGGING
# ============================================================================

def setup_logging():
    """Configura logging para arquivo e console."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(ECO_LOG_FILE, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


logger = setup_logging()

# ============================================================================
# CARREGAMENTO DE DADOS DE REFERÊNCIA
# ============================================================================

def load_fipezap_reference() -> Dict[str, float]:
    """
    Carrega valores de referência FipeZap de Teresina.
    
    Retorna preço médio por m² para venda e aluguel.
    
    Returns:
        Dicionário com valores: {'Venda': float, 'Aluguel': float}
    
    Raises:
        FileNotFoundError: Se arquivo FipeZap não existe
        ValueError: Se arquivo vazio ou formato inválido
    """
    if not FIPEZAP_FILE.exists():
        logger.error(f"Arquivo FipeZap não encontrado: {FIPEZAP_FILE}")
        raise FileNotFoundError(
            f"Arquivo {FIPEZAP_FILE} não encontrado. "
            "Garanta que o dado histórico do FipeZap esteja disponível."
        )

    try:
        df = pd.read_csv(FIPEZAP_FILE)
    except Exception as e:
        logger.error(f"Erro ao ler arquivo FipeZap: {e}")
        raise

    if df.empty:
        raise ValueError("Arquivo FipeZap está vazio.")

    # Usa o registro mais recente
    try:
        df['Data'] = pd.to_datetime(df['Data'])
        df = df.sort_values('Data')
        latest = df.iloc[-1]

        sale_avg = latest.get('Residencial_Venda_PrecoMedio_BRL_m2')
        rent_avg = latest.get('Residencial_Locacao_PrecoMedio_BRL_m2')

        if pd.isna(sale_avg) or pd.isna(rent_avg):
            raise ValueError("Colunas de preço médio não encontradas ou inválidas no arquivo FipeZap.")

        reference = {
            'Venda': float(sale_avg),
            'Aluguel': float(rent_avg)
        }
        
        logger.info(f"[FIPEZAP] Valores carregados: Venda=R${reference['Venda']:.2f}/m², Aluguel=R${reference['Aluguel']:.2f}/m²")
        return reference
        
    except Exception as e:
        logger.error(f"Erro ao processar dados FipeZap: {e}")
        raise


# ============================================================================
# CÁLCULO DE VALORES ECONÔMICOS
# ============================================================================

def lookup_fipezap_value(
    bairro: str,
    tipo_negocio: str,
    reference: Dict[str, float]
) -> float:
    """
    Calcula valor FipeZap para um imóvel baseado em bairro e tipo de negócio.
    
    Aplicacão de fatores:
      - Venda: valor base * fator do bairro
      - Aluguel: valor base * fator do bairro
    
    Args:
        bairro: Nome do bairro
        tipo_negocio: 'Venda' ou 'Aluguel'
        reference: Dicionário com valores base
    
    Returns:
        Preço FipeZap por m² (float)
    """
    # Tipo padrão se não especificado
    tipo_normalized = str(tipo_negocio).strip().capitalize() if tipo_negocio else 'Venda'
    base_value = reference.get(tipo_normalized, reference.get('Venda', 0))
    
    if not bairro or pd.isna(bairro):
        return round(base_value, 2)

    # Aplica fator por bairro
    bairro_str = str(bairro).strip()
    factor = BAIRRO_FACTORS.get(bairro_str, 1.0)
    
    fipezap_value = base_value * factor
    
    logger.debug(f"[LOOKUP] Bairro={bairro_str}, Tipo={tipo_normalized}, Base={base_value:.2f}, Fator={factor}, FipeZap={fipezap_value:.2f}")
    
    return round(fipezap_value, 2)


# ============================================================================
# ENRIQUECIMENTO
# ============================================================================

def enrich_economic_data(df: pd.DataFrame, reference: Dict[str, float]) -> pd.DataFrame:
    """
    Enriquece dados com informações econômicas.
    
    Calcula:
      - FipeZap_m2: Valor de referência por m² (FipeZap + fator bairro)
      - FipeZap_Diferenca_m2: Diferença entre preço anunciado e FipeZap
    
    Args:
        df: DataFrame com dados geoespaciais
        reference: Valores de referência FipeZap
    
    Returns:
        DataFrame enriquecido
    """
    logger.info(f"[ENRICH] Iniciando enriquecimento econômico de {len(df)} registros")
    
    df = df.copy()
    
    # 1. Calcula FipeZap por m² para cada imóvel
    logger.info("[ENRICH] Calculando FipeZap_m2 por bairro...")
    df['FipeZap_m2'] = df.apply(
        lambda row: lookup_fipezap_value(
            row.get('Bairro', ''),
            row.get('Tipo_Negocio', 'Venda'),
            reference
        ),
        axis=1
    )
    
    # 2. Padroniza Area_m2 para cálculos
    logger.info("[ENRICH] Normalizando Area_m2...")
    df['Area_m2'] = pd.to_numeric(df['Area_m2'], errors='coerce')
    df['Area_m2'] = df['Area_m2'].replace({0: np.nan})  # Evita divisão por zero
    
    # 3. Calcula preço por m² do anúncio
    logger.info("[ENRICH] Calculando Preco_Anuncio_m2...")
    df['Preco_Anuncio_m2'] = df['Valor_Anuncio'] / df['Area_m2']
    
    # 4. Calcula diferença: anúncio vs FipeZap
    logger.info("[ENRICH] Calculando FipeZap_Diferenca_m2...")
    df['FipeZap_Diferenca_m2'] = df['Preco_Anuncio_m2'] - df['FipeZap_m2']
    
    # Remove coluna auxiliar (não necessária no output final)
    df = df.drop(columns=['Preco_Anuncio_m2'], errors='ignore')
    
    logger.info("[ENRICH] ✓ Enriquecimento concluído")
    
    return df


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Função principal do módulo de enriquecimento econômico."""
    print()
    print("=" * 80)
    print("=== ESPECULAI - ENRIQUECIMENTO ECONÔMICO (OLX) ===")
    print("=" * 80)
    print()
    
    # Validação de entrada
    if not INPUT_FILE.exists():
        logger.error(f"Arquivo de entrada não encontrado: {INPUT_FILE}")
        logger.error("Execute o enriquecimento geoespacial (enriquecimento_geoespacial.py) primeiro.")
        raise FileNotFoundError(f"Dataset {INPUT_FILE} não encontrado")

    logger.info(f"[MAIN] Lendo dados geoespacialmente enriquecidos de: {INPUT_FILE}")
    df_geo = pd.read_csv(INPUT_FILE)
    logger.info(f"[MAIN] {len(df_geo)} registros carregados")
    
    # Validação de schema
    required_cols = ['Bairro', 'Tipo_Negocio', 'Valor_Anuncio', 'Area_m2']
    missing_cols = [col for col in required_cols if col not in df_geo.columns]
    if missing_cols:
        logger.error(f"Colunas obrigatórias faltando: {missing_cols}")
        raise ValueError(f"Schema inválido: faltam colunas {missing_cols}")

    # Carrega valores FipeZap
    logger.info("[MAIN] Carregando dados FipeZap...")
    reference = load_fipezap_reference()

    # Enriquecimento
    df_enriched = enrich_economic_data(df_geo, reference)
    
    # Salva resultado
    df_enriched.to_csv(OUTPUT_FILE, index=False)
    logger.info(f"[MAIN] Dados enriquecidos salvos em: {OUTPUT_FILE}")
    
    print()
    print("=" * 80)
    print("[OK] Enriquecimento econômico concluído!")
    print(f"[OK] Arquivo: {OUTPUT_FILE}")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()
