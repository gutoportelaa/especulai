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

import logging
import math
import os
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "artifacts"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

from config.paths import DATA_ROOT as _DATA_ROOT

DATA_ROOT = _DATA_ROOT
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

# Features derivadas do próprio alvo — treinar com elas produz R² irreal.
# FipeZap_Diferenca_m2 == Valor_Anuncio / Area_m2 - FipeZap_m2 (identidade exata),
# ou seja, o modelo apenas inverteria a álgebra em vez de aprender o preço.
LEAKAGE_COLUMNS = ("FipeZap_Diferenca_m2",)

# Abaixo disso a mediana do bairro é ruído; cai-se no padrão global.
MIN_AMOSTRAS_PERFIL_BAIRRO = 3

URL_COLUMN = "URL_Anuncio"

# Um mesmo imóvel reanunciado tem estas colunas idênticas. Serve para manter
# todas as cópias do mesmo lado do split treino/teste.
GROUP_KEY_COLUMNS = ("Area_m2", "Quartos", "Banheiros", "Latitude", "Longitude")

# Anúncios abaixo disso são aluguel ou lixo que escapou da limpeza.
PRECO_MINIMO_VENDA = 50_000.0

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

    baratos = (df[TARGET_COLUMN] < PRECO_MINIMO_VENDA).sum()
    if baratos:
        logger.info(f"[LOAD] {baratos} anúncios abaixo de R$ {PRECO_MINIMO_VENDA:,.0f} removidos (aluguel/ruído)")
        df = df[df[TARGET_COLUMN] >= PRECO_MINIMO_VENDA]

    df = deduplicate_listings(df)
    logger.info("[LOAD] ✓ Dataset validado com sucesso")
    return df


def deduplicate_listings(df: pd.DataFrame) -> pd.DataFrame:
    """Remove anúncios repetidos.

    O mesmo imóvel é reanunciado várias vezes na OLX (há casos com 27 cópias).
    Sem isso, o split aleatório coloca cópias do mesmo imóvel em treino e teste,
    e o modelo memoriza em vez de generalizar — o R² sobe sem que o modelo
    melhore.
    """
    if URL_COLUMN not in df.columns:
        logger.warning(f"[LOAD] Coluna '{URL_COLUMN}' ausente — deduplicação ignorada")
        return df

    antes = len(df)
    df = df.drop_duplicates(subset=[URL_COLUMN]).reset_index(drop=True)
    if antes != len(df):
        logger.info(f"[LOAD] Anúncios duplicados removidos: {antes - len(df)} ({antes} -> {len(df)})")
    return df


def listing_groups(df: pd.DataFrame) -> np.ndarray:
    """Identifica o imóvel físico por trás de cada anúncio.

    Anúncios distintos (URLs diferentes) do mesmo imóvel precisam ficar do mesmo
    lado do split; caso contrário o teste mede memorização.
    """
    chaves = [c for c in GROUP_KEY_COLUMNS if c in df.columns]
    if not chaves:
        return np.arange(len(df))
    return df.groupby(chaves, dropna=False).ngroup().to_numpy()


# ============================================================================
# CONSTRUÇÃO DE FEATURES
# ============================================================================

def build_feature_matrix(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, StandardScaler, dict]:
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

    dropped = [TARGET_COLUMN, *(c for c in LEAKAGE_COLUMNS if c in df.columns)]

    # bool entra junto: as colunas one-hot de Bairro são booleanas e
    # select_dtypes(np.number) sozinho as descartaria silenciosamente.
    X = df.drop(columns=dropped).select_dtypes(include=[np.number, "bool"]).astype(float)
    y = df[TARGET_COLUMN].values

    # Colunas constantes não carregam informação e poluem o ranking de features.
    constantes = [c for c in X.columns if X[c].nunique(dropna=False) <= 1]
    if constantes:
        logger.info(f"[FEAT] Features constantes removidas: {constantes}")
        X = X.drop(columns=constantes)

    leaked = [c for c in LEAKAGE_COLUMNS if c in df.columns]
    if leaked:
        logger.info(f"[FEAT] Features removidas por vazamento de alvo: {leaked}")
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
    
    metadata["feature_defaults"] = build_feature_defaults(X)
    metadata["bairro_profiles"] = build_bairro_profiles(X)

    logger.info("[FEAT] ✓ Matriz de features construída com sucesso")
    return X_scaled, y, scaler, metadata


def build_feature_defaults(X: pd.DataFrame) -> dict[str, float]:
    """Mediana de cada feature, usada em inferência para colunas que o usuário não informa.

    Sem isso o serviço preencheria com 0.0, que após o StandardScaler vira um
    outlier de vários desvios e achata a predição num valor constante.
    """
    return {col: float(X[col].median()) for col in X.columns}


def build_bairro_profiles(X: pd.DataFrame) -> dict[str, dict[str, float]]:
    """Perfil contextual mediano por bairro (coordenadas, distâncias a POIs, FipeZap).

    O usuário informa apenas o nome do bairro; essas features derivadas são
    reconstruídas a partir dos imóveis daquele bairro no conjunto de treino.
    """
    bairro_cols = [c for c in X.columns if c.startswith("Bairro_")]
    contextual = [c for c in X.columns if not c.startswith("Bairro_")]

    profiles: dict[str, dict[str, float]] = {}
    for col in bairro_cols:
        mask = X[col] > 0.5
        if mask.sum() < MIN_AMOSTRAS_PERFIL_BAIRRO:
            continue
        subset = X.loc[mask, contextual]
        profiles[col[len("Bairro_") :]] = {c: float(subset[c].median()) for c in contextual}

    logger.info(f"[FEAT] Perfis de bairro construídos: {len(profiles)}/{len(bairro_cols)}")
    return profiles


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


