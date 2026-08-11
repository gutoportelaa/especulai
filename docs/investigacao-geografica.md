# Investigação: quanto a localização explica o preço em Teresina

**Data:** 08/08/2026 · **Fonte:** Rocha & Rocha (1.164 imóveis) · **Modelo congelado:** `v1.0-baseline`

---

## A pergunta

O modelo v1 tinha um teto conhecido: 109 coordenadas distintas para 4.597 anúncios da OLX — uma
por bairro. Toda feature geográfica era, algebricamente, uma função do bairro. Não dava para saber
se localização fina importa, porque o dado não permitia perguntar.

Esta investigação resolve o dado primeiro e só depois pergunta.

## O que foi construído

| Insumo | Antes (OLX) | Agora (Rocha & Rocha) |
|---|---|---|
| Anúncios | 4.597 | 1.164 |
| Coordenadas distintas | 109 (2,4%) | 577 (50%) |
| Precisão de rua | 0% | **90%** (85% com número) |
| POIs | 4 pontos fixos à mão | **1.481 reais do OSM**, 8 categorias |
| Setor censitário IBGE | impossível | 1.154 de 1.164 |

A geocodificação subiu de 65% para 88% de rua confirmada trocando Nominatim por Photon
(ver [`geocodificacao`](#nota-sobre-a-geocodificação)).

## Resultado: a influência geográfica se esgota no bairro

Validação cruzada 5×, agrupada por coordenada (imóveis no mesmo endereço não cruzam as dobras).
Amostra: 498 residenciais de venda.

**Alvo log(preço):**

| Modelo | R² | MdAPE |
|---|---:|---:|
| M0 características do imóvel | 0,679 | 23,9% |
| M1 M0 + bairro | **0,706** | **22,6%** |
| M2 M0 + geografia (lat/lon + POI + IBGE) | 0,628 | 27,6% |
| M3 M0 + bairro + geografia | 0,670 | 24,8% |

**Alvo log(preço/m²)**, que isola a localização tirando o efeito dominante da área:

| Modelo | R² |
|---|---:|
| A características | 0,518 |
| A + bairro | **0,530** |
| A + geografia enxuta (4 features) | 0,449 |
| A + bairro + geografia enxuta | 0,447 |
| A + bairro + geografia completa (38 features) | 0,481 |

Nos dois alvos, **acrescentar geografia ao bairro piora o modelo**. Não é ruído de uma medição:
o sinal é consistente em duas formulações e em cinco dobras.

## Por que — a variância dentro do bairro não é geográfica

Decomposição da variância de log(preço/m²):

| | Variância | Fração |
|---|---:|---:|
| Total | 0,3570 | 100% |
| **Entre** bairros | 0,1703 | 48% |
| **Dentro** do bairro | 0,1867 | **52%** |

Existe muito o que explicar dentro do bairro. A questão é se a geografia fina explica.

Correlação de Spearman entre o **resíduo dentro do bairro** e cada feature geográfica
(19 bairros com ≥10 imóveis, 271 imóveis):

| Feature | Correlação com o resíduo |
|---|---:|
| `poi_dist_pracas` | 0,109 |
| `densidade_populacional` | −0,083 |
| `renda_media_responsavel` | 0,066 |
| `Longitude` | 0,065 |
| `poi_dist_escolas` | −0,024 |

Nenhuma passa de 0,11. **Os 52% de variação dentro do bairro não são explicados por posição.**
São atributos que ninguém coletou: estado de conservação, idade, andar, acabamento, vista,
infraestrutura do condomínio, e a margem de negociação embutida na pedida.

## O que a geografia de fato explica

Ela não é irrelevante — é apenas de baixa resolução. Entre bairros o efeito é grande:

| Bairro | R$/m² mediano |
|---|---:|
| Jóquei | 8.529 |
| Horto | 7.000 |
| Fátima | 6.829 |
| … | |
| Centro | 2.785 |
| Lourival Parente | 2.299 |

Razão entre o mais caro e o mais barato: **3,7×**.

E a melhor feature geográfica isolada é o IBGE, não os POIs:

| Feature | Correlação com log(preço/m²) |
|---|---:|
| `renda_media_responsavel` (setor censitário) | **0,318** (0,346 só em `geo=rua`) |
| `poi_dist_escolas` | 0,203 |
| `densidade_populacional` | −0,143 |
| `poi_dist_shoppings` | −0,068 |
| `poi_dist_mercados` | −0,012 |

A renda do setor censitário confirma-se como o sinal geográfico mais forte do projeto. Mas o
grosso dela é **entre** bairros (dentro do bairro cai para 0,066), ou seja: é largamente redundante
com saber o nome do bairro.

## Um achado lateral: características e localização são confundidas

O bairro acrescenta pouco (+0,013 a +0,027 de R²) sobre as características do imóvel — apesar do
espalhamento de 3,7× entre bairros. A explicação é que os atributos já carregam a localização:
um apartamento com 3 suítes e 3 vagas *está* no Jóquei. Saber o bairro, dado que já se conhece o
imóvel, acrescenta pouca informação nova.

## Conclusão

**A tese da v2 não se confirmou.** Geocodificar a nível de rua era necessário para responder à
pergunta, e a resposta é que, em Teresina e nesta amostra, o bairro já é a resolução certa. Não há
ganho em micro-localização.

O esforço seguinte deve ir para **atributos do imóvel**, não para mais geografia. É lá que estão
os 52% de variância não explicada.

## Teste direto: treinar no Rocha, com tudo ligado (2026-08-11)

A análise acima é correlacional. Fica a pergunta prática: e se o modelo fosse treinado no
Rocha & Rocha, que tem tudo o que o dataset da OLX não tem — `Tipo_Imovel`, POIs reais do OSM
(distância ao mais próximo **e** contagem em 500/1000/2000 m) e renda por setor censitário?

Protocolo idêntico ao `train_model.py`: `GroupShuffleSplit` por imóvel, `GradientBoosting(200,
0.1, 5)`, `StandardScaler`, piso de R$ 50 mil, dedup por URL.

| Modelo | n treino | features | R² teste | MdAPE |
|---|---:|---:|---:|---:|
| **A) OLX — publicado hoje** | 3.677 | 121 | **0,74** | 18,7% |
| B) Rocha: base + bairro + `Tipo_Imovel` | 429 | 96 | 0,33 | 21,2% |
| C) B + POIs reais do OSM | 429 | 128 | 0,34 | 18,7% |
| D) C + renda IBGE por setor | 429 | 132 | **0,27** | 20,8% |

