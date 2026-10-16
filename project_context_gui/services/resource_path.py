"""定位资源文件与程序目录。

兼容三种运行方式：
- 源码运行：从项目根查找
- PyInstaller 打包：程序目录 vs 资源目录不同
- Nuitka 打包：用 __compiled__.containing_dir
"""
from __future__ import annotations

import sys
from pathlib import Path


def program_dir() -> Path:
    """返回**可执行文件所在目录**。

    用于查找与 GUI 同级的外部工具，如 generate-project-context.exe。

    - PyInstaller：exe 所在目录（不是 _internal）
    - Nuitka：用 __compiled__.containing_dir
    - 源码运行：项目根
    """
    # Nuitka 2.4+
    try:
        import __compiled__  # type: ignore
        return Path(__compiled__.containing_dir)
    except ImportError:
        pass

    # PyInstaller
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent

    # 源码运行：project_context_gui/services/resource_path.py → 项目根
    return Path(__file__).resolve().parents[2]


def resource_dir() -> Path:
    """返回**资源文件所在目录**。

    用于查找随包分发的数据文件，如图标、内置配置等。

    - PyInstaller：sys._MEIPASS（即 _internal/）
    - 其它情况：同 program_dir()
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return program_dir()


def resource_path(relative: str) -> Path:
    """返回资源文件的绝对路径。

    relative 例如 "resources/app.ico"。
    """
    return resource_dir() / relative


def find_resource(*candidates: str) -> Path | None:
    """按顺序返回第一个存在的资源路径，全不存在返回 None。

    会在资源目录与程序目录两处查找，兼容各种打包场景。
    """
    bases = []
    for base in (resource_dir(), program_dir()):
        if base not in bases:
            bases.append(base)

    for rel in candidates:
        for base in bases:
            p = base / rel
            if p.is_file():
                return p
    return None