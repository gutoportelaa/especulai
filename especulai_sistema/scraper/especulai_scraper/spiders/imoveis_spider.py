import scrapy
import random


class ImoveisSpider(scrapy.Spider):
    name = "imoveis"

    # Para teste, vamos gerar dados de exemplo ao invés de fazer scraping real
    def start_requests(self):
        # Gerar dados de exemplo para teste
        bairros = ['Copacabana', 'Ipanema', 'Leblon', 'Botafogo', 'Flamengo', 'Tijuca', 'Barra da Tijuca']
        tipos = ['Apartamento', 'Casa', 'Cobertura', 'Studio']
        cidades = ['Rio de Janeiro', 'Niterói', 'São Gonçalo']
        
        for i in range(20):  # Gerar 20 imóveis de exemplo
            item = {
                'preco': f"R$ {random.randint(200000, 2000000):,}",
                'area': f"{random.randint(30, 200)} m²",
                'quartos': str(random.randint(1, 5)),
                'banheiros': str(random.randint(1, 4)),
                'tipo': random.choice(tipos),
                'bairro': random.choice(bairros),
                'cidade': random.choice(cidades)
            }
            yield item


