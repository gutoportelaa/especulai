"""O cifrador de modelos: formato, chave, adulteração. A leitura em JS (Worker) é testada em
`deploy/worker/test/inferencia.test.js` contra o mesmo arquivo."""

from __future__ import annotations

import json

import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from ml.pipeline import cifrar_modelo
from ml.pipeline.export_web import NEGOCIOS

pytestmark = pytest.mark.skipif(
    not all((cifrar_modelo.WEB_MODEL_DIR / f"especulai-{n}.json").exists() for n in NEGOCIOS),
    reason="modelos exportados ausentes — rode `make export-web`",
)


@pytest.fixture
def cifrados(tmp_path, monkeypatch):
    monkeypatch.setattr(cifrar_modelo, "CHAVE", tmp_path / "chave")
    monkeypatch.setattr(cifrar_modelo, "SAIDA", tmp_path / "modelos")
    arquivos = cifrar_modelo.cifrar()
    return {n: a for n, a in zip(NEGOCIOS, arquivos, strict=True)}, tmp_path / "chave"


def _abrir(blob: bytes, chave: bytes) -> dict:
    assert blob.startswith(cifrar_modelo.MAGIC)
    inicio = len(cifrar_modelo.MAGIC)
    nonce, resto = blob[inicio : inicio + 12], blob[inicio + 12 :]
    return json.loads(AESGCM(chave).decrypt(nonce, resto, cifrar_modelo.AAD))


def test_ida_e_volta_preserva_o_modelo(cifrados):
    arquivos, arq_chave = cifrados
    chave = bytes.fromhex(arq_chave.read_text())
    for negocio in NEGOCIOS:
        original = json.loads(
            (cifrar_modelo.WEB_MODEL_DIR / f"especulai-{negocio}.json").read_text("utf-8")
        )
        assert _abrir(arquivos[negocio].read_bytes(), chave) == original


def test_chave_tem_256_bits_e_permissao_600(cifrados):
    _, arq_chave = cifrados
    assert len(bytes.fromhex(arq_chave.read_text())) == 32
    assert arq_chave.stat().st_mode & 0o777 == 0o600


def test_arquivo_nao_contem_o_modelo_legivel(cifrados):
    for arquivo in cifrados[0].values():
        blob = arquivo.read_bytes()
        assert b"trees" not in blob and b"Bairro_" not in blob and b"feature_columns" not in blob


def test_chave_errada_e_adulteracao_sao_rejeitadas(cifrados):
    arquivos, arq_chave = cifrados
    blob = arquivos["venda"].read_bytes()
    with pytest.raises(InvalidTag):
        _abrir(blob, AESGCM.generate_key(256))
    adulterado = bytearray(blob)
    adulterado[-1] ^= 1
    with pytest.raises(InvalidTag):
        _abrir(bytes(adulterado), bytes.fromhex(arq_chave.read_text()))


def test_cada_cifragem_usa_nonce_novo(cifrados, monkeypatch):
    arquivos, _ = cifrados
    primeiro = arquivos["venda"].read_bytes()
    cifrar_modelo.cifrar()
    assert arquivos["venda"].read_bytes()[5:17] != primeiro[5:17]
