# Relatório da recoleta — VivaReal e Chaves na Mão

> Coleta de 2026-10-24/25. Objetivo: reconstruir a cadeia bruta perdida (P27) e dar
> volume ao modelo de aluguel. **O aluguel residencial utilizável foi de 137 para 1.580
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
| Aluguel | 2.086 | 1.169 | 1.898 | **1.580** |
| Venda | 4.902 | 1.485 | 5.897 | **4.543** |

O corpus mantém só residencial, com área, preço dentro de faixas plausíveis (aluguel de
R$ 300 a 25.000, venda de R$ 50 mil a 15 mi) e bairro. O resto do bruto é comercial,
terreno e dados incompletos.
\* Grupos de `unificar.py`: anúncios do mesmo imóvel, ou de unidades muito parecidas do mesmo
prédio, contam uma vez (ver seção 5).

### Composição por fonte

| | só VivaReal | só Chaves | nas duas |
|---|---:|---:|---:|
| Aluguel (grupos) | 1.188 | 252 | 140 |
| Venda (grupos) | 3.529 | 596 | 418 |

37% dos anúncios de aluguel do Chaves e 46% dos de venda caem em grupos que também têm
VivaReal. Conferi seis pares à mão e todos são o mesmo imóvel. Isso não mede a precisão das
regras em geral.

### Completude por fonte (corpus residencial)

| Campo | VivaReal | Chaves |
|---|---:|---:|
| Área, quartos, banheiros | 100% | 100% |
| Vagas | 90% | 0% |
| Condomínio | 52% | 0% |
| IPTU | 20% | 0% |
| Rua | 74% (sem número) | 100% (com número) |
| CEP, latitude, longitude, anunciante | 0% | 100% |

As coordenadas do Chaves têm 871 valores distintos em 1.575 anúncios (55%). A repetição indica
geocodificação por rua ou CEP e não por imóvel, mas **a precisão não foi medida**.

## 4. Comparativo

### Aluguel residencial

| | Rocha & Rocha (doc de aluguel) | VivaReal + Chaves | Meta |
|---|---:|---:|---:|
| Imóveis distintos utilizáveis | 137 | **1.580** | 1.200–1.800 |
| Bairros com ≥ 5 anúncios | 7 | **65** | — |
| Bairros com ≥ 20 anúncios | — | 28 | — |

### Venda residencial: dataset antigo × corpus novo

O dataset antigo (OLX) tem cópias do mesmo imóvel (5.644 linhas, 4.614 URLs). Comparar linhas
brutas é enganoso; a régua justa conta imóveis distintos pela mesma chave (bairro, área,
quartos, banheiros) nos dois lados:

| | Antigo (OLX) | VivaReal | VivaReal + Chaves |
|---|---:|---:|---:|
| Linhas | 5.625 | 4.748 | 5.897 |
| Imóveis distintos (chave grossa) | 2.774 | 3.453 | **3.863** |
| Variação sobre o antigo | — | +24% | **+39%** |
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

Os anúncios **não são apagados**: recebem o mesmo grupo, e o split é feito por grupo. O
agrupamento é transitivo e junta demais: os maiores grupos (até 26 anúncios) são unidades
diferentes do mesmo prédio. Isso é seguro para o split (unidades do mesmo prédio têm preço/m²
correlacionado), mas **o grupo não serve para colapsar linhas**. Foram 2.311 pares certos e
625 prováveis; os limiares são julgamento meu, sem medição de precisão. Uma amostra de 50
pares por nível está em `data/splits/amostra_pares.csv`.

Split 70/15/15 por grupo, estratificado por faixa de preço, semente 42, separado para venda e
aluguel:

| | Treino | Validação | Teste |
|---|---:|---:|---:|
| Venda (anúncios) | 4.109 | 904 | 884 |
| Aluguel (anúncios) | 1.319 | 300 | 279 |

O teste nunca foi aberto. O split foi regenerado uma vez, quando o Chaves entrou; a partir
daí fica congelado.

## 6. Primeiro experimento (só na validação)

`GradientBoostingRegressor(200, 0.1, 5)` com área, quartos, banheiros, vagas, tipo e bairro,
alvo em log do preço, sem geografia.

| | R² | R² em log | MdAPE | dentro de ±20% |
|---|---:|---:|---:|---:|
| Venda, split só VivaReal | 0,652 | 0,801 | 21,2% | 46,9% |
| **Venda, split atual** | 0,778 | 0,797 | 19,6% | 50,9% |
| Aluguel, split só VivaReal | 0,534 | 0,682 | 25,2% | 42,5% |
| **Aluguel, split atual** | 0,650 | 0,674 | 24,6% | 40,3% |

O R² em reais subiu, mas **não deve ser lido como melhora**: o split mudou, e o R² em reais é
dominado pelos valores extremos (o baseline "mediana do bairro" caiu de 0,362 para 0,246 na
venda). O R² em log e o MdAPE ficaram praticamente estáveis. Condomínio não mostra ganho
claro. Por fonte, o modelo erra mais no Chaves na venda (MdAPE 25,0% contra 18,7%, com 171
imóveis); no aluguel acontece o oposto, com 63. Os tamanhos não sustentam conclusão.

## 7. Lacunas e riscos

1. **Mobiliado não foi coletado.** O doc de aluguel o aponta como causa provável do R² negativo
   anterior. Não está no card nem no JSON-LD da listagem (a descrição aparece em 2 de 29
   anúncios); exige a página de detalhe.
2. **IPTU quase vazio** no VivaReal (20%) e com erros de digitação. Provavelmente não serve.
3. **Vagas ausentes são ambíguas.** No VivaReal a ausência pode ser "sem vaga"; no Chaves o
   campo nunca existe. O baseline trata as duas coisas com um indicador.
4. **Precisão das coordenadas do Chaves não medida.**
5. **Precisão das regras de deduplicação não medida**, só amostrada à mão em seis pares.
6. **~57 anúncios de venda do Chaves** ficaram além da página 99.
7. **Preço de anúncio, não de transação.** A margem de negociação entra como ruído.
8. **Teste de aluguel pequeno** (279 anúncios, ~237 imóveis): qualquer métrica terá incerteza
   grande.

## 8. Próximos passos

1. Fatiar o Chaves por tipo ou bairro para pegar os ~57 restantes de venda.
2. Medir a precisão das coordenadas do Chaves (por exemplo, contra o bairro declarado) e, se
   boas, refazer o teste de geografia com n bem maior que os 498 da investigação original.
3. Coletar `Mobiliado` pela página de detalhe, só para o aluguel residencial.
4. Pedido via LAI ao OMI de Teresina por dados de transação.
5. Só então abrir o teste, uma vez, no modelo final.

## Reprodução

```bash
uv sync --extra pipeline   # requests e beautifulsoup4 ficam neste extra
uv run python -m apps.scraper.scraper_vivareal --paginas-alugar 50 --paginas-comprar 50
uv run python -m apps.scraper.scraper_vivareal --fatiado alugar --fatiado comprar
uv run python -m apps.scraper.scraper_chaves --alugar --comprar
uv run python -m ml.pipeline.unificar
uv run python -m ml.experiments.baseline_atributos
```

A coleta de topo do VivaReal (primeira linha) vem antes da fatiada; as duas são incrementais.
Recoletar não reproduz exatamente o bruto versionado, porque o estoque dos portais muda;
`unificar` e o baseline, sim, reproduzem os números deste relatório a partir dele.
