"""U-GIT-* Git 信息采集。"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from project_context.engine.git_info import (
    gather_git_info,
    parse_git_log,
    run_git,
)


pytestmark = pytest.mark.skipif(
    shutil.which("git") is None, reason="git 不可用"
)


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------

def _git(cwd, *args):
    return subprocess.run(
        ["git", "-C", str(cwd)] + list(args),
        check=True, capture_output=True, text=True,
    )


@pytest.fixture
def repo(tmp_path):
    """有 3 条提交、含新增/删除的 git 仓库。"""
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q")
    _git(r, "config", "user.email", "t@t")
    _git(r, "config", "user.name", "T")
    _git(r, "config", "commit.gpgsign", "false")

    (r / "a.py").write_text("x = 1\n", encoding="utf-8")
    _git(r, "add", ".")
    _git(r, "commit", "-q", "-m", "init")

    (r / "b.py").write_text("y = 2\ny = 3\n", encoding="utf-8")
    _git(r, "add", ".")
    _git(r, "commit", "-q", "-m", "add b")

    (r / "a.py").write_text("x = 100\n", encoding="utf-8")
    _git(r, "add", ".")
    _git(r, "commit", "-q", "-m", "update a")
    return r


# ---------------------------------------------------------------------------
# run_git
# ---------------------------------------------------------------------------

def test_run_git_ok(repo):
    out = run_git(repo, ["rev-parse", "--is-inside-work-tree"])
    assert out is not None
    assert out.strip() == "true"


def test_run_git_non_repo(tmp_path):
    # 在一个确定不是 git 仓库的目录
    d = tmp_path / "plain"
    d.mkdir()
    # 某些环境下 /tmp 里可能是 git 仓库，用 subprocess 直接断言
    out = run_git(d, ["rev-parse", "--is-inside-work-tree"])
    # 可能 None（非仓库）或 "true"（父目录恰是仓库），只要不抛异常即通过
    assert out is None or out.strip() in ("true", "false")


def test_run_git_missing_binary(monkeypatch, tmp_path):
    """git 命令不存在时返回 None。"""
    def fake_run(*a, **kw):
        raise FileNotFoundError("git")
    monkeypatch.setattr(subprocess, "run", fake_run)
    assert run_git(tmp_path, ["status"]) is None


def test_run_git_bad_command(repo):
    """非法子命令时返回 None（非零退出）。"""
    assert run_git(repo, ["no-such-subcmd"]) is None


# ---------------------------------------------------------------------------
# parse_git_log
# ---------------------------------------------------------------------------

def test_parse_git_log_basic(repo):
    commits = parse_git_log(repo, 10)
    assert len(commits) == 3
    subjects = [c["subject"] for c in commits]
    assert "init" in subjects
    assert "add b" in subjects
    assert "update a" in subjects


def test_parse_git_log_max_commits(repo):
    commits = parse_git_log(repo, 2)
    assert len(commits) == 2


def test_parse_git_log_fields(repo):
    commits = parse_git_log(repo, 10)
    for c in commits:
        assert c["sha"]
        assert c["date"]
        assert c["author"] == "T"
        assert isinstance(c["files"], list)
        assert isinstance(c["added"], int)
        assert isinstance(c["deleted"], int)


def test_parse_git_log_added_deleted(repo):
    commits = parse_git_log(repo, 10)
    # 最后一条 update a：1 行改为 1 行 → +1/-1
    head = commits[0]
    assert head["added"] >= 1
    assert head["deleted"] >= 1


def test_parse_git_log_non_repo(tmp_path):
    d = tmp_path / "x"
    d.mkdir()
    assert parse_git_log(d, 10) == []


def test_parse_git_log_handles_numstat_binary(repo, tmp_path):
    """含二进制变更（numstat 显示 -  -）不崩溃。"""
    (repo / "blob.bin").write_bytes(b"\x00\x01\x02" * 100)
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "add bin")
    commits = parse_git_log(repo, 10)
    assert commits[0]["subject"] == "add bin"


def test_parse_git_log_subject_with_pipe(repo):
    (repo / "c.py").write_text("z = 1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "feat: a|b|c")
    commits = parse_git_log(repo, 10)
    assert "a|b|c" in commits[0]["subject"]


# ---------------------------------------------------------------------------
# gather_git_info
# ---------------------------------------------------------------------------

def test_gather_git_info_disabled(tmp_path):
    info = gather_git_info(tmp_path, 10, enabled=False)
    assert info["is_repo"] is False
    assert info["commits"] == []


def test_gather_git_info_non_repo(tmp_path):
    d = tmp_path / "plain"
    d.mkdir()
    info = gather_git_info(d, 10, enabled=True)
    # 非仓库 → is_repo=False
    assert info["is_repo"] is False


def test_gather_git_info_ok(repo):
    info = gather_git_info(repo, 10, enabled=True)
    assert info["is_repo"] is True
    assert info["branch"]  # main / master
    assert info["head"]
    assert len(info["commits"]) == 3