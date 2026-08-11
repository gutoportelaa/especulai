"""Exporta o modelo treinado para JSON, para inferência no navegador.

O front calcula o preço no cliente: não há API para hospedar, não há cold start
e o custo de operação é zero.

Por que árvores cruas e não ONNX: o onnxruntime-web arrasta ~27 MB de WASM para
rodar um GradientBoosting de 200 árvores e 8,6 mil nós. As árvores em JSON dão
algumas centenas de KB, avaliam em microssegundos e não precisam de runtime,
de `wasmPaths` nem de cabeçalhos COOP/COEP no host estático.

A predição do GradientBoostingRegressor é exatamente:

    preco = init + learning_rate * Σ_i  folha_i(x_normalizado)

Detalhe que não é opcional: as árvores do sklearn convertem `X` para float32
antes de comparar com o threshold (que segue em float64). Quem consumir este
JSON tem que fazer o mesmo — `Math.fround(x) <= threshold` no JS. Sem isso, um
valor a 1e-8 do corte desce pelo ramo errado.

Saída em `frontend/public/model/especulai.json`:
  feature_columns, feature_defaults, bairro_profiles  -> montagem do vetor
  scaler {mean, scale}                                -> normalização
  trees {left, right, feature, threshold, value}      -> as 200 árvores achatadas

`tests/test_web_export_parity.py` trava a paridade com o sklearn.

Uso: uv run python -m ml.pipeline.export_web
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np

from config.paths import ARTIFACT_DIR, PROJECT_ROOT

WEB_MODEL_DIR = PROJECT_ROOT / "frontend" / "public" / "model"

# Thresholds NÃO são arredondados. As features normalizadas se aglomeram perto
# de zero e os cortes caem a 1e-7 umas das outras: arredondar para 6 casas jogou
# valores para o lado errado da comparação e errou o preço em até 1,3%.
# `json.dumps` já emite a menor string que faz round-trip do float64.
#
# Folhas são preços em reais; 4 casas são 0,0001 centavo de erro.
CASAS_FOLHA = 4


def _load_artifact(path: Path) -> dict[str, Any]:
    artifact = joblib.load(path)
    if not isinstance(artifact, dict) or "model" not in artifact:
        raise ValueError(f"{path} não é um artefato de treino ({{model, preprocessor, metadata}}).")
    return artifact


def _flatten_trees(model) -> dict[str, list]:
    """Achata as 200 árvores em arrays paralelos, com offset por árvore.

    Um array por campo (em vez de objetos aninhados por nó) porque o JSON fica
    ~3x menor e a travessia em JS vira aritmética de índice.
    """
    left: list[int] = []
    right: list[int] = []
    feature: list[int] = []
    threshold: list[float] = []
    value: list[float] = []
    roots: list[int] = []

    for i in range(model.n_estimators_):
        tree = model.estimators_[i, 0].tree_
        offset = len(left)
        roots.append(offset)

        for node in range(tree.node_count):
            filho_esq = tree.children_left[node]
            filho_dir = tree.children_right[node]
            folha = filho_esq == -1

            left.append(-1 if folha else int(filho_esq) + offset)
            right.append(-1 if folha else int(filho_dir) + offset)
            feature.append(-1 if folha else int(tree.feature[node]))
            threshold.append(0.0 if folha else float(tree.threshold[node]))
            value.append(round(float(tree.value[node].ravel()[0]), CASAS_FOLHA) if folha else 0.0)

    return {
        "roots": roots,
        "left": left,
        "right": right,
        "feature": feature,
        "threshold": threshold,
        "value": value,
    }


def export(artifact_path: Path | None = None, out_dir: Path | None = None) -> Path:
    artifact_path = artifact_path or ARTIFACT_DIR / "modelo_definitivo.joblib"
    out_dir = out_dir or WEB_MODEL_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    artifact = _load_artifact(artifact_path)
    model = artifact["model"]
    pre = artifact["preprocessor"]
    scaler = pre["scaler"]

    feature_columns: list[str] = list(pre["feature_columns"])
    n = len(feature_columns)

    init = float(model._raw_predict_init(np.zeros((1, n))).ravel()[0])

    bairros = sorted(col[len("Bairro_") :] for col in feature_columns if col.startswith("Bairro_"))

    payload = {
        "feature_columns": feature_columns,
        "feature_defaults": {k: float(v) for k, v in (pre.get("feature_defaults") or {}).items()},
        "bairro_profiles": {
            bairro: {k: float(v) for k, v in perfil.items()}
            for bairro, perfil in (pre.get("bairro_profiles") or {}).items()
        },
        "bairros": bairros,
        "scaler": {
            "mean": [float(v) for v in scaler.mean_],
            "scale": [float(v) for v in scaler.scale_],
        },
        "init": init,
        "learning_rate": float(model.learning_rate),
        "trees": _flatten_trees(model),
        "metrics": artifact.get("metadata", {}).get("metrics", {}),
        "trained_at": str(artifact.get("metadata", {}).get("trained_at", "")),
    }

    out_path = out_dir / "especulai.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), "utf-8")

    kb = out_path.stat().st_size / 1024
    print(f"[OK] {out_path} ({kb:.0f} KB)")
    print(f"     {n} features, {len(bairros)} bairros, {len(payload['trees']['left'])} nós")
    return out_path


if __name__ == "__main__":
    export()
