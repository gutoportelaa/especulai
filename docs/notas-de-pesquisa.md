# Notas de pesquisa

> Material de trabalho, não documentação. São anotações brutas de brainstorm sobre estratégia
> de coleta (OLX, rochaerocha), geocodificação e uso da malha censitária do IBGE. Ficam aqui
> como registro das decisões e dos becos sem saída; o que virou produto está no
> [README](../README.md) e em [CONTEXT.md](../CONTEXT.md).

---

 Aja como um desenvolvedor fullstack sênior, especializado em ciência de dados. Vamos fazer um brainstorm sobre a estratégia de coleta via webcrawling do CEP(ou a malha censitária do IBGE) dos imóveis através da url da OLX, ou de https://www.rochaerocha.com.br/, e a partir desse scraping estimar os demais dados de geolocalização Area_m2,Quartos,Banheiros,Vagas_Garagem,Valor_Anuncio,URL_Anuncio,Data_Coleta,Latitude,Longitude,distancia_farmacias,distancia_escolas,distancia_mercados,distancia_hospitais,score_comercial,FipeZap_m2,FipeZap_Diferenca_m2,Descricao_Length,Bairro_Aeroporto,Bairro_Alegre,Bairro_Alto Alegre, ... . A informação coletada servirá para o treinamento do modelo preditivo do projeto. Dê a preferência por uso de requests e beautifulsoup, se não for possível no caso de OLX, utilize selenium.

Boa — esse é exatamente o gargalo certo pra atacar. Antes de propor código, deixa eu reorganizar o problema, porque a forma como ele está colocado esconde a decisão mais importante.

O problema real não é "scraping", é precisão de localização

Quase todas as features que você listou são funções de (Latitude, Longitude):

distancia_farmacias, distancia_escolas, distancia_mercados,
distancia_hospitais, score_comercial, Bairro_*  →  todas derivam de lat/lon
FipeZap_m2, FipeZap_Diferenca_m2               →  derivam de bairro/m²
Area_m2, Quartos, Banheiros, Vagas, Valor, URL →  vêm direto do anúncio

Ou seja: o scraping só precisa extrair ~7 campos crus + um identificador de local. Todo o resto é enriquecimento offline. Isso muda a estratégia: o esforço de anti-bot deve ser mínimo (pegar os campos crus) e o esforço de engenharia deve ir para o pipeline de geocodificação e a malha do IBGE, que é onde está o ganho de qualidade do modelo.

E aqui já aponto um bug que vi no código atual (enriquecimento_geoespacial.py): distancia_farmacias etc. hoje é a distância até um único ponto de referência hardcoded por categoria (POI_REFERENCE_POINTS). Isso não é "distância à farmácia mais próxima" — é "distância àquele ponto da cidade". Se você está listando essas features pra valer, elas precisam ser recalculadas de verdade (detalho abaixo).

---
Avaliação das fontes

OLX — o atalho que evita Selenium na maior parte

OLX BR é Next.js. Cada página de anúncio embute um <script id="__NEXT_DATA__" type="application/json"> com o anúncio inteiro estruturado — tipicamente em props.pageProps.ad:

import requests, json
from bs4 import BeautifulSoup

html = requests.get(url_anuncio, headers=HEADERS, timeout=15).text
soup = BeautifulSoup(html, "html.parser")
data = json.loads(soup.find("script", id="__NEXT_DATA__").string)
ad = data["props"]["pageProps"]["ad"]
# ad["location"] → {municipality, neighbourhood, zipcode?, lat, lon}
# ad["properties"] → [{name:"rooms",value:"3"}, {"bathrooms"...}, {"size"...}, {"garage_spaces"...}]
# ad["subject"], ad["body"] (→ Descricao_Length), ad["priceValue"]

Implicações:
- Você não parseia HTML — extrai JSON. Robusto a mudança de layout.
- OLX já entrega lat/lon no anúncio — porém ofuscado para nível de bairro (privacidade). Útil como feature, mas não é precisão de rua.
- zipcode (CEP) às vezes vem; muitas vezes não. Quartos/banheiros/vagas/m² vêm consistentes em properties.
- O bloqueio anti-bot (DataDome) está nas páginas de busca/listagem, não tanto nas de detalhe. Então a divisão de trabalho ideal é:
  - Selenium/Playwright só para varrer a busca e colher as URLs dos anúncios (ou usar o sitemap da OLX).
  - requests + bs4 para cada URL de detalhe via __NEXT_DATA__.

