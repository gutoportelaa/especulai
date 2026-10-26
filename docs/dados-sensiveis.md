# Dados de portais: o que fica fora do git e como compartilhar

Os brutos dos portais (`data/raw_*.csv`, `data/detalhes_*.csv`) trazem nome do anunciante, rua com
número, CEP e a URL de cada anúncio. Anunciantes podem ser pessoas físicas e o conteúdo é dos
portais. Esses arquivos **não entram no git**, nem neste repositório público.

## O que é versionado

| Item | Por quê é seguro |
|---|---|
| Código dos coletores e `unificar` | não contém dados |
| `data/splits/*.csv` | só `ID_Imovel`, `ID_Grupo` e a partição; sem nome, rua, CEP ou URL |
| Modelo exportado (`especulai.json`) | parâmetros de árvores e perfis por bairro, sem anúncios |
| Relatórios | só agregados |

O `data/dataset_treino_olx_final.csv` é anterior a esta regra e traz a URL do anúncio e
centróides de bairro, sem nome nem rua. Fica como legado explícito na trava.

## Onde fica o bruto

- **Cópia de trabalho:** `data/` (ignorado pelo git), mais uma cópia local em
  `~/especulai-dados-privados/` (permissão 700, com `SHA256SUMS`).
- **Armazenamento definitivo:** dataset **privado** `gutoportelaa/especulai-dados` no Hugging Face
  (<https://huggingface.co/datasets/gutoportelaa/especulai-dados>). Os checksums foram conferidos
  após o envio e o acesso sem token responde 401. **Nunca torná-lo público.**

Para reproduzir o corpus em outra máquina:

```bash
uv run --with huggingface_hub hf download gutoportelaa/especulai-dados --repo-type dataset --local-dir data/
cd data && sha256sum -c SHA256SUMS
```

O modelo exportado, por outro lado, é público: não carrega anúncios (ver "O que é versionado").
Ele irá em um repositório de **modelo** separado, nunca no repositório de dados.

## A trava

`git config core.hooksPath .githooks` ativa `scripts/verificar_dados_sensiveis.py`, que recusa
(a) os caminhos de bruto e (b) qualquer CSV com colunas como `Anunciante`, `Endereco_Completo`
ou `CEP`. A trava depende de cada clone rodar o `git config` acima.

## Se um dia for preciso compartilhar uma base derivada

Uma base derivada (por exemplo, para outro pesquisador) tem que sair do pipeline já tratada:

1. **Minimizar.** Descartar `Anunciante`, `URL_Anuncio`, `CEP`, rua e coordenadas. O modelo de
   preço não usa nenhum deles.
2. **Generalizar o que sobra.** Trocar rua e coordenada por bairro (já é o que o modelo usa) e
   arredondar área e preço em faixas se houver bairro com poucos anúncios.
3. **Medir o risco de reidentificação** nos quase-identificadores (bairro, tipo, área, quartos),
   por k-anonimato, l-diversidade e t-closeness. Bibliotecas como pyCANON fazem isso. O
   k-anonimato sozinho é considerado uma métrica fraca.
4. **Pseudonimizar o que precisar de ligação** (por exemplo, o ID do anúncio) com HMAC-SHA256
   e chave guardada à parte. O mesmo ID gera o mesmo pseudônimo, então os joins continuam
   funcionando. Se a chave vazar, é preciso refazer tudo com outra. Pseudonimizar **não**
   anonimiza: a LGPD (art. 13, §4º) ainda trata como dado pessoal.
5. **Documentar** o método usado (trilha de auditoria / prestação de contas).

Referências: LGPD arts. 5º III, 12 e 13 §4º; minuta do Guia de Anonimização e Pseudonimização
da ANPD (consulta pública de 2024; confirmar no site da ANPD se já há versão final).
