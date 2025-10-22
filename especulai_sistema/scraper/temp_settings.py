BOT_NAME = "especulai_scraper"

SPIDER_MODULES = ["especulai_scraper.spiders"]
NEWSPIDER_MODULE = "especulai_scraper.spiders"

ROBOTSTXT_OBEY = False

# Configuração para salvar em CSV
FEEDS = {
    'data/imoveis_raw.csv': {
        'format': 'csv',
        'encoding': 'utf8',
    }
}

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"
