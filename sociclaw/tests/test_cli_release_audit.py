import json

from sociclaw.scripts.cli import build_parser


def test_cli_release_audit_warn_non_strict(tmp_path, capsys):
    (tmp_path / "README.md").write_text("https://github.com/<your-org>/repo", encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args(
        [
            "release-audit",
            "--root",
            str(tmp_path),
            "--forbidden-terms",
            "Creathoon",
        ]
    )
    rc = args.func(args)
    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "warn"
    assert payload["counts"]["total"] >= 1


def test_cli_release_audit_ok_strict(tmp_path, capsys):
    (tmp_path / "README.md").write_text("SociClaw clean docs", encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args(
        [
            "release-audit",
            "--root",
            str(tmp_path),
            "--forbidden-terms",
            "Creathoon",
            "--strict",
        ]
    )
    rc = args.func(args)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
