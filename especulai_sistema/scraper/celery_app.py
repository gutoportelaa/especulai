import os
from celery import Celery


celery = Celery(__name__)
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
celery.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")


@celery.task(name="start_scrapy_spider")
def start_scrapy_spider():
    import subprocess
    import pathlib
    import os

    # Navegar para o diretório do scraper
    scraper_path = pathlib.Path(__file__).resolve().parent
    os.chdir(str(scraper_path))
    
    try:
        # Usar runspider com arquivo de configuração
        result = subprocess.run([
            "scrapy", "runspider", "especulai_scraper/spiders/imoveis_spider.py",
            "-s", "SETTINGS_MODULE=temp_settings"
        ], capture_output=True, text=True, check=True)
        return {"status": "success", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        return {"status": "error", "output": e.stderr}


