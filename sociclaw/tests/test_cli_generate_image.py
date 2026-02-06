import json

from sociclaw.scripts.cli import build_parser
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
