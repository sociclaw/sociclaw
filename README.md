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

## OpenClaw Config (env + settings)

OpenClaw injects per-skill env/config from `openclaw.json`. Example:

```json
{
  "skills": {
    "entries": {
      "sociclaw": {
        "env": {
          "SOCICLAW_IMAGE_API_BASE_URL": "https://sociclaw.com",
          "SOCICLAW_PROVISION_URL": "https://sociclaw.com/api/sociclaw/provision",
          "SOCICLAW_INTERNAL_TOKEN": "optional"
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

## Vercel Layout (Rewrite)

Use two Vercel projects:

1. `website` project (public domain `sociclaw.com`)
2. `sociclaw` project (API domain, e.g. `sociclaw.vercel.app`)

On the `website` project, add rewrites so `sociclaw.com/api/*` proxies to the API project:

```json
{
  "rewrites": [
    { "source": "/api/:path*", "destination": "https://sociclaw.vercel.app/api/:path*" }
  ]
}
```

With this, users/bots always call:
- `https://sociclaw.com/api/sociclaw/provision`

## Environment Variables

Create a `.env` at the repo root:

```bash
# X API (trend research)
XAI_API_KEY=your_x_api_key

# SociClaw image API (single-account mode)
SOCICLAW_IMAGE_API_KEY=your_sociclaw_image_api_key
SOCICLAW_IMAGE_MODEL=nano-banana

# SociClaw image API base (topup + image generation)
SOCICLAW_IMAGE_API_BASE_URL=https://sociclaw.com

# Recommended: provision users via your gateway (Vercel)
SOCICLAW_PROVISION_URL=https://sociclaw.com/api/sociclaw/provision
SOCICLAW_INTERNAL_TOKEN=your_internal_token  # optional
SOCICLAW_PROVISION_UPSTREAM_URL=https://<upstream-provider>/api/app-router?action=openclaw-provision

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
- API project env vars:
  - `OPENCLAW_PROVISION_SECRET` (required)
  - `SOCICLAW_INTERNAL_TOKEN` (optional; protects the endpoint)
  - `SOCICLAW_PROVISION_UPSTREAM_URL` (required; upstream provisioning endpoint)

## MVP CLI (Local)

Provision and generate an image locally:

```powershell
$env:SOCICLAW_PROVISION_URL="https://sociclaw.com/api/sociclaw/provision"
$env:SOCICLAW_INTERNAL_TOKEN="..."

.\.venv\Scripts\python.exe -m sociclaw.scripts.cli provision-image-gateway --provider telegram --provider-user-id 123
.\.venv\Scripts\python.exe -m sociclaw.scripts.cli generate-image --provider telegram --provider-user-id 123 --prompt "minimal blue bird logo"
```

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
