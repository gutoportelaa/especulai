import scrapy


class ImovelItem(scrapy.Item):
    preco = scrapy.Field()
    area = scrapy.Field()
    quartos = scrapy.Field()
    banheiros = scrapy.Field()
    tipo = scrapy.Field()
    bairro = scrapy.Field()
    cidade = scrapy.Field()


