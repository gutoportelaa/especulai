"""
Scraper dedicado APENAS para OLX - Teresina.

Responsabilidades:
  - Coletar anúncios de venda e aluguel da OLX
  - Extrair features básicas (preço, área, quartos, etc)
  - Salvar em raw_olx.csv para posterior enriquecimento

Saída: raw_olx.csv com colunas padrão

NÃO faz: Enriquecimento, múltiplas fontes, lógica de negócio
"""

from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import csv
import json
import random
import time
import re
import logging

import requests
from bs4 import BeautifulSoup

# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT = WORKSPACE_ROOT / "dados_imoveis_teresina"
RAW_OLX_FILE = DATA_ROOT / "raw_olx.csv"
SCRAPER_LOG_FILE = DATA_ROOT / "scraper_olx_log.txt"

# URLs OLX Teresina
OLX_VENDA_BASE = "https://www.olx.com.br/imoveis/venda/estado-pi/regiao-de-teresina-e-parnaiba/teresina"
OLX_ALUGUEL_BASE = "https://www.olx.com.br/imoveis/aluguel/estado-pi/regiao-de-teresina-e-parnaiba/teresina"

# Headers para requisição
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

REQUEST_TIMEOUT = 15
DELAY_BETWEEN_PAGES = (2, 5)  # segundos (min, max) para não sobrecarregar
DELAY_BETWEEN_DETAILS = (0.5, 1.5)  # segundos

# Schema de saída
OUTPUT_HEADERS = [
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
    'Endereco_Completo'
]

# ============================================================================
# LOGGING
# ============================================================================

