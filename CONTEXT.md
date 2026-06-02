# Especulai — Contexto do Produto e Diagnóstico Técnico

Plataforma de estimativa de preços de imóveis em Teresina (PI) usando Machine Learning.
Pipeline: OLX Scraping → Enriquecimento Geoespacial + Econômico → Gradient Boosting → API REST + Frontend React.

---

## 1. Visão do Produto

**Problema:** Compradores e vendedores de imóveis em Teresina não têm referência objetiva de preço justo.

**Solução:** Modelo ML treinado em dados reais da OLX (venda + aluguel) enriquecidos com:
- Coordenadas geográficas e POI (farmácias, escolas, mercados, hospitais)
- Dados econômicos FipeZap (preço médio do m² por região)

**Saída:** API REST (`POST /predict`) que recebe área, quartos, banheiros, bairro e tipo de imóvel e retorna preço estimado + nível de confiança.

---

## 2. Arquitetura Atual

```
especulai/
├── apps/
│   ├── api/          # FastAPI — serve predições e orquestra pipeline
│   └── scraper/      # Coleta bruta de dados OLX (requests + BeautifulSoup)
├── ml/
│   ├── artifacts/    # Modelos treinados (.joblib) — não versionados
│   └── pipeline/
│       ├── modules/  # enriquecimento_geoespacial.py, enriquecimento_economico.py
│       ├── orchestrator.py    # Coordena os 5 estágios
│       ├── prepare_dataset.py # Limpeza, OHE, feature engineering
│       └── train_model.py     # GradientBoostingRegressor
├── frontend/         # React 19 + Vite + Tailwind (sem package.json até agora)
├── notebooks/        # Análise exploratória e avaliação de modelos
├── config/           # env.template
└── docs/             # Guias de treinamento
```

**Fluxo de dados (fora do projeto):**
```
dados_imoveis_teresina/   ← FORA do diretório especulai/
├── raw_olx.csv
├── enriched_geo_olx.csv
├── enriched_economic_olx.csv
├── dataset_treino_olx_final.csv
├── pipeline_status.json
└── *.log
```

---

## 3. Problemas Diagnosticados

### 3.1 Críticos (bloqueiam funcionamento em ambiente limpo)

**P1 — Sem gerenciamento de pacotes Python**
- Não havia `pyproject.toml` nem `uv.lock`; apenas `requirements.txt` flat sem pins de versão adequados
- `uv sync` não funcionava; dependências inconsistentes entre ambientes
- **Correção aplicada:** `pyproject.toml` criado com `uv` como gerenciador

**P2 — Frontend sem `package.json`**
- `frontend/` tinha apenas arquivos-fonte; impossível executar `bun install` ou `npm install`
- Não havia scripts definidos (`dev`, `build`, `check`, `fix`)
- **Correção aplicada:** `frontend/package.json` criado com `bun` como gerenciador

**P3 — Sem `Makefile`**
- Nenhum ponto de entrada padronizado para desenvolvedores
- Comandos espalhados em docs sem automação
- **Correção aplicada:** `Makefile` criado com targets para backend (uv), frontend (bun) e pipeline

**P4 — DATA_ROOT aponta fora do repositório**
- `WORKSPACE_ROOT = Path(__file__).resolve().parents[N]` resolve para o diretório PAI do projeto
- `DATA_ROOT = WORKSPACE_ROOT / "dados_imoveis_teresina"` cria dados em `~/Documents/dados_imoveis_teresina/`
- Isso quebra silenciosamente em qualquer clone limpo ou CI
- Afeta: `orchestrator.py`, `scraper_olx.py`, `prepare_dataset.py`, `train_model.py`, `pipeline.py` (rota)
- **Melhoria sugerida:** `DATA_ROOT = PROJECT_ROOT / "data"` (dentro do repo, ignorado pelo `.gitignore`)

**P5 — Imports assumem `especulai.` como namespace raiz sem instalação do pacote**
- `from especulai.apps.api.routes.health import router` falha se o pacote não estiver instalado
- Não havia `pyproject.toml` definindo o pacote instalável
- **Correção aplicada:** `pyproject.toml` registra o pacote; `uv sync` instala em modo editable por padrão

