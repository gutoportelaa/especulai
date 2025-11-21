import argparse
import os
import csv
import time
import json
import random
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Iterable, Union, Optional
from urllib.parse import quote_plus

import pandas as pd
import requests
from bs4 import BeautifulSoup

try:
    import cloudscraper  # type: ignore
except ImportError:  # pragma: no cover
    cloudscraper = None

# --- Configurações ---
WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
OUTPUT_DIR = WORKSPACE_ROOT / "dados_imoveis_teresina"
OUTPUT_FILE = OUTPUT_DIR / "raw_data.csv"
HEADERS = [
    'ID_Imovel',
    'Tipo_Negocio',
    'Tipo_Imovel',
    'Area_m2',
    'Quartos',
    'Banheiros',
    'Vagas_Garagem',
    'Valor_Anuncio',
    'Bairro',
    'CEP',
    'URL_Anuncio',
    'Data_Coleta',
    'Descricao',
    'Fonte',
    'Endereco_Completo',
    'Endereco_Geocode'
]

BASE_URL_TEMPLATE = "https://www.olx.com.br/imoveis/{tipo_oferta}/estado-pi/regiao-de-teresina-e-parnaiba/teresina"
DEFAULT_SEARCH_TERM = "imóvel teresina"
DEFAULT_PROPERTY_TYPES = ["1020", "1040"]  # 1020 -> Apartamento, 1040 -> Casa
DEFAULT_TIPO_OFERTA = "aluguel"
DEFAULT_FONTE_LABEL = "OLX"
REQUEST_TIMEOUT = 15
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1"
}
MAX_ADS_PER_PAGE = 60
DETAIL_SLEEP_SECONDS = (1.0, 2.5)
PAGE_SLEEP_SECONDS = (3.0, 6.0)

NUMERIC_CLEAN_REGEX = re.compile(r"[^\d,.-]")
SESSION = cloudscraper.create_scraper() if cloudscraper else requests.Session()
SESSION.headers.update(REQUEST_HEADERS)

# --- Configurações específicas Rocha & Rocha ---
ROCHA_BASE_LISTING_URL = "https://www.rochaerocha.com.br/imoveis/comprar/"
ROCHA_LISTING_DEFAULT_PARAMS = {
    "base": "2",
    "uf": "17",
    "cidade": "5676",
    "bairro": "",
    "tipo": "",
    "valorminimo": "",
    "valormaximo": "",
    "pg": "1",
}
ROCHA_PROPERTY_TYPES = ["1", "12"]  # 1 -> Apartamentos, 12 -> Casas/Condomínios
ROCHA_FONTE_LABEL = "RochaRocha"
ROCHA_OUTPUT_FILE = OUTPUT_DIR / "rocha_rocha_raw.csv"
ROCHA_ADDRESS_PATTERN = re.compile(r'var\s+address\s*=\s*"([^"]+)"', re.IGNORECASE)

