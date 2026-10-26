"""Limiar de outliers por resíduo e intervalos conformais, medidos só na validação.

Resíduos fora da amostra (CV agrupada no treino) servem a dois fins:
  - outliers: anúncios com |resíduo em log| acima de K desvios robustos (MAD) são removidos do
    treino; compara-se o modelo com e sem a limpeza na validação, que não é limpa;
  - conformal: o quantil dos |resíduos| de treino dá a meia-largura do intervalo em log, e a
    cobertura é conferida na validação.

Uso: uv run python -m ml.experiments.intervalos_outliers
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import GroupKFold

from ml.experiments.baseline_atributos import carregar, matriz, metricas

SEED = 42
K_MAD = 3.5
NIVEIS = (0.5, 0.8, 0.9)


def modelo() -> GradientBoostingRegressor:
    return GradientBoostingRegressor(
        n_estimators=200, learning_rate=0.1, max_depth=5, random_state=SEED
    )


def residuos_oof(df: pd.DataFrame) -> np.ndarray:
    X, y = matriz(df, None, False), np.log(df["Valor_Anuncio"].to_numpy())
    pred = np.zeros(len(df))
    for a, b in GroupKFold(n_splits=5).split(X, y, df["ID_Grupo"]):
        pred[b] = modelo().fit(X.iloc[a], y[a]).predict(X.iloc[b])
    return y - pred


def main() -> None:
    for negocio in ("venda", "aluguel"):
        df = carregar(negocio)
        tr = df[df["split"] == "treino"].reset_index(drop=True)
        va = df[df["split"] == "validacao"].reset_index(drop=True)
        res = residuos_oof(tr)
        mad = 1.4826 * np.median(np.abs(res - np.median(res)))
        fora = np.abs(res - np.median(res)) > K_MAD * mad
        print(f"\n== {negocio}: treino {len(tr)} | validação {len(va)}")
        print(f"MAD robusto do resíduo em log: {mad:.3f} | outliers (>{K_MAD} MAD): {fora.sum()}")
        if fora.any():
            colunas = ["Fonte", "Tipo_Imovel", "Bairro", "Area_m2", "Quartos", "Valor_Anuncio"]
            amostra = tr[fora].assign(resid_log=res[fora]).sort_values("resid_log")
            print(amostra[colunas + ["resid_log"]].head(6).round(2).to_string())
            print(amostra[colunas + ["resid_log"]].tail(6).round(2).to_string())

        X_va = matriz(va, None, False)
        linhas = {}
        for rotulo, manter in (("com todos", np.ones(len(tr), bool)), ("sem outliers", ~fora)):
            sub = tr[manter]
            X_tr = matriz(sub, None, False)
            m = modelo().fit(X_tr, np.log(sub["Valor_Anuncio"]))
            pred = m.predict(X_va.reindex(columns=X_tr.columns, fill_value=0))
            linhas[rotulo] = metricas(va["Valor_Anuncio"].to_numpy(), np.exp(pred))
        print(pd.DataFrame(linhas).T.round(3).to_string())

        # intervalos: meia-largura em log vem dos resíduos de treino (todos os anúncios)
        y_va = np.log(va["Valor_Anuncio"].to_numpy())
        X_tr = matriz(tr, None, False)
        m = modelo().fit(X_tr, np.log(tr["Valor_Anuncio"]))
        pred_va = m.predict(X_va.reindex(columns=X_tr.columns, fill_value=0))
        terco = pd.qcut(pd.Series(np.exp(pred_va)), 3, labels=["barato", "meio", "caro"])
        print("cobertura na validação (nominal → observada | por terço de preço previsto):")
        for nivel in NIVEIS:
            q = np.quantile(np.abs(res), nivel)
            dentro = np.abs(y_va - pred_va) <= q
            por_terco = pd.Series(dentro).groupby(terco.to_numpy()).mean()
            partes = " ".join(f"{k} {v:.0%}" for k, v in por_terco.items())
            print(f"  {nivel:.0%} → {dentro.mean():.1%} | ×/÷ {np.exp(q):.2f}  [{partes}]")


if __name__ == "__main__":
    main()
