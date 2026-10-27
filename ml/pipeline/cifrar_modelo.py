"""Cifra os modelos exportados para o servidor de inferência (`deploy/worker/modelos/*.enc`).

Os pesos são o ativo: nunca vão em claro para o git nem para a pasta pública do site. Cada modelo
(venda, aluguel) é cifrado separado com AES-256-GCM, sem compressão: o Worker só abre o que a
requisição usa, e descompressão gastaria CPU do plano gratuito. Formato:
`ESPC2 | nonce(12) | ciphertext+tag(16)`, com o rótulo de versão como dado associado.

A chave de 256 bits é gerada uma vez e fica em `~/especulai-dados-privados/modelo.key`
(chmod 600), fora do repositório. No servidor ela entra como segredo (`MODEL_KEY`, em hex).
Perdeu a chave? Gere outra e recifre: os pesos em claro vêm de `ml.pipeline.export_web`.

Uso: uv run --extra dev python -m ml.pipeline.cifrar_modelo
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from ml.pipeline.export_web import NEGOCIOS, WEB_MODEL_DIR

MAGIC = b"ESPC2"
AAD = b"especulai-modelo-v2"
CHAVE = Path.home() / "especulai-dados-privados" / "modelo.key"
SAIDA = Path(__file__).resolve().parents[2] / "deploy" / "worker" / "modelos"


def chave() -> bytes:
    if CHAVE.exists():
        return bytes.fromhex(CHAVE.read_text().strip())
    CHAVE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    nova = AESGCM.generate_key(bit_length=256)
    fd = os.open(CHAVE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(nova.hex())
    return nova


def cifrar() -> list[Path]:
    SAIDA.mkdir(parents=True, exist_ok=True)
    cifra = AESGCM(chave())
    saidas = []
    for negocio in NEGOCIOS:
        claro = (WEB_MODEL_DIR / f"especulai-{negocio}.json").read_bytes()
        claro = json.dumps(json.loads(claro), separators=(",", ":")).encode()
        nonce = os.urandom(12)
        destino = SAIDA / f"{negocio}.enc"
        destino.write_bytes(MAGIC + nonce + cifra.encrypt(nonce, claro, AAD))
        print(f"[OK] {destino.name} ({destino.stat().st_size / 1024:.0f} KB)")
        saidas.append(destino)
    return saidas


if __name__ == "__main__":
    cifrar()
