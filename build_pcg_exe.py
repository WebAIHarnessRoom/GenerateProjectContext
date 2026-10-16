#!/usr/bin/env python3
"""把 project_context GUI 用 PyInstaller 打包为独立 EXE。

默认 onedir 模式，产物在 build/gpcg/。
不打包 project_context 包与 CLI EXE——GUI 通过配置
generate-project-context.exe 路径来执行。

用法：
    python build_pcg_exe.py                 # 默认构建（onedir，无控制台）
    python build_pcg_exe.py --console       # 保留控制台窗口（调试用）
    python build_pcg_exe.py --onefile       # 单文件模式
    python build_pcg_exe.py --clean         # 仅清理
    python build_pcg_exe.py --no-clean      # 保留上次构建缓存（增量）
    python build_pcg_exe.py --slim          # 精简体积（排除未使用的 Qt 模块）
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path


# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent
BUILD_DIR = ROOT / "build"
OUTPUT_DIR = BUILD_DIR / "gpcg"           # 最终产物
WORK_DIR = BUILD_DIR / "gpcg_build"       # PyInstaller 中间文件
SPEC_DIR = BUILD_DIR / "gpcg_spec"        # .spec 文件目录
EXE_BASENAME = "generate-project-context-gui"

ENTRY_POINT = ROOT / "project_context_gui" / "__main__.py"
ICON_PATH = ROOT / "resources" / "app.ico"


# ---------------------------------------------------------------------------
# 精简排除项
# ---------------------------------------------------------------------------

SLIM_EXCLUDES = [
    # Qt 未使用模块
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuick3D",
    "PySide6.QtQuickWidgets",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DRender",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DExtras",
    "PySide6.QtSql",
    "PySide6.QtTest",
    "PySide6.QtBluetooth",
    "PySide6.QtNfc",
    "PySide6.QtPositioning",
    "PySide6.QtSensors",
    "PySide6.QtSerialPort",
    "PySide6.QtNetworkAuth",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtStateMachine",
    "PySide6.QtTextToSpeech",
    "PySide6.QtWebChannel",
    "PySide6.QtWebSockets",
    "PySide6.QtDesigner",
    "PySide6.QtHelp",
    "PySide6.QtUiTools",

    # Python 标准库中未使用的部分
    "tkinter",
    "unittest",
    "pydoc",
    "doctest",
    "pdb",

    # 测试框架
    "pytest",
    "nose",
    "nose2",
    "_pytest",

    # 打包工具自身
    "PyInstaller",
    "setuptools",
    "pip",
    "wheel",
]


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------

def _log(msg: str) -> None:
    print(f"[build] {msg}", flush=True)


def _error(msg: str) -> None:
    print(f"[build][ERROR] {msg}", file=sys.stderr, flush=True)


def check_environment() -> None:
    """检查 PyInstaller 是否可用。"""
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        _error(
            "未安装 PyInstaller。请先执行：\n"
            "    pip install pyinstaller\n"
        )
        sys.exit(1)

    if not ENTRY_POINT.is_file():
        _error(f"未找到入口文件：{ENTRY_POINT}")
        sys.exit(1)

    _log(f"入口文件：{ENTRY_POINT}")
    _log(f"Python：{sys.executable}")
    _log(f"PyInstaller：{_pyinstaller_version()}")

    if ICON_PATH.is_file():
        _log(f"图标文件：{ICON_PATH}")
    else:
        _log("未找到图标，构建将不使用自定义图标")


def _pyinstaller_version() -> str:
    try:
        import PyInstaller
        return getattr(PyInstaller, "__version__", "unknown")
    except Exception:
        return "unknown"


def _rmtree(p: Path) -> None:
    if p.is_dir():
        shutil.rmtree(p, ignore_errors=True)
    elif p.exists():
        try:
            p.unlink()
        except OSError:
            pass


def clean() -> None:
    """清理输出目录、中间目录、spec 目录。"""
    for d in (OUTPUT_DIR, WORK_DIR, SPEC_DIR):
        if d.exists():
            _log(f"删除旧目录：{d}")
            shutil.rmtree(d, ignore_errors=True)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    SPEC_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# 构建命令
# ---------------------------------------------------------------------------

def build_command(
    onefile: bool = False,
    console: bool = False,
    clean_build: bool = False,
    slim: bool = False,
) -> list:
    """生成 PyInstaller 命令行。"""
    args = [sys.executable, "-m", "PyInstaller"]

    # 模式
    args.append("--onefile" if onefile else "--onedir")

    # 控制台
    args.append("--console" if console else "--windowed")

    # 其它基础选项
    args += [
        "--noconfirm",
        f"--name={EXE_BASENAME}",
        f"--distpath={OUTPUT_DIR}",
        f"--workpath={WORK_DIR}",
        f"--specpath={SPEC_DIR}",
    ]

    if clean_build:
        args.append("--clean")

    # 图标（EXE 文件图标）
    if ICON_PATH.is_file():
        args.append(f"--icon={ICON_PATH}")

        # 同时把图标作为数据文件打进产物，供运行时 setWindowIcon 使用
        sep = ";" if sys.platform.startswith("win") else ":"
        args.append(f"--add-data={ICON_PATH}{sep}resources")

    # 精简排除
    if slim:
        for mod in SLIM_EXCLUDES:
            args.append(f"--exclude-module={mod}")

    # 收集必要的包（PyInstaller 一般能自动处理 PySide6，这里显式声明更稳）
    args += [
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=PySide6.QtWidgets",
    ]

    # 入口
    args.append(str(ENTRY_POINT))
    return args


def run_build(args: list) -> int:
    """执行 PyInstaller 构建。"""
    _log("构建命令：")
    print("    " + " ".join(str(a) for a in args), flush=True)
    print()

    t0 = time.monotonic()
    try:
        proc = subprocess.run(args, cwd=str(ROOT))
    except KeyboardInterrupt:
        _error("用户中断")
        return 130

    dt = time.monotonic() - t0
    _log(f"构建耗时 {dt:.1f} 秒，退出码 {proc.returncode}")
    return proc.returncode


# ---------------------------------------------------------------------------
# 产物检查
# ---------------------------------------------------------------------------

def verify_output(onefile: bool) -> None:
    """检查产物是否完整。"""
    exe = OUTPUT_DIR / f"{EXE_BASENAME}.exe"
    if sys.platform != "win32":
        exe = OUTPUT_DIR / EXE_BASENAME

    if not exe.is_file():
        _error(f"未找到主程序：{exe}")
        _list_output()
        return

    _log(f"主程序：{exe}")
    _log(f"主程序大小：{exe.stat().st_size / 1024 / 1024:.1f} MB")

    # onedir 模式下检查 _internal 目录
    if not onefile and sys.platform.startswith("win"):
        internal = OUTPUT_DIR / "_internal"
        if internal.is_dir():
            _log(f"依赖目录：{internal}")
        else:
            _log("未找到 _internal 目录（可能是旧版 PyInstaller 结构）")

    # 检查图标是否随包
    for candidate in (
        OUTPUT_DIR / "resources" / "app.ico",
        OUTPUT_DIR / "_internal" / "resources" / "app.ico",
    ):
        if candidate.is_file():
            _log(f"图标资源：{candidate}")
            break
    else:
        _log("警告：未找到打包后的图标资源")


def _list_output() -> None:
    """产物缺失时列出目录内容，便于排查。"""
    _log(f"目录内容：{OUTPUT_DIR}")
    if OUTPUT_DIR.is_dir():
        for item in sorted(OUTPUT_DIR.iterdir()):
            _log(f"  {item.name}")


def report_size() -> None:
    """统计产物总体积。"""
    total = 0
    file_count = 0
    for p in OUTPUT_DIR.rglob("*"):
        if p.is_file():
            total += p.stat().st_size
            file_count += 1
    _log(f"产物共 {file_count} 个文件，总计 "
         f"{total / 1024 / 1024:.1f} MB")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description="把 project_context GUI 打包为独立 EXE（PyInstaller）"
    )
    ap.add_argument(
        "--onefile", action="store_true",
        help="单文件模式（启动较慢，不推荐 GUI 使用）",
    )
    ap.add_argument(
        "--console", action="store_true",
        help="保留控制台窗口（默认隐藏，便于排查启动崩溃）",
    )
    ap.add_argument(
        "--clean", action="store_true",
        help="仅清理后退出",
    )
    ap.add_argument(
        "--no-clean", action="store_true",
        help="保留上次构建缓存（增量构建）",
    )
    ap.add_argument(
        "--slim", action="store_true",
        help="精简体积：排除未使用的 Qt 模块与测试框架",
    )
    args = ap.parse_args()

    check_environment()

    if args.clean:
        clean()
        _log("清理完成")
        return 0

    if not args.no_clean:
        clean()

    cmd = build_command(
        onefile=args.onefile,
        console=args.console,
        clean_build=False,
        slim=args.slim,
    )
    code = run_build(cmd)
    if code != 0:
        _error(f"PyInstaller 构建失败，退出码 {code}")
        return code

    verify_output(onefile=args.onefile)
    report_size()

    print()
    _log("构建完成")
    _log(f"输出目录：{OUTPUT_DIR}")
    _log("")
    _log("后续步骤：")
    _log("  1. 把 generate-project-context.exe 拷贝到 build/gpcg/ 同一目录")
    _log("  2. 双击 generate-project-context-gui.exe 启动")
    _log("  3. 首次运行可在「设置」中指定 CLI EXE 路径")
    return 0


if __name__ == "__main__":
    sys.exit(main())