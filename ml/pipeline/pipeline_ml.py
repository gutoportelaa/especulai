from pathlib import Path
import sys
import pandas as pd
import numpy as np
import time
import re
import unicodedata


from datetime import datetime, timedelta
from typing import List, Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # .../especulai
WORKSPACE_ROOT = PROJECT_ROOT.parent
DATA_ROOT = WORKSPACE_ROOT / "dados_imoveis_teresina"

for path in {str(PROJECT_ROOT), str(WORKSPACE_ROOT)}:
    if path not in sys.path:
        sys.path.append(path)

from especulai.apps.scraper import collector as scraper_imoveis
from especulai.ml.pipeline.modules import enriquecimento_geoespacial, enriquecimento_economico

# --- Configurações de Arquivos ---
RAW_FILE = DATA_ROOT / "dataset_fonte_olx.csv"
GEO_FILE = DATA_ROOT / "enriched_geo_data.csv"
ECONOMIC_FILE = DATA_ROOT / "enriched_economic.csv"
FINAL_FILE = DATA_ROOT / "dataset_treino_ml_v1.csv"
DATA_DICT_FILE = DATA_ROOT / "dicionario_dados.txt"
SEGMENTED_DIR = DATA_ROOT / "segmentos"
RESULTS_FILE = DATA_ROOT / "resultados_modelos.csv"
MIN_RECORDS_SEGMENT = 30
DATA_EXPIRATION_DAYS = 7

# --- Utilitários ---

def ensure_fonte_column(df: pd.DataFrame) -> pd.DataFrame:
    """Garante a existência da coluna 'Fonte'."""
    if 'Fonte' not in df.columns:
        df['Fonte'] = ''
    df['Fonte'] = df['Fonte'].fillna('')

    def detect_source(row) -> str:
        fonte = row.get('Fonte', '')
        if fonte and fonte not in ('Desconhecida', 'desconhecida', ''):
            return fonte

        url = row.get('URL_Anuncio', '')
        if isinstance(url, str):
            url_lower = url.lower()
            if "olx.com.br" in url_lower:
                return "OLX"
            if "rochaerocha.com.br" in url_lower:
                return "RochaRocha"
            if "imovelweb.com" in url_lower:
                return "ImovelWeb"
        return "Desconhecida"

    df['Fonte'] = df.apply(detect_source, axis=1)
    return df


def slugify(value: str) -> str:
    """Normaliza strings para uso em nomes de arquivos."""
    if not value:
        return "desconhecido"
    normalized = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "_", normalized.lower()).strip("_")
    return slug or "desconhecido"


# --- Funções de Limpeza e Preparação ---

