"""Cifra os modelos exportados para o servidor de inferência (`deploy/space/modelo.enc`).

Os pesos são o ativo: nunca vão em claro para o git nem para a pasta pública do site. O pacote
(venda + aluguel) é comprimido e cifrado com AES-256-GCM; o formato é
`ESPC1 | nonce(12) | ciphertext+tag`, com o rótulo de versão como dado associado.

A chave de 256 bits é gerada uma vez e fica em `~/especulai-dados-privados/modelo.key`
(chmod 600), fora do repositório. No servidor ela entra como segredo (`MODEL_KEY`, em hex).
Perdeu a chave? Gere outra e recifre: os pesos em claro vêm de `ml.pipeline.export_web`.

Uso: uv run --with cryptography python -m ml.pipeline.cifrar_modelo
"""

from __future__ import annotations

import gzip
import json
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from ml.pipeline.export_web import NEGOCIOS, WEB_MODEL_DIR

MAGIC = b"ESPC1"
AAD = b"especulai-modelo-v1"
CHAVE = Path.home() / "especulai-dados-privados" / "modelo.key"
SAIDA = Path(__file__).resolve().parents[2] / "deploy" / "space" / "modelo.enc"


def chave() -> bytes:
    if CHAVE.exists():
        return bytes.fromhex(CHAVE.read_text().strip())
    CHAVE.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    nova = AESGCM.generate_key(bit_length=256)
    fd = os.open(CHAVE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(nova.hex())
    return nova


def cifrar() -> Path:
    pacote = {
        n: json.loads((WEB_MODEL_DIR / f"especulai-{n}.json").read_text("utf-8")) for n in NEGOCIOS
    }
    claro = gzip.compress(json.dumps(pacote, separators=(",", ":")).encode(), mtime=0)
    nonce = os.urandom(12)
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_bytes(MAGIC + nonce + AESGCM(chave()).encrypt(nonce, claro, AAD))
    print(f"[OK] {SAIDA} ({SAIDA.stat().st_size / 1024:.0f} KB); chave em {CHAVE}")
    return SAIDA


if __name__ == "__main__":
    cifrar()
