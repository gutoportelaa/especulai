# Especulai — CLAUDE.md

Guia completo de engenharia para o projeto Especulai. Leia este arquivo no início de **cada sessão** antes de qualquer tarefa.

---

## 1. Visão Geral do Produto

Especulai é uma plataforma de **estimativa de preços de imóveis em Teresina (PI)** usando Machine Learning. Dados brutos são coletados da OLX, enriquecidos com informações geoespaciais e econômicas, e usados para treinar um modelo de regressão que serve predições via API REST.

**Pipeline principal:**
```
OLX Scraping → Enriquecimento Geoespacial → Enriquecimento Econômico → Preparação do Dataset → Treinamento → API REST
```

**Entrada do usuário:** área (m²), quartos, banheiros, tipo (apartamento/casa), bairro, cidade
**Saída:** preço estimado (R$) + nível de confiança (alta / média / baixa)

---

## 2. Estrutura de Diretórios

```
especulai/
├── apps/
│   ├── api/                   # Backend FastAPI
│   │   ├── main.py            # App FastAPI, middlewares, routers
│   │   ├── legacy_main.py     # MORTO — não usar, aguardando remoção
│   │   ├── models/
│   │   │   └── schemas.py     # ImovelInput, PredictionOutput, HealthCheck (Pydantic)
│   │   ├── routes/
│   │   │   ├── health.py      # GET / e GET /health
│   │   │   ├── predict.py     # POST /predict
│   │   │   ├── pipeline.py    # POST /api/v1/pipeline/run e demais endpoints de pipeline
│   │   │   └── scrape.py      # POST /api/v1/scrape/start (501 — stub, não implementado)
│   │   └── services/
│   │       ├── model_service.py   # Carga do artefato .joblib e inferência
│   │       └── scrape_service.py  # STUB — sempre lança 501
│   └── scraper/
│       ├── scraper_olx.py     # Scraper ativo (requests + BeautifulSoup)
│       ├── old_collector.py   # MORTO — não usar, aguardando remoção
│       └── collector.py       # Coletor auxiliar
├── ml/
│   ├── artifacts/             # Modelos treinados (.joblib) — não versionados
│   └── pipeline/
│       ├── orchestrator.py        # Coordena os 5 estágios, persiste status em JSON
│       ├── prepare_dataset.py     # Limpeza, OHE, feature engineering
│       ├── train_model.py         # GradientBoostingRegressor + artefatos
│       └── modules/
│           ├── enriquecimento_geoespacial.py   # Geocoding (Nominatim) + distâncias POI
│           └── enriquecimento_economico.py     # Fatores FipeZap por bairro
├── frontend/                  # React 19 + Vite + Tailwind
│   ├── src/
│   │   ├── api/               # client.js (fetch), prediction.js
│   │   ├── components/        # layout/ (Header, Footer) + ui/ (shadcn) 
│   │   ├── features/
│   │   │   └── prediction/    # constants.js, utils.js
│   │   ├── hooks/             # usePrediction.js, useMobileMenu.js, useScroll.js
│   │   ├── pages/             # Home.jsx, Predict.jsx
│   │   ├── App.jsx            # BrowserRouter com rotas /  e /predict
│   │   └── main.jsx           # Ponto de entrada React
│   ├── package.json           # Gerenciado por bun
│   ├── vite.config.js
│   └── tailwind.config.js
├── notebooks/                 # Análise exploratória e avaliação de modelos
├── config/
│   └── env.template           # Template de variáveis de ambiente
├── docs/                      # Guias de treinamento e README interno
├── data/                      # Dados intermediários do pipeline (não versionados)
│   └── (raw_olx.csv, enriched_geo_olx.csv, enriched_economic_olx.csv, ...)
├── pyproject.toml             # Gerenciado por uv
├── Makefile                   # Ponto de entrada único de comandos
└── CONTEXT.md                 # Diagnóstico técnico e melhorias priorizadas
```

> **Atenção:** `apps/api/legacy_main.py` e `apps/scraper/old_collector.py` são código morto — não modificar, aguardam remoção.

---

## 3. Stack Tecnológica

### Backend (`apps/`)

