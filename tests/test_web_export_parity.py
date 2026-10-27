"""Paridade entre o treino em Python e a inferência que roda no navegador.

1. sklearn -> árvores exportadas: percorrer o JSON tem que devolver o mesmo log-preço que
   `model.predict`, para o vetor montado pelo código de treino (`matriz` + `X_com`).
2. Treino -> servidor de inferência: este teste congela entrada, vetor e log-preço em
   `tests/fixtures/parity.json`; `test_space_inferencia.py` compara a reimplementação sem sklearn
   (`deploy/space/inferencia.py`) contra esse arquivo.
"""

from __future__ import annotations

import json
import unicodedata

import joblib
import numpy as np
import pandas as pd
import pytest

from config.paths import ARTIFACT_DIR, PROJECT_ROOT
from ml.experiments.renda_ibge import X_com, com_ibge
from ml.pipeline.export_web import NEGOCIOS, WEB_MODEL_DIR

FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "parity.json"

CASOS = [
    {"area": 90, "quartos": 3, "banheiros": 2, "tipo": "Apartamento", "bairro": "Fátima"},
    {"area": 200, "quartos": 4, "banheiros": 3, "tipo": "Casa", "bairro": "Centro"},
    {
        "area": 45,
        "quartos": 1,
        "banheiros": 1,
        "tipo": "Apartamento",
        "bairro": "Jóquei",
        "vagas": 1,
    },
    {"area": 350, "quartos": 5, "banheiros": 4, "tipo": "Casa de Condomínio", "bairro": "Ininga"},
    {
        "area": 60,
        "quartos": 2,
        "banheiros": 1,
        "tipo": "apartamento",
        "bairro": "fatima",
        "vagas": 0,
    },
    {"area": 120, "quartos": 3, "banheiros": 2, "tipo": "Casa", "bairro": "Bairro Inexistente"},
    {"area": 15, "quartos": 0, "banheiros": 1, "tipo": "Kitnet", "bairro": "Centro"},
    {"area": 1200, "quartos": 6, "banheiros": 5, "tipo": "Sobrado", "bairro": "Ininga", "vagas": 4},
]

pytestmark = pytest.mark.skipif(
    not all((ARTIFACT_DIR / f"final_{n}.joblib").exists() for n in NEGOCIOS)
    or not all((WEB_MODEL_DIR / f"especulai-{n}.json").exists() for n in NEGOCIOS),
    reason="modelos finais não treinados/exportados — rode `make export-web`",
)


def _chave(valor: str) -> str:
    texto = unicodedata.normalize("NFKD", valor).encode("ascii", "ignore").decode()
    return "".join(c for c in texto.lower() if c.isalnum())


def _canonico(valor: str, colunas: list[str], prefixo: str) -> str | None:
    for col in colunas:
        if col.startswith(prefixo) and _chave(col[len(prefixo) :]) == _chave(valor):
            return col[len(prefixo) :]
    return None


def vetor_de_treino(caso: dict, colunas: list[str]) -> list[float]:
    """Vetor montado pelo código de treino, com o bairro/tipo no nome canônico do corpus."""
    bairro = _canonico(caso["bairro"], colunas, "Bairro_") or caso["bairro"]
    tipo = _canonico(caso["tipo"], colunas, "Tipo_Imovel_") or caso["tipo"]
    vagas = caso.get("vagas")
    df = com_ibge(
        pd.DataFrame(
            [
                {
                    "Area_m2": max(float(caso["area"]), 1.0),
                    "Quartos": caso["quartos"],
                    "Banheiros": caso["banheiros"],
                    "Vagas_Garagem": np.nan if vagas is None else vagas,
                    "Tipo_Imovel": tipo,
                    "Bairro": bairro,
                }
            ]
        )
    )
    return [float(v) for v in X_com(df, colunas, True).iloc[0]]


