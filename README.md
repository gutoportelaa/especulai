<p align="center">
  <img width="160" height="160" alt="Especulai" src="https://github.com/user-attachments/assets/85cc721c-f969-4668-80d2-397bb0e079e7" />
</p>

<h1 align="center">Especulai</h1>

<p align="center">
  <strong>Faixa de preço de <em>venda</em> e <em>aluguel</em> de imóveis em Teresina (PI) com Machine Learning.</strong><br>
  Do scraping à API de inferência (Cloudflare Workers), com os pesos do modelo cifrados.
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white">
  <img alt="Cloudflare Workers" src="https://img.shields.io/badge/Cloudflare-Workers-F38020?logo=cloudflare&logoColor=white">
  <img alt="scikit-learn" src="https://img.shields.io/badge/scikit--learn-1.5-F7931E?logo=scikitlearn&logoColor=white">
  <img alt="React" src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black">
  <img alt="Vite" src="https://img.shields.io/badge/Vite-5-646CFF?logo=vite&logoColor=white">
  <img alt="AES-256-GCM" src="https://img.shields.io/badge/pesos-AES--256--GCM-222">
</p>

---

## O problema

Quem anuncia ou aluga um imóvel em Teresina não tem uma referência objetiva de preço. Os anúncios
são a única fonte pública, e eles refletem a expectativa de quem anuncia, não o preço de fechamento.

O Especulai coleta esses anúncios de dois portais, junta renda e densidade dos bairros (Censo 2022
do IBGE) e treina dois modelos, um para venda e outro para aluguel. A saída é uma **faixa** com 80%
de chance de conter o preço anunciado, e um nível de confiança que diz o quanto o modelo conhece
aquele bairro.

**Entrada:** negócio, área, quartos, banheiros, vagas (opcional), tipo, bairro
**Saída:** faixa de preço, estimativa central e confiança (alta, média ou baixa)

> O alvo é o **preço pedido**. Não é avaliação nem laudo.

---

## Resultados (teste, aberto uma única vez)

| | Venda (887 anúncios) | Aluguel (276 anúncios) |
|---|---:|---:|
| R² em log | 0,832 | 0,622 |
| Erro mediano (MdAPE) | 21,1% | 24,4% |
| Estimativa central a ±20% do pedido | 48,6% | 42,8% |
| Cobertura da faixa de 80% | 81,4% | 80,1% |
| Limite superior ÷ inferior da faixa | 2,28× | 2,61× |

Menos da metade dos anúncios cai a ±20% da estimativa central, e por isso o produto é a faixa.
A largura é calibrada por terço de preço previsto: uma largura única cobria bem no total, mas
sub-cobria o terço caro (75% em vez de 80%). A metodologia completa, com o que foi testado e
descartado, está em [`docs/relatorio-coleta.md`](docs/relatorio-coleta.md).

### O que ajudou e o que não ajudou

| Hipótese | Resultado |
|---|---|
| Renda e densidade do bairro (IBGE) | **Ganho consistente**, maior em bairros com poucos anúncios |
| Coordenadas de rua além do bairro | Sem ganho: o bairro já carrega a localização |
| Remover outliers do treino | Piora a venda: só sinalizar |
| Campo "mobiliado" (aluguel) | Ganho pequeno, só em um portal: fora do modelo |

### Limitações

- Um único mês de coleta, sem sazonalidade; só Teresina; só imóveis residenciais.
- Aluguel tem 1.898 anúncios: o R² do teste ficou abaixo da validação (0,622 contra 0,698), dentro
  do ruído de 276 anúncios.
- Sem dados de transação. Um pedido de acesso à informação ao município (ITBI) está em andamento.

---

## Arquitetura

```
 VivaReal + Chaves ─► coleta ─► unificar (dedup por grupo, split 70/15/15)
                                      │
 Censo 2022 (bairro) ─────────────────┤
                                      ▼
                       treino_final ─► final_{venda,aluguel}.joblib ─ não versionado
                                      │
                         export_web ──┴─► pesos em JSON (claro, não versionado)
                                      │
                       cifrar_modelo ─► deploy/space/modelo.enc  (AES-256-GCM)
                                      │
                       API de inferência (Cloudflare Worker) ◄─ MODEL_KEY (segredo)
                                      ▲
                      Site estático (React) ── POST /estimar ──┘
```

