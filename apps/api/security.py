"""Controle de acesso aos endpoints administrativos.

O router de pipeline dispara scraping e retreino — operações caras que gravam
no disco do servidor. Expostas sem autenticação numa API pública, qualquer
pessoa consegue consumir a máquina inteira. Por isso o padrão aqui é
*fail-closed*: em produção o router só é montado se explicitamente habilitado,
e quando habilitado exige token.
"""

from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException


def _env_flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def is_development() -> bool:
    return os.environ.get("ENVIRONMENT", "development").strip().lower() == "development"


def pipeline_api_enabled() -> bool:
    """Router de pipeline montado? Ligado em dev, desligado fora dele."""
    return _env_flag("ENABLE_PIPELINE_API", default=is_development())


async def require_admin_token(authorization: str | None = Header(default=None)) -> None:
    """Exige `Authorization: Bearer <PIPELINE_API_TOKEN>` quando o token existe.

    Sem `PIPELINE_API_TOKEN` definido, libera apenas em desenvolvimento. Isso
    evita que um deploy com `ENABLE_PIPELINE_API=true` e token esquecido caia
    silenciosamente em acesso aberto.
    """
    expected = os.environ.get("PIPELINE_API_TOKEN", "").strip()

    if not expected:
        if is_development():
            return
        raise HTTPException(
            status_code=403,
            detail="Endpoint administrativo indisponível: PIPELINE_API_TOKEN não configurado.",
        )

    scheme, _, provided = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(provided.strip(), expected):
        raise HTTPException(
            status_code=401,
            detail="Token administrativo inválido ou ausente.",
            headers={"WWW-Authenticate": "Bearer"},
        )