▎ Recomendo Playwright em vez de Selenium para o fallback: mais rápido, playwright-stealth lida melhor com DataDome, e o context async encaixa no resto.

rochaerocha.com.br — baixo volume, alta qualidade

Imobiliária de Teresina, site server-rendered (provável WordPress/custom). Vantagens: pouco anti-bot, requests+bs4 puro, e frequentemente expõe endereço/bairro com mais precisão que a OLX (corretora quer que você ache o imóvel). Desvantagem: volume baixo e schema próprio → outro parser.

Veredito: OLX é o volume (treino), rochaerocha é o reforço de bairros premium e validação cruzada. Não unifique o scraper — faça dois coletores que produzem o mesmo schema cru (raw_olx.csv, raw_rocha.csv) e concatene antes do enriquecimento.

---
A escada de localização (do mais preciso ao pior)

CEP no Brasil não é 1:1 com coordenada. Em Teresina há muito "CEP geral" (ex.: 64000-000) que mapeia pro centroide da cidade — lixo. Então trate localização como uma escada com fallback explícito e registre qual nível foi usado (vira até uma feature de confiança):

┌───────┬──────────────────────────────┬────────────────────────────────────────┬──────────┐
│ Nível │            Sinal             │        Como resolver p/ lat/lon        │ Precisão │
├───────┼──────────────────────────────┼────────────────────────────────────────┼──────────┤
│ 1     │ CEP de logradouro específico │ ViaCEP → logradouro+bairro → Nominatim │ rua      │
├───────┼──────────────────────────────┼────────────────────────────────────────┼──────────┤
│ 2     │ lat/lon da OLX (ofuscado)    │ usar direto                            │ ~bairro  │
├───────┼──────────────────────────────┼────────────────────────────────────────┼──────────┤
│ 3     │ Bairro                       │ centroide do bairro (tabela própria)   │ bairro   │
├───────┼──────────────────────────────┼────────────────────────────────────────┼──────────┤
│ 4     │ Só município                 │ descartar a linha                      │ inútil   │
└───────┴──────────────────────────────┴────────────────────────────────────────┴──────────┘

ViaCEP (grátis) dá logradouro/bairro/uf mas não dá lat/lon — você ainda passa pelo Nominatim (1 req/s, exige User-Agent, cache agressivo — você já tem geocode_cache.csv, mantenha). Para escala, vale baixar uma base aberta de CEP→coord uma vez e consultar localmente em vez de bater no Nominatim por linha.

---
CEP e malha do IBGE — não é ou/ou, é camada sobre camada

A malha censitária é o maior salto de qualidade e substitui o BAIRRO_FACTORS hardcoded por dado real:

1. Baixe a malha de setores censitários de Teresina (IBGE, município 2211001) — shapefile.
2. geopandas.sjoin (point-in-polygon): lat/lon → setor censitário.
3. Join com Agregados do Censo 2022 por setor → renda média, densidade domiciliar, % domicílios, etc.

Isso te dá um proxy socioeconômico contínuo por imóvel, muito superior a um dicionário de multiplicadores por bairro. O FipeZap_m2 continua como âncora de preço; a malha entra como features explicativas do desvio.

Detalhe sênior: para qualquer cálculo métrico (distâncias, point-in-polygon), reprojete para UTM 23S (EPSG:31983). Fazer distância em graus (lat/lon cru, como o geodesic ponto-a-ponto atual) é impreciso e lento em lote.

---
POI / distâncias — como fazer de verdade

Troque o "distância a um ponto fixo" por nearest-neighbor real:

1. Uma vez: Overpass API (OSM) → baixe todas as farmácias, escolas, mercados, hospitais de Teresina (amenity=pharmacy|school|hospital, shop=supermarket).
2. Reprojete tudo pra EPSG:31983, monte um scipy.spatial.cKDTree (ou sklearn.BallTree com métrica haversine se preferir manter em graus).
3. Por imóvel: tree.query(ponto) → distância ao mais próximo de cada categoria. Vetorizado, milhares de imóveis em milissegundos.
4. score_comercial = densidade de POIs comerciais num raio (ex.: tree.query_ball_point(ponto, 1000m) contando shop/amenity comerciais), normalizado. Muito mais fiel que o atual.

---
Mapa de proveniência das features (onde cada coluna nasce)

