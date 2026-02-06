# SociClaw - OpenClaw Onboarding

Use this guide to install the skill and finish setup.

## Copy/Paste (to your agent)

If your OpenClaw agent can read URLs, paste this:

```text
Read this page and follow the onboarding steps:
https://<your-domain>/skill.md
```

## Install

Clone this repo into your OpenClaw skills folder.

Common locations:
- `~/.openclaw/skills` (global)
- `<your-workspace>/skills` (workspace-local)

Example:

```bash
git clone https://github.com/<your-org-or-user>/sociclaw ~/.openclaw/skills/sociclaw
cd ~/.openclaw/skills/sociclaw
```

## Configure

Create a `.env` at the repo root:

```bash
# X API (trend research)
XAI_API_KEY=your_x_api_key

# Recommended: provision users via your gateway (Vercel)
SOCICLAW_PROVISION_URL=https://<your-app>.vercel.app/api/sociclaw/provision
SOCICLAW_INTERNAL_TOKEN=your_internal_token  # optional
SOCICLAW_PROVISION_UPSTREAM_URL=https://<your-image-api-domain>/api/app-router?action=openclaw-provision

# Optional: single-account images (no provisioning)
SOCICLAW_IMAGE_API_KEY=your_sociclaw_image_api_key
SOCICLAW_IMAGE_MODEL=nano-banana

# SociClaw image API base
SOCICLAW_IMAGE_API_BASE_URL=https://<your-image-api-domain>

# Trello (optional)
TRELLO_API_KEY=your_trello_key
TRELLO_TOKEN=your_trello_token
TRELLO_BOARD_ID=your_board_id

# Notion (optional)
NOTION_API_KEY=your_notion_key
NOTION_DATABASE_ID=your_database_id

# SociClaw Credits are off-chain. No on-chain config needed.
```

## OpenClaw Config (recommended)

You can also inject env + config via `openclaw.json`:

```json
{
  "skills": {
    "entries": {
      "sociclaw": {
        "env": {
          "SOCICLAW_IMAGE_API_BASE_URL": "https://<your-image-api-domain>",
          "SOCICLAW_PROVISION_URL": "https://<your-app>.vercel.app/api/sociclaw/provision"
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

## Run

In OpenClaw, run:

```text
/sociclaw
```

Then follow the prompts:

```text
/sociclaw setup
```

And generate:

```text
/sociclaw plan Q1
/sociclaw generate
```

## Notes

- `OPENCLAW_PROVISION_SECRET` is **admin-only**. It must live in your backend (Vercel), never on user devices.