def predizer_json(vetor: list[float], modelo: dict) -> float:
    """Mesma travessia do model.js; float32 espelha Math.fround e o cast do sklearn."""
    x = [float(np.float32(v)) for v in vetor]
    t = modelo["trees"]
    soma = 0.0
    for raiz in t["roots"]:
        no = raiz
        while t["feature"][no] != -1:
            no = t["left"][no] if x[t["feature"][no]] <= t["threshold"][no] else t["right"][no]
        soma += t["value"][no]
    return modelo["init"] + modelo["learning_rate"] * soma


@pytest.fixture(scope="module", params=NEGOCIOS)
def par(request):
    artefato = joblib.load(ARTIFACT_DIR / f"final_{request.param}.joblib")
    web = json.loads((WEB_MODEL_DIR / f"especulai-{request.param}.json").read_text("utf-8"))
    return request.param, artefato, web


@pytest.mark.parametrize("caso", CASOS, ids=lambda c: f"{c['bairro']}-{c['area']}m2")
def test_arvores_exportadas_batem_com_sklearn(par, caso):
    _, artefato, web = par
    vetor = vetor_de_treino(caso, artefato["columns"])
    esperado = float(
        artefato["model"].predict(pd.DataFrame([vetor], columns=artefato["columns"]))[0]
    )
    assert predizer_json(vetor, web) == pytest.approx(esperado, abs=1e-5)


def test_export_cobre_o_modelo_treinado(par):
    _, artefato, web = par
    assert web["feature_columns"] == artefato["columns"]
    assert len(web["trees"]["roots"]) == artefato["model"].n_estimators_
    esperado = sum(
        artefato["model"].estimators_[i, 0].tree_.node_count
        for i in range(artefato["model"].n_estimators_)
    )
    assert len(web["trees"]["left"]) == esperado


def test_folhas_e_nos_internos_sao_consistentes(par):
    t = par[2]["trees"]
    n = len(t["left"])
    for i, feature in enumerate(t["feature"]):
        if feature == -1:
            assert t["left"][i] == -1 and t["right"][i] == -1
        else:
            assert 0 <= t["left"][i] < n and 0 <= t["right"][i] < n


def test_amostra_aleatoria_ampla(par):
    _, artefato, web = par
    rng = np.random.default_rng(42)
    tipos = [c[len("Tipo_Imovel_") :] for c in artefato["columns"] if c.startswith("Tipo_")]
    for _ in range(200):
        caso = {
            "area": float(rng.uniform(20, 800)),
            "quartos": int(rng.integers(0, 7)),
            "banheiros": int(rng.integers(0, 6)),
            "tipo": str(rng.choice(tipos)),
            "bairro": str(rng.choice(web["bairros"])),
            "vagas": int(rng.integers(0, 4)) if rng.random() < 0.5 else None,
        }
        vetor = vetor_de_treino(caso, artefato["columns"])
        esperado = float(
            artefato["model"].predict(pd.DataFrame([vetor], columns=artefato["columns"]))[0]
        )
        assert predizer_json(vetor, web) == pytest.approx(esperado, abs=1e-5), caso


def test_intervalo_exportado_igual_ao_do_treino(par):
    _, artefato, web = par
    assert web["intervalo"]["cortes"] == artefato["intervalos"]["cortes"]
    assert web["intervalo"]["meia_largura"] == artefato["intervalos"]["meia_largura"]


def test_gera_fixtures_para_o_js():
    """Congela entrada -> vetor -> log-preço para o teste do bun comparar."""
    saida: dict[str, list[dict]] = {}
    for negocio in NEGOCIOS:
        artefato = joblib.load(ARTIFACT_DIR / f"final_{negocio}.joblib")
        casos = []
        for caso in CASOS:
            vetor = vetor_de_treino(caso, artefato["columns"])
            log_preco = float(
                artefato["model"].predict(pd.DataFrame([vetor], columns=artefato["columns"]))[0]
            )
            casos.append({"entrada": caso, "vetor": vetor, "log_preco": log_preco})
        saida[negocio] = casos
    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(json.dumps(saida, ensure_ascii=False, indent=2), "utf-8")
    assert all(len(v) == len(CASOS) for v in saida.values())
