BOT_NAME = "especulai_scraper"

SPIDER_MODULES = ["especulai_scraper.spiders"]
NEWSPIDER_MODULE = "especulai_scraper.spiders"

ROBOTSTXT_OBEY = False

POSTGRES_DB = "especulai_db"
POSTGRES_USER = "user"
POSTGRES_PASSWORD = "password"
POSTGRES_HOST = "db"

ITEM_PIPELINES = {
    "especulai_scraper.pipelines.PostgresPipeline": 300,
}

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"