def setup_environment():
    """Cria o diretório de saída e o arquivo CSV se não existirem."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not OUTPUT_FILE.exists():
        with OUTPUT_FILE.open('w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(HEADERS)
    else:
        _ensure_schema_alignment()
    print(f"Ambiente configurado. Dados serão salvos em: {OUTPUT_FILE}")


def _ensure_schema_alignment():
    """Garante que o CSV existente possua todas as colunas esperadas."""
    try:
        df = pd.read_csv(OUTPUT_FILE)
    except pd.errors.EmptyDataError:
        df = pd.DataFrame(columns=HEADERS)

    updated = False
    for col in HEADERS:
        if col not in df.columns:
            df[col] = "Desconhecida" if col == 'Fonte' else ""
            updated = True

    if set(df.columns) != set(HEADERS):
        df = df[[col for col in HEADERS]]
        updated = True

    if updated:
        df.to_csv(OUTPUT_FILE, index=False)
        print("Schema do arquivo raw_data.csv atualizado para incluir todas as colunas.")


def _build_page_url(tipo_oferta: str, search_term: str, property_types: List[str], page_number: int) -> str:
    """Monta a URL completa com filtros (oferta, busca, tipos, paginação)."""
    tipo_normalized = tipo_oferta.lower().strip()
    if tipo_normalized not in {"venda", "aluguel"}:
        raise ValueError("tipo_oferta deve ser 'venda' ou 'aluguel'")

    base_url = BASE_URL_TEMPLATE.format(tipo_oferta=tipo_normalized)
    query_parts = []

    if search_term:
        query_parts.append(f"q={quote_plus(search_term)}")

    for property_type in property_types or []:
        query_parts.append(f"ret={quote_plus(str(property_type))}")

    if page_number > 1:
        query_parts.append(f"o={page_number}")

    if not query_parts:
        return base_url

    return f"{base_url}?{'&'.join(query_parts)}"


def _request_html(url: str) -> str:
    """Realiza uma requisição GET e retorna o HTML."""
    response = SESSION.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.text


def _coerce_float(value: Union[str, int, float, None]) -> float:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = NUMERIC_CLEAN_REGEX.sub("", value)
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _coerce_int(value: Union[str, int, float, None]) -> int:
    float_value = _coerce_float(value)
    return int(float_value) if float_value is not None else None


def _normalize_cep_string(value: Union[str, None]) -> str:
    if not value:
        return ""
    digits = re.sub(r"\D", "", str(value))
    if len(digits) == 8:
        return f"{digits[:5]}-{digits[5:]}"
    return digits or str(value).strip()


def _extract_bairro_from_location(text: Optional[str]) -> str:
    if not text:
        return ""

    cleaned = re.sub(r"\d{2}\.\d{3}-\d{3}", "", text)
    cleaned = re.sub(r"\d{5}-\d{3}", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    segments = [segment.strip() for segment in re.split(r"[-,]", cleaned) if segment.strip()]
    if not segments:
        return ""

    for segment in reversed(segments):
        normalized = segment.lower()
        if not segment:
            continue
        if normalized.isdigit():
            continue
        if len(segment) == 2 and segment.isalpha():
            continue
        if "teresina" in normalized:
            continue
        return segment

    return segments[-1]


def _extract_json_payload(html: str) -> Dict[str, Any]:
    """Extrai o payload JSON do script principal (Next.js / Nuxt)."""
    soup = BeautifulSoup(html, "html.parser")

    # Next.js padrão
    next_data = soup.find("script", id="__NEXT_DATA__")
    if next_data and next_data.string:
        try:
            return json.loads(next_data.string)
        except json.JSONDecodeError:
            pass

    # Fallback: procura scripts que contenham window.__NUXT__ ou estruturas similares
    for script in soup.find_all("script"):
        if not script.string:
            continue
        content = script.string.strip()
        if "window.__NUXT__" in content:
            try:
                json_str = content.split("window.__NUXT__=")[1]
                if json_str.endswith(";"):
                    json_str = json_str[:-1]
                return json.loads(json_str)
            except (IndexError, json.JSONDecodeError):
                continue

    return {}


def _extract_property_attribute(data: Dict[str, Any], candidate_names: Iterable[str]):
    """Busca atributos dentro da lista 'properties' retornada pela OLX."""
    props = data.get("properties")
    if not isinstance(props, list):
        return None

    names = {name.lower() for name in candidate_names}
    for prop in props:
        name = str(prop.get("name", "")).lower()
        if name in names:
            return prop.get("value")
    return None


def _iter_dicts(node: Any) -> Iterable[Dict[str, Any]]:
    """Itera recursivamente sobre todos os dicionários de uma estrutura."""
    stack = [node]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            yield current
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)


def _extract_ads_from_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Procura candidatos a anúncios dentro do payload JSON."""
    ads = []
    seen_ids = set()

    for candidate in _iter_dicts(payload):
        list_id = candidate.get("listId") or candidate.get("ad_id") or candidate.get("id")
        price = candidate.get("price") or candidate.get("priceValue") or candidate.get("price_total")
        title = candidate.get("title") or candidate.get("subject")

        if not list_id or not price or not title:
            continue

        if list_id in seen_ids:
            continue

        seen_ids.add(list_id)
        ads.append(candidate)

        if len(ads) >= MAX_ADS_PER_PAGE:
            break

    return ads


