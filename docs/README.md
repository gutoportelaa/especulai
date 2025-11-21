## Especulai - Organização e Manual de Inicialização

### Estrutura Modular

```
especulai/
├── apps/
│   ├── api/                # FastAPI + Celery entrypoint
│   └── scraper/            # Projeto de coleta (Scrapy/Celery)
├── frontend/               # Aplicação React (inalterada)
├── ml/
│   ├── pipeline/           # Scripts de treinamento (`train_model.py`)
│   └── artifacts/          # `modelo_definitivo.joblib`, métricas CSV etc.
├── notebooks/              # Experimentos e análise (Colab friendly)
├── docs/                   # Documentação adicional (este arquivo)
├── config/                 # `env.template`, variáveis compartilhadas
├── infra/redis/            # Artefatos de infraestrutura (ex.: dump.rdb)
└── requirements/           # `backend.txt`, `dev.txt`, etc.
```

### Requisitos

- Python 3.10+
- Node 18+
- Redis (Celery)
- PostgreSQL (dados do scraper/pipeline)

### Variáveis de Ambiente Sugeridas (`config/env.template`)

```
DATABASE_URL=postgresql://user:password@localhost:5432/especulai_db
MODEL_PATH=../ml/artifacts/modelo_definitivo.joblib
PREPROCESSOR_PATH=../ml/artifacts/preprocessador.joblib
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Backend (API FastAPI)

1. Instale dependências:
```bash
cd especulai
python -m venv .venv
.\.venv\Scripts\activate              # Windows
source .venv/bin/activate             # Linux/Mac
pip install -r requirements/backend.txt
```

2. Execute a API:
```bash
# estando na pasta especulai/
PYTHONPATH=%CD% python -m uvicorn especulai.apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

3. Testes rápidos:
```
GET  http://localhost:8000/
POST http://localhost:8000/predict
```

### Celery / Scraper

1. Suba o Redis local (ou use docker-compose da sua infra).
2. Dispare o worker:
```bash
cd especulai
PYTHONPATH=%CD% python -m celery -A especulai.apps.scraper.celery_app worker --loglevel=info
```
3. Use `POST /api/v1/scrape/start` para iniciar uma tarefa de scraping.

### Treinamento de ML

1. (Opcional) Regerar os CSVs com coleta/enriquecimento:
   ```bash
   cd especulai/ml/pipeline
   python pipeline_ml.py
   ```
2. Treinar e exportar o Gradient Boosting definitivo:
   ```bash
   cd especulai/ml/pipeline
   python train_model.py
   ```
3. Os artefatos serão salvos automaticamente em `ml/artifacts/` (`modelo_definitivo.joblib` e `preprocessador.joblib`). Configure `MODEL_PATH`/`PREPROCESSOR_PATH` conforme necessário.

### Frontend

```
cd especulai/frontend
npm install
npm run dev
```

A aplicação consome `VITE_API_URL` (definida em `.env`) apontando para o backend.

### Notas Finais

- A pasta `frontend/` permanece imutável para facilitar o deploy na Vercel/Netlify.
- Métricas e experimentos ficam versionados em `ml/artifacts` e `notebooks/`.
- Ajuste o `PYTHONPATH` sempre que executar scripts diretamente fora do pacote `especulai`.
