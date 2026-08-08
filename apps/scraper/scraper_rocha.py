"""
Coletor Rocha & Rocha (Teresina) — fonte secundária de alta qualidade.

O site (https://www.rochaerocha.com.br) é WordPress server-rendered com tema
custom `rochaerocha2019`, sem JS dinâmico de conteúdo. Estratégia: requests +
BeautifulSoup. Não requer Selenium.

Particularidades descobertas na auditoria do site:
  - URL de detalhe exige barra final (301 → `/`) e segue redirect.
  - Sessão precisa de cookie PHPSESSID (aquecido na home).
  - Busca paginada: /imoveis/{comprar|alugar}/?base=...&pg=N (13 imóveis/página).
  - A página de detalhe embute o endereço textual completo:
        var address = "Rua Visconde da Parnaíba, 2312, HORTO, TERESINA/PI";
    Esse é o melhor input para a escada de geocodificação (precisão de rua).

Saída: data/raw_rocha.csv (schema compatível com raw_olx.csv + colunas de geo).

Escada de geocodificação (v1):
  Nível 1 (`rua`):    geocodifica `var address` via Nominatim.
  Nível 3 (`bairro`): fallback para centroide do bairro.
  Nível 4 (`cidade`): fallback final para centroide de Teresina.
A malha censitária do IBGE entra na v2 (ver CONTEXT.md).
"""

from __future__ import annotations

import csv
import logging
import random
import re
import time
import unicodedata
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # .../especulai
DATA_DIR = PROJECT_ROOT / "data"
RAW_FILE = DATA_DIR / "raw_rocha.csv"
GEOCODE_CACHE_FILE = DATA_DIR / "geocode_cache.csv"

BASE_URL = "https://www.rochaerocha.com.br"

# Templates de busca (Teresina/PI). `base` distingue alugar (1) de comprar (2).
SEARCH_TEMPLATES = {
    "alugar": BASE_URL + "/imoveis/alugar/?base=1&uf=PI&cidade=879&bairro=&tipo=&valorminimo=&valormaximo=&pg={pg}",
    "comprar": BASE_URL + "/imoveis/comprar/?base=2&uf=17&cidade=5676&bairro=&tipo=&valorminimo=&valormaximo=&pg={pg}",
}

DETAIL_URL_RE = re.compile(r"/imovel/(?:comprar|alugar)/[^\"'/]+/\d+")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

REQUEST_TIMEOUT = 20
DELAY_PAGES = (2.0, 4.0)      # entre páginas de busca / detalhes
NOMINATIM_DELAY = 1.1        # política de uso do Nominatim: 1 req/s
PHOTON_DELAY = 1.0

GEOCODER_UA = {"User-Agent": "especulai/0.2 (https://github.com/gutoportelaa/especulai)"}

# Caixa de Teresina. Coordenada fora disso é resposta errada do geocodificador,
# não um imóvel distante — Nominatim às vezes devolve outra cidade homônima.
TERESINA_BBOX = (-5.30, -42.95, -4.90, -42.60)  # lat_min, lon_min, lat_max, lon_max

# O anúncio abrevia o logradouro de forma inconsistente ("R.", "Av.", "Des.").
# Sem expandir, o geocodificador não casa o nome da rua.
ABREVIACOES = {
    r"\bR\.": "Rua", r"\bAv\.": "Avenida", r"\bAvn\.": "Avenida", r"\bTv\.": "Travessa",
    r"\bPç\.": "Praça", r"\bPc\.": "Praça", r"\bDes\.": "Desembargador",
    r"\bDr\.": "Doutor", r"\bDra\.": "Doutora", r"\bProfa\.": "Professora",
    r"\bProf\.": "Professor", r"\bSta\.": "Santa", r"\bSto\.": "Santo",
    r"\bMons\.": "Monsenhor", r"\bCel\.": "Coronel", r"\bGen\.": "General",
    r"\bPe\.": "Padre", r"\bSen\.": "Senador", r"\bPres\.": "Presidente",
}

# Similaridade mínima entre a rua pedida e a rua devolvida para aceitar o ponto.
SIMILARIDADE_MINIMA_RUA = 0.75

