-- Script para configurar banco de dados do Especulai
-- Execute este script conectado como usuário 'postgres'

-- 1. Criar banco de dados
CREATE DATABASE especulai_db;

-- 2. Criar usuário específico para o aplicativo
CREATE USER especulai_user WITH PASSWORD 'especulai_senha_123';

-- 3. Conceder privilégios ao usuário
GRANT ALL PRIVILEGES ON DATABASE especulai_db TO especulai_user;

-- 4. Conectar ao banco especulai_db
\c especulai_db;

-- 5. Conceder permissões adicionais no schema public
GRANT ALL ON SCHEMA public TO especulai_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO especulai_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO especulai_user;

-- 6. Criar tabela para armazenar dados dos imóveis
CREATE TABLE IF NOT EXISTS imoveis_raw (
    id SERIAL PRIMARY KEY,
    preco VARCHAR(255),
    area VARCHAR(255),
    quartos VARCHAR(255),
    banheiros VARCHAR(255),
    tipo VARCHAR(255),
    bairro VARCHAR(255),
    cidade VARCHAR(255),
    data_coleta TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Conceder permissões na tabela para o usuário
GRANT ALL PRIVILEGES ON TABLE imoveis_raw TO especulai_user;
GRANT USAGE, SELECT ON SEQUENCE imoveis_raw_id_seq TO especulai_user;

-- 8. Criar índices para melhorar performance
CREATE INDEX IF NOT EXISTS idx_cidade ON imoveis_raw(cidade);
CREATE INDEX IF NOT EXISTS idx_bairro ON imoveis_raw(bairro);
CREATE INDEX IF NOT EXISTS idx_tipo ON imoveis_raw(tipo);
CREATE INDEX IF NOT EXISTS idx_data_coleta ON imoveis_raw(data_coleta);

-- 9. Verificar se tudo foi criado corretamente
\dt
\du

