"""Baseline sobre o corpus canônico: atributos + tipo + bairro, sem geografia.

Treina em `treino` e mede em `validacao`. O `teste` não é lido aqui: ele só deve ser aberto
uma vez, para o modelo que for reportado. Alvo em log(preço); métricas voltam à escala em R$.

Uso: uv run python -m ml.experiments.baseline_atributos
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor

from config.paths import DATA_ROOT

SEED = 42
BASE = ["Area_m2", "Quartos", "Banheiros", "Vagas_Garagem"]


def carregar(negocio: str) -> pd.DataFrame:
    canon = pd.read_csv(DATA_ROOT / "canonico.csv")
    split = pd.read_csv(DATA_ROOT / "splits" / f"{negocio}.csv")
    return canon.merge(split[["ID_Imovel", "split"]], on="ID_Imovel", suffixes=("_x", ""))


def matriz(df: pd.DataFrame, colunas: list[str] | None, com_condominio: bool) -> pd.DataFrame:
    X = df[BASE].copy()
    # VivaReal omite "sem vaga" (suposição: ausente = 0); o Chaves nunca informa vagas.
    X["Vagas_informado"] = X["Vagas_Garagem"].notna().astype(int)
    X["Vagas_Garagem"] = X["Vagas_Garagem"].fillna(0)
    X = X.fillna(X.median(numeric_only=True))
    if com_condominio:
        X["Condominio"] = df["Condominio"].fillna(-1)
        X["Condominio_informado"] = df["Condominio"].notna().astype(int)
    onehot = pd.get_dummies(df[["Tipo_Imovel", "Bairro"]], dtype=int)
    X = pd.concat([X, onehot], axis=1)
    return X if colunas is None else X.reindex(columns=colunas, fill_value=0)


def metricas(y: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    erro_rel = np.abs(pred - y) / y
    ss_res, ss_tot = np.sum((y - pred) ** 2), np.sum((y - y.mean()) ** 2)
    return {
        "R2": 1 - ss_res / ss_tot,
        "R2_log": 1
        - np.sum((np.log(y) - np.log(pred)) ** 2) / np.sum((np.log(y) - np.log(y).mean()) ** 2),
        "MdAPE%": 100 * float(np.median(erro_rel)),
        "dentro10%": 100 * float(np.mean(erro_rel <= 0.10)),
        "dentro20%": 100 * float(np.mean(erro_rel <= 0.20)),
    }


def main() -> None:
    for negocio in ("venda", "aluguel"):
        df = carregar(negocio)
        tr, va = df[df["split"] == "treino"], df[df["split"] == "validacao"]
        print(f"\n== {negocio}: treino {len(tr)} | validação {len(va)}")

        # referência: mediana de preço/m² do bairro (cai na global se o bairro for novo)
        ppm = (tr["Valor_Anuncio"] / tr["Area_m2"]).groupby(tr["Bairro"]).median()
        global_ppm = (tr["Valor_Anuncio"] / tr["Area_m2"]).median()
        ref = va["Area_m2"] * va["Bairro"].map(ppm).fillna(global_ppm)
        linhas = {
            "mediana R$/m² do bairro": metricas(va["Valor_Anuncio"].to_numpy(), ref.to_numpy())
        }

        for rotulo, cond in (("GBR atributos+tipo+bairro", False), ("  + condomínio", True)):
            X_tr = matriz(tr, None, cond)
            X_va = matriz(va, list(X_tr.columns), cond)
            modelo = GradientBoostingRegressor(
                n_estimators=200, learning_rate=0.1, max_depth=5, random_state=SEED
            )
            modelo.fit(X_tr, np.log(tr["Valor_Anuncio"]))
            pred = np.exp(modelo.predict(X_va))
            linhas[rotulo] = metricas(va["Valor_Anuncio"].to_numpy(), pred)

        print(pd.DataFrame(linhas).T.round(3).to_string())

        por_fonte = {
            fonte: metricas(
                g["Valor_Anuncio"].to_numpy(),
                np.exp(modelo.predict(matriz(g, list(X_tr.columns), cond))),
            )
            for fonte, g in va.groupby("Fonte")
        }
        print(f"  por fonte (último modelo, n por fonte: {va['Fonte'].value_counts().to_dict()})")
        print(pd.DataFrame(por_fonte).T.round(3).to_string())


if __name__ == "__main__":
    main()