OUTPUT_HEADERS = [
    "ID_Imovel", "Tipo_Negocio", "Tipo_Imovel", "Area_m2", "Quartos",
    "Suites", "Banheiros", "Vagas_Garagem", "Valor_Anuncio", "Bairro", "CEP",
    "Latitude", "Longitude", "geo_precision", "Endereco_Completo",
    "Descricao", "Descricao_Length", "URL_Anuncio", "Data_Coleta",
]

# Centroides aproximados de bairros de Teresina (fallback nível 3).
# Lista enxuta; ampliar conforme a cobertura da coleta.
BAIRRO_CENTROIDS: dict[str, tuple[float, float]] = {
    "centro": (-5.0892, -42.8016),
    "fatima": (-5.0808, -42.7906),
    "jockey": (-5.0731, -42.7889),
    "joquei": (-5.0731, -42.7889),
    "horto": (-5.0686, -42.7770),
    "ininga": (-5.0540, -42.7860),
    "noivos": (-5.0838, -42.7721),
    "morada do sol": (-5.0567, -42.7700),
    "sao cristovao": (-5.0620, -42.7980),
    "piçarra": (-5.1050, -42.8050),
    "picarra": (-5.1050, -42.8050),
    "ilhotas": (-5.0980, -42.8030),
    "cabral": (-5.0930, -42.8090),
    "marquês": (-5.0760, -42.7990),
    "marques": (-5.0760, -42.7990),
    "vermelha": (-5.0680, -42.8090),
}
CIDADE_CENTROID = (-5.0892, -42.8016)  # Praça da Bandeira, Teresina

KNOWN_TYPES = [
    "Apartamento", "Casa", "Terreno", "Flat", "Sala", "Loja", "Galpão",
    "Sobrado", "Kitnet", "Ponto", "Lote", "Cobertura", "Sítio", "Chácara",
]

# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger("scraper_rocha")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def _sleep(rng: tuple[float, float]) -> None:
    time.sleep(random.uniform(*rng))


# ============================================================================
# SESSÃO HTTP
# ============================================================================

