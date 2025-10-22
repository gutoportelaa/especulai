# 🐘 Guia de Configuração PostgreSQL - Especulai

## ✅ O que já foi preparado:

1. **Arquivo .env** criado com as credenciais
2. **Script SQL** (`setup_database.sql`) para criar banco e tabelas
3. **Script de teste** (`test_db_connection.py`) para verificar conexão
4. **Settings.py** do Scrapy atualizado para usar PostgreSQL

## 🚀 Próximos Passos (Execute na ordem):

### Passo 1: Configurar o Banco de Dados

Abra o **pgAdmin 4** (instalado com PostgreSQL) ou use o terminal:

**Opção A - pgAdmin 4 (Recomendado para iniciantes):**
1. Abra pgAdmin 4
2. Conecte ao servidor PostgreSQL (use a senha que definiu na instalação)
3. Clique com botão direito em "Databases" → "Create" → "Database"
4. Nome: `especulai_db`
5. Clique em "Save"

**Opção B - Terminal:**
```bash
# Conectar como superusuário postgres
psql -U postgres

# Executar o script SQL
\i setup_database.sql
```

### Passo 2: Testar Conexão

```bash
cd C:\Users\gutop\Desktop\especulai\especulai\especulai_sistema
python test_db_connection.py
```

**Resultado esperado:**
```
✅ Conexão com PostgreSQL bem-sucedida!
✅ Tabela 'imoveis_raw' encontrada!
📊 Tabela tem 0 registros
```

### Passo 3: Testar Scraper com PostgreSQL

```bash
# Configurar PYTHONPATH
$env:PYTHONPATH="C:\Users\gutop\Desktop\especulai\especulai"

# Testar scraper
python -c "from especulai_sistema.scraper.celery_app import start_scrapy_spider; result = start_scrapy_spider(); print('Resultado:', result)"
```

### Passo 4: Verificar Dados no Banco

```bash
# Conectar ao banco
psql -U especulai_user -d especulai_db

# Verificar dados
SELECT COUNT(*) FROM imoveis_raw;
SELECT * FROM imoveis_raw LIMIT 5;
```

## 🔧 Credenciais do Banco:

- **Banco:** especulai_db
- **Usuário:** especulai_user  
- **Senha:** especulai_senha_123
- **Host:** localhost
- **Porta:** 5432

## ❓ Problemas Comuns:

**Erro: "role especulai_user does not exist"**
→ Execute o script `setup_database.sql` primeiro

**Erro: "database especulai_db does not exist"**
→ Crie o banco manualmente no pgAdmin ou execute o script SQL

**Erro de conexão**
→ Verifique se o PostgreSQL está rodando (serviço postgresql)

## 🎯 Próximo Passo:

Após configurar o PostgreSQL, vamos treinar o modelo de ML com os dados coletados!

