# API de inferência (Cloudflare Worker)

Recebe as características do imóvel e devolve só a faixa de preço. Os pesos chegam cifrados em
`modelos/*.enc` (AES-256-GCM, gerados por `ml/pipeline/cifrar_modelo.py`) e só a chave `MODEL_KEY`,
um segredo do Worker, os abre. Visão geral e justificativa: README e CLAUDE.md na raiz.

| Rota | Função |
|---|---|
| `POST /estimar` | `{negocio, area, quartos, banheiros, vagas?, tipo, bairro}` → `{preco_estimado, minimo, maximo, nivel, confianca}` |
| `GET /saude` | 200 se os dois modelos abrem; 503 se a chave estiver ausente ou errada |

## Desenvolvimento

Requer Node 22+ (o `wrangler` recusa versões anteriores) e a chave local.

```bash
bun install
bun test                         # paridade com o sklearn, cifragem, validação, 429, CORS
make api-inferencia              # na raiz: wrangler dev em modo local, com .dev.vars (ignorado pelo git)
```

## Publicação (uma vez)

```bash
node node_modules/wrangler/bin/wrangler.js login
node node_modules/wrangler/bin/wrangler.js secret put MODEL_KEY      # cole o conteúdo de ~/especulai-dados-privados/modelo.key
make deploy-api                                                       # na raiz
curl https://especulai-api.<sua-conta>.workers.dev/saude              # deve responder {"ok":true,...}
```

Depois defina a variável `API_URL` do repositório no GitHub (Settings, Actions, Variables) com essa
URL, sem barra final. A migração do Durable Object (`Limitador`) roda no primeiro deploy.

Ajuste `ALLOWED_ORIGINS` e os limites em `wrangler.toml` se mudar o domínio do site.
