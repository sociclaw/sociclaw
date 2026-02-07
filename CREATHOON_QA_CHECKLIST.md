# Creathoon Integration QA Checklist

Use this checklist to validate `SociClaw -> Creathoon` provisioning, image generation, and topup.

## Required Variables

```bash
CREATHOON_BASE="https://creathoon.com"
OPENCLAW_SECRET="<OPENCLAW_PROVISION_SECRET>"
TG_ID="123456789"
```

## QA-1 Provision (expect `200` + `api_key` or `image_api_key`)

```bash
curl -i -X POST "$CREATHOON_BASE/api/openclaw/provision" \
  -H "Content-Type: application/json" \
  -H "x-openclaw-secret: $OPENCLAW_SECRET" \
  -d "{\"provider\":\"telegram\",\"provider_user_id\":\"$TG_ID\",\"create_api_key\":true}"
```

Save returned API key in `API_KEY`.

## QA-2 Generate Start (expect `201` + `job_id`)

```bash
curl -i -X POST "$CREATHOON_BASE/api/v1?path=generate" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"prompt\":\"Turn this image into a cinematic sci-fi painting\",\"image_url\":\"https://picsum.photos/seed/creathoon/768/768\"}"
```

Save returned `job_id` in `JOB_ID`.

## QA-3 Job Poll (expect `200`; `status=processing|completed`)

```bash
curl -i "$CREATHOON_BASE/api/v1/jobs/$JOB_ID" \
  -H "Authorization: Bearer $API_KEY"
```

When completed, response should include `result_url`.

## QA-4 Topup Start (expect `200` + `sessionId` + `depositAddress`)

```bash
curl -i -X POST "$CREATHOON_BASE/api/v1?path=account/topup/start" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"expectedAmountUsd\":1.23,\"chain\":\"base\",\"tokenSymbol\":\"USDC\"}"
```

Save returned `sessionId` in `SESSION_ID`.

## QA-5 Topup Status (expect `200` + `status`)

```bash
curl -i "$CREATHOON_BASE/api/v1?path=account/topup/status&sessionId=$SESSION_ID" \
  -H "Authorization: Bearer $API_KEY"
```

Expected status: `pending|confirmed|credited`.

## QA-6 Topup Claim (expect `credited` OR pending states)

```bash
curl -i -X POST "$CREATHOON_BASE/api/v1?path=account/topup/claim" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"sessionId\":\"$SESSION_ID\",\"txHash\":\"0xa1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1\"}"
```

## Report Format

- QA-1: HTTP + returned API key fields (`api_key`/`image_api_key`)
- QA-2: HTTP + `job_id`
- QA-3: final `status` + `result_url` (if completed)
- QA-4: HTTP + `sessionId` + `depositAddress`
- QA-5: status
- QA-6: claim status (`credited|pending|confirming|confirmed`) + error if any
