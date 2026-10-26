# Relatório da recoleta — VivaReal e Chaves na Mão

> Coleta de 2026-10-24/25. Objetivo: reconstruir a cadeia bruta perdida (P27) e dar
> volume ao modelo de aluguel. **O aluguel residencial utilizável foi de 137 para 1.481
> imóveis distintos (11×). Na venda o ganho de volume é de 15% a 39%, conforme a régua. A
> acurácia na validação praticamente não mudou.** Falta o campo "mobiliado", e o modelo
> ainda não foi avaliado no conjunto de teste.

---

## 1. Escolha das fontes

| Fonte | Resposta a cliente HTTP | Estoque em Teresina | Situação |
|---|---|---|---|
| OLX | 403 Cloudflare, também com Chromium via Playwright | — | descartada |
| **VivaReal** | 200, dados no card | 6.503 venda, 3.735 aluguel | coletada |
| **Chaves na Mão** | 200, dados em JSON-LD | 1.542 venda, 1.169 aluguel | coletada |
| ZAP Imóveis | 200 | 6.489 venda, 3.729 aluguel | não coletada: mesmo grupo e estoque do VivaReal |
| Imovelweb, Mercado Livre, QuintoAndar, Wimoveis | bloqueio, captcha ou sem anúncios | — | descartadas |

A OLX foi tentada uma vez com navegador real em modo normal. Ao ser barrada, a tentativa
parou ali, sem recorrer a modos de evasão do Cloudflare.

**Ferramentas e bases públicas.** Firecrawl e os scrapers do Apify não trazem nada que o
coletor próprio não faça: os portais coletados já respondem a requisições comuns. O modo
anti-bloqueio do Firecrawl custa 5 créditos por página e só serviria para sites bloqueados.
O GitHub e o Hugging Face não têm bases de Teresina; os datasets do Kaggle são
majoritariamente de São Paulo, e o de aluguel nacional é de 2020, defasado (o FipeZap mostra
o aluguel de Teresina subindo ~22% em 2025). Uma pista a explorar é o Observatório do
Mercado Imobiliário (OMI) da Prefeitura, que reúne dados de ITBI; não encontrei base aberta,
só um caminho via Lei de Acesso à Informação.

## 2. Os coletores

| | `scraper_vivareal.py` | `scraper_chaves.py` |
|---|---|---|
| Origem dos dados | card HTML; tipo, área, quartos e preço vêm do slug da URL | JSON-LD `RealEstateListing` |
| Paginação | `?pagina=N`, 30 por página, **teto na página 50** | `?pg=N`, 15 por página, **teto na página 99** (403 na 100) |
| Passar do teto | fatiar por tipo residencial e, se bater o teto, por bairro | não foi necessário no aluguel; faltam ~57 de venda |
| Exclusivo | condomínio, IPTU, vagas | rua com número, CEP, coordenadas, anunciante |
| Ausente | suítes, CEP, descrição, mobiliado, andar | condomínio, IPTU, vagas |

Ambos são incrementais (ID já gravado é pulado) e gravam uma linha por página. No Chaves,
a área do slug às vezes difere do `floorSize`; o `floorSize` vai em `Area_m2` e a do slug em
`Area_slug_m2`, para auditoria.

Um defeito encontrado e corrigido: o Chaves rotula `Casa Em Condominio`, e o mapa de tipos só
conhecia `Casa de Condomínio`. Com isso 147 casas residenciais estavam sendo descartadas.

## 3. Resultado

### Bruto e corpus residencial

| | Bruto VivaReal | Bruto Chaves | Corpus (anúncios) | Imóveis distintos* |
|---|---:|---:|---:|---:|
| Aluguel | 2.086 | 1.169 | 1.898 | **1.481** |
| Venda | 4.902 | 1.534 | 5.945 | **4.485** |

O corpus mantém só residencial, com área, preço dentro de faixas plausíveis (aluguel de
R$ 300 a 25.000, venda de R$ 50 mil a 15 mi) e bairro. O resto do bruto é comercial,
terreno e dados incompletos.
\* Grupos de `unificar.py`: anúncios do mesmo imóvel, ou de unidades muito parecidas do mesmo
prédio, contam uma vez (ver seção 5).

### Composição por fonte

| | só VivaReal | só Chaves | nas duas |
|---|---:|---:|---:|
| Aluguel (grupos) | 1.099 | 155 | 227 |
| Venda (grupos) | 3.444 | 542 | 499 |

60% dos anúncios de aluguel do Chaves e 54% dos de venda caem em grupos que também têm
VivaReal. Conferi seis pares à mão e todos são o mesmo imóvel. Isso não mede a precisão das
regras em geral.

### Completude por fonte (corpus residencial)