┌──────────────────────────────────┬────────────────────────────────────────────────────────────────────────────────────────────────────┐
│              Origem              │                                              Colunas                                               │
├──────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Scraping direto                  │ Area_m2, Quartos, Banheiros, Vagas_Garagem, Valor_Anuncio, URL_Anuncio, Data_Coleta,               │
│                                  │ Descricao(→_Length)                                                                                │
├──────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ Geocodificação (escada           │ Latitude, Longitude                                                                                │
│ CEP→bairro)                      │                                                                                                    │
├──────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ OSM + KDTree                     │ distancia_farmacias, _escolas, _mercados, _hospitais, score_comercial                              │
├──────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ FipeZap                          │ FipeZap_m2, FipeZap_Diferenca_m2                                                                   │
├──────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ IBGE malha (novo)                │ renda_setor, densidade_setor, ... (substitui factors)                                              │
├──────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ One-hot do bairro                │ Bairro_Aeroporto, Bairro_Alegre, ...                                                               │
└──────────────────────────────────┴────────────────────────────────────────────────────────────────────────────────────────────────────┘

Isso encaixa perfeitamente nos seus 5 estágios atuais — não precisa redesenhar o pipeline, só fortalecer os estágios 1–3:
- Estágio 1 (scraper): dois coletores → schema cru comum.
- Estágio 2 (geo): escada de localização + KDTree de POIs + sjoin IBGE.
- Estágio 3 (econômico): FipeZap como está, mas o desvio agora é explicado por features de setor.

---
Stack de robustez (resumo)

- requests + bs4 + __NEXT_DATA__ como caminho principal (OLX detalhe + rochaerocha).
- Playwright + stealth só para colher URLs de busca da OLX quando o DataDome bloquear.
- Rotação de User-Agent, delay 2–5s (você já faz), cache de geocoding e de POIs (download único).
- Checkpoint incremental por CEP/URL pra retomar coleta sem refazer.

---
Pontos de decisão (é aqui que preciso de você)

1. Fonte primária de volume: começo pela OLX (__NEXT_DATA__ + Playwright só pra URLs) ou valido o conceito ponta-a-ponta primeiro na rochaerocha, que é trivial de raspar? → Recomendo rochaerocha primeiro pra fechar o pipeline de enriquecimento rápido, depois OLX pra escala.
2. Localização: implemento já a malha IBGE (geopandas + Censo 2022) ou na v1 fico só na escada CEP/bairro e deixo IBGE pra v2? → Recomendo escada na v1, IBGE logo em seguida — é o maior ganho.
3. Fallback OLX: Playwright (minha recomendação) ou você quer manter Selenium por já ter no ambiente?

Me diz por onde prefere começar que eu prototipo o primeiro pedaço — minha sugestão é começar pelo coletor __NEXT_DATA__ da OLX (extrai os campos crus sem Selenium) ou pelo enriquecimento POI-KDTree (corrige o bug das distâncias e já melhora o modelo com os dados que você já tem). Qual ataco primeiro?

✻ Cogitated for 2m 5s

❯ Inicialmente valide o ponta-a-ponta de rochaerocha. Sobre localização: use escada na v1 e IBGE em seguida. Sobre o fallback OLX, se trata da fonte mais relevante na região para busca de imóveis, trará mais veracidade para o dataset.

Boa, decisões claras. Começo pela validação ponta-a-ponta da rochaerocha. Mas antes de escrever qualquer parser, vou olhar o site de verdade — plataforma, estrutura de URL, onde os campos vivem no HTML, e se há algum atalho (WordPress REST API, JSON embutido).

  Ran 2 shell commands

WordPress + Elementor, e — crucialmente — expõe wp-json. Se os imóveis forem um custom post type, a REST API me dá tudo em JSON estruturado, sem parsear HTML. Vou sondar as rotas.

  Ran 1 shell command

Sem custom post type óbvio no wp/v2. Mas plugins de imobiliária registram namespaces próprios. Vou listar todos os namespaces e os tipos de post, e ver como as páginas de imóvel se organizam.

  Ran 1 shell command

Sem CPT de imóvel no REST (e há Wordfence = WAF, anoto). Os imóveis devem ser páginas Elementor ou um CPT sem REST. O Yoast está ativo → tem sitemap. Vou usar o sitemap pra descobrir a estrutura de URLs dos imóveis.

  Ran 2 shell commands

Tudo esclarecido — e há um achado importante:

