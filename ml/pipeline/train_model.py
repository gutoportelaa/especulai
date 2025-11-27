"""
Treina modelo ÚNICO Gradient Boosting com dataset OLX.

Entrada: dataset_treino_olx_final.csv (preparado com prepare_dataset.py)
Saída: modelo_definitivo.joblib + preprocessador.joblib

Responsabilidades:
  - Carregar dataset já preparado
  - Construir matriz de features (já com One-Hot Encoding)
  - Normalizar com StandardScaler
  - Treinar Gradient Boosting
  - Avaliar e salvar artefatos

Não faz: Limpeza, enriquecimento, filtragem de fontes (feito no prepare_dataset.py)
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple
from datetime import datetime
import logging
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import math
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "artifacts"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

DATA_ROOT = WORKSPACE_ROOT / "dados_imoveis_teresina"
DATA_ROOT.mkdir(parents=True, exist_ok=True)

# Dataset preparado (entrada)
DATASET_PATH = DATA_ROOT / "dataset_treino_olx_final.csv"

# Artefatos (saída)
# Nome do modelo pode ser parametrizado via variável de ambiente MODEL_NAME.
# Se não existir, usamos um nome com timestamp para evitar sobrescrita.
model_name = os.environ.get("MODEL_NAME")
if model_name:
    MODEL_PATH = ARTIFACT_DIR / model_name
else:
    MODEL_PATH = ARTIFACT_DIR / f"modelo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.joblib"
PREPROCESSOR_PATH = ARTIFACT_DIR / "preprocessador.joblib"
TRAIN_LOG_FILE = DATA_ROOT / "train_model_log.txt"

TARGET_COLUMN = "Valor_Anuncio"

# ============================================================================
# LOGGING
# ============================================================================

def setup_logging():
    """Configura logging para arquivo e console."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(TRAIN_LOG_FILE, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


logger = setup_logging()

# ============================================================================
# CARREGAMENTO E VALIDAÇÃO
# ============================================================================

def load_and_validate_dataset(csv_path: Path) -> pd.DataFrame:
    """
    Carrega e valida dataset preparado.
    
    Args:
        csv_path: Caminho do dataset_treino_olx_final.csv
    
    Returns:
        DataFrame validado
    
    Raises:
        FileNotFoundError: Se arquivo não existe
        ValueError: Se schema inválido
    """
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Dataset {csv_path} não encontrado. "
            "Execute prepare_dataset.py primeiro."
        )
    
    logger.info(f"[LOAD] Carregando dataset: {csv_path}")
    df = pd.read_csv(csv_path)
    
    logger.info(f"[LOAD] Dataset carregado: {len(df)} registros, {len(df.columns)} features")
    
    # Validação: coluna alvo existe
    if TARGET_COLUMN not in df.columns:
        raise ValueError(
            f"Coluna alvo '{TARGET_COLUMN}' não encontrada no dataset. "
            f"Colunas disponíveis: {df.columns.tolist()}"
        )
    
    # Validação: sem NaN na coluna alvo
    nan_count = df[TARGET_COLUMN].isna().sum()
    if nan_count > 0:
        logger.warning(f"[LOAD] {nan_count} valores faltantes em {TARGET_COLUMN}, removendo...")
        df = df.dropna(subset=[TARGET_COLUMN])
    
    logger.info("[LOAD] ✓ Dataset validado com sucesso")
    return df


# ============================================================================
# CONSTRUÇÃO DE FEATURES
# ============================================================================

def build_feature_matrix(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, StandardScaler, Dict]:
    """
    Constrói matriz de features a partir do dataset já preparado.
    
    Assume que o dataset já tem:
      - One-Hot Encoding aplicado
      - Features numéricas
      - Feature Engineering executado
    
    Args:
        df: DataFrame com dados preparados
    
    Returns:
        Tupla (X_scaled, y, scaler, metadata)
    """
    logger.info("[FEAT] Construindo matriz de features...")
    
    # Seleciona apenas colunas numéricas (exclui alvo)
    X = df.drop(columns=[TARGET_COLUMN]).select_dtypes(include=[np.number])
    y = df[TARGET_COLUMN].values
    
    logger.info(f"[FEAT] Features selecionadas: {X.shape[1]}")
    logger.info(f"[FEAT] Target shape: {y.shape}")
    
    # Normalização
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Metadata para posterior uso em predição
    metadata = {
        "feature_columns": X.columns.tolist(),
        "target_column": TARGET_COLUMN,
        "trained_at": datetime.now().isoformat(),
        "dataset_shape": {
            "n_samples": len(df),
            "n_features": X.shape[1],
        }
    }
    
    logger.info("[FEAT] ✓ Matriz de features construída com sucesso")
    return X_scaled, y, scaler, metadata


