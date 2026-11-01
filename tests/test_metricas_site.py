"""As métricas da página Como Funciona têm que ser as do modelo publicado.

`metricas-modelo.json` é gerado por `export_web` e versionado junto com o site. Sem os artefatos
locais, confere só contra `metricas_teste.json`; com eles, regera e exige igualdade: retreinar e
esquecer o `make export-web` falha aqui. Os gráficos SVG e a tabela do README saem do mesmo JSON e
também têm que estar em dia.
"""

from __future__ import annotations

import json

import pytest

from config.paths import ARTIFACT_DIR
from ml.pipeline import graficos_readme
from ml.pipeline.export_web import (
    METRICAS_TESTE,
    NEGOCIOS,
    SITE_METRICAS,
    _grupo,
    gerar_metricas_site,
)


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
