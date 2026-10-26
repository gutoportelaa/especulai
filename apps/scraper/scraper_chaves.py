"""
Coletor Chaves na Mão (Teresina) — segunda fonte independente do VivaReal.

Cada página de listagem traz um JSON-LD `RealEstateListing` com os anúncios estruturados
(`offers.itemListElement`), então não há parsing de HTML nem visita ao detalhe. Além do que
o VivaReal dá, este portal entrega rua **com número**, CEP, coordenadas e o anunciante —
o que permite deduplicar entre fontes e dispensa geocodificação.

Particularidades descobertas:
  - Paginação por `?pg=N`, 15 anúncios por página. `?pagina=N` é ignorado.
  - Passando do fim a página responde 200 com lista vazia (uma sondagem na página 100 deu 403,
    não reproduzida nas páginas 79–90).
  - O tipo e o negócio só aparecem no slug da URL.
  - A área do slug às vezes difere do `floorSize` (terreno × construída?). O `floorSize` é usado
    em `Area_m2`; a do slug fica em `Area_slug_m2` para auditoria.
  - Não há condomínio, IPTU nem contagem de vagas no JSON-LD.

Saída: data/raw_chaves.csv, append-only e incremental (ID já gravado é pulado).
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import random
import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from config.paths import DATA_ROOT

RAW_FILE = DATA_ROOT / "raw_chaves.csv"

BASE_URL = "https://www.chavesnamao.com.br"
SEARCH_ROOTS = {
    "alugar": BASE_URL + "/imoveis-para-alugar/pi-teresina/",
    "comprar": BASE_URL + "/imoveis-a-venda/pi-teresina/",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}

REQUEST_TIMEOUT = 25
DELAY_PAGES = (2.0, 4.0)
MAX_RETRIES = 3
PAGINAS_MAX = 200  # só um limite de segurança; a coleta para na primeira página vazia

OUTPUT_HEADERS = [
    "ID_Imovel",
    "Fonte",
    "Tipo_Negocio",
    "Tipo_Imovel",
    "Area_m2",
    "Area_slug_m2",
    "Quartos",
    "Banheiros",
    "Valor_Anuncio",
    "Bairro",
    "Endereco_Completo",
    "CEP",
    "Latitude",
    "Longitude",
    "Anunciante",
    "URL_Anuncio",
    "Data_Coleta",
]

logger = logging.getLogger("scraper_chaves")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

_ID_RE = re.compile(r"/id-(\d+)/?$")
_SLUG_RE = re.compile(r"/imovel/(.+?)-(?:para-alugar|a-venda|para-comprar)-")
_SLUG_AREA_RE = re.compile(r"-(\d[\d.]*)m2")
_AREA_RE = re.compile(r"(\d[\d.,]*)")

_TIPOS = {
    "apartamento": "Apartamento",
    "casa": "Casa",
    "casa-de-condominio": "Casa de Condomínio",
    "sobrado": "Sobrado",
    "kitnet": "Kitnet",
    "studio": "Studio",
    "cobertura": "Cobertura",
    "flat": "Flat",
    "casa-comercial": "Casa Comercial",
    "casa-em-condominio": "Casa de Condomínio",
    "terreno-comercial": "Terreno Comercial",
    "terreno-em-condominio": "Terreno em Condomínio",
    "sala-comercial": "Sala Comercial",
    "predio": "Prédio",
    "chacara": "Chácara",
    "loft": "Loft",
    "garagem": "Garagem",
    "fazenda": "Fazenda",
    "terreno": "Terreno",
    "lote": "Lote",
    "sala": "Sala",
    "loja": "Loja",
    "galpao": "Galpão",
}


def _area(texto: object) -> float | None:
    if not isinstance(texto, str):
        return None
    m = _AREA_RE.search(texto.replace(".", "").replace(",", "."))
    return float(m.group(1)) if m else None


def _parse_oferta(oferta: dict[str, object], negocio: str) -> dict[str, object] | None:
    url = str(oferta.get("url", ""))
    m_id = _ID_RE.search(url)
    if m_id is None:
        return None
    item = oferta.get("itemOffered") or {}
    assert isinstance(item, dict)
    endereco = item.get("address") or {}
    geo = item.get("geo") or {}
    piso = item.get("floorSize") or {}
    anunciante = oferta.get("offeredBy") or {}
    assert isinstance(endereco, dict) and isinstance(geo, dict)
    assert isinstance(piso, dict) and isinstance(anunciante, dict)

    m_slug = _SLUG_RE.search(url)
    slug_tipo = m_slug.group(1) if m_slug else ""
    m_area_slug = _SLUG_AREA_RE.search(url)
    preco = oferta.get("price")
    area_slug = float(m_area_slug.group(1)) if m_area_slug else None
    rua = str(endereco.get("streetAddress", "")).strip().rstrip(",").strip()

    return {
        "ID_Imovel": f"chaves-{m_id.group(1)}",
        "Fonte": "chaves",
        "Tipo_Negocio": "aluguel" if negocio == "alugar" else "venda",
        "Tipo_Imovel": _TIPOS.get(slug_tipo, slug_tipo.replace("-", " ").title()),
        "Area_m2": _area(piso.get("unitText")) or area_slug,
        "Area_slug_m2": area_slug,
        "Quartos": item.get("numberOfBedrooms"),
        "Banheiros": item.get("numberOfBathroomsTotal"),
        "Valor_Anuncio": float(str(preco)) if preco not in (None, "") else None,
        "Bairro": endereco.get("addressLocality", ""),
        "Endereco_Completo": rua,
        "CEP": endereco.get("postalCode", ""),
        "Latitude": geo.get("latitude"),
        "Longitude": geo.get("longitude"),
        "Anunciante": anunciante.get("name", ""),
        "URL_Anuncio": url,
        "Data_Coleta": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def _ofertas(html: str) -> list[dict[str, object]]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all("script", type="application/ld+json"):
        if not tag.string:
            continue
        dados = json.loads(tag.string)
        if isinstance(dados, dict) and dados.get("@type") == "RealEstateListing":
            return list(dados.get("offers", {}).get("itemListElement", []))
    return []


def _fetch(session: requests.Session, url: str) -> str | None:
    for tentativa in range(1, MAX_RETRIES + 1):
        try:
            r = session.get(url, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as exc:
            logger.warning("falha de rede (%d/%d): %s", tentativa, MAX_RETRIES, exc)
            time.sleep(5 * tentativa)
            continue
        if r.status_code == 200:
            return r.text
        logger.warning("HTTP %s em %s (%d/%d)", r.status_code, url, tentativa, MAX_RETRIES)
        time.sleep(10 * tentativa)
    return None


def _ids_existentes() -> set[str]:
    if not RAW_FILE.exists():
        return set()
    with RAW_FILE.open(encoding="utf-8", newline="") as f:
        return {row["ID_Imovel"] for row in csv.DictReader(f)}


FATIAS_VENDA = (
    "apartamentos",
    "casas",
    "casas-em-condominio",
    "sobrados",
    "kitnets",
    "coberturas",
    "flats",
    "studios",
)


def _raiz(negocio: str, fatia: str | None) -> str:
    if fatia is None:
        return SEARCH_ROOTS[negocio]
    sufixo = "a-venda" if negocio == "comprar" else "para-alugar"
    return f"{BASE_URL}/{fatia}-{sufixo}/pi-teresina/"


def coletar(negocio: str, max_paginas: int = PAGINAS_MAX, fatia: str | None = None) -> int:
    """Coleta até a primeira página vazia. Devolve quantos anúncios novos gravou.

    `fatia` restringe a um tipo (ex.: "apartamentos") para passar do teto de 99 páginas.
    """
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    existentes = _ids_existentes()
    novo_arquivo = not RAW_FILE.exists()
    session = requests.Session()
    session.headers.update(HEADERS)
    gravados = 0

    with RAW_FILE.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_HEADERS)
        if novo_arquivo:
            writer.writeheader()

        for pg in range(1, max_paginas + 1):
            html = _fetch(session, f"{_raiz(negocio, fatia)}?pg={pg}")
            if html is None:
                logger.error("[%s] página %d sem resposta utilizável — parando", negocio, pg)
                break
            ofertas = _ofertas(html)
            if not ofertas:
                logger.info("[%s] página %d vazia — fim da paginação", negocio, pg)
                break

            novos = 0
            for oferta in ofertas:
                registro = _parse_oferta(oferta, negocio)
                if registro is None or registro["ID_Imovel"] in existentes:
                    continue
                existentes.add(str(registro["ID_Imovel"]))
                writer.writerow(registro)
                novos += 1
            f.flush()
            gravados += novos
            logger.info("[%s] página %d: %d anúncios, %d novos", negocio, pg, len(ofertas), novos)
            time.sleep(random.uniform(*DELAY_PAGES))

    return gravados


def main() -> None:
    parser = argparse.ArgumentParser(description="Coletor Chaves na Mão — Teresina")
    parser.add_argument("--alugar", action="store_true")
    parser.add_argument("--comprar", action="store_true")
    parser.add_argument(
        "--fatiado", action="store_true", help="venda por tipo, para passar do teto de páginas"
    )
    args = parser.parse_args()

    if args.fatiado:
        for fatia in FATIAS_VENDA:
            logger.info("[comprar/%s] %d anúncios novos", fatia, coletar("comprar", fatia=fatia))

    for negocio, ativo in (("alugar", args.alugar), ("comprar", args.comprar)):
        if ativo:
            logger.info("[%s] %d anúncios novos", negocio, coletar(negocio))


if __name__ == "__main__":
    main()