| Camada | Tecnologia |
|---|---|
| Runtime | Python 3.11+ |
| Framework HTTP | FastAPI 0.115+ + Uvicorn |
| Validação | Pydantic v2 |
| ML | scikit-learn (GradientBoosting) + XGBoost (suporte via duck-typing) |
| Dados | pandas 2.2+, numpy 1.26+ |
| Serialização de modelos | joblib |
| Geocodificação | geopy (Nominatim) |
| Scraping | requests + BeautifulSoup4 |
| Configuração | python-dotenv |
| Gerenciador de deps | `uv` |
| Linting | Ruff |
| Type checking | basedpyright |
| Testes | pytest + pytest-asyncio + httpx |

### Frontend (`frontend/`)

| Camada | Tecnologia |
|---|---|
| Framework | React 19 |
| Bundler | Vite 5 |
| Linguagem | JavaScript (JSX) — sem TypeScript ainda |
| Estilização | Tailwind CSS 3 |
| Componentes base | shadcn/ui (Radix UI) |
| Roteamento | react-router-dom v6 |
| HTTP | `fetch` nativo via `api/client.js` |
| Animações | framer-motion |
| Ícones | lucide-react |
| Linting | Biome |
| Gerenciador de deps | `bun` |

---

## 4. ML Pipeline — Detalhado

### Estágios

```
[Estágio 1] Scraping OLX
    scraper_olx.py
    - requests + BeautifulSoup para venda e aluguel
    - Delay aleatório entre páginas (2–5s) para evitar bloqueio
    - Saída: data/raw_olx.csv
    - Colunas: ID_Imovel, Tipo_Negocio, Tipo_Imovel, Area_m2, Quartos,
               Banheiros, Vagas_Garagem, Valor_Anuncio, Bairro, CEP, URL_Anuncio

[Estágio 2] Enriquecimento Geoespacial
    modules/enriquecimento_geoespacial.py
    - Geocodificação: Bairro → Lat/Lon via Nominatim (com cache local CSV)
    - Fallback: coordenadas do centro de Teresina (-5.0892, -42.8016)
    - Distâncias a 4 POIs: farmácias, escolas, mercados, hospitais
    - Saída: data/enriched_geo_olx.csv

[Estágio 3] Enriquecimento Econômico
    modules/enriquecimento_economico.py
    - Preço por m² baseado em dados FipeZap
    - Fatores de ajuste por bairro (dicionário hardcoded: Fátima=1.18, Centro=0.95, etc.)
    - Calcula FipeZap_m2 e FipeZap_Diferenca_m2
    - Saída: data/enriched_economic_olx.csv

[Estágio 4] Preparação de Dataset
    prepare_dataset.py
    - Limpeza: remove NaN em colunas obrigatórias, filtra outliers de preço
    - Feature engineering: densidade_comodos = (quartos + banheiros) / area
    - One-Hot Encoding: Tipo_Imovel, Bairro
    - Normalização: StandardScaler (ajustado aqui, salvo junto ao modelo)
    - Saída: data/dataset_treino_olx_final.csv

[Estágio 5] Treinamento
    train_model.py
    - Modelo: GradientBoostingRegressor(n_estimators=200, learning_rate=0.1, max_depth=5)
    - Split: 80% treino / 20% teste (random_state=42)
    - Métricas: MAE, RMSE, R² no treino e teste
    - Artefato: ml/artifacts/<timestamp>.joblib contendo {model, preprocessor, metadata}
    - preprocessor = {scaler, feature_columns, label_encoders, reference_values}
```

### Orquestração

`PipelineOrchestrator` persiste status em `data/pipeline_status.json`:
```
PENDING → RUNNING → SUCCESS / FAILED
```

Estágios já completados são pulados automaticamente (idempotente). Use `force_all=True` para re-executar tudo.

### Schemas de entrada/saída da API

```python
class ImovelInput(BaseModel):
    area: float          # m², obrigatório, > 0
    quartos: int         # >= 0
    banheiros: int       # >= 0
    tipo: str            # "apartamento" | "casa"
    bairro: str
    cidade: str

class PredictionOutput(BaseModel):
    preco_estimado: float   # R$
    confianca: str          # "alta" | "média" | "baixa"
```

### ModelService — lógica de inferência

`model_service.py` detecta o tipo de modelo automaticamente:
- **XGBRegressor:** chama `_predict_xgboost()` usando feature names do booster
- **Qualquer outro (GradientBoosting, etc.):** chama `_predict_standard()` com scaler + label encoders

