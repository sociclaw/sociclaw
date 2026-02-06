import json

from sociclaw.scripts.brand_profile import BrandProfile, save_brand_profile
from sociclaw.scripts.cli import build_parser
from sociclaw.scripts.runtime_config import RuntimeConfig, RuntimeConfigStore
from sociclaw.scripts.state_store import StateStore


def test_cli_smoke_ok(tmp_path, monkeypatch, capsys):
    config_path = tmp_path / "runtime.json"
    state_path = tmp_path / "state.json"
    brand_path = tmp_path / "brand.md"
    tmp_dir = tmp_path / "tmp"

    RuntimeConfigStore(config_path).save(RuntimeConfig(provider="telegram", provider_user_id="123"))
    StateStore(state_path).upsert_user(provider="telegram", provider_user_id="123", image_api_key="sk_user")
    save_brand_profile(BrandProfile(name="SociClaw", keywords=["SociClaw"]), brand_path)

    monkeypatch.setenv("SOCICLAW_PROVISION_URL", "https://api.sociclaw.com/api/sociclaw/provision")
    monkeypatch.setenv("XAI_API_KEY", "x-key")

    parser = build_parser()
    args = parser.parse_args(
        [
            "smoke",
            "--config-path",
            str(config_path),
            "--state-path",
            str(state_path),
            "--brand-profile-path",
            str(brand_path),
            "--tmp-dir",
            str(tmp_dir),
        ]
    )

    rc = args.func(args)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["checks"]["content_generation_ok"] is True
    assert payload["checks"]["user_has_image_api_key"] is True


def test_cli_smoke_warn_without_state(tmp_path, monkeypatch, capsys):
    config_path = tmp_path / "runtime.json"
    RuntimeConfigStore(config_path).save(RuntimeConfig(provider="telegram", provider_user_id="123"))
    monkeypatch.setenv("SOCICLAW_PROVISION_URL", "https://api.sociclaw.com/api/sociclaw/provision")
    monkeypatch.setenv("XAI_API_KEY", "x-key")

    parser = build_parser()
    args = parser.parse_args(["smoke", "--config-path", str(config_path)])
    rc = args.func(args)
    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "warn"
    assert any("provision-image-gateway" in r for r in payload["recommendations"])