def _extract_listing_urls_from_dom(html: str) -> List[str]:
    """Extrai URLs de anúncios a partir da estrutura de componentes da página."""
    soup = BeautifulSoup(html, "html.parser")
    selectors = [
        'a[data-ds-component="DS-AdCard"]',
        'a[data-testid="ad-card-link"]',
        'a[data-lurker_list_id]'
    ]

    urls: List[str] = []
    seen = set()
    for selector in selectors:
        for anchor in soup.select(selector):
            href = anchor.get("href")
            if not href:
                continue
            if href.startswith("//"):
                href = f"https:{href}"
            elif href.startswith("/"):
                href = f"https://www.olx.com.br{href}"

            if href.startswith("http") and href not in seen:
                seen.add(href)
                urls.append(href)

    return urls


def _extract_location(data: Dict[str, Any]) -> Dict[str, Any]:
    location = {}
    raw_location = data.get("location") or data.get("address")
    if isinstance(raw_location, dict):
        location.update(raw_location)
    elif isinstance(raw_location, str):
        parts = [part.strip() for part in raw_location.split(",") if part.strip()]
        if len(parts) >= 2:
            location["city"] = parts[0]
            location["neighbourhood"] = parts[1]

    details = data.get("locationDetails") or data.get("realEstate", {}).get("address")
    if isinstance(details, dict):
        location.update(details)

    return location


def _safe_get(obj: Dict[str, Any], *keys, default=None):
    current = obj
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return current if current is not None else default


def _normalize_business(data: Dict[str, Any]) -> str:
    business = data.get("business") or _safe_get(data, "category", "business")
    if isinstance(business, str):
        return "Venda" if "vend" in business.lower() else "Aluguel"
    if isinstance(business, dict):
        label = business.get("label") or business.get("name")
        if label:
            return "Venda" if "vend" in label.lower() else "Aluguel"
    # Assume aluguel para o link específico
    return "Aluguel"


def _normalize_property_type(data: Dict[str, Any]) -> str:
    tipo = _safe_get(data, "category", "label") or _safe_get(data, "category", "name")
    if not tipo:
        tipo = _safe_get(data, "properties", "property_type") or data.get("type")
    return tipo or "Imóvel"


def _normalize_description(data: Dict[str, Any]) -> str:
    description = data.get("description") or data.get("body")
    if description:
        return description.strip()
    return ""


def _normalize_bairro(location: Dict[str, Any]) -> str:
    bairro = (
        location.get("neighbourhood")
        or location.get("suburb")
        or _safe_get(location, "addressComponents", "neighbourhood")
    )
    if bairro:
        return bairro.strip()
    return location.get("city") or ""


def _normalize_cep(location: Dict[str, Any]) -> str:
    cep = (
        location.get("zip_code")
        or location.get("postal_code")
        or _safe_get(location, "addressComponents", "zipCode")
    )
    if not cep:
        return ""
    cep_digits = re.sub(r"\D", "", cep)
    if len(cep_digits) == 8:
        return f"{cep_digits[:5]}-{cep_digits[5:]}"
    return cep


def _normalize_rooms(data: Dict[str, Any], field_names: Iterable[str]) -> int:
    for field in field_names:
        value = data.get(field) or _safe_get(data, "realEstate", field) or _safe_get(data, "real_estate_data", field)
        if value is not None:
            coerced = _coerce_int(value)
            if coerced is not None:
                return coerced

    property_value = _extract_property_attribute(data, field_names)
    if property_value is not None:
        coerced = _coerce_int(property_value)
        if coerced is not None:
            return coerced
    return 0


def _normalize_area(data: Dict[str, Any]) -> float:
    area = (
        data.get("usableAreas")
        or data.get("usableArea")
        or _safe_get(data, "realEstate", "usableArea")
        or _safe_get(data, "real_estate_data", "usable_area")
        or data.get("size")
    )

    if isinstance(area, list) and area:
        area = area[0]
    if area is None:
        area = _extract_property_attribute(
            data,
            ["usable_area", "usableAreas", "usableArea", "size", "building_size"]
        )

    return _coerce_float(area)


def _normalize_price(data: Dict[str, Any]) -> float:
    price = data.get("price") or data.get("priceValue") or _safe_get(data, "pricing", "price")
    if isinstance(price, dict):
        value = price.get("value") or price.get("amount")
        if value is None and price.get("label"):
            value = price["label"]
        return _coerce_float(value)
    return _coerce_float(price)


