"""
Coletor VivaReal (Teresina) — fonte de volume para venda e aluguel.

A OLX bloqueia clientes HTTP e navegador headless com Cloudflare (403), então a
escala vem daqui. O VivaReal é do mesmo grupo e serve o HTML da listagem com tudo
o que o modelo precisa no próprio card — não é preciso abrir a página de detalhe:
preço, condomínio, IPTU, área, quartos, banheiros, vagas, rua e bairro.

Particularidades descobertas:
  - Paginação por `?pagina=N`, 30 cards por página; passa do teto devolve 404.
  - Anúncios patrocinados reaparecem em páginas seguintes: dedup por ID.
  - O ID do anúncio está na URL (`...-id-2903351397/`).
  - Condomínio e IPTU só existem quando o anunciante preenche; ausente != zero.

Saída: data/raw_vivareal.csv, append-only e incremental (IDs já coletados são
pulados), uma linha gravada por página para poder retomar após interrupção.
"""

from __future__ import annotations

import argparse
import csv
import logging
import random
import re
import time
import unicodedata
from datetime import datetime

import requests
from bs4 import BeautifulSoup, Tag

from config.paths import DATA_ROOT

RAW_FILE = DATA_ROOT / "raw_vivareal.csv"

BASE_URL = "https://www.vivareal.com.br"
SEARCH_ROOTS = {
    "alugar": BASE_URL + "/aluguel/piaui/teresina/",
    "comprar": BASE_URL + "/venda/piaui/teresina/",
}

# O portal corta a paginação na página 50 (~1.500 anúncios por busca). Para passar
# disso a busca é fatiada por tipo e, se a fatia ainda bater o teto, por bairro.
PAGINAS_MAX_PORTAL = 50
TIPOS_RESIDENCIAIS = [
    "apartamento_residencial",
    "casa_residencial",
    "condominio_residencial",
    "kitnet_residencial",
    "flat_residencial",
    "cobertura_residencial",
]

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

OUTPUT_HEADERS = [
    "ID_Imovel",
    "Fonte",
    "Tipo_Negocio",
    "Tipo_Imovel",
    "Area_m2",
    "Quartos",
    "Banheiros",
    "Vagas_Garagem",
    "Valor_Anuncio",
    "Condominio",
    "IPTU",
    "Bairro",
    "Endereco_Completo",
    "URL_Anuncio",
    "Data_Coleta",
]

logger = logging.getLogger("scraper_vivareal")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

_ID_RE = re.compile(r"-id-(\d+)")
_SLUG_AREA_RE = re.compile(r"(\d[\d.]*)m2-(?:aluguel|venda)")
_SLUG_PRECO_RE = re.compile(r"-RS(\d+)-id-")
_SLUG_QUARTOS_RE = re.compile(r"-(\d+)-quartos?-")
_PRICE_RE = re.compile(r"R\$\s*([\d.]+)")
_COND_RE = re.compile(r"Cond\.\s*R\$\s*([\d.]+)")
_IPTU_RE = re.compile(r"IPTU\s*R\$\s*([\d.]+)")
_AREA_RE = re.compile(r"Tamanho do imóvel\s+(\d[\d.]*)\s*m²")

# O título do card é livre (o anunciante escreve o que quiser); o slug da URL não.
_TIPOS = {
    "ponto-comercial": "Ponto Comercial",
    "casa-de-condominio": "Casa de Condomínio",
    "casa-de-vila": "Casa de Vila",
    "apartamento": "Apartamento",
    "casa": "Casa",
    "sobrado": "Sobrado",
    "sala": "Sala",
    "loja": "Loja",
    "lote": "Lote",
    "terreno": "Terreno",
    "kitnet": "Kitnet",
    "studio": "Studio",
    "cobertura": "Cobertura",
    "flat": "Flat",
    "galpao": "Galpão",
    "imovel-comercial": "Imóvel Comercial",
    "edificio-residencial": "Edifício Residencial",
    "fazenda": "Fazenda",
    "sitio": "Sítio",
    "chacara": "Chácara",
    "predio": "Prédio",
}
_TIPO_SLUG_RE = re.compile(r"^(" + "|".join(sorted(_TIPOS, key=len, reverse=True)) + r")-")


