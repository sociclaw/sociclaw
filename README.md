# SociClaw

Autonomous agent to research, plan, and generate X (Twitter) posts - with AI images and Trello/Notion sync. Credits run as off-chain SociClaw Credits.

Website: https://sociclaw.com

## Repo Structure

```
sociclaw/                   # Python package (skill logic)
  scripts/                  # research/scheduler/generators/sync/provisioning
  templates/                # post/calendar templates
  fixtures/                 # sample data
  tests/                    # pytest
api/sociclaw/provision.js   # Vercel API gateway for provisioning
src/lib/sociclaw/           # Optional TS helper SDK (topup client)
SKILL.md                    # OpenClaw skill definition (English)
SPEC.md                     # Technical notes
ROADMAP.md                  # Future work (on-chain credits, etc.)
requirements.txt            # Python deps
```

## Install (OpenClaw)

OpenClaw can load skills from:
- `~/.openclaw/skills` (global)
- `<your-workspace>/skills` (workspace-local)

So users can install by cloning this repo:

```bash
git clone https://github.com/sociclaw/sociclaw.git ~/.openclaw/skills/sociclaw
```

One-command install/update (Linux/macOS):

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/sociclaw/sociclaw/main/tools/update_sociclaw.sh)
```

## OpenClaw Config (env + settings)

OpenClaw injects per-skill env/config from `openclaw.json`. Example:

```json
{
  "skills": {
    "entries": {
      "sociclaw": {
        "env": {
          "SOCICLAW_IMAGE_API_BASE_URL": "https://api.sociclaw.com",
          "SOCICLAW_PROVISION_URL": "https://api.sociclaw.com/api/sociclaw/provision"
        },
        "config": {
          "userNiche": "crypto",
          "postingFrequency": "2/day"
        }
      }
    }
  }
}
```

## Quick Start (Python)

```powershell
cd D:\sociclaw
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
```

## Vercel Layout (Two Projects)

Use two Vercel projects:

1. `website` project (public domain `sociclaw.com`)
2. `sociclaw` project (API domain `api.sociclaw.com`)

Users/bots should call:
- `https://api.sociclaw.com/api/sociclaw/provision`

## Environment Variables

Create a `.env` at the repo root:

```bash
# X API (trend research)
XAI_API_KEY=your_x_api_key

# SociClaw image API (single-account mode)
SOCICLAW_IMAGE_API_KEY=your_sociclaw_image_api_key
SOCICLAW_IMAGE_MODEL=nano-banana

# SociClaw image API base (topup + image generation)
SOCICLAW_IMAGE_API_BASE_URL=https://api.sociclaw.com

# Recommended: provision users via your gateway (Vercel)
SOCICLAW_PROVISION_URL=https://api.sociclaw.com/api/sociclaw/provision
SOCICLAW_PROVISION_UPSTREAM_URL=https://creathoon.com/api/openclaw/provision

# Optional server-only hardening (do not distribute to end-user clients)
# SOCICLAW_INTERNAL_TOKEN=your_internal_token

# Trello (optional)
TRELLO_API_KEY=your_trello_key
TRELLO_TOKEN=your_trello_token
TRELLO_BOARD_ID=your_board_id

# Notion (optional)
NOTION_API_KEY=your_notion_key
NOTION_DATABASE_ID=your_database_id

# SociClaw Credits are off-chain; no on-chain config needed.
```

## Provisioning Gateway (API Project)

To keep `OPENCLAW_PROVISION_SECRET` server-side, deploy a small proxy:

- Source: `api/sociclaw/provision.js` (this repo, API project)
- Vercel config: `vercel.json` (API-only deploy, no vite build)
- API project env vars:
  - `OPENCLAW_PROVISION_SECRET` (required)
  - `SOCICLAW_INTERNAL_TOKEN` (optional; only for server-to-server callers you control)
  - `SOCICLAW_PROVISION_UPSTREAM_URL` (required; upstream provisioning endpoint)
  - `SOCICLAW_RATE_LIMIT_WINDOW_SECONDS` (optional; default `3600`)
  - `SOCICLAW_RATE_LIMIT_MAX_PER_IP` (optional; default `20`)
  - `SOCICLAW_RATE_LIMIT_MAX_PER_USER` (optional; default `5`)
  - `SOCICLAW_RATE_LIMIT_MAX_KEYS` (optional; default `5000`)
  - `SOCICLAW_RATE_LIMIT_DISABLED` (optional; default `false`)

If end-users call provisioning directly from their own OpenClaw runtime, leave
`SOCICLAW_INTERNAL_TOKEN` unset and enforce abuse controls on the API project
(rate limits, provider_user_id validation, monitoring).

## MVP CLI (Local)

