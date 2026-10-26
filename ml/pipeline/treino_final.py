"""Treino final por negócio: atributos + tipo + bairro + renda/densidade, intervalo por faixa.

Duas fases, para proteger o teste:
  desenvolvimento  treina em `treino`, calibra o intervalo e mede em `validacao`;
  final            reajusta em treino+validação e lê o `teste` uma única vez (`--abrir-teste`).

O intervalo é conformal em log: a meia-largura de cada faixa de preço previsto é o quantil dos
|resíduos| fora da amostra (CV agrupada por `ID_Grupo`) dos anúncios cuja previsão caiu na faixa.
Uma largura global cobre o conjunto mas sub-cobre o terço caro.

Uso: uv run python -m ml.pipeline.treino_final [--abrir-teste]
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import GroupKFold

from config.paths import ARTIFACT_DIR
from ml.experiments.baseline_atributos import carregar, metricas
from ml.experiments.renda_ibge import X_com, com_ibge

SEED = 42
NIVEL = 0.8
FAIXAS = 3


@dataclass
class Intervalos:
    """Cortes de preço previsto (R$) e meia-largura em log de cada faixa."""

    cortes: list[float]
    meia_largura: list[float]

    def faixa(self, preco: np.ndarray) -> np.ndarray:
        return np.searchsorted(self.cortes, preco)

    def limites(self, preco: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        w = np.asarray(self.meia_largura)[self.faixa(preco)]
        return preco * np.exp(-w), preco * np.exp(w)


def novo_modelo(semente: int = SEED) -> GradientBoostingRegressor:
    return GradientBoostingRegressor(
        n_estimators=200, learning_rate=0.1, max_depth=5, random_state=semente
    )


def calibrar(X: pd.DataFrame, y_log: np.ndarray, grupos: pd.Series) -> Intervalos:
    oof = np.zeros(len(X))
    for a, b in GroupKFold(n_splits=5).split(X, y_log, grupos):
        oof[b] = novo_modelo().fit(X.iloc[a], y_log[a]).predict(X.iloc[b])
    preco = np.exp(oof)
    cortes = [float(c) for c in np.quantile(preco, np.linspace(0, 1, FAIXAS + 1)[1:-1])]
    faixa = np.searchsorted(cortes, preco)
    res = np.abs(y_log - oof)
    largura = [float(np.quantile(res[faixa == k], NIVEL)) for k in range(FAIXAS)]
    return Intervalos(cortes, largura)


def avaliar(
    modelo: GradientBoostingRegressor, iv: Intervalos, X: pd.DataFrame, y: np.ndarray
) -> dict[str, object]:
    pred = np.exp(modelo.predict(X))
    lo, hi = iv.limites(pred)
    dentro = (y >= lo) & (y <= hi)
    por_faixa = pd.Series(dentro).groupby(iv.faixa(pred)).mean()
    return {
        "metricas": {k: round(float(v), 3) for k, v in metricas(y, pred).items()},
        "cobertura": round(float(dentro.mean()), 3),
        "cobertura_por_faixa": [round(float(v), 3) for v in por_faixa],
        "razao_media_hi_lo": round(float(np.mean(hi / lo)), 2),
    }


def treinar(negocio: str, abrir_teste: bool) -> dict[str, object]:
    df = com_ibge(carregar(negocio))
    tr, va, te = (
        df[df["split"] == s].reset_index(drop=True) for s in ("treino", "validacao", "teste")
    )
    saida: dict[str, object] = {"n": {"treino": len(tr), "validacao": len(va), "teste": len(te)}}

    X_tr = X_com(tr, None, True)
    y_tr = np.log(tr["Valor_Anuncio"].to_numpy())
    iv = calibrar(X_tr, y_tr, tr["ID_Grupo"])
    m = novo_modelo().fit(X_tr, y_tr)
    X_va = X_com(va, list(X_tr.columns), True)
    saida["desenvolvimento"] = avaliar(m, iv, X_va, va["Valor_Anuncio"].to_numpy())

    pool = pd.concat([tr, va], ignore_index=True)
    X_pool = X_com(pool, None, True)
    y_pool = np.log(pool["Valor_Anuncio"].to_numpy())
    iv_final = calibrar(X_pool, y_pool, pool["ID_Grupo"])
    modelo_final = novo_modelo().fit(X_pool, y_pool)
    if abrir_teste:
        X_te = X_com(te, list(X_pool.columns), True)
        saida["teste"] = avaliar(modelo_final, iv_final, X_te, te["Valor_Anuncio"].to_numpy())

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": modelo_final,
            "columns": list(X_pool.columns),
            "intervalos": iv_final.__dict__,
            "contagem_bairro": {str(k): int(v) for k, v in pool["Bairro"].value_counts().items()},
        },
        ARTIFACT_DIR / f"final_{negocio}.joblib",
    )
    saida["intervalo_final"] = iv_final.__dict__
    return saida


def main() -> None:
    parser = argparse.ArgumentParser(description="Treino final por negócio")
    parser.add_argument("--abrir-teste", action="store_true", help="lê o teste (uma única vez)")
    args = parser.parse_args()
    resultado = {n: treinar(n, args.abrir_teste) for n in ("venda", "aluguel")}
    print(json.dumps(resultado, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
