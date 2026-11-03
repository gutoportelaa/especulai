"""Treino final por negócio: atributos + tipo + bairro + renda/densidade, intervalo por faixa.

Duas fases, para proteger o teste:
  desenvolvimento  treina em `treino`, calibra o intervalo e mede em `validacao`;
  final            reajusta em treino+validação e lê o `teste` uma única vez (`--abrir-teste`).

O intervalo é conformal em log: a meia-largura de cada faixa de preço previsto é o quantil dos
|resíduos| fora da amostra (CV agrupada por `ID_Grupo`) dos anúncios cuja previsão caiu na faixa.
Uma largura global cobre o conjunto mas sub-cobre o terço caro.

O artefato leva também o `diagnostico` do site (previsto × pedido e viés por faixa de preço), feito
com as mesmas previsões fora da amostra da calibração: mostra o comportamento do modelo sem reabrir
o teste, e os agregados `por_bairro` do mapa do site. Com `--abrir-teste`, as métricas vão para `metricas_teste.json` junto com a impressão
digital do modelo medido; `export_web` recusa publicar métricas de outro modelo.

Uso: uv run python -m ml.pipeline.treino_final [--abrir-teste]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import GroupKFold

from config.paths import ARTIFACT_DIR
from ml.experiments.baseline_atributos import carregar, metricas
from ml.experiments.renda_ibge import X_com, _chave, com_ibge

SEED = 42
NIVEL = 0.8
FAIXAS = 3
METRICAS_TESTE = Path(__file__).with_name("metricas_teste.json")
# Imóveis distintos que um bairro precisa ter para ganhar número no mapa do site, e para ceder
# exemplos de anúncio (descritos, arredondados no export). Abaixo disso, só a contagem.
MIN_AGREGADO = 5
MIN_EXEMPLO = 15
EXEMPLOS_POR_BAIRRO = 2


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


def fora_da_amostra(X: pd.DataFrame, y_log: np.ndarray, grupos: pd.Series) -> np.ndarray:
    """Log-preço previsto por um modelo que não viu o anúncio nem o seu grupo (CV agrupada)."""
    oof = np.zeros(len(X))
    for a, b in GroupKFold(n_splits=5).split(X, y_log, grupos):
        oof[b] = novo_modelo().fit(X.iloc[a], y_log[a]).predict(X.iloc[b])
    return oof


def calibrar(y_log: np.ndarray, oof: np.ndarray) -> Intervalos:
    preco = np.exp(oof)
    cortes = [float(c) for c in np.quantile(preco, np.linspace(0, 1, FAIXAS + 1)[1:-1])]
    faixa = np.searchsorted(cortes, preco)
    res = np.abs(y_log - oof)
    largura = [float(np.quantile(res[faixa == k], NIVEL)) for k in range(FAIXAS)]
    return Intervalos(cortes, largura)


def diagnostico(y: np.ndarray, pred: np.ndarray) -> dict[str, list[dict[str, float]]]:
    """Agregados por faixa de preço pedido; nenhum anúncio individual sai daqui."""

    def faixas(n: int) -> list[np.ndarray]:
        cortes = np.quantile(y, np.linspace(0, 1, n + 1))
        idx = np.clip(np.searchsorted(cortes, y, side="right") - 1, 0, n - 1)
        return [idx == k for k in range(n)]

    calibracao = [
        {
            "pedido": float(np.median(y[m])),
            "previsto": float(np.median(pred[m])),
            "previsto_p10": float(np.quantile(pred[m], 0.1)),
            "previsto_p90": float(np.quantile(pred[m], 0.9)),
            "n": int(m.sum()),
        }
        for m in faixas(10)
    ]
    vies = [
        {
            "de": float(y[m].min()),
            "ate": float(y[m].max()),
            "vies": float(np.median(pred[m] / y[m] - 1)),
            "erro": float(np.median(np.abs(pred[m] / y[m] - 1))),
            "n": int(m.sum()),
        }
        for m in faixas(5)
    ]
    return {"calibracao": calibracao, "vies": vies}


def por_bairro(
    pool: pd.DataFrame, oof_log: np.ndarray, iv: Intervalos
) -> dict[str, dict[str, object]]:
    """Agregados fora da amostra por bairro (chave do IBGE, sem acento nem caixa).

    Os exemplos são sorteados, não escolhidos: entram anúncios que a faixa erra, na proporção em
    que ela erra. Saem daqui com valores exatos; o export arredonda antes de publicar.
    """
    y = pool["Valor_Anuncio"].to_numpy()
    pred = np.exp(oof_log)
    lo, hi = iv.limites(pred)
    df = pool.assign(
        _chave=pool["Bairro"].map(_chave),
        _pred=pred,
        _lo=lo,
        _hi=hi,
        _razao=pred / y - 1,
        _m2=y / pool["Area_m2"].to_numpy(),
        _dentro=(y >= lo) & (y <= hi),
    )
    saida: dict[str, dict[str, object]] = {}
    for chave, g in df.groupby("_chave", sort=True):
        imoveis = int(g["ID_Grupo"].nunique())
        item: dict[str, object] = {"anuncios": len(g), "imoveis": imoveis}
        if imoveis >= MIN_AGREGADO:
            item |= {
                "m2": float(g["_m2"].median()),
                "erro": float(g["_razao"].abs().median()),
                "vies": float(g["_razao"].median()),
                "cobertura": float(g["_dentro"].mean()),
            }
        if imoveis >= MIN_EXEMPLO:
            sorteio = g.drop_duplicates("ID_Grupo").sample(EXEMPLOS_POR_BAIRRO, random_state=SEED)
            item["exemplos"] = [
                {
                    "tipo": str(r["Tipo_Imovel"]),
                    "area": float(r["Area_m2"]),
                    "quartos": None if pd.isna(r["Quartos"]) else int(r["Quartos"]),
                    "pedido": float(r["Valor_Anuncio"]),
                    "previsto": float(r["_pred"]),
                    "minimo": float(r["_lo"]),
                    "maximo": float(r["_hi"]),
                }
                for _, r in sorteio.iterrows()
            ]
        saida[str(chave)] = item
    return saida


def impressao(modelo: GradientBoostingRegressor, colunas: list[str]) -> str:
    """Identifica o modelo treinado: muda se mudar uma coluna, um corte ou uma folha."""
    h = hashlib.sha256(json.dumps(colunas).encode())
    for arvore in modelo.estimators_[:, 0]:
        h.update(arvore.tree_.threshold.tobytes())
        h.update(arvore.tree_.value.tobytes())
    return h.hexdigest()[:16]


def avaliar(
    modelo: GradientBoostingRegressor, iv: Intervalos, X: pd.DataFrame, y: np.ndarray
) -> dict[str, object]:
    pred = np.exp(modelo.predict(X))
    lo, hi = iv.limites(pred)
    dentro = (y >= lo) & (y <= hi)
    por_faixa = pd.Series(dentro).groupby(iv.faixa(pred)).mean()
    return {
        "n_teste": len(y),
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
    iv = calibrar(y_tr, fora_da_amostra(X_tr, y_tr, tr["ID_Grupo"]))
    m = novo_modelo().fit(X_tr, y_tr)
    X_va = X_com(va, list(X_tr.columns), True)
    saida["desenvolvimento"] = avaliar(m, iv, X_va, va["Valor_Anuncio"].to_numpy())

    pool = pd.concat([tr, va], ignore_index=True)
    X_pool = X_com(pool, None, True)
    y_pool = np.log(pool["Valor_Anuncio"].to_numpy())
    oof_pool = fora_da_amostra(X_pool, y_pool, pool["ID_Grupo"])
    iv_final = calibrar(y_pool, oof_pool)
    modelo_final = novo_modelo().fit(X_pool, y_pool)
    saida["modelo"] = impressao(modelo_final, list(X_pool.columns))
    if abrir_teste:
        X_te = X_com(te, list(X_pool.columns), True)
        saida["teste"] = {
            **avaliar(modelo_final, iv_final, X_te, te["Valor_Anuncio"].to_numpy()),
            "modelo": saida["modelo"],
        }

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": modelo_final,
            "columns": list(X_pool.columns),
            "intervalos": iv_final.__dict__,
            "contagem_bairro": {str(k): int(v) for k, v in pool["Bairro"].value_counts().items()},
            "diagnostico": diagnostico(np.exp(y_pool), np.exp(oof_pool)),
            "por_bairro": por_bairro(pool, oof_pool, iv_final),
            "corpus": {
                "anuncios": len(df),
                "imoveis": int(df["ID_Grupo"].nunique()),
                "ligados_ibge": float(df["Renda_bairro"].notna().mean()),
                "mediana_pedido": float(pool["Valor_Anuncio"].median()),
            },
            "impressao": saida["modelo"],
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
    if args.abrir_teste:
        teste = {n: r["teste"] for n, r in resultado.items()}
        METRICAS_TESTE.write_text(json.dumps(teste, indent=2, ensure_ascii=False) + "\n", "utf-8")
        print(f"[OK] {METRICAS_TESTE.name} gravado. Não abra o teste de novo para este split.")


if __name__ == "__main__":
    main()
