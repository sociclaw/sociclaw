from sociclaw.scripts import updater
from sociclaw.scripts.updater import UpdateCheckResult


class DummyProc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_check_for_update_available(monkeypatch, tmp_path):
    monkeypatch.setattr(updater, "is_git_repo", lambda _: True)

    calls = {"n": 0}

    def fake_run(cmd, cwd):
        calls["n"] += 1
        key = " ".join(cmd)
        if key == "git rev-parse HEAD":
            return DummyProc(stdout="aaa\n")
        if key == "git fetch origin main":
            return DummyProc(stdout="")
        if key == "git rev-parse origin/main":
            return DummyProc(stdout="bbb\n")
        return DummyProc(returncode=1, stderr="bad")

    monkeypatch.setattr(updater, "_run", fake_run)
    result = updater.check_for_update(tmp_path, remote="origin", branch="main", fetch=True)
    assert result.ok is True
    assert result.update_available is True
    assert result.current_commit == "aaa"
    assert result.remote_commit == "bbb"
    assert calls["n"] >= 3


def test_apply_update_blocks_dirty(monkeypatch, tmp_path):
    monkeypatch.setattr(updater, "is_git_repo", lambda _: True)

    def fake_run(cmd, cwd):
        key = " ".join(cmd)
        if key == "git remote get-url origin":
            return DummyProc(stdout="git@github.com:sociclaw/sociclaw.git")
        if key == "git status --porcelain":
            return DummyProc(stdout=" M file.py")
        return DummyProc(stdout="")

    monkeypatch.setattr(updater, "_run", fake_run)
    result = updater.apply_update(tmp_path, remote="origin", branch="main", allow_dirty=False)
    assert result["ok"] is False
    assert "dirty" in result["error"].lower()


def test_apply_update_success_skip_pip(monkeypatch, tmp_path):
    monkeypatch.setattr(updater, "is_git_repo", lambda _: True)

    def fake_run(cmd, cwd):
        key = " ".join(cmd)
        if key == "git remote get-url origin":
            return DummyProc(stdout="git@github.com:sociclaw/sociclaw.git")
        if key == "git status --porcelain":
            return DummyProc(stdout="")
        if key == "git checkout main":
            return DummyProc(stdout="")
        if key == "git pull --ff-only origin main":
            return DummyProc(stdout="updated")
        return DummyProc(stdout="")

    monkeypatch.setattr(updater, "_run", fake_run)
    result = updater.apply_update(
        tmp_path,
        remote="origin",
        branch="main",
        allow_dirty=False,
        install_requirements=False,
    )
    assert result["ok"] is True
    assert result["restart_required"] is True


def test_apply_update_dirty_auto_stash(monkeypatch, tmp_path):
    monkeypatch.setattr(updater, "is_git_repo", lambda _: True)

    calls = {"stash": 0}

    def fake_run(cmd, cwd):
        key = " ".join(cmd)
        if key == "git remote get-url origin":
            return DummyProc(stdout="git@github.com:sociclaw/sociclaw.git")
        if key == "git status --porcelain":
            return DummyProc(stdout="?? new.file")
        if key == "git rev-parse --abbrev-ref HEAD":
            return DummyProc(stdout="fix/custom\n")
        if key.startswith("git stash push -u -m sociclaw-auto-stash "):
            calls["stash"] += 1
            return DummyProc(stdout="Saved working directory and index state")
        if key == "git checkout main":
            return DummyProc(stdout="")
        if key == "git pull --ff-only origin main":
            return DummyProc(stdout="updated")
        return DummyProc(stdout="")

    monkeypatch.setattr(updater, "_run", fake_run)
    result = updater.apply_update(
        tmp_path,
        remote="origin",
        branch="main",
        allow_dirty=False,
        auto_stash=True,
        install_requirements=False,
    )
    assert result["ok"] is True
    assert result["auto_stashed"] is True
    assert calls["stash"] == 1


def test_cli_self_update_requires_yes(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("SOCICLAW_SELF_UPDATE_ENABLED", "true")
    from sociclaw.scripts import cli

    monkeypatch.setattr(
        cli,
        "check_for_update",
        lambda *args, **kwargs: UpdateCheckResult(
            ok=True,
            repo_dir=str(tmp_path),
            remote="origin",
            branch="main",
            current_commit="a",
            remote_commit="b",
            update_available=True,
            error=None,
        ),
    )
    parser = cli.build_parser()
    args = parser.parse_args(["self-update", "--repo-dir", str(tmp_path)])
    rc = args.func(args)
    assert rc == 1
    payload = capsys.readouterr().out
    assert "run again with --yes" in payload


def test_cli_self_update_disabled_without_env(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("SOCICLAW_SELF_UPDATE_ENABLED", raising=False)
    from sociclaw.scripts import cli

    parser = cli.build_parser()
    args = parser.parse_args(["self-update", "--repo-dir", str(tmp_path)])
    rc = args.func(args)
    assert rc == 1
    payload = capsys.readouterr().out
    assert "Self-update is disabled" in payload or "self-update-disabled" in payload
