"""语言查找与自动检测。"""
from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple

from ..errors import LanguageNotFoundError
from .loader import find_language_by_name, find_language_files, parse_toml
from .merger import load_language
from .models import FilterConfig, LanguageConfig


def list_available_languages(extra_dirs: List[Path]) -> List[str]:
    return sorted(find_language_files(extra_dirs).keys())


def resolve_active_languages(
    spec,
    root: Path,
    extra_dirs: List[Path],
    language_overrides: Dict[str, Path],
    common_filter: FilterConfig,
    detect_min_files: int,
) -> List[str]:
    if spec == "all":
        return list_available_languages(extra_dirs)

    if spec == "auto" or spec is None:
        return detect_languages(
            root=root,
            extra_dirs=extra_dirs,
            language_overrides=language_overrides,
            common_filter=common_filter,
            detect_min_files=detect_min_files,
        )

    if isinstance(spec, str):
        names = [s.strip() for s in spec.split(",") if s.strip()]
    else:
        names = list(spec)

    available = set(list_available_languages(extra_dirs))
    for n in names:
        if n not in available and n not in language_overrides:
            raise LanguageNotFoundError(n, available)
    return names


def detect_languages(
    root: Path,
    extra_dirs: List[Path],
    language_overrides: Dict[str, Path],
    common_filter: FilterConfig,
    detect_min_files: int,
) -> List[str]:
    _ensure_marker_names(extra_dirs)
    # 1. 预扫描：后缀计数 + 文件名集合 + 目录集合
    suffix_hits: Dict[str, int] = {}
    filenames: Set[str] = set()
    dirs_with: Set[str] = set()

    for dirpath, dirnames, filenames_in_dir in os.walk(root):
        # 用通用规则过滤目录
        dirnames[:] = [
            d for d in dirnames
            if not _dir_ignored(d, common_filter)
        ]
        for fn in filenames_in_dir:
            suffix_hits[Path(fn).suffix.lower()] = suffix_hits.get(Path(fn).suffix.lower(), 0) + 1
            filenames.add(fn)
            if fn in _ALL_MARKER_NAMES:
                dirs_with.add(fn)

    # 2. 候选语言 = 内置 + 额外目录
    candidates = list(find_language_files(extra_dirs).keys())

    # 3. 逐个打分
    active: List[str] = []
    for name in candidates:
        explicit = language_overrides.get(name)
        lcfg, _ = load_language(name, root, explicit, extra_dirs)
        if not lcfg.active:
            continue
        hits = 0
        for s in lcfg.detect.suffixes:
            hits += suffix_hits.get(s.lower(), 0)
        for g in lcfg.detect.file_globs:
            if any(fnmatch.fnmatchcase(fn, g) for fn in filenames):
                hits += 1
        for m in lcfg.detect.dir_markers:
            if m in dirs_with:
                hits += 1
        if hits >= detect_min_files:
            active.append(name)
    return active


_ALL_MARKER_NAMES: Set[str] = set()


def _ensure_marker_names(extra_dirs: List[Path]) -> None:
    """收集所有语言 dir_markers 用到的文件名。"""
    global _ALL_MARKER_NAMES
    if _ALL_MARKER_NAMES:
        return
    names: Set[str] = set()
    for name in find_language_files(extra_dirs).keys():
        p = find_language_by_name(name, extra_dirs)
        if p is None:
            continue
        try:
            d = parse_toml(p)
        except Exception:
            continue
        for m in (d.get("detect", {}) or {}).get("dir_markers", []) or []:
            names.add(m)
    _ALL_MARKER_NAMES = names


def _dir_ignored(name: str, fc: FilterConfig) -> bool:
    if name in fc.ignore_dirs:
        return True
    return any(fnmatch.fnmatchcase(name, p) for p in fc.ignore_dir_globs)