# ============================================================================
# TREINAMENTO
# ============================================================================

def train_gradient_boosting(X_train: np.ndarray, y_train: np.ndarray) -> GradientBoostingRegressor:
    """
    Treina modelo Gradient Boosting com parâmetros validados.
    
    Parâmetros otimizados via notebook de análise:
      - n_estimators=200
      - learning_rate=0.1
      - max_depth=5
      - subsample=0.9
      - min_samples_split=4
      - min_samples_leaf=2
    
    Args:
        X_train: Features de treino
        y_train: Target de treino
    
    Returns:
        Modelo treinado
    """
    logger.info("[TRAIN] Iniciando treinamento do Gradient Boosting...")
    logger.info("[TRAIN] Parâmetros: n_estimators=200, learning_rate=0.1, max_depth=5")
    
    model = GradientBoostingRegressor(
        n_estimators=200,
        learning_rate=0.1,
        max_depth=5,
        subsample=0.9,
        min_samples_split=4,
        min_samples_leaf=2,
        random_state=42,
        verbose=0
    )
    
    model.fit(X_train, y_train)
    logger.info("[TRAIN] ✓ Modelo treinado com sucesso!")
    
    return model


def evaluate_model(
    model: GradientBoostingRegressor,
    X_train: np.ndarray, X_test: np.ndarray,
    y_train: np.ndarray, y_test: np.ndarray
) -> Dict:
    """
    Avalia modelo em treino e teste.
    
    Args:
        model: Modelo treinado
        X_train, X_test: Features de treino/teste
        y_train, y_test: Target de treino/teste
    
    Returns:
        Dicionário com métricas
    """
    logger.info("[EVAL] Avaliando modelo...")
    
    # Predições
    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)
    
    # Métricas
    metrics = {
        "train": {
            "mae": mean_absolute_error(y_train, y_pred_train),
            "rmse": math.sqrt(mean_squared_error(y_train, y_pred_train)),
            "r2": r2_score(y_train, y_pred_train),
        },
        "test": {
            "mae": mean_absolute_error(y_test, y_pred_test),
            "rmse": math.sqrt(mean_squared_error(y_test, y_pred_test)),
            "r2": r2_score(y_test, y_pred_test),
        }
    }
    
    print("\n" + "=" * 80)
    print("=== MÉTRICAS DE DESEMPENHO (GRADIENT BOOSTING) ===")
    print("=" * 80)
    
    print("\n🎓 TREINO:")
    print(f"  MAE : R$ {metrics['train']['mae']:>12,.2f}")
    print(f"  RMSE: R$ {metrics['train']['rmse']:>12,.2f}")
    print(f"  R²  : {metrics['train']['r2']:>15.4f}")
    
    print("\n✅ TESTE:")
    print(f"  MAE : R$ {metrics['test']['mae']:>12,.2f}")
    print(f"  RMSE: R$ {metrics['test']['rmse']:>12,.2f}")
    print(f"  R²  : {metrics['test']['r2']:>15.4f}")
    
    print("=" * 80 + "\n")
    
    logger.info(f"[EVAL] Métricas teste -> MAE: {metrics['test']['mae']:.2f}, R²: {metrics['test']['r2']:.4f}")
    
    return metrics


