"""
Treina o modelo usando APENAS o dataset_fonte_olx.csv (já processado com One-Hot Encoding).
Este modelo será treinado exclusivamente com dados da fonte OLX, evitando viés de outras fontes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import math
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "artifacts"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
DATA_ROOT = WORKSPACE_ROOT / "dados_imoveis_teresina"
DATA_ROOT.mkdir(parents=True, exist_ok=True)

# Dataset já processado com One-Hot Encoding
DATASET_OLX_PATH = DATA_ROOT / "segmentos" / "dataset_fonte_olx.csv"
MODEL_PATH = ARTIFACT_DIR / "modelo_definitivo.joblib"
PREPROCESSOR_PATH = ARTIFACT_DIR / "preprocessador.joblib"


def extract_bairro_from_ohe(df: pd.DataFrame) -> pd.Series:
    """Extrai a coluna 'bairro' categórica das colunas One-Hot Encoding Bairro_*"""
    bairro_cols = [col for col in df.columns if col.startswith('Bairro_')]
    
    if not bairro_cols:
        # Se não tem OHE, tenta coluna Bairro direta
        if 'Bairro' in df.columns:
            return df['Bairro'].astype(str).str.title().str.strip()
        return pd.Series(['Desconhecido'] * len(df), index=df.index)
    
    # Encontra qual coluna Bairro_* é True para cada linha
    bairros = []
    for idx, row in df[bairro_cols].iterrows():
        # Encontra a coluna que é True
        true_cols = row[row == True].index.tolist()
        if true_cols:
            # Remove o prefixo 'Bairro_' e usa como nome do bairro
            bairro_name = true_cols[0].replace('Bairro_', '').replace('_', ' ')
            bairros.append(bairro_name)
        else:
            bairros.append('Desconhecido')
    
    return pd.Series(bairros, index=df.index)


def extract_tipo_from_ohe(df: pd.DataFrame) -> pd.Series:
    """Extrai a coluna 'tipo' categórica das colunas One-Hot Encoding Tipo_Imovel_*"""
    tipo_cols = [col for col in df.columns if col.startswith('Tipo_Imovel_')]
    
    if not tipo_cols:
        # Se não tem OHE, tenta coluna Tipo_Imovel direta
        if 'Tipo_Imovel' in df.columns:
            return df['Tipo_Imovel'].astype(str).str.lower().str.strip()
        # Se não tem tipo, tenta inferir da URL ou usa padrão
        if 'URL_Anuncio' in df.columns:
            # Tenta inferir do URL (ex: "casa", "apartamento", "sobrado")
            tipos = []
            for url in df['URL_Anuncio'].fillna(''):
                url_lower = str(url).lower()
                if 'casa' in url_lower:
                    tipos.append('casa')
                elif 'apartamento' in url_lower or 'apto' in url_lower:
                    tipos.append('apartamento')
                elif 'sobrado' in url_lower:
                    tipos.append('sobrado')
                elif 'terreno' in url_lower:
                    tipos.append('terreno')
                else:
                    tipos.append('apartamento')  # padrão
            return pd.Series(tipos, index=df.index)
        # Se não tem nada, usa padrão
        return pd.Series(['apartamento'] * len(df), index=df.index)
    
    # Encontra qual coluna Tipo_Imovel_* é True para cada linha
    tipos = []
    for idx, row in df[tipo_cols].iterrows():
        # Encontra a coluna que é True
        true_cols = row[row == True].index.tolist()
        if true_cols:
            # Remove o prefixo 'Tipo_Imovel_' e usa como nome do tipo
            tipo_name = true_cols[0].replace('Tipo_Imovel_', '').lower().strip()
            tipos.append(tipo_name)
        else:
            tipos.append('apartamento')  # padrão
    
    return pd.Series(tipos, index=df.index)


def prepare_dataset_olx(csv_path: Path = DATASET_OLX_PATH) -> pd.DataFrame:
    """Prepara o dataset OLX já processado para treinamento"""
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Dataset OLX não encontrado em {csv_path}. "
            f"Execute pipeline_ml.py para gerar os datasets segmentados."
        )
    
    print(f"[OK] Carregando dataset OLX de: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"[OK] Dataset carregado: {len(df)} registros, {len(df.columns)} colunas")
    
    # Verifica colunas obrigatórias
    required_numeric = ['Area_m2', 'Quartos', 'Banheiros', 'Valor_Anuncio']
    missing = [col for col in required_numeric if col not in df.columns]
    if missing:
        raise ValueError(f"Colunas numéricas obrigatórias ausentes: {missing}")
    
    # Limpa dados
    df = df.dropna(subset=required_numeric)
    df['Area_m2'] = pd.to_numeric(df['Area_m2'], errors='coerce').clip(lower=1)
    df['Quartos'] = pd.to_numeric(df['Quartos'], errors='coerce').fillna(0).astype(int)
    df['Banheiros'] = pd.to_numeric(df['Banheiros'], errors='coerce').fillna(0).astype(int)
    df['Valor_Anuncio'] = pd.to_numeric(df['Valor_Anuncio'], errors='coerce')
    
    # Remove registros inválidos
    df = df[df['Area_m2'] > 0]
    df = df[df['Valor_Anuncio'] > 0]
    df = df.dropna(subset=['Area_m2', 'Valor_Anuncio'])
    
    # Extrai colunas categóricas do One-Hot Encoding
    df['bairro'] = extract_bairro_from_ohe(df)
    df['tipo'] = extract_tipo_from_ohe(df)
    df['cidade'] = 'Teresina'
    
    # Renomeia colunas para formato padrão
    df = df.rename(columns={
        'Area_m2': 'area',
        'Quartos': 'quartos',
        'Banheiros': 'banheiros',
    })
    
    # Calcula densidade de cômodos
    df['densidade_comodos'] = (df['quartos'] + df['banheiros']) / df['area']
    
    print(f"[OK] Dataset preparado: {len(df)} registros válidos")
    print(f"  - Bairros únicos: {df['bairro'].nunique()}")
    print(f"  - Tipos únicos: {df['tipo'].nunique()}")
    print(f"  - Área média: {df['area'].mean():.1f} m²")
    print(f"  - Preço médio: R$ {df['Valor_Anuncio'].mean():,.2f}")
    
    return df


def build_feature_matrix(
    df: pd.DataFrame,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, LabelEncoder], StandardScaler, Dict]:
    """Constrói a matriz de features usando Label Encoding para variáveis categóricas"""
    label_encoders: Dict[str, LabelEncoder] = {}
    
    # Codifica variáveis categóricas
    for col in ["tipo", "bairro", "cidade"]:
        encoder = LabelEncoder()
        df[f"{col}_encoded"] = encoder.fit_transform(df[col])
        label_encoders[col] = encoder
        print(f"  - {col}: {len(encoder.classes_)} classes únicas")
    
    # Features finais (mesmo formato do train_model.py original)
    feature_columns = [
        "area",
        "quartos",
        "banheiros",
        "densidade_comodos",
        "tipo_encoded",
        "bairro_encoded",
        "cidade_encoded",
    ]
    
    X = df[feature_columns].values
    y = df["Valor_Anuncio"].values
    
    # Normaliza features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    metadata = {
        "feature_columns": feature_columns,
        "preco_por_m2_median": float((df["Valor_Anuncio"] / df["area"]).median()),
    }
    
    print(f"[OK] Matriz de features construída: {X_scaled.shape}")
    
    return X_scaled, y, label_encoders, scaler, metadata


def train_gradient_boosting(X: np.ndarray, y: np.ndarray) -> GradientBoostingRegressor:
    """
    Treina o modelo Gradient Boosting com os parâmetros validados.
    """
    print("\n[OK] Iniciando treinamento do modelo Gradient Boosting...")
    model = GradientBoostingRegressor(
        n_estimators=200,
        learning_rate=0.1,
        max_depth=5,
        subsample=0.9,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=42,
    )
    model.fit(X, y)
    print("[OK] Modelo treinado com sucesso!")
    return model


def evaluate(model, X_train, X_test, y_train, y_test):
    """Avalia o modelo e exibe métricas"""
    y_pred = model.predict(X_test)
    metrics = {
        "mae": mean_absolute_error(y_test, y_pred),
        "rmse": math.sqrt(mean_squared_error(y_test, y_pred)),
        "r2": r2_score(y_test, y_pred),
    }
    print("\n=== Métricas de Desempenho (Gradient Boosting - OLX) ===")
    print(f"MAE : R$ {metrics['mae']:,.2f}")
    print(f"RMSE: R$ {metrics['rmse']:,.2f}")
    print(f"R²  : {metrics['r2']:.4f}")
    return metrics


def save_artifacts(model, scaler, label_encoders, metadata):
    """Salva o modelo e pré-processador no formato esperado pela API"""
    preprocessor = {
        "scaler": scaler,
        "label_encoders": label_encoders,
        "feature_columns": metadata["feature_columns"],
        "reference_values": {"preco_por_m2_median": metadata["preco_por_m2_median"]},
    }
    full_artifact = {"model": model, "preprocessor": preprocessor, "metadata": metadata}
    
    joblib.dump(full_artifact, MODEL_PATH)
    joblib.dump(preprocessor, PREPROCESSOR_PATH)
    print(f"\n[OK] Modelo salvo em {MODEL_PATH}")
    print(f"[OK] Pré-processador salvo em {PREPROCESSOR_PATH}")


def main():
    print("=" * 70)
    print("=== Especulai - Treinamento Gradient Boosting (Modelo OLX) ===")
    print("=" * 70)
    print("\nEste modelo será treinado APENAS com dados da fonte OLX")
    print("para evitar viés de outras fontes (ex: RochaRocha).\n")
    
    # Prepara dataset
    df = prepare_dataset_olx()
    
    # Constrói matriz de features
    X_scaled, y, label_encoders, scaler, metadata = build_feature_matrix(df)
    
    # Divide em treino e teste
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42
    )
    print(f"\n[OK] Divisão treino/teste: {len(X_train)} / {len(X_test)} registros")
    
    # Treina modelo
    model = train_gradient_boosting(X_train, y_train)
    
    # Avalia modelo
    evaluate(model, X_train, X_test, y_train, y_test)
    
    # Salva artefatos
    save_artifacts(model, scaler, label_encoders, metadata)
    
    print("\n" + "=" * 70)
    print("[OK] Treinamento concluído com sucesso!")
    print("=" * 70)
    print("\nO modelo está pronto para ser usado pela API.")
    print(f"Artefatos salvos em: {ARTIFACT_DIR}")


if __name__ == "__main__":
    main()

