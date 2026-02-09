import json
from pathlib import Path

import pytest

from sociclaw.scripts.cli import build_parser


def _touch(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_cli_reset_requires_yes_without_dry_run():
    parser = build_parser()
    args = parser.parse_args(["reset"])
    with pytest.raises(SystemExit, match="without --yes"):
        args.func(args)


def test_cli_reset_dry_run_does_not_delete(tmp_path, capsys):
    state = tmp_path / "sociclaw_state.json"
    config = tmp_path / "runtime_config.json"
    session_db = tmp_path / "sociclaw_sessions.db"
    brand = tmp_path / "company_profile.md"
    for p in (state, config, session_db, brand):
        _touch(p)

    parser = build_parser()
    args = parser.parse_args(
        [
            "reset",
            "--dry-run",
            "--state-path",
            str(state),
            "--config-path",
            str(config),
            "--session-db-path",
            str(session_db),
            "--brand-profile-path",
            str(brand),
        ]
    )
    rc = args.func(args)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["dry_run"] is True
    assert all(item["existed"] is True for item in payload["files"])
    assert state.exists()
    assert config.exists()
    assert session_db.exists()
    assert brand.exists()


def test_cli_reset_yes_deletes_files(tmp_path, capsys):
    state = tmp_path / "sociclaw_state.json"
    config = tmp_path / "runtime_config.json"
    session_db = tmp_path / "sociclaw_sessions.db"
    brand = tmp_path / "company_profile.md"
    for p in (state, config, session_db, brand):
        _touch(p)

    parser = build_parser()
    args = parser.parse_args(
        [
            "reset",
            "--yes",
            "--state-path",
            str(state),
            "--config-path",
            str(config),
            "--session-db-path",
            str(session_db),
            "--brand-profile-path",
            str(brand),
        ]
    )
    rc = args.func(args)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["reset"] is True
    assert all(item["removed"] is True for item in payload["files"])
    assert not state.exists()
    assert not config.exists()
    assert not session_db.exists()
    assert not brand.exists()