def _num(texto: str | None) -> float | None:
    if not texto:
        return None
    limpo = texto.replace(".", "")
    return float(limpo) if limpo.isdigit() else None


def _rotulado(texto: str, rotulo: str) -> int | None:
    m = re.search(rf"{rotulo}\s+(\d+)", texto)
    return int(m.group(1)) if m else None


def _parse_card(card: Tag, negocio: str) -> dict[str, object] | None:
    link = card.select_one("a[href]")
    if link is None:
        return None
    href = str(link.get("href", ""))
    # Lançamentos (`/imoveis-lancamentos/`) têm outra estrutura e faixa de preço.
    if "/imovel/" not in href:
        return None
    m_id = _ID_RE.search(href)
    if m_id is None:
        return None

    slug = href.split("/imovel/", 1)[1].split("?")[0]
    titulo = str(link.get("title", ""))
    texto = card.get_text(" ", strip=True)

    m_tipo = _TIPO_SLUG_RE.match(slug)
    m_area = _AREA_RE.search(texto) or _SLUG_AREA_RE.search(slug)
    m_quartos = _SLUG_QUARTOS_RE.search(slug)
    m_preco_slug = _SLUG_PRECO_RE.search(slug)

    # "… em Rua Álvaro Freire, Cristo Rei, Teresina" — o logradouro pode faltar.
    localizacao = titulo.split(" em ", 1)[1] if " em " in titulo else ""
    partes = [p.strip() for p in localizacao.split(",") if p.strip()]
    bairro = partes[-2] if len(partes) >= 2 else ""
    rua = ", ".join(partes[:-2]) if len(partes) > 2 else ""

    sem_encargos = _IPTU_RE.sub("", _COND_RE.sub("", texto))
    m_preco = _PRICE_RE.search(sem_encargos)
    m_cond = _COND_RE.search(texto)
    m_iptu = _IPTU_RE.search(texto)

    quartos = _rotulado(texto, "Quantidade de quartos")
    if quartos is None and m_quartos:
        quartos = int(m_quartos.group(1))

    return {
        "ID_Imovel": f"vivareal-{m_id.group(1)}",
        "Fonte": "vivareal",
        "Tipo_Negocio": "aluguel" if negocio == "alugar" else "venda",
        "Tipo_Imovel": _TIPOS[m_tipo.group(1)] if m_tipo else "",
        "Area_m2": _num(m_area.group(1)) if m_area else None,
        "Quartos": quartos,
        "Banheiros": _rotulado(texto, "Quantidade de banheiros"),
        "Vagas_Garagem": _rotulado(texto, "Quantidade de vagas de garagem"),
        "Valor_Anuncio": (
            float(m_preco_slug.group(1))
            if m_preco_slug
            else _num(m_preco.group(1))
            if m_preco
            else None
        ),
        "Condominio": _num(m_cond.group(1)) if m_cond else None,
        "IPTU": _num(m_iptu.group(1)) if m_iptu else None,
        "Bairro": bairro,
        "Endereco_Completo": rua,
        "URL_Anuncio": href.split("?")[0],
        "Data_Coleta": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def _fetch(session: requests.Session, url: str) -> str | None:
    """Devolve o HTML, ou None se a página não existe (fim da paginação)."""
    for tentativa in range(1, MAX_RETRIES + 1):
        try:
            r = session.get(url, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as exc:
            logger.warning("falha de rede (%d/%d): %s", tentativa, MAX_RETRIES, exc)
            time.sleep(5 * tentativa)
            continue
        if r.status_code == 404:
            return None
        if r.status_code == 200:
            return r.text
        logger.warning("HTTP %s em %s (%d/%d)", r.status_code, url, tentativa, MAX_RETRIES)
        time.sleep(10 * tentativa)
    raise RuntimeError(f"sem resposta utilizável após {MAX_RETRIES} tentativas: {url}")


def _ids_existentes() -> set[str]:
    if not RAW_FILE.exists():
        return set()
    with RAW_FILE.open(encoding="utf-8", newline="") as f:
        return {row["ID_Imovel"] for row in csv.DictReader(f)}


def _slug_bairro(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-")


def _bairros_conhecidos() -> list[str]:
    if not RAW_FILE.exists():
        return []
    with RAW_FILE.open(encoding="utf-8", newline="") as f:
        return sorted({row["Bairro"] for row in csv.DictReader(f) if row["Bairro"]})


def coletar_fatiado(negocio: str) -> int:
    """Coleta por tipo residencial e subdivide por bairro as fatias que batem o teto."""
    total = 0
    for tipo in TIPOS_RESIDENCIAIS:
        novos, paginas = coletar(negocio, PAGINAS_MAX_PORTAL, tipo + "/")
        total += novos
        if paginas < PAGINAS_MAX_PORTAL:
            continue
        logger.info("[%s] %s bateu o teto — subdividindo por bairro", negocio, tipo)
        for bairro in _bairros_conhecidos():
            total += coletar(
                negocio, PAGINAS_MAX_PORTAL, f"bairros/{_slug_bairro(bairro)}/{tipo}/"
            )[0]
    return total


def coletar(negocio: str, max_paginas: int, caminho: str = "") -> tuple[int, int]:
    """Coleta até `max_paginas` páginas. Devolve (anúncios novos, páginas lidas com anúncios)."""
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    existentes = _ids_existentes()
    novo_arquivo = not RAW_FILE.exists()
    session = requests.Session()
    session.headers.update(HEADERS)
    gravados = 0
    lidas = 0

    with RAW_FILE.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_HEADERS)
        if novo_arquivo:
            writer.writeheader()

        for pg in range(1, max_paginas + 1):
            html = _fetch(session, f"{SEARCH_ROOTS[negocio]}{caminho}?pagina={pg}")
            if html is None:
                logger.info("[%s] página %d não existe — fim da paginação", negocio, pg)
                break

            soup = BeautifulSoup(html, "html.parser")
            cards = soup.select('[data-cy="rp-property-cd"]')
            if not cards:
                logger.info("[%s] página %d sem anúncios — fim", negocio, pg)
                break

            novos = 0
            for card in cards:
                registro = _parse_card(card, negocio)
                if registro is None or registro["ID_Imovel"] in existentes:
                    continue
                existentes.add(str(registro["ID_Imovel"]))
                writer.writerow(registro)
                novos += 1
            f.flush()
            gravados += novos
            lidas += 1
            logger.info(
                "[%s] %s página %d: %d cards, %d novos",
                negocio,
                caminho or "tudo",
                pg,
                len(cards),
                novos,
            )
            time.sleep(random.uniform(*DELAY_PAGES))

    return gravados, lidas


def main() -> None:
    parser = argparse.ArgumentParser(description="Coletor VivaReal — Teresina")
    parser.add_argument("--paginas-alugar", type=int, default=0)
    parser.add_argument("--paginas-comprar", type=int, default=0)
    parser.add_argument(
        "--fatiado",
        choices=["alugar", "comprar"],
        action="append",
        default=[],
        help="coleta por tipo e bairro para passar do teto de 50 páginas",
    )
    args = parser.parse_args()

    for negocio in args.fatiado:
        logger.info("[%s] fatiado: %d anúncios novos", negocio, coletar_fatiado(negocio))

    for negocio, paginas in (("alugar", args.paginas_alugar), ("comprar", args.paginas_comprar)):
        if paginas > 0:
            logger.info("[%s] %d anúncios novos", negocio, coletar(negocio, paginas)[0])


if __name__ == "__main__":
    main()
