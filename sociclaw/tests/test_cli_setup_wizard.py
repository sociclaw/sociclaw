import json

from sociclaw.scripts.cli import build_parser


def test_cli_setup_wizard_non_interactive(tmp_path, capsys):
    parser = build_parser()
    out_path = tmp_path / "runtime_config.json"
    args = parser.parse_args(
        [
            "setup-wizard",
            "--config-path",
            str(out_path),
            "--provider",
            "telegram",
            "--provider-user-id",
            "123",
            "--user-niche",
            "crypto",
            "--posting-frequency",
            "2/day",
            "--brand-logo-url",
            "https://cdn.example.com/logo.png",
            "--use-trello",
            "--timezone",
            "UTC",
            "--non-interactive",
        ]
    )

    rc = args.func(args)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["saved"] is True
    assert payload["config"]["provider_user_id"] == "123"
    assert payload["config"]["use_trello"] is True
    assert payload["config"]["use_notion"] is False
    assert payload["config"]["brand_logo_url"] == "https://cdn.example.com/logo.png"


def test_cli_setup_alias_non_interactive(tmp_path, capsys):
    parser = build_parser()
    out_path = tmp_path / "runtime_config.json"
    args = parser.parse_args(
        [
            "setup",
            "--config-path",
            str(out_path),
            "--provider",
            "telegram",
            "--provider-user-id",
            "999",
            "--non-interactive",
        ]
    )

    rc = args.func(args)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["saved"] is True
    assert payload["config"]["provider_user_id"] == "999"
