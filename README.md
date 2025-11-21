
<p align="center"> <img width="320" height="320" alt="logoEspeculai" src="https://github.com/user-attachments/assets/85cc721c-f969-4668-80d2-397bb0e079e7" />  </p>


# Especulai - Sistema de Estimativa de Preços de Imóveis

Sistema completo de Machine Learning para estimativa de preços de imóveis baseado em dados coletados da web. O projeto agora está modularizado dentro da pasta `especulai/`, facilitando o deploy independente de cada componente.

## Visão Geral dos Módulos

| Pasta               | Descrição                                                                 |
|---------------------|---------------------------------------------------------------------------|
| `apps/api`          | API FastAPI + rotas de scraping.                                          |
| `apps/scraper`      | Projeto Scrapy/Celery para coletar os anúncios.                           |
| `frontend`          | Aplicação React/Tailwind que consome o endpoint `/predict`.               |
| `ml/pipeline`       | Scripts de treinamento (`train_model.py`, utilitários).                   |
| `ml/artifacts`      | Artefatos prontos para produção (`modelo_definitivo.joblib`, métricas).   |
| `notebooks`         | Experimentos no Colab (por exemplo `analise_modelos.ipynb`).              |
| `config`            | Arquivos de configuração compartilhados (`env.template`).                 |
| `infra/redis`       | Artefatos de infraestrutura (ex.: `dump.rdb`).                            |
| `docs`              | Documentação operacional e guias rápidos.                                 |
| `requirements`      | Listas de dependências segmentadas (`backend.txt`, etc.).                 |

### Componentes Ativos

1. **Scraper** (`apps/scraper/`): coleta dados de portais como OLX e salva no banco relacional configurado por `DATABASE_URL`.
2. **Pipeline de ML** (`ml/pipeline/`):
   - Trata dados (remoção de outliers, normalização de features e sanitização de localização de OLX).
   - Treina modelos baseline (XGBoost) e consolida o Gradient Boosting vencedor.
   - Exporta artefatos para `ml/artifacts/` (modelo, pré-processador e CSVs de comparação como `comparacao_modelos_full.csv`).
3. **API REST** (`apps/api/`):
   - Montada com FastAPI.
   - Consome os artefatos finalizados (`modelo_definitivo.joblib` com Gradient Boosting + pré-processador).
   - Exponde `GET /`, `GET /health`, `POST /predict`, `GET /model-info` e `POST /api/v1/scrape/start`.
4. **Frontend** (`frontend/`):
   - Responsável pela interface com o botão “Especulai”.
   - Comunica-se com o backend via `predictImovel()` apontando para `VITE_API_URL`.

## Estrutura de Diretórios (detalhada)

```
especulai/
├── apps/
│   ├── __init__.py
│   ├── api/
│   │   ├── main.py
│   │   ├── routes/
│   │   ├── services/
│   │   └── models/
│   └── scraper/
├── frontend/                 # mantida sem alterações estruturais
├── ml/
│   ├── pipeline/train_model.py
│   └── artifacts/
│       ├── modelo_definitivo.joblib
│       └── comparacao_modelos_full.csv
├── notebooks/
├── docs/README.md
├── config/env.template
├── infra/redis/dump.rdb
├── requirements/
│   └── backend.txt
└── requirements.txt          # agrega os arquivos acima
```

## Instalação e Execução

### Pré-requisitos
- Python 3.10+
- Node 18+ (para o frontend)
- Docker e Docker Compose (para execução containerizada)

### Instalação Local

1. **Backend / Pipeline**
```bash
cd especulai
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements/backend.txt

# Pipeline / Treinamento
cd ml/pipeline
python pipeline_ml.py   # atualiza os CSVs em dados_imoveis_teresina/
python train_model.py   # treina o Gradient Boosting definitivo

# API
cd ../..
PYTHONPATH=%CD% uvicorn especulai.apps.api.main:app --reload
```

2. **Frontend**
```bash
cd especulai/frontend
npm install
npm run dev
```

### Execução com Docker

1. **Build e iniciar containers**:
```bash
docker compose up --build
```
2. **Acessar API**:
   - URL: http://localhost:8000
   - Documentação interativa: http://localhost:8000/docs

## Uso da API

### Exemplo de Requisição

```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "area": 85.0,
    "quartos": 3,
    "banheiros": 2,
    "tipo": "apartamento",
    "bairro": "Jardins",
    "cidade": "São Paulo"
  }'
```

### Exemplo de Resposta

```json
{
  "preco_estimado": 450000.00,
  "confianca": "alta"
}
```

## Tecnologias Utilizadas

- **Python 3.9**: Linguagem principal
- **FastAPI**: Framework web de alta performance
- **GradientBoostingRegressor**: Modelo de Machine Learning principal
- **Scikit-learn**: Pré-processamento e métricas
- **Pandas**: Manipulação de dados
- **BeautifulSoup**: Web scraping
- **Docker**: Containerização
- **Uvicorn**: Servidor ASGI

## Características Técnicas

### Performance
- Modelo Gradient Boosting otimizado para inferência rápida
- API assíncrona com FastAPI
- Pré-processamento eficiente com caching

### Robustez
- Validação de entrada com Pydantic
- Tratamento de erros em todos os componentes
- Health checks para monitoramento

### Escalabilidade
- Arquitetura de microserviços
- Containerização com Docker
- Stateless API para fácil replicação

## Métricas do Modelo

O modelo é avaliado usando:
- **MAE** (Mean Absolute Error): Erro médio em reais
- **RMSE** (Root Mean Squared Error): Raiz do erro quadrático médio
- **R²** (Coefficient of Determination): Qualidade do ajuste

## Segmentação de Datasets e Notebook Analítico

- O pipeline (`ml/pipeline/train_model.py`) gera automaticamente:
  - `dados_imoveis_teresina/dataset_treino_ml_v1.csv`: dataset completo (sem filtros).
  - `dados_imoveis_teresina/segmentos/dataset_*.csv`: versões segmentadas por fonte, tipo de negócio e combinações.
- Execute `python ml/pipeline/train_model.py` após coletar e enriquecer os dados para atualizar todos os arquivos.
- Utilize o notebook `notebooks/analise_modelos.ipynb` (compatível com Google Colab + GPU) para carregar cada dataset segmentado, treinar o mesmo modelo (XGBoost) e comparar métricas (RMSE e R²). As métricas consolidadas são salvas em `dados_imoveis_teresina/resultados_modelos.csv`.

## Melhorias Futuras

1. **Coleta de Dados**:
   - Implementar scraping de múltiplos sites
   - Adicionar agendamento automático de coletas

2. **Modelo**:
   - Experimentar ensemble de modelos
   - Implementar validação cruzada
   - Adicionar features geográficas (coordenadas)

3. **API**:
   - Adicionar autenticação
   - Implementar rate limiting
   - Cache de predições frequentes
   - Logging estruturado

4. **Infraestrutura**:
   - CI/CD pipeline
   - Monitoramento com Prometheus/Grafana
   - Deploy em cloud (AWS/GCP/Azure)

