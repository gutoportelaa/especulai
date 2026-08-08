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
from datetime import datetime
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


def _nominatim(address: str) -> tuple[float, float] | None:
    """Geocodifica via Nominatim (respeita política de uso)."""
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": address, "format": "json", "limit": 1, "countrycodes": "br"},
            headers={"User-Agent": "EspeculaiTeresina/1.0 (pesquisa academica)"},
            timeout=REQUEST_TIMEOUT,
        )
        time.sleep(NOMINATIM_DELAY)
        data = resp.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except (requests.RequestException, ValueError, KeyError) as exc:
        logger.warning("[GEO] Nominatim falhou para '%s': %s", address, exc)
    return None


def geocode_escada(
    endereco: str, bairro: str, cache: dict[str, tuple[float, float, str]]
) -> tuple[float | None, float | None, str]:
    """Resolve lat/lon pela escada de precisão, com cache."""
    if endereco and endereco in cache:
        return cache[endereco]

    # Nível 1: endereço completo
    if endereco:
        coord = _nominatim(endereco)
        if coord:
            result = (coord[0], coord[1], "rua")
            cache[endereco] = result
            return result

    # Nível 3: centroide do bairro
    key = re.sub(r"\s+", " ", bairro.strip().lower())
    if key in BAIRRO_CENTROIDS:
        lat, lon = BAIRRO_CENTROIDS[key]
        return lat, lon, "bairro"

    # Nível 4: centroide da cidade
    return CIDADE_CENTROID[0], CIDADE_CENTROID[1], "cidade"


# ============================================================================
# MAIN
# ============================================================================

def main(
    max_pages_comprar: int = 1,
    max_pages_alugar: int = 0,
    limit: int | None = None,
    geocode: bool = True,
) -> Path:
    """
    Executa a coleta ponta-a-ponta.

    Args:
        max_pages_comprar: páginas da busca de compra a percorrer.
        max_pages_alugar: páginas da busca de aluguel a percorrer.
        limit: limite total de imóveis (para validação rápida).
        geocode: se True, aplica a escada de geocodificação.

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

    if geocode:
        _save_geocode_cache(cache)

    with RAW_FILE.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_HEADERS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in OUTPUT_HEADERS})

    logger.info("[MAIN] ✓ %d linhas escritas em %s", len(rows), RAW_FILE)
    return RAW_FILE


if __name__ == "__main__":
    main(max_pages_comprar=1, max_pages_alugar=0, limit=8)
