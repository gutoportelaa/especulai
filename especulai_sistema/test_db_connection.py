#!/usr/bin/env python3
"""
Script para testar conexão com PostgreSQL
Execute este script após configurar o banco de dados
"""

import psycopg2
import os
from dotenv import load_dotenv

def test_connection():
    """Testa conexão com o banco PostgreSQL"""
    print("=== Teste de Conexão PostgreSQL ===\n")
    
    # Carrega variáveis de ambiente
    load_dotenv()
    
    try:
        # Tenta conectar ao banco
        print("Tentando conectar ao PostgreSQL...")
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB", "especulai_db"),
            user=os.getenv("POSTGRES_USER", "especulai_user"),
            password=os.getenv("POSTGRES_PASSWORD", "especulai_senha_123"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432")
        )
        
        print("✅ Conexão com PostgreSQL bem-sucedida!")
        
        # Cria cursor para executar comandos SQL
        cur = conn.cursor()
        
        # Verifica se a tabela existe
        cur.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_name = 'imoveis_raw'
        """)
        table_exists = cur.fetchone()[0] > 0
        
        if table_exists:
            print("✅ Tabela 'imoveis_raw' encontrada!")
            
            # Conta registros na tabela
            cur.execute("SELECT COUNT(*) FROM imoveis_raw;")
            count = cur.fetchone()[0]
            print(f"📊 Tabela tem {count} registros")
            
            # Mostra alguns registros de exemplo
            if count > 0:
                cur.execute("SELECT * FROM imoveis_raw LIMIT 3;")
                records = cur.fetchall()
                print("\n📋 Primeiros 3 registros:")
                for record in records:
                    print(f"   ID: {record[0]}, Preço: {record[1]}, Área: {record[2]}, Cidade: {record[6]}")
        else:
            print("❌ Tabela 'imoveis_raw' não encontrada!")
            print("   Execute o script setup_database.sql primeiro")
        
        # Fecha conexão
        cur.close()
        conn.close()
        print("\n✅ Teste concluído com sucesso!")
        
    except psycopg2.Error as e:
        print(f"❌ Erro de conexão PostgreSQL: {e}")
        print("\n🔧 Possíveis soluções:")
        print("   1. Verifique se o PostgreSQL está rodando")
        print("   2. Execute o script setup_database.sql")
        print("   3. Verifique as credenciais no arquivo .env")
        
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

if __name__ == "__main__":
    test_connection()