def _build_property_record(
    ad: Dict[str, Any],
    default_tipo_negocio: str = "",
    source_url: str = "",
    fonte_label: str = DEFAULT_FONTE_LABEL
) -> Dict[str, Any]:
    location = _extract_location(ad)
    now = datetime.now().strftime("%Y-%m-%d")

    record = {
        'ID_Imovel': ad.get("listId") or ad.get("id") or ad.get("ad_id") or random.randint(100000, 999999),
        'Tipo_Negocio': _normalize_business(ad),
        'Tipo_Imovel': _normalize_property_type(ad),
        'Area_m2': _normalize_area(ad),
        'Quartos': _normalize_rooms(ad, ["bedrooms", "rooms", "bedroom"]),
        'Banheiros': _normalize_rooms(ad, ["bathrooms", "bathroom"]),
        'Vagas_Garagem': _normalize_rooms(ad, ["parkingSpaces", "garages", "garage"]),
        'Valor_Anuncio': _normalize_price(ad),
        'Bairro': _normalize_bairro(location),
        'CEP': _normalize_cep(location),
        'URL_Anuncio': ad.get("url") or ad.get("permalink") or ad.get("adLink") or source_url,
        'Data_Coleta': now,
        'Descricao': _normalize_description(ad),
        'Fonte': fonte_label
    }

    if not record['Tipo_Negocio'] and default_tipo_negocio:
        record['Tipo_Negocio'] = default_tipo_negocio

    # Garantias mínimas
    if not record['URL_Anuncio']:
        slug = ad.get("friendly_url") or ad.get("slug")
        if slug:
            record['URL_Anuncio'] = f"https://www.olx.com.br/busca?q={slug}"

    return record


def extract_property_data_from_listing(page_html: str, default_tipo_negocio: str, fonte_label: str) -> List[Dict[str, Any]]:
    payload = _extract_json_payload(page_html)
    ads = _extract_ads_from_payload(payload)

    records: List[Dict[str, Any]] = []
    for ad in ads:
        record = _build_property_record(
            ad,
            default_tipo_negocio=default_tipo_negocio,
            fonte_label=fonte_label
        )
        if record['Valor_Anuncio'] and record['Area_m2']:
            records.append(record)

    return records


def _fetch_detail_record(url: str, default_tipo_negocio: str, fonte_label: str) -> Dict[str, Any]:
    """Busca dados completos acessando a página do anúncio."""
    try:
        html = _request_html(url)
    except requests.RequestException as exc:
        print(f"    - Falha ao acessar anúncio {url}: {exc}")
        return None

    payload = _extract_json_payload(html)
    ads = _extract_ads_from_payload(payload)

    for ad in ads:
        record = _build_property_record(
            ad,
            default_tipo_negocio=default_tipo_negocio,
            source_url=url,
            fonte_label=fonte_label
        )
        if record['Valor_Anuncio'] and record['Area_m2']:
            return record

    return None


# --- Rocha & Rocha helpers ------------------------------------------------- #

def _parse_rocha_listing_card(card) -> Dict[str, Any]:
    data: Dict[str, Any] = {
        "summary_features": [li.get_text(" ", strip=True) for li in card.select(".facilities-list li")]
    }

    link = card.select_one("h2.title a")
    if link and link.get("href"):
        data["detail_url"] = link["href"].strip()
        data["title"] = link.get_text(strip=True)

    code = card.select_one(".properties-cod")
    if code:
        code_digits = re.sub(r"\D", "", code.get_text())
        if code_digits:
            data["id"] = code_digits

    if not data.get("id") and data.get("detail_url"):
        match = re.search(r"/(\d+)/?$", data["detail_url"])
        if match:
            data["id"] = match.group(1)

    price = card.select_one(".property-price")
    if price:
        data["price"] = price.get_text(strip=True)

    tipo = card.select_one(".property-tipo")
    if tipo:
        data["tipo_imovel"] = tipo.get_text(strip=True)

    bairro_tag = card.select_one(".property-tag.bairro")
    if bairro_tag:
        data["bairro"] = bairro_tag.get_text(strip=True)

    address = card.select_one("h3.property-address")
    if address:
        address_text = address.get_text(" ", strip=True)
        data["raw_address"] = address_text
        data["cep"] = _normalize_cep_string(address_text)

    return data


def _extract_rocha_total_pages(soup: BeautifulSoup) -> Optional[int]:
    pages = []
    for link in soup.select("ul.pagination li a"):
        text = link.get_text(strip=True)
        if text.isdigit():
            pages.append(int(text))
    if pages:
        return max(pages)
    return None


