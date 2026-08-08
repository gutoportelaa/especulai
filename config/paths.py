"""Caminhos canônicos do projeto.

Ponto único de verdade para diretórios de dados e artefatos. Todos os módulos
do pipeline e da API devem importar daqui em vez de recalcular `parents[N]`,
que varia conforme a profundidade do arquivo e quebra em clone limpo.

Sobrescrevível por ambiente:
  DATA_DIR      diretório de dados intermediários do pipeline (padrão: <repo>/data)
  ARTIFACT_DIR  diretório de artefatos de modelo (padrão: <repo>/ml/artifacts)
"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]

DATA_ROOT: Path = Path(os.environ.get("DATA_DIR") or PROJECT_ROOT / "data")
ARTIFACT_DIR: Path = Path(os.environ.get("ARTIFACT_DIR") or PROJECT_ROOT / "ml" / "artifacts")


def ensure_dirs() -> None:
    """Cria os diretórios de trabalho caso ainda não existam."""
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