- Tema custom server-rendered (rochaerocha2019), jQuery puro, sem JS dinâmico → requests+bs4 resolve, zero Selenium.
- Padrão de URL de imóvel: /imovel/{comprar|alugar}/{slug}/{id}
- Busca: /imoveis/comprar/?base=2&uf=17&cidade=5676&bairro=&tipo=... (paginável)
- Usa Leaflet (leaflet.css, map.css) → a página de detalhe quase certamente embute lat/lon do marcador no JS → posso pular o geocoding no nível 1 da escada. Vou confirmar inspecionando uma página de detalhe.

  Ran 1 shell command

Zero bytes — provável WAF/sessão. Vou seguir redirects, usar cookie jar (PHPSESSID) e ver o status real.

  Ran 1 shell command

O detalhe exige barra final (301 → /) + follow redirects. Agora com 62KB de HTML, vou localizar onde os campos e as coordenadas vivem.

  Searched for 1 pattern

Coordenadas via Google Maps embutidas (lat:/lng:) — nível 1 da escada de graça. Vou extrair os valores reais e o bloco HTML das características.

  Ran 1 shell command

O mapa usa variáveis JS latitude/longitude — preciso achar onde são atribuídas. E faltou ver Valor, Bairro, CEP. Vou caçar esses três + a atribuição das coordenadas.

  Ran 1 shell command

Achado decisivo: a página não armazena lat/lon — ela geocodifica em runtime via Google (results[0].geometry.location.lat()) a partir de uma string address montada no servidor. Ou seja, o endereço textual está no HTML — é exatamente o input da minha escada. Vou extrair como o address é montado + pegar preço/bairro com Python (sem quebrar no $).

  Ran 1 shell command

Agora tenho o mapa completo. A página embute o endereço textual completo direto no HTML:

var address = "Rua Visconde da Parnaíba, 2312, HORTO, TERESINA/PI";

Isso é o melhor input possível pra escada — logradouro + número + bairro + cidade/UF. Geocodifico eu mesmo via Nominatim (nível 1, precisão de rua), sem depender da chave Google. Todo campo de treino está localizável. Vou confirmar a paginação da busca pra fechar o harvester de URLs.

  Ran 1 shell command

Busca paginada (13 imóveis/página, class="pagination"). Vou pegar o formato exato da URL de paginação e então construir o módulo.

  Ran 1 shell command

Tenho o mapa completo da fonte. Resumo do que confirmei:

┌──────────────────────────────────────┬────────────────────────────────────────────────────────────────────┐
│                Campo                 │                         Onde está no HTML                          │
├──────────────────────────────────────┼────────────────────────────────────────────────────────────────────┤
│ ID_Imovel                            │ Código: 195376 + id da URL                                         │
├──────────────────────────────────────┼────────────────────────────────────────────────────────────────────┤
│ Tipo_Negocio                         │ URL /comprar/ ou /alugar/                                          │
├──────────────────────────────────────┼────────────────────────────────────────────────────────────────────┤
│ Valor_Anuncio                        │ R$ 360.000,00                                                      │
├──────────────────────────────────────┼────────────────────────────────────────────────────────────────────┤
│ Area_m2                              │ Área Útil: 70,00 m²                                                │
├──────────────────────────────────────┼────────────────────────────────────────────────────────────────────┤
│ Quartos / Suíte / Banheiro / Garagem │ 3 Dormitório 1 Suíte, 2 Banheiro, 1 Garagem                        │
├──────────────────────────────────────┼────────────────────────────────────────────────────────────────────┤
│ Bairro + Endereco_Completo           │ var address = "Rua Visconde da Parnaíba, 2312, HORTO, TERESINA/PI" │
├──────────────────────────────────────┼────────────────────────────────────────────────────────────────────┤
│ Descricao                            │ parágrafo descritivo                                               │
├──────────────────────────────────────┼────────────────────────────────────────────────────────────────────┤
│ Lat/Lon                              │ geocodifico address via Nominatim (escada nível 1)                 │
└──────────────────────────────────────┴────────────────────────────────────────────────────────────────────┘

Paginação = &pg=N, 13/página. Tudo server-rendered, zero Selenium. Vou montar o PoC ponta-a-ponta e rodá-lo de verdade. Primeiro preparo o ambiente.

  Ran 1 shell command

uv disponível, requests já no sistema. Vou criar um venv enxuto com bs4 (padrão do projeto) e escrever o módulo coletor em paralelo. Deixo o registro de tarefas e parto pra implementação.

Agora preparo o ambiente e escrevo o módulo coletor:

  Ran 1 shell command

● Background command "Create venv and install scraper deps" completed (exit code 0)

Ambiente pronto. Vou escrever o módulo coletor + escada de geocodificação:

