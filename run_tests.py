#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_tests.py —— 一键运行测试套件。

用法：
    python run_tests.py                     # 运行全部
    python run_tests.py -k merger           # 透传 -k 给 pytest
    python run_tests.py tests/unit          # 只跑单元
    python run_tests.py --cov               # 加覆盖率
    python run_tests.py --gates             # 只跑门禁
    python run_tests.py --quiet             # 简洁输出
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
TESTS_DIR = REPO_ROOT / "tests"


def _check_env() -> None:
    if sys.version_info < (3, 9):
        print(f"[错误] 需要 Python 3.9+，当前 {sys.version}", file=sys.stderr)
        sys.exit(2)
    try:
        import pytest  # noqa: F401
    except ImportError:
        print("[错误] 缺少 pytest。请先安装：pip install pytest pytest-cov",
              file=sys.stderr)
        sys.exit(2)
    if not TESTS_DIR.is_dir():
        print(f"[错误] 测试目录不存在：{TESTS_DIR}", file=sys.stderr)
        sys.exit(2)


def main() -> int:
    _check_env()

    argv = sys.argv[1:]

    # 提取自有开关
    cov = "--cov" in argv
    gates = "--gates" in argv
    quiet = "--quiet" in argv
    rest = [a for a in argv if a not in ("--cov", "--gates", "--quiet")]

    cmd = [sys.executable, "-m", "pytest"]

    # 目标
    has_target = any(not a.startswith("-") and Path(a).exists() for a in rest)
    if not has_target and not any(a.startswith("-k") for a in rest):
        cmd.append(str(TESTS_DIR))

    # 输出风格（quiet 只在未显式 -v/-q 时生效）
    has_verbosity = any(a in ("-v", "-vv", "-q", "--quiet") for a in rest)
    if not has_verbosity:
        if quiet:
            cmd.extend(["-q", "--no-header"])
        else:
            cmd.extend(["-v", "--tb=short"])

    # 覆盖率
    if cov:
        cmd.extend([
            "--cov=project_context",
            "--cov-report=term-missing",
            "--cov-report=html:.coverage_html",
        ])

    # 门禁
    if gates:
        cmd.extend(["-m", "gate"])

    # 透传剩余参数
    cmd.extend(rest)

    print(f"$ {' '.join(cmd)}\n")
    code = subprocess.run(cmd, cwd=str(REPO_ROOT)).returncode

    if code == 0:
        print("\n[OK] 全部通过")
    else:
        print(f"\n[FAIL] 存在失败（exit={code}）")

    if cov and (REPO_ROOT / ".coverage_html").is_dir():
        print(f"覆盖率报告：{REPO_ROOT / '.coverage_html' / 'index.html'}")

    return code


if __name__ == "__main__":
    sys.exit(main())