def _metricas(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Métricas absolutas e relativas.

    MdAPE e a taxa de acerto em ±20% são as mais informativas aqui: o MAE em
    reais é dominado pelos imóveis caros, e o R² esconde viés sistemático.
    """
    erro_rel = np.abs(y_pred - y_true) / y_true
    return {
        "mae": mean_absolute_error(y_true, y_pred),
        "rmse": math.sqrt(mean_squared_error(y_true, y_pred)),
        "r2": r2_score(y_true, y_pred),
        "mdape": float(np.median(erro_rel)),
        "dentro_20pct": float(np.mean(erro_rel <= 0.20)),
    }


def _metricas_por_faixa(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Erro e viés por faixa de preço, para expor a regressão à média.

    O modelo tende a puxar os extremos para o centro: superestima o barato e
    subestima o caro. O agregado não mostra isso.
    """
    limites = [0, 250_000, 450_000, 800_000, 1_200_000, np.inf]
    rotulos = ["<250k", "250-450k", "450-800k", "800k-1,2M", ">1,2M"]

    faixas = {}
    for i, rotulo in enumerate(rotulos):
        m = (y_true >= limites[i]) & (y_true < limites[i + 1])
        if not m.any():
            continue
        faixas[rotulo] = {
            "n": int(m.sum()),
            "mdape": float(np.median(np.abs(y_pred[m] - y_true[m]) / y_true[m])),
            "vies_mediano": float(np.median((y_pred[m] - y_true[m]) / y_true[m])),
        }
    return faixas


def evaluate_model(
    model: GradientBoostingRegressor,
    X_train: np.ndarray, X_test: np.ndarray,
    y_train: np.ndarray, y_test: np.ndarray
) -> dict:
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
        "train": _metricas(y_train, y_pred_train),
        "test": _metricas(y_test, y_pred_test),
        "test_por_faixa": _metricas_por_faixa(y_test, y_pred_test),
    }
    
    print("\n" + "=" * 80)
    print("=== MÉTRICAS DE DESEMPENHO (GRADIENT BOOSTING) ===")
    print("=" * 80)
    
    print("\n🎓 TREINO:")
    print(f"  MAE : R$ {metrics['train']['mae']:>12,.2f}")
    print(f"  RMSE: R$ {metrics['train']['rmse']:>12,.2f}")
    print(f"  R²  : {metrics['train']['r2']:>15.4f}")
    
    print("\n✅ TESTE (split por grupo de imóvel):")
    print(f"  MAE        : R$ {metrics['test']['mae']:>12,.2f}")
    print(f"  RMSE       : R$ {metrics['test']['rmse']:>12,.2f}")
    print(f"  R²         : {metrics['test']['r2']:>15.4f}")
    print(f"  MdAPE      : {metrics['test']['mdape'] * 100:>14.1f}%")
    print(f"  ±20%       : {metrics['test']['dentro_20pct'] * 100:>14.1f}%")

    print("\n📊 POR FAIXA DE PREÇO (viés > 0 = superestima):")
    print(f"  {'faixa':<12}{'n':>6}{'MdAPE':>9}{'viés':>9}")
    for rotulo, m in metrics["test_por_faixa"].items():
        print(f"  {rotulo:<12}{m['n']:>6}{m['mdape'] * 100:>8.1f}%{m['vies_mediano'] * 100:>8.1f}%")

    print("=" * 80 + "\n")
    
    logger.info(f"[EVAL] Métricas teste -> MAE: {metrics['test']['mae']:.2f}, R²: {metrics['test']['r2']:.4f}")
    
    return metrics


def save_artifacts(model: GradientBoostingRegressor, scaler: StandardScaler, metadata: dict):
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
        import numpy as np
        from sklearn.preprocessing import LabelEncoder

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
        "reference_values": metadata.get("reference_values", {}),
        "feature_defaults": metadata.get("feature_defaults", {}),
        "bairro_profiles": metadata.get("bairro_profiles", {}),
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
    
    print("\n💾 Artefatos salvos:")
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
        
        # 3. Divisão treino/teste — por grupo, para que cópias do mesmo imóvel
        #    não apareçam dos dois lados e inflem a métrica.
        grupos = listing_groups(df)
        idx_train, idx_test = next(
            GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42).split(
                X_scaled, y, groups=grupos
            )
        )
        X_train, X_test = X_scaled[idx_train], X_scaled[idx_test]
        y_train, y_test = y[idx_train], y[idx_test]
        logger.info(
            f"[SPLIT] Treino: {len(X_train)} | Teste: {len(X_test)} | "
            f"grupos distintos: {len(np.unique(grupos))}"
        )
        
        # 4. Treinar modelo
        model = train_gradient_boosting(X_train, y_train)
        
        # 5. Avaliar
        metrics = evaluate_model(model, X_train, X_test, y_train, y_test)
        metadata["metrics"] = metrics

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