def save_artifacts(model: GradientBoostingRegressor, scaler: StandardScaler, metadata: Dict):
    """
    Salva modelo e pré-processador em disco.
    
    Args:
        model: Modelo treinado
        scaler: StandardScaler ajustado
        metadata: Dicionário com metadata
    """
    logger.info("[SAVE] Salvando artefatos...")
    
    # Pré-processador (usado em produção)
    # Além do scaler e feature_columns, tentamos derivar encoders categóricos
    # a partir de colunas One-Hot Encoding presentes em metadata["feature_columns"].
    feature_cols = metadata.get("feature_columns", [])

    # Detecta colunas OHE para tipo e bairro (prefixos esperados)
    tipo_prefixes = ["Tipo_Imovel_", "TipoImovel_", "tipo_", "Tipo_"]
    bairro_prefixes = ["Bairro_", "bairro_"]

    tipo_classes = []
    bairro_classes = []
    for col in feature_cols:
        for p in tipo_prefixes:
            if col.startswith(p):
                cls = col[len(p):]
                tipo_classes.append(cls)
                break
        for p in bairro_prefixes:
            if col.startswith(p):
                cls = col[len(p):]
                bairro_classes.append(cls)
                break

    # Normaliza classes (remove empty, convert underscores to spaces)
    def normalize_class_list(lst):
        out = []
        for v in lst:
            if not v:
                continue
            s = str(v).strip()
            s = s.replace("_", " ")
            out.append(s)
        # unique preserving order
        seen = set()
        uniq = []
        for x in out:
            if x not in seen:
                seen.add(x)
                uniq.append(x)
        return uniq

    tipo_classes = normalize_class_list(tipo_classes)
    bairro_classes = normalize_class_list(bairro_classes)

    # Cria label encoders se houver classes detectadas
    label_encoders = {}
    try:
        from sklearn.preprocessing import LabelEncoder
        import numpy as np

        if tipo_classes:
            le_tipo = LabelEncoder()
            le_tipo.classes_ = np.array(tipo_classes, dtype=object)
            label_encoders['tipo'] = le_tipo

        if bairro_classes:
            le_bairro = LabelEncoder()
            le_bairro.classes_ = np.array(bairro_classes, dtype=object)
            label_encoders['bairro'] = le_bairro

        # Cidade: assumimos 'teresina' como padrão
        le_cidade = LabelEncoder()
        le_cidade.classes_ = np.array(["Teresina", "teresina"], dtype=object)
        label_encoders['cidade'] = le_cidade
    except Exception:
        label_encoders = {}

    preprocessor = {
        "scaler": scaler,
        "feature_columns": feature_cols,
        "target_column": metadata.get("target_column"),
        "label_encoders": label_encoders,
        "reference_values": metadata.get("reference_values", {})
    }
    
    # Artefato completo (modelo + preprocessador + metadata)
    full_artifact = {
        "model": model,
        "preprocessor": preprocessor,
        "metadata": metadata,
    }
    
    # Salvar
    joblib.dump(full_artifact, MODEL_PATH)
    joblib.dump(preprocessor, PREPROCESSOR_PATH)
    
    logger.info(f"[SAVE] ✓ Modelo salvo: {MODEL_PATH}")
    logger.info(f"[SAVE] ✓ Pré-processador salvo: {PREPROCESSOR_PATH}")
    
    print(f"\n💾 Artefatos salvos:")
    print(f"   Modelo: {MODEL_PATH}")
    print(f"   Preprocessador: {PREPROCESSOR_PATH}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Função principal do treinamento."""
    print()
    print("=" * 80)
    print("=== ESPECULAI - TREINAMENTO DO MODELO (OLX) ===")
    print("=" * 80)
    print()
    
    try:
        # 1. Carregar e validar dataset
        df = load_and_validate_dataset(DATASET_PATH)
        # Se o dataset estiver vazio, não tentamos treinar — apenas registramos e saímos com sucesso controlado
        if len(df) == 0:
            logger.warning("[MAIN] Dataset vazio. Nenhum treinamento será executado.")
            print()
            print("[WARN] Dataset vazio — treinamento ignorado.")
            return
        
        # 2. Construir features
        X_scaled, y, scaler, metadata = build_feature_matrix(df)
        
        # 3. Divisão treino/teste
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42
        )
        logger.info(f"[SPLIT] Treino: {len(X_train)} | Teste: {len(X_test)}")
        
        # 4. Treinar modelo
        model = train_gradient_boosting(X_train, y_train)
        
        # 5. Avaliar
        metrics = evaluate_model(model, X_train, X_test, y_train, y_test)
        
        # 6. Salvar artefatos
        save_artifacts(model, scaler, metadata)
        
        print()
        print("=" * 80)
        print("[OK] Treinamento concluído com sucesso! Modelo pronto para produção.")
        print("=" * 80)
        print()
        
    except Exception as e:
        logger.error(f"[ERROR] Erro durante treinamento: {e}")
        raise


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()

