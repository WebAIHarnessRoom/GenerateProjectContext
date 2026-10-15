#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 Nuitka 将 project_context 打包为 Windows 可执行文件。

最终产物：
    build/gpc/generate-project-context.exe   (及同目录下的运行时依赖)

用法：
    python build_pc_exe.py
    python build_pc_exe.py --onefile      # 打成单个 exe
    python build_pc_exe.py --clean        # 只清理产物，不编译
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PKG_DIR = ROOT / "project_context"
ENTRY = PKG_DIR / "__main__.py"
CONFIGS = PKG_DIR / "configs"

BUILD_ROOT = ROOT / "build"
OUTPUT_DIR = BUILD_ROOT
TARGET_DIR = BUILD_ROOT / "gpc"
EXE_NAME = "generate-project-context.exe"


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------

def _clean(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    elif path.is_file():
        try:
            path.unlink()
        except FileNotFoundError:
            pass


def _clean_all_staging() -> None:
    """清掉 build/ 下所有 Nuitka 中间产物和旧目标目录。"""
    _clean(TARGET_DIR)
    for p in OUTPUT_DIR.glob("*.dist"):
        _clean(p)
    for p in OUTPUT_DIR.glob("*.build"):
        _clean(p)
    for p in OUTPUT_DIR.glob("*.exe"):
        # 只清掉非目标最终 exe（避免误删 build/gpc/ 之外的旧产物）
        if p.parent == OUTPUT_DIR:
            _clean(p)


def _move_into(src: Path, dst: Path) -> None:
    """把 src 目录下所有内容移动到 dst，保留 src 目录本身（被清空）。"""
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dst / item.name
        _clean(target)
        shutil.move(str(item), str(target))


def _find_staging_dist() -> Path | None:
    """Nuitka 生成的 *.dist 目录名取决于入口；动态查找。"""
    candidates = [p for p in OUTPUT_DIR.glob("*.dist") if p.is_dir()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def build(onefile: bool) -> int:
    if not ENTRY.is_file():
        print(f"[error] 入口不存在: {ENTRY}", file=sys.stderr)
        return 1
    if not CONFIGS.is_dir():
        print(f"[error] configs 目录不存在: {CONFIGS}", file=sys.stderr)
        return 1

    _clean_all_staging()

    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--python-flag=-m",                       # 以 -m 方式运行包
        "--mingw64",
        "--assume-yes-for-downloads",
        f"--include-data-dir={CONFIGS}=project_context/configs",
        "--include-package=project_context",
        f"--output-dir={OUTPUT_DIR}",
        f"--output-filename={EXE_NAME}",
        "--remove-output",
        "--nofollow-import-to=pytest",
        "--noinclude-pytest-mode=nofollow",
        "--noinclude-setuptools-mode=nofollow",
        "--noinclude-unittest-mode=nofollow",
        "project_context",                        # 传包名（配合 -m）
    ]
    if onefile:
        cmd.append("--onefile")

    print("$ " + " ".join(str(c) for c in cmd))
    rc = subprocess.run(cmd, cwd=str(ROOT)).returncode
    if rc != 0:
        print(f"\n[FAIL] Nuitka 打包失败 (exit={rc})", file=sys.stderr)
        return rc

    # 落地到 build/gpc/
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    if onefile:
        # onefile 时 Nuitka 会生成 <entry>.exe（不是 dist 目录）
        candidates = [
            p for p in OUTPUT_DIR.glob("*.exe")
            if p.parent == OUTPUT_DIR
        ]
        if not candidates:
            print(f"\n[FAIL] 未找到 onefile 产物 (*.exe)", file=sys.stderr)
            return 1
        src = max(candidates, key=lambda p: p.stat().st_mtime)
        shutil.move(str(src), str(TARGET_DIR / EXE_NAME))
    else:
        staging = _find_staging_dist()
        if staging is None:
            print(f"\n[FAIL] 未找到 Nuitka 输出目录 (*.dist)", file=sys.stderr)
            return 1
        _move_into(staging, TARGET_DIR)
        _clean(staging)

    for p in OUTPUT_DIR.glob("*.build"):
        _clean(p)

    exe = TARGET_DIR / EXE_NAME
    if not exe.is_file():
        print(f"\n[FAIL] 未找到可执行文件: {exe}", file=sys.stderr)
        return 1

    size_mb = exe.stat().st_size / 1024 / 1024
    print("\n[OK] 打包成功")
    print(f"     EXE  : {exe}  ({size_mb:.1f} MB)")
    print(f"     分发 : {TARGET_DIR}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="用 Nuitka 打包 project_context")
    parser.add_argument("--onefile", action="store_true",
                        help="生成单个 exe（启动较慢，分发方便）")
    parser.add_argument("--clean", action="store_true",
                        help="只清理 build 产物，不编译")
    args = parser.parse_args()

    if args.clean:
        _clean_all_staging()
        print("[OK] 已清理 build 产物")
        return 0

    return build(onefile=args.onefile)


if __name__ == "__main__":
    sys.exit(main())