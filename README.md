
<p align="center"> <img width="320" height="320" alt="logoEspeculai" src="https://github.com/user-attachments/assets/85cc721c-f969-4668-80d2-397bb0e079e7" />  </p>


# Especulai - Sistema de Estimativa de Preços de Imóveis

Sistema completo de Machine Learning para estimativa de preços de imóveis baseado em dados coletados da web. O projeto utiliza arquitetura de microserviços containerizada com Docker e prioriza velocidade de resposta ao usuário final.

## Arquitetura do Sistema

O projeto é dividido em três componentes principais:

### 1. Web Scraper (Coleta de Dados)
- **Arquivo**: `scraper/scrape_data.py`
- **Função**: Coleta dados de anúncios de imóveis
- **Dados coletados**: preço, área, quartos, banheiros, tipo, localização
- **Saída**: `data/imoveis_raw.csv`

### 2. Pipeline de ML (Treinamento)
- **Arquivo**: `ml_pipeline/train_model.py`
- **Função**: Processa dados e treina modelo LightGBM
- **Características**:
  - Limpeza e tratamento de outliers
  - Engenharia de features
  - Modelo LightGBM otimizado para velocidade
- **Saída**: `model.joblib` e `preprocessor.joblib`

### 3. API REST (Inferência)
- **Arquivo**: `api/main.py`
- **Framework**: FastAPI
- **Função**: Serve predições de preços em tempo real
- **Endpoints**:
  - `GET /` - Health check
  - `GET /health` - Status detalhado
  - `POST /predict` - Predição de preço
  - `GET /model-info` - Informações do modelo

## Estrutura de Diretórios

```
especulai_project/
├── api/
│   ├── main.py              # API FastAPI
│   └── Dockerfile           # Container da API
├── ml_pipeline/
│   ├── train_model.py       # Pipeline de treinamento
│   ├── model.joblib         # Modelo treinado (gerado)
│   └── preprocessor.joblib  # Pré-processadores (gerado)
├── scraper/
│   └── scrape_data.py       # Script de coleta de dados
├── data/
│   └── imoveis_raw.csv      # Dados coletados (gerado)
├── requirements.txt         # Dependências Python
└── docker-compose.yml       # Orquestração de containers
```

## Instalação e Execução

### Pré-requisitos
- Python 3.9+
- Docker e Docker Compose (para execução containerizada)

### Instalação Local

1. **Instalar dependências**:
```bash
pip install -r requirements.txt
```

2. **Executar coleta de dados**:
```bash
cd scraper
python scrape_data.py
```

3. **Treinar modelo**:
```bash
cd ml_pipeline
python train_model.py
```

4. **Executar API**:
```bash
cd api
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Execução com Docker

1. **Build e iniciar containers**:
```bash
docker-compose up --build
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
- **LightGBM**: Modelo de Machine Learning otimizado
- **Scikit-learn**: Pré-processamento e métricas
- **Pandas**: Manipulação de dados
- **BeautifulSoup**: Web scraping
- **Docker**: Containerização
- **Uvicorn**: Servidor ASGI

## Características Técnicas

### Performance
- Modelo LightGBM otimizado para inferência rápida
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

## Melhorias Futuras

1. **Coleta de Dados**:
   - Implementar scraping real de múltiplos sites
   - Adicionar agendamento automático de coletas
   - Expandir dados coletados (garagem, elevador, etc.)

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

