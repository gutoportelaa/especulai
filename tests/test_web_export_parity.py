"""Paridade entre a inferência em Python e a que roda no navegador.

Duas fronteiras podem divergir, e ambas são cobertas aqui:

1. sklearn -> árvores exportadas: percorrer as árvores do JSON tem que devolver
   o mesmo preço que `model.predict`. Se `export_web.py` achatar as árvores
   errado, ou arredondar demais, quebra aqui.
2. Python -> JS: o vetor de 121 features e o preço final que o JS produz têm que
   bater com os do `ModelService`. Este teste congela casos de referência em
   `frontend/src/features/prediction/__fixtures__/parity.json`; o teste do bun
   (features.test.js) compara contra esse arquivo.
"""

from __future__ import annotations

import json

import joblib
import numpy as np
import pytest

from apps.api.services.model_service import ModelService
from config.paths import ARTIFACT_DIR, PROJECT_ROOT

WEB_MODEL_PATH = PROJECT_ROOT / "frontend" / "public" / "model" / "especulai.json"
FIXTURE_PATH = (
    PROJECT_ROOT / "frontend" / "src" / "features" / "prediction" / "__fixtures__" / "parity.json"
)

CASOS = [
    {"area": 90, "quartos": 3, "banheiros": 2, "tipo": "apartamento", "bairro": "Fátima"},
    {"area": 200, "quartos": 4, "banheiros": 3, "tipo": "casa", "bairro": "Centro"},
    {"area": 45, "quartos": 1, "banheiros": 1, "tipo": "apartamento", "bairro": "Jóquei"},
    {"area": 350, "quartos": 5, "banheiros": 4, "tipo": "casa", "bairro": "Ininga"},
    {"area": 60, "quartos": 2, "banheiros": 1, "tipo": "apartamento", "bairro": "fatima"},
    {"area": 120, "quartos": 3, "banheiros": 2, "tipo": "casa", "bairro": "Bairro Inexistente"},
    {"area": 15, "quartos": 0, "banheiros": 1, "tipo": "apartamento", "bairro": "Centro"},
    {"area": 1200, "quartos": 6, "banheiros": 5, "tipo": "casa", "bairro": "Ininga"},
]

pytestmark = pytest.mark.skipif(
    not (ARTIFACT_DIR / "modelo_definitivo.joblib").exists(),
    reason="modelo não treinado neste ambiente",
)


@pytest.fixture(scope="module")
def service() -> ModelService:
    svc = ModelService()
    svc.load()
    assert svc.is_ready(), "modelo não carregou"
    return svc


@pytest.fixture(scope="module")
def web_model() -> dict:
    if not WEB_MODEL_PATH.exists():
        pytest.skip("modelo web não exportado — rode `make export-web`")
    return json.loads(WEB_MODEL_PATH.read_text("utf-8"))


def _vetor(service: ModelService, caso: dict) -> list[float]:
    """Reproduz a montagem de `_predict_standard` sem tocar no privado dele."""
    pre = service.preprocessor
    defaults = pre.get("feature_defaults") or {}
    profiles = pre.get("bairro_profiles") or {}

    area = max(float(caso["area"]), 1.0)
    quartos = int(caso["quartos"])
    banheiros = int(caso["banheiros"])

    nome, col_ohe = service._resolve_bairro(caso["bairro"])
    perfil = profiles.get(nome, {}) if nome else {}

    informado = {
        "Area_m2": area,
        "Quartos": float(quartos),
        "Banheiros": float(banheiros),
        "densidade_comodos": (quartos + banheiros) / area,
    }

    vetor = []
    for col in service.feature_columns:
        if col in informado:
            vetor.append(float(informado[col]))
        elif col.startswith("Bairro_"):
            vetor.append(1.0 if col == col_ohe else 0.0)
        elif col in perfil:
            vetor.append(float(perfil[col]))
        else:
            vetor.append(float(defaults.get(col, 0.0)))
    return vetor


