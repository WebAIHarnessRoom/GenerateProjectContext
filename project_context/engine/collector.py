"""文件遍历与降噪。"""
from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Iterable, List

from ..config.models import FilterConfig


def _dir_ignored(name: str, fc: FilterConfig) -> bool:
    if name in fc.ignore_dirs:
        return True
    return any(fnmatch.fnmatchcase(name, p) for p in fc.ignore_dir_globs)


def _file_ignored(name: str, rel_posix: str, fc: FilterConfig) -> bool:
    if Path(name).suffix.lower() in fc.ignore_suffixes:
        return True
    for pat in fc.ignore_file_globs:
        if fnmatch.fnmatchcase(name, pat) or fnmatch.fnmatchcase(rel_posix, pat):
            return True
    for pat in fc.exclude_globs:
        if fnmatch.fnmatchcase(name, pat) or fnmatch.fnmatchcase(rel_posix, pat):
            return True
    return False


def collect_files(
    root: Path,
    filters: FilterConfig,
    output_path: Path | None = None,
) -> List[Path]:
    files: List[Path] = []
    out_resolved = output_path.resolve() if output_path else None

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            d for d in dirnames
            if not _dir_ignored(d, filters)
            and not os.path.islink(os.path.join(dirpath, d))
        )
        for fn in sorted(filenames):
            p = Path(dirpath) / fn
            if os.path.islink(p):
                continue
            try:
                rel = p.relative_to(root).as_posix()
            except ValueError:
                rel = p.name
            if _file_ignored(fn, rel, filters):
                continue
            if out_resolved and p.resolve() == out_resolved:
                continue
            files.append(p)

    files.sort(key=lambda x: x.relative_to(root).as_posix().lower())
    return files