| Campo | VivaReal | Chaves |
|---|---:|---:|
| Área, quartos, banheiros | 100% | 100% |
| Vagas | 90% | 0% |
| Condomínio | 52% | 0% |
| IPTU | 20% | 0% |
| Rua | 74% (sem número) | 81% (com número) |
| CEP, anunciante | 0% | 100% |
| Latitude, longitude válidas | 0% | 82% |

Quando o anunciante omite o endereço, o Chaves grava a rua como "não disponível" e a coordenada
como 0,0: são 291 dos 1.575 anúncios (18%). Uma versão anterior deste relatório contava esses
casos como preenchidos (100%).

**Precisão das coordenadas válidas** (1.284 anúncios, 102 bairros): a coordenada é a do
logradouro ou CEP, não a do imóvel. Cada CEP tem um único ponto (mediana), e 74% dos pontos
aparecem em um só anúncio. A distância até a mediana do bairro tem mediana de 0,49 km e P90 de
1,35 km. No mesmo endereço com número, a dispersão tem mediana zero e P90 de 0,6 km, mas há
casos de até 10 km, então existem coordenadas erradas. Serve como localização em nível de rua
(~500 m), com cauda de outliers que pede filtro.

## 4. Comparativo

### Aluguel residencial

| | Rocha & Rocha (doc de aluguel) | VivaReal + Chaves | Meta |
|---|---:|---:|---:|
| Imóveis distintos utilizáveis | 137 | **1.481** | 1.200–1.800 |
| Bairros com ≥ 5 anúncios | 7 | **65** | — |
| Bairros com ≥ 20 anúncios | — | 28 | — |

### Venda residencial: dataset antigo × corpus novo

O dataset antigo (OLX) tem cópias do mesmo imóvel (5.644 linhas, 4.614 URLs). Comparar linhas
brutas é enganoso; a régua justa conta imóveis distintos pela mesma chave (bairro, área,
quartos, banheiros) nos dois lados:

| | Antigo (OLX) | VivaReal | VivaReal + Chaves |
|---|---:|---:|---:|
| Linhas | 5.625 | 4.748 | 5.945 |
| Imóveis distintos (chave grossa) | 2.774 | 3.453 | **3.879** |
| Variação sobre o antigo | — | +24% | **+40%** |
| Mediana de valor | R$ 430.000 | — | R$ 450.000 |
| Mediana de R$/m² | 4.902 | — | 4.737 |
| `Tipo_Imovel` | **ausente** | presente | presente |

A chave grossa pode juntar imóveis diferentes de mesma metragem; ela subestima os dois lados.
A cauda cara cresceu: imóveis acima de R$ 1,5 mi eram 2,8% do antigo e são 11,5% do VivaReal,
então as métricas dos dois datasets não são comparáveis entre si.

### Validação cruzada com o FipeZap (aluguel)

O FipeZap dá o aluguel de Teresina em R$ 26,62/m² (dez/2025). A mediana do corpus é R$ 25,7/m².
Por bairro, a mediana do VivaReal ficou em: Jóquei 37,8 (FipeZap 41,0), São Cristóvão 41,0
(39,6) e Planalto 41,5 (32,7). O desvio do Planalto tem explicação de composição: 15 dos 43
anúncios têm até 30 m² e mediana de R$ 92/m², e vários são studios do mesmo prédio. Nenhuma
estatística minha reproduz os três bairros ao mesmo tempo, e o método do FipeZap não é público.
Serve como checagem de plausibilidade, não como prova.

## 5. Deduplicação e split

`ml/pipeline/unificar.py` agrupa anúncios do mesmo imóvel (`ID_Grupo`) dentro de blocos de
negócio, tipo e bairro (grafia unificada). Dois níveis de pareamento:

- **Certo:** rua parecida (≥ 0,75), número igual quando os dois têm, área ±2%, quartos e
  banheiros iguais, preço ±10%.
- **Provável:** sem rua em um dos lados, área ±0,5% e preço ±5%.

Defeito corrigido em 2026-10-25: o texto "não disponível" do Chaves era tratado como nome de
rua, e 292 anúncios eram comparados entre si pela regra "certa", mais frouxa. Agora o marcador
vale como ausência de rua. Os grupos passaram de 1.580 para 1.481 (aluguel) e de 4.543 para
4.465 (venda), e o split foi regenerado. O teste nunca tinha sido aberto, então a troca não
contamina nada.

Os anúncios **não são apagados**: recebem o mesmo grupo, e o split é feito por grupo. O
agrupamento é transitivo e junta demais: os maiores grupos (até 26 anúncios) são unidades
diferentes do mesmo prédio. Isso é seguro para o split (unidades do mesmo prédio têm preço/m²
correlacionado), mas **o grupo não serve para colapsar linhas**. Foram 2.283 pares certos e
927 prováveis; os limiares são julgamento meu, sem medição de precisão. Uma amostra de 50
pares por nível está em `data/splits/amostra_pares.csv`.