Provision and generate an image locally:

```powershell
$env:SOCICLAW_PROVISION_URL="https://api.sociclaw.com/api/sociclaw/provision"

.\.venv\Scripts\python.exe -m sociclaw.scripts.cli provision-image-gateway --provider telegram --provider-user-id 123
.\.venv\Scripts\python.exe -m sociclaw.scripts.cli generate-image --provider telegram --provider-user-id 123 --prompt "minimal blue bird logo"
```

Preflight and Brand Brain:

```powershell
.\.venv\Scripts\python.exe -m sociclaw.scripts.cli check-env
.\.venv\Scripts\python.exe -m sociclaw.scripts.cli briefing
.\.venv\Scripts\python.exe -m sociclaw.scripts.cli setup-wizard --non-interactive --provider telegram --provider-user-id 123 --user-niche crypto --posting-frequency 2/day
.\.venv\Scripts\python.exe -m sociclaw.scripts.cli doctor
.\.venv\Scripts\python.exe -m sociclaw.scripts.cli smoke
.\.venv\Scripts\python.exe -m sociclaw.scripts.cli e2e-staging --config-path .sociclaw/runtime_config.json --state-path .tmp/sociclaw_state.json
.\.venv\Scripts\python.exe -m sociclaw.scripts.cli release-audit --strict
.\.venv\Scripts\python.exe -m sociclaw.scripts.cli trello-normalize --board-id <trello_board_id>
.\.venv\Scripts\python.exe -m sociclaw.scripts.cli check-update
.\.venv\Scripts\python.exe -m sociclaw.scripts.cli self-update --yes
```

- `check-env` validates critical env/settings before setup.
- `briefing` creates/updates `.sociclaw/company_profile.md` used by content generation.
- `briefing` also captures `content_language` and optional brand-document path for better localization/context.
- Scheduler defaults to a starter plan (`14 days x 1 post/day`) to reduce first-run token/cost friction.
- If a past start date is passed, the scheduler clamps to today by default (avoids generating January posts when the user is already in February).
- Trello sync now includes an internal post marker (`SociClaw-ID`) to avoid duplicate cards on retries.
- Trello columns are now minimal and dynamic: only the current planning window months are created, stale quarter/month columns are archived, and cards auto-route to the post month list.

Topup flow (txHash):

```powershell
.\.venv\Scripts\python.exe -m sociclaw.scripts.cli topup-start --provider telegram --provider-user-id 123 --amount-usd 5
.\.venv\Scripts\python.exe -m sociclaw.scripts.cli topup-claim --provider telegram --provider-user-id 123 --tx-hash 0x... --wait
.\.venv\Scripts\python.exe -m sociclaw.scripts.cli topup-status --provider telegram --provider-user-id 123
.\.venv\Scripts\python.exe -m sociclaw.scripts.cli generate-image --provider telegram --provider-user-id 123 --prompt "test image" --dry-run
```

`--tx-hash` must be a full Base tx hash (`0x` + 64 hex chars).

Release process checklist: see `RELEASE_CHECKLIST.md`.
Creathoon integration QA script/checklist: see `CREATHOON_QA_CHECKLIST.md`.

## Auto-update for running bots

Use scheduled execution (cron/systemd timer) to let the bot update itself safely:

```bash
python -m sociclaw.scripts.cli self-update --yes || true
```

If update succeeded, restart your bot process/service.  
Recommended policy: run every 6-12 hours with `git pull --ff-only` (already enforced by `self-update`).

## Telegram Topup (txHash)

SociClaw uses a txHash topup flow: the user sends USDC to the deposit address, then returns a txHash.
We claim the deposit with txHash and credit SociClaw Credits to the user's account.

SDK: `src/lib/sociclaw/topup-sdk.ts`

Usage sketch:

```ts
import { createSociClawTopupClient } from './src/lib/sociclaw/topup-sdk';

const client = createSociClawTopupClient({
  baseUrl: process.env.SOCICLAW_IMAGE_API_BASE_URL!,
  apiKey: userApiKey,
  userAgent: 'SociClawBot/1.0',
});

// /pay
const start = await client.startTopup({ expectedAmountUsd: 5 });
// reply with: start.depositAddress + start.amountUsdcExact

// /paid <txHash>
const claim = await client.claimTopup({ sessionId: start.sessionId, txHash });
```

To persist `sessionId` per Telegram user locally (safer than JSON), use:

```py
from sociclaw.scripts.local_session_store import LocalSessionStore

store = LocalSessionStore()
store.upsert_session(telegram_user_id="123", session_id="sess_abc")
record = store.get_session("123")
```

## Roadmap

See `ROADMAP.md` for the on-chain credits plan and other future work.