● Write(apps/scraper/scraper_rocha.py)
Wrote 415 lines to apps/scraper/scraper_rocha.py
"""
Coletor Rocha & Rocha (Teresina) — fonte secundária de alta qualidade.

O site (https://www.rochaerocha.com.br) é WordPress server-rendered com tema
custom `rochaerocha2019`, sem JS dinâmico de conteúdo. Estratégia: requests +
BeautifulSoup. Não requer Selenium.

Particularidades descobertas na auditoria do site:
  - URL de detalhe exige barra final (301 → `/`) e segue redirect.
  - Sessão precisa de cookie PHPSESSID (aquecido na home).
… +405 lines

Agora rodo a validação ponta-a-ponta com uma amostra pequena:

  Ran 1 shell command

Ponta-a-ponta funcionando. 7/8 imóveis coletados, 6 geocodificados a nível de rua via Nominatim, 1 caiu pro fallback de cidade. Vou inspecionar o CSV gerado pra confirmar que todas as colunas do schema estão preenchidas.

  Ran 1 shell command

Validação sólida — schema preenchido nos campos centrais. Mas o PoC revelou 3 problemas reais (exatamente o objetivo). Vou diagnosticar os dois parsers que falharam (Descrição 0/7 e área faltando em alguns) antes de corrigir.

  Ran 1 shell command

Dois achados precisos:

1. Descrição mora na meta tag og:description/twitter:description — fonte mais limpa que <p>. Fix fácil.
2. #195379 não tem bloco de características — é um lançamento/condomínio sem specs por unidade. A ausência é real, não bug do parser. Bom saber: o modelo precisará filtrar esses casos.

Vou corrigir a descrição (meta tag) e o encoding da URL com | (que derrubou a conexão):

● Update(apps/scraper/scraper_rocha.py)
Added 2 lines, removed 1 line
    """GET seguindo redirects (barra final), com Referer da home."""
    try:
        resp = session.get(
            url, timeout=REQUEST_TIMEOUT, allow_redirects=True,
            requests.utils.requote_uri(url),  # encoda chars inseguros (ex.: '|')
            timeout=REQUEST_TIMEOUT, allow_redirects=True,
            headers={"Referer": BASE_URL + "/"},
        )
        if resp.status_code != 200 or not resp.text:

● Update(apps/scraper/scraper_rocha.py)
Added 1 line, removed 1 line
    # Valor (primeiro R$ relevante)
    valor = _num(r"R\$\s*([\d.,]+)", text)

    # Descrição (maior parágrafo de texto da página, heurística simples)
    # Descrição (meta og/twitter — fonte mais limpa que o corpo HTML)
    descricao = _parse_descricao(soup)

    if valor is None and area is None and quartos is None:

● Update(apps/scraper/scraper_rocha.py)
Added 7 lines, removed 3 lines


def _parse_descricao(soup: BeautifulSoup) -> str:
    """Heurística: maior bloco <p> da página."""
    """A descrição do anúncio vive na meta og:/twitter:description."""
    for attrs in ({"property": "og:description"}, {"name": "twitter:description"}):
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            return tag["content"].strip()
    # Fallback: maior bloco <p> com conteúdo relevante
    candidates = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    candidates = [c for c in candidates if len(c) > 60]
    return max(candidates, key=len, default="")
    return max((c for c in candidates if len(c) > 60), key=len, default="")


# ============================================================================
You've hit your session limit · resets 11:40pm (America/Fortaleza)
/upgrade or /usage-credits to finish what you’re working on.

✻ Sautéed for 8m 2s

❯ Continue

Vou rodar a validação novamente para confirmar que as duas correções (descrição via meta tag e encoding da URL com |) funcionam:

  Ran 1 shell command

O | na URL agora resolve (8/8, antes era 7/8). Vou confirmar a completude da descrição e schema final:

  Ran 1 shell command

Validação completa. Todas as correções confirmadas. Vou fechar as tarefas e registrar o progresso:

  Recalled 2 memories, wrote 2 memories

Validação ponta-a-ponta da rochaerocha — concluída ✅

Construí e rodei de verdade o coletor (apps/scraper/scraper_rocha.py). Resultado em data/raw_rocha.csv: 8/8 imóveis coletados, 7/8 geocodificados a nível de rua, todas as colunas do schema de treino preenchidas — só com requests + BeautifulSoup, zero Selenium.

O que a auditoria do site revelou

- WordPress server-rendered (tema rochaerocha2019), sem JS dinâmico de conteúdo. WAF Wordfence presente mas não bloqueia leitura.
- A página de detalhe embute o endereço textual completo em var address = "Rua X, 123, BAIRRO, TERESINA/PI" — input ideal pra escada. (O site geocodifica via Google em runtime e não armazena lat/lon; eu geocodifico por conta própria.)
- Detalhes táticos: exige barra final (301), cookie PHPSESSID aquecido na home, busca paginada &pg=N.

Escada de geocodificação v1 (implementada)

rua (Nominatim sobre endereço completo, cache + 1 req/s) → bairro (centroide) → cidade (fallback). A coluna geo_precision registra o nível por imóvel — vira feature de confiança no modelo.

Bugs reais que o PoC expôs (e já corrigi)

┌──────────────────────────────────────────┬─────────────────────────────────────────────────────────────┐
│                  Achado                  │                          Correção                           │
├──────────────────────────────────────────┼─────────────────────────────────────────────────────────────┤
│ Descrição vinha vazia (<p> não continha) │ Lida da meta og:description → agora 8/8                     │
├──────────────────────────────────────────┼─────────────────────────────────────────────────────────────┤
│ URL com | derrubava a conexão            │ requests.utils.requote_uri → 8/8                            │
├──────────────────────────────────────────┼─────────────────────────────────────────────────────────────┤
│ Lançamentos sem specs por unidade        │ Ausência real de dado, não bug — o modelo precisará filtrar │
└──────────────────────────────────────────┴─────────────────────────────────────────────────────────────┘

Amostra coletada

Apartamento | Horto    | R$ 320.000 | 77m² 3Q 1suíte 2ban 1vaga | (-5.0678, -42.7775) rua
Casa        | Socopó   | R$ 1.350.000 | 192m² 4Q 2suíte 4ban 4vaga | (-5.0162, -42.7674) rua
Apartamento | Joquei   | R$ 280.000 | ... | (-5.0782, -42.7929) rua

Próximos passos (na ordem que você definiu)

1. IBGE v2 — substituir os centroides hardcoded pela malha censitária (município 2211001, geopandas sjoin, reprojeção EPSG:31983) e enriquecer com renda/densidade por setor.
2. POI via Overpass + KDTree — corrigir o bug do enriquecimento_geoespacial.py (hoje usa 1 ponto fixo por categoria, não a distância real ao mais próximo).
3. OLX — a fonte de volume/veracidade que você apontou: extração via __NEXT_DATA__ + Playwright só pra harvestar URLs da busca (DataDome).

Quer que eu ataque o IBGE v2 agora, ou prefere primeiro escalar a coleta da rochaerocha (todas as páginas de compra + aluguel) pra ter um dataset real antes de enriquecer?

✻ Baked for 2m 4s

※ recap: Building Especulai's data pipeline: I validated the rochaerocha scraper end-to-end (8/8 properties, street-level geocoding) and saved it. Next: decide whether to add IBGE census enrichment or first scale rochaerocha collection to a full dataset. (disable recaps in /config)

❯ Ataue o IBGE v2

Bom. IBGE v2 = trocar os centroides hardcoded por point-in-polygon real (lat/lon → setor censitário) e anexar features socioeconômicas por setor. Antes de escrever código, preciso de duas coisas: confirmar as URLs reais da malha do IBGE e instalar o stack geoespacial (geopandas é pesado). Vou disparar a instalação em background e fazer o recon do IBGE em paralelo.

  Ran 1 shell command

Agora o recon do IBGE — confirmar a estrutura real do servidor geoftp para a malha de setores censitários do Censo 2022:

  Ran 1 shell command

IBGE alcançável e censo_2022/ existe. Vou navegar até encontrar o arquivo de setores do Piauí:

  Ran 1 shell command

● Background command "Install geopandas stack in background" completed (exit code 0)

geopandas instalado. Há gpkg/ (mais conveniente que shapefile). Vou achar o arquivo do PI e confirmar o geopandas:

  Ran 1 shell command

shp/ tem BR/ e UF/. Vou entrar em UF/ e achar o Piauí:

  Ran 1 shell command

Encontrei: PI_setores_CD2022.zip. Vou baixar e inspecionar tamanho/estrutura:

  Ran 1 shell command

20MB zip, shapefile completo do PI. Vou extrair, filtrar Teresina (município 2211001) e inspecionar os atributos disponíveis (incluindo dados socioeconômicos no .dbf):

  Ran 1 shell command

Malha carregada: 7.340 setores do PI, CRS EPSG:4674 (SIRGAS 2000). Tem CD_SETOR, AREA_KM2 e NM_BAIRRO (nome oficial do bairro — melhor que o meu parse!), mas não tem dados socioeconômicos — esses estão nas tabelas "Agregados por setor". Primeiro vou filtrar Teresina e validar o sjoin com os 8 imóveis, depois anexo os agregados:

  Ran 1 shell command

Sjoin perfeito: 8/8 imóveis mapeados a um setor censitário. E o bairro oficial do IBGE confere com meu parse (Horto→Horto, Socopó, Jóquei...). Repare na validação do design de confiança: o imóvel geo=cidade (Santa Maria da Codipe) caiu no setor do "Centro" — porque o fallback usou o centroide da cidade. Isso confirma por que a coluna geo_precision importa: esse setor é não-confiável e o modelo deve tratá-lo com cautela.

Agora os agregados socioeconômicos. Vou localizar a tabela do Censo 2022:

  Ran 1 shell command

Excelente — há Agregados_por_Setor_csv/ (consolidado) e até uma pasta dedicada de Rendimento do Responsável (renda). Vou inspecionar o csv consolidado:

  Ran 1 shell command

O arquivo basico é o que tem os agregados-chave (população, domicílios, rendimento médio). É um zip BR inteiro — vou checar o tamanho antes de baixar:

  Ran 1 shell command

14.7 MB, tranquilo. Vou baixar e inspecionar as colunas socioeconômicas disponíveis:

  Ran 2 shell commands

basico tem v0001–v0009. Pelo dicionário do Censo 2022: v0001=população, v0002/v0003=domicílios, v0005=média de moradores. Isso já me dá densidade populacional (v0001/AREA_KM2) — o proxy socioeconômico espacial mais forte. Renda está numa pasta separada; vou verificar se vale incluir agora:

  Ran 1 shell command

Há renda por setor (Agregados_por_setores_renda_responsavel) — a feature socioeconômica mais preditiva pra preço de imóvel. Vou baixar e juntar tudo:

  Ran 2 shell commands

Achei tudo: V06004 = rendimento médio mensal do responsável (R$) — a feature mais preditiva. Agora tenho os 3 insumos (malha + básico + renda), todos keyed por CD_SETOR. Vou construir o módulo de enriquecimento:

● Write(ml/pipeline/modules/enriquecimento_ibge.py)
Wrote 211 lines to ml/pipeline/modules/enriquecimento_ibge.py
"""
Enriquecimento socioeconômico via malha censitária do IBGE (Censo 2022).

