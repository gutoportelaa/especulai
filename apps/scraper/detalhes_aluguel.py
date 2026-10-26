"""
Campos que só a página de detalhe traz, para os anúncios de aluguel do corpus: mobiliado e
comodidades.

  - VivaReal: lista estruturada de comodidades (`li.amenities-item`). Ausência da comodidade é
    lida como "não mobiliado", o que supõe que o anunciante marca o que tem.
  - Chaves na Mão: não há campo; só a descrição em texto livre, que quase nunca o menciona
    (~7% dos anúncios), então fica fora da coleta padrão (`--fontes chaves` para incluir). Mobiliado = 1 se o texto afirma,
    0 se nega ("sem móveis", "não mobiliado") e vazio se não menciona — silêncio não é negação.

Saída: data/detalhes_aluguel.csv, append-only e incremental. `Mobiliado_origem` registra qual
das duas leituras gerou o valor, porque elas não têm o mesmo significado.
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

import pandas as pd
import requests
from bs4 import BeautifulSoup

from config.paths import DATA_ROOT

OUT_FILE = DATA_ROOT / "detalhes_aluguel.csv"
CANONICO_FILE = DATA_ROOT / "canonico.csv"
HEADERS_HTTP = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}
CAMPOS = ["ID_Imovel", "Fonte", "Mobiliado", "Mobiliado_origem", "Comodidades", "Data_Coleta"]
DELAY = (6.0, 10.0)
TIMEOUT = 25
MAX_RETRIES = 5
RECUO_MAX = 900.0

_NEGA = re.compile(r"\b(?:n[aã]o\s+(?:[eé]\s+|est[aá]\s+)?mobili|sem\s+(?:m[oó]veis|mobili))", re.I)
_AFIRMA = re.compile(r"\b(?:mobili[ao]d[ao]s?|mobiliado|totalmente\s+mobili|semi.?mobili)", re.I)

logger = logging.getLogger("detalhes_aluguel")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def comodidades_vivareal(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    return [
        e.get_text(strip=True) for e in soup.select("li.amenities-item span.amenities-item-text")
    ]


def descricao_chaves(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    textos = []
    for tag in soup.find_all("script", type="application/ld+json"):
        if not tag.string:
            continue
        dados = json.loads(tag.string)
        if isinstance(dados, dict) and isinstance(dados.get("description"), str):
            textos.append(dados["description"])
    return max(textos, key=len, default="")


def mobiliado_texto(texto: str) -> int | None:
    if _NEGA.search(texto):
        return 0
    return 1 if _AFIRMA.search(texto) else None


def _espera(resposta: requests.Response, tentativa: int) -> float:
    """Segundos de recuo: obedece `Retry-After` no 429 e, sem ele, dobra a cada tentativa."""
    if resposta.status_code != 429:
        return 10.0 * tentativa
    indicado = resposta.headers.get("Retry-After", "")
    base = float(indicado) if indicado.isdigit() else 120.0 * 2 ** (tentativa - 1)
    return min(base, RECUO_MAX)


def _fetch(session: requests.Session, url: str) -> str | None:
    for tentativa in range(1, MAX_RETRIES + 1):
        try:
            r = session.get(url, timeout=TIMEOUT)
        except requests.RequestException as exc:
            logger.warning("falha de rede (%d/%d): %s", tentativa, MAX_RETRIES, exc)
            time.sleep(5 * tentativa)
            continue
        if r.status_code == 200:
            return r.text
        if r.status_code in (404, 410):
            return ""
        logger.warning("HTTP %s em %s (%d/%d)", r.status_code, url, tentativa, MAX_RETRIES)
        time.sleep(_espera(r, tentativa))
    return None


def _registro(fonte: str, id_imovel: str, html: str) -> dict[str, object]:
    base = {
        "ID_Imovel": id_imovel,
        "Fonte": fonte,
        "Data_Coleta": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    if fonte == "vivareal":
        itens = comodidades_vivareal(html)
        return base | {
            "Mobiliado": int(any(i.lower() == "mobiliado" for i in itens)) if itens else None,
            "Mobiliado_origem": "comodidade",
            "Comodidades": "|".join(itens),
        }
    return base | {
        "Mobiliado": mobiliado_texto(descricao_chaves(html)),
        "Mobiliado_origem": "texto",
        "Comodidades": "",
    }


def coletar(limite: int | None = None, fontes: tuple[str, ...] = ("vivareal",)) -> int:
    alvo = pd.read_csv(CANONICO_FILE)
    alvo = alvo[(alvo["Tipo_Negocio"] == "aluguel") & alvo["Fonte"].isin(fontes)]
    alvo = alvo[["ID_Imovel", "Fonte", "URL_Anuncio"]]
    feitos: set[str] = set()
    if OUT_FILE.exists():
        feitos = set(pd.read_csv(OUT_FILE)["ID_Imovel"])
    alvo = alvo[~alvo["ID_Imovel"].isin(feitos)]
    if limite:
        alvo = alvo.head(limite)

    session = requests.Session()
    session.headers.update(HEADERS_HTTP)
    novo = not OUT_FILE.exists()
    gravados = 0
    with OUT_FILE.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS)
        if novo:
            writer.writeheader()
        for linha in alvo.itertuples():
            url = str(linha.URL_Anuncio)
            if not url.startswith("http"):
                url = "https://www.vivareal.com.br" + url
            html = _fetch(session, url)
            if html is None:
                logger.error("sem resposta em %s — parando", url)
                break
            writer.writerow(_registro(str(linha.Fonte), str(linha.ID_Imovel), html))
            f.flush()
            gravados += 1
            if gravados % 50 == 0:
                logger.info("%d detalhes gravados", gravados)
            time.sleep(random.uniform(*DELAY))
    return gravados


def main() -> None:
    parser = argparse.ArgumentParser(description="Detalhes (mobiliado) dos anúncios de aluguel")
    parser.add_argument("--limite", type=int, default=None)
    parser.add_argument("--fontes", nargs="+", default=["vivareal"], choices=["vivareal", "chaves"])
    args = parser.parse_args()
    logger.info("FIM: %d detalhes novos", coletar(args.limite, tuple(args.fontes)))


if __name__ == "__main__":
    main()
