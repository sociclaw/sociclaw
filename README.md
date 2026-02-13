# SociClaw

[![CI](https://github.com/sociclaw/sociclaw/actions/workflows/ci.yml/badge.svg)](https://github.com/sociclaw/sociclaw/actions/workflows/ci.yml)

SociClaw is an OpenClaw skill that helps teams produce X/Twitter content automatically:

- discovers trending topics
- plans posts
- generates text + optional images
- syncs to Trello/Notion
- supports local/managed updates for running bots

**Website:** https://sociclaw.com

---

## What this repo contains

- `sociclaw/` — Python skill (core code + CLI)
- `api/sociclaw/` — Vercel API gateway for secure provisioning
- `src/lib/sociclaw/` — Optional TypeScript helper SDK
- `templates/`, `fixtures/`, `tests/` — assets and tests

---

## Install (2 minutes)

```bash
git clone https://github.com/sociclaw/sociclaw.git ~/.openclaw/skills/sociclaw
cd ~/.openclaw/skills/sociclaw
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Then start your OpenClaw runtime and run `/sociclaw`.

For quick local tests:

```bash
python -m pytest -q
```

---

## OpenClaw setup (quick)

### 1) Minimal config

In `openclaw.json` (or your environment), set:

```json
{
  "skills": {
    "entries": {
      "sociclaw": {
        "env": {
          "SOCICLAW_IMAGE_API_BASE_URL": "https://creathoon.com",
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

### 2) Run one-time setup

```bash
python -m sociclaw.scripts.cli setup
```

You will be guided through:
- provider/user id
- niche and posting frequency
- content language
- brand logo (for image generation)
- optional integrations (Trello / Notion)

### 3) Start using commands

```bash
/sociclaw setup
/sociclaw plan
/sociclaw generate
/sociclaw pay
/sociclaw paid <tx-hash>
/sociclaw status
/sociclaw reset
```

---

## Main CLI commands (optional for dev/test)

```bash
# Provision image account (via your secure API gateway)
python -m sociclaw.scripts.cli provision-image-gateway --provider telegram --provider-user-id 123

# Create/update plan
python -m sociclaw.scripts.cli plan --sync-trello --with-image

# Generate due posts and sync
python -m sociclaw.scripts.cli generate --with-image --sync-trello

# Credits topup
python -m sociclaw.scripts.cli topup-start --provider telegram --provider-user-id 123 --amount-usd 5
python -m sociclaw.scripts.cli topup-claim --provider telegram --provider-user-id 123 --tx-hash 0x...
```

---

## Environments and secrets

### Recommended (server)

- `OPENCLAW_PROVISION_SECRET` (server-side only)
- `SOCICLAW_PROVISION_UPSTREAM_URL=https://creathoon.com/api/openclaw/provision`
- `SOCICLAW_PROVISION_URL=https://api.sociclaw.com/api/sociclaw/provision`
- `SOCICLAW_IMAGE_API_BASE_URL=https://creathoon.com`

### Optional (feature-by-feature)

- `XAI_API_KEY` (trend research)
- `SOCICLAW_IMAGE_API_KEY` (single-account mode)
- `SOCICLAW_IMAGE_MODEL` (ex: `nano-banana`)
- `TRELLO_API_KEY`, `TRELLO_TOKEN`, `TRELLO_BOARD_ID`
- `NOTION_API_KEY`, `NOTION_DATABASE_ID`

> Do **not** send `OPENCLAW_PROVISION_SECRET` to end-users.

---

## Data and behavior defaults (important)

- Default plan is starter-friendly: **14 days × 1 post/day**.
- If no logo is configured, `nano-banana` generation is skipped automatically.
- Planning starts from the current date and clamps past dates.
- Trello sync keeps board columns focused on the active window (past months are not recreated).
- A local persistent memory DB (`.sociclaw/memory.db`) tracks generated posts and improves topic variety across sessions.

---

## Update and maintenance

```bash
python -m sociclaw.scripts.cli self-update --yes
```

Run this in a scheduled job or after deploy updates; restart your bot/service afterward.

If your bot has local changes, `self-update` auto-stashes untracked/dirty files by default.

---

## Troubleshooting (fast)

- **Provision fails with 500/secret error**: check gateway envs and deploy logs.
- **Image says model needs input image**: use `nano-banana` + valid logo URL/path in setup.
- **Plan/user seems stale**: run `/sociclaw reset --yes` and setup again.

---

## Helpful docs

- `SKILL.md` (skill contract)
- `SPEC.md` (architecture notes)
- `ROADMAP.md` (future roadmap)
- `CREATHOON_QA_CHECKLIST.md` (integration test playbook)

