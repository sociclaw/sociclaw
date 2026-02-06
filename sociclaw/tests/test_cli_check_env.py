import json

from sociclaw.scripts.cli import build_parser


def _run_check_env(tmp_path, monkeypatch, env):
    keys = [
        "SOCICLAW_PROVISION_URL",
        "SOCICLAW_IMAGE_API_KEY",
        "XAI_API_KEY",
        "TRELLO_API_KEY",
        "TRELLO_TOKEN",
        "NOTION_API_KEY",
        "NOTION_DATABASE_ID",
    ]
    for key in keys:
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    parser = build_parser()
    return parser.parse_args(["check-env", "--tmp-dir", str(tmp_path)])


def test_check_env_errors_when_missing_image_config(tmp_path, monkeypatch, capsys):
    args = _run_check_env(tmp_path, monkeypatch, {})
    rc = args.func(args)
    assert rc == 1

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    assert payload["checks"]["TMP_WRITABLE"] is True


def test_check_env_warns_without_xai(tmp_path, monkeypatch, capsys):
    args = _run_check_env(
        tmp_path,
        monkeypatch,
        {"SOCICLAW_PROVISION_URL": "https://api.sociclaw.com/api/sociclaw/provision"},
    )
    rc = args.func(args)
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "warn"
    assert payload["checks"]["SOCICLAW_PROVISION_URL"] is True


def test_check_env_ok_with_minimum_settings(tmp_path, monkeypatch, capsys):
    args = _run_check_env(
        tmp_path,
        monkeypatch,
        {
            "SOCICLAW_PROVISION_URL": "https://api.sociclaw.com/api/sociclaw/provision",
            "XAI_API_KEY": "xai-token",
        },
    )
    rc = args.func(args)
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
