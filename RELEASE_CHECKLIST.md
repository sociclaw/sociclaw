# SociClaw Release Checklist

## Pre-release
- [ ] Run tests: `python -m pytest -q`
- [ ] Run env preflight: `python -m sociclaw.scripts.cli check-env`
- [ ] Run smoke test: `python -m sociclaw.scripts.cli smoke`
- [ ] Run staging E2E baseline: `python -m sociclaw.scripts.cli e2e-staging --config-path .sociclaw/runtime_config.json --state-path .tmp/sociclaw_state.json`
- [ ] Run repo audit: `python -m sociclaw.scripts.cli release-audit --strict`

## API (Vercel)
- [ ] `OPENCLAW_PROVISION_SECRET` configured in API project
- [ ] `SOCICLAW_PROVISION_UPSTREAM_URL` configured in API project
- [ ] Rate limits configured (`SOCICLAW_RATE_LIMIT_*`)
- [ ] Deploy healthy at `https://api.sociclaw.com/api/sociclaw/provision`

## Skill Distribution
- [ ] `SKILL.md` points to correct homepage/domain
- [ ] `.env.example` has no sensitive values
- [ ] `.gitignore` excludes local runtime artifacts (`.tmp/`, `.sociclaw/`, `.env`)
- [ ] No forbidden third-party branding references in public docs

## Optional live path
- [ ] Real topup test: `topup-start` + `topup-claim --wait`
- [ ] Real image generation test: `generate-image` (without `--dry-run`)
- [ ] Trello/Notion connectivity validated (`e2e-staging --run-sync`)
