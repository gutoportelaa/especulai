# 🚀 Guia Passo a Passo: Treinamento do Modelo Gradient Boosting

Este guia explica como executar o treinamento do modelo de predição de preços de imóveis **localmente** (não é necessário usar Google Colab).

## 📋 Pré-requisitos

Antes de começar, certifique-se de ter:

1. **Python 3.10+** instalado
2. **Ambiente virtual** ativado (`.venv`)
3. **Dependências** instaladas
4. **Arquivo FipeZap** na raiz do projeto (`fipezap-teresina.csv`)

## 🔍 Verificação Inicial

Verifique se os arquivos necessários existem:

```bash
# Na raiz do projeto (especulai_v0.0/)
ls dados_imoveis_teresina/enriched_economic.csv  # Deve existir
ls fipezap-teresina.csv  # Deve existir
```

## 📝 Passo a Passo Completo

### **Passo 1: Ativar o Ambiente Virtual**

```powershell
# No PowerShell (Windows)
cd C:\Users\gutop\Desktop\especulai_v0.0
.\.venv\Scripts\Activate.ps1
```

Ou se estiver usando Git Bash:
```bash
source .venv/Scripts/activate
```

### **Passo 2: Verificar Dependências**

```bash
pip install -r especulai/requirements.txt
```

Principais dependências necessárias:
- `pandas`
- `numpy`
- `scikit-learn`
- `joblib`

### **Passo 3: Executar o Pipeline de Dados (se necessário)**

⚠️ **IMPORTANTE**: O arquivo `enriched_economic.csv` deve existir antes de treinar o modelo.

Se o arquivo não existir ou estiver desatualizado, execute o pipeline completo:

```bash
cd especulai/ml/pipeline
python pipeline_ml.py
```

Este script executa:
1. **Módulo 1**: Coleta de dados (scraping)
2. **Módulo 2**: Enriquecimento geoespacial
3. **Módulo 3**: Enriquecimento econômico (usa `fipezap-teresina.csv`)
4. **Módulo 4**: Limpeza e preparação final

**Tempo estimado**: 5-15 minutos (dependendo do tamanho do dataset)

### **Passo 4: Verificar o Dataset**

Antes de treinar, verifique se o dataset tem a coluna `Tipo_Negocio`:

```bash
python -c "import pandas as pd; df = pd.read_csv('dados_imoveis_teresina/enriched_economic.csv'); print('Colunas:', df.columns.tolist()); print('Tipo_Negocio:', df['Tipo_Negocio'].value_counts() if 'Tipo_Negocio' in df.columns else 'NÃO ENCONTRADO')"
```

### **Passo 5: Treinar o Modelo**

Execute o script de treinamento:

```bash
# A partir da raiz do projeto
python especulai/ml/pipeline/train_model.py
```

Ou:

```bash
cd especulai/ml/pipeline
python train_model.py
```

**O que acontece durante o treinamento:**

1. ✅ Carrega o dataset `enriched_economic.csv`
2. ✅ **Separa automaticamente** os dados de **Venda** e **Aluguel**
3. ✅ Salva o dataset de aluguel em `dados_imoveis_teresina/dataset_aluguel.csv`
4. ✅ Filtra apenas **Venda** para treinamento
5. ✅ Prepara features (área, quartos, banheiros, tipo, bairro, cidade)
6. ✅ Treina o modelo **Gradient Boosting** com parâmetros validados:
   - `n_estimators=200`
   - `learning_rate=0.1`
   - `max_depth=5`
7. ✅ Avalia o modelo (MAE, RMSE, R²)
8. ✅ Salva o modelo em `especulai/ml/artifacts/modelo_definitivo.joblib`
9. ✅ Salva o pré-processador em `especulai/ml/artifacts/preprocessador.joblib`

**Tempo estimado**: 1-5 minutos (dependendo do tamanho do dataset)

### **Passo 6: Verificar os Resultados**

Após o treinamento, verifique:

```bash
# Verificar se o modelo foi salvo
ls especulai/ml/artifacts/modelo_definitivo.joblib

# Verificar se o dataset de aluguel foi separado
ls dados_imoveis_teresina/dataset_aluguel.csv
```

## 📊 Saída Esperada

Durante o treinamento, você verá algo como:

```
=== Especulai - Treinamento Gradient Boosting (Modelo Definitivo) ===
✓ Dataset de ALUGUEL salvo: C:\Users\gutop\Desktop\especulai_v0.0\dados_imoveis_teresina\dataset_aluguel.csv (150 registros)
✓ Filtrado para VENDA: 850 registros para treinamento

=== Métricas de Desempenho (Gradient Boosting) ===
MAE : R$ 23,456.78
RMSE: R$ 28,901.23
R²  : 0.9963

✓ Modelo salvo em especulai/ml/artifacts/modelo_definitivo.joblib
✓ Pré-processador salvo em especulai/ml/artifacts/preprocessador.joblib

✓ Treinamento concluído com sucesso!
```

## ⚠️ Solução de Problemas

### Erro: "Dataset não encontrado"

**Problema**: O arquivo `enriched_economic.csv` não existe.

**Solução**:
```bash
# Execute o pipeline primeiro
cd especulai/ml/pipeline
python pipeline_ml.py
```

### Erro: "Nenhum registro de VENDA encontrado"

**Problema**: O dataset não tem registros com `Tipo_Negocio = 'Venda'`.

**Solução**: Verifique o dataset:
```bash
python -c "import pandas as pd; df = pd.read_csv('dados_imoveis_teresina/enriched_economic.csv'); print(df['Tipo_Negocio'].value_counts())"
```

### Erro: "Arquivo FipeZap não encontrado"

**Problema**: O arquivo `fipezap-teresina.csv` não está na raiz do projeto.

**Solução**: Certifique-se de que o arquivo está em:
```
especulai_v0.0/fipezap-teresina.csv
```

## 🔄 Treinamento no Google Colab (Opcional)

Se preferir usar o Google Colab para experimentação:

1. **Faça upload do notebook**:
   - `especulai/notebooks/analise_modelos.ipynb`

2. **Faça upload dos dados**:
   - `dados_imoveis_teresina/enriched_economic.csv`
   - `fipezap-teresina.csv`

3. **Execute o notebook** no Colab

⚠️ **Nota**: O treinamento local é mais rápido e não requer upload de dados grandes.

## 📌 Resumo Rápido

```bash
# 1. Ativar ambiente virtual
.\.venv\Scripts\Activate.ps1

# 2. Executar pipeline (se necessário)
cd especulai/ml/pipeline
python pipeline_ml.py

# 3. Treinar modelo
python train_model.py

# 4. Verificar resultados
ls ../artifacts/modelo_definitivo.joblib
```

## ✅ Checklist Final

- [ ] Ambiente virtual ativado
- [ ] Dependências instaladas
- [ ] Arquivo `fipezap-teresina.csv` na raiz
- [ ] Arquivo `enriched_economic.csv` existe
- [ ] Pipeline executado (se necessário)
- [ ] Modelo treinado com sucesso
- [ ] Dataset de aluguel separado
- [ ] Modelo salvo em `ml/artifacts/`

---

**Pronto!** Seu modelo está treinado e pronto para uso na API. 🎉


