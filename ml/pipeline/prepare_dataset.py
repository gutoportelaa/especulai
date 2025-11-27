"""
Módulo de preparação de dataset para treinamento ML.

Entrada: enriched_economic_olx.csv (dados enriquecidos)
Saída: dataset_treino_olx_final.csv (pronto para treinar)

Responsabilidades:
  - Limpeza de dados (tipos, NaN, outliers)
  - Feature Engineering (densidade de cômodos, etc)
  - One-Hot Encoding (categorias)
  - Validação e seleção de features finais
  - Geração de dicionário de dados

Não faz: Normalização (feita no train_model.py com StandardScaler)
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import logging
import pandas as pd
import numpy as np

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = WORKSPACE_ROOT / "dados_imoveis_teresina"

ECONOMIC_FILE = DATA_ROOT / "enriched_economic_olx.csv"
FINAL_FILE = DATA_ROOT / "dataset_treino_olx_final.csv"
DATA_DICT_FILE = DATA_ROOT / "dicionario_dados_olx.txt"
PREPARE_LOG_FILE = DATA_ROOT / "prepare_dataset_log.txt"

# Schema esperado após enriquecimento
REQUIRED_NUMERIC_COLS = [
    'Valor_Anuncio', 'Area_m2', 'Quartos', 'Banheiros', 'Vagas_Garagem',
    'Latitude', 'Longitude'
]

REQUIRED_CATEGORICAL_COLS = [
    'Tipo_Imovel', 'Bairro'
]

OPTIONAL_COLS = [
    'Descricao', 'Descricao_Length', 'FipeZap_m2', 'FipeZap_Diferenca_m2',
    'URL_Anuncio', 'Data_Coleta'
]

# ============================================================================
# LOGGING
# ============================================================================

def setup_logging():
    """Configura logging para arquivo e console."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(PREPARE_LOG_FILE, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


logger = setup_logging()

# ============================================================================
# PREPARAÇÃO DE DADOS
# ============================================================================

def load_enriched_data(csv_path: Path) -> pd.DataFrame:
    """
    Carrega dados enriquecidos e valida schema.
    
    Args:
        csv_path: Caminho do arquivo enriched_economic.csv
    
    Returns:
        DataFrame com dados validados
    
    Raises:
        FileNotFoundError: Se arquivo não existe
        ValueError: Se schema inválido
    """
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Arquivo {csv_path} não encontrado. "
            "Execute enriquecimento econômico primeiro."
        )
    
    logger.info(f"[LOAD] Carregando dados enriquecidos de: {csv_path}")
    df = pd.read_csv(csv_path)
    
    logger.info(f"[LOAD] Dataset carregado: {len(df)} registros, {len(df.columns)} colunas")
    
    # Validação de colunas obrigatórias
    missing_cols = [col for col in REQUIRED_NUMERIC_COLS + REQUIRED_CATEGORICAL_COLS if col not in df.columns]
    if missing_cols:
        raise ValueError(
            f"Colunas obrigatórias faltando: {missing_cols}. "
            f"Schema esperado: {REQUIRED_NUMERIC_COLS + REQUIRED_CATEGORICAL_COLS}"
        )
    
    logger.info("[LOAD] ✓ Schema validado com sucesso")
    return df


