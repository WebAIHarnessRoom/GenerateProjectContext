"""CLI main() 的进程内测试（覆盖 cli.py）。"""
import sys
from pathlib import Path

import pytest

from project_context.cli import main


def test_cli_basic(tmp_path, capsys):
    proj = tmp_path / "p"
    proj.mkdir()
    (proj / "a.py").write_text("x = 1\n", encoding="utf-8")
    out = tmp_path / "ctx.md"

    rc = main([str(proj), "-o", str(out), "--no-timestamp", "--no-git"])
    assert rc == 0
    assert out.is_file()

    captured = capsys.readouterr()
    assert "DONE" in captured.out


def test_cli_quiet(tmp_path):
    proj = tmp_path / "p"
    proj.mkdir()
    (proj / "a.py").write_text("x = 1\n", encoding="utf-8")
    out = tmp_path / "ctx.md"

    rc = main([str(proj), "-o", str(out), "--no-timestamp",
               "--no-git", "--quiet"])
    assert rc == 0


def test_cli_default_output(tmp_path):
    proj = tmp_path / "p"
    proj.mkdir()
    (proj / "a.py").write_text("x = 1\n", encoding="utf-8")
    rc = main([str(proj), "--no-timestamp", "--no-git"])
    assert rc == 0
    assert (proj / "PROJECT_CONTEXT.md").is_file()


def test_cli_no_content(tmp_path, capsys):
    proj = tmp_path / "p"
    proj.mkdir()
    (proj / "a.py").write_text("x = 1\n", encoding="utf-8")
    out = tmp_path / "ctx.md"
    rc = main([str(proj), "-o", str(out), "--no-timestamp",
               "--no-git", "--no-content"])
    assert rc == 0
    md = out.read_text(encoding="utf-8")
    assert "## 4. 源码与配置文件内容" not in md


def test_cli_no_ast(tmp_path):
    proj = tmp_path / "p"
    proj.mkdir()
    (proj / "a.py").write_text("x = 1\n", encoding="utf-8")
    out = tmp_path / "ctx.md"
    rc = main([str(proj), "-o", str(out), "--no-timestamp",
               "--no-git", "--no-ast"])
    assert rc == 0
    md = out.read_text(encoding="utf-8")
    assert "## 3. 代码结构总览" not in md


def test_cli_exclude(tmp_path):
    proj = tmp_path / "p"
    proj.mkdir()
    (proj / "a.py").write_text("x = 1\n", encoding="utf-8")
    (proj / "skip.pb.go").write_text("package x\n", encoding="utf-8")
    out = tmp_path / "ctx.md"
    rc = main([str(proj), "-o", str(out), "--no-timestamp",
               "--no-git", "--exclude", "*.pb.go"])
    assert rc == 0
    md = out.read_text(encoding="utf-8")
    assert "skip.pb.go" not in md


def test_cli_exclude_dir(tmp_path):
    proj = tmp_path / "p"
    proj.mkdir()
    (proj / "a.py").write_text("x = 1\n", encoding="utf-8")
    (proj / "vendor").mkdir()
    (proj / "vendor" / "v.py").write_text("y = 1\n", encoding="utf-8")
    out = tmp_path / "ctx.md"
    rc = main([str(proj), "-o", str(out), "--no-timestamp",
               "--no-git", "--exclude-dir", "vendor"])
    assert rc == 0
    md = out.read_text(encoding="utf-8")
    assert "vendor/v.py" not in md


def test_cli_languages_explicit(tmp_path):
    proj = tmp_path / "p"
    proj.mkdir()
    (proj / "a.py").write_text("x = 1\n", encoding="utf-8")
    out = tmp_path / "ctx.md"
    rc = main([str(proj), "-o", str(out), "--no-timestamp",
               "--no-git", "--languages", "python"])
    assert rc == 0


def test_cli_languages_invalid(tmp_path, capsys):
    proj = tmp_path / "p"
    proj.mkdir()
    rc = main([str(proj), "--languages", "no_such_lang_xyz",
               "--no-timestamp", "--no-git"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "config-error" in err


def test_cli_list_languages(tmp_path, capsys):
    rc = main([str(tmp_path), "--list-languages"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "python" in out
    assert "node" in out


def test_cli_dump_config(tmp_path, capsys):
    proj = tmp_path / "p"
    proj.mkdir()
    (proj / "a.py").write_text("x = 1\n", encoding="utf-8")
    rc = main([str(proj), "--dump-config", "--no-timestamp", "--no-git"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "[filter]" in out
    assert "ignore_dirs" in out


def test_cli_nonexistent_root(tmp_path, capsys):
    rc = main([str(tmp_path / "nope"), "--no-timestamp"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "error" in err


def test_cli_max_file_size(tmp_path):
    proj = tmp_path / "p"
    proj.mkdir()
    (proj / "a.py").write_text("x = 1\n", encoding="utf-8")
    out = tmp_path / "ctx.md"
    rc = main([str(proj), "-o", str(out), "--no-timestamp",
               "--no-git", "--max-file-size", "300"])
    assert rc == 0


def test_cli_no_git(tmp_path):
    proj = tmp_path / "p"
    proj.mkdir()
    (proj / "a.py").write_text("x = 1\n", encoding="utf-8")
    out = tmp_path / "ctx.md"
    rc = main([str(proj), "-o", str(out), "--no-timestamp", "--no-git"])
    assert rc == 0
    md = out.read_text(encoding="utf-8")
    assert "Git 仓库：未检测到" in md


def test_cli_inherit_defaults_flags(tmp_path):
    proj = tmp_path / "p"
    proj.mkdir()
    (proj / "a.py").write_text("x = 1\n", encoding="utf-8")
    out = tmp_path / "ctx.md"
    rc = main([str(proj), "-o", str(out), "--no-timestamp",
               "--no-git", "--no-inherit-defaults"])
    assert rc == 0