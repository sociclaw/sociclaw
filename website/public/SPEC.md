# SociClaw - Technical Spec (MVP)

## Overview
SociClaw is an OpenClaw skill that automates trend research, quarterly planning, and daily post generation for X (Twitter), with optional images via the SociClaw image API. Credits run off-chain as SociClaw Credits.

## Components
- `sociclaw/scripts/research.py`: trend research via X API v2 (tweepy).
- `sociclaw/scripts/scheduler.py`: quarterly planner (90 days, 2 posts/day).
- `sociclaw/scripts/content_generator.py`: text generation + image prompt generation.
- `sociclaw/scripts/image_generator.py`: image generation with retries + local backup.
- `sociclaw/scripts/provisioning_client.py`: user + API key provisioning (server-side).
- `sociclaw/scripts/trello_sync.py`: Trello board/list/card sync.
- `sociclaw/scripts/notion_sync.py`: Notion database sync.
- (Future optional) `sociclaw/scripts/payment_handler.py`: on-chain credits flow (see ROADMAP.md).

## Data Models

### TrendData
- `topics`: top topics currently discussed
- `formats`: engagement by detected format
- `peak_hours`: peak engagement hours (UTC)
- `hashtags`: high-signal hashtags
- `sample_posts`: example posts with engagement metrics

### PostPlan
- `date`: planned publication date
- `time`: planned publication hour (UTC)
- `category`: post category
- `topic`: topic to cover
- `hashtags`: selected hashtags

### GeneratedPost
- `text`: final post text (<= 280 chars unless thread)
- `image_prompt`: image prompt (backend-specific)
- `hashtags`: final hashtags
- `category`: category
- `date`: `YYYY-MM-DD`
- `time`: hour `0-23` (UTC)

## Integrations

### X API (tweepy)
- API: v2 client
- Operation: search recent posts
- Fields: `created_at`, `public_metrics`, `entities`, `referenced_tweets`

### SociClaw image API
- Default model: `nano-banana` (configurable)
- Generate: `POST <provider>/api/v1?path=generate`
- Poll: `GET <provider>/api/v1/jobs/{job_id}` until `completed`
- Output: image URL (saved locally as backup)

### Trello
- Board: `SociClaw Content Calendar`
- Lists: Backlog, quarterly/month buckets, Review, Scheduled, Published
- Card fields: title, description, due date, labels, approval checklist, image attachment

### Notion
- Database properties (expected):
  - `Title` (title)
  - `Content` (rich_text)
  - `Date` (date)
  - `Status` (select: Draft/Review/Scheduled/Published)
  - `Category` (multi_select)
  - `Image` (files)
  - `Engagement` (number)

### Credits (off-chain)
- Credits are managed by the user's SociClaw account.
- SociClaw uses the provisioned API key to generate images.

## Environment Variables
- `XAI_API_KEY`
- `SOCICLAW_IMAGE_API_KEY` (recommended single-account key)
- `SOCICLAW_IMAGE_MODEL` (default: `nano-banana`)
- `SOCICLAW_IMAGE_GENERATE_URL` (default: `https://<image-api-domain>/api/v1?path=generate`)
- `SOCICLAW_IMAGE_JOBS_URL` (default: `https://<image-api-domain>/api/v1/jobs/`)
- `SOCICLAW_IMAGE_API_BASE_URL` (used by topup SDK)
- `SOCICLAW_PROVISION_URL` (recommended; your backend gateway)
- `SOCICLAW_PROVISION_UPSTREAM_URL` (optional; upstream provisioning endpoint override)
- `SOCICLAW_INTERNAL_TOKEN` (optional; protects the gateway)
- `OPENCLAW_PROVISION_SECRET` (admin-only; server-side only)
- `TRELLO_API_KEY`
- `TRELLO_TOKEN`
- `TRELLO_BOARD_ID`
- `NOTION_API_KEY`
- `NOTION_DATABASE_ID`
