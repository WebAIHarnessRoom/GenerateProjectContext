"""E-PAR-* CLI 与 API 输出一致性。"""
import subprocess
import sys

import pytest

from project_context import generate_context


def _args_to_kwargs(args):
    """把 CLI 参数列表转换成 generate_context 的关键字参数。"""
    kw = {}
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--no-git":
            kw["include_git"] = False
            i += 1
        elif a == "--no-content":
            kw["include_content"] = False
            i += 1
        elif a == "--no-ast":
            kw["include_ast"] = False
            i += 1
        elif a == "--exclude":
            kw.setdefault("exclude", []).append(args[i + 1])
            i += 2
        elif a == "--exclude-dir":
            kw.setdefault("exclude_dirs", []).append(args[i + 1])
            i += 2
        elif a == "--languages":
            kw["languages"] = args[i + 1]
            i += 2
        elif a == "--max-file-size":
            kw["max_file_size_kb"] = int(args[i + 1])
            i += 2
        else:
            i += 1
    return kw


def _run_cli(root, out_path, args):
    cmd = [
        sys.executable, "-m", "project_context",
        str(root), "-o", str(out_path), "--no-timestamp",
    ] + args
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0, f"CLI 失败: {proc.stderr}"
    return out_path.read_text(encoding="utf-8")


@pytest.mark.parametrize("args", [
    [],
    ["--no-git"],
    ["--no-content"],
    ["--no-ast"],
    ["--exclude", "*.pb.go"],
    ["--exclude-dir", "third_party"],
    ["--languages", "python"],
])
def test_cli_api_parity(tmp_path, py_only, args):
    cli_out = tmp_path / "cli.md"
    cli_md = _run_cli(py_only, cli_out, args)

    api_kwargs = _args_to_kwargs(args)
    api_md = generate_context(
        root=py_only, output=None, no_timestamp=True, **api_kwargs,
    )
    assert cli_md == api_md, f"CLI 与 API 输出不一致 (args={args})"


def test_api_returns_path(tmp_path, py_only):
    out = tmp_path / "ctx.md"
    r = generate_context(root=py_only, output=out, no_timestamp=True)
    assert r == out.resolve()
    assert out.is_file()


def test_api_returns_str_when_no_output(py_only):
    md = generate_context(root=py_only, output=None, no_timestamp=True)
    assert isinstance(md, str)
    assert md.startswith("# 项目上下文文档")


def test_api_dump_config(py_only):
    text = generate_context(root=py_only, output=None, dump_config=True)
    assert "[filter]" in text
    assert "ignore_dirs" in text