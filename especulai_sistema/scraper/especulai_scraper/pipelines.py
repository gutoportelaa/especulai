import psycopg2
from itemadapter import ItemAdapter


class PostgresPipeline:
    def __init__(self, dbname, user, password, host):
        self.dbname = dbname
        self.user = user
        self.password = password
        self.host = host

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            dbname=crawler.settings.get("POSTGRES_DB"),
            user=crawler.settings.get("POSTGRES_USER"),
            password=crawler.settings.get("POSTGRES_PASSWORD"),
            host=crawler.settings.get("POSTGRES_HOST")
        )

    def open_spider(self, spider):
        self.conn = psycopg2.connect(dbname=self.dbname, user=self.user, password=self.password, host=self.host)
        self.cur = self.conn.cursor()
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS imoveis_raw (
                id SERIAL PRIMARY KEY,
                preco VARCHAR(255),
                area VARCHAR(255),
                quartos VARCHAR(255),
                banheiros VARCHAR(255),
                tipo VARCHAR(255),
                bairro VARCHAR(255),
                cidade VARCHAR(255)
            )
        """)
        self.conn.commit()

    def close_spider(self, spider):
        self.cur.close()
        self.conn.close()

    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        self.cur.execute("""
            INSERT INTO imoveis_raw (preco, area, quartos, banheiros, tipo, bairro, cidade)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            adapter.get("preco"),
            adapter.get("area"),
            adapter.get("quartos"),
            adapter.get("banheiros"),
            adapter.get("tipo"),
            adapter.get("bairro"),
            adapter.get("cidade"),
        ))
        self.conn.commit()
        return item