def setup_logging():
    """Configura logging para arquivo e console."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(SCRAPER_LOG_FILE, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# ============================================================================
# FUNÇÕES DE UTILIDADE
# ============================================================================

def setup_environment():
    """Cria diretórios e arquivo CSV base."""
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    
    if not RAW_OLX_FILE.exists():
        with RAW_OLX_FILE.open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=OUTPUT_HEADERS)
            writer.writeheader()
        logger.info(f"[SETUP] Arquivo CSV criado: {RAW_OLX_FILE}")
    else:
        logger.info(f"[SETUP] Arquivo CSV já existe: {RAW_OLX_FILE}")


def _coerce_int(value: Any) -> Optional[int]:
    """Converte valor para int, retorna None se inválido."""
    if value is None:
        return None
    try:
        # Remove caracteres não-numéricos
        clean = re.sub(r'[^\d]', '', str(value).strip())
        return int(clean) if clean else None
    except (ValueError, TypeError):
        return None


def _coerce_float(value: Any) -> Optional[float]:
    """Converte valor para float, retorna None se inválido."""
    if value is None:
        return None
    try:
        # Remove 'R$', espaços, e substitui ',' por '.'
        clean = str(value).strip()
        clean = clean.replace('R$', '').strip()
        clean = clean.replace(',', '.')
        return float(clean) if clean else None
    except (ValueError, TypeError):
        return None


def _normalize_text(value: Any, default: str = '') -> str:
    """Normaliza texto: strip, lowercase safe."""
    if not value:
        return default
    return str(value).strip()


def _sleep_random(min_sec: float, max_sec: float):
    """Aguarda tempo aleatório entre min e max segundos."""
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)


# ============================================================================
# SCRAPING
# ============================================================================

def fetch_page(url: str, tipo_negocio: str) -> List[Dict[str, Any]]:
    """
    Coleta anúncios de uma página OLX.
    
    Args:
        url: URL da página OLX
        tipo_negocio: 'venda' ou 'aluguel'
    
    Returns:
        Lista de registros extraídos
    """
    records = []
    
    try:
        logger.info(f"[FETCH] Requisitando: {url}")
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"[FETCH] Erro ao requisitar {url}: {e}")
        return records
    
    try:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # TODO: Implementar parsing específico para estrutura OLX atual
        # A estrutura HTML pode variar. Este é um exemplo genérico.
        # Você pode precisar inspecionar o HTML real e ajustar os seletores CSS.
        
        # Exemplo: buscar cards de anúncio
        ad_containers = soup.select('[data-testid="ad-card"]')
        
        logger.info(f"[FETCH] Encontrados {len(ad_containers)} anúncios na página")
        
        for idx, container in enumerate(ad_containers):
            try:
                record = _parse_ad_container(container, tipo_negocio)
                if record:
                    records.append(record)
            except Exception as e:
                logger.warning(f"[FETCH] Erro ao parsear anúncio {idx}: {e}")
                continue
        
    except Exception as e:
        logger.error(f"[FETCH] Erro ao fazer parse da página: {e}")
    
    return records


def _parse_ad_container(container, tipo_negocio: str) -> Optional[Dict[str, Any]]:
    """
    Extrai informações de um container de anúncio.
    
    NOTA: Você precisa inspecionar a estrutura HTML real da OLX e adaptar os seletores CSS aqui.
    """
    record = {
        'ID_Imovel': None,
        'Tipo_Negocio': tipo_negocio.capitalize(),
        'Tipo_Imovel': None,
        'Area_m2': None,
        'Quartos': None,
        'Banheiros': None,
        'Vagas_Garagem': None,
        'Valor_Anuncio': None,
        'Bairro': None,
        'CEP': None,
        'URL_Anuncio': None,
        'Data_Coleta': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'Descricao': '',
        'Endereco_Completo': ''
    }
    
    try:
        # Exemplo: extração de URL (ajustar seletor conforme necessário)
        link_elem = container.select_one('a[href*="/i/"]')
        if link_elem and link_elem.get('href'):
            record['URL_Anuncio'] = link_elem['href']
            record['ID_Imovel'] = record['URL_Anuncio'].split('/')[-1]
        
        # Exemplo: extração de preço
        price_elem = container.select_one('[class*="price"]')
        if price_elem:
            record['Valor_Anuncio'] = _coerce_float(price_elem.get_text())
        
        # Exemplo: extração de localização
        location_elem = container.select_one('[class*="location"]')
        if location_elem:
            record['Bairro'] = _normalize_text(location_elem.get_text())
        
        # Exemplo: extração de features
        features = container.select('[class*="feature"]')
        for feature in features:
            text = feature.get_text().lower()
            if 'm²' in text or 'm2' in text:
                record['Area_m2'] = _coerce_float(text)
            elif 'quarto' in text:
                record['Quartos'] = _coerce_int(text)
            elif 'banheiro' in text:
                record['Banheiros'] = _coerce_int(text)
        
        # Descrição
        desc_elem = container.select_one('[class*="description"]')
        if desc_elem:
            record['Descricao'] = _normalize_text(desc_elem.get_text())
        
        # Validação mínima
        if not record['URL_Anuncio'] or not record['Valor_Anuncio']:
            return None
        
        return record
        
    except Exception as e:
        logger.warning(f"[PARSE] Erro ao extrair dados do container: {e}")
        return None


def save_records(records: List[Dict[str, Any]], append: bool = True):
    """
    Salva registros no arquivo CSV.
    
    Args:
        records: Lista de dicionários
        append: Se True, append; se False, sobrescreve
    """
    if not records:
        logger.warning("[SAVE] Nenhum registro para salvar")
        return
    
    mode = 'a' if append else 'w'
    
    try:
        with RAW_OLX_FILE.open(mode, newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=OUTPUT_HEADERS)
            
            # Se é modo write, escreve header
            if mode == 'w':
                writer.writeheader()
            
            writer.writerows(records)
        
        logger.info(f"[SAVE] Salvos {len(records)} registros em {RAW_OLX_FILE}")
        
    except Exception as e:
        logger.error(f"[SAVE] Erro ao salvar registros: {e}")


# ============================================================================
# ORQUESTRAÇÃO
# ============================================================================

def main(
    num_pages_venda: int = 5,
    num_pages_aluguel: int = 5,
    clear_previous: bool = False
):
    """
    Função principal do scraper OLX.
    
    Args:
        num_pages_venda: Número de páginas para coletar VENDA
        num_pages_aluguel: Número de páginas para coletar ALUGUEL
        clear_previous: Se True, limpa dados anteriores antes de scraping
    """
    print("=" * 80)
    print("=== ESPECULAI - SCRAPER OLX (APENAS TERESINA) ===")
    print("=" * 80)
    print()
    
    setup_environment()
    
    if clear_previous and RAW_OLX_FILE.exists():
        logger.info("[MAIN] Limpando dados anteriores...")
        RAW_OLX_FILE.unlink()
        setup_environment()
    
    total_records = 0
    
    # Scraping VENDA
    logger.info("[MAIN] ===== INICIANDO SCRAPING VENDA =====")
    for page in range(1, num_pages_venda + 1):
        url = f"{OLX_VENDA_BASE}?o={page}" if page > 1 else OLX_VENDA_BASE
        logger.info(f"[MAIN] Página {page}/{num_pages_venda} (VENDA)")
        
        records = fetch_page(url, "venda")
        save_records(records, append=True)
        total_records += len(records)
        
        if page < num_pages_venda:
            delay = random.uniform(*DELAY_BETWEEN_PAGES)
            logger.info(f"[MAIN] Aguardando {delay:.1f}s antes da próxima página...")
            _sleep_random(*DELAY_BETWEEN_PAGES)
    
    # Scraping ALUGUEL
    logger.info("[MAIN] ===== INICIANDO SCRAPING ALUGUEL =====")
    for page in range(1, num_pages_aluguel + 1):
        url = f"{OLX_ALUGUEL_BASE}?o={page}" if page > 1 else OLX_ALUGUEL_BASE
        logger.info(f"[MAIN] Página {page}/{num_pages_aluguel} (ALUGUEL)")
        
        records = fetch_page(url, "aluguel")
        save_records(records, append=True)
        total_records += len(records)
        
        if page < num_pages_aluguel:
            delay = random.uniform(*DELAY_BETWEEN_PAGES)
            logger.info(f"[MAIN] Aguardando {delay:.1f}s antes da próxima página...")
            _sleep_random(*DELAY_BETWEEN_PAGES)
    
    logger.info("[MAIN] ===== SCRAPING CONCLUÍDO =====")
    print()
    print("=" * 80)
    print(f"[OK] Scraping concluído!")
    print(f"[OK] Total de registros coletados: {total_records}")
    print(f"[OK] Arquivo salvo: {RAW_OLX_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    main(num_pages_venda=3, num_pages_aluguel=3, clear_previous=False)