Split 70/15/15 por grupo, estratificado por faixa de preço, semente 42, separado para venda e
aluguel:

| | Treino | Validação | Teste |
|---|---:|---:|---:|
| Venda (anúncios) | 4.183 | 874 | 888 |
| Aluguel (anúncios) | 1.347 | 275 | 276 |

O teste nunca foi aberto. O split foi regenerado duas vezes, quando o Chaves entrou e quando
corrigi o marcador "não disponível"; a partir daqui fica congelado.

## 6. Primeiro experimento (só na validação)

`GradientBoostingRegressor(200, 0.1, 5)` com área, quartos, banheiros, vagas, tipo e bairro,
alvo em log do preço, sem geografia.

| | R² | R² em log | MdAPE | dentro de ±20% |
|---|---:|---:|---:|---:|
| Venda, split só VivaReal | 0,652 | 0,801 | 21,2% | 46,9% |
| **Venda, split atual** | 0,700 | 0,810 | 21,2% | 46,7% |
| Aluguel, split só VivaReal | 0,534 | 0,682 | 25,2% | 42,5% |
| **Aluguel, split atual** | 0,602 | 0,675 | 25,1% | 40,7% |

O R² em reais variou entre 0,65 e 0,78 na venda só por troca de split (0,652, 0,778, 0,739, 0,700),
então **não serve para comparar**: ele é dominado pelos valores extremos. O R² em log e o MdAPE ficaram praticamente estáveis. Condomínio não mostra ganho
claro. Por fonte, o modelo erra mais no Chaves na venda (MdAPE 21,9% contra 20,0%, com 160
anúncios); no aluguel também (27,9% contra 24,1%, com 59). Os tamanhos não sustentam conclusão.

## 7. Lacunas e riscos

1. **Mobiliado só existe para o VivaReal** (seção 9). No Chaves não há campo e a descrição o
   menciona em ~7% dos anúncios, então ele ficou de fora. No VivaReal, 26% dos anúncios de
   aluguel não têm lista de comodidades, e a ausência da comodidade foi lida como "não
   mobiliado", o que supõe que o anunciante a marca quando existe.
2. **IPTU quase vazio** no VivaReal (20%) e com erros de digitação. Provavelmente não serve.
3. **Vagas ausentes são ambíguas.** No VivaReal a ausência pode ser "sem vaga"; no Chaves o
   campo nunca existe. O baseline trata as duas coisas com um indicador.
4. **Coordenadas do Chaves em nível de rua**, ausentes em 18% e com outliers (seção 3).
5. **Precisão das regras de deduplicação não medida**, só amostrada à mão em seis pares.
6. **~8 anúncios de venda do Chaves** ainda faltam. O fatiamento por tipo (`--fatiado`) recuperou 49
   dos ~57 que ficavam além da página 99.
7. **Preço de anúncio, não de transação.** A margem de negociação entra como ruído.
8. **Teste de aluguel pequeno** (276 anúncios, ~223 imóveis): qualquer métrica terá incerteza
   grande.

## 8. Geografia com as coordenadas do Chaves

`ml/experiments/geografia_chaves.py`: só anúncios do Chaves com coordenada válida e a até 5 km
da mediana do bairro, validação cruzada agrupada em 5 partes sobre treino e validação (teste
fechado), média de 3 sementes. Bairro contra bairro + latitude, longitude e distância ao centro:

| | n | R² em log, bairro | com geografia | MdAPE, bairro | com geografia |
|---|---:|---:|---:|---:|---:|
| Venda | 865 | 0,713 | 0,723 | 22,3% | 21,9% |
| Aluguel | 248 | 0,540 | 0,559 | 27,9% | 25,6% |

Os ganhos (+0,010 e +0,019) são pequenos. Numa rodada anterior, com 830 anúncios de venda,
a diferença foi −0,011, ou seja, muda de sinal com 35 anúncios a mais. É ruído, e a conclusão
da investigação original se mantém: além do bairro, a localização em nível de rua não ajuda
com esta amostra.

## 9. Mobiliado (aluguel, VivaReal)

`apps/scraper/detalhes_aluguel.py` lê a lista de comodidades da página de detalhe e grava
`data/detalhes_aluguel.csv` (1.471 anúncios, sem 429 depois que o intervalo passou para 6–10 s e o
coletor passou a obedecer `Retry-After`). Dos 1.087 anúncios com lista, 15% são mobiliados.

| | mediana R$/m² |
|---|---:|
| Mobiliado | 40,4 |
| Não mobiliado | 25,3 |

