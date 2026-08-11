"""Vale trocar a fonte de treino da OLX para o Rocha & Rocha?

O dataset da OLX tem volume (4.597 anúncios únicos) mas features pobres: não
tem Tipo_Imovel, e as distâncias a POI medem distância a um ponto fixo por
categoria. O Rocha tem tudo o que falta — Tipo_Imovel, POIs reais do OSM com
contagem por raio, renda por setor censitário do IBGE — mas só 537 vendas
depois da limpeza.

Resposta medida em 2026-08-11: **não vale**. R² de teste cai de 0,74 para 0,33,
e ligar a renda do IBGE piora ainda mais (0,27). Com n=429 no treino e 130
features, o modelo memoriza (R² 0,99 no treino).

Ver docs/investigacao-geografica.md, seção "Teste direto: treinar no Rocha".

Uso: uv run python -m ml.experiments.comparar_fontes
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler

SEED = 42
PRECO_MIN = 50_000.0


def metricas(y, pred, nome):
    mae = mean_absolute_error(y, pred)
    r2 = r2_score(y, pred)
    mdape = np.median(np.abs((y - pred) / y)) * 100
    print(f"  {nome:24s} MAE R$ {mae:>10,.0f} | R² {r2:6.4f} | MdAPE {mdape:5.1f}%")
    return mae, r2, mdape


def treina(X, y, grupos, rotulo):
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED)
    tr, te = next(gss.split(X, y, groups=grupos))

    scaler = StandardScaler().fit(X.iloc[tr])
    Xtr, Xte = scaler.transform(X.iloc[tr]), scaler.transform(X.iloc[te])

    m = GradientBoostingRegressor(
        n_estimators=200, learning_rate=0.1, max_depth=5, random_state=SEED
    ).fit(Xtr, y.iloc[tr])

    print(f"\n{rotulo}  (treino {len(tr)} | teste {len(te)} | {X.shape[1]} features)")
    metricas(y.iloc[tr], m.predict(Xtr), "treino")
    r = metricas(y.iloc[te], m.predict(Xte), "TESTE")
    return m, r


# ---------------------------------------------------------------- OLX (atual)
olx = pd.read_csv("data/dataset_treino_olx_final.csv")
olx = olx[olx["Valor_Anuncio"] >= PRECO_MIN]
olx = olx.drop_duplicates(subset=["URL_Anuncio"]).reset_index(drop=True)
grupos_olx = olx["URL_Anuncio"]
y_olx = olx["Valor_Anuncio"]
X_olx = olx.drop(
    columns=["Valor_Anuncio", "URL_Anuncio", "Data_Coleta", "FipeZap_Diferenca_m2"]
).select_dtypes(include=[np.number, "bool"])
X_olx = X_olx.loc[:, X_olx.std() > 0]
treina(X_olx, y_olx, grupos_olx, "=== A) OLX — o modelo publicado hoje ===")

# -------------------------------------------------------------- Rocha (venda)
ro = pd.read_csv("data/enriched_rocha_full.csv")
print(f"\nRocha bruto: {len(ro)} anúncios")
ro = ro[ro["Tipo_Negocio"].str.lower().isin({"comprar", "venda", "vender"})]
print(f"  após filtro de venda: {len(ro)}")
ro = ro[ro["Valor_Anuncio"].notna() & (ro["Valor_Anuncio"] >= PRECO_MIN)]
ro = ro[ro["Area_m2"].notna() & (ro["Area_m2"] > 0)]
ro = ro.drop_duplicates(subset=["URL_Anuncio"]).reset_index(drop=True)
print(f"  após limpeza: {len(ro)}  | bairros: {ro['Bairro'].nunique()}")

y_ro = ro["Valor_Anuncio"]
grupos_ro = ro["URL_Anuncio"]

base = ["Area_m2", "Quartos", "Banheiros", "Suites", "Vagas_Garagem", "Latitude", "Longitude"]
pois = [c for c in ro.columns if c.startswith("poi_")]
ibge = ["populacao_setor", "densidade_populacional", "media_moradores", "renda_media_responsavel"]


def monta(cols, com_ohe=True):
    X = ro[[c for c in cols if c in ro.columns]].copy()
    for c in X.columns:
        X[c] = pd.to_numeric(X[c], errors="coerce")
    X = X.fillna(X.median(numeric_only=True))
    if com_ohe:
        X = pd.concat(
            [
                X,
                pd.get_dummies(ro["Bairro"], prefix="Bairro", drop_first=True),
                pd.get_dummies(ro["Tipo_Imovel"], prefix="Tipo", drop_first=True),
            ],
            axis=1,
        )
    X = X.loc[:, X.std() > 0]
    return X


treina(monta(base), y_ro, grupos_ro, "=== B) Rocha — base + bairro + TIPO ===")
treina(monta(base + pois), y_ro, grupos_ro, "=== C) B + POIs reais (OSM) ===")
treina(monta(base + pois + ibge), y_ro, grupos_ro, "=== D) C + renda IBGE por setor ===")