### 3.2 Importantes (degradam qualidade e manutenibilidade)

**P6 — Código morto não removido**
- `apps/api/legacy_main.py` — versão original monolítica da API, nunca usada em produção
- `apps/scraper/old_collector.py` — scraper antigo com Scrapy, substituído por `scraper_olx.py`
- Cria confusão sobre qual implementação está ativa
- **Ação sugerida:** remover ambos e atualizar `.gitignore`

**P7 — `scrape_service.py` é stub morto (HTTP 501)**
- `POST /api/v1/scrape/start` sempre retorna 501 Not Implemented
- Endpoint registrado na API sem funcionalidade real
- **Ação sugerida:** remover o endpoint ou implementar disparo real do orchestrator em background

**P8 — CORS hardcoded no `main.py`**
- `allow_origins=["http://localhost:5173", ...]` não usa variável de ambiente
- Em produção será necessário mudar o código em vez de config
- **Melhoria sugerida:** ler `ALLOWED_ORIGINS` de `.env` via `python-dotenv`

**P9 — `ModelService.load()` tem lógica de fallback excessiva que oculta erros reais**
- ~100 linhas de tratamento de exceção com múltiplos `try/except` aninhados
- Constrói `StandardScaler` e `LabelEncoder` com valores arbitrários quando os artefatos não existem
- Resulta em predições silenciosamente erradas em vez de falha rápida
- **Melhoria sugerida:** falhar em startup se os artefatos não existirem; usar health check para reportar o estado

**P10 — `train_model.py` tem `if __name__ == "__main__": main()` duplicado**
- Linhas finais têm dois blocos idênticos — dead code
- **Correção sugerida:** remover o segundo bloco

**P11 — Logging não centralizado**
- Cada módulo chama `setup_logging()` que chama `logging.basicConfig()`
- `basicConfig` só configura uma vez; chamadas subsequentes são ignoradas
- Log vai para múltiplos arquivos (`pipeline_orchestrator.log`, `scraper_olx_log.txt`, `prepare_dataset_log.txt`, `train_model_log.txt`) fora do repo
- **Melhoria sugerida:** logger central em `especulai/logger.py` configurado no startup da API/pipeline

**P12 — `api/routes/health.py` não verificado — importado mas não lido**
- Roteador de health está registrado mas o conteúdo não foi auditado nesta sessão

**P13 — Frontend usa `fetch` nativo em vez de cliente tipado**
- `api/client.js` usa `fetch` diretamente
- Não há tratamento de timeout, retry, nem interceptores centralizados
- **Melhoria sugerida:** migrar para `axios` com instância configurada por `VITE_API_URL`

**P14 — CLAUDE.md aponta para projeto errado (RecruttAI)**
- O arquivo CLAUDE.md em raiz descreve o produto RecruttAI (currículo com IA), não o Especulai
- Toda a seção de stack, estrutura e pipeline está incorreta para este repositório
- **Ação sugerida:** reescrever CLAUDE.md para o contexto Especulai

### 3.3 Menores (tech debt e boas práticas)

**P15 — Sem testes automatizados**
- Não há diretório `tests/` nem arquivos `test_*.py`
- Pipeline e API sem cobertura; regressões só descobertas manualmente
- **Melhoria sugerida:** pytest com fixtures para `ModelService` e endpoints FastAPI (usar `httpx.AsyncClient`)

**P16 — `model_service.py` mistura detecção de modelo com lógica de predição**
- Dois métodos `_predict_xgboost` e `_predict_standard` com lógica diferente para cada tipo de modelo
- Viola Single Responsibility; difícil testar isoladamente

**P17 — `requirements.txt` e `requirements/backend.txt` são redundantes**
- Com `pyproject.toml` + uv, esses arquivos não são mais necessários
- **Ação sugerida:** remover após validar que `pyproject.toml` cobre todas as dependências

