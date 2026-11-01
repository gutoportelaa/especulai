"""Exporta os modelos finais (venda e aluguel) para JSON, para inferência no navegador.

Árvores cruas em vez de ONNX: o servidor de inferência fica sem sklearn nem runtime de ML,
só a soma das 200 árvores de ~9 mil nós.

O modelo prevê log(preço) sobre atributos crus (sem scaler):

    preco = exp(init + learning_rate * Σ_i folha_i(x))
    intervalo = preco × exp(∓ meia_largura[faixa(preco)])

Detalhe que não é opcional: as árvores do sklearn convertem `X` para float32 antes de comparar
com o threshold (float64). O consumidor tem que fazer `Math.fround(x) <= threshold`.
Thresholds não são arredondados; folhas (log-preço) vão com 6 casas, erro < 1e-6 relativo.

Saída em `ml/artifacts/web/especulai-{venda,aluguel}.json` (NÃO versionado e fora da pasta pública:
os pesos só chegam ao usuário cifrados, ver `cifrar_modelo.py` e `deploy/space/`). O site recebe
apenas `frontend/public/model/bairros.json`, com os nomes dos bairros para o autocomplete, e
`frontend/src/features/conteudo/metricas-modelo.json`, com o que a página Como Funciona mostra:
métricas do teste (de `metricas_teste.json`, aberto uma única vez, ver docs/relatorio-coleta.md §12),
diagnóstico fora da amostra, importância por grupo de atributos e um exemplo de faixa. Só agregados:
nenhum anúncio individual e nenhum peso do modelo. Do mesmo arquivo saem os gráficos e a tabela
de resultados do README (`graficos_readme.py`).
`tests/test_web_export_parity.py` trava a paridade com o sklearn.

Uso: uv run python -m ml.pipeline.export_web
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from config.paths import ARTIFACT_DIR, PROJECT_ROOT
from ml.experiments.renda_ibge import com_ibge
from ml.pipeline import graficos_readme

WEB_MODEL_DIR = ARTIFACT_DIR / "web"
SITE_MODEL_DIR = PROJECT_ROOT / "frontend" / "public" / "model"
SITE_METRICAS = graficos_readme.SITE_METRICAS
METRICAS_TESTE = Path(__file__).with_name("metricas_teste.json")
NEGOCIOS = ("venda", "aluguel")
CASAS_FOLHA = 6


def _flatten_trees(model: Any) -> dict[str, list[float | int]]:
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
            folha = tree.children_left[node] == -1
            left.append(-1 if folha else int(tree.children_left[node]) + offset)
            right.append(-1 if folha else int(tree.children_right[node]) + offset)
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


def _bairros(colunas: list[str], contagem: dict[str, int]) -> dict[str, dict[str, float]]:
    nomes = sorted(c[len("Bairro_") :] for c in colunas if c.startswith("Bairro_"))
    ibge = com_ibge(pd.DataFrame({"Bairro": nomes}))
    info: dict[str, dict[str, float]] = {}
    for nome, renda, dens in zip(
        nomes, ibge["Renda_bairro"], ibge["Densidade_bairro"], strict=True
    ):
        achou = bool(pd.notna(renda))
        info[nome] = {
            "renda": float(renda) if achou else -1.0,
            "densidade": float(dens) if achou else -1.0,
            "casou": 1.0 if achou else 0.0,
            "n": float(contagem.get(nome, 0)),
        }
    return info


# Uma coluna nova sem grupo aqui quebra o export de propósito: o site não pode omitir um atributo.
GRUPOS_ATRIBUTO = {
    "Area_m2": "Área",
    "Quartos": "Quartos",
    "Banheiros": "Banheiros",
    "Vagas_Garagem": "Vagas",
    "Vagas_informado": "Vagas",
    "Renda_bairro": "Renda do bairro (IBGE)",
    "Densidade_bairro": "Densidade do bairro (IBGE)",
    "IBGE_casou": "Bairro",
}
PREFIXOS_ATRIBUTO = {"Bairro_": "Bairro", "Tipo_Imovel_": "Tipo do imóvel"}


def _grupo(coluna: str) -> str:
    if coluna in GRUPOS_ATRIBUTO:
        return GRUPOS_ATRIBUTO[coluna]
    for prefixo, grupo in PREFIXOS_ATRIBUTO.items():
        if coluna.startswith(prefixo):
            return grupo
    raise KeyError(f"coluna sem grupo para o site: {coluna!r} (ver GRUPOS_ATRIBUTO)")


def _arredondar(valor: float) -> int:
    """Mesmo arredondamento da API (deploy/worker/src/inferencia.js)."""
    passo = 1000 if valor >= 10_000 else 10
    return int(round(valor / passo) * passo)


def metricas_site(negocio: str, artefato: dict[str, Any], teste: dict[str, Any]) -> dict[str, Any]:
    if teste.get("modelo") != artefato["impressao"]:
        raise ValueError(
            f"{negocio}: metricas_teste.json mede o modelo {teste.get('modelo')}, mas o artefato é "
            f"{artefato['impressao']}. Abra o teste do modelo novo (treino_final --abrir-teste) "
            "antes de publicar."
        )
    importancia: dict[str, float] = {}
    for coluna, peso in zip(
        artefato["columns"], artefato["model"].feature_importances_, strict=True
    ):
        importancia[_grupo(coluna)] = importancia.get(_grupo(coluna), 0.0) + float(peso)

    iv = artefato["intervalos"]
    central = artefato["corpus"]["mediana_pedido"]
    w = iv["meia_largura"][int(np.searchsorted(iv["cortes"], central))]
    diag = artefato["diagnostico"]
    return {
        "modelo": artefato["impressao"],
        "corpus": {
            "anuncios": artefato["corpus"]["anuncios"],
            "imoveis": artefato["corpus"]["imoveis"],
            "ligados_ibge": round(artefato["corpus"]["ligados_ibge"], 3),
        },
        "teste": {k: v for k, v in teste.items() if k != "modelo"},
        "exemplo_faixa": {
            "central": _arredondar(central),
            "minimo": _arredondar(central * np.exp(-w)),
            "maximo": _arredondar(central * np.exp(w)),
        },
        "importancia": [
            {"atributo": k, "peso": round(v, 4)}
            for k, v in sorted(importancia.items(), key=lambda kv: -kv[1])
        ],
        "calibracao": [
            {k: (v if k == "n" else int(round(v))) for k, v in faixa.items()}
            for faixa in diag["calibracao"]
        ],
        "vies": [
            {k: (round(v, 3) if k in ("vies", "erro") else int(round(v))) for k, v in faixa.items()}
            for faixa in diag["vies"]
        ],
    }


def exportar(negocio: str, out_dir: Path | None = None) -> Path:
    out_dir = out_dir or WEB_MODEL_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    artefato = joblib.load(ARTIFACT_DIR / f"final_{negocio}.joblib")
    model, colunas = artefato["model"], list(artefato["columns"])
    init = float(model._raw_predict_init(np.zeros((1, len(colunas)))).ravel()[0])
    bairros = _bairros(colunas, artefato["contagem_bairro"])

    payload = {
        "negocio": negocio,
        "feature_columns": colunas,
        "bairros": list(bairros),
        "bairro_info": bairros,
        "init": init,
        "learning_rate": float(model.learning_rate),
        "trees": _flatten_trees(model),
        "intervalo": {"nivel": 0.8, **artefato["intervalos"]},
        "metricas_teste": json.loads(METRICAS_TESTE.read_text("utf-8"))[negocio],
    }
    caminho = out_dir / f"especulai-{negocio}.json"
    caminho.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), "utf-8")
    kb = caminho.stat().st_size / 1024
    print(f"[OK] {caminho.name}: {kb:.0f} KB, {len(colunas)} features, {len(bairros)} bairros")
    return caminho


def gerar_metricas_site() -> dict[str, Any]:
    teste = json.loads(METRICAS_TESTE.read_text("utf-8"))
    return {
        n: metricas_site(n, joblib.load(ARTIFACT_DIR / f"final_{n}.joblib"), teste[n])
        for n in NEGOCIOS
    }


def export() -> list[Path]:
    caminhos = [exportar(n) for n in NEGOCIOS]
    SITE_METRICAS.write_text(
        json.dumps(gerar_metricas_site(), ensure_ascii=False, indent=2) + "\n", "utf-8"
    )
    print(f"[OK] {SITE_METRICAS.relative_to(PROJECT_ROOT)}")
    graficos_readme.main(SITE_METRICAS)
    bairros = {
        n: json.loads(c.read_text("utf-8"))["bairros"]
        for n, c in zip(NEGOCIOS, caminhos, strict=True)
    }
    SITE_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    (SITE_MODEL_DIR / "bairros.json").write_text(
        json.dumps(bairros, ensure_ascii=False, separators=(",", ":")), "utf-8"
    )
    return caminhos


if __name__ == "__main__":
    export()