### Proteção dos pesos

O navegador precisa da chave para calcular, então cifrar o modelo **dentro do site** não protege
nada. A proteção está em não enviar o modelo ao cliente:

- **Em repouso:** `venda.enc` e `aluguel.enc` (~200 KB cada) são os modelos cifrados com
  AES-256-GCM. Sem a chave são indistinguíveis de bytes aleatórios, e qualquer alteração é detectada.
- **Chave fora do código:** `MODEL_KEY` é segredo do Worker. Local, fica em
  `~/especulai-dados-privados/modelo.key` (permissão 600).
- **Em uso:** os pesos só existem em claro na memória do isolate. Com a chave ausente ou errada,
  `/saude` responde 503 e `/estimar` nunca devolve o motivo do erro.
- **Contra extração por consulta:** a API devolve só a faixa, arredondada; valida as entradas;
  limita 20 consultas por minuto e 200 por hora por IP, e 3.000 por hora no total (Durable Object,
  pelo IP que o Cloudflare informa; se o limitador cair, a API recusa em vez de liberar).
- **Limite honesto:** quem puder consultar muito consegue aproximar o comportamento do modelo. O
  limite de taxa encarece isso; não elimina.
- **Trava no git:** o hook de pré-commit bloqueia pesos em claro e dados brutos de portais.

### Dados

Os dados brutos têm nome de anunciante e endereço, e **não são publicados**. Ficam num dataset
privado fora do GitHub. Ver [`docs/dados-sensiveis.md`](docs/dados-sensiveis.md).

---

## Começando

**Pré-requisitos:** Python 3.11+, [uv](https://docs.astral.sh/uv/), [bun](https://bun.sh), Node 22+ (para o `wrangler`)

```bash
git clone https://github.com/gutoportelaa/especulai.git
cd especulai
git config core.hooksPath .githooks     # ativa a trava de pré-commit

make install-dev
make web-install
```

Os dados brutos e a chave de cifragem não vêm no clone. Sem eles você roda o site e os testes que
não dependem do modelo; para reproduzir o treino, peça acesso ao dataset privado.

```bash
make api-inferencia     # Worker local em http://localhost:8787 (precisa da chave em ~/especulai-dados-privados/)
make web-dev            # site em http://localhost:5173 (VITE_API_URL=http://localhost:8787)
make test               # paridade treino ↔ sklearn e cifragem (Python)
make test-worker        # paridade do Worker, validação, limite de consultas, CORS (bun)
```

### Retreinar e reimplantar

```bash
uv run python -m ml.pipeline.unificar
uv run python -m ml.pipeline.treino_final     # sem --abrir-teste: o teste já foi aberto
make cifrar-modelo                            # gera deploy/space/modelo.enc
```

Commite os `.enc` e publique com `make deploy-api` (antes: `wrangler login` e
`wrangler secret put MODEL_KEY`, ver [`deploy/worker/README.md`](deploy/worker/README.md)).
Defina a variável `API_URL` do repositório (Settings, Actions, Variables) com a URL do Worker: o
workflow do site falha de propósito sem ela, para não publicar uma página apontando para `localhost`.

---

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `apps/scraper/` | coletores (VivaReal, Chaves na Mão) com atraso e respeito a `Retry-After` |
| `ml/pipeline/` | `unificar`, `treino_final`, `export_web`, `cifrar_modelo` |
| `ml/experiments/` | experimentos medidos só em treino e validação |
| `deploy/worker/` | API de inferência (Cloudflare Worker, JS, sem sklearn) e os modelos cifrados |
| `frontend/` | site React estático |
| `docs/` | relatório da coleta e dos experimentos, política de dados |
| `tests/` | paridade com o sklearn e cifragem (Python); o Worker tem testes em `deploy/worker/test/` |

> `apps/api/` e `ml/pipeline/orchestrator.py` são a versão antiga do projeto, com o modelo da OLX,
> e não fazem parte do fluxo atual.
