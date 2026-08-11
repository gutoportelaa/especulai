---
title: Especulai API
emoji: 🏘️
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Estimativa de preços de imóveis em Teresina (PI)
---

# Especulai — API

Estimativa de preços de imóveis em Teresina (PI) por Machine Learning.
Código-fonte: [github.com/gutoportelaa/especulai](https://github.com/gutoportelaa/especulai)

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/health` | Health check; informa se o modelo carregou |
| `POST` | `/predict` | Estimativa de preço |
| `GET` | `/docs` | OpenAPI interativo |

```bash
curl -X POST https://gutoportelaa-especulai-api.hf.space/predict \
  -H 'Content-Type: application/json' \
  -d '{"area":90,"quartos":3,"banheiros":2,"tipo":"apartamento","bairro":"Fátima","cidade":"Teresina"}'
```

```json
{ "preco_estimado": 420000.0, "confianca": "alta" }
```

Os endpoints de pipeline (`/api/v1/pipeline/*`) e de scraping não são montados
em produção — respondem 404 de propósito.

## Modelo

`GradientBoostingRegressor` treinado sobre anúncios coletados em Teresina.

- **R² (teste, por grupo): 0,684** — número real, depois de corrigir vazamento
  de alvo e duplicatas no split.
- Viés conhecido por faixa: superestima ~28% abaixo de R$250k e subestima ~27%
  acima de R$1,2M. Regressão à média — não use nos extremos.
- O alvo é **preço de anúncio**, não preço de transação. O ITBI de Teresina é
  fechado, então não há como calibrar contra valor negociado.

Estimativa para fins informativos e de pesquisa. Não é laudo de avaliação e não
atende à NBR 14653-2.
