"""A renda do bairro (Censo 2022) melhora o modelo além do próprio bairro?

Junta `renda_media_responsavel` (V06004) e a densidade (pessoas/km²) por nome de bairro, sem
acento nem caixa. Anúncios cujo bairro não casa ficam com NaN e entram com indicador. Treina em
`treino` e mede em `validacao` (teste fechado); repete em validação cruzada agrupada porque a
validação de aluguel é pequena. O ganho esperado é nos bairros com poucos anúncios.

Uso: uv run python -m ml.experiments.renda_ibge
"""

from __future__ import annotations

import unicodedata

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import GroupKFold

from config.paths import DATA_ROOT
from ml.experiments.baseline_atributos import carregar, matriz, metricas

SEED = 42
COD_TERESINA = "2211001"
IBGE = DATA_ROOT / "ibge"

# Grafias dos portais que o IBGE escreve de outro jeito (conferidas pelo nome, não por mapa).
ALIAS_BAIRRO = {
    "parque piaui": "parque do piaui",
    "marques": "marques de paranagua",
    "porenquanto": "por enquanto",
    "nossa senhora das gracas": "n.s.das gracas",
}


def _chave(nome: object) -> str:
    texto = unicodedata.normalize("NFKD", str(nome)).encode("ascii", "ignore").decode()
    chave = " ".join(texto.lower().split())
    return ALIAS_BAIRRO.get(chave, chave)


def bairros_ibge() -> pd.DataFrame:
    renda = pd.read_csv(IBGE / "Agregados_por_bairros_renda_responsavel_BR.csv", sep=";",
                        encoding="latin1", dtype=str)  # fmt: skip
    basico = pd.read_csv(IBGE / "Agregados_por_bairros_basico_BR.csv", sep=";",
                         encoding="latin1", dtype=str)  # fmt: skip
    renda = renda[renda["CD_BAIRRO"].str.startswith(COD_TERESINA, na=False)]
    basico = basico[basico["CD_BAIRRO"].str.startswith(COD_TERESINA, na=False)]
    df = renda[["CD_BAIRRO", "NM_BAIRRO", "V06004"]].merge(
        basico[["CD_BAIRRO", "AREA_KM2", "v0001"]], on="CD_BAIRRO"
    )
    df["Renda_bairro"] = pd.to_numeric(df["V06004"].str.replace(",", "."), errors="coerce")
    km2 = pd.to_numeric(df["AREA_KM2"].str.replace(",", "."), errors="coerce")
    df["Densidade_bairro"] = pd.to_numeric(df["v0001"], errors="coerce") / km2
    df["_chave"] = df["NM_BAIRRO"].map(
        lambda n: _chave(n).replace("n.s.das gracas", "n.s.das gracas")
    )
    return df.drop_duplicates("_chave")[["_chave", "Renda_bairro", "Densidade_bairro"]]


def com_ibge(df: pd.DataFrame) -> pd.DataFrame:
    chave = df["Bairro"].map(_chave).rename("_chave")
    ib = bairros_ibge().set_index("_chave")
    return df.assign(
        Renda_bairro=chave.map(ib["Renda_bairro"]).to_numpy(),
        Densidade_bairro=chave.map(ib["Densidade_bairro"]).to_numpy(),
    )


def X_com(df: pd.DataFrame, colunas: list[str] | None, usar: bool) -> pd.DataFrame:
    X = matriz(df, colunas, False)
    if usar:
        X = X.assign(
            Renda_bairro=df["Renda_bairro"].fillna(-1).to_numpy(),
            Densidade_bairro=df["Densidade_bairro"].fillna(-1).to_numpy(),
            IBGE_casou=df["Renda_bairro"].notna().astype(int).to_numpy(),
        )
    return X


def modelo(semente: int = SEED) -> GradientBoostingRegressor:
    return GradientBoostingRegressor(
        n_estimators=200, learning_rate=0.1, max_depth=5, random_state=semente
    )


def main() -> None:
    for negocio in ("venda", "aluguel"):
        df = com_ibge(carregar(negocio))
        casou = df["Renda_bairro"].notna()
        print(f"\n== {negocio}: {len(df)} anúncios | bairro casou com o IBGE em {casou.mean():.1%}")
        nao = df.loc[~casou, "Bairro"].value_counts().head(8)
        print("bairros sem correspondência (anúncios):", nao.to_dict())
        ppm = (df["Valor_Anuncio"] / df["Area_m2"])[casou]
        print(f"corr(renda do bairro, R$/m²) = {np.corrcoef(df.loc[casou,'Renda_bairro'], ppm)[0,1]:.2f}")  # fmt: skip

        tr, va = df[df["split"] == "treino"], df[df["split"] == "validacao"]
        linhas = {}
        for rotulo, usar in (("sem IBGE", False), ("com renda+densidade", True)):
            X_tr = X_com(tr, None, usar)
            m = modelo().fit(X_tr, np.log(tr["Valor_Anuncio"]))
            pred = np.exp(m.predict(X_com(va, list(X_tr.columns), usar)))
            linhas[rotulo] = metricas(va["Valor_Anuncio"].to_numpy(), pred)
        print(f"validação (treino {len(tr)} | validação {len(va)})")
        print(pd.DataFrame(linhas).T.round(3).to_string())

        pool = df[df["split"] != "teste"].reset_index(drop=True)
        y = np.log(pool["Valor_Anuncio"].to_numpy())
        cont = pool["Bairro"].map(pool["Bairro"].value_counts())
        raro = (cont < 15).to_numpy()
        cv: dict[str, dict[str, float]] = {}
        for rotulo, usar in (("sem IBGE", False), ("com renda+densidade", True)):
            Xu = X_com(pool, None, usar)
            r2, r2_raro = [], []
            for s in range(3):
                pred = np.zeros(len(pool))
                for a, b in GroupKFold(n_splits=5).split(Xu, y, pool["ID_Grupo"]):
                    pred[b] = modelo(SEED + s).fit(Xu.iloc[a], y[a]).predict(Xu.iloc[b])
                r2.append(1 - np.sum((y - pred) ** 2) / np.sum((y - y.mean()) ** 2))
                r = raro
                r2_raro.append(
                    1 - np.sum((y[r] - pred[r]) ** 2) / np.sum((y[r] - y[r].mean()) ** 2)
                )
            cv[rotulo] = {"R2_log": float(np.mean(r2)), f"R2_log bairros <15 (n={raro.sum()})": float(np.mean(r2_raro))}  # fmt: skip
        print(f"CV agrupada (n={len(pool)})")
        print(pd.DataFrame(cv).T.round(3).to_string())


if __name__ == "__main__":
    main()
