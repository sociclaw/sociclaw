import json

from sociclaw.scripts.brand_profile import BrandProfile, save_brand_profile
from sociclaw.scripts.cli import build_parser
from sociclaw.scripts.runtime_config import RuntimeConfig, RuntimeConfigStore
from sociclaw.scripts.state_store import StateStore


def test_cli_doctor_reports_readiness(tmp_path, capsys):
    config_path = tmp_path / "runtime.json"
    brand_path = tmp_path / "company_profile.md"
    state_path = tmp_path / "state.json"
    session_db = tmp_path / "sessions.db"

    RuntimeConfigStore(config_path).save(
        RuntimeConfig(provider="telegram", provider_user_id="123", user_niche="crypto")
    )
    save_brand_profile(BrandProfile(name="SociClaw", keywords=["SociClaw"]), brand_path)
    StateStore(state_path).upsert_user(provider="telegram", provider_user_id="123", image_api_key="sk_user")

    parser = build_parser()
    args = parser.parse_args(
        [
            "doctor",
            "--config-path",
            str(config_path),
            "--brand-profile-path",
            str(brand_path),
            "--state-path",
            str(state_path),
            "--session-db-path",
            str(session_db),
        ]
    )
    rc = args.func(args)
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["provider"] == "telegram"
    assert payload["state_user_found"] is True
    assert payload["state_has_api_key"] is True
    assert payload["brand_profile_ready"] is True
