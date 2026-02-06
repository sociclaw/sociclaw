"""
Self-update helpers for SociClaw skill installs.

Design goals:
- Safe-by-default (fast-forward only)
- Works for user-managed VPS/mac mini installs
- No destructive git operations
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class UpdateCheckResult:
    ok: bool
    repo_dir: str
    remote: str
    branch: str
    current_commit: Optional[str]
    remote_commit: Optional[str]
    update_available: bool
    error: Optional[str] = None


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=False)


def _stdout(result: subprocess.CompletedProcess) -> str:
    return (result.stdout or "").strip()


def is_git_repo(repo_dir: Path) -> bool:
    res = _run(["git", "rev-parse", "--is-inside-work-tree"], repo_dir)
    return res.returncode == 0 and _stdout(res).lower() == "true"


def check_for_update(repo_dir: Path, *, remote: str = "origin", branch: str = "main", fetch: bool = True) -> UpdateCheckResult:
    if not is_git_repo(repo_dir):
        return UpdateCheckResult(
            ok=False,
            repo_dir=str(repo_dir),
            remote=remote,
            branch=branch,
            current_commit=None,
            remote_commit=None,
            update_available=False,
            error="Not a git repository",
        )

    current = _run(["git", "rev-parse", "HEAD"], repo_dir)
    if current.returncode != 0:
        return UpdateCheckResult(
            ok=False,
            repo_dir=str(repo_dir),
            remote=remote,
            branch=branch,
            current_commit=None,
            remote_commit=None,
            update_available=False,
            error="Unable to read current commit",
        )
    current_commit = _stdout(current)

    if fetch:
        _run(["git", "fetch", remote, branch], repo_dir)

    remote_ref = f"{remote}/{branch}"
    remote_head = _run(["git", "rev-parse", remote_ref], repo_dir)
    if remote_head.returncode != 0:
        return UpdateCheckResult(
            ok=False,
            repo_dir=str(repo_dir),
            remote=remote,
            branch=branch,
            current_commit=current_commit,
            remote_commit=None,
            update_available=False,
            error=f"Unable to resolve remote ref {remote_ref}",
        )
    remote_commit = _stdout(remote_head)

    return UpdateCheckResult(
        ok=True,
        repo_dir=str(repo_dir),
        remote=remote,
        branch=branch,
        current_commit=current_commit,
        remote_commit=remote_commit,
        update_available=(current_commit != remote_commit),
        error=None,
    )


def apply_update(
    repo_dir: Path,
    *,
    remote: str = "origin",
    branch: str = "main",
    allow_dirty: bool = False,
    install_requirements: bool = True,
    python_bin: Optional[str] = None,
) -> dict:
    if not is_git_repo(repo_dir):
        return {"ok": False, "error": "Not a git repository", "repo_dir": str(repo_dir)}

    allowed_remote = os.getenv("SOCICLAW_UPDATE_ALLOWED_REMOTE", "github.com/sociclaw/sociclaw").strip()
    remote_url_res = _run(["git", "remote", "get-url", remote], repo_dir)
    if remote_url_res.returncode != 0:
        return {"ok": False, "error": f"Unable to read remote URL for {remote}", "repo_dir": str(repo_dir)}
    remote_url = _stdout(remote_url_res)
    normalized_remote_url = remote_url.replace(":", "/")
    if normalized_remote_url.endswith(".git"):
        normalized_remote_url = normalized_remote_url[:-4]

    if allowed_remote and allowed_remote not in normalized_remote_url:
        return {
            "ok": False,
            "error": "Remote URL does not match allowed SociClaw origin",
            "repo_dir": str(repo_dir),
            "remote_url": remote_url,
            "allowed_remote": allowed_remote,
        }

    if not allow_dirty:
        status = _run(["git", "status", "--porcelain"], repo_dir)
        if status.returncode != 0:
            return {"ok": False, "error": "Unable to read git status", "repo_dir": str(repo_dir)}
        if _stdout(status):
            return {
                "ok": False,
                "error": "Working tree is dirty; refusing self-update",
                "repo_dir": str(repo_dir),
            }

    checkout = _run(["git", "checkout", branch], repo_dir)
    if checkout.returncode != 0:
        return {"ok": False, "error": f"git checkout {branch} failed", "detail": checkout.stderr.strip()}

    pull = _run(["git", "pull", "--ff-only", remote, branch], repo_dir)
    if pull.returncode != 0:
        return {"ok": False, "error": "git pull --ff-only failed", "detail": pull.stderr.strip()}

    install_result = None
    if install_requirements:
        interpreter = python_bin or sys.executable
        pip = subprocess.run(
            [interpreter, "-m", "pip", "install", "-r", "requirements.txt"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        if pip.returncode != 0:
            return {
                "ok": False,
                "error": "Dependency install failed",
                "detail": (pip.stderr or pip.stdout or "").strip()[:1000],
            }
        install_result = "ok"

    return {
        "ok": True,
        "repo_dir": str(repo_dir),
        "remote": remote,
        "branch": branch,
        "remote_url": remote_url,
        "install_requirements": bool(install_requirements),
        "install_result": install_result,
        "restart_required": True,
    }
