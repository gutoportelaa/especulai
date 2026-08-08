# =============================================================================
# Especulai — Makefile
# Backend: uv | Frontend: bun
# =============================================================================

.PHONY: help install venv dev start kill-port \
        web-install web-dev web-build web-check web-fix \
        pipeline train scrape \
        test coverage typecheck lint ci \
        docker docker-down clean

# Porta padrão da API
PORT ?= 8000

# =============================================================================
# AJUDA
# =============================================================================

help:
	@echo ""
	@echo "  Especulai — Comandos disponíveis"
	@echo "  ================================="
	@echo ""
	@echo "  BACKEND (uv)"
	@echo "    make install        Instala dependências Python (uv sync)"
	@echo "    make venv           Cria virtualenv (.venv)"
	@echo "    make dev            API com hot-reload (porta $(PORT))"
	@echo "    make start          API modo produção"
	@echo "    make kill-port      Mata processo na porta $(PORT)"
	@echo ""
	@echo "  FRONTEND (bun)"
	@echo "    make web-install    Instala dependências JS (bun install)"
	@echo "    make web-dev        Dev server Vite (porta 5173)"
	@echo "    make web-build      Build de produção"
	@echo "    make web-check      Lint com Biome"
	@echo "    make web-fix        Auto-fix com Biome"
	@echo ""
	@echo "  ML PIPELINE"
	@echo "    make pipeline       Executa pipeline completo (scrape → train)"
	@echo "    make train          Treina modelo com dataset existente"
	@echo "    make scrape         Scraping OLX (5 páginas venda)"
	@echo ""
	@echo "  QUALIDADE"
	@echo "    make test           pytest (todos os testes)"
	@echo "    make coverage       pytest + relatório HTML"
	@echo "    make typecheck      basedpyright"
	@echo "    make lint           ruff check + format"
	@echo "    make ci             lint + typecheck + test (pipeline local)"
	@echo ""
	@echo "  INFRA"
	@echo "    make docker         Sobe containers (docker compose up -d)"
	@echo "    make docker-down    Para containers"
	@echo "    make clean          Remove __pycache__, .pyc, .ruff_cache"
	@echo ""

# =============================================================================
# BACKEND — uv
# =============================================================================

venv:
	uv venv

install:
	uv sync

install-dev:
	uv sync --extra dev

dev:
	uv run uvicorn apps.api.main:app --reload --host 0.0.0.0 --port $(PORT)

start:
	uv run uvicorn apps.api.main:app --host 0.0.0.0 --port $(PORT)

kill-port:
	@lsof -ti :$(PORT) | xargs kill -9 2>/dev/null || echo "Nenhum processo na porta $(PORT)"

# =============================================================================
# FRONTEND — bun
# =============================================================================

web-install:
	cd frontend && bun install

web-dev:
	cd frontend && bun run dev

web-build:
	cd frontend && bun run build

web-check:
	cd frontend && bun run check

web-fix:
	cd frontend && bun run fix

# =============================================================================
# ML PIPELINE
# =============================================================================

pipeline:
	uv run python -m ml.pipeline.orchestrator

train:
	uv run python -m ml.pipeline.train_model

scrape:
	uv run python -m apps.scraper.scraper_olx

prepare:
	uv run python -m ml.pipeline.prepare_dataset

# =============================================================================
# QUALIDADE DE CÓDIGO
# =============================================================================

test:
	uv run pytest tests/ -n auto -v

test-serial:
	uv run pytest tests/ -v

coverage:
	uv run pytest tests/ --cov=apps --cov=ml \
		--cov-report=html:reports/coverage \
		--cov-report=term-missing
	@echo "Relatório: reports/coverage/index.html"

typecheck:
	uv run basedpyright apps/ ml/

lint:
	uv run ruff check apps/ ml/
	uv run ruff format --check apps/ ml/

lint-fix:
	uv run ruff check --fix apps/ ml/
	uv run ruff format apps/ ml/

ci: lint typecheck test

# =============================================================================
# INFRA / DOCKER
# =============================================================================

docker:
	docker compose up -d

docker-down:
	docker compose down

# =============================================================================
# UTILITÁRIOS
# =============================================================================

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.pyo" -delete 2>/dev/null || true
	rm -rf .ruff_cache .pytest_cache .mypy_cache
	@echo "Cache limpo."
