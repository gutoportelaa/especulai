from pathlib import Path
from typing import Dict

import os

import pandas as pd

# Configurações
WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
DATA_DIR = WORKSPACE_ROOT / "dados_imoveis_teresina"
INPUT_FILE = DATA_DIR / "enriched_geo_data.csv"
OUTPUT_FILE = DATA_DIR / "enriched_economic.csv"
FIPEZAP_FILE = WORKSPACE_ROOT / "fipezap-teresina.csv"

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


def load_fipezap_reference() -> Dict[str, float]:
    """
    Lê o arquivo oficial do FipeZap e retorna o valor médio mais recente
    para venda e aluguel em Teresina.
    """
    if not FIPEZAP_FILE.exists():
        raise FileNotFoundError(
            f"Arquivo {FIPEZAP_FILE} não encontrado. Garanta que o dado histórico do FipeZap esteja disponível."
        )

    df = pd.read_csv(FIPEZAP_FILE)
    if df.empty:
        raise ValueError("Arquivo FipeZap está vazio.")

    # Usa o registro mais recente
    df['Data'] = pd.to_datetime(df['Data'])
    df = df.sort_values('Data')
    latest = df.iloc[-1]

    sale_avg = latest.get('Residencial_Venda_PrecoMedio_BRL_m2')
    rent_avg = latest.get('Residencial_Locacao_PrecoMedio_BRL_m2')

    if pd.isna(sale_avg) or pd.isna(rent_avg):
        raise ValueError("Colunas de preço médio não encontradas ou inválidas no arquivo FipeZap.")

    return {
        'Venda': float(sale_avg),
        'Aluguel': float(rent_avg)
    }


def lookup_fipezap_value(bairro: str, tipo_negocio: str, reference: Dict[str, float]) -> float:
    """
    Calcula o valor FipeZap para o bairro/tipo usando fatores relativos.
    Para bairros novos, aplica o valor médio da cidade.
    """
    base_value = reference.get(tipo_negocio, reference['Venda'])
    if not bairro:
        return round(base_value, 2)

    factor = BAIRRO_FACTORS.get(bairro.strip(), 1.0)
    return round(base_value * factor, 2)


def enrich_economic_data(df: pd.DataFrame) -> pd.DataFrame:
    """Processa o DataFrame para enriquecimento econômico com dados reais do FipeZap."""

    reference = load_fipezap_reference()
    df['FipeZap_m2'] = df.apply(
        lambda row: lookup_fipezap_value(row.get('Bairro', ''), row.get('Tipo_Negocio', 'Venda'), reference),
        axis=1
    )

    # Protege contra divisão por zero
    df['Area_m2'] = pd.to_numeric(df['Area_m2'], errors='coerce')
    df['Area_m2'].replace({0: pd.NA}, inplace=True)

    df['Valor_Anuncio_m2'] = df['Valor_Anuncio'] / df['Area_m2']
    df['FipeZap_Diferenca_m2'] = df['Valor_Anuncio_m2'] - df['FipeZap_m2']

    df = df.drop(columns=['Valor_Anuncio_m2'])

    return df

def main():
    """Função principal do módulo de enriquecimento econômico."""
    if not INPUT_FILE.exists():
        print(f"Erro: Arquivo de entrada não encontrado em {INPUT_FILE}. Execute o Módulo 2 primeiro.")
        return

    print(f"Lendo dados geoespacialmente enriquecidos de: {INPUT_FILE}")
    df_geo = pd.read_csv(INPUT_FILE)
    
    # Garante que as colunas necessárias existam
    if 'Bairro' not in df_geo.columns or 'Tipo_Negocio' not in df_geo.columns or 'Valor_Anuncio' not in df_geo.columns or 'Area_m2' not in df_geo.columns:
        print("Erro: O arquivo CSV não contém as colunas 'Bairro', 'Tipo_Negocio', 'Valor_Anuncio' e 'Area_m2' necessárias.")
        return

    print(f"Iniciando enriquecimento econômico em {len(df_geo)} registros...")
    df_enriched = enrich_economic_data(df_geo)
    
    # Salva o resultado
    df_enriched.to_csv(OUTPUT_FILE, index=False)
    print(f"\nEnriquecimento concluído. Dados salvos em: {OUTPUT_FILE}")
    print("\nPrimeiras 5 linhas do arquivo enriquecido (colunas relevantes):")
    
    # Exibe apenas as colunas relevantes para o enriquecimento econômico
    cols_to_display = ['Bairro', 'Tipo_Negocio', 'Valor_Anuncio', 'Area_m2', 'FipeZap_m2', 'FipeZap_Diferenca_m2']
    print(df_enriched[cols_to_display].head().to_markdown(index=False))

if __name__ == "__main__":
    # Adiciona o caminho de instalação local ao PATH do Python
    import sys
    sys.path.append(os.path.expanduser('~/.local/lib/python3.11/site-packages'))
    main()
