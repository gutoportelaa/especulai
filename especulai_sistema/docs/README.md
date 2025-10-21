## Especulai - Organização e Manual de Inicialização

### Estrutura Modular

- backend API (`api/`)
  - `main.py`: ponto de entrada FastAPI.
  - `routes/`: rotas da API (`health.py`, `predict.py`, `scrape.py`).
  - `models/schemas.py`: modelos Pydantic de entrada/saída.
  - `services/model_service.py`: carregamento do modelo e predição.
  - `services/scrape_service.py`: disparo de scraping via Celery.

- pipeline de ML (`ml_pipeline/`)
  - Espera os scripts e artefatos: `train_model.py`, `model.joblib`, `preprocessor.joblib`.

- scraper (`scraper/`)
  - Projeto Scrapy: `especulai_scraper/` e `spiders/`.

- frontend (`frontend/`)
  - Aplicação React em `src/` e `public/`.

### Requisitos

- Python 3.10+
- Node 18+
- Redis (para Celery)
- PostgreSQL (dados do scraper e pipeline de ML)

### Variáveis de Ambiente

```
DATABASE_URL=postgresql://user:password@localhost:5432/especulai_db
MODEL_PATH=../ml_pipeline/model.joblib
PREPROCESSOR_PATH=../ml_pipeline/preprocessor.joblib
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Inicialização - Backend (API)

1. Crie e ative venv e instale dependências:
```bash
cd especulai_sistema
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install fastapi uvicorn celery
```

2. Execute a API (opção 1 - script direto):
```bash
# Windows:
start_api.bat

# Linux/Mac:
PYTHONPATH=/caminho/para/especulai python run_api.py
```

3. Execute a API (opção 2 - uvicorn manual):
```bash
# Windows PowerShell:
$env:PYTHONPATH="C:\Users\gutop\Desktop\especulai"
python -m uvicorn especulai_sistema.api.main:app --reload --host 0.0.0.0 --port 8000

# Linux/Mac:
PYTHONPATH=/caminho/para/especulai python -m uvicorn especulai_sistema.api.main:app --reload --host 0.0.0.0 --port 8000
```

4. Teste:
```
GET http://localhost:8000/
POST http://localhost:8000/predict
```

### Inicialização - Celery (Scraping)

1. Suba o Redis local.
2. Inicie o worker Celery:
```
celery -A v2.tasks.celery worker --loglevel=info
```
3. Dispare o scraping:
```
POST http://localhost:8000/api/v1/scrape/start
```

Observação: ajuste o caminho do projeto Scrapy na task caso necessário.

### Treinamento de ML

1. Garanta o PostgreSQL e a tabela `imoveis_raw` populada.
2. Execute o pipeline para gerar `model.joblib` e `preprocessor.joblib`:
```
python v2/train_model.py
```
3. Verifique os artefatos em `ml_pipeline/` e atualize `MODEL_PATH`/`PREPROCESSOR_PATH` se necessário.

### Frontend

1. Instale dependências e rode localmente:
```
cd especulai_sistema/frontend
npm install
npm run dev
```
2. A UI consome `http://localhost:8000/predict`.

### Notas

- Se os artefatos não estiverem disponíveis, a rota `/health` da API retorna estado degradado.
- Para usar Docker/Compose, adapte os serviços de Redis, Postgres, API, Celery e Frontend conforme sua infra.