Fallback no `POST /predict`: se `model_service.is_ready()` retornar `False`, a predição usa `area × preco_por_m2_median` com confiança "baixa". Isso permite que o frontend funcione sem modelo treinado.

---

## 5. Organização do Código — Backend

### Anatomia de uma Feature (API)

```
apps/api/
├── models/schemas.py      # Schemas Pydantic de entrada/saída
├── routes/<endpoint>.py   # Um arquivo por grupo de endpoints
└── services/<nome>.py     # Lógica de negócio desacoplada da rota
```

### Resposta padrão (atual)

A API retorna diretamente o schema Pydantic — sem envelope `{ success, errors, data }`.
Se adicionar novo endpoint, manter o mesmo padrão do existente.

### Endpoints disponíveis

| Método | Rota | Status | Descrição |
|---|---|---|---|
| GET | `/` | OK | Health check raiz |
| GET | `/health` | OK | Health check detalhado |
| POST | `/predict` | OK | Predição de preço |
| POST | `/api/v1/pipeline/run` | OK | Dispara pipeline em background |
| GET | `/api/v1/pipeline/status` | OK | Status atual do pipeline |
| GET | `/api/v1/pipeline/logs` | OK | Últimas linhas de log |
| POST | `/api/v1/pipeline/reset` | OK | Reseta pipeline |
| GET | `/api/v1/pipeline/info` | OK | Metadados do modelo treinado |
| POST | `/api/v1/scrape/start` | **501** | Stub — não implementado |

---

## 6. Organização do Código — Frontend

```
frontend/src/
├── api/
│   ├── client.js        # apiFetch() — wrapper de fetch com base URL via VITE_API_URL
│   └── prediction.js    # predictImovel() — chama POST /predict
├── components/
│   ├── layout/          # Header.jsx, Footer.jsx
│   ├── sections/        # HeroSection, FeaturesSection, HowItWorksSection, CTASection, FAQSection
│   └── ui/              # shadcn: accordion, badge, button, card
├── features/
│   └── prediction/
│       ├── constants.js # PREDICTION_DEFAULTS, TIPO_OPTIONS
│       └── utils.js     # normalizePredictionPayload()
├── hooks/
│   ├── usePrediction.js  # Estado do formulário + submit + reset
│   ├── useMobileMenu.js
│   └── useScroll.js
└── pages/
    ├── Home.jsx          # Landing page (todas as seções)
    └── Predict.jsx       # Formulário de predição + card de resultado
```

### Rotas

| Path | Componente | Descrição |
|---|---|---|
| `/` | `Home` | Landing page |
| `/predict` | `Predict` | Formulário de estimativa |

---

## 7. Makefile — Comandos

```bash
# Backend (uv)
make install        # uv sync
make install-dev    # uv sync --extra dev
make venv           # uv venv
make dev            # Uvicorn hot-reload (porta 8000)
make start          # Uvicorn produção
make kill-port      # Mata processo na porta 8000

# Frontend (bun)
make web-install    # bun install
make web-dev        # Vite dev server (porta 5173)
make web-build      # Build de produção
make web-check      # Biome lint
make web-fix        # Biome lint --write

# ML Pipeline
make pipeline       # Pipeline completo (scrape → enrich → prepare → train)
make train          # Treina modelo com dataset existente
make scrape         # Scraping OLX (5 páginas venda)
make prepare        # Prepara dataset para treinamento

# Qualidade
make test           # pytest -n auto (paralelo)
make test-serial    # pytest single-thread (debug)
make coverage       # pytest + relatório HTML em reports/coverage/
make typecheck      # basedpyright apps/ ml/
make lint           # ruff check + format --check
make lint-fix       # ruff check --fix + format
make ci             # lint + typecheck + test

# Infra
make docker         # docker compose up -d
make docker-down    # docker compose down
make clean          # Remove __pycache__, .pyc, caches
```

---

## 8. Gerenciadores de Dependências

| Projeto | Gerenciador | Arquivo de lock | Adicionar dep |
|---|---|---|---|
| `apps/` + `ml/` | `uv` | `uv.lock` | `uv add <pkg>` |
| `frontend/` | `bun` | `bun.lockb` | `bun add <pkg>` |

**Regras:**
- Backend: **sempre `uv`**, nunca `pip` diretamente
- Frontend: **sempre `bun`**, nunca `npm` ou `yarn`