def _extract_reference_text(container: Optional[BeautifulSoup]) -> str:
    if not container:
        return ""
    strong = container.find("strong")
    if strong:
        # texto após o strong costuma conter a referência
        sibling_text = ""
        node = strong.parent.next_sibling
        while node:
            if isinstance(node, str):
                sibling_text += node
            elif hasattr(node, "get_text"):
                sibling_text += node.get_text(" ", strip=True)
            node = node.next_sibling
        return sibling_text.strip()
    return ""


def _apply_rocha_feature(text: str, target: Dict[str, Any]):
    if not text:
        return
    normalized = text.lower()
    if "quarto" in normalized or "dormit" in normalized:
        value = _coerce_int(text)
        if value is not None:
            target["Quartos"] = value
            return
    if "banheiro" in normalized:
        value = _coerce_int(text)
        if value is not None:
            target["Banheiros"] = value
            return
    if "garagem" in normalized or "vaga" in normalized:
        value = _coerce_int(text)
        if value is not None:
            target["Vagas_Garagem"] = value
            return
    if any(token in normalized for token in ("área", "area", "m²", "m2", "terreno")):
        if not target.get("Area_m2"):
            value = _coerce_float(text)
            if value is not None:
                target["Area_m2"] = value


def _fetch_rocha_detail_info(url: str) -> Optional[Dict[str, Any]]:
    try:
        html = _request_html(url)
    except requests.RequestException as exc:
        print(f"    - Falha ao acessar imóvel {url}: {exc}")
        return None

    soup = BeautifulSoup(html, "html.parser")
    detail: Dict[str, Any] = {
        "feature_texts": [li.get_text(" ", strip=True) for li in soup.select(".properties-condition li")],
        "descricao": "",
    }

    heading = soup.select_one(".heading-properties")
    if heading:
        code = heading.select_one("small strong")
        if code:
            digits = re.sub(r"\D", "", code.get_text())
            if digits:
                detail["id"] = digits
        tipo = heading.select_one(".pull-right h3 span")
        if tipo:
            detail["tipo_imovel"] = tipo.get_text(strip=True)
        location = heading.select_one(".pull-left p")
        if location:
            text = location.get_text(" ", strip=True)
            detail["heading_location"] = text
            bairro = _extract_bairro_from_location(text)
            if bairro:
                detail["bairro"] = bairro

    description = soup.select_one("#descricao .conteudo")
    if description:
        detail["descricao"] = description.get_text(" ", strip=True)

    location_block = soup.select_one("#localizacao .main-title-2")
    if location_block:
        address = location_block.find("p")
        if address:
            text = address.get_text(" ", strip=True)
            detail["full_address"] = text
            bairro = _extract_bairro_from_location(text)
            if bairro:
                detail["bairro"] = bairro
        reference_text = _extract_reference_text(location_block)
        if reference_text:
            detail["referencia"] = reference_text

    price_li = None
    for li in soup.select(".imovel-informacoes li"):
        left = li.select_one(".pull-left")
        right = li.select_one(".pull-right")
        if not left or not right:
            continue
        label = left.get_text(strip=True).lower()
        if "venda" in label or "aluguel" in label:
            price_li = li
            detail["business"] = left.get_text(strip=True).title()
            detail["price"] = right.get_text(strip=True)
            break
    if not detail.get("business"):
        detail["business"] = "Venda"

    match = ROCHA_ADDRESS_PATTERN.search(html)
    if match:
        detail["map_address"] = match.group(1).strip()
        bairro = _extract_bairro_from_location(detail["map_address"])
        if bairro and not detail.get("bairro"):
            detail["bairro"] = bairro

    return detail


