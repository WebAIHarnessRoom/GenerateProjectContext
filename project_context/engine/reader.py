"""文件读取。"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple


def read_text_file(path: Path, max_bytes: int) -> Optional[Tuple[str, bool]]:
    try:
        data = path.read_bytes()
    except OSError:
        return None

    truncated = False
    if len(data) > max_bytes:
        data = data[:max_bytes]
        truncated = True

    if b"\x00" in data[:8192]:
        return None

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = data.decode("gbk")
        except UnicodeDecodeError:
            text = data.decode("utf-8", errors="replace")

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text, truncated


def read_all(
    files,
    root: Path,
    max_file_size_kb: int,
    only_py: bool = False,
) -> Dict[str, Tuple[str, bool]]:
    out: Dict[str, Tuple[str, bool]] = {}
    max_bytes = max(1, max_file_size_kb) * 1024
    for f in files:
        if only_py and f.suffix != ".py":
            continue
        rel = f.relative_to(root).as_posix()
        r = read_text_file(f, max_bytes)
        if r is None:
            continue
        out[rel] = r
    return out