---

## 9. Variáveis de Ambiente

### Backend (`api/.env` ou `.env` na raiz)

| Variável | Padrão | Descrição |
|---|---|---|
| `API_PORT` | `8000` | Porta da API |
| `ENVIRONMENT` | `development` | `development` \| `production` |
| `ALLOWED_ORIGINS` | `http://localhost:5173,...` | CORS origins (csv) |
| `MODEL_PATH` | `ml/artifacts/modelo_definitivo.joblib` | Caminho do artefato do modelo |
| `PREPROCESSOR_PATH` | `ml/artifacts/preprocessador.joblib` | Caminho do preprocessador |
| `DATA_DIR` | `data` | Diretório dos dados do pipeline |

### Frontend (`frontend/.env`)

| Variável | Padrão | Descrição |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | URL base da API |

> Copie `config/env.template` para `.env` e ajuste os valores.

---

## 10. Convenções de Código

### Python (Backend / ML)

- Type hints obrigatórios em funções públicas
- Sem `Any` — usar tipos específicos ou `Unknown`
- Sem comentários óbvios — apenas quando o WHY não é evidente
- Imports organizados: stdlib → third-party → local
- `basedpyright` com `typeCheckingMode = "standard"`
- Ruff para lint e format (linha máxima: 100)

### JavaScript (Frontend)

- Sem TypeScript ainda — não adicionar sem discutir antes
- `export function Component()` — não arrow function para componentes de página
- Arquivos em PascalCase para componentes (`Header.jsx`), camelCase para hooks e utilitários (`usePrediction.js`)
- Um componente por arquivo
- HTTP: **sempre** via `api/client.js` — nunca `fetch` direto em componentes
- Ícones: `lucide-react` (padrão atual do projeto)

---

## 11. Adicionar Nova Feature

### Backend

1. Criar schema em `apps/api/models/schemas.py` (ou arquivo separado para features grandes)
2. Criar `apps/api/services/<nome>_service.py` com lógica isolada
3. Criar `apps/api/routes/<nome>.py` com `APIRouter`
4. Incluir router em `apps/api/main.py`
5. `make ci` (lint + typecheck + tests)

### Frontend

1. Criar hook em `frontend/src/hooks/use<Nome>.js`
2. Criar constantes/utilitários em `frontend/src/features/<nome>/`
3. Criar página em `frontend/src/pages/<Nome>.jsx`
4. Adicionar rota em `frontend/src/App.jsx`
5. `make web-check` (Biome)

---

## 12. Problemas Conhecidos (Tech Debt)

| # | Problema | Impacto | Arquivo(s) |
|---|---|---|---|
| P1 | `DATA_ROOT` aponta fora do repo (`../dados_imoveis_teresina/`) | Quebra em clone limpo | `orchestrator.py`, `scraper_olx.py`, `prepare_dataset.py`, `train_model.py` |
| P2 | Código morto não removido | Confusão | `legacy_main.py`, `old_collector.py` |
| P3 | `/api/v1/scrape/start` retorna 501 permanentemente | Endpoint inativo | `scrape.py`, `scrape_service.py` |
| P4 | CORS hardcoded em vez de ler `.env` | Config via código | `main.py` |
| P5 | `ModelService.load()` constrói artefatos mock em vez de falhar | Erros silenciosos | `model_service.py` |
| P6 | Logging não centralizado (cada módulo chama `basicConfig`) | Logs inconsistentes | todos os módulos ML |
| P7 | Sem testes automatizados | Regressões não detectadas | — |
| P8 | `dataset_fonte_olx.csv` (5 MB) commitado violando `.gitignore` | Repo pesado | `.gitignore` |
| P9 | `train_model.py` tem bloco `if __name__` duplicado | Dead code | `train_model.py` L final |

> Para lista completa com soluções propostas, ver `CONTEXT.md`.

---

## 13. Referências Internas

- `CONTEXT.md` — Diagnóstico técnico detalhado + melhorias priorizadas
- `config/env.template` — Template de variáveis de ambiente
- `docs/GUIA_TREINAMENTO.md` — Como executar o pipeline de ponta a ponta
- `notebooks/analise_modelos.ipynb` — Comparação de modelos e feature importance
- `notebooks/avaliacao_metricas_modelos.ipynb` — Avaliação detalhada de métricas