def _build_rocha_record(listing_data: Dict[str, Any], fonte_label: str) -> Optional[Dict[str, Any]]:
    detail = _fetch_rocha_detail_info(listing_data.get("detail_url", ""))
    if detail is None:
        return None

    record: Dict[str, Any] = {
        "ID_Imovel": detail.get("id") or listing_data.get("id"),
        "Tipo_Negocio": detail.get("business") or "Venda",
        "Tipo_Imovel": detail.get("tipo_imovel") or listing_data.get("tipo_imovel") or "Imóvel",
        "Area_m2": None,
        "Quartos": None,
        "Banheiros": None,
        "Vagas_Garagem": None,
        "Valor_Anuncio": None,
        "Bairro": listing_data.get("bairro") or detail.get("bairro") or "",
        "CEP": listing_data.get("cep", ""),
        "URL_Anuncio": listing_data.get("detail_url", ""),
        "Data_Coleta": datetime.now().strftime("%Y-%m-%d"),
        "Descricao": detail.get("descricao", ""),
        "Fonte": fonte_label,
    }

    for feature in detail.get("feature_texts", []):
        _apply_rocha_feature(feature, record)
    for feature in listing_data.get("summary_features", []):
        _apply_rocha_feature(feature, record)

    price_text = detail.get("price") or listing_data.get("price")
    record["Valor_Anuncio"] = _coerce_float(price_text)

    if detail.get("full_address"):
        record.setdefault("Endereco_Completo", detail["full_address"])

    if detail.get("map_address"):
        record.setdefault("Endereco_Geocode", detail["map_address"])

    # Garante que campos obrigatórios existam
    if not record["Valor_Anuncio"]:
        print(f"    - Registro ignorado por ausência de preço em {record['URL_Anuncio']}")
        return None
    if record["Area_m2"] is None:
        print(f"    - Registro ignorado por ausência de área útil em {record['URL_Anuncio']}")
        return None

    return record


