import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

BOT_NAME = "especulai_scraper"

SPIDER_MODULES = ["especulai_scraper.spiders"]
NEWSPIDER_MODULE = "especulai_scraper.spiders"

ROBOTSTXT_OBEY = False

# Configurações do PostgreSQL
POSTGRES_DB = os.getenv("POSTGRES_DB", "especulai_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "especulai_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "especulai_senha_123")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")

# Pipeline do PostgreSQL ativado
ITEM_PIPELINES = {
    "especulai_scraper.pipelines.PostgresPipeline": 300,
}

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"