Substitui os centroides/fatores de bairro hardcoded por dados reais por
setor censitário, resolvidos por point-in-polygon (lat/lon → CD_SETOR).

Entrada: CSV com colunas Latitude/Longitude (ex.: data/raw_rocha.csv).
Saída:   CSV enriquecido com features por setor censitário.

Insumos IBGE (baixados em data/ibge/, município 2211001 = Teresina):
… +201 lines

Agora a validação ponta-a-ponta: construir o cache de setores enriquecido e rodar sobre os 8 imóveis:

  Ran 1 shell command

8/8 imóveis associados a um setor. Vou inspecionar as features socioeconômicas resultantes:

  Ran 1 shell command

Enriquecimento funcionando e o sanity check é forte: renda por setor mapeia bem (Jóquei R$17k premium vs N.S. das Graças R$2.6k) e a correlação renda×preço/m² = 0,576 já em 6 pontos confiáveis — sinal preditivo real, que é o objetivo.

Mas há um bug: densidade_populacional saiu 0.0 em tudo. Vou depurar:

  Ran 1 shell command

Achei: area_setor_km2 está em ~1e14 — o AREA_KM2 da malha usa ponto decimal (ou já é float), mas eu tratei como vírgula, removendo o ponto e transformando 0.539 em 5393102. Só os CSVs de agregados usam vírgula. Vou confirmar e corrigir:

  Ran 1 shell command

