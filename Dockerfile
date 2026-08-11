# Imagem de serving da API. Instala apenas o extra base do pyproject —
# scraping e geopandas ficam de fora de propósito (ver comentário nas deps).
FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# HF Spaces roda o container como uid 1000 e monta nada gravável fora de $HOME.
RUN useradd -m -u 1000 app
ENV HOME=/home/app \
    PATH=/home/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/home/app/.venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

USER app
WORKDIR /home/app/especulai

# Camada de dependências separada do código: rebuild de código não reinstala o
# mundo. --no-install-project porque o pacote local ainda não foi copiado.
COPY --chown=app:app pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project

COPY --chown=app:app apps/ ./apps/
COPY --chown=app:app ml/ ./ml/
COPY --chown=app:app config/ ./config/
RUN uv sync --locked --no-dev

# DATA_DIR precisa ser gravável: os endpoints de health e info leem daqui.
ENV DATA_DIR=/home/app/especulai/data \
    ARTIFACT_DIR=/home/app/especulai/ml/artifacts \
    ENVIRONMENT=production \
    API_PORT=7860
RUN mkdir -p "$DATA_DIR"

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,os;urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"API_PORT\"]}/health').read()"

CMD ["sh", "-c", "uvicorn apps.api.main:app --host 0.0.0.0 --port ${API_PORT:-7860}"]
