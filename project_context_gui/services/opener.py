"""跨平台打开文件夹 / 定位文件。"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def open_folder(path: str | Path) -> None:
    """在系统文件管理器中打开一个文件夹。"""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    if p.is_file():
        p = p.parent

    if sys.platform.startswith("win"):
        os.startfile(str(p))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(p)])
    else:
        subprocess.Popen(["xdg-open", str(p)])


def reveal_file(path: str | Path) -> None:
    """在文件管理器中高亮显示一个文件。"""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))

    if sys.platform.startswith("win"):
        subprocess.Popen(["explorer", "/select,", str(p)])
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", str(p)])
    else:
        # 大多数 Linux 文件管理器没有统一 select 协议，打开父目录即可
        subprocess.Popen(["xdg-open", str(p.parent)])