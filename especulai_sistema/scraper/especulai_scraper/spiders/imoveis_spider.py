import scrapy
from ..items import ImovelItem


class ImoveisSpider(scrapy.Spider):
    name = "imoveis"

    start_urls = [
        'http://example.com/imoveis',
    ]

    def parse(self, response):
        for imovel_selector in response.css('div.imovel'):
            item = ImovelItem()
            item['preco'] = imovel_selector.css('span.preco::text').get()
            item['area'] = imovel_selector.css('span.area::text').get()
            yield item


