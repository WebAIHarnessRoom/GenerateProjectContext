"""R-OLD-* 旧 CLI 参数回归。"""
import subprocess
import sys

import pytest


def _run_cli(root, *args):
    cmd = [sys.executable, "-m", "project_context", str(root)] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True)


def test_legacy_root_positional(tmp_path, py_only):
    out = tmp_path / "ctx.md"
    p = _run_cli(py_only, "-o", str(out), "--no-timestamp")
    assert p.returncode == 0
    assert out.is_file()


def test_legacy_max_file_size(tmp_path, py_only):
    out = tmp_path / "ctx.md"
    p = _run_cli(py_only, "-o", str(out), "--no-timestamp",
                 "--max-file-size", "300")
    assert p.returncode == 0


def test_legacy_max_git_commits(tmp_path, py_only):
    out = tmp_path / "ctx.md"
    p = _run_cli(py_only, "-o", str(out), "--no-timestamp",
                 "--max-git-commits", "10")
    assert p.returncode == 0


def test_legacy_no_git(tmp_path, py_only):
    out = tmp_path / "ctx.md"
    p = _run_cli(py_only, "-o", str(out), "--no-timestamp", "--no-git")
    assert p.returncode == 0
    md = out.read_text(encoding="utf-8")
    assert "## 5. Git 提交历史" not in md


def test_legacy_no_content(tmp_path, py_only):
    out = tmp_path / "ctx.md"
    p = _run_cli(py_only, "-o", str(out), "--no-timestamp", "--no-content")
    assert p.returncode == 0
    md = out.read_text(encoding="utf-8")
    assert "## 4. 源码与配置文件内容" not in md


def test_legacy_no_ast(tmp_path, py_only):
    out = tmp_path / "ctx.md"
    p = _run_cli(py_only, "-o", str(out), "--no-timestamp", "--no-ast")
    assert p.returncode == 0
    md = out.read_text(encoding="utf-8")
    assert "## 3. 代码结构总览" not in md


def test_legacy_exclude(tmp_path, py_node):
    out = tmp_path / "ctx.md"
    p = _run_cli(py_node, "-o", str(out), "--no-timestamp",
                 "--exclude", "*.ts")
    assert p.returncode == 0
    md = out.read_text(encoding="utf-8")
    assert "index.ts" not in md


def test_legacy_default_output(tmp_path, py_only):
    """不指定 -o 时输出到 <root>/PROJECT_CONTEXT.md。"""
    p = _run_cli(py_only, "--no-timestamp", "--no-git")
    assert p.returncode == 0
    assert (py_only / "PROJECT_CONTEXT.md").is_file()


def test_legacy_document_has_core_sections(tmp_path, py_only):
    out = tmp_path / "ctx.md"
    _run_cli(py_only, "-o", str(out), "--no-timestamp", "--no-git")
    md = out.read_text(encoding="utf-8")
    assert "## 1. 项目概览" in md
    assert "## 2. 目录结构" in md
    assert "## 3. 代码结构总览" in md
    assert "## 4. 源码与配置文件内容" in md