def clean_and_prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Realiza a limpeza, tratamento de outliers, imputação e Feature Engineering.
    """
    print("Iniciando limpeza e preparação de dados...")
    df = df.copy()
    df = ensure_fonte_column(df)
    if 'Descricao' not in df.columns:
        df['Descricao'] = ''
    
    # 1. Tratamento de Tipos (Garantir floats limpos)
    # Como os dados mock já são numéricos, esta etapa é mais para robustez
    # e para lidar com a saída real do scraper (ex: remover 'R$' e '.')
    
    # Colunas que devem ser inteiras/float
    int_cols = ['Area_m2', 'Quartos', 'Banheiros', 'Vagas_Garagem']
    float_cols = ['Valor_Anuncio', 'Latitude', 'Longitude', 'FipeZap_m2', 'FipeZap_Diferenca_m2']
    
    for col in int_cols + float_cols:
        if col not in df.columns:
            df[col] = np.nan
        # Tenta converter para numérico, forçando erros para NaN
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # 2. Feature Engineering (Texto)
    df['Descricao_Length'] = df['Descricao'].fillna('').apply(len)
    
    # 3. Imputação de Dados Faltantes
    
    # Imputação simples para features de contagem (assumir 0 se for NaN)
    for col in ['Quartos', 'Banheiros', 'Vagas_Garagem']:
        df[col] = df[col].fillna(0).astype(int)
        
    # Imputação de Area_m2 pela média do Bairro (mais robusto)
    df['Area_m2'] = df['Area_m2'].fillna(df.groupby('Bairro')['Area_m2'].transform('mean'))
    # Imputação de Latitude/Longitude pela média do Bairro
    df['Latitude'] = df['Latitude'].fillna(df.groupby('Bairro')['Latitude'].transform('mean'))
    df['Longitude'] = df['Longitude'].fillna(df.groupby('Bairro')['Longitude'].transform('mean'))
    
    # Preencher quaisquer nulos restantes com a média geral
    df = df.fillna(df.mean(numeric_only=True))
    
    # 4. Tratamento de Outliers (IQR)
    # Aplicado apenas à variável alvo: Valor_Anuncio
    Q1 = df['Valor_Anuncio'].quantile(0.25)
    Q3 = df['Valor_Anuncio'].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    
    df_clean = df[(df['Valor_Anuncio'] >= lower_bound) & (df['Valor_Anuncio'] <= upper_bound)].copy()
    print(f"Registros removidos por Outlier (IQR): {len(df) - len(df_clean)}")
    
    # 5. Codificação de Variáveis Categóricas (One-Hot Encoding)
    
    # Colunas para OHE
    categorical_cols = ['Tipo_Negocio', 'Tipo_Imovel', 'Bairro', 'Fonte']
    df_final = pd.get_dummies(df_clean, columns=categorical_cols, drop_first=True)
    
    # 6. Seleção de Features Finais
    # Remove apenas colunas realmente desnecessárias para ML
    # MANTÉM URL_Anuncio e Data_Coleta para rastreabilidade e análise temporal
    cols_to_drop = ['ID_Imovel', 'CEP', 'Descricao']
    df_final = df_final.drop(columns=[col for col in cols_to_drop if col in df_final.columns], errors='ignore')
    
    print(f"Limpeza e preparação concluídas. Dataset final com {len(df_final)} registros e {len(df_final.columns)} colunas.")
    return df_final

def create_data_dictionary(df: pd.DataFrame):
    """Gera um dicionário de dados simples para o dataset final."""
    
    dictionary_content = "Dicionário de Dados - Dataset de Treino ML (Imóveis Teresina)\n\n"
    dictionary_content += "Este arquivo descreve as colunas do dataset final após o pipeline de limpeza e enriquecimento.\n\n"
    
    for col in df.columns:
        dtype = df[col].dtype
        description = ""
        
        if col == 'Valor_Anuncio':
            description = "Variável Alvo: Valor do anúncio (R$)."
        elif col == 'URL_Anuncio':
            description = "URL do anúncio original (para rastreabilidade e validação). Permite verificar se o imóvel ainda está disponível."
        elif col == 'Data_Coleta':
            description = "Data de coleta do anúncio (formato YYYY-MM-DD). Útil para análise temporal e detecção de anúncios removidos."
        elif col == 'Area_m2':
            description = "Área do imóvel em metros quadrados."
        elif col == 'Quartos':
            description = "Número de quartos."
        elif col == 'Banheiros':
            description = "Número de banheiros."
        elif col == 'Vagas_Garagem':
            description = "Número de vagas de garagem."
        elif col == 'Latitude':
            description = "Coordenada geográfica (Latitude)."
        elif col == 'Longitude':
            description = "Coordenada geográfica (Longitude)."
        elif col == 'FipeZap_m2':
            description = "Valor médio por m² (simulado FipeZap) para o Bairro e Tipo_Negocio."
        elif col == 'FipeZap_Diferenca_m2':
            description = "Diferença entre o Valor_Anuncio/Area_m2 e o FipeZap_m2 (Feature de valor)."
        elif col.startswith('distancia_'):
            description = f"Distância (em metros) do POI mais próximo ({col.split('_')[1]}). 9999 indica ausência."
        elif col == 'score_comercial':
            description = "Score de proximidade comercial (soma de farmácias e mercados simulados)."
        elif col == 'Descricao_Length':
            description = "Comprimento da descrição do anúncio (Feature de Text Mining)."
        elif col.startswith('Tipo_Negocio_'):
            description = f"One-Hot Encoding para Tipo_Negocio: {col.split('_')[-1]} (Venda é a base)."
        elif col.startswith('Tipo_Imovel_'):
            description = f"One-Hot Encoding para Tipo_Imovel: {col.split('_')[-1]} (Apartamento é a base)."
        elif col.startswith('Bairro_'):
            description = f"One-Hot Encoding para Bairro: {col.split('_')[-1]} (Fátima é a base)."
        else:
            description = "Coluna gerada por One-Hot Encoding ou outra feature."
            
        dictionary_content += f"Coluna: {col}\n"
        dictionary_content += f"Tipo: {dtype}\n"
        dictionary_content += f"Descrição: {description}\n\n"
        
    with DATA_DICT_FILE.open('w', encoding='utf-8') as f:
        f.write(dictionary_content)
    print(f"Dicionário de dados salvo em: {DATA_DICT_FILE}")


def _save_segment(name: str, df_segment: pd.DataFrame):
    SEGMENTED_DIR.mkdir(parents=True, exist_ok=True)
    output_path = SEGMENTED_DIR / f"dataset_{name}.csv"
    df_segment.to_csv(output_path, index=False)
    print(f"Segmento '{name}' salvo com {len(df_segment)} registros em: {output_path}")


def _process_segment(name: str, subset: pd.DataFrame) -> pd.DataFrame:
    if len(subset) < MIN_RECORDS_SEGMENT:
        print(f"Segmento '{name}' ignorado (apenas {len(subset)} registros).")
        return None
    return clean_and_prepare_data(subset)


def generate_segmented_datasets(df_enriched: pd.DataFrame, df_full_processed: pd.DataFrame):
    """
    Cria datasets segmentados por fonte, tipo de negócio e combinações.
    FILTRA fontes desconhecidas/vazias antes de gerar segmentos.
    """
    df_enriched = ensure_fonte_column(df_enriched.copy())
    df_enriched['Tipo_Negocio'] = df_enriched['Tipo_Negocio'].fillna('Desconhecido')
    
    # FILTRA fontes desconhecidas/vazias - não queremos dados fictícios
    fonte_mask = (
        df_enriched['Fonte'].notna() & 
        (df_enriched['Fonte'] != '') & 
        (df_enriched['Fonte'].str.lower() != 'desconhecida') &
        (df_enriched['Fonte'].str.lower() != 'desconhecido')
    )
    df_enriched = df_enriched[fonte_mask].copy()
    
    if len(df_enriched) == 0:
        print("Aviso: Nenhum registro com fonte válida encontrado após filtragem.")
        segments: Dict[str, pd.DataFrame] = {"full": df_full_processed}
        _save_segment("full", df_full_processed)
        return
    
    segments: Dict[str, pd.DataFrame] = {"full": df_full_processed}

    for fonte, subset in df_enriched.groupby('Fonte'):
        name = f"fonte_{slugify(fonte)}"
        processed = _process_segment(name, subset.copy())
        if processed is not None:
            segments[name] = processed

    for negocio, subset in df_enriched.groupby('Tipo_Negocio'):
        name = f"negocio_{slugify(negocio)}"
        processed = _process_segment(name, subset.copy())
        if processed is not None:
            segments[name] = processed

    for (fonte, negocio), subset in df_enriched.groupby(['Fonte', 'Tipo_Negocio']):
        name = f"fonte_{slugify(fonte)}__negocio_{slugify(negocio)}"
        processed = _process_segment(name, subset.copy())
        if processed is not None:
            segments[name] = processed

    for name, df_segment in segments.items():
        _save_segment(name, df_segment)

def check_file_age(filepath: Path) -> bool:
    """Verifica se o arquivo existe e se é mais antigo que DATA_EXPIRATION_DAYS."""
    filepath = Path(filepath)
    if not filepath.exists():
        return True  # Arquivo não existe, precisa ser gerado
    
    file_mod_time = datetime.fromtimestamp(filepath.stat().st_mtime)
    expiration_date = datetime.now() - timedelta(days=DATA_EXPIRATION_DAYS)
    
    return file_mod_time < expiration_date

def run_full_pipeline():
    """
    Função principal que orquestra a execução de todos os módulos.
    """
    print("--- Iniciando Pipeline de Engenharia de Dados ---")
    
    # --- Módulo 1: Coleta (Scraping) ---
    if check_file_age(RAW_FILE):
        print(f"Arquivo {RAW_FILE} expirado ou inexistente. Executando Módulo 1 (Scraping)...")
        # Simula a execução do scraper
        scraper_imoveis.main_scraper(num_pages=3)
    else:
        print(f"Arquivo {RAW_FILE} está atualizado. Pulando Módulo 1.")
        
    # --- Módulo 2: Enriquecimento Geoespacial ---
    if check_file_age(GEO_FILE):
        print(f"Arquivo {GEO_FILE} expirado ou inexistente. Executando Módulo 2 (Geoespacial)...")
        # Simula a execução do enriquecimento geoespacial
        # NOTA: O módulo real faria a leitura do RAW_FILE e salvaria no GEO_FILE
        # Para a simulação, vamos garantir que o arquivo exista antes de tentar ler
        if RAW_FILE.exists():
            # O script de enriquecimento geoespacial já contém a lógica de leitura/escrita
            enriquecimento_geoespacial.main()
        else:
            print(f"ERRO: Não foi possível executar Módulo 2. Arquivo {RAW_FILE} não encontrado.")
            return
    else:
        print(f"Arquivo {GEO_FILE} está atualizado. Pulando Módulo 2.")
        
    # --- Módulo 3: Enriquecimento Econômico ---
    if check_file_age(ECONOMIC_FILE):
        print(f"Arquivo {ECONOMIC_FILE} expirado ou inexistente. Executando Módulo 3 (Econômico)...")
        if GEO_FILE.exists():
            # O script de enriquecimento econômico já contém a lógica de leitura/escrita
            enriquecimento_economico.main()
        else:
            print(f"ERRO: Não foi possível executar Módulo 3. Arquivo {GEO_FILE} não encontrado.")
            return
    else:
        print(f"Arquivo {ECONOMIC_FILE} está atualizado. Pulando Módulo 3.")
        
    # --- Módulo 4: Limpeza e Preparação Final ---
    print("\nExecutando Módulo 4: Limpeza e Preparação Final para ML...")
    
    if not ECONOMIC_FILE.exists():
        print(f"ERRO: Arquivo final de enriquecimento {ECONOMIC_FILE} não encontrado. Pipeline interrompido.")
        return
        
    df_final = pd.read_csv(ECONOMIC_FILE)
    df_processed = clean_and_prepare_data(df_final)
    
    # Salva o dataset final em CSV (conforme solicitado)
    df_processed.to_csv(FINAL_FILE, index=False)
    print(f"Dataset final salvo em: {FINAL_FILE}")

    # Gera datasets segmentados
    generate_segmented_datasets(df_final, df_processed)
    
    # Cria o dicionário de dados
    create_data_dictionary(df_processed)
    
    print("--- Pipeline de Engenharia de Dados Concluído ---")
    
    # Exibe o cabeçalho do dataset final
    print("\nPrimeiras 5 linhas do Dataset Final (Pronto para ML):")
    print(df_processed.head().to_markdown(index=False))

if __name__ == "__main__":
    run_full_pipeline()
