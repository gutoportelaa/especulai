"""O servidor de inferência (`deploy/space`) reproduz o treino sem sklearn, cifra os pesos e limita
o uso. Paridade contra as fixtures geradas por `test_web_export_parity.py`."""

from __future__ import annotations

import json
import os
import sys

import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi.testclient import TestClient

from config.paths import PROJECT_ROOT
from ml.pipeline import cifrar_modelo
from ml.pipeline.export_web import NEGOCIOS, WEB_MODEL_DIR

sys.path.insert(0, str(PROJECT_ROOT / "deploy" / "space"))
import app as servidor  # noqa: E402
import inferencia  # noqa: E402

FIXTURES = PROJECT_ROOT / "tests" / "fixtures" / "parity.json"

pytestmark = pytest.mark.skipif(
    not all((WEB_MODEL_DIR / f"especulai-{n}.json").exists() for n in NEGOCIOS)
    or not FIXTURES.exists(),
    reason="modelos exportados ausentes — rode `make export-web` e `uv run pytest tests/`",
)


@pytest.fixture(scope="module")
def modelos() -> dict:
    return {
        n: json.loads((WEB_MODEL_DIR / f"especulai-{n}.json").read_text("utf-8")) for n in NEGOCIOS
    }


@pytest.fixture(scope="module")
def fixtures() -> dict:
    return json.loads(FIXTURES.read_text("utf-8"))


@pytest.mark.parametrize("negocio", NEGOCIOS)
def test_vetor_e_log_preco_batem_com_o_treino(modelos, fixtures, negocio):
    for caso in fixtures[negocio]:
        entrada = {k: v for k, v in caso["entrada"].items()}
        vetor, *_ = inferencia.montar_vetor(entrada, modelos[negocio])
        assert vetor == pytest.approx(caso["vetor"], abs=1e-9), entrada
        log = inferencia.prever_log(vetor, modelos[negocio])
        assert log == pytest.approx(caso["log_preco"], abs=1e-5), entrada


def test_intervalo_e_simetrico_em_log_e_respeita_a_faixa():
    cfg = {"cortes": [100.0, 200.0], "meia_largura": [0.1, 0.2, 0.3], "nivel": 0.8}
    assert inferencia.intervalo(50, cfg)[1] == pytest.approx(50 * 2.718281828**0.1, rel=1e-6)
    assert inferencia.intervalo(100, cfg)[1] == pytest.approx(100 * 2.718281828**0.1, rel=1e-6)
    assert inferencia.intervalo(900, cfg)[1] == pytest.approx(900 * 2.718281828**0.3, rel=1e-6)
    lo, hi = inferencia.intervalo(300, cfg)
    assert lo * hi == pytest.approx(300 * 300)


def test_arredondamento():
    assert inferencia.arredondar(1234.0) == 1230
    assert inferencia.arredondar(456_789.0) == 457_000


def test_confianca():
    assert inferencia.confianca(False, True, 100, 90) == "baixa"
    assert inferencia.confianca(True, True, 3, 90) == "média"
    assert inferencia.confianca(True, False, 100, 90) == "média"
    assert inferencia.confianca(True, True, 100, 5000) == "média"
    assert inferencia.confianca(True, True, 100, 90) == "alta"


def test_cifragem_ida_e_volta_e_rejeita_chave_errada_e_adulteracao(modelos, tmp_path, monkeypatch):
    monkeypatch.setattr(cifrar_modelo, "CHAVE", tmp_path / "k")
    monkeypatch.setattr(cifrar_modelo, "SAIDA", tmp_path / "m.enc")
    monkeypatch.setattr(cifrar_modelo, "WEB_MODEL_DIR", WEB_MODEL_DIR)
    saida = cifrar_modelo.cifrar()
    blob = saida.read_bytes()
    chave = bytes.fromhex((tmp_path / "k").read_text())
    assert (tmp_path / "k").stat().st_mode & 0o777 == 0o600
    assert b"trees" not in blob and b"Bairro_" not in blob

    assert inferencia.decifrar(blob, chave)["venda"]["init"] == modelos["venda"]["init"]
    with pytest.raises(InvalidTag):
        inferencia.decifrar(blob, AESGCM.generate_key(256))
    adulterado = bytearray(blob)
    adulterado[-1] ^= 1
    with pytest.raises(InvalidTag):
        inferencia.decifrar(bytes(adulterado), chave)


def test_pacote_versionado_abre_com_a_chave_local():
    chave = cifrar_modelo.CHAVE
    if not chave.exists():
        pytest.skip("chave local ausente")
    abertos = inferencia.decifrar(
        cifrar_modelo.SAIDA.read_bytes(), bytes.fromhex(chave.read_text())
    )
    assert set(abertos) == set(NEGOCIOS)


@pytest.fixture
def cliente(modelos, monkeypatch):
    monkeypatch.setattr(servidor, "POR_MINUTO", 5)
    return TestClient(servidor.criar_app(modelos))


BASE = {"negocio": "venda", "area": 90, "quartos": 3, "banheiros": 2, "tipo": "Apartamento",
        "bairro": "Fátima"}  # fmt: skip


def test_resposta_so_traz_a_faixa(cliente):
    r = cliente.post("/estimar", json=BASE)
    assert r.status_code == 200
    corpo = r.json()
    assert set(corpo) == {"negocio", "preco_estimado", "minimo", "maximo", "nivel", "confianca"}
    assert corpo["minimo"] < corpo["preco_estimado"] < corpo["maximo"]


@pytest.mark.parametrize(
    "mudanca",
    [
        {"area": 5},
        {"area": 99999},
        {"quartos": -1},
        {"negocio": "troca"},
        {"bairro": ""},
        {"tipo": "x" * 100},
        {"vagas": 500},
    ],  # fmt: skip
)
def test_entradas_invalidas_sao_rejeitadas(cliente, mudanca):
    assert cliente.post("/estimar", json={**BASE, **mudanca}).status_code == 422


def test_limite_por_minuto_responde_429_com_retry_after(cliente):
    cabecalho = {"x-forwarded-for": "9.9.9.9"}
    codigos = [cliente.post("/estimar", json=BASE, headers=cabecalho).status_code for _ in range(7)]
    assert codigos[:5] == [200] * 5 and codigos[5:] == [429, 429]
    r = cliente.post("/estimar", json=BASE, headers=cabecalho)
    assert int(r.headers["retry-after"]) >= 1
    outro = cliente.post("/estimar", json=BASE, headers={"x-forwarded-for": "8.8.8.8"})
    assert outro.status_code == 200


def test_ip_forjado_no_inicio_do_cabecalho_nao_burla_o_limite(cliente):
    codigos = [
        cliente.post(
            "/estimar", json=BASE, headers={"x-forwarded-for": f"1.1.1.{i}, 7.7.7.7"}
        ).status_code
        for i in range(7)
    ]
    assert codigos.count(429) == 2


def test_cors_so_para_origens_permitidas(cliente):
    ok = cliente.options(
        "/estimar",
        headers={
            "Origin": "https://gutoportelaa.github.io",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert ok.headers.get("access-control-allow-origin") == "https://gutoportelaa.github.io"
    mau = cliente.options(
        "/estimar",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in mau.headers


def test_sem_chave_o_servidor_nao_sobe(monkeypatch):
    monkeypatch.delenv("MODEL_KEY", raising=False)
    with pytest.raises(RuntimeError):
        servidor.carregar_modelos()
    assert os.environ.get("MODEL_KEY") is None
