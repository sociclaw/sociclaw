# SociClaw

SociClaw is an autonomous OpenClaw skill to plan and generate X (Twitter) posts, with optional image generation. Credits run as off-chain SociClaw Credits.

## Quick Start (Local Dev)

### Python (skill code)
```powershell
cd D:\sociclaw

# Create a venv (recommended)
$py = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
& $py -m venv .venv
.\\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Run tests
.\\.venv\Scripts\python.exe -m pytest -q
```

### Website (landing)
```powershell
cd D:\sociclaw\website
npm install
npm run dev
```

## Environment Variables

Create a `.env` in `D:\sociclaw`:

```bash
XAI_API_KEY=your_x_api_key

# Images (single-account mode)
SOCICLAW_IMAGE_API_KEY=your_sociclaw_image_api_key
SOCICLAW_IMAGE_MODEL=nano-banana

# SociClaw image API base
SOCICLAW_IMAGE_API_BASE_URL=https://sociclaw.com

# Recommended: provision users via your gateway (Vercel)
SOCICLAW_PROVISION_URL=https://sociclaw.com/api/sociclaw/provision
SOCICLAW_INTERNAL_TOKEN=your_internal_token  # optional
SOCICLAW_PROVISION_UPSTREAM_URL=https://sociclaw.com/api/app-router?action=openclaw-provision

# Admin-only (server-side): provisioning secret used by your gateway
OPENCLAW_PROVISION_SECRET=your_openclaw_provision_secret

TRELLO_API_KEY=your_trello_key
TRELLO_TOKEN=your_trello_token
TRELLO_BOARD_ID=your_board_id

NOTION_API_KEY=your_notion_key
NOTION_DATABASE_ID=your_database_id

# SociClaw Credits are off-chain. No on-chain config needed.
```

## What's Included (MVP)

- Trend research (X API) -> `sociclaw/scripts/research.py`
- Quarterly planner (180 ideas) -> `sociclaw/scripts/scheduler.py`
- Content generator (text + image prompt) -> `sociclaw/scripts/content_generator.py`
- Image generator (retries + local backup) -> `sociclaw/scripts/image_generator.py`
- Provisioning client (create user + API key) -> `sociclaw/scripts/provisioning_client.py`
- Trello / Notion sync -> `sociclaw/scripts/trello_sync.py`, `sociclaw/scripts/notion_sync.py`
- Credits are managed off-chain (no Base/USDC config required for MVP)
