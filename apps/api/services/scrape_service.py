from fastapi import HTTPException


def start_scrapy_task():
    """
    Serviço placeholder para disparar o scraper via API.

    O módulo original ainda não foi implementado para esta versão do projeto.
    Mantemos este stub para evitar erros de importação ao subir a API e
    sinalizamos claramente que a funcionalidade não está disponível.
    """
    raise HTTPException(
        status_code=501,
        detail="Serviço de scraping não está disponível nesta build.",
    )