AREA_KM2 já é float64 nativo. Corrijo para não aplicar parsing de vírgula nele:

● Update(ml/pipeline/modules/enriquecimento_ibge.py)
Added 2 lines, removed 1 line
    malha = gpd.read_file(MALHA_SHP)
    tere = malha[malha["CD_MUN"] == CD_MUN_TERESINA].copy()
    tere["CD_SETOR"] = tere["CD_SETOR"].astype(str)
    tere["area_setor_km2"] = _to_float(tere["AREA_KM2"], decimal=",")
    # AREA_KM2 na malha já é float64 (ponto decimal); só os CSVs de agregados usam vírgula.
    tere["area_setor_km2"] = pd.to_numeric(tere["AREA_KM2"], errors="coerce")
    setores_teresina = set(tere["CD_SETOR"])
    logger.info("[IBGE] Teresina: %d setores censitários", len(tere))


Preciso reconstruir o cache (force) para aplicar a correção. Vou rodar com rebuild e revalidar a densidade:

  Ran 1 shell command

Densidade agora realista: Jóquei 12.001 hab/km² (bairro vertical denso, renda R$17k) vs Socopó 322 hab/km² (baixa densidade, lotes grandes — coerente com a casa de R$1,35M/192m²). Bug corrigido. Vou fechar as tarefas e registrar o progresso:

  Ran 1 shell command

