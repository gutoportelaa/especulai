"""
Treina o modelo definitivo (Gradient Boosting) a partir do dataset consolidado
gerado pelo pipeline de dados (`pipeline_ml.py`). O modelo e os pré-processadores
são salvos em `ml/artifacts/`, sendo consumidos diretamente pelo backend.
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

# Usa enriched_economic.csv como fonte (tem Tipo_Negocio original)
# Filtra apenas OLX para ter mais registros
DATASET_PATH = DATA_ROOT / "enriched_economic.csv"
DATASET_ALUGUEL_PATH = DATA_ROOT / "dataset_aluguel.csv"
DATASET_OLX_VENDA_PATH = DATA_ROOT / "dataset_olx_venda.csv"
MODEL_PATH = ARTIFACT_DIR / "modelo_definitivo.joblib"
PREPROCESSOR_PATH = ARTIFACT_DIR / "preprocessador.joblib"

PRIMARY_FEATURE_MAP = {
    "Valor_Anuncio": "Valor_Anuncio",
    "area": "Area_m2",
    "quartos": "Quartos",
    "banheiros": "Banheiros",
    "tipo": "Tipo_Imovel",
    "bairro": "Bairro",
}

REQUIRED_COLUMNS = ["Valor_Anuncio", "area", "quartos", "banheiros", "tipo", "bairro"]
LOCATION_COLUMNS = ["Latitude", "Longitude", "Rua", "Numero"]


def sanitize_olx_locations(df: pd.DataFrame) -> pd.DataFrame:
    if "Fonte" not in df.columns:
        return df
    mask = df["Fonte"].astype(str).str.lower() == "olx"
    cols = [col for col in LOCATION_COLUMNS if col in df.columns]
    if cols:
        df.loc[mask, cols] = np.nan
    return df


def prepare_dataset(csv_path: Path = DATASET_PATH) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset não encontrado em {csv_path}. Rode pipeline_ml.py antes.")

    df = pd.read_csv(csv_path)
    df = sanitize_olx_locations(df)

    # Separação de datasets: Venda e Aluguel (ANTES de filtrar por fonte)
    if 'Tipo_Negocio' in df.columns:
        # Normaliza a coluna Tipo_Negocio
        df['Tipo_Negocio'] = df['Tipo_Negocio'].astype(str).str.strip().str.title()
        
        # Separa dataset de aluguel (todas as fontes)
        df_aluguel = df[df['Tipo_Negocio'].str.lower() == 'aluguel'].copy()
        if len(df_aluguel) > 0:
            df_aluguel.to_csv(DATASET_ALUGUEL_PATH, index=False)
            print(f"[OK] Dataset de ALUGUEL salvo: {DATASET_ALUGUEL_PATH} ({len(df_aluguel)} registros)")
            
            # Separa aluguel OLX se existir
            if 'Fonte' in df_aluguel.columns:
                df_aluguel_olx = df_aluguel[df_aluguel['Fonte'].astype(str).str.strip().str.upper() == 'OLX'].copy()
                if len(df_aluguel_olx) > 0:
                    olx_aluguel_path = DATA_ROOT / "dataset_olx_aluguel.csv"
                    df_aluguel_olx.to_csv(olx_aluguel_path, index=False)
                    print(f"  -> Dataset de ALUGUEL (OLX) salvo: {olx_aluguel_path} ({len(df_aluguel_olx)} registros)")
        else:
            print("[AVISO] Nenhum registro de ALUGUEL encontrado no dataset.")
        
        # Filtra apenas VENDA para treinamento
        df_venda = df[df['Tipo_Negocio'].str.lower() == 'venda'].copy()
        
        # Prioriza OLX se existir, senão usa todas as fontes
        if 'Fonte' in df_venda.columns:
            df_venda_olx = df_venda[df_venda['Fonte'].astype(str).str.strip().str.upper() == 'OLX'].copy()
            if len(df_venda_olx) > 0:
                # Usa OLX de venda (mais registros)
                df_venda_olx.to_csv(DATASET_OLX_VENDA_PATH, index=False)
                print(f"[OK] Dataset de VENDA (OLX) salvo: {DATASET_OLX_VENDA_PATH} ({len(df_venda_olx)} registros)")
                df = df_venda_olx
                print(f"[OK] Usando VENDA (OLX): {len(df)} registros para treinamento")
            else:
                # Usa todas as fontes de venda
                print(f"[AVISO] Nenhum registro de VENDA (OLX) encontrado. Usando todas as fontes de VENDA.")
                print(f"[OK] Usando VENDA (todas as fontes): {len(df_venda)} registros para treinamento")
                df = df_venda
        else:
            df = df_venda
            print(f"[OK] Usando VENDA: {len(df)} registros para treinamento")
        
        if len(df) == 0:
            raise ValueError("Nenhum registro de VENDA encontrado no dataset. Verifique a coluna 'Tipo_Negocio'.")
    else:
        print("[AVISO] Coluna 'Tipo_Negocio' não encontrada. Treinando com todos os dados (pode comprometer o modelo).")

    rename_map = {raw: canonical for canonical, raw in PRIMARY_FEATURE_MAP.items() if raw in df.columns}
    df = df.rename(columns=rename_map)

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Colunas ausentes no dataset principal: {missing}")

    df = df.dropna(subset=REQUIRED_COLUMNS)
    df["area"] = pd.to_numeric(df["area"], errors="coerce").clip(lower=1)
    df["quartos"] = pd.to_numeric(df["quartos"], errors="coerce").fillna(0).astype(int)
    df["banheiros"] = pd.to_numeric(df["banheiros"], errors="coerce").fillna(0).astype(int)

    df = df.dropna(subset=["area"])

    df["tipo"] = df["tipo"].astype(str).str.lower().str.strip()
    df["bairro"] = df["bairro"].astype(str).str.title().str.strip()
    df["cidade"] = "Teresina"

    df["densidade_comodos"] = (df["quartos"] + df["banheiros"]) / df["area"]
    df = df[df["area"] > 0]
    return df


def build_feature_matrix(
    df: pd.DataFrame,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, LabelEncoder], StandardScaler, Dict]:
    label_encoders: Dict[str, LabelEncoder] = {}
    for col in ["tipo", "bairro", "cidade"]:
        encoder = LabelEncoder()
        df[f"{col}_encoded"] = encoder.fit_transform(df[col])
        label_encoders[col] = encoder

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

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    metadata = {
        "feature_columns": feature_columns,
        "preco_por_m2_median": float((df["Valor_Anuncio"] / df["area"]).median()),
    }

    return X_scaled, y, label_encoders, scaler, metadata


def train_gradient_boosting(X: np.ndarray, y: np.ndarray) -> GradientBoostingRegressor:
    """
    Treina o modelo Gradient Boosting com os parâmetros validados pelo notebook.
    Parâmetros do melhor modelo: n_estimators=200, learning_rate=0.1, max_depth=5
    """
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
    return model


def evaluate(model, X_train, X_test, y_train, y_test):
    y_pred = model.predict(X_test)
    metrics = {
        "mae": mean_absolute_error(y_test, y_pred),
        "rmse": math.sqrt(mean_squared_error(y_test, y_pred)),
        "r2": r2_score(y_test, y_pred),
    }
    print("\n=== Métricas de Desempenho (Gradient Boosting) ===")
    print(f"MAE : R$ {metrics['mae']:,.2f}")
    print(f"RMSE: R$ {metrics['rmse']:,.2f}")
    print(f"R²  : {metrics['r2']:.4f}")
    return metrics


def save_artifacts(model, scaler, label_encoders, metadata):
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
    print(f"[OK] Pre-processador salvo em {PREPROCESSOR_PATH}")


def main():
    print("=== Especulai - Treinamento Gradient Boosting (Modelo Definitivo) ===")
    df = prepare_dataset()
    X_scaled, y, label_encoders, scaler, metadata = build_feature_matrix(df)
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42
    )

    model = train_gradient_boosting(X_train, y_train)
    evaluate(model, X_train, X_test, y_train, y_test)
    save_artifacts(model, scaler, label_encoders, metadata)

    print("\n[OK] Treinamento concluido com sucesso!")


if __name__ == "__main__":
    main()