**P18 — `.gitignore` ignora `*.csv` globalmente**
- `dataset_fonte_olx.csv` (5 MB) está commitado no repo, violando a própria regra do `.gitignore`
- Arquivos grandes de dados não deveriam estar no VCS
- **Ação sugerida:** usar Git LFS ou mover para `data/` e documentar processo de obtenção

---

## 4. Melhorias Prioritárias

### Alta Prioridade

1. **Consolidar DATA_ROOT dentro do projeto**
   ```python
   # Em todos os módulos de pipeline:
   PROJECT_ROOT = Path(__file__).resolve().parents[2]  # especulai/
   DATA_DIR = PROJECT_ROOT / "data" / "raw"
   ARTIFACT_DIR = PROJECT_ROOT / "ml" / "artifacts"
   ```

2. **Centralizar configuração via `.env`**
   ```
   # .env (baseado em config/env.template)
   MODEL_PATH=ml/artifacts/modelo_definitivo.joblib
   PREPROCESSOR_PATH=ml/artifacts/preprocessador.joblib
   ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
   DATA_DIR=data
   API_PORT=8000
   ```

3. **Remover código morto**
   - `apps/api/legacy_main.py`
   - `apps/scraper/old_collector.py`
   - Segundo bloco `if __name__` em `train_model.py`

4. **Implementar ou remover `/api/v1/scrape/start`**
   - Endpoint registrado na API não pode retornar 501 permanentemente

### Média Prioridade

5. **Suite mínima de testes**
   ```
   tests/
   ├── conftest.py
   ├── api/
   │   ├── test_health.py
   │   └── test_predict.py      # testa fallback + modelo carregado
   └── ml/
       └── test_model_service.py  # testa load + predict com artefatos mock
   ```

6. **Logger centralizado**
   ```python
   # especulai/logger.py
   import logging
   def get_logger(name: str) -> logging.Logger:
       ...
   ```

7. **Simplificar `ModelService.load()`**
   - Fail fast se artefato não existir; apenas um caminho de carregamento
   - Health endpoint retorna `{"model_loaded": false}` para ambiente sem artefato

### Baixa Prioridade

8. **Migrar frontend para TypeScript**
   - Adicionar `tsconfig.json`; renomear `.jsx` → `.tsx`
   - Tipos para resposta da API (`PredictionResponse`, `HealthResponse`)

9. **Adicionar `docker-compose.yml`**
   - Serviço `api` (Python + uv)
   - Serviço `web` (bun + vite)
   - Volume para `ml/artifacts/` e `data/`

10. **Documentar processo de treinamento end-to-end**
    - `make scrape` → `make pipeline` → `make train` → `make dev`

---

## 5. Comandos Disponíveis

Com `pyproject.toml` e `Makefile` adicionados, o workflow padronizado é:

```bash
# Setup inicial
uv sync --extra dev          # Instala Python deps
cd frontend && bun install   # Instala JS deps

# Desenvolvimento
make dev                     # API em http://localhost:8000
make web-dev                 # Frontend em http://localhost:5173

# Pipeline ML
make scrape                  # Coleta dados OLX
make pipeline                # Pipeline completo
make train                   # Treina com dataset existente

# Qualidade
make ci                      # lint + typecheck + tests
make test                    # Só testes
make coverage                # Testes + relatório HTML
```

---

## 6. Decisões de Design Conhecidas

- **GradientBoosting em vez de XGBoost como primário:** modelo mais interpretável e sem dependência nativa; XGBoost é suportado no `ModelService` via duck-typing
- **Dados fora do repo:** volume de dados OLX pode crescer para centenas de MB; decisão de não commitar raw data (exceto o `dataset_fonte_olx.csv` inicial de 5MB que já está no repo)
- **Scraping direto (sem Scrapy):** `scraper_olx.py` usa `requests + BeautifulSoup` em vez do Scrapy original (`old_collector.py`) por simplicidade; OLX bloqueia bots com frequência, scraping é intrinsecamente frágil
- **Pipeline síncrono via background_tasks do FastAPI:** sem Redis/Celery para não aumentar dependências; adequado para volume atual (minutos por execução)