`ml/experiments/mobiliado_aluguel.py`, mesmo GBR do baseline, sem abrir o teste:

| | R² em log | MdAPE |
|---|---:|---:|
| Validação (159 anúncios), sem mobiliado | 0,628 | 24,0% |
| Validação, com mobiliado | 0,638 | 24,9% |
| CV agrupada (930 anúncios), sem mobiliado | 0,682 | — |
| CV agrupada, com mobiliado | **0,705** | — |

O ganho é de +0,01 a +0,02 de R² em log, e o MdAPE não melhora na validação (n pequeno). O prêmio
bruto de 60% no R$/m² é em boa parte composição: imóveis mobiliados tendem a ser menores
(studios, kitnets), e a área já está no modelo. Não é o efeito que o doc de aluguel imaginava
(causa do R² negativo anterior), mas a direção é consistente. O campo entra, com o aviso de que
vale só para o VivaReal.

## 10. Outliers e intervalos (só treino e validação)

`ml/experiments/intervalos_outliers.py`. Os resíduos em log vêm de validação cruzada agrupada no
treino. Um anúncio é "outlier" se o resíduo passa de 3,5 desvios robustos (MAD).

**Outliers.** Venda: 36 de 4.183 (MAD 0,32). Aluguel: 10 de 1.347 (MAD 0,36). Tirá-los do treino:

| | R² (reais) | R² em log | MdAPE |
|---|---:|---:|---:|
| Venda, todos | 0,700 | 0,810 | 21,2% |
| Venda, sem outliers | 0,678 | 0,804 | 22,0% |
| Aluguel, todos | 0,602 | 0,675 | 25,1% |
| Aluguel, sem outliers | 0,627 | 0,681 | 23,6% |

Na venda, a limpeza **piora** um pouco. No aluguel melhora, mas com 10 anúncios removidos e uma
validação de 275, a diferença está no ruído. Os marcados são em boa parte casas grandes de preço
alto, imóveis legítimos, mais alguns suspeitos (casa de 229 m² a R$ 80 mil, kitnet de 70 m² a
R$ 60 mil). **Decisão:** não remover automaticamente. O limiar de 3,5 MAD serve para *sinalizar*
anúncios a revisar; o intervalo conformal já absorve o ruído sem apagar a cauda cara.

**Intervalos conformais** (meia-largura em log = quantil dos |resíduos| de treino). Cobertura na
validação:

| Nível | Venda observada | Aluguel observada | Fator multiplicativo (venda / aluguel) |
|---|---:|---:|---:|
| 50% | 47,7% | 46,9% | ×/÷ 1,24 / 1,27 |
| 80% | 80,1% | 79,3% | ×/÷ 1,52 / 1,64 |
| 90% | 91,0% | 89,5% | ×/÷ 1,79 / 1,99 |

A cobertura global bate com o nível nominal nos dois modelos. **Não é uniforme:** no nível de 80%,
o terço de imóveis mais caros fica com 75% (venda) e 73% (aluguel), e o mais barato com 89% e 84%.
Ou seja, o intervalo é largo demais para os baratos e estreito para os caros, que é a regressão à
média (P18) aparecendo na faixa. Em reais, um imóvel previsto em R$ 450 mil tem intervalo de 80% de
cerca de R$ 296 mil a R$ 684 mil. É isto que o usuário precisa ver, e não um número único.

Para publicar, o intervalo deve ser **por faixa de preço previsto** (conformal normalizado ou por
terço), e não um fator único.

## 11. Próximos passos

1. Renda do IBGE por bairro (P19): exige baixar a malha de setores e os agregados do Censo 2022
   para `data/ibge/`, que não estão no disco. A VivaReal não tem coordenada, então a junção seria
   pelo nome oficial do bairro.
2. Pedido via LAI ao OMI de Teresina por dados de transação.
3. Só então abrir o teste, uma vez, no modelo final.

## Reprodução

```bash
uv sync --extra pipeline   # requests e beautifulsoup4 ficam neste extra
uv run python -m apps.scraper.scraper_vivareal --paginas-alugar 50 --paginas-comprar 50
uv run python -m apps.scraper.scraper_vivareal --fatiado alugar --fatiado comprar
uv run python -m apps.scraper.scraper_chaves --alugar --comprar
uv run python -m apps.scraper.scraper_chaves --fatiado    # venda por tipo, passa do teto de 99 páginas
uv run python -m ml.pipeline.unificar
uv run python -m ml.experiments.baseline_atributos
```

A coleta de topo do VivaReal (primeira linha) vem antes da fatiada; as duas são incrementais.
Recoletar não reproduz exatamente o bruto versionado, porque o estoque dos portais muda;
`unificar` e o baseline, sim, reproduzem os números deste relatório a partir dele.
