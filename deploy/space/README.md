---
title: Especulai Teresina API
emoji: 🏠
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Especulai Teresina — API de inferência

Serve a faixa de preço pedido de imóveis em Teresina (PI), venda e aluguel. Metodologia e
resultados: <https://huggingface.co/gutoportelaa/especulai-teresina>.

`POST /estimar` com `{negocio, area, quartos, banheiros, vagas?, tipo, bairro}` devolve
`{preco_estimado, minimo, maximo, nivel, confianca}` e nada mais.

## Como os pesos são protegidos

- `modelo.enc` é o pacote dos dois modelos, comprimido e cifrado com **AES-256-GCM**. Sem a chave,
  o arquivo público é indistinguível de bytes aleatórios e qualquer adulteração é detectada.
- A chave (`MODEL_KEY`) é segredo do Space: não está no código nem na imagem, e os pesos só existem
  em claro na memória do processo.
- A API devolve apenas a faixa, arredondada. Há limite de consultas por IP e global, e as entradas
  são validadas (faixas de área, quartos etc.), o que encarece a cópia do modelo por consulta.
- Limite honesto: quem puder consultar muito consegue aproximar o comportamento do modelo. O
  limite de taxa reduz o risco, não o elimina.

Nenhuma entrada de usuário é registrada.
