"""As métricas da página Como Funciona têm que ser as do modelo publicado.

`metricas-modelo.json` é gerado por `export_web` e versionado junto com o site. Sem os artefatos
locais, confere só contra `metricas_teste.json`; com eles, regera e exige igualdade: retreinar e
esquecer o `make export-web` falha aqui. Os gráficos SVG e a tabela do README saem do mesmo JSON e
também têm que estar em dia, assim como o mapa de bairros da Home, que além disso não pode
publicar nada abaixo dos mínimos de `treino_final` (política de `docs/dados-sensiveis.md`).
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from config.paths import ARTIFACT_DIR
from ml.pipeline import graficos_readme, mapa_bairros
from ml.pipeline.export_web import (
    METRICAS_TESTE,
    NEGOCIOS,
    SITE_METRICAS,
    _grupo,
    gerar_metricas_site,
)
from ml.pipeline.treino_final import MIN_AGREGADO, MIN_EXEMPLO


def _site() -> dict[str, dict[str, object]]:
    return json.loads(SITE_METRICAS.read_text("utf-8"))


@pytest.mark.parametrize("negocio", NEGOCIOS)
def test_site_mostra_o_teste_do_modelo_publicado(negocio: str) -> None:
    teste = json.loads(METRICAS_TESTE.read_text("utf-8"))[negocio]
    site = _site()[negocio]
    assert site["modelo"] == teste["modelo"]
    assert site["teste"] == {k: v for k, v in teste.items() if k != "modelo"}


@pytest.mark.skipif(
    not all((ARTIFACT_DIR / f"final_{n}.joblib").exists() for n in NEGOCIOS),
    reason="modelos finais não treinados — rode `python -m ml.pipeline.treino_final`",
)
def test_site_esta_em_dia_com_os_artefatos() -> None:
    assert _site() == json.loads(json.dumps(gerar_metricas_site())), (
        "metricas-modelo.json desatualizado: rode `make export-web` e commite o arquivo"
    )


def test_readme_e_graficos_em_dia_com_o_site() -> None:
    svgs, readme = graficos_readme.gerar(_site(), graficos_readme.README.read_text("utf-8"))
    assert graficos_readme.README.read_text("utf-8") == readme, (
        "tabela de resultados do README desatualizada: rode `make export-web`"
    )
    for nome, conteudo in svgs.items():
        caminho = graficos_readme.GRAFICOS_DIR / nome
        assert caminho.read_text("utf-8") == conteudo, (
            f"{nome} desatualizado: rode `make export-web`"
        )


def test_coluna_nova_sem_grupo_quebra_o_export() -> None:
    assert _grupo("Bairro_Fátima") == "Bairro"
    with pytest.raises(KeyError):
        _grupo("Piscina")


# --- Mapa de bairros da Home -------------------------------------------------------------------

CAMPOS_EXEMPLO = {"tipo", "area", "quartos", "pedido", "central", "minimo", "maximo", "dentro"}


def _mapa() -> dict[str, Any]:
    return json.loads(mapa_bairros.SITE_MAPA.read_text("utf-8"))


def test_mapa_e_do_modelo_publicado() -> None:
    teste = json.loads(METRICAS_TESTE.read_text("utf-8"))
    assert _mapa()["modelo"] == {n: teste[n]["modelo"] for n in NEGOCIOS}, (
        "mapa-bairros.json é de outro modelo: rode `make export-web`"
    )


@pytest.mark.parametrize("negocio", NEGOCIOS)
def test_mapa_so_publica_o_que_a_politica_de_dados_permite(negocio: str) -> None:
    """Agregado só com MIN_AGREGADO imóveis; exemplo só com MIN_EXEMPLO, descrito e arredondado."""
    for bairro in _mapa()["bairros"]:
        d = bairro[negocio]
        if d["imoveis"] < MIN_AGREGADO:
            assert not {"m2", "erro", "vies", "cobertura"} & d.keys(), bairro["nome"]
        if d["imoveis"] < MIN_EXEMPLO:
            assert "exemplos" not in d, bairro["nome"]
        for e in d.get("exemplos", []):
            assert set(e) == CAMPOS_EXEMPLO
            assert e["area"] % 5 == 0
            digitos = str(e["pedido"]).rstrip("0")
            assert len(digitos) <= 2, f"pedido sem arredondar: {e['pedido']}"
            assert e["dentro"] == (e["minimo"] <= e["pedido"] <= e["maximo"])


def test_mapa_cobre_todos_os_bairros_do_ibge() -> None:
    mapa = _mapa()
    assert len(mapa["bairros"]) == 123
    assert len({b["id"] for b in mapa["bairros"]}) == 123


@pytest.mark.skipif(
    not all((ARTIFACT_DIR / f"final_{n}.joblib").exists() for n in NEGOCIOS)
    or not mapa_bairros.MALHA.exists(),
    reason="sem modelos finais ou sem a malha do IBGE em data/ibge/",
)
def test_mapa_em_dia_com_os_artefatos() -> None:
    gerado = json.loads(json.dumps(mapa_bairros.gerar(mapa_bairros.carregar_artefatos())))
    assert _mapa() == gerado, "mapa-bairros.json desatualizado: rode `make export-web`"


def test_demo_do_hero_em_dia_com_o_mapa() -> None:
    demo = json.loads(mapa_bairros.SITE_DEMO.read_text("utf-8"))
    assert demo == mapa_bairros.demo_hero(_mapa())
    for n in ("venda", "aluguel"):
        assert sum(n in c for c in demo["candidatos"]) >= 10
    assert not any("imoveis" in b or "venda" in b for b in demo["bairros"])
