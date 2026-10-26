"""A localização em nível de rua do Chaves melhora o modelo além do bairro?

Usa só anúncios do Chaves com coordenada válida (sem o 0,0 de "não disponível") e descarta
os que ficam a mais de LIMITE_KM da mediana do bairro. Validação cruzada agrupada por
`ID_Grupo` sobre treino+validação; o teste não é lido.

Uso: uv run python -m ml.experiments.geografia_chaves
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import GroupKFold

from config.paths import DATA_ROOT
from ml.experiments.baseline_atributos import matriz

LIMITE_KM = 5.0
SEED = 42
COS_LAT = np.cos(np.radians(5.09))


def km(lat: pd.Series, lon: pd.Series, lat0: pd.Series, lon0: pd.Series) -> pd.Series:
    return 111.2 * np.hypot(lat - lat0, (lon - lon0) * COS_LAT)


def carregar(negocio: str) -> pd.DataFrame:
    canon = pd.read_csv(DATA_ROOT / "canonico.csv")
    split = pd.read_csv(DATA_ROOT / "splits" / f"{negocio}.csv")
    df = canon.merge(split[["ID_Imovel", "split"]], on="ID_Imovel", suffixes=("_x", ""))
    df = df[(df["Fonte"] == "chaves") & df["Latitude"].notna() & (df["split"] != "teste")]
    mediana = df.groupby("Bairro")[["Latitude", "Longitude"]].transform("median")
    dist = km(df["Latitude"], df["Longitude"], mediana["Latitude"], mediana["Longitude"])
    return df[dist <= LIMITE_KM].reset_index(drop=True)


def com_geo(df: pd.DataFrame, X: pd.DataFrame) -> pd.DataFrame:
    X = X.copy()
    X["Latitude"], X["Longitude"] = df["Latitude"], df["Longitude"]
    centro = (-5.0892, -42.8016)
    X["Dist_centro_km"] = km(df["Latitude"], df["Longitude"], centro[0], centro[1])
    return X


def avaliar(df: pd.DataFrame, geo: bool, semente: int) -> tuple[float, float]:
    y = np.log(df["Valor_Anuncio"].to_numpy())
    pred = np.zeros(len(df))
    X_all = matriz(df, None, False)
    if geo:
        X_all = com_geo(df, X_all)
    for tr, va in GroupKFold(n_splits=5).split(X_all, y, df["ID_Grupo"]):
        m = GradientBoostingRegressor(
            n_estimators=200, learning_rate=0.1, max_depth=5, random_state=semente
        )
        m.fit(X_all.iloc[tr], y[tr])
        pred[va] = m.predict(X_all.iloc[va])
    r2 = 1 - np.sum((y - pred) ** 2) / np.sum((y - y.mean()) ** 2)
    return float(r2), 100 * float(np.median(np.abs(np.exp(pred) / np.exp(y) - 1)))


def main() -> None:
    for negocio in ("venda", "aluguel"):
        df = carregar(negocio)
        print(f"\n== {negocio}: {len(df)} anúncios do Chaves, {df['ID_Grupo'].nunique()} grupos")
        linhas = {}
        for rotulo, geo in (("bairro", False), ("bairro + lat/lon + dist. centro", True)):
            r = np.array([avaliar(df, geo, SEED + s) for s in range(3)])
            linhas[rotulo] = {"R2_log": r[:, 0].mean(), "MdAPE%": r[:, 1].mean()}
        print(pd.DataFrame(linhas).T.round(3).to_string())


if __name__ == "__main__":
    main()