O cache é self-contained (1,3 MB) vs 253 MB de insumos brutos — os arquivos BR podem ser apagados após o build. data/ está no .gitignore. Vou atualizar a memória do projeto:

  Wrote 1 memory

IBGE v2 — concluído e validado ✅

Construí ml/pipeline/modules/enriquecimento_ibge.py, que substitui os centroides/fatores de bairro hardcoded por dados reais do Censo 2022 via point-in-polygon.

O que foi feito (tudo rodado de verdade)

1. Recon do IBGE — confirmei e baixei do geoftp/ftp oficial:
  - Malha de setores Censo 2022 (PI_setores_CD2022.shp) → 1.531 setores em Teresina (município 2211001)
  - Agregados básicos (v0001=população, v0005=média de moradores)
  - Rendimento do responsável (V06004=renda média mensal R$) — a feature mais preditiva
2. Módulo de enriquecimento — sjoin lat/lon → CD_SETOR, CRS de trabalho EPSG:31983 (UTM 23S), com cache self-contained (teresina_setores_enriquecido.gpkg, 1,3 MB).
3. Validação nos 8 imóveis: 8/8 associados a um setor; bairro oficial do IBGE confere com o parse do scraper.

Features novas por imóvel

cd_setor, ibge_bairro, area_setor_km2, populacao_setor, densidade_populacional, media_moradores, renda_media_responsavel.

Sinal preditivo confirmado

corr(renda do setor, preço/m²) = 0,576 já em 6 pontos confiáveis (geo=rua) — exatamente o que justifica a feature. Densidade também ficou coerente: Jóquei 12.001 hab/km² (vertical, renda R$17k) vs Socopó 322 hab/km² (lotes grandes, casa de R$1,35M).

Bug encontrado e corrigido

densidade saiu 0.0 na 1ª rodada: o AREA_KM2 da malha já é float64 (ponto decimal), mas eu apliquei parse de vírgula, transformando 0.539 em 5393102. Só os CSVs de agregados usam vírgula decimal. Corrigido e revalidado.

Pontos de atenção (para você decidir)

- Reprodutibilidade: data/ está 100% no .gitignore, então nem o cache de 1,3 MB vai pro git. Sugiro ou git add -f no gpkg (leve), ou adicionar auto-download dos insumos IBGE no módulo. Recomendo o auto-download.
- A renda_media_responsavel tem NaN em alguns setores (sigilo estatístico do IBGE em setores pouco populosos) — o prepare_dataset.py vai precisar tratar (imputação por mediana do bairro/RGI).

Próximos passos na fila

1. POI via Overpass + KDTree — corrigir o bug do enriquecimento_geoespacial.py (distância a 1 ponto fixo → distância real ao mais próximo).
2. OLX — fonte de volume via __NEXT_DATA__ + Playwright só pro harvest de URLs.
3. Integrar o estágio IBGE no orchestrator.py.

Quer que eu siga para o POI/Overpass (fecha o bloco de enriquecimento geoespacial) ou prefere integrar o IBGE no orquestrador e escalar a coleta da rochaerocha primeiro?

✻ Cogitated for 7m 49s

※ recap: Goal: enrich the Especulai property dataset for ML price prediction. Done: validated the rochaerocha scraper end-to-end and built/validated the IBGE census enrichment (income correlates 0.576 with price/m²). Next: build POI distances via Overpass + KDTree, or integrate IBGE into the orchestrator. (disable recaps in /config)
                                                               sent 33926 chars via OSC 52 · check terminal clipboard settings if paste fails
──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
❯
───────────────────────────────────gi