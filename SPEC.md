# SociClaw - Especificacao Tecnica

## Visao Geral
SociClaw e uma skill para OpenClaw que automatiza pesquisa, planejamento, geracao e publicacao de posts no X (Twitter), com imagens via API de imagem do SociClaw. Os creditos e cobrancas sao off-chain.

## Componentes
- `sociclaw/scripts/research.py`: pesquisa tendencias no X usando API v2 (tweepy).
- `sociclaw/scripts/scheduler.py`: gera planejamento trimestral (90 dias, 2 posts/dia).
- `sociclaw/scripts/content_generator.py`: gera texto otimizado e prompt de imagem.
- `sociclaw/scripts/image_generator.py`: gera imagens (provider) com controle de creditos e backup local.
- `sociclaw/scripts/provisioning_client.py`: provisiona conta/API key no provider (uso server-side).
- `sociclaw/scripts/provisioning_gateway.py`: cliente para provisionamento via gateway (recomendado).
- `api/sociclaw/provision.js`: gateway API (Vercel) que protege `OPENCLAW_PROVISION_SECRET`.
- `sociclaw/scripts/trello_sync.py`: sincroniza posts com Trello.
- `sociclaw/scripts/notion_sync.py`: sincroniza posts com Notion.
- (Opcional futuro) fluxo on-chain (ver ROADMAP.md).

## Modelos de Dados
### TrendData
- `topics`: lista de topicos em alta.
- `formats`: formatos com mais engajamento.
- `peak_hours`: horarios de pico (UTC).
- `hashtags`: hashtags relevantes.
- `sample_posts`: exemplos de posts com alta performance.

### PostPlan
- `date`: data do post.
- `time`: hora (UTC).
- `category`: categoria do post.
- `topic`: topico a ser abordado.
- `hashtags`: lista de hashtags.

### GeneratedPost
- `text`: texto final do post.
- `image_prompt`: prompt para imagem.
- `hashtags`: hashtags finais.
- `category`: categoria.
- `date`: data (YYYY-MM-DD).
- `time`: hora (0-23 UTC).

## Integracoes
### X API (tweepy)
- Endpoint: `search_recent_tweets`.
- Campos: `created_at`, `public_metrics`, `entities`.

### API de imagem (SociClaw)
- Modelo padrão: `nano-banana` (configurável).
- Gerar: `POST https://sociclaw.com/api/v1?path=generate`
- Poll: `GET https://sociclaw.com/api/v1/jobs/{job_id}`
- Saida: URL da imagem (com backup local).

### Topup (txHash)
- `POST /api/v1?path=account/topup/start` -> retorna `sessionId`, `depositAddress`, `amountUsdcExact`
- `POST /api/v1?path=account/topup/claim` -> envia `sessionId` + `txHash`
- `GET /api/v1?path=account/topup/status&sessionId=...`
- O deposito precisa bater exatamente o `amountUsdcExact` enviado no start.
- Persistencia local recomendada: SQLite em `.tmp/sociclaw_sessions.db` (ver `sociclaw/scripts/local_session_store.py`).

### Trello
- Board: `SociClaw Content Calendar`.
- Listas: Backlog, Q1/Q2/Q3/Q4 2026 (meses), Em Revisao, Agendado, Publicado.
- Campos do card: titulo, descricao, due date, labels, checklist.

### Notion
- Database properties:
  - `Titulo` (title)
  - `Conteudo` (rich_text)
  - `Data` (date)
  - `Status` (select)
  - `Categoria` (multi_select)
  - `Imagem` (files, external)
  - `Engajamento` (number)

### Creditos (off-chain)
- Os creditos sao gerenciados pela conta do usuario no SociClaw.
- SociClaw usa a API key provisionada para gerar imagens.

## Roadmap
- Creditos on-chain via USDC/Base (fora do MVP). Ver `ROADMAP.md`.

## Fluxos Principais
1. Setup inicial (nicho, frequencia, integracoes).
2. Pesquisa de tendencias (30 dias).
3. Planejamento trimestral (180 ideias).
4. Geracao diaria de texto e imagem.
5. Sincronizacao Trello/Notion.
6. Geracao de imagens com SociClaw Credits.

## Variaveis de Ambiente
- `XAI_API_KEY`
- `SOCICLAW_IMAGE_API_KEY` (recomendado; chave da conta de imagens)
- `SOCICLAW_IMAGE_MODEL` (default: `nano-banana`)
- `SOCICLAW_IMAGE_GENERATE_URL` (default: `https://sociclaw.com/api/v1?path=generate`)
- `SOCICLAW_IMAGE_JOBS_URL` (default: `https://sociclaw.com/api/v1/jobs/`)
- `SOCICLAW_IMAGE_API_BASE_URL` (usado no fluxo de topup por SDK)
- `SOCICLAW_PROVISION_URL` (recomendado; gateway no seu backend)
- `SOCICLAW_PROVISION_UPSTREAM_URL` (obrigatorio no projeto de API; endpoint upstream de provisionamento)
- `SOCICLAW_INTERNAL_TOKEN` (opcional; protege o gateway)
- `OPENCLAW_PROVISION_SECRET` (admin-only; fica só no seu backend)
- `TRELLO_API_KEY`
- `TRELLO_TOKEN`
- `TRELLO_BOARD_ID`
- `NOTION_API_KEY`
- `NOTION_DATABASE_ID`