def build_session() -> requests.Session:
    """Cria sessão e aquece o cookie PHPSESSID na home."""
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        session.get(BASE_URL + "/", timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        logger.warning("[SESSION] Falha ao aquecer sessão: %s", exc)
    return session


def fetch(session: requests.Session, url: str) -> str | None:
    """GET seguindo redirects (barra final), com Referer da home."""
    try:
        resp = session.get(
            requests.utils.requote_uri(url),  # encoda chars inseguros (ex.: '|')
            timeout=REQUEST_TIMEOUT, allow_redirects=True,
            headers={"Referer": BASE_URL + "/"},
        )
        if resp.status_code != 200 or not resp.text:
            logger.warning("[FETCH] %s -> HTTP %s (%d bytes)", url, resp.status_code, len(resp.text))
            return None
        return resp.text
    except requests.RequestException as exc:
        logger.warning("[FETCH] Erro em %s: %s", url, exc)
        return None


# ============================================================================
# HARVEST DE URLs (busca paginada)
# ============================================================================

def harvest_listing_urls(
    session: requests.Session, tipo_negocio: str, max_pages: int
) -> list[str]:
    """Coleta URLs de detalhe percorrendo a busca paginada até esgotar."""
    template = SEARCH_TEMPLATES[tipo_negocio]
    seen: list[str] = []
    seen_set: set[str] = set()

    for pg in range(1, max_pages + 1):
        html = fetch(session, template.format(pg=pg))
        if not html:
            break
        found = DETAIL_URL_RE.findall(html)
        new = [BASE_URL + p + "/" for p in dict.fromkeys(found) if (BASE_URL + p) not in seen_set]
        if not new:
            logger.info("[HARVEST] %s pg=%d sem novos imóveis — parando.", tipo_negocio, pg)
            break
        for u in new:
            seen_set.add(u.rstrip("/"))
            seen.append(u)
        logger.info("[HARVEST] %s pg=%d -> +%d (total %d)", tipo_negocio, pg, len(new), len(seen))
        _sleep(DELAY_PAGES)

    return seen


# ============================================================================
# PARSE DE DETALHE
# ============================================================================

def _num(pattern: str, text: str, cast=float) -> float | None:
    m = re.search(pattern, text, re.IGNORECASE)
    if not m:
        return None
    raw = m.group(1).replace(".", "").replace(",", ".")
    try:
        return cast(float(raw))
    except (ValueError, TypeError):
        return None


def parse_detail(html: str, url: str) -> dict | None:
    """Extrai campos crus de uma página de detalhe."""
    soup = BeautifulSoup(html, "lxml")
    text = re.sub(r"\s+", " ", soup.get_text(" "))

    # Endereço textual (input da escada de geocodificação)
    addr_m = re.search(r'var\s+address\s*=\s*"([^"]+)"', html)
    endereco = addr_m.group(1).strip() if addr_m else ""
    bairro = _parse_bairro(endereco)

    # ID do imóvel (da URL)
    id_m = re.search(r"/(\d+)/?$", url)
    id_imovel = id_m.group(1) if id_m else ""

    # Tipo de negócio (da URL)
    tipo_negocio = "comprar" if "/comprar/" in url else "alugar"

    # Tipo de imóvel (primeiro tipo conhecido que aparecer no texto)
    tipo_imovel = next((t for t in KNOWN_TYPES if re.search(rf"\b{t}\b", text, re.IGNORECASE)), "")

    # Características numéricas
    area = _num(r"Área\s*(?:Útil|Constru[ií]da)?\s*:?\s*([\d.,]+)\s*m", text)
    quartos = _num(r"(\d+)\s*Dormit", text, int)
    suites = _num(r"(\d+)\s*Su[ií]te", text, int)
    banheiros = _num(r"(\d+)\s*Banheiro", text, int)
    vagas = _num(r"(\d+)\s*Garagem", text, int)

    # Valor (primeiro R$ relevante)
    valor = _num(r"R\$\s*([\d.,]+)", text)

    # Descrição (meta og/twitter — fonte mais limpa que o corpo HTML)
    descricao = _parse_descricao(soup)

    if valor is None and area is None and quartos is None:
        logger.warning("[PARSE] Sem campos úteis em %s — ignorando.", url)
        return None

    return {
        "ID_Imovel": id_imovel,
        "Tipo_Negocio": tipo_negocio,
        "Tipo_Imovel": tipo_imovel,
        "Area_m2": area,
        "Quartos": quartos,
        "Suites": suites,
        "Banheiros": banheiros,
        "Vagas_Garagem": vagas,
        "Valor_Anuncio": valor,
        "Bairro": bairro,
        "CEP": "",  # site não expõe CEP; mantido por compatibilidade de schema
        "Endereco_Completo": endereco,
        "Descricao": descricao,
        "Descricao_Length": len(descricao),
        "URL_Anuncio": url,
        "Data_Coleta": datetime.now().isoformat(timespec="seconds"),
    }


def _parse_bairro(endereco: str) -> str:
    """Extrai o bairro do endereço 'Logradouro, Num, BAIRRO, CIDADE/UF'."""
    if not endereco:
        return ""
    parts = [p.strip() for p in endereco.split(",") if p.strip()]
    # O token de cidade contém '/'; o bairro é o anterior a ele.
    for i, p in enumerate(parts):
        if "/" in p and i > 0:
            return parts[i - 1].title()
    return parts[-2].title() if len(parts) >= 2 else ""


def _parse_descricao(soup: BeautifulSoup) -> str:
    """A descrição do anúncio vive na meta og:/twitter:description."""
    for attrs in ({"property": "og:description"}, {"name": "twitter:description"}):
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            return tag["content"].strip()
    # Fallback: maior bloco <p> com conteúdo relevante
    candidates = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    return max((c for c in candidates if len(c) > 60), key=len, default="")


# ============================================================================
# ESCADA DE GEOCODIFICAÇÃO
# ============================================================================

def _load_geocode_cache() -> dict[str, tuple[float, float, str]]:
    cache: dict[str, tuple[float, float, str]] = {}
    if GEOCODE_CACHE_FILE.exists():
        with GEOCODE_CACHE_FILE.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                cache[row["address"]] = (
                    float(row["lat"]), float(row["lon"]), row["precision"],
                )
    return cache


def _save_geocode_cache(cache: dict[str, tuple[float, float, str]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with GEOCODE_CACHE_FILE.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["address", "lat", "lon", "precision"])
        for addr, (lat, lon, prec) in cache.items():
            writer.writerow([addr, lat, lon, prec])


def split_endereco(endereco: str) -> tuple[str, str, str]:
    """Quebra 'Rua X, 123, BAIRRO, TERESINA/PI' em (rua, numero, bairro), normalizado.

    A normalização é o que faz o geocodificador acertar: o anúncio escreve
    "R. Des. João Pereira" e o número como "3.353", e nenhum dos dois casa
    com o cadastro do OSM sem tratamento.
    """
    partes = [p.strip() for p in endereco.split(",")]
    rua = partes[0] if partes else ""
    numero = partes[1] if len(partes) > 1 else ""
    bairro = partes[2] if len(partes) > 2 else ""

    for padrao, expansao in ABREVIACOES.items():
        rua = re.sub(padrao, expansao, rua, flags=re.IGNORECASE)

    rua = re.sub(r"\s+", " ", rua).strip().title()
    numero = re.sub(r"[^\d]", "", numero)  # "3.353" -> "3353"
    return rua, numero, bairro.strip().title()


def _sem_acento(texto: str) -> str:
    base = unicodedata.normalize("NFKD", str(texto))
    return "".join(c for c in base if not unicodedata.combining(c)).lower().strip()


def _dentro_de_teresina(lat: float, lon: float) -> bool:
    lat_min, lon_min, lat_max, lon_max = TERESINA_BBOX
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max


def _rua_confere(rua_pedida: str, rua_devolvida: str) -> bool:
    """Evita aceitar um ponto que o geocodificador escolheu por aproximação ruim."""
    if not rua_devolvida:
        return False
    similaridade = SequenceMatcher(
        None, _sem_acento(rua_pedida), _sem_acento(rua_devolvida)
    ).ratio()
    return similaridade >= SIMILARIDADE_MINIMA_RUA


def _nominatim(params: dict, rua_pedida: str) -> tuple[float, float, bool] | None:
    """Consulta o Nominatim e devolve (lat, lon, rua_confere) ou None."""
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={**params, "format": "json", "limit": 1,
                    "countrycodes": "br", "addressdetails": 1},
            headers=GEOCODER_UA,
            timeout=REQUEST_TIMEOUT,
        )
        time.sleep(NOMINATIM_DELAY)
        dados = resp.json()
        if not dados:
            return None
        lat, lon = float(dados[0]["lat"]), float(dados[0]["lon"])
        if not _dentro_de_teresina(lat, lon):
            return None
        return lat, lon, _rua_confere(rua_pedida, dados[0].get("address", {}).get("road", ""))
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.warning("[GEO] Nominatim falhou (%s): %s", params, exc)
        time.sleep(NOMINATIM_DELAY)
        return None


def _photon(consulta: str, rua_pedida: str) -> tuple[float, float, bool] | None:
    """Photon (Komoot): mesmo dado do OSM, casamento difuso melhor que o Nominatim."""
    try:
        resp = requests.get(
            "https://photon.komoot.io/api",
            # Sem `lang`: o Photon só aceita default/de/en/fr e devolve 400 com "pt".
            params={"q": consulta, "limit": 1, "lat": CIDADE_CENTROID[0],
                    "lon": CIDADE_CENTROID[1]},
            headers=GEOCODER_UA,
            timeout=REQUEST_TIMEOUT,
        )
        time.sleep(PHOTON_DELAY)
        feicoes = resp.json().get("features", [])
        if not feicoes:
            return None
        lon, lat = feicoes[0]["geometry"]["coordinates"]
        if not _dentro_de_teresina(lat, lon):
            return None
        props = feicoes[0]["properties"]
        rua = props.get("street") or props.get("name", "")
        return lat, lon, _rua_confere(rua_pedida, rua)
    except (requests.RequestException, ValueError, KeyError, IndexError) as exc:
        logger.warning("[GEO] Photon falhou ('%s'): %s", consulta, exc)
        time.sleep(PHOTON_DELAY)
        return None


def geocode_escada(
    endereco: str, bairro: str, cache: dict[str, tuple[float, float, str]]
) -> tuple[float | None, float | None, str]:
    """Resolve lat/lon descendo da maior para a menor precisão.

    Níveis, do melhor para o pior:
      `rua_numero` — endereço com número confirmado pelo geocodificador
      `rua`        — logradouro localizado, número não confirmado
      `bairro`     — centroide do bairro
      `cidade`     — centroide de Teresina

    `geo_precision` vira feature: o modelo pode aprender a desconfiar de
    imóveis cuja posição é só o centroide do bairro.
    """
    if endereco and endereco in cache:
        return cache[endereco]

    rua, numero, bairro_end = split_endereco(endereco) if endereco else ("", "", "")
    bairro_busca = bairro_end or bairro

    if rua:
        estruturado = {"city": "Teresina", "state": "Piauí", "country": "Brasil"}

        # Ordem medida em 97 endereços reais (rua confirmada pelo geocodificador):
        #   Photon só rua        88%      Nominatim estruturado só rua    76%
        #   Photon rua+número    82%      Nominatim estruturado rua+nº    74%
        #                                 Nominatim texto livre           65%
        # O Photon casa nomes de logradouro muito melhor sobre a mesma base OSM,
        # então vai primeiro em cada nível.

        # Nível 1: rua + número.
        for fn, args in (
            (_photon, (f"{rua} {numero}, {bairro_busca}, Teresina, Piaui", rua)),
            (_nominatim, ({**estruturado, "street": f"{numero} {rua}".strip()}, rua)),
        ):
            resultado = fn(*args)
            if resultado and resultado[2]:
                lat, lon, _ = resultado
                cache[endereco] = (lat, lon, "rua_numero")
                return lat, lon, "rua_numero"

        # Nível 2: só o logradouro — perde o número, mantém a rua certa.
        for fn, args in (
            (_photon, (f"{rua}, Teresina, Piaui", rua)),
            (_nominatim, ({**estruturado, "street": rua}, rua)),
        ):
            resultado = fn(*args)
            if resultado and resultado[2]:
                lat, lon, _ = resultado
                cache[endereco] = (lat, lon, "rua")
                return lat, lon, "rua"

    # Nível 3: centroide do bairro
    chave = re.sub(r"\s+", " ", (bairro_busca or "").strip().lower())
    if chave in BAIRRO_CENTROIDS:
        lat, lon = BAIRRO_CENTROIDS[chave]
        return lat, lon, "bairro"

    # Nível 4: centroide da cidade
    return CIDADE_CENTROID[0], CIDADE_CENTROID[1], "cidade"


# ============================================================================
# MAIN
# ============================================================================

def _carregar_existentes() -> dict[str, dict]:
    """Lê o CSV já coletado, indexado por URL, para permitir coleta incremental."""
    if not RAW_FILE.exists():
        return {}
    with RAW_FILE.open(encoding="utf-8") as f:
        return {r["URL_Anuncio"]: r for r in csv.DictReader(f) if r.get("URL_Anuncio")}


def main(
    max_pages_comprar: int = 40,
    max_pages_alugar: int = 20,
    limit: int | None = None,
    geocode: bool = True,
    incremental: bool = True,
) -> Path:
    """
    Executa a coleta ponta-a-ponta.

    A busca paginada para sozinha quando uma página não traz imóvel novo, então
    os limites de página são apenas um teto de segurança.

    Args:
        max_pages_comprar: teto de páginas da busca de compra.
        max_pages_alugar: teto de páginas da busca de aluguel.
        limit: limite total de imóveis (para validação rápida).
        geocode: se True, aplica a escada de geocodificação.
        incremental: preserva imóveis já coletados e só busca os novos. Evita
            refazer geocodificação, que é o passo lento (1 req/s no Nominatim).

    Returns:
        Caminho do CSV gerado.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    session = build_session()

    urls: list[str] = []
    if max_pages_comprar:
        urls += harvest_listing_urls(session, "comprar", max_pages_comprar)
    if max_pages_alugar:
        urls += harvest_listing_urls(session, "alugar", max_pages_alugar)

    existentes = _carregar_existentes() if incremental else {}
    if existentes:
        antes = len(urls)
        urls = [u for u in urls if u not in existentes]
        logger.info("[MAIN] %d já coletados, %d novos (de %d anunciados).",
                    len(existentes), len(urls), antes)

    if limit:
        urls = urls[:limit]
    logger.info("[MAIN] %d imóveis a coletar.", len(urls))

    cache = _load_geocode_cache() if geocode else {}
    rows: list[dict] = []

    for i, url in enumerate(urls, 1):
        html = fetch(session, url)
        if not html:
            continue
        row = parse_detail(html, url)
        if not row:
            continue

        if geocode:
            lat, lon, prec = geocode_escada(row["Endereco_Completo"], row["Bairro"], cache)
            row["Latitude"], row["Longitude"], row["geo_precision"] = lat, lon, prec
        else:
            row["Latitude"] = row["Longitude"] = None
            row["geo_precision"] = "none"

        rows.append(row)
        logger.info(
            "[MAIN] (%d/%d) %s | %s | R$ %s | %s | geo=%s",
            i, len(urls), row["Tipo_Imovel"] or "?", row["Bairro"] or "?",
            row["Valor_Anuncio"], row["Endereco_Completo"][:40], row["geo_precision"],
        )
        _sleep(DELAY_PAGES)

        # Persiste a cada 25 imóveis: a coleta é longa e uma queda de rede no
        # meio não pode custar meia hora de geocodificação.
        if geocode and i % 25 == 0:
            _save_geocode_cache(cache)
            _escrever_csv(existentes, rows)

    if geocode:
        _save_geocode_cache(cache)

    total = _escrever_csv(existentes, rows)
    logger.info("[MAIN] ✓ %d linhas em %s (%d novas nesta execução)",
                total, RAW_FILE, len(rows))
    _resumo_geo(existentes, rows)
    return RAW_FILE


def _escrever_csv(existentes: dict[str, dict], novos: list[dict]) -> int:
    """Grava o CSV unindo o que já existia com o coletado agora."""
    combinado = dict(existentes)
    for row in novos:
        combinado[row["URL_Anuncio"]] = row

    with RAW_FILE.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_HEADERS)
        writer.writeheader()
        for row in combinado.values():
            writer.writerow({k: row.get(k, "") for k in OUTPUT_HEADERS})
    return len(combinado)


def _resumo_geo(existentes: dict[str, dict], novos: list[dict]) -> None:
    """Loga a distribuição de precisão — é o indicador de saúde da coleta."""
    combinado = dict(existentes)
    for row in novos:
        combinado[row["URL_Anuncio"]] = row

    contagem: dict[str, int] = {}
    for row in combinado.values():
        chave = str(row.get("geo_precision") or "?")
        contagem[chave] = contagem.get(chave, 0) + 1

    total = sum(contagem.values()) or 1
    logger.info("[GEO] Precisão da geocodificação:")
    for nivel in ("rua_numero", "rua", "bairro", "cidade", "none", "?"):
        if nivel in contagem:
            logger.info("[GEO]   %-11s %4d (%.0f%%)", nivel, contagem[nivel],
                        contagem[nivel] / total * 100)


def _cli() -> None:
    import argparse

    p = argparse.ArgumentParser(description="Coletor Rocha & Rocha (Teresina)")
    p.add_argument("--paginas-comprar", type=int, default=40, help="teto de páginas de compra")
    p.add_argument("--paginas-alugar", type=int, default=20, help="teto de páginas de aluguel")
    p.add_argument("--limit", type=int, default=None, help="máximo de imóveis (validação rápida)")
    p.add_argument("--sem-geocode", action="store_true", help="pula a geocodificação")
    p.add_argument("--recomecar", action="store_true", help="ignora o CSV existente e recoleta tudo")
    a = p.parse_args()

    main(
        max_pages_comprar=a.paginas_comprar,
        max_pages_alugar=a.paginas_alugar,
        limit=a.limit,
        geocode=not a.sem_geocode,
        incremental=not a.recomecar,
    )


if __name__ == "__main__":
    _cli()
