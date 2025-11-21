# ⚡ Treinamento Rápido - Modelo Gradient Boosting

## 🎯 Comando Único (se tudo estiver pronto)

### Opção 1: Treinar com dataset OLX (recomendado - evita viés de outras fontes)

```powershell
# Na raiz do projeto (especulai_v0.0/)
.\.venv\Scripts\Activate.ps1
python especulai/ml/pipeline/train_model_olx.py
```

### Opção 2: Treinar com dataset completo (todas as fontes)

```powershell
# Na raiz do projeto (especulai_v0.0/)
.\.venv\Scripts\Activate.ps1
python especulai/ml/pipeline/train_model.py
```

## 📋 Passo a Passo Completo

### 1️⃣ Ativar Ambiente Virtual
```powershell
cd C:\Users\gutop\Desktop\especulai_v0.0
.\.venv\Scripts\Activate.ps1
```

### 2️⃣ Verificar Pré-requisitos
```powershell
# Verificar se o dataset existe
Test-Path dados_imoveis_teresina\enriched_economic.csv

# Verificar se o FipeZap existe
Test-Path fipezap-teresina.csv
```

### 3️⃣ Executar Pipeline (se necessário)
```powershell
# Se enriched_economic.csv não existir ou estiver desatualizado
cd especulai\ml\pipeline
python pipeline_ml.py
cd ..\..\..
```

### 4️⃣ Treinar o Modelo

**Opção A: Treinar apenas com dados OLX (recomendado)**
```powershell
# A partir da raiz do projeto
python especulai\ml\pipeline\train_model_olx.py
```
Este script treina o modelo usando APENAS o `dataset_fonte_olx.csv`, evitando viés de outras fontes (ex: RochaRocha).

**Opção B: Treinar com todas as fontes**
```powershell
# A partir da raiz do projeto
python especulai\ml\pipeline\train_model.py
```

## ✅ O que os Scripts Fazem Automaticamente

### `train_model_olx.py` (Recomendado)
1. ✅ Carrega `dados_imoveis_teresina/segmentos/dataset_fonte_olx.csv`
2. ✅ Extrai features categóricas do One-Hot Encoding (bairros, tipos)
3. ✅ Treina modelo APENAS com dados da fonte OLX (evita viés)
4. ✅ Salva modelo em `especulai/ml/artifacts/modelo_definitivo.joblib`

### `train_model.py` (Todas as fontes)
1. ✅ Carrega `dados_imoveis_teresina/enriched_economic.csv`
2. ✅ **Separa** dados de **Venda** e **Aluguel**
3. ✅ Salva aluguel em `dados_imoveis_teresina/dataset_aluguel.csv`
4. ✅ Treina apenas com dados de **Venda** (prioriza OLX se disponível)
5. ✅ Salva modelo em `especulai/ml/artifacts/modelo_definitivo.joblib`

## 📊 Resultado Esperado

```
=== Especulai - Treinamento Gradient Boosting (Modelo Definitivo) ===
✓ Dataset de ALUGUEL salvo: ...\dataset_aluguel.csv (XXX registros)
✓ Filtrado para VENDA: XXX registros para treinamento

=== Métricas de Desempenho (Gradient Boosting) ===
MAE : R$ XX,XXX.XX
RMSE: R$ XX,XXX.XX
R²  : 0.XXXX

✓ Modelo salvo em ...\modelo_definitivo.joblib
✓ Pré-processador salvo em ...\preprocessador.joblib

✓ Treinamento concluído com sucesso!
```

## ⚠️ Problemas Comuns

| Erro | Solução |
|------|---------|
| `Dataset não encontrado` | Execute `pipeline_ml.py` primeiro para gerar os datasets segmentados |
| `Dataset OLX não encontrado` | Verifique se `dados_imoveis_teresina/segmentos/dataset_fonte_olx.csv` existe |
| `Nenhum registro de VENDA` | Verifique a coluna `Tipo_Negocio` no dataset |
| `FipeZap não encontrado` | Coloque `fipezap-teresina.csv` na raiz do projeto |

## 📚 Documentação Completa

Para mais detalhes, consulte: `especulai/docs/GUIA_TREINAMENTO.md`

---

