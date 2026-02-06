---
name: "SociClaw"
description: "An autonomous social media manager agent that researches, plans, and posts content."
homepage: https://sociclaw.xyz
user-invocable: true
disable-model-invocation: false
metadata: {"version":"0.1.0","tags":["social-media","x","twitter","automation","content","image-api","trello","notion","credits"]}
---
# SociClaw Skill

SociClaw is an AI agent dedicated to managing social media accounts autonomously. Drafts are synced to Trello/Notion, and images are generated via the SociClaw image API.

## Commands

### `/sociclaw`
Welcome message + quick help (recommended). If the user is not configured yet, start onboarding.

### `/sociclaw setup`
Configure niche, posting frequency, and integrations.

### `/sociclaw plan [quarter]`
Generate a quarterly content plan (90 days x 2 posts/day = 180 ideas).

### `/sociclaw generate`
Generate today's posts (text + image prompt + image) and attach results to Trello/Notion.

### `/sociclaw sync`
Force a sync to Trello/Notion.

### `/sociclaw status`
Show plan progress and integration status.

## Image Generation (SociClaw API)
### Provisioning (Recommended)

To auto-create users + API keys without exposing your admin secret, deploy a small gateway on your backend (Vercel) and set:

```bash
SOCICLAW_PROVISION_URL=https://<your-app>.vercel.app/api/sociclaw/provision
SOCICLAW_INTERNAL_TOKEN=your_internal_token  # optional
SOCICLAW_PROVISION_UPSTREAM_URL=https://<your-image-api-domain>/api/app-router?action=openclaw-provision
```

The gateway keeps `OPENCLAW_PROVISION_SECRET` **server-side**. End-users never see it.

### Single-Account Mode (Optional)

If you don't want provisioning, you can run images with a single API key:

```bash
SOCICLAW_IMAGE_API_KEY=your_sociclaw_image_api_key
SOCICLAW_IMAGE_MODEL=nano-banana
```

## Integrations

- **X API**: trend research and (optional) posting
- **Trello**: kanban workflow (Backlog -> Review -> Scheduled -> Published)
- **Notion**: database workflow (Draft/Review/Scheduled/Published)
- **SociClaw image API**: image generation and credit management (off-chain)

## Install

You can install skills by cloning this repo into your OpenClaw skills folder.

Typical locations:
- `~/.openclaw/skills` (global)
- `<your-workspace>/skills` (workspace-local)

Example:

```bash
git clone https://github.com/<your-org-or-user>/sociclaw ~/.openclaw/skills/sociclaw
```

Then start OpenClaw and run:

```text
/sociclaw
```

## Local Dev

```powershell
cd D:\sociclaw
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
```