def _predict_web(vetor: list[float], modelo: dict) -> float:
    """Mesmo algoritmo do model.js — se este divergir, o JS também diverge."""
    mean = modelo["scaler"]["mean"]
    scale = modelo["scaler"]["scale"]
    # float32 espelha o Math.fround do JS, que por sua vez espelha o cast que a
    # árvore do sklearn faz em X antes de comparar com o threshold.
    x = [float(np.float32((v - mean[i]) / scale[i])) for i, v in enumerate(vetor)]

    t = modelo["trees"]
    soma = 0.0
    for raiz in t["roots"]:
        no = raiz
        while t["feature"][no] != -1:
            no = t["left"][no] if x[t["feature"][no]] <= t["threshold"][no] else t["right"][no]
        soma += t["value"][no]

    return modelo["init"] + modelo["learning_rate"] * soma


@pytest.mark.parametrize("caso", CASOS, ids=lambda c: f"{c['bairro']}-{c['area']}m2")
def test_arvores_exportadas_batem_com_sklearn(service, web_model, caso):
    esperado = service.predict({**caso, "cidade": "Teresina"})["preco_estimado"]
    obtido = _predict_web(_vetor(service, caso), web_model)

    # Thresholds vão em precisão cheia; só as folhas são arredondadas (4 casas).
    assert obtido == pytest.approx(esperado, rel=1e-6), (
        f"{caso['bairro']}: sklearn={esperado:.2f} web={obtido:.2f}"
    )


def test_export_cobre_o_modelo_treinado(service, web_model):
    assert web_model["feature_columns"] == list(service.feature_columns)
    assert len(web_model["bairros"]) == sum(
        1 for c in service.feature_columns if c.startswith("Bairro_")
    )
    assert len(web_model["scaler"]["mean"]) == len(service.feature_columns)


def test_todas_as_arvores_foram_exportadas(web_model):
    modelo = joblib.load(ARTIFACT_DIR / "modelo_definitivo.joblib")["model"]
    assert len(web_model["trees"]["roots"]) == modelo.n_estimators_
    esperado = sum(modelo.estimators_[i, 0].tree_.node_count for i in range(modelo.n_estimators_))
    assert len(web_model["trees"]["left"]) == esperado


def test_folhas_e_nos_internos_sao_consistentes(web_model):
    t = web_model["trees"]
    for i, feature in enumerate(t["feature"]):
        if feature == -1:
            assert t["left"][i] == -1 and t["right"][i] == -1, f"folha {i} com filhos"
        else:
            assert 0 <= t["left"][i] < len(t["left"]), f"nó {i} com filho esquerdo inválido"
            assert 0 <= t["right"][i] < len(t["left"]), f"nó {i} com filho direito inválido"


def test_amostra_aleatoria_ampla(service, web_model):
    """Os 8 casos fixos podem não tocar todos os ramos; 300 aleatórios tocam mais."""
    rng = np.random.default_rng(42)
    bairros = web_model["bairros"]

    for _ in range(300):
        caso = {
            "area": float(rng.uniform(20, 800)),
            "quartos": int(rng.integers(0, 7)),
            "banheiros": int(rng.integers(0, 6)),
            "tipo": str(rng.choice(["apartamento", "casa"])),
            "bairro": str(rng.choice(bairros)),
        }
        esperado = service.predict({**caso, "cidade": "Teresina"})["preco_estimado"]
        obtido = _predict_web(_vetor(service, caso), web_model)
        assert obtido == pytest.approx(esperado, rel=1e-6), caso


def test_gera_fixtures_para_o_js(service, web_model):
    """Congela entrada -> vetor -> preço para o teste do bun comparar."""
    casos = []
    for caso in CASOS:
        vetor = _vetor(service, caso)
        resultado = service.predict({**caso, "cidade": "Teresina"})
        casos.append(
            {
                "entrada": caso,
                "vetor": vetor,
                "preco": resultado["preco_estimado"],
                "confianca": resultado["confianca"],
            }
        )

    FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_PATH.write_text(json.dumps(casos, ensure_ascii=False, indent=2), "utf-8")
    assert len(casos) == len(CASOS)


def test_confianca_reflete_cobertura_do_treino(service):
    conhecido = service.predict(
        {
            "area": 90,
            "quartos": 3,
            "banheiros": 2,
            "tipo": "apartamento",
            "bairro": "Fátima",
            "cidade": "Teresina",
        }
    )
    desconhecido = service.predict(
        {
            "area": 90,
            "quartos": 3,
            "banheiros": 2,
            "tipo": "apartamento",
            "bairro": "Bairro Inexistente",
            "cidade": "Teresina",
        }
    )
    assert conhecido["confianca"] == "alta"
    assert desconhecido["confianca"] == "baixa"
