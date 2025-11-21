from fastapi import APIRouter
from especulai.apps.api.services.scrape_service import start_scrapy_task


router = APIRouter()


@router.post("/api/v1/scrape/start")
async def start_scrape():
    return start_scrapy_task()


