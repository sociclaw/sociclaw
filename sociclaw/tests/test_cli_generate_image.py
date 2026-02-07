import json

import pytest

from sociclaw.scripts.cli import build_parser
from sociclaw.scripts.runtime_config import RuntimeConfig, RuntimeConfigStore
from sociclaw.scripts.state_store import StateStore


def test_cli_generate_image_dry_run(tmp_path, capsys):
    state_path = tmp_path / "state.json"
    StateStore(state_path).upsert_user(
        provider="telegram",
        provider_user_id="123",
        image_api_key="sk_user",
    )

    parser = build_parser()
    args = parser.parse_args(
        [
            "generate-image",
            "--provider",
            "telegram",
            "--provider-user-id",
            "123",
            "--prompt",
            "A blue abstract icon",
            "--dry-run",
            "--state-path",
            str(state_path),
        ]
    )
    rc = args.func(args)
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["dry_run"] is True
    assert payload["has_api_key"] is True
    assert payload["has_image_url"] is False


def test_cli_generate_image_dry_run_uses_brand_logo_from_runtime_config(tmp_path, capsys):
    state_path = tmp_path / "state.json"
    config_path = tmp_path / "runtime_config.json"
    StateStore(state_path).upsert_user(
        provider="telegram",
        provider_user_id="123",
        image_api_key="sk_user",
    )
    RuntimeConfigStore(config_path).save(
        RuntimeConfig(
            provider="telegram",
            provider_user_id="123",
            brand_logo_url="https://cdn.example.com/logo.png",
        )
    )

    parser = build_parser()
    args = parser.parse_args(
        [
            "generate-image",
            "--provider",
            "telegram",
            "--provider-user-id",
            "123",
            "--prompt",
            "A blue abstract icon",
            "--dry-run",
            "--state-path",
            str(state_path),
            "--config-path",
            str(config_path),
        ]
    )
    rc = args.func(args)
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["has_image_url"] is True


def test_cli_generate_image_requires_image_for_nano_banana(tmp_path):
    state_path = tmp_path / "state.json"
    StateStore(state_path).upsert_user(
        provider="telegram",
        provider_user_id="123",
        image_api_key="sk_user",
    )

    parser = build_parser()
    args = parser.parse_args(
        [
            "generate-image",
            "--provider",
            "telegram",
            "--provider-user-id",
            "123",
            "--prompt",
            "A blue abstract icon",
            "--model",
            "nano-banana",
            "--state-path",
            str(state_path),
        ]
    )

    with pytest.raises(SystemExit, match="requires an input image"):
        args.func(args)