def scrape_rocha_rocha(
    max_pages_per_type: Optional[int] = None,
    property_type_ids: Optional[List[str]] = None,
    fonte_label: str = ROCHA_FONTE_LABEL
) -> int:
    property_type_ids = property_type_ids or ROCHA_PROPERTY_TYPES
    seen_ids: set[str] = set()
    total_records = 0

    for tipo in property_type_ids:
        print(f"\nColetando imóveis Rocha & Rocha | Tipo {tipo}")
        page = 1
        detected_pages: Optional[int] = None

        while True:
            if max_pages_per_type and page > max_pages_per_type:
                break
            if detected_pages and page > detected_pages:
                break

            params = dict(ROCHA_LISTING_DEFAULT_PARAMS)
            params["pg"] = str(page)
            params["tipo"] = tipo

            try:
                response = SESSION.get(
                    ROCHA_BASE_LISTING_URL,
                    params=params,
                    timeout=REQUEST_TIMEOUT
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                print(f"  -> Falha ao carregar página {page} para tipo {tipo}: {exc}")
                break

            soup = BeautifulSoup(response.text, "html.parser")
            if detected_pages is None:
                detected_pages = _extract_rocha_total_pages(soup)
                if detected_pages:
                    print(f"  -> {detected_pages} páginas detectadas para o tipo {tipo}.")

            cards = soup.select("div.property")
            if not cards:
                print("  -> Nenhum imóvel encontrado nesta página.")
                break

            page_records: List[Dict[str, Any]] = []
            for card in cards:
                listing_data = _parse_rocha_listing_card(card)
                detail_url = listing_data.get("detail_url")
                if not detail_url:
                    continue

                listing_id = listing_data.get("id")
                if listing_id and listing_id in seen_ids:
                    continue

                record = _build_rocha_record(listing_data, fonte_label)
                if not record:
                    continue

                if record["ID_Imovel"]:
                    seen_ids.add(str(record["ID_Imovel"]))
                page_records.append(record)
                time.sleep(random.uniform(*DETAIL_SLEEP_SECONDS))

            if page_records:
                save_data_incrementally(page_records, output_file=ROCHA_OUTPUT_FILE)
                total_records += len(page_records)
                print(f"  -> {len(page_records)} registros válidos salvos (página {page}).")
            else:
                print("  -> Nenhum registro válido nesta página.")

            page += 1

    print(f"\nColeta Rocha & Rocha concluída. Total de registros salvos: {total_records}")
    return total_records


def main_scraper_rocha(
    max_pages_per_type: Optional[int] = None,
    property_type_ids: Optional[List[str]] = None,
    fonte_label: str = ROCHA_FONTE_LABEL
):
    """Executa a coleta dedicada da imobiliária Rocha & Rocha."""
    setup_environment()
    scrape_rocha_rocha(
        max_pages_per_type=max_pages_per_type,
        property_type_ids=property_type_ids,
        fonte_label=fonte_label,
    )

def scrape_listing_page(
    page_number: int,
    tipo_oferta: str,
    search_term: str,
    property_types: List[str],
    fonte_label: str
) -> List[Dict[str, Any]]:
    """
    Coleta dados reais de uma página de listagem da OLX.
    """
    listing_url = _build_page_url(tipo_oferta, search_term, property_types, page_number)
    print(f"Coletando dados da página: {listing_url}")

    try:
        html = _request_html(listing_url)
    except requests.RequestException as exc:
        print(f"Falha ao requisitar página {page_number}: {exc}")
        return []

    default_tipo_negocio = "Venda" if tipo_oferta.lower() == "venda" else "Aluguel"
    records = extract_property_data_from_listing(html, default_tipo_negocio, fonte_label)

    if records:
        print(f"  -> {len(records)} anúncios obtidos via payload JSON.")
        return records

    print("  -> Nenhum anúncio encontrado no payload. Tentando extrair URLs dos componentes da página...")
    urls = _extract_listing_urls_from_dom(html)
    if not urls:
        print("  -> Nenhum link de anúncio identificado.")
        return []

    detail_records = []
    for url in urls:
        record = _fetch_detail_record(url, default_tipo_negocio, fonte_label)
        if record:
            detail_records.append(record)
        time.sleep(random.uniform(*DETAIL_SLEEP_SECONDS))

    print(f"  -> {len(detail_records)} anúncios obtidos via fallback nos detalhes.")
    return detail_records

def save_data_incrementally(
    data: List[Dict[str, Any]],
    output_file: Union[str, Path] = OUTPUT_FILE
):
    """Salva os dados coletados incrementalmente no arquivo CSV especificado."""
    if not data:
        return
        
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = output_path.exists() and output_path.stat().st_size > 0
    
    with output_path.open('a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        
        # Se o arquivo não existe ou está vazio, escreve o cabeçalho
        if not file_exists:
             writer.writeheader()
             
        for row in data:
            writer.writerow({k: row.get(k, '') for k in HEADERS})
    print(f"Salvos {len(data)} novos registros em {output_path}")

def main_scraper(
    num_pages: int = 3,
    tipo_oferta: str = DEFAULT_TIPO_OFERTA,
    search_term: str = DEFAULT_SEARCH_TERM,
    property_types: List[str] = None,
    fonte_label: str = DEFAULT_FONTE_LABEL
):
    """Função principal do scraper."""
    setup_environment()
    property_types = property_types or DEFAULT_PROPERTY_TYPES
    print(
        f"Iniciando coleta | Oferta: {tipo_oferta} | Fonte: {fonte_label} | Busca: '{search_term}' | "
        f"Tipos: {', '.join(property_types)} | Páginas: {num_pages}"
    )
    
    total_records = 0
    for page in range(1, num_pages + 1):
        # 1. Coleta os dados da página de listagem
        new_records = scrape_listing_page(page, tipo_oferta, search_term, property_types, fonte_label)
        if new_records:
            # 2. Salva os dados incrementalmente
            save_data_incrementally(new_records)
            total_records += len(new_records)
        else:
            print("  -> Nenhum anúncio válido encontrado nesta página.")
        
        # 3. Implementa delay aleatório para evitar bloqueio de IP
        if page < num_pages:
            delay = random.uniform(*PAGE_SLEEP_SECONDS)
            print(f"Aguardando {delay:.2f} segundos antes da próxima página...")
            time.sleep(delay)
            
    print(f"\nColeta finalizada. Total de registros coletados: {total_records}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper de imóveis (OLX / Rocha & Rocha).")
    parser.add_argument(
        "--fonte",
        choices=["olx", "rocha"],
        default="olx",
        help="Seleciona a fonte de coleta (olx ou rocha)."
    )
    parser.add_argument(
        "--num-pages",
        type=int,
        default=15,
        help="Número máximo de páginas a percorrer para cada fonte."
    )
    parser.add_argument(
        "--tipos",
        nargs="+",
        help="IDs de tipo da Rocha & Rocha (ex.: 1 12). Usado apenas com --fonte rocha."
    )
    args = parser.parse_args()

    if args.fonte == "rocha":
        main_scraper_rocha(
            max_pages_per_type=args.num_pages,
            property_type_ids=args.tipos
        )
    else:
        main_scraper(num_pages=args.num_pages)
