"""Recusa commit de dados brutos de portais ou de colunas que identificam pessoas.

Lê só os arquivos em staging. Chamado por `.githooks/pre-commit`.
"""

from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path

CAMINHOS_PROIBIDOS = re.compile(r"^data/(raw_[^/]+|detalhes_[^/]+)\.csv$")
PESOS_EM_CLARO = re.compile(r"(^|/)especulai-(venda|aluguel)\.json$")
COLUNAS_PROIBIDAS = {"anunciante", "endereco_completo", "cep", "telefone", "email", "cpf"}
# Já versionado antes desta regra; contém URL e centróides de bairro, sem nome nem rua.
LEGADO = {"data/dataset_treino_olx_final.csv"}


def staged() -> list[str]:
    saida = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=AM"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [linha for linha in saida.splitlines() if linha]


def problemas(caminho: str) -> list[str]:
    if CAMINHOS_PROIBIDOS.match(caminho):
        return [f"{caminho}: bruto de portal não vai para o git"]
    if PESOS_EM_CLARO.search(caminho):
        return [f"{caminho}: pesos em claro não vão para o git (só cifrados, deploy/space)"]
    if not caminho.endswith(".csv") or caminho in LEGADO:
        return []
    with Path(caminho).open(encoding="utf-8", newline="") as f:
        cabecalho = next(csv.reader(f), [])
    achadas = sorted({c for c in cabecalho if c.strip().lower() in COLUNAS_PROIBIDAS})
    return [f"{caminho}: coluna que identifica pessoa: {', '.join(achadas)}"] if achadas else []


def main() -> int:
    erros = [e for caminho in staged() for e in problemas(caminho)]
    for erro in erros:
        print(f"BLOQUEADO  {erro}", file=sys.stderr)
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main())
