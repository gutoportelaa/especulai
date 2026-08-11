# Modelo de aluguel — viabilidade e plano

> Medido em 2026-08-11. A pergunta era: dá para prever aluguel de forma
> independente do modelo de venda? **Arquitetura: sim, e é barato. Dado: ainda
> não, e falta cerca de 10×.**

---

## 1. Por que dois modelos, e não um só com uma flag

A tentação é adicionar `Tipo_Negocio` como feature e treinar um regressor só.
Não funciona, e o motivo é aritmético: no Rocha & Rocha a venda tem mediana de
**R$ 360.000** e o aluguel, **R$ 1.500/mês** — três ordens de grandeza.

Um `GradientBoostingRegressor` minimiza erro quadrático sobre o alvo. Errar 10%
num imóvel de R$ 400 mil custa 40.000; errar 10% num aluguel de R$ 1.500 custa
150. O gradiente é dominado pela venda em todos os splits, e o ramo de aluguel
vira ruído de arredondamento. Transformar em log ajuda na escala mas não resolve
o resto: aluguel e venda respondem a fatores diferentes (mobília, condomínio
incluso, prazo de contrato) que o dataset de venda nem coleta.

**Decisão: dois artefatos independentes.** Mesmo pipeline de features, mesmo
código de treino, alvos e amostras separados.

## 2. Onde a arquitetura atual ajuda

O modelo já roda no navegador como JSON estático, então um segundo modelo é
quase de graça:

```
ml/pipeline/export_web.py  →  frontend/public/model/especulai.json         (venda)
                           →  frontend/public/model/especulai-aluguel.json (aluguel)
```

`model.js` já carrega o JSON sob demanda e memoriza. Servir dois é trocar a
constante por um parâmetro — o usuário só baixa o modelo que pedir. Não há
servidor, então não há custo por endpoint novo.

Na interface, um alternador **Venda | Aluguel** acima do formulário. Os campos
são os mesmos; muda o modelo carregado, o rótulo do resultado
(`Preço de Venda Estimado` → `Aluguel Mensal Estimado`) e a formatação (`/mês`).

## 3. O dado que existe hoje não sustenta

Coleta atual do Rocha & Rocha: **467 anúncios de aluguel**. Depois de filtrar,
sobra pouco:

| Etapa | Restam |
|---|---:|
| Aluguéis brutos | 467 |
| Com área e valor preenchidos | 271 |
| **Residenciais** (Apartamento, Casa, Flat) | **157** |
| Após dedup e faixa plausível (R$ 300–25.000) | **137** |

O funil é brutal por uma razão que não era óbvia: **o aluguel nesse site é
majoritariamente comercial.**

| Tipo | n |
|---|---:|
| Sala | 139 |
| Terreno | 97 |
| Apartamento | 94 |
| Casa | 62 |
| Loja | 43 |
| Ponto | 23 |
| Galpão | 6 |

Comercial + terreno somam **308 dos 467**. Sala comercial e apartamento não
pertencem ao mesmo modelo.

### O que 137 anúncios produzem

Protocolo idêntico ao de venda (`GroupShuffleSplit`, `GradientBoosting(200, 0.1, 5)`):

| Modelo | n treino | features | R² teste | MdAPE |
|---|---:|---:|---:|---:|
| base + bairro + tipo | 102 | 64 | **−0,191** | 48,2% |
| + POIs reais do OSM | 102 | 96 | **−0,208** | 43,8% |
| *baseline: chutar a mediana* | — | — | −0,334 | 48,1% |

**R² negativo.** O modelo empata com chutar a mediana (MdAPE 48,2% contra 48,1%)
e as features não agregam nada. Publicar isso seria vender ruído com uma casa
decimal.

Só 7 bairros têm 5 ou mais anúncios, contra 110 bairros no modelo de venda — o
one-hot de bairro, que é o principal preditor na venda, não tem onde se apoiar.

## 4. Quanto dado seria preciso

Curva de aprendizado do modelo de venda, conjunto de teste fixo em 920 imóveis,
média de 5 amostragens por ponto:

| n treino | R² teste | MdAPE |
|---:|---:|---:|
| 100 | 0,388 | 26,2% |
| 200 | 0,490 | 25,1% |
| 400 | 0,572 | 20,7% |
| 800 | 0,641 | 19,4% |
| 1.200 | 0,698 | 18,7% |
| 1.800 | 0,723 | 18,6% |
| 2.500 | 0,726 | 18,7% |
| 3.677 | 0,741 | 18,7% |

O ganho satura perto de **n = 1.800**; de 1.800 para 3.677 rende 2 pontos de R².

**Meta para o aluguel: 1.200–1.800 anúncios residenciais**, contra os 137 de
hoje — cerca de **10× mais**. Dado que ~1/3 dos aluguéis coletados são
residenciais utilizáveis, isso significa coletar algo entre **4.000 e 5.500
anúncios de aluguel brutos**.

> **Ressalva:** a curva vem da venda e é usada como proxy. O aluguel pode exigir
> mais, e há razão para suspeitar que exija: nos mesmos ~137 anúncios o modelo
> de aluguel foi a R² −0,19, enquanto a curva de venda em n=137 sugeriria ~0,42.
> A diferença provável está em variância não observada — mobiliado ou não,
> condomínio e IPTU inclusos ou não. Nada disso é coletado hoje.

## 5. Plano de execução

1. **Coletar volume de aluguel.** A OLX é a fonte de escala e o scraper já
   pagina aluguel por padrão (`num_pages_aluguel`). Alvo: 4.000+ anúncios brutos.
2. **Capturar os campos que faltam** na coleta: mobiliado (sim/não), condomínio
   e IPTU inclusos, valor do condomínio. São eles que explicam boa parte dos 48%
   de MdAPE atuais.
3. **Separar residencial de comercial** já no preparo. Sala, Loja, Ponto, Galpão
   e Terreno saem — ou viram um terceiro modelo, se houver volume.
4. **Reaproveitar `train_model.py`** com `TARGET_COLUMN` e faixa de preço
   parametrizados. O piso de R$ 50.000 vira teto de R$ 25.000 no aluguel.
5. **Exportar como segundo JSON** e ligar o alternador na interface.
6. **Recalibrar a régua de confiança.** Os cortes atuais (área 20–1000 m²,
   bairro com perfil) foram escolhidos para venda.

Só ligar a interface depois que o R² de teste passar de ~0,55 num split por
grupo. Abaixo disso, o número na tela engana mais do que informa.

## Reprodução

```bash
uv run python -m ml.experiments.comparar_fontes   # venda: OLX vs Rocha
```

Os números de aluguel e a curva de aprendizado desta página saíram de scripts
exploratórios da sessão de 2026-08-11, sobre `data/enriched_rocha_full.csv` e
`data/dataset_treino_olx_final.csv`.