> R² de A não é diretamente comparável ao de B–D (amostras e conjuntos de teste diferentes).
> O que importa é a comparação **entre** B, C e D, que dividem exatamente o mesmo split.

Três leituras:

1. **Volume vence riqueza de features.** Os 537 anúncios de venda do Rocha, com 96–132 features,
   memorizam: R² de 0,99 no treino contra 0,33 no teste. Não há dado suficiente para sustentar
   essa largura.
2. **POIs reais quase não movem o ponteiro** (0,326 → 0,337). Substituir a distância a um ponto
   fixo pela distância real ao equipamento mais próximo, com contagem por raio, rende 1 ponto
   percentual de R² — coerente com a conclusão acima.
3. **A renda do IBGE piorou** (0,337 → 0,272). A correlação de 0,58 entre renda do setor e
   preço/m² é real, mas como feature adicional em n=429 ela adiciona mais variância do que sinal.

**Decisão: o modelo publicado continua sendo o da OLX.** Trocar por qualquer um dos alternativos
seria trocar R² 0,74 por 0,33 em nome de features mais bonitas. O caminho para corrigir o P23
(`tipo` inerte) e o P24 (features de engenharia perdidas) passa por **recoletar volume**, não por
trocar de fonte.

Reprodução: `uv run python -m ml.experiments.comparar_fontes`

## Limites desta conclusão

Vale registrar o que ela não sustenta:

- **n = 498 é pequeno.** Um efeito real da ordem de 0,11 de correlação exigiria algo como
  1.000–2.000 imóveis para ser detectado com confiança. A ausência de sinal aqui é compatível com
  um sinal fraco existente.
- **Só 19 bairros têm ≥10 imóveis.** A análise dentro do bairro apoia-se em 271 imóveis.
- **Aluguel ficou de fora**: apenas 135 imóveis residenciais, e um único bairro com ≥10. Não dá
  para replicar a decomposição.
- **É específico de Teresina.** Uma cidade com mais heterogeneidade interna de bairro — orla
  versus miolo, presença de favela colada a área nobre — provavelmente daria outro resultado.
- **Preço de anúncio, não de transação.** A margem de negociação entra como ruído.

## Nota sobre a geocodificação

Benchmark em 97 endereços reais, medindo se o geocodificador devolve a mesma rua que foi pedida:

| Estratégia | Resolveu | Rua confere | Coords únicas |
|---|---:|---:|---:|
| Nominatim texto livre (era o uso) | 71% | 65% | 59 |
| Nominatim estruturado rua+nº | 77% | 74% | 65 |
| Nominatim estruturado só rua | 79% | 76% | 60 |
| Photon rua+nº | 93% | 82% | 76 |
| **Photon só rua** | **98%** | **88%** | **76** |

A escada final é `rua_numero → rua → bairro → cidade`, com Photon primeiro e Nominatim de reserva
em cada nível, validando por bounding box de Teresina e similaridade do nome da rua.

Duas armadilhas encontradas: o Photon devolve HTTP 400 com `lang=pt` (aceita só default/de/en/fr),
o que fazia todas as chamadas falharem em silêncio; e o CEP não serve como geocodificador — a
BrasilAPI devolve `location.coordinates` vazio para Teresina, e o Rocha & Rocha não expõe CEP em
nenhum dos 97 anúncios inspecionados.

## Reprodução

```bash
make scrape-rocha                                    # coleta incremental
uv run python -m ml.pipeline.modules.enriquecimento_poi --refresh   # snapshot de POIs
```

O snapshot de POIs usado nesta análise está versionado em
`data/pois/pois_teresina_20260808.json`.
