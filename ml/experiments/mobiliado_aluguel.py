"""O campo "mobiliado" melhora o modelo de aluguel?

Usa os anúncios do VivaReal com a lista de comodidades presente (`Mobiliado` 0/1). Treina em
`treino` e mede em `validacao`, com e sem a variável; o teste não é lido. Como a validação é
pequena, repete com validação cruzada agrupada sobre treino+validação.

Uso: uv run python -m ml.experiments.mobiliado_aluguel
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import GroupKFold

from config.paths import DATA_ROOT
from ml.experiments.baseline_atributos import matriz, metricas

SEED = 42


def carregar() -> pd.DataFrame:
    canon = pd.read_csv(DATA_ROOT / "canonico.csv")
    split = pd.read_csv(DATA_ROOT / "splits" / "aluguel.csv")
    det = pd.read_csv(DATA_ROOT / "detalhes_aluguel.csv")[["ID_Imovel", "Mobiliado", "Comodidades"]]
    df = canon.merge(split[["ID_Imovel", "split"]], on="ID_Imovel", suffixes=("_x", ""))
    df = df.merge(det, on="ID_Imovel", how="inner")
    return df.dropna(subset=["Mobiliado"]).reset_index(drop=True)


def modelo(semente: int) -> GradientBoostingRegressor:
    return GradientBoostingRegressor(
        n_estimators=200, learning_rate=0.1, max_depth=5, random_state=semente
    )


def com_mobiliado(df: pd.DataFrame, X: pd.DataFrame, usar: bool) -> pd.DataFrame:
    return X.assign(Mobiliado=df["Mobiliado"].to_numpy()) if usar else X


def main() -> None:
    df = carregar()
    print(f"{len(df)} anúncios com comodidades; mobiliados: {df['Mobiliado'].mean():.1%}")
    ppm = df["Valor_Anuncio"] / df["Area_m2"]
    print("mediana R$/m²: mobiliado", round(ppm[df["Mobiliado"] == 1].median(), 1),
          "| não", round(ppm[df["Mobiliado"] == 0].median(), 1))  # fmt: skip

    tr, va = df[df["split"] == "treino"], df[df["split"] == "validacao"]
    X_tr = matriz(tr, None, False)
    X_va = matriz(va, list(X_tr.columns), False)
    linhas = {}
    for rotulo, usar in (("sem mobiliado", False), ("com mobiliado", True)):
        m = modelo(SEED).fit(com_mobiliado(tr, X_tr, usar), np.log(tr["Valor_Anuncio"]))
        pred = np.exp(m.predict(com_mobiliado(va, X_va, usar)))
        linhas[rotulo] = metricas(va["Valor_Anuncio"].to_numpy(), pred)
    print(f"\nvalidação (treino {len(tr)} | validação {len(va)})")
    print(pd.DataFrame(linhas).T.round(3).to_string())

    pool = df[df["split"] != "teste"].reset_index(drop=True)
    y = np.log(pool["Valor_Anuncio"].to_numpy())
    X = matriz(pool, None, False)
    cv = {}
    for rotulo, usar in (("sem mobiliado", False), ("com mobiliado", True)):
        Xu = com_mobiliado(pool, X, usar)
        r2 = []
        for semente in range(3):
            pred = np.zeros(len(pool))
            for a, b in GroupKFold(n_splits=5).split(Xu, y, pool["ID_Grupo"]):
                pred[b] = modelo(SEED + semente).fit(Xu.iloc[a], y[a]).predict(Xu.iloc[b])
            r2.append(1 - np.sum((y - pred) ** 2) / np.sum((y - y.mean()) ** 2))
        cv[rotulo] = {"R2_log (CV agrupada)": float(np.mean(r2))}
    print(f"\nvalidação cruzada agrupada, treino+validação (n={len(pool)})")
    print(pd.DataFrame(cv).T.round(3).to_string())


if __name__ == "__main__":
    main()