def clean_and_prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpeza completa do dataset:
      1. Conversão de tipos
      2. Feature Engineering
      3. Imputação de NaN
      4. Tratamento de outliers
      5. One-Hot Encoding
      6. Seleção de features finais
    
    Args:
        df: DataFrame para preparar
    
    Returns:
        DataFrame preparado e pronto para treinamento
    """
    df = df.copy()
    logger.info("[PREP] Iniciando limpeza e preparação de dados...")
    
    # ========================================================================
    # 1. CONVERSÃO DE TIPOS
    # ========================================================================
    logger.info("[PREP] 1. Convertendo tipos de dados...")
    
    for col in REQUIRED_NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    for col in REQUIRED_CATEGORICAL_COLS:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.title()
    
    logger.info(f"[PREP]    Tipos convertidos para {len(REQUIRED_NUMERIC_COLS)} numéricas + {len(REQUIRED_CATEGORICAL_COLS)} categóricas")
    
    # ========================================================================
    # 2. FEATURE ENGINEERING
    # ========================================================================
    logger.info("[PREP] 2. Criando features engineered...")
    
    # Densidade de cômodos
    df['Densidade_Comodos'] = (df['Quartos'] + df['Banheiros']) / df['Area_m2'].clip(lower=1)
    df['Densidade_Comodos'] = df['Densidade_Comodos'].replace([np.inf, -np.inf], 0).fillna(0)
    
    # Preço por m²
    df['Preco_m2'] = df['Valor_Anuncio'] / df['Area_m2'].clip(lower=1)
    df['Preco_m2'] = df['Preco_m2'].replace([np.inf, -np.inf], 0).fillna(0)
    
    # Total de dependências
    df['Total_Dependencias'] = df['Quartos'] + df['Banheiros'] + df['Vagas_Garagem']
    
    logger.info("[PREP]    ✓ Features engineered criadas: Densidade_Comodos, Preco_m2, Total_Dependencias")
    
    # ========================================================================
    # 3. IMPUTAÇÃO DE DADOS FALTANTES
    # ========================================================================
    logger.info("[PREP] 3. Imputando dados faltantes...")
    
    # Contagens inteiras: preencher com 0 (assume "não informado" = não existe)
    for col in ['Quartos', 'Banheiros', 'Vagas_Garagem']:
        if col in df.columns:
            df[col] = df[col].fillna(0).astype(int)
    
    # Área: imputar pela média do bairro
    if 'Bairro' in df.columns:
        df['Area_m2'] = df['Area_m2'].fillna(
            df.groupby('Bairro')['Area_m2'].transform('mean')
        )
    
    df['Area_m2'] = df['Area_m2'].fillna(df['Area_m2'].mean()).clip(lower=1)
    
    # Geolocalização: imputar pela média do bairro
    for col in ['Latitude', 'Longitude']:
        if col in df.columns:
            df[col] = df[col].fillna(
                df.groupby('Bairro')[col].transform('mean')
            )
            df[col] = df[col].fillna(df[col].mean())
    
    # FipeZap: preencher com 0 se não tiver (será tratado como "não enriquecido")
    for col in ['FipeZap_m2', 'FipeZap_Diferenca_m2']:
        if col in df.columns:
            df[col] = df[col].fillna(0)
    
    # Descrição
    if 'Descricao' in df.columns:
        df['Descricao'] = df['Descricao'].fillna('')
    
    if 'Descricao_Length' in df.columns:
        df['Descricao_Length'] = df['Descricao_Length'].fillna(0).astype(int)
    
    logger.info(f"[PREP]    ✓ NaN imputados. Registros com NaN restante: {df.isna().sum().sum()}")
    
    # ========================================================================
    # 4. TRATAMENTO DE OUTLIERS (IQR)
    # ========================================================================
    logger.info("[PREP] 4. Removendo outliers...")
    
    # Apenas na variável alvo: Valor_Anuncio
    Q1 = df['Valor_Anuncio'].quantile(0.25)
    Q3 = df['Valor_Anuncio'].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    
    df_clean = df[
        (df['Valor_Anuncio'] >= lower_bound) & 
        (df['Valor_Anuncio'] <= upper_bound)
    ].copy()
    
    removed = len(df) - len(df_clean)
    logger.info(f"[PREP]    Registros removidos por outlier (IQR): {removed}")
    
    # Validação: manter apenas Area_m2 > 0 e Valor > 0
    df_clean = df_clean[
        (df_clean['Area_m2'] > 0) & 
        (df_clean['Valor_Anuncio'] > 0)
    ].copy()
    
    logger.info(f"[PREP]    Dataset após limpeza: {len(df_clean)} registros")
    
    # ========================================================================
    # 5. ONE-HOT ENCODING
    # ========================================================================
    logger.info("[PREP] 5. Aplicando One-Hot Encoding...")
    
    categorical_cols = ['Tipo_Imovel', 'Bairro']
    df_encoded = pd.get_dummies(
        df_clean,
        columns=categorical_cols,
        drop_first=True,
        prefix=categorical_cols
    )
    
    ohe_cols = [col for col in df_encoded.columns if col.startswith('Tipo_Imovel_') or col.startswith('Bairro_')]
    logger.info(f"[PREP]    Colunas OHE criadas: {len(ohe_cols)}")
    
    # ========================================================================
    # 6. SELEÇÃO DE FEATURES FINAIS
    # ========================================================================
    logger.info("[PREP] 6. Selecionando features finais...")
    
    # Colunas a manter: numéricas + OHE + features engineered
    features_to_keep = (
        REQUIRED_NUMERIC_COLS +
        ['Densidade_Comodos', 'Preco_m2', 'Total_Dependencias'] +
        ohe_cols
    )
    
    # Adicionar opcionais que existem e são numéricos
    for col in OPTIONAL_COLS:
        if col in df_encoded.columns and df_encoded[col].dtype in ['int64', 'float64']:
            if col not in features_to_keep:
                features_to_keep.append(col)
    
    # Filtrar apenas colunas que existem
    features_final = [col for col in features_to_keep if col in df_encoded.columns]
    
    df_final = df_encoded[features_final].copy()
    
    logger.info(f"[PREP]    Features finais selecionadas: {len(df_final.columns)}")
    logger.info(f"[PREP]    Registros finais: {len(df_final)}")
    
    return df_final


def create_data_dictionary(df: pd.DataFrame):
    """
    Gera dicionário de dados documentando todas as features.
    
    Args:
        df: DataFrame para documentar
    """
    logger.info("[DICT] Gerando dicionário de dados...")
    
    content = []
    content.append("=" * 80)
    content.append("DICIONÁRIO DE DADOS - DATASET TREINO ML OLX")
    content.append("=" * 80)
    content.append(f"Gerado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    content.append(f"Total de registros: {len(df)}")
    content.append(f"Total de features: {len(df.columns)}")
    content.append("")
    content.append("FEATURES:")
    content.append("-" * 80)
    
    for col in df.columns:
        dtype = df[col].dtype
        non_null = df[col].notna().sum()
        null_count = df[col].isna().sum()
        unique = df[col].nunique()
        
        content.append(f"\n📊 {col}")
        content.append(f"   Tipo: {dtype}")
        content.append(f"   Não-nulos: {non_null}/{len(df)} ({100*non_null/len(df):.1f}%)")
        
        if dtype in ['float64', 'int64']:
            content.append(f"   Min: {df[col].min():.4f}")
            content.append(f"   Max: {df[col].max():.4f}")
            content.append(f"   Média: {df[col].mean():.4f}")
            content.append(f"   Std: {df[col].std():.4f}")
            content.append(f"   Mediana: {df[col].median():.4f}")
        
        if unique <= 20:
            content.append(f"   Únicos ({unique}): {list(df[col].dropna().unique())[:10]}")
        else:
            content.append(f"   Únicos: {unique}")
    
    content.append("")
    content.append("=" * 80)
    content.append("FIM DO DICIONÁRIO")
    content.append("=" * 80)
    
    dict_content = "\n".join(content)
    
    with DATA_DICT_FILE.open('w', encoding='utf-8') as f:
        f.write(dict_content)
    
    logger.info(f"[DICT] Dicionário salvo: {DATA_DICT_FILE}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Função principal do módulo de preparação."""
    print("=" * 80)
    print("=== ESPECULAI - PREPARAÇÃO DE DATASET (OLX) ===")
    print("=" * 80)
    print()
    
    try:
        # 1. Carregar dados enriquecidos
        df = load_enriched_data(ECONOMIC_FILE)
        
        # 2. Limpar e preparar
        df_final = clean_and_prepare_data(df)
        
        # 3. Salvar dataset final
        df_final.to_csv(FINAL_FILE, index=False)
        logger.info(f"[SAVE] Dataset final salvo: {FINAL_FILE}")
        
        # 4. Gerar dicionário
        create_data_dictionary(df_final)
        
        print()
        print("=" * 80)
        print("[OK] Preparação de dataset concluída com sucesso!")
        print(f"[OK] Dataset final: {len(df_final)} registros × {len(df_final.columns)} features")
        print(f"[OK] Arquivo: {FINAL_FILE}")
        print("=" * 80)
        print()
        
    except Exception as e:
        logger.error(f"[ERROR] Erro na preparação: {e}")
        raise


if __name__ == "__main__":
    main()
